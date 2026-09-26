# aaif-trace-reader

An independently implemented reader for the AAIF Observability and Traceability WG's Agent Behavior Trace Model, written in Python from the contract text and the shared fixtures only. It is one of the two readers for [aaif/wg-observability-and-traceability#45](https://github.com/aaif/wg-observability-and-traceability/issues/45).

Status on 2026-09-26: **first implementation slice, no comparison yet.** The parser, the four tables and all four questions are implemented (standard library only), with a mapping file for the PR #57 test kit at head `afc26fdd`. The local cases that cover effects and parsing pass, and so do mutants m1, m2 and m5. The comparison against the kit's expected answers has not run: DESIGN.md section 10 step 4 requires the full case and mutant set first. `FINDINGS.md` lists what this slice found against the contract, the kit and this reader's own design, and what remains before a comparison.

Tooling: written with an AI coding assistant, Claude Opus 5.5, directed and reviewed by the maintainer. It implements the interpretation register of DESIGN.md revision 7 against contract v0.7-draft (PR #51 head `e82abf1`). The two deviations the first slice had from revision 6 (`FINDINGS.md` D1, D2) are resolved: D1 by revision 7, D2 by the implementation following section 3.

    scripts/fetch_kit.sh          # fetch the pinned kit into inputs/ and check digests
    python3 -m unittest -v tests.test_reader
    python3 -m aaif_reader --mapping mappings/test-kit-afc26fdd.json --out OUT inputs/test-kit-*/cases/CASE/records.otlp.json

License: Apache-2.0.
