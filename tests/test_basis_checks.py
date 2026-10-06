"""Basis registry revision 2: scope is decided per named check.

Written before the implementation, against the basis.json shape at kit
4a028675ef (a `checks` list, with an optional `<check>_follows` object that
overrides `answer_follows` for that check). No expected-answer file is read.
"""
import json
import unittest

from aaif_reader.cli import read
from tests.test_reader import MAPPING, export, AGENT, receipt

CONTRACT_URL = 'https://github.com/aaif/wg-observability-and-traceability/blob/e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md'
PAIR_URL = 'https://github.com/aaif/wg-observability-and-traceability/blob/41e6eacc2fc6bf783f45d873c3d01eb7dd0f9560/working-documents/agent-mcp-server-boundary-deep-dive.md'
ISSUE42 = 'https://github.com/aaif/wg-observability-and-traceability/issues/42'
ISSUE42_PINNED = {'url': ISSUE42, 'also_stated_in': {'url': CONTRACT_URL}}


class PerCheckBasis(unittest.TestCase):
    def run_basis(self, basis):
        raw = export(AGENT, ('test-ticket-service', [receipt('03')]))
        return read([('arbitrary.json', raw)], MAPPING, basis_raw=json.dumps(basis).encode())[0]

    def checks(self, report):
        return {c: v['status'] for c, v in report['scope']['checks'].items()}

    def test_pair_shape_answers_correlation_and_not_signature(self):
        r = self.run_basis({'answer_follows': {'url': PAIR_URL, 'outside': {'why': 'x'}},
                            'checks': ['effect_correlation', 'receipt_signature'],
                            'effect_correlation_follows': ISSUE42_PINNED})
        self.assertEqual(self.checks(r), {'effect_correlation': 'supported',
                                          'receipt_signature': 'outside_supported_contract'})
        self.assertEqual(r['processing'], 'complete')
        self.assertTrue(any(e['question'] == 'effects' and e['status'] == 'established' for e in r['entries']))

    def test_signature_is_never_a_contract_answer_even_if_basis_names_the_contract(self):
        r = self.run_basis({'answer_follows': ISSUE42_PINNED, 'checks': ['effect_correlation', 'receipt_signature']})
        self.assertEqual(self.checks(r)['receipt_signature'], 'no_contract_rule')
        self.assertEqual(self.checks(r)['effect_correlation'], 'supported')

    def test_per_check_basis_must_be_pinned(self):
        unpinned = {'url': ISSUE42, 'also_stated_in': {'url': CONTRACT_URL.replace('e82abf1e58b066c586c25767edfba862c4ebd027', 'main')}}
        r = self.run_basis({'answer_follows': {'url': PAIR_URL}, 'checks': ['effect_correlation'],
                            'effect_correlation_follows': unpinned})
        self.assertEqual(self.checks(r), {'effect_correlation': 'unknown_basis'})
        self.assertEqual(r['processing'], 'not_evaluated')
        self.assertEqual(r['entries'], [])

    def test_no_correlation_check_means_no_contract_answers(self):
        r = self.run_basis({'answer_follows': ISSUE42_PINNED, 'checks': ['receipt_signature']})
        self.assertEqual(r['processing'], 'not_evaluated')
        self.assertEqual(r['entries'], [])

    def test_unknown_check_is_recorded_and_admits_nothing(self):
        r = self.run_basis({'answer_follows': ISSUE42_PINNED, 'checks': ['ticket_count']})
        self.assertEqual(self.checks(r), {'ticket_count': 'unknown_check'})
        self.assertEqual(r['entries'], [])

    def test_outside_hint_never_excludes_a_supported_check(self):
        r = self.run_basis({'answer_follows': {'url': ISSUE42, 'also_stated_in': {'url': CONTRACT_URL},
                                               'outside': {'document': 'v0.7', 'why': 'skip'}},
                            'checks': ['effect_correlation']})
        self.assertEqual(self.checks(r), {'effect_correlation': 'supported'})
        self.assertTrue(r['entries'])

    def test_override_key_only_for_named_checks(self):
        # A `<check>_follows` for a check the basis does not ask for changes nothing.
        r = self.run_basis({'answer_follows': {'url': PAIR_URL}, 'checks': ['receipt_signature'],
                            'effect_correlation_follows': ISSUE42_PINNED})
        self.assertEqual(self.checks(r), {'receipt_signature': 'outside_supported_contract'})
        self.assertEqual(r['entries'], [])

    def test_malformed_checks_are_invalid(self):
        for checks in ('effect_correlation', [1], ['effect_correlation', 'effect_correlation'], []):
            with self.subTest(checks=checks):
                r = self.run_basis({'answer_follows': ISSUE42_PINNED, 'checks': checks})
                self.assertEqual(r['scope']['status'], 'invalid_basis')
                self.assertEqual(r['entries'], [])


if __name__ == '__main__':
    unittest.main()
