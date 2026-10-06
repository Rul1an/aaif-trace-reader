# Rerun of AAIF O&T PR #57 at kit 4a028675ef

Kit: `4a028675ef9b5727e614762df305f5f037b04b98`. Contract: v0.7-draft
(`e82abf1e58b066c586c25767edfba862c4ebd027`). Reader: `951e57e` (basis registry
revision 2, mapping `mappings/test-kit-4a02867.json`). Written with an AI coding
assistant, Claude Opus 5.5, directed and reviewed by the maintainer.

**Frozen before any expected answer at this kit revision was opened.** The
`expected.json` files were fetched and hashed (`inputs.sha256.json`); their
contents have not been read. `run.py` and `generate.py` were not fetched. The
kit README states the intended outcome of each case, so this run is
expected-file-blind, not answer-blind.

## What changed in the kit, from the files a reader may read

- The four `records.otlp.json` and the trust key are byte-identical to 8fa732e.
- `basis.json` now lists the checks each case asks for. The pair's
  `answer_follows` is deep dive §3.3 (#32) with v0.7 named under `outside`, and
  `effect_correlation_follows` puts effect correlation under issue #42 and v0.7
  section 6. The effects cases ask for `effect_correlation` only.
- `test-kit/mapping.md` declares R1 and R5 as attribute-reference and R6 as
  external-correlation-key, deduplicated on `receipt.id` within
  `test-ticket-service`, and says the agent's `evidence.externally_verified` is a
  claim, not a link method or a verification result.

## Results, correlation and signature reported separately

| Case | Checks asked | Effect correlation (contract reader) | Receipt signature (separate check) |
| --- | --- | --- | --- |
| receipt twice | effect_correlation | established: one effect `R-1`, two deliveries | not asked |
| receipt missing | effect_correlation | execution established, effect unknown (R6 missing) | not asked |
| pair verifies | effect_correlation, receipt_signature | established: one effect `R-7` | valid |
| pair fails | effect_correlation, receipt_signature | established: one effect `R-7` | invalid |

The two pair cases get the same correlation answer: the signature does not
decide correlation under v0.7 (contract line 112). The signature check rebuilds
the README's 126-byte input for R-7 (sha256 `194b732e…`) and verifies it under
the supplied test key (sha256 `7e2cca85…`). Validity under a synthetic key is
not evidence of a real service or effect.

`evidence.externally_verified` and `receipt.signature` stay unplaced in the
contract reader and are reported as losses; neither is read as a result.

## Limits kept from earlier runs

- F4: the execution has no native id, so it is keyless, and R6 runs through the
  proposal's `action.id`; the scope of `receipt.action_id` (`support-agent`) is
  this reader's declaration, consistent with mapping.md's single-agent statement.
- The report carries effect identity and count, not a list of ticket ids.
- The per-check `<check>_follows` key is read from the kit's basis files; the
  kit's TEMPLATE describes `basis.json` as naming "the checks it asks for" but
  does not spell out that key. It is recorded here as this reader's reading.

## Verification

`tests.log`: 73 tests pass. `mutants.log`: 22/22 must-fail mutants killed by an
assertion failure, including b1 to b6 for the per-check gate and the R6 source
scope. The frozen 8fa732e reports reproduce as identical JSON under this reader.

## Comparison with the expected answers (after the freeze at c298e7d)

Opened after `c298e7d` was pushed. Field by field (`comparison.json`); no
whole-case pass is claimed.

| Case | action | effect | confirmed_tickets | receipt_signature_verified |
| --- | --- | --- | --- | --- |
| receipt twice | match | match (confirmed) | not scored | not asked, not expected |
| receipt missing | match | match (unconfirmed) | not scored (kit: null) | not asked, not expected |
| pair fails | match | match (confirmed) | not scored | match (false) |
| pair verifies | match | match (confirmed) | not scored | match (true) |

- `effect`: the reader says `established` / `unknown`; the kit says `confirmed` /
  `unconfirmed`. Both words are the contract's own (lines 108 and 109: "one
  confirmed effect"; a missing observation is unknown, "creation unconfirmed").
- `confirmed_tickets`: the report carries effect identity (`receipt.id`) and a
  count, not ticket ids. It shows one distinct effect where the kit lists one
  ticket and none where the kit gives `null`, but the list itself is not in the
  report and was not reconstructed after the freeze.
- The kit's `externally_verified` field (8fa732e) is gone; the signature result
  is now its own field, which is what this reader reports separately.
