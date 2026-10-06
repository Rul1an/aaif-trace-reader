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
    # Basis registry revision 2 (kit 4a028675ef): scope per named check.
    ("b1", "ignore the per-check basis and use answer_follows for every check", R + "cli.py",
     'basis.get(c + "_follows", follows)',
     'follows',
     ["tests.test_basis_checks.PerCheckBasis.test_pair_shape_answers_correlation_and_not_signature"]),
    ("b2", "let an outside hint exclude a check", R + "cli.py",
     '        url, status = _classify(basis.get(c + "_follows", follows))\n',
     '        url, status = _classify(basis.get(c + "_follows", follows))\n'
     '        status = "outside_supported_contract" if isinstance(follows, dict) and "outside" in follows else status\n',
     ["tests.test_basis_checks.PerCheckBasis.test_outside_hint_never_excludes_a_supported_check"]),
    ("b3", "answer the signature check under the contract", R + "cli.py",
     '        if c != CONTRACT_CHECK and status == "supported":',
     '        if False:',
     ["tests.test_basis_checks.PerCheckBasis.test_signature_is_never_a_contract_answer_even_if_basis_names_the_contract"]),
    ("b4", "admit the contract read when any check is supported", R + "cli.py",
     '    admitted = per.get(CONTRACT_CHECK, {}).get("status") == "supported"',
     '    admitted = any(v["status"] in ("supported", "no_contract_rule") for v in per.values())',
     ["tests.test_basis_checks.PerCheckBasis.test_no_correlation_check_means_no_contract_answers"]),
    ("b5", "accept duplicate check names", R + "cli.py",
     '            or len(set(checks)) != len(checks)):',
     '            or False):',
     ["tests.test_basis_checks.PerCheckBasis.test_malformed_checks_are_invalid"]),
    ("b6", "let a receipt from another service inherit the R6 default", R + "model.py",
     '        if "source_scope" in c and system_of(scope, t.tenant_scoped) != c["source_scope"]:',
     '        if False:',
     ["tests.test_mapping_4a02867.KitMapping.test_other_service_does_not_inherit_r6"]),
    ("b7", "drop the tenant from the scope", R + "model.py",
     '    return f"{system}@{tv[1]}"',
     '    return system',
     ["tests.test_mapping_b658795.TenantScope.test_queried_tenant_confirms_only_its_own_ticket",
      "tests.test_mapping_b658795.TenantScope.test_same_receipt_key_in_two_tenants_is_two_effects_not_a_conflict"]),
    ("b8", "compare the whole qualified scope against the declared receipt service", R + "model.py",
     '        if "source_scope" in c and system_of(scope, t.tenant_scoped) != c["source_scope"]:',
     '        if "source_scope" in c and scope != c["source_scope"]:',
     ["tests.test_mapping_b658795.TenantScope.test_queried_tenant_confirms_only_its_own_ticket"]),
    ("b9", "ignore the tenant when selecting effects for a query", R + "answer.py",
     '          and system_of(r[2][0], ts) == service and tenant_of(r[2][0], ts) == tenant]',
     '          and system_of(r[2][0], ts) == service]',
     ["tests.test_mapping_b658795.TenantScope.test_query_keeps_the_tenant_even_when_the_mapping_joins_across_it"]),
    ("b10", "resolve a receipt reference in the agent's scope without its tenant", R + "model.py",
     '            return spec["declared"] + (f"@{tenant}" if tenant else "")',
     '            return spec["declared"]',
     ["tests.test_mapping_b658795.TenantScope.test_queried_tenant_confirms_only_its_own_ticket"]),
    ("b11", "keep only one ticket id per receipt", R + "answer.py",
     '    return values or None',
     '    return values[:1] or None',
     ["tests.test_mapping_b658795.TicketIds.test_conflicting_ticket_ids_on_one_receipt_are_kept"]),
    ("b12", "allow the scope separator inside a system name", R + "model.py",
     '    if "@" in system:\n        return None',
     '    if False:\n        return None',
     ["tests.test_mapping_b658795.TenantScope.test_separator_in_scope_is_unreadable"]),
    ("b13", "report an unknown effect's answer fields as an empty list (F5)", R + "answer.py",
     '        if not efs or any(view[name] is None for view in views):',
     '        if False:',
     ["tests.test_mapping_b658795.TicketIds.test_missing_receipt_is_unknown_not_absent"]),
    ("r1", "split on '@' without a declared tenant key (review finding 1)", R + "model.py",
     '    return scope.split("@", 1)[0] if tenant_scoped else scope',
     '    return scope.split("@", 1)[0]',
     ["tests.test_review_b658795.Review.test_1_lookalike_service_does_not_inherit_r6_under_old_mapping"]),
    ("r2", "report an unstated answer field as an empty list (review finding 2)", R + "answer.py",
     '    return values or None',
     '    return values',
     ["tests.test_review_b658795.Review.test_2_established_effect_without_ticket_id_is_not_an_empty_list"]),
    ("r3", "call it a conflict only when every effect conflicts (review finding 3)", R + "answer.py",
     '        out["status"] = "conflict" if any(v["count"] == "conflict" for v in views) else "established"',
     '        out["status"] = "conflict" if all(v["count"] == "conflict" for v in views) else "established"',
     ["tests.test_review_b658795.Review.test_3_one_conflicting_effect_makes_the_answer_a_conflict"]),
    ("r4", "count executions of any issuing system (review finding 4)", R + "answer.py",
     '                and (not t.action_systems or system_of(key[0], ts) in t.action_systems))',
     '                and True)',
     ["tests.test_review_b658795.Review.test_4_executions_are_those_of_the_declared_issuing_system"]),
]

# Not a mutant: removing the UNRESOLVED/KEYLESS guard in query() (review finding 4,
# second half) cannot change any output, because build() never creates an R5
# relation whose target scope is unresolved: such a reference becomes a loss
# ("reference with unresolved scope"). The guard stays as defense in depth and
# test_4b pins the observable behaviour; a mutant no input can kill is not kept.


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
