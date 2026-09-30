"""The kit-declared mapping at 4a028675ef: R6 only for the declared service.

Local records only; no kit expected-answer file is read.
"""
import unittest
from pathlib import Path

from aaif_reader.cli import read
from tests.test_reader import AGENT, export, receipt

MAPPING = (Path(__file__).resolve().parent.parent / "mappings" / "test-kit-4a02867.json").read_bytes()


def effects(raw):
    report, _ = read([("in.json", raw)], MAPPING)
    return [e for e in report["entries"] if e["question"] == "effects" and e["subject"][0] == "KEYLESS"]


class KitMapping(unittest.TestCase):
    def test_declared_service_receipt_correlates(self):
        (e,) = effects(export(AGENT, ("test-ticket-service", [receipt("03")])))
        self.assertEqual(e["status"], "established")
        self.assertEqual([x["effect"] for x in e["answer"]["effects"]], [["test-ticket-service", "external_effect", "R-1"]])

    def test_other_service_does_not_inherit_r6(self):
        (e,) = effects(export(AGENT, ("other-ticket-service", [receipt("03")])))
        self.assertEqual(e["answer"]["effects"], [])
        self.assertNotEqual(e["status"], "established")


if __name__ == "__main__":
    unittest.main()
