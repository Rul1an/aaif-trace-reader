"""Acceptance cases C3 to C18 on LOCAL records (DESIGN.md section 8).

Every record here is authored by this reader's own tests through
mappings/local-v1.json; none is a WG fixture, and no expected-answer file is
read. Each degraded case sits next to its positive twin where section 8 names
one.
"""

from __future__ import annotations

import itertools
import json
import random
import unittest
from pathlib import Path

from aaif_reader.cli import read

ROOT = Path(__file__).resolve().parent.parent
LOCAL = json.loads((ROOT / "mappings" / "local-v1.json").read_text(encoding="utf-8"))


def mapping(**changes):
    m = json.loads(json.dumps(LOCAL))
    for key, value in changes.items():
        m[key] = value
    return json.dumps(m).encode()


MAP = mapping()


def attr(k, v):
    if isinstance(v, bool):
        return {"key": k, "value": {"boolValue": v}}
    if isinstance(v, int):
        return {"key": k, "value": {"intValue": str(v)}}
    if isinstance(v, float):
        return {"key": k, "value": {"doubleValue": v}}
    return {"key": k, "value": {"stringValue": v}}


_ids = itertools.count(1)


def span(name, trace="a" * 32, **attrs):
    return {"traceId": trace, "spanId": f"{next(_ids):016x}", "parentSpanId": "", "name": name,
            "startTimeUnixNano": "1", "endTimeUnixNano": "2",
            "attributes": [attr(k.replace("__", "."), v) for k, v in attrs.items()]}


def export(*spans, service="agent"):
    return json.dumps({"resourceSpans": [
        {"resource": {"attributes": [attr("service.name", service)]}, "scopeSpans": [{"scope": {"name": "local"}, "spans": list(spans)}]}
    ]}).encode()


def run(*raws, mapping_raw=MAP):
    report, run_ = read([(f"in{i}.json", raw) for i, raw in enumerate(raws)], mapping_raw)
    assert run_["processing"]["status"] == "complete", run_
    return report


def entry(report, question, native_id):
    found = [e for e in report["entries"] if e["question"] == question and e["subject"][2] == native_id]
    assert len(found) == 1, (question, native_id, [e["subject"] for e in report["entries"]])
    return found[0]


def body(report):
    return json.dumps([{k: v for k, v in e.items() if k != "basis"} for e in report["entries"]], sort_keys=True)


def shuffled(raw, rng):
    doc = json.loads(raw)
    for rs in doc["resourceSpans"]:
        for ss in rs["scopeSpans"]:
            rng.shuffle(ss["spans"])
    return json.dumps(doc).encode()


TURN = span("invoke_agent", turn__id="T2", conversation__id="C1")
PROPOSAL = span("propose_action", action__id="P1", turn__id="T2")


def decision(did, outcome, policy="p", time="t", proposal="P1"):
    return span("approval", decision__id=did, decision__proposal_id=proposal, decision__outcome=outcome,
                decision__policy=policy, decision__time=time)


def execution(eid="E1", followed=None, action="P1"):
    kw = {"execution__id": eid, "action__id": action, "tool__name": "create_ticket"}
    if followed:
        kw["execution__decision_id"] = followed
    return span("execute_tool create_ticket", **kw)


class Calls(unittest.TestCase):
    def call(self, *records):
        return entry(run(export(TURN, *records)), "calls", "T2")["answer"]["calls"]

    def test_c3_failure_exported_success_missing(self):
        (c,) = self.call(span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="failure", usage__attempt__tokens=10))
        self.assertEqual(c["call"], ["agent", "model_call", "M2"])
        self.assertEqual(c["outcome"], "unknown")
        self.assertEqual(c["usage"]["status"], "unknown")

    def test_c3_twin_success_exported(self):
        (c,) = self.call(span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="failure"),
                         span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="success", usage__call__tokens=22))
        self.assertEqual(c["outcome"], "succeeded")
        self.assertEqual(c["usage"], {"status": "established", "value": 22, "levels": {"call": [22]}})

    def test_ic6_attempts_are_one_call(self):
        calls = self.call(span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="failure"),
                          span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="success"))
        self.assertEqual(len(calls), 1)

    def test_c5_two_levels_without_declared_aggregation(self):
        (c,) = self.call(span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="failure", usage__attempt__tokens=10),
                         span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="success", usage__attempt__tokens=12, usage__call__tokens=22))
        self.assertEqual(c["usage"]["status"], "unknown")
        self.assertEqual(c["usage"]["levels"], {"attempt": [10, 12], "call": [22]})
        self.assertNotIn("value", c["usage"])

    def test_c18_counter_as_float_or_string(self):
        for bad in (22.0, "22"):
            report = run(export(TURN, span("chat model", call__id="M2", turn__id="T2", call__attempt__outcome="success", usage__call__tokens=bad)))
            e = entry(report, "calls", "T2")
            (c,) = e["answer"]["calls"]
            self.assertEqual(c["usage"]["status"], "unknown", bad)
            self.assertEqual(c["usage"]["levels"], {"call": ["unknown"]}, bad)
            self.assertTrue(any("usage counter 'usage.call.tokens'" in l[1] for l in e["losses"]), bad)

    def test_no_call_exported_is_unknown_not_zero(self):
        e = entry(run(export(TURN)), "calls", "T2")
        self.assertEqual(e["status"], "unknown")
        self.assertEqual(e["answer"]["calls"], [])


class Approvals(unittest.TestCase):
    def ap(self, *records):
        return entry(run(export(PROPOSAL, *records)), "approvals", "P1")

    def test_c6_execution_references_the_denial_it_followed(self):
        e = self.ap(decision("A1", "denied"), execution(followed="A1"))
        self.assertEqual(e["relations"], [{"execution": ["agent", "tool_execution", "E1"], "followed": ["agent", "approval_decision", "A1"], "finding": "inconsistent_with_decision"}])
        self.assertEqual((e["enforcement"], e["executed"]), ("unknown", "established"))
        self.assertNotIn("applicability", e)
        self.assertEqual(e["answer"]["executions"], [["agent", "tool_execution", "E1"]])

    def test_c6a_no_decision_recorded(self):
        e = self.ap(execution())
        self.assertEqual(e["relations"], [{"execution": ["agent", "tool_execution", "E1"], "decision": "unknown"}])
        self.assertEqual(e["decision_count"], 0)
        self.assertNotIn("applicability", e)
        self.assertEqual(e["enforcement"], "unknown")

    def test_c6b_only_denial_and_no_reference(self):
        e = self.ap(decision("A1", "denied"), execution())
        self.assertEqual(e.get("applicability"), "unresolved")
        self.assertEqual(e["relations"], [{"execution": ["agent", "tool_execution", "E1"], "finding": "unresolved"}])
        self.assertEqual(e["decisions_recorded"], [{"decision": ["agent", "approval_decision", "A1"], "outcome": "denied"}])
        self.assertEqual(e["enforcement"], "unknown")

    def test_c14_denial_and_approval_no_execution(self):
        e = self.ap(decision("A1", "denied", time="2"), decision("A2", "approved", time="1"))
        self.assertEqual((e["status"], e["decision_count"], e.get("applicability")), ("established", 2, "unresolved"))
        self.assertEqual(e["conflicts"], [])
        self.assertEqual((e["enforcement"], e["executed"]), ("unknown", "unknown"))
        self.assertEqual(sorted(d["outcome"] for d in e["decisions_recorded"]), ["approved", "denied"])

    def test_c14_twin_single_decision(self):
        e = self.ap(decision("A2", "approved"))
        self.assertEqual(e["decision_count"], 1)
        self.assertNotIn("applicability", e)

    def test_c14a_two_approvals_from_two_policies(self):
        e = self.ap(decision("A1", "approved", policy="x", time="2"), decision("A2", "approved", policy="y", time="1"))
        self.assertEqual((e["status"], e["decision_count"], e.get("applicability")), ("established", 2, "unresolved"))
        self.assertEqual(e["conflicts"], [])
        self.assertEqual([d["outcome"] for d in e["decisions_recorded"]], ["approved", "approved"])

    def test_c14b_denial_approval_and_unreferenced_execution(self):
        e = self.ap(decision("A1", "denied"), decision("A2", "approved"), execution())
        self.assertEqual(e.get("applicability"), "unresolved")
        self.assertEqual(e["relations"], [{"execution": ["agent", "tool_execution", "E1"], "finding": "unresolved"}])
        self.assertEqual(sorted(d["outcome"] for d in e["decisions_recorded"]), ["approved", "denied"])
        self.assertEqual(e["enforcement"], "unknown")

    def test_c14b_twin_execution_references_the_approval(self):
        e = self.ap(decision("A2", "approved"), execution(followed="A2"))
        self.assertEqual(e["relations"][0]["finding"], "consistent")
        self.assertNotIn("applicability", e)

    def test_c14c_two_approvals_and_unreferenced_execution(self):
        e = self.ap(decision("A1", "approved", policy="x"), decision("A2", "approved", policy="y"), execution())
        self.assertEqual(e.get("applicability"), "unresolved")
        self.assertEqual([d["outcome"] for d in e["decisions_recorded"]], ["approved", "approved"])
        self.assertEqual(e["relations"], [{"execution": ["agent", "tool_execution", "E1"], "finding": "unresolved"}])

    def test_c14c_twin_execution_references_one_approval(self):
        e = self.ap(decision("A1", "approved", policy="x"), execution(followed="A1"))
        self.assertEqual(e["relations"][0]["finding"], "consistent")

    def test_reference_to_one_of_several_decisions(self):
        # Revision 6: the per-execution finding follows the reference, and the
        # entry keeps applicability unresolved (this reader's reading of line 104).
        e = self.ap(decision("A1", "denied"), decision("A2", "approved"), execution(followed="A1"))
        self.assertEqual(e["relations"][0]["finding"], "inconsistent_with_decision")
        self.assertEqual(e.get("applicability"), "unresolved")

    def test_ic8_same_key_equal_content_is_one_decision(self):
        e = self.ap(decision("A1", "denied"), decision("A1", "denied"))
        self.assertEqual((e["decision_count"], e["conflicts"]), (1, []))

    def test_ic8_same_key_different_content_is_a_conflict(self):
        e = self.ap(decision("A1", "denied"), decision("A1", "approved"))
        self.assertEqual(e["decision_count"], 1)
        self.assertEqual(e["conflicts"], [["agent", "approval_decision", "A1"]])
        self.assertEqual(e["decisions_recorded"][0]["outcome"], "conflict")

    def test_approvals_invariant_under_shuffle(self):
        raw = export(PROPOSAL, decision("A1", "denied", time="2"), decision("A2", "approved", time="1"),
                     execution("E1"), execution("E2", followed="A2"))
        want = body(run(raw))
        rng = random.Random(11)
        for _ in range(200):
            self.assertEqual(body(run(shuffled(raw, rng))), want)


class Continuity(unittest.TestCase):
    def test_c12_turn_without_conversation_identity(self):
        report = run(export(span("invoke_agent", turn__id="T9")))
        e = entry(report, "continuity", "T9")
        self.assertEqual((e["status"], e["answer"]), ("unknown", {"membership": "unknown"}))
        self.assertFalse([x for x in report["entries"] if x["subject"][1] == "conversation"])

    def test_c13_resumed_in_new_session_and_trace(self):
        report = run(export(span("invoke_agent", trace="a" * 32, turn__id="T1", conversation__id="C1", session__id="S1"),
                            span("invoke_agent", trace="b" * 32, turn__id="T3", conversation__id="C1", session__id="S2")))
        e = entry(report, "continuity", "C1")
        self.assertEqual([t[2] for t in e["answer"]["turns"]], ["T1", "T3"])
        self.assertEqual((e["answer"]["state"], e["answer"]["order"]), ("not_answered", "not_answered"))


def rel(method=None, source="T1", target="C1", kind="R1"):
    kw = {"rel__kind": kind, "rel__source_kind": "turn", "rel__source_id": source,
          "rel__target_kind": "conversation", "rel__target_id": target}
    if method is not None:
        kw["rel__method"] = method
    return span("relationship", **kw)


BARE_TURN = span("invoke_agent", turn__id="T1")
NO_R1_DEFAULT = mapping(default_methods={k: v for k, v in LOCAL["default_methods"].items() if k != "R1"})


class Relationships(unittest.TestCase):
    def test_c15_no_method_and_no_default(self):
        report = run(export(BARE_TURN, rel()), mapping_raw=NO_R1_DEFAULT)
        e = entry(report, "continuity", "T1")
        self.assertEqual(e["status"], "unknown")
        self.assertTrue(any("no method on the record and no mapping default" in l[1] for l in e["losses"]))

    def test_c15a_no_method_with_default(self):
        e = entry(run(export(BARE_TURN, rel())), "continuity", "C1")
        self.assertEqual(e["answer"]["memberships"], [{"turn": ["agent", "turn", "T1"], "methods": ["attribute-reference"], "deliveries": 1}])

    def test_c15b_unrecognized_method_with_default(self):
        report = run(export(BARE_TURN, rel("carrier-pigeon")))
        e = entry(report, "continuity", "T1")
        self.assertEqual(e["status"], "unknown")
        self.assertTrue(any("'carrier-pigeon'" in l[1] for l in e["losses"]))

    def test_c15c_span_link_and_attribute_reference(self):
        report = run(export(span("invoke_agent", turn__id="T1", conversation__id="C1"), rel("span-link")))
        e = entry(report, "continuity", "C1")
        self.assertEqual(e["answer"]["memberships"], [{"turn": ["agent", "turn", "T1"], "methods": ["attribute-reference", "span-link"], "deliveries": 2}])
        self.assertEqual(e["conflicts"], [])

    def test_c15d_same_relationship_twice_same_method(self):
        e = entry(run(export(BARE_TURN, rel("span-link"), rel("span-link"))), "continuity", "C1")
        self.assertEqual(e["answer"]["memberships"], [{"turn": ["agent", "turn", "T1"], "methods": ["span-link"], "deliveries": 2}])


def section_10_example(suffix=""):
    """The contract's section 10 fixture example, as local records."""
    s = suffix
    return [
        span("invoke_agent", trace="a" * 32, turn__id=f"T1{s}", conversation__id=f"C1{s}"),
        span("invoke_agent", trace="b" * 32, turn__id=f"T2{s}", conversation__id=f"C1{s}"),
        span("chat model", call__id=f"M1{s}", turn__id=f"T1{s}", call__attempt__outcome="success", usage__call__tokens=5),
        span("chat model", call__id=f"M2{s}", turn__id=f"T2{s}", call__attempt__outcome="failure", usage__attempt__tokens=3),
        span("chat model", call__id=f"M2{s}", turn__id=f"T2{s}", call__attempt__outcome="success", usage__call__tokens=9),
        span("propose_action", action__id=f"P1{s}", turn__id=f"T2{s}"),
        span("approval", decision__id=f"A1{s}", decision__proposal_id=f"P1{s}", decision__outcome="approved"),
        span("execute_tool create_ticket", execution__id=f"E1{s}", action__id=f"P1{s}", execution__decision_id=f"A1{s}", ticket__id=f"42{s}"),
        span("invoke_agent", trace="c" * 32, turn__id=f"T3{s}", conversation__id=f"C1{s}"),
    ]


RECEIPT = lambda s="": span("ticket.create.receipt", receipt__id=f"R{s}", receipt__ticket_id=f"42{s}")


def two_services(spans, receipts):
    return json.dumps({"resourceSpans": [
        {"resource": {"attributes": [attr("service.name", "agent")]}, "scopeSpans": [{"scope": {"name": "local"}, "spans": spans}]},
        {"resource": {"attributes": [attr("service.name", "ticket-service")]}, "scopeSpans": [{"scope": {"name": "local"}, "spans": receipts}]},
    ]}).encode()


class OrderInvariance(unittest.TestCase):
    def test_c7_section_10_example(self):
        spans = section_10_example()
        want = body(run(two_services(spans, [RECEIPT()])))
        # Nine agent records plus the receipt: over the exhaustive limit of
        # section 8 (under nine), so seeded shuffles.
        rng = random.Random(3)
        for _ in range(300):
            s = spans[:]
            rng.shuffle(s)
            self.assertEqual(body(run(two_services(s, [RECEIPT()]))), want)
        e = entry(run(two_services(spans, [RECEIPT()])), "effects", "E1")
        self.assertEqual(e["answer"]["effects"][0]["effect"], ["ticket-service", "external_effect", "R"])

    def test_c8_fifty_records(self):
        spans, receipts = [], []
        for i in range(5):
            spans += section_10_example(f"-{i}")
            receipts.append(RECEIPT(f"-{i}"))
        self.assertEqual(len(spans) + len(receipts), 50)
        want = body(run(two_services(spans, receipts)))
        rng = random.Random(8)
        for _ in range(200):
            s, r = spans[:], receipts[:]
            rng.shuffle(s)
            rng.shuffle(r)
            self.assertEqual(body(run(two_services(s, r))), want)


if __name__ == "__main__":
    unittest.main()
