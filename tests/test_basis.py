import json
import unittest
from aaif_reader.cli import read
from tests.test_reader import MAPPING, export, AGENT, receipt

CONTRACT_URL = 'https://github.com/aaif/wg-observability-and-traceability/blob/e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md'
PAIR_URL = 'https://github.com/aaif/wg-observability-and-traceability/blob/41e6eacc2fc6bf783f45d873c3d01eb7dd0f9560/working-documents/agent-mcp-server-boundary-deep-dive.md'

class BasisTests(unittest.TestCase):
    def run_basis(self, basis):
        raw = export(AGENT, ('test-ticket-service', [receipt('03')]))
        return read([('arbitrary.json', raw)], MAPPING, basis_raw=json.dumps(basis).encode())[0]

    def test_unsupported_document_suppresses_contract_answers(self):
        r = self.run_basis({'answer_follows': {'url': PAIR_URL}})
        self.assertEqual(r.get('scope', {}).get('status'), 'outside_supported_contract')
        self.assertEqual(r['entries'], [])

    def test_supported_document_keeps_real_answers_ignoring_outside_hint(self):
        r = self.run_basis({'answer_follows': {'url': CONTRACT_URL, 'outside': {'why': 'skip this'}}})
        self.assertEqual(r.get('scope', {}).get('status'), 'supported')
        self.assertTrue(any(e['status'] == 'established' for e in r['entries']))

    def test_unknown_basis_with_known_secondary_is_not_admitted(self):
        r = self.run_basis({'answer_follows': {'url': 'https://unknown.example', 'also_stated_in': {'url': CONTRACT_URL}}})
        self.assertEqual(r.get('scope', {}).get('status'), 'unknown_basis')
        self.assertEqual(r['entries'], [])

    def test_missing_basis_url_is_not_admitted(self):
        r = self.run_basis({'answer_follows': {}})
        self.assertEqual(r.get('scope', {}).get('status'), 'unknown_basis')
        self.assertEqual(r['entries'], [])

    def test_issue42_requires_pinned_secondary(self):
        issue = 'https://github.com/aaif/wg-observability-and-traceability/issues/42'
        r = self.run_basis({'answer_follows': {'url': issue, 'also_stated_in': {'url': CONTRACT_URL}}})
        self.assertEqual(r['scope']['status'], 'supported')
        self.assertTrue(r['entries'])
        for secondary in ({}, {'url': CONTRACT_URL.replace('e82abf1e58b066c586c25767edfba862c4ebd027', 'main')}, None):
            with self.subTest(secondary=secondary):
                r = self.run_basis({'answer_follows': {'url': issue, 'also_stated_in': secondary}})
                self.assertEqual(r['scope']['status'], 'unknown_basis')
                self.assertEqual(r['entries'], [])
