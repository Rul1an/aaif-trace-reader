# aaif-trace-reader

An independently implemented reader for the AAIF Observability and Traceability WG's Agent Behavior Trace Model, written in Python from the contract text and the shared fixtures only. It is one of the two readers for [aaif/wg-observability-and-traceability#45](https://github.com/aaif/wg-observability-and-traceability/issues/45).

Status on 2026-10-06: **bounded PR #57 known-answer repair validation complete.**
The six cases at kit `b658795` now match effect and ticket answers, with signatures
checked separately in the two pair cases. The old frozen result remains five of
six ticket matches; it is not rewritten as a pass. See
[the repair run](results/b658795-repaired/README.md) for source pins, command,
raw reports, per-field comparison and limitations. The latest reader repairs
were made after expected answers were known; this is not a blind evaluation.
The general DESIGN section 7 comparator, full cross-reader comparison and runtime
exports remain open. This does not complete WG Task 7.


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
