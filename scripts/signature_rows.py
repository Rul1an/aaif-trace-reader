"""Separate signature check over one pinned kit revision; never imported by the reader.

Runs the README-derived Ed25519 check (scripts/check_signing_input.py) only on
cases whose basis.json lists `receipt_signature`; other cases are recorded as
not asked. Usage: python3 scripts/signature_rows.py <kit sha> > signatures.json
"""
import hashlib
import json
import platform
import sys
from pathlib import Path

import cryptography

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_signing_input import MalformedSignature, signing_bytes, verifies  # noqa: E402


def attrs(span):
    out = {}
    for a in span.get("attributes", []):
        v = a["value"]
        if not v:
            if a["key"].startswith("receipt."):
                out[a["key"]] = None
            continue
        out[a["key"]] = next(iter(v.values()))
    return out


def main(kit):
    root = Path(__file__).resolve().parent.parent / "inputs" / f"test-kit-{kit}"
    key = (root / "trust" / "test-ticket-service.pub.pem").read_bytes()
    rows = []
    for case in sorted(p.name for p in (root / "cases").iterdir()):
        basis = json.loads((root / "cases" / case / "basis.json").read_bytes())
        if "receipt_signature" not in basis.get("checks", []):
            rows.append({"case": case, "signature_check": "not_asked_by_basis"})
            continue
        export = json.loads((root / "cases" / case / "records.otlp.json").read_bytes())
        before = len(rows)
        for rs in export["resourceSpans"]:
            for ss in rs["scopeSpans"]:
                for sp in ss["spans"]:
                    a = attrs(sp)
                    if "receipt.signature" not in a:
                        continue
                    try:
                        b = signing_bytes(a)
                        if not isinstance(a["receipt.signature"], str):
                            raise ValueError("Invalid signature value")
                    except (KeyError, ValueError):
                        rows.append({"case": case, "signature_check": "invalid_receipt_fields",
                                     "signature_valid": None})
                        continue
                    row = {"case": case, "receipt": a["receipt.id"], "signing_bytes_utf8": b.decode(),
                           "length": len(b), "sha256": hashlib.sha256(b).hexdigest()}
                    try:
                        row["signature_valid"] = verifies(a, key)
                    except MalformedSignature:
                        # Not checked, so neither valid nor invalid.
                        row.update(signature_check="malformed_signature", signature_valid=None)
                    rows.append(row)
        if len(rows) == before:
            rows.append({"case": case, "signature_check": "missing_signature", "signature_valid": None})
    return {"kit": kit, "python": platform.python_version(), "cryptography": cryptography.__version__,
            "key_sha256": hashlib.sha256(key).hexdigest(), "rows": rows,
            "claim": "Signature validity under the supplied synthetic key only; not actual effects or independence"}


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1]), indent=2))
