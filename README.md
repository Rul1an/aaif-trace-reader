# aaif-trace-reader

An independently implemented reader for the AAIF Observability and Traceability WG's Agent Behavior Trace Model, written in Python from the contract text and the shared fixtures only. It is one of the two readers for [aaif/wg-observability-and-traceability#45](https://github.com/aaif/wg-observability-and-traceability/issues/45).

Status on 2026-09-27: **bounded PR #57 rerun complete; partial comparison only.**
The v0.7 contract reader now accepts explicit per-case basis metadata. Results
at kit `8fa732e` were frozen before expected-answer inspection; a later manual
comparison found narrow effects agreement, an unresolved `externally_verified`
meaning question, and our own ticket-list representation gap. The two #32 cases
are outside the contract reader's scope, not passing cases. A separate
README-derived Ed25519 check distinguishes their signatures. See
[the run record](results/8fa732e/README.md) and [basis interpretation](BASIS-RERUN.md).
The general DESIGN section 7 comparator and other-reader comparison remain undone.


Tooling: the original reader was written with Claude Opus 5.5, directed and reviewed by the maintainer. The basis gate, separate signing check and bounded rerun were implemented with Codex. Frozen run metadata preserves the original reader attribution; BASIS-RERUN.md records the extension separately. It implements the interpretation register of DESIGN.md revision 7 against contract v0.7-draft (PR #51 head `e82abf1`). The two deviations the first slice had from revision 6 (`FINDINGS.md` D1, D2) are resolved: D1 by revision 7, D2 by the implementation following section 3.

    scripts/fetch_kit.sh          # fetch the pinned kit into inputs/ and check digests
    python3 -m unittest -v tests.test_reader tests.test_cases
    python3 tests/mutants.py      # m1 to m13 and three controls; exit 0 only if all are killed
    python3 -m aaif_reader --mapping mappings/test-kit-afc26fdd.json --out OUT inputs/test-kit-*/cases/CASE/records.otlp.json

License: Apache-2.0.

The contract reader remains standard-library-only. The separate signature tests
require `cryptography==46.0.7` (the version used for this run). With it installed,
run the complete local suite with `python3 -m unittest discover -s tests -v`.
`--basis PATH/basis.json` enables the explicit scope gate; omitted, the CLI keeps
legacy contract-only operation. An out-of-scope case exits 4, not success.
The existing fetch script remains pinned to the historical afc26fdd kit.
