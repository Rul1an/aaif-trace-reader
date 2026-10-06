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
from .answer import all_entries, query, unplaced_losses
from .model import build, canon
from . import parse
from .parse import CapBreach, ParseFailure, digest, load_json, spans_from_otlp

CONTRACT = {
    "pr": "aaif/wg-observability-and-traceability#51",
    "head": "e82abf1e58b066c586c25767edfba862c4ebd027",
    "file_sha256": "745dc261d4cf12358a74ac4e9fe942aa85d8b1d85e514896f3a6026b9d08b0b4",
    "version": "v0.7-draft",
}


def _read(inputs: list[tuple[str, bytes]], mapping_raw: bytes, basis_raw: bytes | None = None, ctx=None):
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
    if ctx is not None:
        if not _valid_context(ctx):
            report["query"] = {"status": "invalid_context"}
        elif status != "complete":
            report["query"] = {"status": "not_evaluated", "context": ctx}
        else:
            report["query"] = query(tables, ctx)
    return report, run


def _valid_context(ctx):
    return (isinstance(ctx, dict) and set(ctx) == {"action", "service", "tenant"}
            and isinstance(ctx["action"], str) and ctx["action"]
            and isinstance(ctx["service"], str) and ctx["service"]
            and (ctx["tenant"] is None or (isinstance(ctx["tenant"], str) and ctx["tenant"])))


CONTRACT_URL = "https://github.com/aaif/wg-observability-and-traceability/blob/e82abf1e58b066c586c25767edfba862c4ebd027/working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md"
PAIR_URL = "https://github.com/aaif/wg-observability-and-traceability/blob/41e6eacc2fc6bf783f45d873c3d01eb7dd0f9560/working-documents/agent-mcp-server-boundary-deep-dive.md"
ISSUE42_URL = "https://github.com/aaif/wg-observability-and-traceability/issues/42"


KNOWN_CHECKS = ("effect_correlation", "receipt_signature")
CONTRACT_CHECK = "effect_correlation"


def _classify(follows):
    """Registry lookup for one basis object; only pinned URLs are recognised."""
    if not isinstance(follows, dict):
        return None, "unknown_basis"
    url = follows.get("url")
    secondary = follows.get("also_stated_in")
    if url == CONTRACT_URL or (url == ISSUE42_URL and isinstance(secondary, dict) and secondary.get("url") == CONTRACT_URL):
        return url, "supported"
    return url, "outside_supported_contract" if url == PAIR_URL else "unknown_basis"


def _scope(basis):
    """Revision 1 without `checks`; revision 2 decides scope per named check.

    `outside` and every other hint are ignored: scope comes from the registry.
    Only the contract check is answered by this reader; the signature check is
    never a contract answer (contract line 112) and is reported separately.
    """
    if not isinstance(basis, dict):
        return {"status": "unknown_basis", "answer_document": None}, False
    follows = basis.get("answer_follows", {})
    if "checks" not in basis:
        url, status = _classify(follows)
        return {"status": status, "answer_document": url}, status == "supported"
    checks = basis["checks"]
    if (not isinstance(checks, list) or not checks or not all(isinstance(c, str) for c in checks)
            or len(set(checks)) != len(checks)):
        return {"status": "invalid_basis", "answer_document": None}, False
    per = {}
    for c in checks:
        if c not in KNOWN_CHECKS:
            per[c] = {"status": "unknown_check", "answer_document": None}
            continue
        url, status = _classify(basis.get(c + "_follows", follows))
        if c != CONTRACT_CHECK and status == "supported":
            status = "no_contract_rule"
        per[c] = {"status": status, "answer_document": url}
    admitted = per.get(CONTRACT_CHECK, {}).get("status") == "supported"
    return {"status": "per_check", "checks": per}, admitted


def read(inputs, mapping_raw, basis_raw=None):
    """An optional case-level scope gate; outside hints never decide scope.

    This registry is the reader's interpretation, not WG metadata authority.
    Legacy callers without a basis retain their explicit contract-only mode.
    """
    if basis_raw is None:
        return _read(inputs, mapping_raw)
    ctx = None
    try:
        parsed = load_json(basis_raw)
        scope, admitted = _scope(parsed)
        if isinstance(parsed, dict) and "evaluation_context" in parsed:
            ctx = parsed["evaluation_context"]
    except ParseFailure:
        scope, admitted = {"status": "invalid_basis", "answer_document": None}, False
    if admitted:
        report, run = _read(inputs, mapping_raw, ctx=ctx)
    else:
        report = {"processing": "not_evaluated", "entries": []}
        run = {"contract": CONTRACT, "mapping_sha256": digest(mapping_raw),
               "inputs": sorted([{"sha256": digest(raw), "bytes": len(raw)} for _, raw in inputs], key=canon),
               "processing": {"status": "not_evaluated"}}
    report["scope"] = scope
    run["basis_sha256"] = digest(basis_raw)
    run["scope_register"] = ("PR57 basis registry revision 3 (evaluation_context); see BASIS-RERUN-b658795.md"
                             if ctx is not None else "PR57 basis registry revision 2; see BASIS-RERUN-4a02867.md")
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
