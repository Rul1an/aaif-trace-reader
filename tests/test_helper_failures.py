import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import signature_rows
MalformedSignature = signature_rows.MalformedSignature  # the class signature_rows itself raises and catches
from tests import test_signing_input

ROOT = Path(__file__).resolve().parents[1]
KIT = 'b6587950986eb4ec501e080cc9730fd21dcb69fa'


class HelperFailures(unittest.TestCase):
    def test_invalid_signature_encoding(self):
        fixture = test_signing_input.SigningTests(); fixture.setUp()
        # A signature that cannot be decoded was not checked: it must not read as
        # a cryptographic failure (False), which is reserved for a decoded
        # signature that does not verify.
        for sig in ['!!!', fixture.attrs['receipt.signature'] + '\n', None]:
            with self.subTest(sig=sig):
                with self.assertRaises(MalformedSignature):
                    signature_rows.verifies({**fixture.attrs, 'receipt.signature': sig}, fixture.public)
        self.assertFalse(signature_rows.verifies({**fixture.attrs, 'receipt.ticket_id': 'T-9'}, fixture.public))
        with self.assertRaises(ValueError):
            signature_rows.verifies(fixture.attrs, b'bad key')

    def test_empty_unrelated_attribute(self):
        self.assertEqual(signature_rows.attrs({'attributes': [{'key': 'unused', 'value': {}}]}), {})

    def check_missing(self, empty, malformed=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = root / 'inputs' / ('test-kit-' + KIT)
            shutil.copytree(ROOT / 'inputs' / ('test-kit-' + KIT), kit)
            p = kit / 'cases/evidence-grade-pair-verifies/records.otlp.json'
            doc = json.loads(p.read_text())
            for rs in doc['resourceSpans']:
                for ss in rs['scopeSpans']:
                    for sp in ss['spans']:
                        if malformed:
                            for attr in sp['attributes']:
                                if attr['key'] == 'receipt.signature': attr['value'] = {'stringValue': '!!!'}
                        elif empty:
                            for attr in sp['attributes']:
                                if attr['key'] == 'receipt.signature': attr['value'] = {}
                        else:
                            sp['attributes'] = [a for a in sp['attributes'] if a['key'] != 'receipt.signature']
            p.write_text(json.dumps(doc))
            with patch.object(signature_rows, '__file__', str(root / 'scripts/signature_rows.py')):
                result = signature_rows.main(KIT)
            rows = [r for r in result['rows'] if r['case'] == 'evidence-grade-pair-verifies']
            self.assertEqual(len(rows), 1)
            expected = 'malformed_signature' if malformed else 'invalid_receipt_fields' if empty else 'missing_signature'
            self.assertEqual(rows[0].get('signature_check'), expected)
            self.assertIsNone(rows[0]['signature_valid'])

    def test_requested_signature_missing(self): self.check_missing(False)
    def test_requested_signature_empty(self): self.check_missing(True)
    def test_requested_signature_malformed(self): self.check_missing(False, malformed=True)

    def test_fetch_tree_failure_or_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'scripts').mkdir(); (root/'bin').mkdir()
            shutil.copy(ROOT/'scripts/fetch_kit_at.sh',root/'scripts/fetch_kit_at.sh')
            gh=root/'bin/gh'
            for code in (0, 1):
                gh.write_text('#!/bin/sh\nexit '+str(code)+'\n'); gh.chmod(0o755)
                r=subprocess.run(['sh','scripts/fetch_kit_at.sh',KIT],cwd=root,
                                 env={**os.environ,'PATH':str(root/'bin')+':'+os.environ['PATH']},capture_output=True)
                self.assertNotEqual(r.returncode,0)
