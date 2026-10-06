# Findings from the first implementation slice

Status on 2026-09-26 (updated for DESIGN.md revision 7 and the full local case set): the reader runs against the PR #57 test kit at head
`afc26fdd2199844bf7dff23879739e941fa81107`. **No comparison against expected answers has run.**
DESIGN.md section 10 step 4, every case C1 to C18 and every mutant m1 to m13 run locally first, is
now met (see the last section). Every finding
here comes from the pinned contract, the kit's records, its README and its TEMPLATE/mapping.md. The
kit's `expected.json` files were fetched with the records (`scripts/fetch_kit.sh`) into the ignored
directory `inputs/expected-afc26fdd…/`, and their sha256 digests were computed; their contents have
not been opened. The reader has no code path to that directory, and `tests/test_reader.py`
(`IndependenceBoundary`) fails on any reader module that imports the comparator or spells a path to
it. The kit's `run.py` and `generate.py` were not read, because they carry another reader's source
(DESIGN.md section 2).

## Against the contract or the kit (to file on #41 or #42, not settle between readers)

**F1. The evidence-grade pair follows a different document than the reader, and nothing a reader
may read says so.** Contract v0.7 line 112 reads: "A service-side receipt is correlation evidence,
not cryptographic attestation." The kit README (line 25) says the pair is "the fixture pair from
section 3.3 of the MCP boundary deep dive" (PR #32), and that cases for continuity, calls and
approvals, none of which is in the kit yet, will follow the contract (#41). Section 3.3 attaches to an E0 to E4 ladder that is not in contract v0.7
(nor in PR #25 at head `05c47c4`). A reader built to v0.7 gives the signature no meaning, so this
reader answers both pair cases the same way: the effect is `established`, and `receipt.signature`
surfaces as an unplaced attribute (`results/afc26fdd/`). The correct v0.7 answer is that the pair is
outside the contract, but this reader cannot tell which case is which: case and file names are not
input to it (DESIGN.md section 2 item 2, case C9), and every receipt in the kit carries
`receipt.signature`, the effects cases included, so the field's presence does not identify the pair. The gap is a per-case statement, in the case's
own files, of which document its expected answer follows.

**F2. The signed bytes are not specified in any text a reader may use.** The README names Ed25519
and a public key in `trust/`, and says a rebuild is byte-identical because the signatures are
deterministic. It does not say which bytes are signed: which fields, in what order, in what
encoding. The only definition is the kit's `generate.py`, and reading it would cross this reader's
independence boundary. So even after F1 is settled, two readers can only agree on signature
verification if the signing input is written down in the contract or the kit's README.

**F3. The kit leaves the mapping to each reader.** `TEMPLATE/mapping.md` names `conversation.id`,
`turn.id`, `action.id` and `receipt.*`, but not which contract identity or relationship each carries,
and the records carry no relationship records and no method field. Under contract lines 62 to 68 a
relationship without a method is established only by a mapping-file default. This reader declares
its own defaults (`mappings/test-kit-afc26fdd.json`: R1 and R5 by attribute reference, R6 by
external correlation key). Two readers can therefore agree or disagree through their mappings
rather than through the contract, and that difference would be invisible in a comparison of answers.

**F4. The execution carries no native id, and R6 runs through the proposal's id.** The
`execute_tool` span has no tool-execution identifier, so this reader keeps it keyless (identity
rule 2 forbids synthesizing one). R6 correlation runs through `action.id` on the execution and
`receipt.action_id` on the receipt. That is a shared scoped key, but it is the proposal's identity,
where contract line 60 gives the ticket id returned by both the tool and the service as the example.
It also needs a scope the receipt does not carry: the mapping declares that `receipt.action_id`
refers to an action issued by `support-agent`.

## Against this reader's own design (resolved in DESIGN.md revision 7)

**D1. A keyless subject could not be both locator-labelled and locator-free.** Section 4 kept a
keyless record under its source locator, and section 6 requires a report body that does not move
when inputs are permuted or renamed. The first implementation (`f449b0b`) labelled a keyless subject
by a digest of its content, which identity rule 2 names as a synthesized identifier. Revision 7
(`da76f63`) renders it as `["KEYLESS", kind, "<anchor>#<n>"]`: the least of the record's own outgoing
references, and an ordinal in the canonical order of content. The kit's execution is now
`R5:support-agent/proposed_action/P1#1`. Section 7 matches keyless subjects by kind and anchor.

**D2. Cap breaches failed instead of marking processing partial.** This was an implementation
deviation, not a design question: section 3 already says `partial`, and that choice coincides with
the other reader's design, so the implementation now follows it. A size or record-count breach marks
processing `partial`, every entry becomes `not_evaluated` with no answer, and nothing is dropped by
arrival order. Depth and malformed input still fail.

## Process note

On 2026-09-26 an independent reviewer of a comment draft for PR #57 read a docstring in the kit's
`generate.py` that describes the signed fields in one phrase. That text came into this session. The
reader does not implement signature verification, so nothing in `aaif_reader/` depends on it, and
F2 stands: the README, which is the text a reader may use, does not state the signing input.
A second reviewer of the same comment checked the top-level keys of the kit's `expected.json` files
to confirm that none names a source document, and reported that finding without the key names. The
maintainer has not opened those files, and nothing in `aaif_reader/` reads them.

## Before any comparison (DESIGN.md section 10 step 4): complete

Every case in section 8 now runs locally, including each lettered variant: C1, C2, C4, C9, C10, C11,
C16 and C17 in `tests/test_reader.py`, and C3, C5, C6, C6a, C6b, C7, C8, C12, C13, C14 to C14c,
C15 to C15d and C18 in `tests/test_cases.py`, with the positive twins section 8 names. The local
cases use `mappings/local-v1.json`, this reader's own mapping for its own records; none is a WG
fixture. 54 tests pass.

`python3 tests/mutants.py` applies each of m1 to m13, plus three controls for behaviours the first
slice had (failing on a cap breach, a content-hash label, truncation by arrival order), and requires
every one to turn its named case red **by an assertion failure**. A kill by an exception is reported
as `ERROR` and counts as a survivor, because it shows the mutant broke the program rather than that a
case caught a wrong answer. The first run of that rule found two such kills (m8, m11), caused by
tests indexing a field the mutant removed; those asserts now compare the field, and all 16 are killed
by an assertion failure.

Two notes on how the cases meet section 8's wording. m6 ("resolve references in arrival order, C7
or C8 must fail") is killed by a 200-shuffle invariance test on a proposal with two decisions and two
executions, which is a C8-form test on approvals; the section 10 example in C7 has one referenced
decision per proposal, so arrival-order resolution cannot change its answer. C7 has ten records, over
section 8's exhaustive limit of nine, so it runs 300 seeded shuffles.

Not done yet: the comparator (section 7). Writing it means opening the kit's `expected.json` files for
the first time, and the comparison runs once per pinned fixture revision (section 10 step 5).

## After the b6587950 comparison (2026-10-06)

**F5. An unknown effect reports an empty ticket list, not an absent one.** In
`effects-receipt-missing` the frozen query answer at `f48a01d` carries `ticket_ids: []`
beside `status: unknown`; the kit's expected answer is `confirmed_tickets: null`. Read on
its own, an empty list says no ticket was created, which a missing receipt does not establish
(contract line 108). The initial comparison mapped the field to null because the status was unknown.
That normalization has been withdrawn: `results/b658795/comparison.json` now records
a ticket mismatch for this case (5 of 6 ticket matches). This is this reader's defect, not the kit's;
the fix is to emit null whenever the effect is not established, with a test and a mutant, in a
revision after this frozen run rather than inside it.

F5 resolved in the revision after `c774b0e`: the query emits null answer fields whenever no
effect is established; test `test_missing_receipt_is_unknown_not_absent` and mutant b13 pin it.
The frozen b6587950 results are not rerun or edited.

The two assertions that pin F5 were changed from `[]` to `None` after the kit's
expected answers had been read. They are fitted to that answer key, not
pre-registered.

**F6. Four defects found by independent review of `5036716..5e63b26`, fixed in `1d3c66c`.**
(1) `system_of` split scopes at `@` even when the mapping declared no tenant key, so under the
4a02867 mapping a receipt from `test-ticket-service@evil` correlated as if it came from
`test-ticket-service`; the frozen fixtures could not show this because no name contains `@`.
(2) An established effect that states no ticket id reported `[]`, the misreading F5 removed for
unknown effects. (3) A query with one conflicting and one clean effect reported `established`
with the conflicting values merged in. (4) Query executions were not limited to the declared
issuing system. Each has a regression test and a mutant. A further guard (an unresolved scope
matching a tenantless query) has a test but no mutant, because `build()` never creates an R5
relation with an unresolved target, so no input can kill it. The review also found the
comparison scored F5 as a match and the order-of-work text stated what the history cannot show;
both are corrected in place, with the correction recorded.
