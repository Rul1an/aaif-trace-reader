import base64
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from scripts.check_signing_input import signing_bytes, verifies

class SigningTests(unittest.TestCase):
    def setUp(self):
        self.attrs = {'receipt.action_id':'P1','receipt.created_at':'2026-09-21T15:00:00Z','receipt.id':'R-7','receipt.service':'test-ticket-service','receipt.ticket_id':'T-1042'}
        self.literal = b'{"action_id":"P1","created_at":"2026-09-21T15:00:00Z","receipt_id":"R-7","service":"test-ticket-service","ticket_id":"T-1042"}'
        key = Ed25519PrivateKey.generate()
        self.public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        self.attrs['receipt.signature'] = base64.b64encode(key.sign(self.literal)).decode()

    def test_exact_documented_bytes(self):
        self.assertEqual(len(self.literal),126)
        self.assertEqual(signing_bytes(self.attrs),self.literal)

    def test_positive_and_changed_field(self):
        self.assertTrue(verifies(self.attrs,self.public))
        self.attrs['receipt.ticket_id']='OTHER'
        self.assertFalse(verifies(self.attrs,self.public))

    def test_other_key_rejected(self):
        key=Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        self.assertFalse(verifies(self.attrs,key))

    def test_unicode_uses_ascii_escapes(self):
        self.attrs['receipt.ticket_id']='é'
        self.assertIn(b'\\u00e9',signing_bytes(self.attrs))
