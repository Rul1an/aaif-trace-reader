"""DESIGN.md section 7, revision 8: compare one run with the kit's expected
answers and, in a separate table, with another reader's answers.

Rules this module enforces on itself:
- every expected case and field must be answered; silence never matches, and
  an expected answer with no fields never matches;
- values are compared strictly by type: 1 is not True, [] is not null;
- a case whose processing is not complete fails every field;
- before scoring, a synthetic all-unknown run is projected for every positive
  case (expected effect confirmed); if any field whose expected value is a
  positive answer comes out equal to it, the projection or the comparator is
  broken and nothing is scored (ControlFailed);
- a field the run reports but the expected answer lacks is recorded, never
  dropped; it does not decide a match;
- fields marked by_construction are counted apart;
- the other reader's rows must carry the exact kit revision, one row per case,
  a completed run (exit 0, one selected answer, pass not false) and an actual
  value per field; anything else is recorded and does not agree;
- agreement with the expected answers and agreement with the other reader are
  two tables with two summaries, never one score.
"""
from __future__ import annotations

import copy

ABSENT = object()
NEGATIVE = (None, False, "unconfirmed")


class ControlFailed(Exception):
    """The all-unknown control produced a positive expected answer; nothing is scored."""


def same(a, b) -> bool:
    """Equality that does not coerce: 1 != True, 1 != 1.0, [] != None."""
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return a == b


def _walk(obj, path):
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return ABSENT
        obj = obj[key]
    return obj


def project(report, signature_rows, projection):
    """The run's answer per kit field, or ABSENT where the run says nothing."""
    out = {}
    for field, spec in projection["fields"].items():
        source = spec["from"]
        if source == "report":
            value = _walk(report, spec["path"])
            if value is not ABSENT and "map" in spec and isinstance(value, str):
                value = spec["map"].get(value, value)
        elif source == "signatures":
            rows = [r for r in signature_rows or [] if spec["key"] in r]
            if not rows:
                value = ABSENT
            elif len(rows) > 1:
                value = "more than one signature row"
            else:
                value = rows[0][spec["key"]]
        elif source == "constant":
            value = spec["value"]
        else:
            raise ValueError(f"unknown projection source {source!r}")
        out[field] = value
    return out


def _case_vs_expected(case, report, signature_rows, expected, projection):
    by_construction = {f for f, s in projection["fields"].items() if s.get("by_construction")}
    fields = []
    if report is None:
        for field, exp in expected.items():
            row = {"field": field, "expected": exp, "actual": None, "match": False,
                   "reason": "case absent from the run"}
            if field in by_construction:
                row["by_construction"] = True
            fields.append(row)
        return {"case": case, "all_fields_match": False, "fields": fields, "reported_not_expected": []}
    complete = report.get("processing") == "complete"
    answers = project(report, signature_rows, projection)
    for field, exp in expected.items():
        actual = answers.get(field, ABSENT)
        row = {"field": field, "expected": exp, "actual": None if actual is ABSENT else actual}
        if field in by_construction:
            row["by_construction"] = True
        if not complete:
            row.update(match=False, reason=f"processing {report.get('processing')!r}, not complete")
        elif actual is ABSENT:
            row.update(match=False, reason="absent from the report")
        else:
            row["match"] = same(actual, exp)
            if not row["match"]:
                row["reason"] = "differs"
        fields.append(row)
    extra = [{"field": f, "actual": v} for f, v in sorted(answers.items())
             if f not in expected and v is not ABSENT]
    result = {"case": case, "all_fields_match": bool(fields) and all(f["match"] for f in fields),
              "fields": fields, "reported_not_expected": extra}
    if not fields:
        result["reason"] = "the expected answer names no field"
    return result


def _other_run_problem(row):
    if row.get("exit_code", 0) != 0:
        return f"other reader exited {row.get('exit_code')}"
    if row.get("selected_answers", 1) != 1:
        return f"other reader selected {row.get('selected_answers')} answers"
    if row.get("pass") is False:
        return "other reader reported its own case as not passing"
    return None


def _case_vs_other(case, answers, rows, our_complete, by_construction=frozenset()):
    if not rows:
        return {"case": case, "other_reader": "no row at this kit revision", "all_fields_agree": False, "fields": []}
    if len(rows) > 1:
        return {"case": case, "other_reader": "more than one row for this case", "all_fields_agree": False,
                "fields": []}
    row = rows[0]
    theirs = {f["field"]: (f["actual"] if "actual" in f else ABSENT) for f in row.get("fields", [])}
    fields = []
    for field in sorted(set(theirs) | {f for f, v in answers.items() if v is not ABSENT}):
        ours, other = answers.get(field, ABSENT), theirs.get(field, ABSENT)
        out = {"field": field, "ours": None if ours is ABSENT else ours, "theirs": None if other is ABSENT else other}
        if field in by_construction:
            out["by_construction"] = True
        if ours is ABSENT:
            out.update(agree=False, reason="only the other reader answered")
        elif field not in theirs:
            out.update(agree=False, reason="only this reader answered")
        elif other is ABSENT:
            out.update(agree=False, reason="the other reader's row has no actual value")
        else:
            out["agree"] = same(ours, other)
        fields.append(out)
    result = {"case": case, "fields": fields}
    problems = [p for p in (_other_run_problem(row),
                            None if our_complete else "this reader's processing is not complete") if p]
    if problems:
        result["run_problems"] = problems
    result["all_fields_agree"] = bool(fields) and not problems and all(f["agree"] for f in fields)
    return result


def _all_unknown(report):
    r = copy.deepcopy(report) if report else {"query": {"context": {}}}
    r["processing"] = "complete"
    q = r.setdefault("query", {})
    q.update(status="unknown", execution="unknown", ticket_ids=None, effects=[])
    return r


def control_all_unknown(reports, expected, projection):
    """Field by field: an all-unknown run must not produce any positive expected answer."""
    positive = sorted(c for c, e in expected.items() if e.get("effect") == "confirmed")
    by_construction = {f for f, s in projection["fields"].items() if s.get("by_construction")}
    leaks = []
    for c in positive:
        answers = project(_all_unknown(reports.get(c)), [], projection)
        for field, exp in expected[c].items():
            if field in by_construction or any(same(exp, n) for n in NEGATIVE) or exp == []:
                continue
            got = answers.get(field, ABSENT)
            if got is not ABSENT and same(got, exp):
                leaks.append(f"{c}.{field}")
    if leaks:
        raise ControlFailed(f"an all-unknown run yields expected positive answers: {leaks}")
    return {"positive_cases": positive, "result": "no positive expected answer from an all-unknown run, as required"}


def compare(reports, signatures, expected, projection, other_rows, kit):
    controls = {"all_unknown": control_all_unknown(reports, expected, projection)}
    vs_expected = [_case_vs_expected(c, reports.get(c), signatures.get(c, []), expected[c], projection)
                   for c in sorted(expected)]
    other_by_case = {}
    for r in other_rows:
        if r.get("revision") == kit:
            other_by_case.setdefault(r["case"], []).append(r)
    by_construction = frozenset(f for f, s in projection["fields"].items() if s.get("by_construction"))
    vs_other = [_case_vs_other(c, project(reports[c], signatures.get(c, []), projection) if c in reports else {},
                               other_by_case.get(c, []),
                               c in reports and reports[c].get("processing") == "complete", by_construction)
                for c in sorted(expected)]
    flat = [f for c in vs_expected for f in c["fields"]]
    other_flat = [f for c in vs_other for f in c["fields"]]
    return {
        "controls": controls,
        "vs_expected": {
            "cases": vs_expected,
            "summary": {
                "cases": len(vs_expected),
                "cases_all_fields_match": sum(c["all_fields_match"] for c in vs_expected),
                "fields_matched": sum(f["match"] for f in flat if not f.get("by_construction")),
                "fields_compared": sum(1 for f in flat if not f.get("by_construction")),
                "by_construction_fields_matched": sum(f["match"] for f in flat if f.get("by_construction")),
                "reported_not_expected": sum(len(c["reported_not_expected"]) for c in vs_expected),
            },
        },
        "vs_other_reader": {
            "cases": vs_other,
            "summary": {
                "cases_with_a_row": sum(1 for c in vs_other if "other_reader" not in c),
                "cases_all_fields_agree": sum(c["all_fields_agree"] for c in vs_other),
                "fields_agree": sum(f["agree"] for f in other_flat if not f.get("by_construction")),
                "fields_compared": sum(1 for f in other_flat if not f.get("by_construction")),
                "by_construction_fields_agree": sum(f["agree"] for f in other_flat if f.get("by_construction")),
            },
        },
    }
