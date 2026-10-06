# PR #57 rerun at kit 4a028675ef, 2026-09-30

Basis registry revision 2, reader `951e57e`. Contract remains v0.7-draft
(`e82abf1e58b066c586c25767edfba862c4ebd027`). Written with Claude Opus 5.5.

At this kit revision `basis.json` names the checks each case asks for. A basis
with a `checks` list is scoped per check: `<check>_follows` for that check if
present, else `answer_follows`, looked up in the same bounded registry as
revision 1 (the pinned contract URL; issue #42 only with the pinned contract as
`also_stated_in`; the pinned #32 deep dive as outside). Hints such as `outside`
never decide scope. Only `effect_correlation` is a contract check; a
`receipt_signature` check is never answered by the contract reader, even where a
basis names the contract, because contract line 112 gives a service receipt no
attestation meaning (`no_contract_rule`). It is answered by the separate
README-derived Ed25519 check (`scripts/signature_rows.py`), only where asked.
Unknown check names are recorded as `unknown_check` and admit nothing. A basis
without `checks` is handled exactly as in revision 1 (see BASIS-RERUN.md); the
frozen 8fa732e reports reproduce as identical JSON.

Mapping `mappings/test-kit-4a02867.json` encodes the kit's own
`test-kit/mapping.md`. Its R1/R5/R6 defaults equal the ones this reader declared
itself at 8fa732e (F3), so agreement between readers on these links now comes
from one declared input. R6 on a receipt applies only in `test-ticket-service`
(`source_scope`), as mapping.md says a different service does not inherit it.

Order of work: tests first (red), implementation, 73 tests and 22/22 mutants,
results frozen and pushed (`c298e7d`), then the expected files opened and
compared (`results/4a02867/comparison.json`).
