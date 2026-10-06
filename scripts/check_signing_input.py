"""Separate README-derived Ed25519 check; never imported by the contract reader.

Requires cryptography. No assertion of service independence or real effects.
"""
import base64
import binascii
import json
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class MalformedSignature(ValueError):
    """The signature value could not be decoded, so nothing was verified."""


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
    # True or False only for a signature that was decoded and checked. A value
    # that cannot be decoded was not checked, so it raises instead of reading
    # as a failed signature.
    encoded = attributes.get('receipt.signature')
    if not isinstance(encoded, str):
        raise MalformedSignature('Signature is not a string')
    try:
        signature = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise MalformedSignature('Signature is not valid base64') from exc
    if base64.b64encode(signature).decode() != encoded:
        raise MalformedSignature('Signature is not canonical base64')
    try:
        key.verify(signature, signing_bytes(attributes))
        return True
    except InvalidSignature:
        return False
