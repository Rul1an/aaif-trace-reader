# Comparator results at kit b6587950, 6 October 2026

First run of the DESIGN section 7 comparator (`aaif_compare`, revision 8), on two existing runs.
Nothing was rerun for this record: both inputs are committed reports.

| Input | Against the kit's expected answers | Against the other reader |
| --- | --- | --- |
| `results/b658795-repaired/verified-run` (reader at 59b3a06) | 6 of 6 cases; 14 of 14 fields, plus 6 by-construction `action` fields | 6 of 6 cases; 14 of 14 fields, plus 6 by-construction fields |
| `results/b658795` (frozen run, reader 2d7d3ba) | 5 of 6 cases; 13 of 14 fields: `effects-receipt-missing` reports `[]` where `null` is expected (FINDINGS F5) | not compared (no `--other` given) |

The frozen run is the comparator's positive control on real data: it finds F5 on its own, with
no normalisation, which the first hand-written comparison did not. Before scoring, the comparator
also projects a synthetic all-unknown run for every positive case and refuses to score if any
field comes out equal to its positive expected answer. That control was checked field by field
after an independent review showed a whole-case version would not have caught a wrong `effect`
mapping.

## Inputs

- Kit expected answers at `b6587950986eb4ec501e080cc9730fd21dcb69fa`, fetched with
  `scripts/fetch_kit_at.sh`; digests in each comparison's `inputs.expected`.
- Projection `projections/kit-b658795.json`: how this reader's `query` section and signature
  rows map onto the kit's fields. It is a declared input, not code.
- The other reader's answers: imran-siddique's Rust reader, `comparison.json` at
  [agentrust-io/agentrust-telemetry@49727d4](https://github.com/agentrust-io/agentrust-telemetry/blob/49727d483de0c4c96c61e0a5b2b1ed918abb4f39/interop/aaif-trace-model/results/2026-10-05/comparison.json),
  sha256 `fb86f8c0e1d3e5a269a7eac84d4027c566e72aaa2c9d3d5c20dd80f0f333b147`; its rows for this
  kit revision only. Saved locally under `inputs/` (not committed), as the kit is.

## Reproduce

```sh
scripts/fetch_kit_at.sh b6587950986eb4ec501e080cc9730fd21dcb69fa
mkdir -p inputs/other-reader-49727d483de0c4c96c61e0a5b2b1ed918abb4f39
curl -sL -o inputs/other-reader-49727d483de0c4c96c61e0a5b2b1ed918abb4f39/comparison.json \
  https://raw.githubusercontent.com/agentrust-io/agentrust-telemetry/49727d483de0c4c96c61e0a5b2b1ed918abb4f39/interop/aaif-trace-model/results/2026-10-05/comparison.json
python3 -m aaif_compare --kit b6587950986eb4ec501e080cc9730fd21dcb69fa \
  --run results/b658795-repaired/verified-run --expected inputs/expected-b6587950986eb4ec501e080cc9730fd21dcb69fa \
  --projection projections/kit-b658795.json \
  --other inputs/other-reader-49727d483de0c4c96c61e0a5b2b1ed918abb4f39/comparison.json --out OUT.json
python3 -m aaif_compare --kit b6587950986eb4ec501e080cc9730fd21dcb69fa \
  --run results/b658795 --expected inputs/expected-b6587950986eb4ec501e080cc9730fd21dcb69fa \
  --projection projections/kit-b658795.json --out OUT-frozen.json   # exits 1: F5
```

Both outputs are byte-identical to the committed files; CI checks the first.

## What this does and does not show

Shows: on these six synthetic cases this reader's answers and the `actual` column of the other
reader's own published comparison are the same on every kit field, and this reader matches the kit.
The other side is that comparison file, not the other reader's raw report. The two tables are kept apart and never summed into one score.

Does not show:
- independent interpretation of the links: both readers apply the kit's declared R1/R5/R6
  mapping, so agreement on those joins comes from one shared input;
- a blind result: both readers were repaired after the expected answers were known;
- anything beyond the kit's projected fields: full reports are not compared field by field,
  because the two readers' report formats differ;
- anything about real exports or real effects. Task 7's runtime-export cases remain open.
