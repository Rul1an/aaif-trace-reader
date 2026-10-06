"""Four tables and one key, DESIGN.md section 4.

All inputs are loaded before any query runs (IC-1), and every answer is a set
query over the tables. Nothing here depends on the order records arrived in:
outputs are sorted by their canonical form.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .parse import Locator, SpanRecord

METHODS = ("span-link", "attribute-reference", "causal-flag", "external-correlation-key")
KEYLESS = "KEYLESS"
UNRESOLVED = "UNRESOLVED"


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def render_value(tv):
    """A typed value in report form: [type, value], never a bare coerced value."""
    tag = tv[0]
    if tag == "null":
        return ["null"]
    if tag in ("array",):
        return ["array", [render_value(v) for v in tv[1]]]
    if tag == "object":
        return ["object", [[k, render_value(v)] for k, v in tv[1]]]
    return [tag, tv[1]]


@dataclass
class Tables:
    entities: dict = field(default_factory=dict)       # key -> {"kind", "locators", "keyless"}
    observations: dict = field(default_factory=dict)   # (key, field, typed) -> set(Locator)
    relations: dict = field(default_factory=dict)      # (rel, src, tgt) -> {"methods": set, "locators": set}
    losses: list = field(default_factory=list)         # dicts
    contents: dict = field(default_factory=dict)       # key -> {content_canon: set(Locator)}
    answer_fields: dict = field(default_factory=dict)  # kind -> {answer name: attribute}, from the mapping
    record_key: dict = field(default_factory=dict)     # Locator -> key
    decision_outcomes: dict = field(default_factory=dict)  # key -> {content_canon: "denied"|"approved"|"other:<v>"}
    call_records: dict = field(default_factory=dict)       # key -> {content_canon: {"outcome", "counters", "declared"}}


def _match(rule, name: str) -> bool:
    spec = rule["span_name"]
    if "exact" in spec:
        return name == spec["exact"]
    if "prefix" in spec:
        return name.startswith(spec["prefix"])
    return False


def _scope(mapping, rec: SpanRecord):
    """The issuing system, qualified by the tenant where the mapping names a
    tenant attribute and the record carries one (identity rule 4, line 49).

    A qualified scope renders system@tenant; with a tenant key declared, a
    system or tenant containing '@' is unreadable, so the rendering is never
    ambiguous. Without a tenant key the scope is the system, as before.
    """
    s = mapping["scope"]
    if s.get("from") != "resource_attribute":
        return None
    v = rec.resource.get(s["key"])
    if not (v and v[0] == "str" and v[1]):
        return None
    system = v[1]
    tkey = s.get("tenant_key")
    if tkey is None:
        return system
    if "@" in system:
        return None
    tv = rec.resource.get(tkey)
    if tv is None:
        return system
    if not (tv[0] == "str" and tv[1]) or "@" in tv[1]:
        return None
    return f"{system}@{tv[1]}"


def system_of(scope):
    return scope.split("@", 1)[0] if scope else None


def tenant_of(scope):
    return scope.split("@", 1)[1] if scope and "@" in scope else None


def _target_scope(spec, source_scope):
    if spec.get("same_as_source"):
        return source_scope
    if "declared" in spec:
        if spec.get("tenant") == "same_as_source":
            if source_scope is None:
                return None
            tenant = tenant_of(source_scope)
            return spec["declared"] + (f"@{tenant}" if tenant else "")
        return spec["declared"]
    return None


def _content(rec: SpanRecord) -> str:
    """Record content minus declared delivery fields (DESIGN.md section 4 dedup rule)."""
    return canon({
        "name": rec.name,
        "resource": [[k, render_value(v)] for k, v in sorted(rec.resource.items())],
        "attrs": [[k, render_value(v)] for k, v in sorted(rec.attrs.items())],
    })


def build(records: list[SpanRecord], mapping: dict) -> Tables:
    t = Tables()
    t.answer_fields = {r["kind"]: r["answer_fields"] for r in mapping["entities"] if r.get("answer_fields")}
    defaults = mapping.get("default_methods", {})
    pending_keyless = []   # (rec, rule, scope)
    correlations = []      # (rel, key_triple, role, owner_key or rec, locator)

    relrule = mapping.get("relationship_records")
    for rec in records:
        if relrule and _match(relrule, rec.name):
            _relationship_record(t, rec, relrule, _scope(mapping, rec), defaults)
            continue
        rule = next((r for r in mapping["entities"] if _match(r, rec.name)), None)
        if rule is None:
            t.losses.append({"locator": rec.locator, "record": None, "what": f"unknown record kind {rec.name!r}", "question": None})
            continue
        scope = _scope(mapping, rec)
        placed = set(rule.get("observations", []))
        if rule["native_id"]:
            placed.add(rule["native_id"])
        placed |= {r["attribute"] for r in rule.get("references", [])}
        placed |= {c["attribute"] for c in rule.get("correlation_keys", [])}
        if rule.get("outcome"):
            placed.add(rule["outcome"]["attribute"])
        if rule.get("attempt_outcome"):
            placed.add(rule["attempt_outcome"]["attribute"])
        placed |= {c["attribute"] for c in rule.get("usage_counters", [])}

        nid = None
        if rule["native_id"]:
            v = rec.attrs.get(rule["native_id"])
            if v and v[0] == "str" and v[1]:
                nid = v[1]
        if rule["native_id"] is None or nid is None:
            pending_keyless.append((rec, rule, scope, placed))
            continue
        key = (scope if scope is not None else UNRESOLVED, rule["kind"], nid)
        _place(t, rec, rule, key, scope, placed, defaults, correlations)

    # Keyless records are rendered by a display handle (DESIGN.md section 4,
    # revision 7): the least of the record's own outgoing references, and an
    # ordinal in the canonical order of content. Never a locator, never a hash,
    # and it joins nothing (identity rule 2).
    groups: dict = {}
    for rec, rule, scope, placed in pending_keyless:
        groups.setdefault((rule["kind"], _anchor(rec, rule, scope)), []).append((rec, rule, scope, placed))
    for (kind, anchor), members in sorted(groups.items()):
        members.sort(key=lambda m: _content(m[0]))
        for i, (rec, rule, scope, placed) in enumerate(members, 1):
            key = (KEYLESS, kind, f"{anchor}#{i}")
            t.losses.append({"locator": rec.locator, "record": key, "what": f"no native id ({rule['native_id'] or 'none mapped'}); kept keyless, joins nothing", "question": _question_for(kind)})
            _place(t, rec, rule, key, scope, placed, defaults, correlations)

    # R6 by shared scoped correlation key (IC-10): execution side x effect side.
    by_key: dict = {}
    for rel, ckey, kind, owner, loc in correlations:
        by_key.setdefault((rel, ckey), {"tool_execution": set(), "external_effect": set()}).setdefault(kind, set()).add((owner, loc))
    for (rel, ckey), sides in by_key.items():
        method = defaults.get(rel)
        for ex, exloc in sides.get("tool_execution", ()):
            for ef, efloc in sides.get("external_effect", ()):
                if method not in METHODS:
                    t.losses.append({"locator": efloc, "record": ef, "what": f"{rel} correlation without an established method", "question": "effects"})
                    continue
                slot = t.relations.setdefault((rel, ex, ef), {"methods": set(), "locators": set()})
                slot["methods"].add(method)
                slot["locators"].update({exloc, efloc})
    return t


def _relationship_record(t, rec: SpanRecord, rr, scope, defaults):
    """An exported relationship record (contract section 4, IC-2).

    The method comes from the record if it names one of the four; a present
    but unrecognized method is not established and never falls back to the
    default; an absent method uses the mapping default for the kind, if any.
    """
    def s(name):
        v = rec.attrs.get(rr[name])
        return v[1] if v and v[0] == "str" and v[1] else None

    kind, sk, sid, tk, tid = s("kind"), s("source_kind"), s("source_id"), s("target_kind"), s("target_id")
    src = (scope if scope is not None else UNRESOLVED, sk, sid) if sk and sid else None
    if not (kind and src and tk and tid):
        t.losses.append({"locator": rec.locator, "record": src, "what": "relationship record without kind, source or target", "question": None})
        return
    q = _question_for(sk)
    if scope is None:
        t.losses.append({"locator": rec.locator, "record": src, "what": f"{kind} relationship record with unresolved scope", "question": q})
        return
    raw_method = rec.attrs.get(rr["method"])
    if raw_method is not None:
        value = raw_method[1] if raw_method[0] == "str" else raw_method
        if value not in METHODS:
            t.losses.append({"locator": rec.locator, "record": src, "what": f"{kind} relationship not established: method {value!r} is outside the four named methods", "question": q})
            return
        method = value
    else:
        method = defaults.get(kind)
        if method not in METHODS:
            t.losses.append({"locator": rec.locator, "record": src, "what": f"{kind} relationship not established: no method on the record and no mapping default", "question": q})
            return
    tgt = (scope, tk, tid)
    slot = t.relations.setdefault((kind, src, tgt), {"methods": set(), "locators": set()})
    slot["methods"].add(method)
    slot["locators"].add(rec.locator)


def _anchor(rec: SpanRecord, rule, scope) -> str:
    anchors = []
    for ref in rule.get("references", []):
        v = rec.attrs.get(ref["attribute"])
        tscope = _target_scope(ref["target_scope"], scope)
        if v and v[0] == "str" and v[1] and scope is not None and tscope is not None:
            anchors.append(f"{ref['relation']}:{tscope}/{ref['target_kind']}/{v[1]}")
    return min(anchors) if anchors else "unanchored"


def _question_for(kind):
    return {
        "turn": "continuity",
        "conversation": "continuity",
        "model_call": "calls",
        "proposed_action": "approvals",
        "approval_decision": "approvals",
        "tool_execution": "effects",
        "external_effect": "effects",
    }.get(kind)


def _place(t, rec, rule, key, scope, placed, defaults, correlations):
    ent = t.entities.setdefault(key, {"kind": rule["kind"], "locators": set(), "keyless": key[0] == KEYLESS})
    ent["locators"].add(rec.locator)
    t.record_key[rec.locator] = key
    t.contents.setdefault(key, {}).setdefault(_content(rec), set()).add(rec.locator)
    q = _question_for(rule["kind"])

    if scope is None:
        t.losses.append({"locator": rec.locator, "record": key, "what": "scope not readable; record joins nothing", "question": q})

    oc = rule.get("outcome")
    if oc:
        v = rec.attrs.get(oc["attribute"])
        val = v[1] if v and v[0] == "str" else None
        norm = "denied" if val == oc.get("denied") else "approved" if val == oc.get("approved") else f"other:{val}"
        t.decision_outcomes.setdefault(key, {})[_content(rec)] = norm

    ao = rule.get("attempt_outcome")
    if ao or rule.get("usage_counters"):
        outcome = None
        if ao:
            v = rec.attrs.get(ao["attribute"])
            val = v[1] if v and v[0] == "str" else None
            outcome = "success" if val == ao.get("success") else "failure" if val == ao.get("failure") else None
        counters = {}
        for c in rule.get("usage_counters", []):
            if c["attribute"] not in rec.attrs:
                continue
            v = rec.attrs[c["attribute"]]
            # IC-7 / DESIGN.md section 3: counters are JSON integers only; a
            # float, a string or a negative value is a loss and the counter unknown.
            if v[0] == "int" and v[1] >= 0:
                counters[c["level"]] = v[1]
            else:
                counters[c["level"]] = "unknown"
                t.losses.append({"locator": rec.locator, "record": key, "what": f"usage counter {c['attribute']!r} is not a non-negative integer ({v[0]}); counter unknown", "question": q})
        t.call_records.setdefault(key, {})[_content(rec)] = {
            "outcome": outcome, "counters": counters, "declared": bool(rule.get("aggregation_declared")),
        }

    for name in rule.get("observations", []):
        if name in rec.attrs:
            t.observations.setdefault((key, name, rec.attrs[name]), set()).add(rec.locator)

    for name in sorted(set(rec.attrs) - placed):
        t.losses.append({"locator": rec.locator, "record": key, "what": f"attribute {name!r} has no placement in the mapping", "question": q})
    if rec.links:
        t.losses.append({"locator": rec.locator, "record": key, "what": f"{rec.links} span link(s) with no mapped relationship", "question": q})

    for ref in rule.get("references", []):
        v = rec.attrs.get(ref["attribute"])
        if not v or v[0] != "str" or not v[1]:
            continue
        rel = ref["relation"]
        tscope = _target_scope(ref["target_scope"], scope)
        if scope is None or tscope is None:
            t.losses.append({"locator": rec.locator, "record": key, "what": f"{rel} reference with unresolved scope", "question": q})
            continue
        method = defaults.get(rel)
        if method not in METHODS:
            t.losses.append({"locator": rec.locator, "record": key, "what": f"{rel} reference without an established method", "question": q})
            continue
        tgt = (tscope, ref["target_kind"], v[1])
        slot = t.relations.setdefault((rel, key, tgt), {"methods": set(), "locators": set()})
        slot["methods"].add(method)
        slot["locators"].add(rec.locator)

    for c in rule.get("correlation_keys", []):
        v = rec.attrs.get(c["attribute"])
        if not v or v[0] != "str" or not v[1]:
            continue
        if "source_scope" in c and system_of(scope) != c["source_scope"]:
            t.losses.append({"locator": rec.locator, "record": key, "what": f"{c['relation']} correlation key outside the mapping's declared source scope", "question": q})
            continue
        kscope = _target_scope(c["key_scope"], scope)
        if kscope is None:
            t.losses.append({"locator": rec.locator, "record": key, "what": f"{c['relation']} correlation key with unresolved scope", "question": q})
            continue
        correlations.append((c["relation"], (kscope, c["key_kind"], v[1]), rule["kind"], key, rec.locator))
