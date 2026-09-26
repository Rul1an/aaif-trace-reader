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
from .parse import MAX_DEPTH, MAX_INPUT_BYTES, MAX_RECORDS, ParseFailure, digest, load_json, spans_from_otlp

CONTRACT = {
    "pr": "aaif/wg-observability-and-traceability#51",
    "head": "e82abf1e58b066c586c25767edfba862c4ebd027",
    "file_sha256": "745dc261d4cf12358a74ac4e9fe942aa85d8b1d85e514896f3a6026b9d08b0b4",
    "version": "v0.7-draft",
}


def read(inputs: list[tuple[str, bytes]], mapping_raw: bytes):
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
        "caps": {"max_input_bytes": MAX_INPUT_BYTES, "max_depth": MAX_DEPTH, "max_records": MAX_RECORDS, "hit": []},
    }
    records = []
    try:
        for member, raw in inputs:
            records.extend(spans_from_otlp(raw, member))
    except ParseFailure as exc:
        run["processing"] = {"status": "failed", "reason": str(exc)}
        return {"processing": "failed", "entries": []}, run
    tables = build(records, mapping)
    run["processing"] = {"status": "complete"}
    report = {
        "processing": "complete",
        "entries": all_entries(tables),
        "unplaced_losses": unplaced_losses(tables),
    }
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
    ap.add_argument("inputs", nargs="+")
    a = ap.parse_args(argv)
    inputs = [(Path(p).name, Path(p).read_bytes()) for p in a.inputs]
    report, run = read(inputs, Path(a.mapping).read_bytes())
    run["reader_commit"] = reader_commit()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(canon(report) + "\n", encoding="utf-8")
    (out / "run.json").write_text(canon(run) + "\n", encoding="utf-8")
    return 0 if report["processing"] == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
