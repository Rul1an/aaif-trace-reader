# Known-answer repair validation — 6 October 2026

Execution source and reproduction runner: `a9ad3186d157b9f8aed9a7cea68800d77b6f6287`.
Kit: `b6587950986eb4ec501e080cc9730fd21dcb69fa`; contract remains v0.7-draft.
Reader source unchanged from `3ab914a31cb013ba6760c6bab0d3a2cb56ee4733`.
Run by Codex for Roel; CPython 3.14.3, cryptography 46.0.7. Original reader
assistance is recorded in DESIGN/BASIS; this rerun and runner use Codex assistance.
The run metadata's Claude attribution describes original reader authorship, not
who executed this rerun.

This is a **known-answer repair validation**, not a blind first comparison.
The frozen `results/b658795` reports remain unchanged. Their comparison retains
F5: five of six ticket answers matched; the missing-receipt answer was `[]`
where `null` was expected. The first comparison's incorrect normalization is
recorded as a correction there. F5 and four later reader defects (F6) were fixed
before the present run.

## Reproduce

From this committed repository with Python and cryptography 46.0.7 installed:

```sh
scripts/fetch_kit_at.sh b6587950986eb4ec501e080cc9730fd21dcb69fa
python3 results/b658795-repaired/reproduce.py /tmp/aaif-repair-NEW
python3 -m unittest discover -s tests -v
python3 tests/mutants.py
```

Use a new output path. The runner checks all input hashes from the original
manifest, requires the six-case population, rejects uncommitted execution sources,
runs the CLI before its separate expected-answer comparison, and returns nonzero
for mismatches. It is a bounded script for these six cases, not the general
DESIGN section 7 comparator. Its commit pin is retained in run/comparison.json;
later documentation-only commits may change the reported HEAD on a reproduction.

## Results

- Effect correlation matches all six expected fields; missing receipt remains unknown.
- Ticket IDs match all six, including null for the missing receipt, T-2088 for the
  changed-ticket case and T-1042 for the tenant-a query with reused P1/R-9.
- The separate signature check accepts the valid pair and rejects the invalid pair.
  Both receipts still correlate; signature validity does not authenticate tenant metadata.
- Action labels match in six cases largely by construction: the query echoes the
  requested action. Retained execution observations are separate from that match.
- 91 tests pass; see tests.log. Mutant outcomes are retained in mutants.log.

Source records are synthetic; these checks do not prove real effects, enforcement,
production identity, complete exports or whole-contract coverage. R1/R5/R6 mapping
is shared kit material, not independently invented semantics. No other reader's
implementation was imported. This does not establish full Task 7 completion:
relationship coverage, real example exports and the general comparator remain open.
