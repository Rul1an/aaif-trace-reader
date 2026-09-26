"""Parsing contract, DESIGN.md section 3.

Records are turned into typed values before any interpretation runs, so that the
set semantics of contract line 110 and the no-synthesis rule of line 47 hold on
values this module has already checked. Every rule here is written, not
inherited from Python's json module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

# Declared caps (DESIGN.md section 3). A breach is a processing failure for
# depth, and marks processing partial for size and counts.
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 64
MAX_RECORDS = 100_000


class ParseFailure(Exception):
    """The input is not a record set this reader will interpret."""


class CapBreach(ParseFailure):
    """A size or count cap was hit. Processing is partial, not failed (section 3)."""


@dataclass(frozen=True)
class Locator:
    input_digest: str
    member: str
    ordinal: int

    def render(self) -> str:
        return f"{self.input_digest[:12]}:{self.member}:{self.ordinal}"


def _reject_duplicates(pairs):
    seen = set()
    for key, _ in pairs:
        if key in seen:
            raise ParseFailure(f"duplicate object key {key!r}")
        seen.add(key)
    return dict(pairs)


def _reject_constant(name):
    raise ParseFailure(f"non-finite number {name}")


def _check_depth(text: str) -> None:
    """Count nesting outside strings before json sees the text.

    Python has no depth cap of its own and raises RecursionError at an
    interpreter-dependent depth, so the cap is enforced here.
    """
    depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise ParseFailure(f"nesting depth over cap {MAX_DEPTH}")
        elif ch in "]}":
            depth -= 1


def decode(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ParseFailure("leading byte order mark")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ParseFailure(f"invalid UTF-8: {exc.reason}") from exc
    if text.startswith("﻿"):
        raise ParseFailure("leading U+FEFF")
    return text


def load_json(raw: bytes):
    """Parse one input. Raises ParseFailure, never returns a partial value."""
    if len(raw) > MAX_INPUT_BYTES:
        raise CapBreach(f"input over size cap {MAX_INPUT_BYTES}")
    text = decode(raw)
    _check_depth(text)
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicates,
            parse_constant=_reject_constant,
        )
    except ParseFailure:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        # Integers over the digit limit raise ValueError, not JSONDecodeError.
        raise ParseFailure(f"not JSON: {exc}") from exc


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def typed(value):
    """Type-aware form of a parsed value, so 1, 1.0 and true stay distinct.

    Python's == treats them as equal, which would let a comparison coerce
    silently (DESIGN.md section 3, structural equality).
    """
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", repr(value))
    if isinstance(value, str):
        return ("str", value)
    if isinstance(value, list):
        return ("array", tuple(typed(v) for v in value))
    if isinstance(value, dict):
        return ("object", tuple(sorted((k, typed(v)) for k, v in value.items())))
    raise ParseFailure(f"unexpected parsed type {type(value).__name__}")


def otlp_value(anyvalue):
    """Decode one OTLP/JSON AnyValue into a typed value.

    The OTLP type tag is kept, so an intValue of "1" and a stringValue of "1"
    are different values.
    """
    if not isinstance(anyvalue, dict) or len(anyvalue) != 1:
        raise ParseFailure("AnyValue must carry exactly one typed field")
    (tag, inner), = anyvalue.items()
    if tag == "stringValue" and isinstance(inner, str):
        return ("str", inner)
    if tag == "boolValue" and isinstance(inner, bool):
        return ("bool", inner)
    if tag == "intValue":
        # OTLP/JSON encodes int64 as a decimal string; accept a JSON integer too.
        if isinstance(inner, bool):
            raise ParseFailure("intValue is a boolean")
        if isinstance(inner, int):
            return ("int", inner)
        if isinstance(inner, str) and inner.lstrip("-").isdigit():
            return ("int", int(inner))
        raise ParseFailure("intValue is not an integer")
    if tag == "doubleValue" and isinstance(inner, (int, float)) and not isinstance(inner, bool):
        return ("float", repr(float(inner)))
    if tag == "bytesValue" and isinstance(inner, str):
        return ("bytes", inner)
    if tag == "arrayValue" and isinstance(inner, dict):
        return ("array", tuple(otlp_value(v) for v in inner.get("values", [])))
    if tag == "kvlistValue" and isinstance(inner, dict):
        items = inner.get("values", [])
        return ("object", tuple(sorted((kv["key"], otlp_value(kv["value"])) for kv in items)))
    raise ParseFailure(f"unsupported AnyValue {tag}")


def attributes(raw_attrs) -> dict:
    out = {}
    for kv in raw_attrs or []:
        if not isinstance(kv, dict) or not isinstance(kv.get("key"), str) or "value" not in kv:
            raise ParseFailure("malformed attribute")
        key = kv["key"]
        if key in out:
            raise ParseFailure(f"duplicate attribute key {key!r}")
        out[key] = otlp_value(kv["value"])
    return out


@dataclass(frozen=True)
class SpanRecord:
    locator: Locator
    resource: dict
    name: str
    delivery: tuple  # typed delivery fields, kept for diagnostics only
    attrs: dict
    links: int  # span links; no link semantics are mapped in this version


DELIVERY_KEYS = ("traceId", "spanId", "parentSpanId", "startTimeUnixNano", "endTimeUnixNano")


def spans_from_otlp(raw: bytes, member: str) -> list[SpanRecord]:
    doc = load_json(raw)
    if not isinstance(doc, dict) or not isinstance(doc.get("resourceSpans"), list):
        raise ParseFailure("not an OTLP/JSON trace export")
    dig = digest(raw)
    out: list[SpanRecord] = []
    ordinal = 0
    for rs in doc["resourceSpans"]:
        resource = attributes((rs.get("resource") or {}).get("attributes"))
        for ss in rs.get("scopeSpans", []):
            for span in ss.get("spans", []):
                if not isinstance(span, dict) or not isinstance(span.get("name"), str):
                    raise ParseFailure("span without a name")
                out.append(
                    SpanRecord(
                        locator=Locator(dig, member, ordinal),
                        resource=resource,
                        name=span["name"],
                        delivery=tuple((k, typed(span.get(k))) for k in DELIVERY_KEYS),
                        attrs=attributes(span.get("attributes")),
                        links=len(span.get("links") or []),
                    )
                )
                ordinal += 1
                if len(out) > MAX_RECORDS:
                    raise CapBreach(f"record count over cap {MAX_RECORDS}")
    return out
