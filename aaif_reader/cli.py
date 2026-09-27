"""Command line: read a set of OTLP/JSON exports through one mapping file.

    python3 -m aaif_reader --mapping MAP.json --out DIR INPUT [INPUT ...]

Writes DIR/report.json and DIR/run.json (DESIGN.md section 6). This program has
no code path that reads an expected-answer file (section 2).
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

from . import REGISTER_VERSION, TOOLING
from .answer import all_entries, unplaced_losses
from .model import build, canon
from . import parse
from .parse import CapBreach, ParseFailure, digest, load_json, spans_from_otlp

CONTRACT = {
    "pr": "aaif/wg-observability-and-traceability#51",
    "head": "e82abf1e58b066c586c25767edfba862c4ebd027",
    "file_sha256": "745dc261d4cf12358a74ac4e9fe942aa85d8b1d85e514896f3a6026b9d08b0b4",
    "version": "v0.7-draft",
}


def _read(inputs: list[tuple[str, bytes]], mapping_raw: bytes, basis_raw: bytes | None = None):
    """Pure function from (member name, bytes) pairs to (report, run) dicts.

    Member names become source locators and nothing else.
    """
    try:
        mapping = load_json(mapping_raw)
    except ParseFailure as exc:
        return {"processing": "failed", "entries": []}, {"processing": {"status": "failed", "reason": f"mapping: {exc}"}}
    run = {
        "contract": CONTRACT,
        "register_version": REGISTER_VERSION,
        "tooling": TOOLING,
        "mapping_sha256": digest(mapping_raw),
        "mapping_id": mapping.get("mapping_id"),
        "inputs": sorted(({"sha256": digest(raw), "bytes": len(raw)} for _, raw in inputs), key=canon),
        "caps": {"max_input_bytes": parse.MAX_INPUT_BYTES, "max_depth": parse.MAX_DEPTH, "max_records": parse.MAX_RECORDS, "hit": []},
    }
    records = []
    for member, raw in inputs:
        try:
            records.extend(spans_from_otlp(raw, member))
        except CapBreach as exc:
            # A cap breach marks processing partial and suppresses every
            # export-level conclusion; it never looks like a clean read.
            run["caps"]["hit"].append(str(exc))
        except ParseFailure as exc:
            run["processing"] = {"status": "failed", "reason": str(exc)}
            return {"processing": "failed", "entries": []}, run
    if len(records) > parse.MAX_RECORDS:
        # Nothing is dropped: which records a cut would keep depends on arrival
        # order (IC-1). The breach is recorded and every conclusion suppressed.
        run["caps"]["hit"].append(f"record count over cap {parse.MAX_RECORDS}")
    tables = build(records, mapping)
    entries = all_entries(tables)
    if run["caps"]["hit"]:
        run["processing"] = {"status": "partial", "reasons": sorted(run["caps"]["hit"])}
        entries = [
            {"question": e["question"], "subject": e["subject"], "status": "not_evaluated", "answer": None,
             "missing": ["processing partial: a cap was hit, so no export-level conclusion is drawn"],
             "conflicts": [], "losses": [], "basis": []}
            for e in entries
        ]
        status = "partial"
    else:
        run["processing"] = {"status": "complete"}
        status = "complete"
    report = {"processing": status, "entries": entries, "unplaced_losses": unplaced_losses(tables)}
    return report, run


CONTRACT_URL = "https://github.com/aaif/wg-observability-and-traceability/blob/e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md"
PAIR_URL = "https://github.com/aaif/wg-observability-and-traceability/blob/41e6eacc2fc6bf783f45d873c3d01eb7dd0f9560/working-documents/agent-mcp-server-boundary-deep-dive.md"
ISSUE42_URL = "https://github.com/aaif/wg-observability-and-traceability/issues/42"


def read(inputs, mapping_raw, basis_raw=None):
    """An optional case-level scope gate; outside hints never decide scope.

    This registry is the reader's interpretation, not WG metadata authority.
    Legacy callers without a basis retain their explicit contract-only mode.
    """
    if basis_raw is None:
        return _read(inputs, mapping_raw)
    try:
        basis = load_json(basis_raw)
        follows = basis.get("answer_follows", {}) if isinstance(basis, dict) else {}
        url = follows.get("url") if isinstance(follows, dict) else None
        secondary = follows.get("also_stated_in", {}) if isinstance(follows, dict) else {}
        supported = url == CONTRACT_URL or (url == ISSUE42_URL and isinstance(secondary, dict) and secondary.get("url") == CONTRACT_URL)
        status = "supported" if supported else "outside_supported_contract" if url == PAIR_URL else "unknown_basis"
    except ParseFailure:
        url, status = None, "invalid_basis"
    scope = {"status": status, "answer_document": url}
    if status == "supported":
        report, run = _read(inputs, mapping_raw)
    else:
        report = {"processing": "not_evaluated", "entries": []}
        run = {"contract": CONTRACT, "mapping_sha256": digest(mapping_raw),
               "inputs": sorted([{"sha256": digest(raw), "bytes": len(raw)} for _, raw in inputs], key=canon),
               "processing": {"status": "not_evaluated"}}
    report["scope"] = scope
    run["basis_sha256"] = digest(basis_raw)
    run["scope_register"] = "PR57 basis registry revision 1; see BASIS-RERUN.md"
    return report, run


def reader_commit() -> str:
    try:
        here = Path(__file__).resolve().parent
        out = subprocess.run(["git", "-C", str(here), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        dirty = subprocess.run(["git", "-C", str(here), "status", "--porcelain", "--", str(here)], capture_output=True, text=True).stdout.strip()
        return out.stdout.strip() + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="aaif_reader")
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--basis", help="Explicit case basis; never inferred from a filename")
    ap.add_argument("inputs", nargs="+")
    a = ap.parse_args(argv)
    inputs = [(Path(p).name, Path(p).read_bytes()) for p in a.inputs]
    report, run = read(inputs, Path(a.mapping).read_bytes(), Path(a.basis).read_bytes() if a.basis else None)
    run["reader_commit"] = reader_commit()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(canon(report) + "\n", encoding="utf-8")
    (out / "run.json").write_text(canon(run) + "\n", encoding="utf-8")
    return {"complete": 0, "partial": 3, "not_evaluated": 4}.get(report["processing"], 2)


if __name__ == "__main__":
    sys.exit(main())
