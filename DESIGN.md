# Independent trace reader (Python): design and interpretation record

Status: design only. Revision 4, 19 September 2026: re-pinned to contract v0.5 (PR #51 head `786ef15`), which answered the question this design had filed against line 39, a second decision on one proposal. The answer adopts the other reader's reading and withdraws this design's own, which reported two decisions as a conflict: each decision stands, none displaces another, which one applies is reported as unresolved and is never selected by order, timestamp or count, and two decisions are not by themselves a conflict (line 101); the timestamp and counting bans and the not-a-conflict rationale are the contract's additions to what the other reader had stated. Supersession by an explicit reference stays open as section 9 item 11 (line 157). Changed with it: section 1 (the approvals answer, a new refusal, and the receipt-only effects subject), section 4 (a record without a native id, because distinct decisions must never be keyed together), IC-8, IC-13 (the report values are unchanged; unresolved states are named as answer fields, because v0.5 introduces one), section 6 (approvals fields and the receipt-only effects entry, so the new answers have a place in the report), section 7 (two comparator rules: unresolved fields never match `unknown`, and an item the expected answer lacks is a recorded disagreement, because C14b can report more than a fixture lists), section 8 (C6a, C14, C14a, C14b and mutants m8 to m10), section 9, and section 10 item 4. One interaction v0.5 does not settle, an execution observed while a standing denial's applicability is unresolved, is decided here as this reader's own reading (IC-8, C14b) and raised on #51 with this revision. Every contract line reference is renumbered to the v0.5 file, and four citations are corrected rather than renumbered: section 1's last refusal (line 62 to line 75), IC-13's basis (lines 15, 103 to lines 101, 105, 177), and in the disclosure row lines 62 to 69 to 62 to 68, with lines 113 to 118 added to the revision 2 lines. The line 177 wording in IC-7 and C3 was described as filed in revision 3; it was never raised on #51, and now says so. Revision 3, 19 September 2026: re-pinned to contract v0.4 (PR #51 head `bca2fda`), which answered the two link-method edges this design had raised (a method outside the four; one relationship exported through two methods). Both answers match the choices this design had already recorded, so IC-2, C15b and C15c keep their outcomes and now cite contract lines instead of being marked as this reader's choice; section 9 closes the link-method row; every contract line reference is renumbered to the v0.4 file. Revision 2, 17 September 2026: re-pinned to contract v0.3 (PR #51 head `043f67d`), which answered the line 62 question by allowing a mapping-file default for the link method; IC-2, C15, section 8 and section 9 follow it, and two cases were added. Revision 1 (same day) linked the two filed questions. Tag `design-v1` stays on the first commit. No reader is implemented, no fixture has been read by code, no interoperability result is claimed. This document is the pre-implementation record promised on AAIF Observability WG [#45](https://github.com/aaif/wg-observability-and-traceability/issues/45) (comment 5712243517): the design and the interpretation choices are pinned before any #42 fixture is touched, so that a later correction is visible as a revision and not as a silent fit to expected answers.

## 0. Provenance

| Item | Value |
| --- | --- |
| Contract baseline | [PR #51 (contract draft v0.5)](https://github.com/aaif/wg-observability-and-traceability/pull/51), `working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md` at head `786ef155a190aea7945bfa98123984d12e928d40` (v0.5-draft, revision 5, 2026-09-19); revision 3 of this document was pinned to `bca2fda7730593d018794e1e19e05535c5f36f62` (v0.4-draft); revision 2 of this document was pinned to `043f67d042ca28e0c4b642e83f7fa2a1a0ad7ffe` (v0.3-draft); `design-v1` was pinned to `1af33bab242f1f5ab3060ef54128014748650f7b` (v0.2-draft) |
| Contract bytes as read | sha256 `7d334d22ffa5f7a5584de1ba41955465d2ef03fc01897b26d2228d92df1265c6` (193 lines; line numbers below refer to this file; v0.4 was `00f0533e…`, 188 lines; v0.3 was `8a6f7e84…`, 181 lines; v0.2 was `d630b9ef…`, 171 lines) |
| Other inputs read | #45 (issue body and all comments through 5740043865), #51 (DingNova's v0.4 reply 5726644070, this reader's line-39 options 5740043212, DingNova's v0.5 reply 5740441394), #42 (issue body, astrogilda's test-kit offer 2026-09-13), the contract's section 10 fixture example |
| Not opened for this design | any OTel GenAI mapping code I maintain elsewhere; any code or mapping of the other reader |
| Disclosure of exposure | The other reader's design (imran-siddique, #45 comment 5691732097) was read on 2026-09-17 before this document was written, because it carried the question this design answers. This is therefore not a blind design. Where a choice below coincides with his and a contract sentence carries it, the line is cited; revision 2 of the contract (line 190) was itself written from his reader-design feedback, so lines 49, 60, 93, 95 to 99, 106, 108, 113 to 118, 156 and 178 to 180 encode his reading before mine, and agreement on those rows is agreement with the contract as revised, not independent confirmation. The same holds in the other direction for revision 3 (line 190): lines 62 to 68 and 181 to 182 were written in answer to this reader's own question on line 62, and revision 4 (line 190), lines 70 to 74 and 183 to 184, in answer to this reader's follow-up (#51 comment 5718231537), so this reader following them is not independent confirmation either. Revision 5 (line 190) was written in answer to this reader's line-39 question (5712718367) and adopts option 2 of this reader's options comment (5740043212), which described imran-siddique's reading; DingNova's reply (5740441394) says this is what imran-siddique's reader already does. The contract adds to that reading the no-counting rule, the not-a-conflict rationale and the enforcement corollary. Lines 39, 101, 157, 185 and 186 therefore come from both readers' input, and agreement between the readers on them is not independent confirmation. Where a choice coincides with his and no contract sentence carries it (the receipt equality rule in section 4, the source locator triple, cap breach marking processing partial, the receipt-without-execution answer in IC-10, the two comparator controls in section 7), the row or paragraph says so. No text or table was copied; the rules named here were arrived at with his design in view. |
| Tooling | Written with an AI coding assistant (Claude, Fable 5.1 family) directed and reviewed by the maintainer; revision 4 was edited with Claude Opus 5 and checked by adversarial review passes by the same model, which are not an independent review. The implementation will be written the same way unless stated otherwise in its first commit, and its first commit will name the tooling and model family, as proposed in #45 comment 5712243517 and restated with the pin in 5712718069; the other reader agreed to record language, libraries and AI assistance before the first comparison (5739427059). |
| Language | Python 3.12+, standard library only for the reader and the comparator. No third-party JSON, no ORM, no framework. |

Nothing in this document is a claim about the two agent examples (#43, #44), which have no exports yet, or about the test kit (#42), which has no fixtures yet.

## 1. What the reader answers, and what it refuses to answer

The contract (lines 17 to 22) names four priority questions. The reader answers each **per subject** and only from exported records:

| Question | Subject | Answer shape |
| --- | --- | --- |
| Continuity | a conversation | the set of turns that carry its identity (R1); turn state and turn order are reported only where an exported relation carries them |
| Calls and retries | a turn | the set of logical model calls that reference it (R2); per call, the outcome and usage that the records support |
| Approvals | a proposed action | the set of decisions that reference it (R4) and the set of executions that reference it (R5), plus any inconsistency between them; with more than one decision, their count and `applicability: unresolved` (line 101) |
| Effects | a tool execution, or a receipt with no resolvable execution (IC-10) | the set of scoped external effects correlated to it (R6), deduplicated within scope, with conflicts kept |

The reader refuses to answer, and says so in the report:

- turn **order** inside a conversation (line 91: ordering must not depend only on timestamps or a single span tree; no ordering relation is among R1 to R6, and `gen_ai.request.previous_response.id` (line 125) is recorded as an observation, not used for order);
- whether a turn is suspended, resumed or closed (section 9 item 3 is open);
- whether a denial was **enforced** (line 99);
- whether an effect **occurred** when no receipt is exported (line 105);
- which of several decisions on one proposal **applies** (line 101; section 9 item 11 is open);
- any total usage across aggregation levels without declared semantics (lines 93 and 179);
- anything that would require a relationship the export did not carry (line 75).

## 2. Independence boundary

Shared with the other reader: the pinned contract, the published exporter descriptions and mapping files of the examples, the #42 fixture inputs, later the #43/#44 exports. Not shared: source code, the source-to-contract mapping this reader uses, private runtime state, fixture lookups.

Two mechanical consequences, so the boundary is checkable rather than asserted:

1. The reader package has no code path that reads an expected-answer file. The comparator is a second package that imports the reader's **report schema** and nothing else (its expected-answer format is unknown until #42 publishes one, so section 7 is revised then); the reader cannot import the comparator (enforced by a test that walks the reader's modules with `ast` and rejects any import of the comparator package, including through `importlib`).
2. The reader never reads a fixture's file name, directory name or scenario label as data. File names become source locators in the report and nothing else. A test renames every fixture to a hash and asserts an identical normalized report.

## 3. Parsing contract (the Python-specific part)

The contract says records are interpreted as a set (line 107) and forbids synthesized identifiers (line 47). The parser has to make that true before interpretation starts, and Python's `json` does not do it on its own.

| Concern | Rule | Why it is written rather than inherited |
| --- | --- | --- |
| Duplicate object keys | rejected; the record is a processing failure, not "last value wins" | `json.loads` keeps the last value silently; an `object_pairs_hook` that raises is required |
| `NaN`, `Infinity` | rejected | Python accepts them by default; `parse_constant` must raise |
| Numbers used as counters (usage, counts) | JSON integers only; a float, a string or a negative value is a mapping loss and the counter becomes unknown | Python parses `1e3` as `float`; the contract does not type a counter, so integer-only is this reader's rule and anything else is a loss. Integers over 4300 digits raise `ValueError`, not `JSONDecodeError`, so the parse boundary catches both |
| Nesting depth | explicit counter with a declared cap; breach is a processing failure | Python has no depth cap; it raises `RecursionError` at an interpreter-dependent depth |
| Input size, record count, reference count | declared caps; breach marks processing `partial` and suppresses every export-level conclusion | truncation must never look like a clean read |
| Encoding | UTF-8, BOM rejected, invalid sequences rejected | `json.loads` on `bytes` strips a leading BOM silently (`json.detect_encoding`), on `str` it raises; the reader decodes bytes itself with `utf-8`, never `utf-8-sig`, and rejects a leading U+FEFF before parsing |
| Structural equality | type-aware: `1`, `1.0` and `true` are three different values | Python's `==` treats them as equal (`{"n":1} == {"n":1.0} == {"n":true}`), so dict comparison coerces silently; equality is written over (type, value), or floats and bools are wrapped at parse time via `parse_float` and `object_pairs_hook` |
| Key order, whitespace | irrelevant to meaning | equality of two records is structural equality of parsed values, never of bytes |

Every parsed record carries a source locator: input digest, member name, record ordinal. Locators are diagnostics and are never used as identities (line 47).

## 4. Data model: four tables and one key

The reader is relational, not a pipeline over objects. After parsing, it holds exactly four tables and derives answers by set queries over them. This is the design decision that most shapes everything else, and it was taken because the contract's rules are statements about sets (lines 91, 101, 106, 107, 108) and about counting (line 93), and none about processing order.

**Scoped key.** Every identity is the triple `(scope, kind, native_id)`. `scope` is the issuing system, and where the export carries it, the tenant (identity rule 4, line 49). The exported form of scope is open (section 9 item 10), so the mapping file declares where the reader reads it. A record whose scope cannot be read has key `(UNRESOLVED, kind, native_id)`: it is kept, it appears in the report, and it joins nothing. A record that carries no native id gets no key at all, because none may be synthesized (identity rule 2, line 47): it is kept as its own row under a keyless identity, its source locator marked `keyless`, is recorded as a loss, can never be the target of a join and is never keyed together with another record; its own outgoing references (R1 to R6) are still resolved, and it appears in `entities`, as a `relations` source and as a report subject under that identity. Section 3's rule that locators are never identities is about join identity; a keyless identity joins nothing.

| Table | Row | Notes |
| --- | --- | --- |
| `entities` | scoped key, contract kind (one of the nine identities in section 3), native label, source locators | one row per distinct key; a second record with the same key and different typed fields is a second row in `observations` on that key; a conflict is derived by query from two observations that differ, never stored and never overwritten (line 108) |
| `relations` | kind (R1..R6), source key, target key, observed methods (one or more), source locators | only from exported relationship records; each method must be one of the four the contract names (line 62): span link, attribute reference, causal flag, external correlation key; one row per (kind, source, target), with every exported method kept (line 73) |
| `observations` | scoped key, field name, value, aggregation level (for usage), source locators | multi-valued by construction; the same value from two deliveries is one observation with two locators, two different values are two observations |
| `losses` | source locator, what the mapping could not place, which question it affects | unknown record kinds, unknown fields, relationships without a resolvable method, relationships with a method outside the four (the unrecognized value is kept, line 72), unreadable scope |

Deduplication rule, used only for `observations` and receipts: two records are the same observation when their **parsed values** are structurally equal after removing only the delivery fields the mapping explicitly names as delivery metadata. No sorting of arrays, no numeric coercion, no Unicode normalization, no "close enough". This rule is not in the contract (line 106 defines no equality; section 9 below) and coincides with the other reader's published rule; a shared reading of an undefined term is a gap to file on #42, not a confirmation.

## 5. Interpretation choices register

Each choice cites the contract line it rests on. "Alternative" names the reading this reader did not take, so a disagreement with the other reader can be filed against the sentence rather than against a reader. Where the other reader's published design is known to decide the same way from the same sentence, that is not marked; where this design decides differently, the row says **differs**.

| # | Choice | Contract basis | Alternative not taken |
| --- | --- | --- | --- |
| IC-1 | Input is a set: all files, all members, all records are loaded before any query runs; the report is invariant under any permutation of files and records | line 107 | streaming with first-arrival resolution |
| IC-2 | The link method is resolved in the contract's order: the record's own method field when it carries one of the four named methods, else the example's mapping-file default for that relationship kind when declared, else the relationship is not established and a mapping loss is recorded. A method value outside the four does not satisfy the first step and does not fall back to the default: the relationship is not established and the loss keeps the unrecognized value (line 72). Records with the same source, target and kind establish one relationship, whose observed methods are every method exported for it; different methods are not a conflict (line 73) | lines 62 to 75, 181 to 184 | treat any non-empty method as established; apply the mapping default to an unrecognized method; count a relationship once per method or report different methods as a conflict |
| IC-3 | Scope is read only from where the mapping file says the export carries it; absent scope means no join, never a default scope | line 49; section 9 item 10 | default to the file's producer as scope |
| IC-4 | R1 membership comes from the turn's exported conversation identity or an exported R1 record; trace ancestry, process, session and time never establish it | lines 55, 91 | fall back to trace id when conversation id is missing (forbidden by line 47) |
| IC-5 | Turn order and turn state are not answered in v0.5; the report carries the turn set and `order: not_answered` with the reason | lines 91, 149 | derive order from timestamps or span tree |
| IC-6 | A logical model call is one entity; attempts are observations on it, not calls; the count of exported calls per turn is the number of distinct call keys with an R2 record; unexported calls are unknown, not zero | lines 37, 56, 93 | count attempts as calls |
| IC-7 | Usage is reported per declared aggregation level; two levels without declared semantics give `usage: unknown` and both levels are shown; a failure exported without its success gives outcome unknown and usage unknown; line 177's "the call ... unknown" is read as outcome unknown with the call entity established by its failure record (C3), and that wording is recorded here against line 177, not yet raised on #51 | lines 93, 177, 179 | sum, or prefer the total |
| IC-8 | Per proposal, decisions and executions are two independent sets. Distinct decision keys are distinct decisions and are never deduplicated against each other, which line 186 requires for decisions from different policies (applying it to every pair of distinct keys is this reader's rule); a decision without a native id is never keyed together with another (section 4); the same key with equal content is one decision with two locators, and the same key with differing content is a conflict about one observation (line 101; line 108 for receipts). With more than one decision, the entry reports their count and `applicability: unresolved`, every decision is preserved, none is selected by arrival order, timestamp or count, and the decisions are not by themselves a conflict (line 101). An execution referencing a proposal whose only decision is a denial, or which has no decision, is reported as `inconsistent_with_decision` with the records involved (lines 98, 180). This reader's reading, not the contract's, for an execution while applicability is unresolved (C14b): the execution is related to every standing decision, inconsistent with each denial and consistent with each approval, under `applicability: unresolved` and enforcement unknown, so no decision is made the reference point. For: each decision stands and none displaces another (line 101), and line 180 reports an inconsistency together with enforcement unknown. Against: line 98 applies to "a denied proposal", and whether this proposal counts as denied is what line 101 leaves unresolved; line 101 gives its own rule for this case (enforcement unknown) without an inconsistency, and so does line 185, where line 180 lists one. Raised on #51 with this revision | lines 95 to 101, 108, 180, 185, 186 | resolve to the latest decision, or by majority; report two decisions as a conflict (this reader's reading up to revision 3, filed on #51 as [5712718367](https://github.com/aaif/wg-observability-and-traceability/pull/51#issuecomment-5712718367) with options in [5740043212](https://github.com/aaif/wg-observability-and-traceability/pull/51#issuecomment-5740043212), set aside by v0.5); report only the inconsistency with the denial; suppress it when an approval also stands |
| IC-9 | Enforcement is never established: denial plus no execution gives `enforcement: unknown`; approval plus execution gives `executed: established`, `enforcement: unknown` | line 99 | infer enforcement from absence |
| IC-10 | R6 correlation requires the same scoped key on execution and receipt; same key value in another scope is another effect; a receipt with no resolvable execution is an observed effect with `correlation: unresolved` (that last answer is not in the contract and coincides with the other reader's design) | lines 60, 106 | global deduplication by key value |
| IC-11 | Two receipts with the same scoped key and equal content are one effect with two locators; unequal content is a conflict and the effect count for that key is `conflict`, not one and not two | lines 106, 108 | pick the first or the newest |
| IC-12 | No receipt gives `effect: unknown` with the execution still established | line 105 | report no effect |
| IC-13 | Report values are `established`, `unknown`, `conflict`, `not_answered` (question not answerable under v0.5, IC-5) and `not_evaluated` (processing incomplete); the last two are never counted as either agreement or disagreement by the comparator. The contract supports only that unknown is not zero (lines 105, 177); the five-value split is this reader's. Contract states that are not report values are answer fields: `applicability: unresolved` (IC-8) and `correlation: unresolved` (IC-10) sit in the answer of an `established` entry, and neither is ever rendered as `unknown` or `conflict` | lines 101, 105, 177 | a single "unknown" bucket |
| IC-14 | The report never carries wall-clock time, host paths or absolute file names in its body; run metadata is a separate object with contract sha, reader commit, mapping digest, input digests, tooling | section 2 of this document | timestamps in the body |

## 6. Output

Two files, both canonical JSON (sorted keys, no insignificant whitespace, UTF-8, trailing newline). The body of `report.json` (everything except `basis`) is byte-identical across permuted or renamed input; the `basis` locators and `run.json` are not, because record ordinals, member names and input digests move with the input, and C7 to C9 compare the body only.

`report.json`: one entry per (question, subject) for every subject the tables contain, including subjects whose answer is `unknown`; a missing entry is a reader defect, not an answer. Each entry: question, subject key, status (IC-13), the answer set, the supporting locators, what is missing for a stronger answer, conflicts, losses that touch this subject. Approvals entries also carry `decision_count`, `applicability`, `enforcement` and `relations[]` (each execution against each decision: `consistent` or `inconsistent_with_decision`; an execution on a proposal with no decision is one item with `decision: unknown` and `inconsistent_with_decision`, which is what C6a is scored on). They also carry `executed` (IC-9); `applicability` is `unresolved` with two or more decisions and absent otherwise. A receipt with no resolvable execution is its own effects entry, keyed by the receipt's scoped key, with `correlation: unresolved` (IC-10).

`run.json`: contract sha, contract file sha256, reader commit, mapping file digest, input digests and sizes, caps and whether any was hit, processing status (`complete` or `partial` with reasons), tooling and model family, the interpretation register version this run followed.

Illustrative shape, not a produced result:

```json
{"question":"effects","subject":["svc-ticketing","tool_execution","E1"],"status":"unknown",
 "answer":[],"basis":["in-1:records:7"],"missing":["external_effect for scope svc-ticketing"],
 "conflicts":[],"losses":[]}
```

## 7. Comparator

A separate program reads `report.json` and the test kit's expected answers and writes `comparison.json`. Rules the comparator enforces on itself:

- every expected (question, subject) must be present in the report; an absent entry fails the case (a reader cannot pass by silence);
- a reader whose answers are all `unknown` must fail every positive case, and the comparator asserts this on a synthetic all-unknown report before scoring anything (a control on the comparator, not on the reader);
- `not_evaluated` entries fail; `not_answered` entries are scored only if the expected answer also declares the question not answerable;
- an expected `unresolved` matches only that named answer field on an `established` entry, never the status `unknown`; the all-unknown control must fail C11, C14 and C14a;
- an item the reader reports that the expected answer does not contain is a disagreement, recorded against the contract sentence and the IC row that produced it, and never removed from the report to match;
- agreement with the expected answers and agreement with the other reader are two separate tables, never merged into one score.

## 8. Acceptance cases

The first six degraded cases the contract lists (lines 175 to 180) are the first six rows, its two cases added in v0.3 (lines 181, 182) are C15 and C15d, its two cases added in v0.4 (lines 183, 184) are C15b and C15c, and its two cases added in v0.5 (lines 185, 186) are C14 and C14a, with C14b adding an execution to line 185 and splitting the contract's answer from this reader's; each has a positive twin (the same records with the degraded premise repaired; for C14 and C14a, one of the two decisions removed, so a single decision stands and no applicability question arises; for C14b, the denial removed, so the execution is consistent with the only decision). Rows after that are this reader's own, labeled as such until #42 publishes fixtures.

| # | Case | Required answer |
| --- | --- | --- |
| C1 | receipt delivered twice | one effect, two locators |
| C2 | receipt removed | `effect: unknown`, execution still established |
| C3 | M2 failure exported, success missing | line 177 says "the call and its usage are unknown"; read here as: the exported failure record establishes that a call was attempted, its outcome and usage are unknown; this reading is recorded here against line 177, not yet raised on #51, which does not separate existence from outcome |
| C4 | second service returns ticket id 42 | two effects in two scopes, no merge, no dedup |
| C5 | M2 usage per attempt and as total, no declared aggregation | usage unknown, both levels shown |
| C6 | execution references a proposal whose only decision is a denial | both kept, `inconsistent_with_decision`, enforcement unknown (line 180) |
| C6a | execution references a proposal with no decision (this reader's case) | proposal and execution kept, `inconsistent_with_decision`, decision unknown (lines 98, 99); enforcement unknown is this reader's (IC-9), since with no decision there is no expected enforcement (line 97) |
| C7 | every permutation of the section 10 example's records, exhaustive while the count stays under nine, otherwise seeded shuffles | byte-identical report body (locators excluded, section 2 item 2) |
| C8 | 200 seeded shuffles of a 50-record set | byte-identical report body (locators excluded) |
| C9 | every fixture renamed to a hash | byte-identical report body (locators excluded) |
| C10 | two receipts, same scoped key, different content | `conflict`, count neither one nor two |
| C11 | receipt present, execution absent | effect observed, correlation unresolved |
| C12 | turn without conversation identity | membership unknown, no synthesized conversation (line 47) |
| C13 | resumed work in a new session and trace with the same conversation id | joins the conversation; state `not_answered` |
| C14 | a denial and an approval on one proposal, nothing relating them, no execution; distinct decision keys, timestamps in the reverse of arrival order | both decisions kept, count 2, `applicability: unresolved`, not a conflict (line 185); enforcement unknown (line 99) |
| C14a | two approvals from different policies on one proposal; distinct decision keys, timestamps in the reverse of arrival order | both kept, count 2, `applicability: unresolved`, not a conflict and not a duplicate (line 186) |
| C14b | C14 plus an execution referencing the proposal | contract part (line 185): both decisions and the execution kept, `applicability: unresolved`, enforcement unknown; this reader's part (IC-8): the execution inconsistent with the denial and consistent with the approval |
| C15 | relationship record without method, no mapping-file default | link unused, loss recorded, dependent answer unknown (line 181) |
| C15a | relationship record without method, mapping-file default declared for that kind | link established with the default method |
| C15b | relationship record with a method outside the four, mapping-file default declared for that kind | link unused, default not applied, loss recorded with the unrecognized value (line 183) |
| C15c | same source, target and kind exported once as a span link and once as an attribute reference | one relationship with two observed methods, not a conflict and not two relationships (line 184) |
| C15d | same relationship exported twice with the same method | one relationship, two locators (line 182) |
| C16 | duplicate JSON key, `NaN`, BOM, depth over cap, size over cap | processing failure or partial; never a clean report |
| C17 | unknown record kind beside a valid baseline | loss recorded; baseline answers unchanged |
| C18 | usage counter as float or string | counter unknown, loss recorded |

**Must-fail controls on the reader.** Each is a small, named mutant of the reader that must turn at least one named case red: (m1) drop scope from the key, C4 must fail; (m2) index with overwrite instead of multi-value, C10 must fail; (m3) sum usage across levels, C5 must fail; (m4) drop an execution when its decision is a denial, C6 must fail; (m5) compare receipts with Python `==` or after array sorting, C10 with a `1` against `1.0` or a reordered-array difference must fail; (m6) resolve references in arrival order, C7 or C8 must fail; (m7) read the file name, C9 must fail; (m8) select one decision per proposal, by latest timestamp, by arrival order or by majority, C14 or C14a must fail; (m9) report two decisions on one proposal as `conflict` (the revision 3 reading), C14 and C14a must fail; (m10) suppress the inconsistency when any approval stands, C14b must fail. A mutant that survives is a defect in the case, not evidence about the reader.

These controls measure the sensitivity of specific cases. They do not establish that the case set covers the contract.

## 9. What this design does not settle, and where each goes

| Open point | Contract item | Handling here | Where it should be settled |
| --- | --- | --- | --- |
| Turn entry, suspend, resume, caller context | section 9 items 1 to 4 | `not_answered` | #41 revision, after #43/#44 |
| Scope representation | item 10 | mapping-declared; unresolved scope joins nothing | Task 9 upstream, #41 |
| Usage across providers, hidden retries | item 8 | unknown unless declared | #41 |
| Second decision on one proposal | answered in v0.5 (line 101) after #51 comments 5712718367 and 5740043212 | every decision stands, `applicability: unresolved` (IC-8) | settled on #51 |
| Decision supersession | item 11 (line 157) | not modelled; every decision stands | Task 9, with the attribute it needs |
| Execution while a standing denial's applicability is unresolved | line 185 names the case and gives enforcement unknown; it is silent on whether line 98's inconsistency is also reported | related to each decision, inconsistent with the denial and consistent with the approval (IC-8, C14b) | raised on #51 with this revision |
| Link method | answered in v0.3 (lines 62 to 68) after #51 comment 5712718683, and its two edges in v0.4 (lines 70 to 74, 183, 184) after comment 5718231537 | resolver as in IC-2 | settled on #51; no open point |
| What "the same receipt" means | line 106 says "delivered twice", not what equality is | structural equality minus declared delivery fields (IC-11) | #42 fixture definition |
| OTel crosswalk | section 7, pinned revisions | not implemented in the first version; the reader reads the examples' exports through their mapping files, not raw OTel | later adapter, verified against the pinned revisions only |

## 10. Delivery sequence

1. This document is committed with the contract sha and file sha256 above. Later changes to sections 4, 5, 7 and 8 land as revisions with a reason.
2. Implementation starts only when #42 publishes its input format and expected-answer format, or when #43/#44 export records, whichever is first. Until then, the parser (section 3) and the four tables (section 4) can be written and tested against locally authored records, labeled as local.
3. The first implementation commit names language, standard library version, tooling and model family, and freezes the interpretation register version it implements.
4. Cases C1 to C18, including every lettered variant, and mutants m1 to m10 run locally before any comparison.
5. The comparison against expected answers runs once per pinned fixture revision; every disagreement between the readers is filed against a contract sentence on #41 or #42, and recorded in the report as a finding, not resolved between the readers.

## 11. Non-claims

The reader establishes what the exported records support under the pinned contract. It does not authenticate an export, establish that an export is complete, prove enforcement, prove that an effect occurred, verify hardware or software attestation, or score an agent. Agreement between the two readers is not evidence that the contract is unambiguous: two implementations can share a reading of an ambiguous sentence. The list of sentences they read differently is the result this task exists to produce.
