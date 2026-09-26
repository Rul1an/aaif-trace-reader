"""Local cases for the effects slice and the parsing contract.

Records built here are labeled local: they are this reader's own cases
(DESIGN.md section 8), not the kit's, and no expected-answer file is read.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import unittest
from pathlib import Path

from aaif_reader import parse
from aaif_reader.cli import read

ROOT = Path(__file__).resolve().parent.parent
MAPPING = (ROOT / "mappings" / "test-kit-afc26fdd.json").read_bytes()
KIT = ROOT / "inputs" / "test-kit-afc26fdd2199844bf7dff23879739e941fa81107" / "cases"


def attr(k, v):
    if isinstance(v, bool):
        return {"key": k, "value": {"boolValue": v}}
    if isinstance(v, int):
        return {"key": k, "value": {"intValue": str(v)}}
    if isinstance(v, float):
        return {"key": k, "value": {"doubleValue": v}}
    return {"key": k, "value": {"stringValue": v}}


def span(sid, name, **attrs):
    return {"traceId": "t" * 32, "spanId": sid, "parentSpanId": "", "name": name,
            "startTimeUnixNano": "1", "endTimeUnixNano": "2",
            "attributes": [attr(k.replace("__", "."), v) for k, v in attrs.items()]}


def export(*groups):
    return json.dumps({"resourceSpans": [
        {"resource": {"attributes": [attr("service.name", svc)]}, "scopeSpans": [{"scope": {"name": "local"}, "spans": spans}]}
        for svc, spans in groups
    ]}).encode()


AGENT = ("support-agent", [
    span("01", "propose_action", action__id="P1"),
    span("02", "execute_tool create_ticket", action__id="P1", tool__name="create_ticket"),
])


def receipt(sid, rid="R-1", action="P1", ticket="T-1042", **extra):
    return span(sid, "ticket.create.receipt", receipt__id=rid, receipt__action_id=action, receipt__ticket_id=ticket, **extra)


def entries(raw, member="in.json"):
    report, run = read([(member, raw)], MAPPING)
    return report, run


def body(report):
    return json.dumps([{k: v for k, v in e.items() if k != "basis"} for e in report["entries"]], sort_keys=True)


def effect_entries(report):
    return [e for e in report["entries"] if e["question"] == "effects"]


class ParsingContract(unittest.TestCase):
    """C16: never a clean report on a malformed input."""

    def assertFails(self, raw):
        report, run = entries(raw)
        self.assertEqual(run["processing"]["status"], "failed")
        self.assertEqual(report["entries"], [])

    def test_duplicate_key(self):
        self.assertFails(b'{"resourceSpans": [], "resourceSpans": []}')

    def test_nan(self):
        self.assertFails(b'{"resourceSpans": [], "x": NaN}')

    def test_bom(self):
        self.assertFails(b"\xef\xbb\xbf" + export(AGENT))

    def test_invalid_utf8(self):
        self.assertFails(b'{"resourceSpans": [], "x": "\xff"}')

    def test_depth_over_cap(self):
        self.assertFails(b'{"resourceSpans": [], "x": ' + b"[" * 100 + b"]" * 100 + b"}")

    def test_size_over_cap(self):
        old = parse.MAX_INPUT_BYTES
        parse.MAX_INPUT_BYTES = 10
        try:
            self.assertFails(export(AGENT))
        finally:
            parse.MAX_INPUT_BYTES = old

    def test_duplicate_attribute_key(self):
        raw = export(("support-agent", [span("01", "propose_action", action__id="P1")])).replace(
            b'"attributes": [{"key": "action.id"', b'"attributes": [{"key": "action.id", "value": {"stringValue": "P2"}}, {"key": "action.id"', 1)
        self.assertIn(b'"P2"', raw)
        self.assertFails(raw)

    def test_typed_values_stay_distinct(self):
        # Python's == says 1 == 1.0 == True; the parse boundary must not.
        self.assertNotEqual(parse.typed(1), parse.typed(1.0))
        self.assertNotEqual(parse.typed(1), parse.typed(True))
        self.assertNotEqual(parse.otlp_value({"intValue": "1"}), parse.otlp_value({"stringValue": "1"}))


class Effects(unittest.TestCase):
    def test_c1_receipt_delivered_twice(self):
        report, _ = entries(export(AGENT, ("test-ticket-service", [receipt("a1"), receipt("a2")])))
        (e,) = effect_entries(report)
        self.assertEqual(e["status"], "established")
        self.assertEqual(e["answer"]["effects"], [{"count": 1, "deliveries": 2, "effect": ["test-ticket-service", "external_effect", "R-1"]}])

    def test_c2_receipt_removed(self):
        report, _ = entries(export(AGENT))
        (e,) = effect_entries(report)
        self.assertEqual(e["status"], "unknown")
        self.assertEqual(e["answer"], {"effects": [], "execution": "established"})

    def test_c4_same_receipt_id_in_second_service(self):
        second = ("other-ticket-service", [receipt("b1")])
        report, _ = entries(export(AGENT, ("test-ticket-service", [receipt("a1")]), second))
        effects = effect_entries(report)
        loose = [e for e in effects if e["subject"][1] == "external_effect"]
        # Both receipts carry receipt.id R-1, but in two scopes: two effects, no
        # merge, no dedup (contract line 181). Both correlate to the execution
        # because the mapping declares the correlation key's scope as support-agent.
        views = [v for e in effects for v in e["answer"]["effects"]]
        self.assertEqual(sorted(tuple(v["effect"]) for v in views), [
            ("other-ticket-service", "external_effect", "R-1"),
            ("test-ticket-service", "external_effect", "R-1"),
        ])
        self.assertTrue(all(v["count"] == 1 and v["deliveries"] == 1 for v in views))
        self.assertEqual(loose, [])

    def test_c10_two_receipts_same_key_different_content(self):
        report, _ = entries(export(AGENT, ("test-ticket-service", [receipt("a1"), receipt("a2", ticket="T-9")])))
        (e,) = effect_entries(report)
        self.assertEqual(e["status"], "conflict")
        self.assertEqual(e["answer"]["effects"][0]["count"], "conflict")

    def test_c10_int_against_float_is_a_conflict(self):
        # m5: a reader comparing with Python == would call these equal.
        report, _ = entries(export(AGENT, ("test-ticket-service", [receipt("a1", n=1), receipt("a2", n=1.0)])))
        (e,) = effect_entries(report)
        self.assertEqual(e["answer"]["effects"][0]["count"], "conflict")

    def test_c11_receipt_without_execution(self):
        report, _ = entries(export(("support-agent", [span("01", "propose_action", action__id="P1")]),
                                   ("test-ticket-service", [receipt("a1")])))
        (e,) = effect_entries(report)
        self.assertEqual(e["subject"], ["test-ticket-service", "external_effect", "R-1"])
        self.assertEqual(e["answer"]["correlation"], "unresolved")
        self.assertEqual(e["status"], "established")

    def test_c17_unknown_record_kind(self):
        base, _ = entries(export(AGENT))
        extra, _ = entries(export(AGENT, ("support-agent", [span("09", "mystery_span", x="y")])))
        self.assertEqual(body(base), body(extra))
        self.assertEqual(extra["unplaced_losses"], ["unknown record kind 'mystery_span'"])

    def test_signature_is_not_evaluated(self):
        # Contract v0.7 line 112: a receipt is correlation evidence, not
        # cryptographic attestation. Two receipts differing only in their
        # signature correlate the same way; the field surfaces as a loss.
        a, _ = entries(export(AGENT, ("test-ticket-service", [receipt("a1", receipt__signature="good")])))
        b, _ = entries(export(AGENT, ("test-ticket-service", [receipt("a1", receipt__signature="bad")])))
        self.assertEqual(body(a), body(b))
        losses = [l[1] for l in effect_entries(a)[0]["losses"]]
        self.assertIn("attribute 'receipt.signature' has no placement in the mapping", losses)


def shuffled(raw, rng):
    doc = json.loads(raw)
    for rs in doc["resourceSpans"]:
        for ss in rs["scopeSpans"]:
            rng.shuffle(ss["spans"])
    rng.shuffle(doc["resourceSpans"])
    return json.dumps(doc).encode()


@unittest.skipUnless(KIT.is_dir(), "run scripts/fetch_kit.sh first")
class Invariance(unittest.TestCase):
    """C7 to C9 on the kit's records: the report body ignores order and names."""

    def kit(self):
        return sorted(KIT.iterdir())

    def test_c7_c8_permutations(self):
        for case in self.kit():
            raw = (case / "records.otlp.json").read_bytes()
            want = body(entries(raw)[0])
            rng = random.Random(42)
            for _ in range(200):
                self.assertEqual(body(entries(shuffled(raw, rng))[0]), want, case.name)

    def test_c9_renamed(self):
        for case in self.kit():
            raw = (case / "records.otlp.json").read_bytes()
            renamed = hashlib.sha256(case.name.encode()).hexdigest() + ".json"
            self.assertEqual(body(entries(raw, "records.otlp.json")[0]), body(entries(raw, renamed)[0]))

    def test_split_across_files(self):
        # IC-1: one set, however many files carry it.
        whole = export(AGENT, ("test-ticket-service", [receipt("a1")]))
        a = export(AGENT)
        b = export(("test-ticket-service", [receipt("a1")]))
        one, _ = read([("x.json", whole)], MAPPING)
        two, _ = read([("b.json", b), ("a.json", a)], MAPPING)
        self.assertEqual(body(one), body(two))


class IndependenceBoundary(unittest.TestCase):
    """DESIGN.md section 2: the reader cannot reach the comparator or an expected answer."""

    def test_reader_imports(self):
        for path in (ROOT / "aaif_reader").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    names = []
                for n in names:
                    self.assertFalse(n.startswith("aaif_compare"), path.name)
                    self.assertNotEqual(n, "importlib", path.name)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    # A path to an expected-answer file would have to be spelled somewhere.
                    for needle in ("expected.json", "inputs/expected"):
                        self.assertNotIn(needle, node.value, f"{path.name}: {node.value!r}")


if __name__ == "__main__":
    unittest.main()
