"""Regression tests for the independent review of 5036716..5e63b26 (2026-10-06).

Written before the fixes in the commit that adds them; local records only, no
kit expected-answer file is read.
"""
import json
import unittest
from pathlib import Path

from aaif_reader.cli import read
from tests.test_reader import attr, span
from tests import test_reader as tr
from tests.test_mapping_b658795 import MAPPING, basis, export, agent

ROOT = Path(__file__).resolve().parent.parent
OLD = (ROOT / "mappings" / "test-kit-4a02867.json").read_bytes()


def q(raw, tenant=None):
    return read([("in.json", raw)], MAPPING, basis_raw=basis(tenant))[0]["query"]


class Review(unittest.TestCase):
    def test_1_lookalike_service_does_not_inherit_r6_under_old_mapping(self):
        # No tenant_key in the 4a02867 mapping: '@' is part of the name, not a separator.
        raw = tr.export(tr.AGENT, ("test-ticket-service@evil", [tr.receipt("03")]))
        report, _ = read([("in.json", raw)], OLD)
        (ex,) = [e for e in report["entries"] if e["question"] == "effects" and e["subject"][0] == "KEYLESS"]
        self.assertEqual(ex["answer"]["effects"], [])

    def test_2_established_effect_without_ticket_id_is_not_an_empty_list(self):
        r = span("03", "ticket.create.receipt", receipt__id="R-9", receipt__action_id="P1",
                 receipt__service="test-ticket-service")
        out = q(export(agent(None), ("test-ticket-service", None, [r])))
        self.assertEqual(out["status"], "established")
        self.assertIsNone(out["ticket_ids"])
        self.assertIsNone(out["effects"][0]["ticket_ids"])

    def test_3_one_conflicting_effect_makes_the_answer_a_conflict(self):
        from tests.test_mapping_b658795 import receipt
        raw = export(agent(None), ("test-ticket-service", None,
                                   [receipt("03", "T-1", rid="R-1"), receipt("04", "T-2", rid="R-1"),
                                    receipt("05", "T-3", rid="R-2")]))
        self.assertEqual(q(raw)["status"], "conflict")

    def test_4_executions_are_those_of_the_declared_issuing_system(self):
        other = ("other-agent", None, [span("21", "propose_action", action__id="P1"),
                                       span("22", "execute_tool create_ticket", action__id="P1", tool__name="create_ticket")])
        out = q(export(agent(None), other))
        self.assertEqual(len(out["executions"]), 1)
        self.assertIn("support-agent", out["executions"][0][2])

    def test_4b_unresolved_scope_never_matches_a_tenantless_query(self):
        doc = {"resourceSpans": [{"resource": {"attributes": []}, "scopeSpans": [{"scope": {"name": "l"}, "spans": [
            span("01", "propose_action", action__id="P1"),
            span("02", "execute_tool create_ticket", action__id="P1", tool__name="create_ticket")]}]}]}
        # A mapping with no declared issuing system, so only the scope check
        # keeps an unresolved scope out of the answer.
        m = json.loads(MAPPING)
        for e in m["entities"]:
            for c in e.get("correlation_keys", []):
                c["key_scope"] = {"same_as_source": True}
        out = read([("in.json", json.dumps(doc).encode())], json.dumps(m).encode(), basis_raw=basis(None))[0]["query"]
        self.assertEqual(out["executions"], [])
        self.assertEqual(out["execution"], "unknown")


if __name__ == "__main__":
    unittest.main()
