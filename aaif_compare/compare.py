"""DESIGN.md section 7, revision 8: compare one run with the kit's expected
answers and, in a separate table, with another reader's answers.

Rules this module enforces on itself:
- every expected case and field must be answered; silence never matches;
- a case whose processing is not complete fails every field;
- before scoring, a synthetic all-unknown run must fail every positive case
  (expected effect confirmed); if it does not, the projection or the
  comparator is broken and nothing is scored (ControlFailed);
- a field the run reports but the expected answer lacks is recorded as a
  disagreement, never dropped;
- fields marked by_construction are counted apart;
- agreement with the expected answers and agreement with the other reader
  are two tables with two summaries, never one score.
"""
from __future__ import annotations

import copy

ABSENT = object()


class ControlFailed(Exception):
    """The all-unknown control passed a positive case; nothing is scored."""


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
            row["match"] = actual == exp
            if not row["match"]:
                row["reason"] = "differs"
        fields.append(row)
    extra = [{"field": f, "actual": v} for f, v in sorted(answers.items())
             if f not in expected and v is not ABSENT]
    return {"case": case, "all_fields_match": all(f["match"] for f in fields), "fields": fields,
            "reported_not_expected": extra}


def _case_vs_other(case, answers, other_row, by_construction=frozenset()):
    if other_row is None:
        return {"case": case, "other_reader": "no row at this kit revision", "all_fields_agree": False,
                "fields": []}
    theirs = {f["field"]: f.get("actual") for f in other_row.get("fields", [])}
    fields = []
    for field in sorted(set(theirs) | {f for f, v in answers.items() if v is not ABSENT}):
        ours = answers.get(field, ABSENT)
        row = {"field": field, "ours": None if ours is ABSENT else ours, "theirs": theirs.get(field)}
        if field in by_construction:
            row["by_construction"] = True
        if ours is ABSENT:
            row.update(agree=False, reason="only the other reader answered")
        elif field not in theirs:
            row.update(agree=False, reason="only this reader answered")
        else:
            row["agree"] = ours == theirs[field]
        fields.append(row)
    return {"case": case, "all_fields_agree": all(f["agree"] for f in fields), "fields": fields}


def _all_unknown(report):
    r = copy.deepcopy(report) if report else {"query": {"context": {}}}
    r["processing"] = "complete"
    q = r.setdefault("query", {})
    q.update(status="unknown", execution="unknown", ticket_ids=None, effects=[])
    return r


def control_all_unknown(reports, expected, projection):
    positive = sorted(c for c, e in expected.items() if e.get("effect") == "confirmed")
    passed = [c for c in positive
              if _case_vs_expected(c, _all_unknown(reports.get(c)), [], expected[c], projection)["all_fields_match"]]
    if passed:
        raise ControlFailed(f"an all-unknown run passes positive case(s) {passed}")
    return {"positive_cases": positive, "result": "failed every positive case, as required"}


def compare(reports, signatures, expected, projection, other_rows, kit):
    controls = {"all_unknown": control_all_unknown(reports, expected, projection)}
    vs_expected = [_case_vs_expected(c, reports.get(c), signatures.get(c, []), expected[c], projection)
                   for c in sorted(expected)]
    other_by_case = {r["case"]: r for r in other_rows if str(r.get("revision", "")).startswith(kit[:8])}
    by_construction = frozenset(f for f, s in projection["fields"].items() if s.get("by_construction"))
    vs_other = [_case_vs_other(c, project(reports[c], signatures.get(c, []), projection) if c in reports else {},
                               other_by_case.get(c), by_construction) for c in sorted(expected)]
    other_flat = [f for c in vs_other for f in c["fields"]]
    flat = [f for c in vs_expected for f in c["fields"]]
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
                "cases_with_a_row": sum(1 for c in vs_other if c.get("other_reader") is None),
                "cases_all_fields_agree": sum(c["all_fields_agree"] for c in vs_other),
                "fields_agree": sum(f["agree"] for f in other_flat if not f.get("by_construction")),
                "fields_compared": sum(1 for f in other_flat if not f.get("by_construction")),
                "by_construction_fields_agree": sum(f["agree"] for f in other_flat if f.get("by_construction")),
            },
        },
    }
