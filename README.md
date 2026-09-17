# aaif-trace-reader

An independently implemented reader for the AAIF Observability and Traceability WG's Agent Behavior Trace Model, written in Python from the contract text and the shared fixtures only. It is one of the two readers for [aaif/wg-observability-and-traceability#45](https://github.com/aaif/wg-observability-and-traceability/issues/45).

Status on 2026-09-17: **design only**. `DESIGN.md` is the pre-implementation record: the interpretation choices, the parsing rules, the acceptance cases and the must-fail controls, pinned against contract PR #51 at head `1af33bab242f1f5ab3060ef54128014748650f7b` before any fixture is read by code. No reader exists yet; nothing here is an interoperability result.

The first implementation commit will name its language version, tooling and model family, and the interpretation-register version it implements. Later changes to the design land as revisions with a reason, never as silent edits.

License: Apache-2.0.
