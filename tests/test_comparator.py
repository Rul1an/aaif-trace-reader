"""DESIGN.md section 7 (revision 8): the comparator, tested before it exists.

Synthetic inputs only; no kit expected-answer file is read here.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from aaif_compare.compare import ControlFailed, compare

ROOT = Path(__file__).resolve().parent.parent
PROJECTION = json.loads((ROOT / "projections" / "kit-b658795.json").read_text())
KIT = "b6587950986eb4ec501e080cc9730fd21dcb69fa"


def report(status="established", tickets=("T-1",), action="P1", processing="complete"):
    return {"processing": processing,
            "query": {"context": {"action": action, "service": "s", "tenant": None}, "status": status,
                      "execution": "established", "ticket_ids": list(tickets) if tickets is not None else None,
                      "effects": []}}


class Comparator(unittest.TestCase):
    def setUp(self):
        self.reports = {"c-confirmed": report(), "c-missing": report("unknown", None),
                        "c-signed": report()}
        self.signatures = {"c-signed": [{"case": "c-signed", "signature_valid": True}]}
        self.expected = {"c-confirmed": {"action": "P1", "effect": "confirmed", "confirmed_tickets": ["T-1"]},
                         "c-missing": {"action": "P1", "effect": "unconfirmed", "confirmed_tickets": None},
                         "c-signed": {"action": "P1", "effect": "confirmed", "confirmed_tickets": ["T-1"],
                                      "receipt_signature_verified": True}}
        self.other = [{"revision": KIT, "case": c, "fields": [{"field": k, "actual": v} for k, v in e.items()]}
                      for c, e in self.expected.items()]

    def run_cmp(self, reports=None, expected=None, other=None, projection=None, signatures=None):
        return compare(reports or self.reports, signatures if signatures is not None else self.signatures,
                       expected or self.expected, projection or PROJECTION, other if other is not None else self.other, KIT)

    def test_all_match_when_everything_agrees(self):
        r = self.run_cmp()
        self.assertTrue(all(c["all_fields_match"] for c in r["vs_expected"]["cases"]))
        self.assertTrue(all(c["all_fields_agree"] for c in r["vs_other_reader"]["cases"]))

    def test_a_reader_cannot_pass_by_silence(self):
        reports = copy.deepcopy(self.reports)
        del reports["c-confirmed"]["query"]["ticket_ids"]
        case = {c["case"]: c for c in self.run_cmp(reports=reports)["vs_expected"]["cases"]}["c-confirmed"]
        field = {f["field"]: f for f in case["fields"]}["confirmed_tickets"]
        self.assertFalse(field["match"])
        self.assertEqual(field["reason"], "absent from the report")

    def test_a_missing_case_fails_every_field(self):
        reports = copy.deepcopy(self.reports)
        del reports["c-confirmed"]
        case = {c["case"]: c for c in self.run_cmp(reports=reports)["vs_expected"]["cases"]}["c-confirmed"]
        self.assertFalse(case["all_fields_match"])
        self.assertTrue(all(f["reason"] == "case absent from the run" for f in case["fields"]))
        self.assertFalse(any(f["match"] for f in case["fields"]))

    def test_not_evaluated_fails(self):
        reports = copy.deepcopy(self.reports)
        reports["c-confirmed"]["processing"] = "not_evaluated"
        case = {c["case"]: c for c in self.run_cmp(reports=reports)["vs_expected"]["cases"]}["c-confirmed"]
        self.assertFalse(case["all_fields_match"])

    def test_all_unknown_control_runs_and_fails_positive_cases(self):
        control = self.run_cmp()["controls"]["all_unknown"]
        self.assertEqual(control["result"], "failed every positive case, as required")
        self.assertEqual(sorted(control["positive_cases"]), ["c-confirmed", "c-signed"])

    def test_a_projection_that_lets_unknown_pass_aborts_the_comparison(self):
        projection = copy.deepcopy(PROJECTION)
        projection["fields"]["effect"]["map"]["unknown"] = "confirmed"
        projection["fields"]["confirmed_tickets"] = {"from": "constant", "value": ["T-1"]}
        with self.assertRaises(ControlFailed):
            self.run_cmp(projection=projection, signatures={"c-signed": []},
                         expected={k: v for k, v in self.expected.items() if k != "c-signed"})

    def test_an_unexpected_reported_field_is_a_disagreement_not_dropped(self):
        expected = copy.deepcopy(self.expected)
        del expected["c-signed"]["receipt_signature_verified"]
        case = {c["case"]: c for c in self.run_cmp(expected=expected)["vs_expected"]["cases"]}["c-signed"]
        self.assertEqual(case["reported_not_expected"], [{"field": "receipt_signature_verified", "actual": True}])

    def test_by_construction_field_is_counted_apart(self):
        summary = self.run_cmp()["vs_expected"]["summary"]
        self.assertEqual(summary["by_construction_fields_matched"], 3)
        self.assertEqual(summary["fields_matched"], 7)

    def test_by_construction_is_counted_apart_against_the_other_reader_too(self):
        summary = self.run_cmp()["vs_other_reader"]["summary"]
        self.assertEqual(summary["by_construction_fields_agree"], 3)
        self.assertEqual(summary["fields_agree"], 7)

    def test_the_two_tables_are_never_merged(self):
        other = copy.deepcopy(self.other)
        other[0]["fields"][2]["actual"] = ["T-9"]
        r = self.run_cmp(other=other)
        self.assertTrue(all(c["all_fields_match"] for c in r["vs_expected"]["cases"]))
        self.assertFalse(all(c["all_fields_agree"] for c in r["vs_other_reader"]["cases"]))
        self.assertNotIn("score", r)

    def test_other_reader_rows_at_another_revision_are_ignored(self):
        other = copy.deepcopy(self.other)
        for row in other:
            row["revision"] = "4a028675ef9b5727e614762df305f5f037b04b98"
        cases = self.run_cmp(other=other)["vs_other_reader"]["cases"]
        self.assertTrue(all(c.get("other_reader") == "no row at this kit revision" for c in cases))

    def test_a_signature_row_without_a_verdict_does_not_match(self):
        signatures = {"c-signed": [{"case": "c-signed", "signature_check": "malformed_signature", "signature_valid": None}]}
        case = {c["case"]: c for c in self.run_cmp(signatures=signatures)["vs_expected"]["cases"]}["c-signed"]
        field = {f["field"]: f for f in case["fields"]}["receipt_signature_verified"]
        self.assertFalse(field["match"])


if __name__ == "__main__":
    unittest.main()
