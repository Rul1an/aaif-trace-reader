# Findings from the first implementation slice

Status on 2026-09-26: the effects slice runs against the PR #57 test kit at head
`afc26fdd2199844bf7dff23879739e941fa81107`. **No comparison against expected answers has run.**
DESIGN.md section 10 step 4 requires every case C1 to C18 and every mutant m1 to m13 to run locally
first, and most of them are not implemented yet (see "Before any comparison" below). Every finding
here comes from the pinned contract, the kit's records, its README and its TEMPLATE/mapping.md. No
expected-answer file was opened, and none of the kit's `run.py` or `generate.py` was read, because
those carry another reader's source (DESIGN.md section 2).

## Against the contract or the kit (to file on #41 or #42, not settle between readers)

**F1. The evidence-grade pair and contract v0.7 line 112 point in opposite directions.**
Line 112 reads: "A service-side receipt is correlation evidence, not cryptographic attestation." The
kit README says `evidence-grade-pair-verifies` confirms the effect because the receipt's signature
verifies, and `evidence-grade-pair-fails` leaves it unconfirmed because the signature fails, with
every producer-authored field identical. A reader following v0.7 gives the signature no meaning, so
it answers both cases the same way. This reader does: the effect is `established` in both, and
`receipt.signature` surfaces as an unplaced attribute (`results/afc26fdd/`). Either the contract
needs a revision that admits an evidence grade (a receipt verified against the key of the external
party it names), or the pair tests the MCP boundary deep dive's section 3.3 (PR #32) and not
contract v0.7. Neither reading is this reader's to choose.

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

## Against this reader's own design (to land as DESIGN.md revision 7 before any comparison)

**D1. A keyless subject cannot be both locator-labelled and locator-free.** Section 4 keeps a
keyless record "under a keyless identity, its source locator marked keyless", and section 6 requires
the report body to be byte-identical across permuted or renamed input, with locators excluded. A
subject labelled by its locator breaks the second rule. The implementation labels a keyless subject
by a digest of its content minus the declared delivery fields, with a `~n` suffix when several
records share content. The label is a display label: it joins nothing and is never exported as an
identity. It still reads as a content hash, which identity rule 2 forbids as an identifier, so the
revision has to say why a report label is not an identifier, or pick another label.

**D2. Cap breaches fail instead of marking processing partial.** Section 3 says a breach of the size
or record-count cap marks processing `partial` and suppresses every export-level conclusion. The
implementation reports processing `failed` with no entries, which is stricter and still never looks
like a clean read (C16). Either the design moves to `failed`, or the implementation adds `partial`.

## Before any comparison (DESIGN.md section 10 step 4)

Implemented and passing: the parsing contract (C16: duplicate key, NaN, BOM, invalid UTF-8, depth,
size, duplicate attribute key), typed equality, C1, C2, C4, C10 (including `1` against `1.0`), C11,
C17, C7 and C8 (200 seeded shuffles of each kit case), C9, the split-across-files form of IC-1, and
the independence boundary test. Mutants m1, m2 and m5 each turn their named case red. The boundary
test turns red on a planted comparator import and on a planted expected-answer path.

Not implemented: C3, C5, C6, C6a, C6b, C12, C13, C14 to C14c, C15 to C15d and C18, which need local
mappings for model calls, decisions and relationship records, and mutants m3, m4 and m6 to m13. The
comparator (section 7) is not written; its input format is the kit's `expected.json`, which has not
been opened.
