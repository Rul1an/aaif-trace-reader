# Rerun of AAIF O&T PR #57 at kit b6587950

Kit: `b6587950986eb4ec501e080cc9730fd21dcb69fa`. Contract: v0.7-draft
(`e82abf1e58b066c586c25767edfba862c4ebd027`). Reader: `2d7d3ba` (basis registry
revision 3, mapping `mappings/test-kit-b658795.json`). Written with an AI coding
assistant, Claude Opus 5.5, directed and reviewed by the maintainer.

**Frozen before any expected answer at this kit revision was opened, by the
author's statement.** The commit history shows only commit order, not when a
file was opened. The `expected.json` files were fetched and hashed
(`inputs.sha256.json`); by the author's account their contents had not been
read at freeze time. `run.py` and `generate.py` were not fetched. The
kit README states the intended outcome of each case, so this run is
expected-file-blind, not answer-blind. It is also a targeted run, not a blind
evaluation: the reader was changed for these two new cases with their records
and the README's stated outcomes in view. The four original cases' records are
byte-identical to 4a028675ef.

## Query answers (evaluation_context from basis.json), and the separate signature check

| Case | Context | Effect correlation | Ticket ids | Receipt signature |
| --- | --- | --- | --- | --- |
| action id reused in another scope | P1, test-ticket-service, tenant-a | established: `R-9` in `test-ticket-service@tenant-a` | T-1042 | not asked |
| receipt delivered twice | P1, test-ticket-service, no tenant | established: `R-1`, two deliveries | T-1042 | not asked |
| receipt missing | P1, test-ticket-service, no tenant | unknown (execution established, no R6) | `[]` in frozen output (F5 defect; actual ticket outcome unknown) | not asked |
| ticket id changed | P1, test-ticket-service, no tenant | established: `R-9` | T-2088 | not asked |
| pair fails | P1, test-ticket-service, no tenant | established: `R-7` | T-1042 | invalid |
| pair verifies | P1, test-ticket-service, no tenant | established: `R-7` | T-1042 | valid |

The tenant-b receipt (`R-9`, `T-2088`) is its own effect in
`test-ticket-service@tenant-b`, correlated to the tenant-b execution; it does
not join, replace or conflict with the tenant-a answer. Ticket ids in the pair
cases are what the receipt span states; the signature check is what says the
fails case's signature does not cover those bytes. Validity under a synthetic
key is not evidence of a real service or effect.

84 tests pass (`tests.log`), 28/28 mutants killed (`mutants.log`).

## After the freeze

The expected files were opened after commit `f48a01d` and compared in
`comparison.json`. Action and effect match in all six cases; the action match
is largely by construction, since the query echoes the queried action.
Confirmed tickets match in five of six. In `effects-receipt-missing` the
reader emitted `ticket_ids: []` where the kit expects `null`, which is not a
match (FINDINGS F5). The first version of the comparison scored it as one;
that was corrected after independent review. The separate signature check
matches both pair cases.

An independent review of `5036716..5e63b26` then found four reader defects,
fixed in `1d3c66c` (FINDINGS F6). The frozen outputs here are from `2d7d3ba`
and are not rerun or edited.
