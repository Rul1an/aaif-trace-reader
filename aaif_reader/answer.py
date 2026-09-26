"""Answers per (question, subject), DESIGN.md sections 1, 5 and 6.

Status values are IC-13's: established, unknown, conflict, not_answered,
not_evaluated. Contract states that are not statuses (applicability
unresolved, decision unknown, correlation unresolved) are answer fields.
"""

from __future__ import annotations

import json

from .model import KEYLESS, Tables, canon


def k(key):
    return list(key)


def _losses_for(t: Tables, keys):
    keys = set(keys)
    out = {canon([k(l["record"]) if l["record"] else None, l["what"]]) for l in t.losses if l["record"] in keys}
    return [json.loads(x) for x in sorted(out)]


def _basis(t: Tables, keys, rels=()):
    locs = set()
    for key in keys:
        locs |= t.entities.get(key, {}).get("locators", set())
    for r in rels:
        locs |= t.relations[r]["locators"]
    return sorted(l.render() for l in locs)


def _entry(question, subject, status, answer, missing=(), conflicts=(), losses=(), basis=(), **extra):
    e = {
        "question": question,
        "subject": k(subject),
        "status": status,
        "answer": answer,
        "missing": sorted(missing),
        "conflicts": list(conflicts),
        "losses": list(losses),
        "basis": list(basis),
    }
    e.update(extra)
    return e


def _rels(t: Tables, rel, *, src=None, tgt=None):
    return sorted(
        (r for r in t.relations if r[0] == rel and (src is None or r[1] == src) and (tgt is None or r[2] == tgt)),
        key=canon,
    )


def _of_kind(t: Tables, kind):
    return sorted((key for key, e in t.entities.items() if e["kind"] == kind), key=canon)


def continuity(t: Tables):
    out = []
    conversations = {r[2] for r in t.relations if r[0] == "R1"} | set(_of_kind(t, "conversation"))
    for conv in sorted(conversations, key=canon):
        rels = _rels(t, "R1", tgt=conv)
        turns = sorted({r[1] for r in rels}, key=canon)
        memberships = [
            {"turn": k(r[1]), "methods": sorted(t.relations[r]["methods"]), "deliveries": len(t.relations[r]["locators"])}
            for r in rels
        ]
        out.append(_entry(
            "continuity", conv, "established" if turns else "unknown",
            {"turns": [k(x) for x in turns], "memberships": memberships, "order": "not_answered",
             "order_reason": "no ordering relation among R1 to R6; timestamps and span trees do not establish order (contract line 91)",
             "state": "not_answered"},
            missing=[] if turns else ["turns carrying this conversation identity (R1)"],
            losses=_losses_for(t, turns + [conv]),
            basis=_basis(t, turns, rels),
        ))
    for turn in _of_kind(t, "turn"):
        if not _rels(t, "R1", src=turn):
            out.append(_entry(
                "continuity", turn, "unknown", {"membership": "unknown"},
                missing=["conversation identity for this turn (R1); none is synthesized (contract line 47)"],
                losses=_losses_for(t, [turn]), basis=_basis(t, [turn]),
            ))
    return out


def calls(t: Tables):
    out = []
    for turn in _of_kind(t, "turn"):
        rels = _rels(t, "R2", tgt=turn)
        mcs = sorted({r[1] for r in rels}, key=canon)
        out.append(_entry(
            "calls", turn, "established" if mcs else "unknown",
            {"calls": [_call_view(t, x) for x in mcs]},
            missing=[] if mcs else ["model call records referencing this turn (R2); unexported calls are unknown, not zero"],
            losses=_losses_for(t, mcs + [turn]),
            basis=_basis(t, mcs + [turn], rels),
        ))
    return out


def _call_view(t: Tables, call):
    """IC-6 and IC-7: one logical call; attempts are observations on it.

    The outcome is established only by an exported success; a call known only
    from a failure record exists, with outcome and usage unknown (C3). Usage is
    reported per aggregation level and never summed across levels (C5).
    """
    recs = list(t.call_records.get(call, {}).values())
    outcomes = {r["outcome"] for r in recs}
    levels: dict = {}
    for r in recs:
        for level, value in r["counters"].items():
            levels.setdefault(level, []).append(value)
    declared = any(r["declared"] for r in recs)
    usage = {"status": "unknown", "levels": {lv: sorted(vs, key=canon) for lv, vs in sorted(levels.items())}}
    if "success" in outcomes:
        call_level = levels.get("call", [])
        only_call = set(levels) == {"call"}
        if (only_call or (declared and call_level)) and call_level and "unknown" not in call_level:
            distinct = sorted(set(call_level))
            usage["status"] = "established" if len(distinct) == 1 else "conflict"
            if len(distinct) == 1:
                usage["value"] = distinct[0]
    return {"call": k(call), "outcome": "succeeded" if "success" in outcomes else "unknown", "usage": usage}


def approvals(t: Tables):
    out = []
    proposals = set(_of_kind(t, "proposed_action")) | {r[2] for r in t.relations if r[0] in ("R4", "R5")}
    for p in sorted(proposals, key=canon):
        drels = _rels(t, "R4", tgt=p)
        erels = _rels(t, "R5", tgt=p)
        decisions = sorted({r[1] for r in drels}, key=canon)
        executions = sorted({r[1] for r in erels}, key=canon)
        items = []
        for ex in executions:
            refs = [r[2] for r in _rels(t, "R5-decision", src=ex) if r[2] in decisions]
            if not decisions:
                items.append({"execution": k(ex), "decision": "unknown"})
            elif len(refs) == 1:
                verdict = _decision_verdict(t, refs[0])
                items.append({"execution": k(ex), "followed": k(refs[0]), "finding": verdict})
            else:
                items.append({"execution": k(ex), "finding": "unresolved"})
        conflicts = [k(d) for d in decisions if len(t.contents.get(d, {})) > 1]
        extra = {
            "decision_count": len(decisions),
            "decisions_recorded": [{"decision": k(d), "outcome": _outcome(t, d)} for d in decisions],
            "enforcement": "unknown",
            "executed": "established" if executions else "unknown",
            "relations": items,
        }
        if len(decisions) >= 2 or (decisions and any("followed" not in i for i in items)):
            extra["applicability"] = "unresolved"
        out.append(_entry(
            "approvals", p, "established" if p in t.entities else "unknown",
            {"decisions": [k(d) for d in decisions], "executions": [k(e) for e in executions]},
            missing=[] if p in t.entities else ["the proposed action record itself"],
            conflicts=conflicts,
            losses=_losses_for(t, [p] + decisions + executions),
            basis=_basis(t, [p] + decisions + executions, drels + erels),
            **extra,
        ))
    return out


def _outcome(t, decision):
    outcomes = set(t.decision_outcomes.get(decision, {}).values())
    if len(outcomes) > 1:
        return "conflict"
    return next(iter(outcomes)) if outcomes else "unknown"


def _decision_verdict(t, decision):
    """IC-8: a referenced denial is inconsistent_with_decision, a referenced
    approval consistent (this reader's symmetric reading). The outcome field and
    its values come from the mapping; anything else leaves the finding unresolved."""
    outcome = _outcome(t, decision)
    if outcome == "denied":
        return "inconsistent_with_decision"
    if outcome == "approved":
        return "consistent"
    return "unresolved"


def _effect_view(t: Tables, ef):
    variants = t.contents.get(ef, {})
    locs = sorted(l.render() for s in variants.values() for l in s)
    if len(variants) > 1:
        return {"effect": k(ef), "count": "conflict", "deliveries": len(locs)}, ef
    return {"effect": k(ef), "count": 1, "deliveries": len(locs)}, None


def effects(t: Tables):
    out = []
    correlated = set()
    for ex in _of_kind(t, "tool_execution"):
        rels = _rels(t, "R6", src=ex)
        efs = sorted({r[2] for r in rels}, key=canon)
        correlated |= set(efs)
        views, conflicts = [], []
        for ef in efs:
            v, c = _effect_view(t, ef)
            views.append(v)
            if c:
                conflicts.append(k(c))
        if not efs:
            status = "unknown"
        elif all(v["count"] == "conflict" for v in views):
            status = "conflict"
        else:
            status = "established"
        out.append(_entry(
            "effects", ex, status,
            {"effects": views, "execution": "established"},
            missing=[] if efs else ["an external effect correlated to this execution (R6); a missing receipt makes the effect unknown, not absent (contract line 108)"],
            conflicts=conflicts,
            losses=_losses_for(t, [ex] + efs),
            basis=_basis(t, [ex] + efs, rels),
        ))
    for ef in _of_kind(t, "external_effect"):
        if ef in correlated:
            continue
        v, c = _effect_view(t, ef)
        out.append(_entry(
            "effects", ef, "conflict" if c else "established",
            {"effects": [v], "correlation": "unresolved"},
            missing=["a tool execution sharing this receipt's scoped correlation key (R6)"],
            conflicts=[k(c)] if c else [],
            losses=_losses_for(t, [ef]),
            basis=_basis(t, [ef]),
        ))
    return out


def all_entries(t: Tables):
    entries = continuity(t) + calls(t) + approvals(t) + effects(t)
    return sorted(entries, key=lambda e: canon([e["question"], e["subject"]]))


def unplaced_losses(t: Tables):
    """Losses not attached to any record, such as unknown record kinds (C17)."""
    return sorted({l["what"] for l in t.losses if l["record"] is None})


__all__ = ["all_entries", "unplaced_losses", "KEYLESS"]
