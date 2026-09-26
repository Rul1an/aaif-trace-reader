# aaif-trace-reader

An independently implemented reader for the AAIF Observability and Traceability WG's Agent Behavior Trace Model, written in Python from the contract text and the shared fixtures only. It is one of the two readers for [aaif/wg-observability-and-traceability#45](https://github.com/aaif/wg-observability-and-traceability/issues/45).

Status on 2026-09-26: **implementation complete for the local case set, no comparison yet.** The parser, the four tables and all four questions are implemented (standard library only). Every acceptance case in DESIGN.md section 8 (C1 to C18 with their variants) passes, and every must-fail control (m1 to m13, plus three controls) is killed by an assertion failure. The comparison against the kit's expected answers has not run; it is the next step (section 10 step 5). `FINDINGS.md` lists what building this found against the contract, the kit and this reader's own design.

Tooling: written with an AI coding assistant, Claude Opus 5.5, directed and reviewed by the maintainer. It implements the interpretation register of DESIGN.md revision 7 against contract v0.7-draft (PR #51 head `e82abf1`). The two deviations the first slice had from revision 6 (`FINDINGS.md` D1, D2) are resolved: D1 by revision 7, D2 by the implementation following section 3.

    scripts/fetch_kit.sh          # fetch the pinned kit into inputs/ and check digests
    python3 -m unittest -v tests.test_reader tests.test_cases
    python3 tests/mutants.py      # m1 to m13 and three controls; exit 0 only if all are killed
    python3 -m aaif_reader --mapping mappings/test-kit-afc26fdd.json --out OUT inputs/test-kit-*/cases/CASE/records.otlp.json

License: Apache-2.0.
