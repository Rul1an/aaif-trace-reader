"""The kit-declared mapping at b6587950: tenant-qualified scope, ticket ids, and
the evaluation_context query.

Written before the implementation. Local records only; no kit expected-answer
file is read. The regression test reruns the frozen 4a028675ef reports, which
were frozen by this reader before any expected answer at that revision was read.
"""
import json
import unittest
from pathlib import Path

from aaif_reader.cli import read
from aaif_reader.model import canon
from tests.test_reader import attr, span

ROOT = Path(__file__).resolve().parent.parent
MAPPING = (ROOT / "mappings" / "test-kit-b658795.json").read_bytes()
ISSUE42 = "https://github.com/aaif/wg-observability-and-traceability/issues/42"
CONTRACT_URL = "https://github.com/aaif/wg-observability-and-traceability/blob/e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md"


def export(*groups):
    """groups: (service, tenant or None, spans)."""
    def res(svc, tenant):
        a = [attr("service.name", svc)]
        if tenant is not None:
            a.append(attr("tenant.id", tenant))
        return {"attributes": a}
    return json.dumps({"resourceSpans": [
        {"resource": res(svc, tenant), "scopeSpans": [{"scope": {"name": "local"}, "spans": spans}]}
        for svc, tenant, spans in groups
    ]}).encode()


def agent(tenant, base="0"):
    return ("support-agent", tenant, [
        span(base + "1", "propose_action", action__id="P1"),
        span(base + "2", "execute_tool create_ticket", action__id="P1", tool__name="create_ticket"),
    ])


def receipt(sid, ticket, rid="R-9"):
    return span(sid, "ticket.create.receipt", receipt__id=rid, receipt__action_id="P1",
                receipt__ticket_id=ticket, receipt__service="test-ticket-service")


def basis(tenant):
    return json.dumps({"answer_follows": {"url": CONTRACT_URL}, "checks": ["effect_correlation"],
                       "evaluation_context": {"action": "P1", "service": "test-ticket-service", "tenant": tenant}}).encode()


def query(raw, tenant):
    report, _ = read([("in.json", raw)], MAPPING, basis_raw=basis(tenant))
    return report["query"]


TWO_TENANTS = export(agent("tenant-a", "1"), ("test-ticket-service", "tenant-a", [receipt("13", "T-1042")]),
                     agent("tenant-b", "2"), ("test-ticket-service", "tenant-b", [receipt("23", "T-2088")]))


class TenantScope(unittest.TestCase):
    def test_queried_tenant_confirms_only_its_own_ticket(self):
        q = query(TWO_TENANTS, "tenant-a")
        self.assertEqual(q["status"], "established")
        self.assertEqual(q["ticket_ids"], ["T-1042"])
        self.assertEqual([e["effect"] for e in q["effects"]], [["test-ticket-service@tenant-a", "external_effect", "R-9"]])

    def test_other_tenant_answers_its_own(self):
        self.assertEqual(query(TWO_TENANTS, "tenant-b")["ticket_ids"], ["T-2088"])

    def test_receipt_in_another_tenant_does_not_join(self):
        raw = export(agent("tenant-a"), ("test-ticket-service", "tenant-b", [receipt("03", "T-2088")]))
        q = query(raw, "tenant-a")
        self.assertEqual(q["status"], "unknown")
        self.assertIsNone(q["ticket_ids"])
        self.assertEqual(q["effects"], [])

    def test_same_receipt_key_in_two_tenants_is_two_effects_not_a_conflict(self):
        report, _ = read([("in.json", TWO_TENANTS)], MAPPING)
        effects = [e for e in report["entries"] if e["question"] == "effects" and e["subject"][0] == "KEYLESS"]
        self.assertEqual(len(effects), 2)
        self.assertTrue(all(e["status"] == "established" for e in effects))

    def test_query_keeps_the_tenant_even_when_the_mapping_joins_across_it(self):
        # A mapping whose receipt key ignores the tenant lets R6 join both
        # receipts to both executions; the query must still answer only from
        # the queried tenant's receipts.
        m = json.loads(MAPPING)
        for e in m["entities"]:
            for c in e.get("correlation_keys", []):
                c["key_scope"] = {"declared": "support-agent"}
        report, _ = read([("in.json", TWO_TENANTS)], json.dumps(m).encode(), basis_raw=basis("tenant-a"))
        joined = [e for e in report["entries"] if e["question"] == "effects" and e["subject"][0] == "KEYLESS"]
        self.assertEqual({len(e["answer"]["effects"]) for e in joined}, {2})  # the premise: R6 crosses tenants here
        self.assertEqual(report["query"]["ticket_ids"], ["T-1042"])

    def test_separator_in_scope_is_unreadable(self):
        raw = export(("support@agent", None, [span("01", "propose_action", action__id="P1")]))
        report, _ = read([("in.json", raw)], MAPPING)
        self.assertTrue(any("scope not readable" in l[1] for e in report["entries"] for l in e["losses"]))


class TicketIds(unittest.TestCase):
    def test_ticket_id_is_reported_not_only_counted(self):
        raw = export(agent(None), ("test-ticket-service", None, [receipt("03", "T-2088")]))
        q = query(raw, None)
        self.assertEqual(q["status"], "established")
        self.assertEqual(q["ticket_ids"], ["T-2088"])
        self.assertEqual(q["effects"][0]["effect"], ["test-ticket-service", "external_effect", "R-9"])

    def test_missing_receipt_is_unknown_not_absent(self):
        q = query(export(agent(None)), None)
        self.assertEqual(q["status"], "unknown")
        self.assertEqual(q["execution"], "established")
        self.assertIsNone(q["ticket_ids"])  # F5: unknown, not an empty list

    def test_conflicting_ticket_ids_on_one_receipt_are_kept(self):
        raw = export(agent(None), ("test-ticket-service", None, [receipt("03", "T-1042"), receipt("04", "T-2088")]))
        q = query(raw, None)
        self.assertEqual(q["status"], "conflict")
        self.assertEqual(q["ticket_ids"], ["T-1042", "T-2088"])

    def test_no_query_without_evaluation_context(self):
        raw = export(agent(None))
        report, _ = read([("in.json", raw)], MAPPING, basis_raw=json.dumps(
            {"answer_follows": {"url": CONTRACT_URL}, "checks": ["effect_correlation"]}).encode())
        self.assertNotIn("query", report)


class FrozenRegression(unittest.TestCase):
    """The frozen 4a028675ef reports reproduce byte for byte with their own mapping."""

    def test_4a02867_reports_unchanged(self):
        kit = ROOT / "inputs" / "test-kit-4a028675ef9b5727e614762df305f5f037b04b98" / "cases"
        mapping = (ROOT / "mappings" / "test-kit-4a02867.json").read_bytes()
        for case in sorted(p.name for p in kit.iterdir()):
            raw = (kit / case / "records.otlp.json").read_bytes()
            b = (kit / case / "basis.json").read_bytes()
            report, _ = read([("records.otlp.json", raw)], mapping, basis_raw=b)
            frozen = (ROOT / "results" / "4a02867" / case / "report.json").read_text()
            self.assertEqual(canon(report) + "\n", frozen, case)

    def _rerun(self, kit_sha, mapping, results):
        kit = ROOT / "inputs" / f"test-kit-{kit_sha}" / "cases"
        m = (ROOT / "mappings" / mapping).read_bytes()
        for case in sorted(p.name for p in kit.iterdir()):
            b = kit / case / "basis.json"
            report, _ = read([("records.otlp.json", (kit / case / "records.otlp.json").read_bytes())], m,
                             basis_raw=b.read_bytes() if b.exists() else None)
            yield case, report, (ROOT / "results" / results / case / "report.json").read_text()

    def test_afc26fdd_reports_unchanged(self):
        for case, report, frozen in self._rerun("afc26fdd2199844bf7dff23879739e941fa81107", "test-kit-afc26fdd.json", "afc26fdd"):
            self.assertEqual(canon(report) + "\n", frozen, case)

    def test_8fa732e_reports_unchanged_in_content(self):
        # These frozen files are written in another byte layout; they already
        # differed in bytes, not content, at 5036716, so content is what is pinned.
        for case, report, frozen in self._rerun("8fa732e3ec597e04a8b667c3669d3ac537e3e98a", "test-kit-8fa732e.json", "8fa732e"):
            self.assertEqual(report, json.loads(frozen), case)


if __name__ == "__main__":
    unittest.main()
