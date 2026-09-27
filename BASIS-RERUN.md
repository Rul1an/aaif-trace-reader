# PR #57 bounded rerun — 2026-09-27

Interpretation fixed before opening expected answers at kit revision
8fa732e3ec597e04a8b667c3669d3ac537e3e98a. Contract remains v0.7-draft
(e82abf1e58b066c586c25767edfba862c4ebd027). Codex implemented this extension.

The optional --basis interface is a case-level applicability gate, not a new
contract verdict. The reader recognizes the exact pinned contract URL, and
issue #42 only with the exact pinned contract as also_stated_in. It recognizes
the exact pinned #32 document as outside its supported contract. Other or
missing identifiers are unknown_basis. The outside prose is never executable
policy. Unknown/outside cases have no entries and processing not_evaluated;
they are exclusions, never passes. Without --basis legacy explicit-contract
operation remains unchanged. This is a bounded registry, not a general resolver.
Issue #42's URL is mutable; the kit basis bytes and pinned contract are retained.
A metadata assertion does not authenticate the case or prove runtime events.

Mapping semantics are unchanged from afc26fdd; only the mapping identifier and
applies_to pin change. F3/F4 in FINDINGS.md remain limitations. Case names are
used for result routing only, never to choose answers. The README already
states the intended answers: this is expected-file-blind, not answer-blind.
Earlier process exposure is recorded in FINDINGS.md and is not erased.

Expected comparison plan: preserve all report entries; compare only the effects
projection that these four fixtures exercise, documenting any incompatible
vocabularies and excluding the two unsupported cases from the contract result.
This is not the full section 7 four-question comparator, nor reader-to-reader
comparison. Signature verification is a separate README-derived byte check,
not an extension of the v0.7 contract and not proof of real-world effects.

Validation: initial interface failures were corrected to assertion failures;
all four new cases then failed with missing scope, before scope implementation.
58 tests passed with `python3 -m unittest discover -s tests -v` and all 16
existing mutants were killed by assertion failures. Bare unittest discovery
found zero tests; it is not counted as validation.

## Result

See results/8fa732e/README.md and comparison.json. The frozen reader results
precede expected-file inspection. The later manual comparison found a remaining
externally_verified meaning question and a ticket-list representation gap;
no full conformance pass is claimed. No external response was sent.
