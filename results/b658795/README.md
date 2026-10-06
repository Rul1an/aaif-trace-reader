# Rerun of AAIF O&T PR #57 at kit b6587950

Kit: `b6587950986eb4ec501e080cc9730fd21dcb69fa`. Contract: v0.7-draft
(`e82abf1e58b066c586c25767edfba862c4ebd027`). Reader: `2d7d3ba` (basis registry
revision 3, mapping `mappings/test-kit-b658795.json`). Written with an AI coding
assistant, Claude Opus 5.5, directed and reviewed by the maintainer.

**Frozen before any expected answer at this kit revision was opened.** The
`expected.json` files were fetched and hashed (`inputs.sha256.json`); their
contents have not been read. `run.py` and `generate.py` were not fetched. The
kit README states the intended outcome of each case, so this run is
expected-file-blind, not answer-blind. The four original cases' records are
byte-identical to 4a028675ef.

## Query answers (evaluation_context from basis.json), and the separate signature check

| Case | Context | Effect correlation | Ticket ids | Receipt signature |
| --- | --- | --- | --- | --- |
| action id reused in another scope | P1, test-ticket-service, tenant-a | established: `R-9` in `test-ticket-service@tenant-a` | T-1042 | not asked |
| receipt delivered twice | P1, test-ticket-service, no tenant | established: `R-1`, two deliveries | T-1042 | not asked |
| receipt missing | P1, test-ticket-service, no tenant | unknown (execution established, no R6) | none | not asked |
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
