"""Separate README-derived Ed25519 check; never imported by the contract reader.

Requires cryptography. No assertion of service independence or real effects.
"""
import base64
import binascii
import json
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def signing_bytes(attributes):
    fields = {name: attributes['receipt.' + ('id' if name == 'receipt_id' else name)]
              for name in ('action_id', 'created_at', 'receipt_id', 'service', 'ticket_id')}
    if not all(isinstance(value, str) for value in fields.values()):
        raise ValueError('This bounded verifier accepts string receipt fields only')
    return json.dumps(fields, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def verifies(attributes, public_key):
    key = load_pem_public_key(public_key)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError('Expected Ed25519 SPKI key')
    encoded = attributes.get('receipt.signature')
    if not isinstance(encoded, str):
        return False
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return False
    if base64.b64encode(signature).decode() != encoded:
        return False
    try:
        key.verify(signature, signing_bytes(attributes))
        return True
    except InvalidSignature:
        return False
