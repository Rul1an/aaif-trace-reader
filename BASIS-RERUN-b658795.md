# PR #57 rerun at kit b6587950, 2026-10-06

Basis registry revision 3, mapping `mappings/test-kit-b658795.json`. Contract
remains v0.7-draft (`e82abf1e58b066c586c25767edfba862c4ebd027`). Written with an
AI coding assistant, Claude Opus 5.5, directed and reviewed by the maintainer.

Revision 3 adds one thing to revision 2 (BASIS-RERUN-4a02867.md): where
`basis.json` carries `evaluation_context` (action, service, tenant), the report
gains a `query` section answering effect correlation for that context. The
context selects which subject is answered; it never supplies an answer value.
Scope decisions per check are unchanged.

What the kit's `mapping.md` changed at b6587950, and how this reader encodes it:

- R6 joins and deduplicates on `receipt.id` within the service and tenant scope.
  Scope is the issuing system (`service.name`) qualified by `tenant.id` where a
  record carries one (identity rule 4, contract line 49), rendered
  `system@tenant`. Without `tenant.id` the scope is the system alone, so the
  frozen 4a028675ef reports reproduce byte for byte (test
  `FrozenRegression.test_4a02867_reports_unchanged`).
- `receipt.action_id` refers to the proposed action issued by `support-agent`
  in the receipt's own tenant. The system name stays this reader's declaration
  (FINDINGS F4); the tenant qualification follows mapping.md.
- The README says a count or receipt ID alone cannot answer the ticket-ID
  question. Effect views now carry `ticket_ids`, every value the receipt
  records state; two different values are both kept and the count is
  `conflict`. This closes the gap stated in our 4a02867 report ("my report
  carries the receipt identity and a count rather than ticket ids").

Order of work, as the author reports it: tests first (8 of 10 red), then the
implementation, 84 tests and 28/28 mutants (b9 first survived and gained a test
where the mapping joins across tenants). Tests and implementation landed in one
commit (`2d7d3ba`), so the history cannot show the red step or the b9 survival.
Results were committed (`f48a01d`) before, by the author's account, any
expected.json at this revision was opened; commit order shows only the order of
commits. This is a targeted run, not a blind evaluation: the reader was changed
for the two new cases with their records and the kit README's stated outcomes in
view. Independent review later found four defects, fixed in `1d3c66c` (F6).
