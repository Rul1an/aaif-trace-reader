"""Must-fail controls on the reader, DESIGN.md section 8.

Each mutant is a small, named change to the reader that must turn at least one
named case red. A mutant that survives is a defect in the case, not evidence
about the reader. The three controls after m13 revert behaviours the first
slice had, so the tests that replaced them are proven to bite too.

    python3 tests/mutants.py        # exit 0 only if every mutant is killed

The runner edits one file at a time, runs the named tests in a subprocess,
and restores the file from memory before the next mutant, also on error.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = "aaif_reader/"

MUTANTS = [
    ("m1", "drop scope from the key", R + "model.py",
     'key = (scope if scope is not None else UNRESOLVED, rule["kind"], nid)',
     'key = ("", rule["kind"], nid)',
     ["tests.test_reader.Effects.test_c4_same_receipt_id_in_second_service"]),
    ("m2", "index with overwrite instead of multi-value", R + "model.py",
     't.contents.setdefault(key, {}).setdefault(_content(rec), set()).add(rec.locator)',
     't.contents[key] = {_content(rec): {rec.locator}}',
     ["tests.test_reader.Effects.test_c10_two_receipts_same_key_different_content"]),
    ("m3", "sum usage across aggregation levels", R + "answer.py",
     '    if "success" in outcomes:\n        call_level = levels.get("call", [])',
     '    usage.update(status="established", value=sum(v for vs in levels.values() for v in vs if v != "unknown"))\n'
     '    if False:\n        call_level = levels.get("call", [])',
     ["tests.test_cases.Calls.test_c5_two_levels_without_declared_aggregation"]),
    ("m4", "drop an execution when its decision is a denial", R + "answer.py",
     '        executions = sorted({r[1] for r in erels}, key=canon)',
     '        executions = sorted({r[1] for r in erels if not any(_outcome(t, x[2]) == "denied" for x in _rels(t, "R5-decision", src=r[1]))}, key=canon)',
     ["tests.test_cases.Approvals.test_c6_execution_references_the_denial_it_followed"]),
    ("m5", "compare values with Python == (1 equals 1.0)", R + "parse.py",
     '        return ("float", repr(float(inner)))',
     '        return ("int", int(inner)) if float(inner).is_integer() else ("float", repr(float(inner)))',
     ["tests.test_reader.Effects.test_c10_int_against_float_is_a_conflict"]),
    ("m6", "resolve an unreferenced execution's decision in arrival order", R + "answer.py",
     '            refs = [r[2] for r in _rels(t, "R5-decision", src=ex) if r[2] in decisions]\n',
     '            refs = [r[2] for r in _rels(t, "R5-decision", src=ex) if r[2] in decisions]\n'
     '            if not refs and decisions:\n'
     '                refs = [min(decisions, key=lambda d: min((l.input_digest, l.ordinal) for l in t.entities[d]["locators"]))]\n',
     ["tests.test_cases.Approvals.test_approvals_invariant_under_shuffle"]),
    ("m7", "read the file name", R + "model.py",
     '    return min(anchors) if anchors else "unanchored"',
     '    return rec.locator.member',
     ["tests.test_reader.Invariance.test_c9_renamed"]),
    ("m8", "select one decision per proposal", R + "answer.py",
     '        decisions = sorted({r[1] for r in drels}, key=canon)',
     '        decisions = sorted({r[1] for r in drels}, key=canon)[:1]',
     ["tests.test_cases.Approvals.test_c14_denial_and_approval_no_execution",
      "tests.test_cases.Approvals.test_c14a_two_approvals_from_two_policies"]),
    ("m9", "report two decisions on one proposal as a conflict", R + "answer.py",
     '        conflicts = [k(d) for d in decisions if len(t.contents.get(d, {})) > 1]',
     '        conflicts = [k(d) for d in decisions] if len(decisions) > 1 else []',
     ["tests.test_cases.Approvals.test_c14_denial_and_approval_no_execution",
      "tests.test_cases.Approvals.test_c14a_two_approvals_from_two_policies"]),
    ("m10", "relate an unreferenced execution to a standing denial as inconsistent", R + "answer.py",
     '                items.append({"execution": k(ex), "finding": "unresolved"})',
     '                items.append({"execution": k(ex), "finding": "inconsistent_with_decision" if any(_outcome(t, d) == "denied" for d in decisions) else "unresolved"})',
     ["tests.test_cases.Approvals.test_c6b_only_denial_and_no_reference",
      "tests.test_cases.Approvals.test_c14b_denial_approval_and_unreferenced_execution"]),
    ("m11", "treat a proposal's only decision as the one an unreferenced execution followed", R + "answer.py",
     '            refs = [r[2] for r in _rels(t, "R5-decision", src=ex) if r[2] in decisions]\n',
     '            refs = [r[2] for r in _rels(t, "R5-decision", src=ex) if r[2] in decisions]\n'
     '            if not refs and len(decisions) == 1:\n                refs = decisions[:]\n',
     ["tests.test_cases.Approvals.test_c6b_only_denial_and_no_reference"]),
    ("m12", "render an unresolved entry from an approval-and-denial template", R + "answer.py",
     '            "decisions_recorded": [{"decision": k(d), "outcome": _outcome(t, d)} for d in decisions],',
     '            "decisions_recorded": [{"decision": k(d), "outcome": o} for d, o in zip(decisions, ["approved", "denied"] * len(decisions))] if len(decisions) >= 2 else [{"decision": k(d), "outcome": _outcome(t, d)} for d in decisions],',
     ["tests.test_cases.Approvals.test_c14c_two_approvals_and_unreferenced_execution"]),
    ("m13", "relate an unreferenced execution to each approval as consistent", R + "answer.py",
     '                items.append({"execution": k(ex), "finding": "unresolved"})',
     '                items.append({"execution": k(ex), "finding": "consistent" if all(_outcome(t, d) == "approved" for d in decisions) else "unresolved"})',
     ["tests.test_cases.Approvals.test_c14c_two_approvals_and_unreferenced_execution"]),
    # Controls on behaviours the first slice had (FINDINGS.md D1, D2).
    ("c-cap", "fail instead of marking processing partial on a cap breach", R + "cli.py",
     '        except CapBreach as exc:\n',
     '        except () as exc:\n',
     ["tests.test_reader.ParsingContract.test_size_over_cap_is_partial_not_clean",
      "tests.test_reader.ParsingContract.test_cap_breach_suppresses_every_conclusion"]),
    ("c-hash", "label a keyless subject by a content hash", R + "model.py",
     'key = (KEYLESS, kind, f"{anchor}#{i}")',
     'key = (KEYLESS, kind, __import__("hashlib").sha256(_content(rec).encode()).hexdigest()[:16])',
     ["tests.test_reader.KeylessHandle.test_handle_is_anchor_and_ordinal"]),
    ("c-trunc", "truncate records by arrival order on a count breach", R + "cli.py",
     '        run["caps"]["hit"].append(f"record count over cap {parse.MAX_RECORDS}")\n',
     '        run["caps"]["hit"].append(f"record count over cap {parse.MAX_RECORDS}")\n'
     '        records = records[: parse.MAX_RECORDS]\n',
     ["tests.test_reader.ParsingContract.test_record_count_over_cap_is_partial"]),
]


def run_tests(names) -> bool:
    return _run(names)[0]


def _run(names):
    proc = subprocess.run([sys.executable, "-B", "-m", "unittest", *names], cwd=ROOT, capture_output=True, text=True)
    return proc.returncode == 0, proc.stderr


def main() -> int:
    if not run_tests(sorted({n for m in MUTANTS for n in m[5]})):
        print("baseline: named tests do not pass on the unmutated reader; stop")
        return 2
    survivors = []
    for mid, what, rel, old, new, tests in MUTANTS:
        path = ROOT / rel
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            print(f"{mid}: anchor not found exactly once in {rel}; stop")
            return 2
        try:
            path.write_text(original.replace(old, new, 1), encoding="utf-8")
            ok, log = _run(tests)
            killed = not ok
        finally:
            path.write_text(original, encoding="utf-8")
        # A kill by an exception says the mutant broke the program, not that a
        # case caught a wrong answer; only an assertion failure counts.
        by_error = killed and "errors=" in log.splitlines()[-1] if log.strip() else False
        verdict = "SURVIVED" if not killed else ("ERROR   " if by_error else "killed  ")
        print(f"{mid:8s} {verdict} {what} -> {', '.join(t.rsplit('.', 1)[1] for t in tests)}")
        if not killed or by_error:
            survivors.append(mid)
    if not run_tests(sorted({n for m in MUTANTS for n in m[5]})):
        print("restore check failed: the reader does not pass after restoring; stop")
        return 2
    print(f"{len(MUTANTS) - len(survivors)}/{len(MUTANTS)} killed by an assertion failure")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
