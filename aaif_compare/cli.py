"""Command line for the comparator.

    python3 -m aaif_compare --kit SHA --run RUN_DIR --expected EXPECTED_DIR \
        --projection projections/kit-SHORT.json [--other OTHER_COMPARISON.json] --out comparison.json

RUN_DIR holds one directory per case with the reader's report.json, and the
separate signature check's signatures.json at its top. Exit 0 when every
expected field matches, 1 when any does not, 2 when the all-unknown control
fails or an input cannot be read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .compare import ControlFailed, compare


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aaif_compare")
    ap.add_argument("--kit", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--projection", required=True)
    ap.add_argument("--other")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    run, exp_dir = Path(a.run), Path(a.expected)
    expected = {p.parent.name: json.loads(p.read_text()) for p in sorted(exp_dir.glob("*/expected.json"))}
    if not expected:
        print("aaif_compare: no expected answers found", file=sys.stderr)
        return 2
    reports = {p.parent.name: json.loads(p.read_text()) for p in sorted(run.glob("*/report.json"))}
    signatures = {}
    sig_path = run / "signatures.json"
    if sig_path.is_file():
        for row in json.loads(sig_path.read_text()).get("rows", []):
            signatures.setdefault(row["case"], []).append(row)
    projection_path = Path(a.projection)
    projection = json.loads(projection_path.read_text())
    other_rows = json.loads(Path(a.other).read_text()) if a.other else []

    try:
        result = compare(reports, signatures, expected, projection, other_rows, a.kit)
    except ControlFailed as exc:
        print(f"aaif_compare: control failed, nothing scored: {exc}", file=sys.stderr)
        return 2

    inputs = {"projection": {"path": projection_path.as_posix(), "sha256": _sha(projection_path)},
              "expected": {p.parent.name: _sha(p) for p in sorted(exp_dir.glob("*/expected.json"))},
              "reports": {p.parent.name: _sha(p) for p in sorted(run.glob("*/report.json"))}}
    if sig_path.is_file():
        inputs["signatures"] = _sha(sig_path)
    if a.other:
        inputs["other_reader"] = {"path": Path(a.other).as_posix(), "sha256": _sha(Path(a.other))}
    doc = {"kit": a.kit, "comparator": "aaif_compare, DESIGN.md section 7 revision 8", "inputs": inputs, **result,
           "limits": ["Agreement with the expected answers and with the other reader are separate tables, never one score.",
                      "Fields marked by_construction agree because the query echoes them; they are counted apart.",
                      "A comparison of answers on synthetic fixtures; it says nothing about real effects or exports."]}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n")
    s, o = result["vs_expected"]["summary"], result["vs_other_reader"]["summary"]
    print(json.dumps({"vs_expected": s, "vs_other_reader": o}))
    return 0 if s["cases_all_fields_match"] == s["cases"] else 1
