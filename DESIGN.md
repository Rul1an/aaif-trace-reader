# Independent trace reader (Python): design and interpretation record

Status: design only, 17 September 2026 (revision 1, same day: the two open questions are now filed and linked; tag `design-v1` stays on the first commit). No reader is implemented, no fixture has been read by code, no interoperability result is claimed. This document is the pre-implementation record promised on AAIF Observability WG [#45](https://github.com/aaif/wg-observability-and-traceability/issues/45) (comment 5712243517): the design and the interpretation choices are pinned before any #42 fixture is touched, so that a later correction is visible as a revision and not as a silent fit to expected answers.

## 0. Provenance

| Item | Value |
| --- | --- |
| Contract baseline | [PR #51 (contract draft v0.2)](https://github.com/aaif/wg-observability-and-traceability/pull/51), `working-documents/AGENT-BEHAVIOR-TRACE-MODEL-CONTRACT.md` at head `1af33bab242f1f5ab3060ef54128014748650f7b` (v0.2-draft, revision 2, 2026-09-16) |
| Contract bytes as read | sha256 `d630b9efb1e21f9e72ee8a9ecbb59e5793f429ac8c920705070aeec71ea871ef` (171 lines; line numbers below refer to this file) |
| Other inputs read | #45 (issue body and all comments through 5712243517), #42 (issue body, astrogilda's test-kit offer 2026-09-13), the contract's section 10 fixture example |
| Not opened for this design | any OTel GenAI mapping code I maintain elsewhere; any code or mapping of the other reader |
| Disclosure of exposure | The other reader's design (imran-siddique, #45 comment 5691732097) was read on 2026-09-17 before this document was written, because it carried the question this design answers. This is therefore not a blind design. Where a choice below coincides with his and a contract sentence carries it, the line is cited; revision 2 of the contract (line 168) was itself written from his reader-design feedback, so lines 49, 60, 80, 82 to 86, 91, 93, 141 and 162 to 164 encode his reading before mine, and agreement on those rows is agreement with the contract as revised, not independent confirmation. Where a choice coincides with his and no contract sentence carries it (the receipt equality rule in section 4, the source locator triple, cap breach marking processing partial, the receipt-without-execution answer in IC-10, the two comparator controls in section 7), the row or paragraph says so. No text or table was copied; the rules named here were arrived at with his design in view. |
| Tooling | Written with an AI coding assistant (Claude, Fable 5.1 family) directed and reviewed by the maintainer. The implementation will be written the same way unless stated otherwise in its first commit, and its first commit will name the tooling and model family, as proposed in #45 comment 5712243517 and restated with the pin in 5712718069; the other reader has not yet replied to that proposal. |
| Language | Python 3.12+, standard library only for the reader and the comparator. No third-party JSON, no ORM, no framework. |

Nothing in this document is a claim about the two agent examples (#43, #44), which have no exports yet, or about the test kit (#42), which has no fixtures yet.

## 1. What the reader answers, and what it refuses to answer

The contract (lines 17 to 22) names four priority questions. The reader answers each **per subject** and only from exported records:

| Question | Subject | Answer shape |
| --- | --- | --- |
| Continuity | a conversation | the set of turns that carry its identity (R1); turn state and turn order are reported only where an exported relation carries them |
| Calls and retries | a turn | the set of logical model calls that reference it (R2); per call, the outcome and usage that the records support |
| Approvals | a proposed action | the set of decisions that reference it (R4) and the set of executions that reference it (R5), plus any inconsistency between them |
| Effects | a tool execution | the set of scoped external effects correlated to it (R6), deduplicated within scope, with conflicts kept |

The reader refuses to answer, and says so in the report:

- turn **order** inside a conversation (line 78: ordering must not depend only on timestamps or a single span tree; no ordering relation is among R1 to R6, and `gen_ai.request.previous_response.id` (line 110) is recorded as an observation, not used for order);
- whether a turn is suspended, resumed or closed (section 9 item 3 is open);
- whether a denial was **enforced** (line 86);
- whether an effect **occurred** when no receipt is exported (line 90);
- any total usage across aggregation levels without declared semantics (lines 80 and 163);
- anything that would require a relationship the export did not carry (line 62).

## 2. Independence boundary

Shared with the other reader: the pinned contract, the published exporter descriptions and mapping files of the examples, the #42 fixture inputs, later the #43/#44 exports. Not shared: source code, the source-to-contract mapping this reader uses, private runtime state, fixture lookups.

Two mechanical consequences, so the boundary is checkable rather than asserted:

1. The reader package has no code path that reads an expected-answer file. The comparator is a second package that imports the reader's **report schema** and nothing else (its expected-answer format is unknown until #42 publishes one, so section 7 is revised then); the reader cannot import the comparator (enforced by a test that walks the reader's modules with `ast` and rejects any import of the comparator package, including through `importlib`).
2. The reader never reads a fixture's file name, directory name or scenario label as data. File names become source locators in the report and nothing else. A test renames every fixture to a hash and asserts an identical normalized report.

## 3. Parsing contract (the Python-specific part)

The contract says records are interpreted as a set (line 92) and forbids synthesized identifiers (line 47). The parser has to make that true before interpretation starts, and Python's `json` does not do it on its own.

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

The reader is relational, not a pipeline over objects. After parsing, it holds exactly four tables and derives answers by set queries over them. This is the design decision that most shapes everything else, and it was taken because the contract's rules are statements about sets (lines 78, 91, 92, 93) and about counting (line 80), and none about processing order.

**Scoped key.** Every identity is the triple `(scope, kind, native_id)`. `scope` is the issuing system, and where the export carries it, the tenant (identity rule 4, line 49). The exported form of scope is open (section 9 item 10), so the mapping file declares where the reader reads it. A record whose scope cannot be read has key `(UNRESOLVED, kind, native_id)`: it is kept, it appears in the report, and it joins nothing.

| Table | Row | Notes |
| --- | --- | --- |
| `entities` | scoped key, contract kind (one of the nine identities in section 3), native label, source locators | one row per distinct key; a second record with the same key and different typed fields is a second row in `observations` on that key; a conflict is derived by query from two observations that differ, never stored and never overwritten (line 93) |
| `relations` | kind (R1..R6), source key, target key, establishment method, source locators | only from exported relationship records; method must be one of the four the contract names (line 62): span link, attribute reference, causal flag, external correlation key |
| `observations` | scoped key, field name, value, aggregation level (for usage), source locators | multi-valued by construction; the same value from two deliveries is one observation with two locators, two different values are two observations |
| `losses` | source locator, what the mapping could not place, which question it affects | unknown record kinds, unknown fields, relationships without a method, unreadable scope |

Deduplication rule, used only for `observations` and receipts: two records are the same observation when their **parsed values** are structurally equal after removing only the delivery fields the mapping explicitly names as delivery metadata. No sorting of arrays, no numeric coercion, no Unicode normalization, no "close enough". This rule is not in the contract (line 91 defines no equality; section 9 below) and coincides with the other reader's published rule; a shared reading of an undefined term is a gap to file on #42, not a confirmation.

## 5. Interpretation choices register

Each choice cites the contract line it rests on. "Alternative" names the reading this reader did not take, so a disagreement with the other reader can be filed against the sentence rather than against a reader. Where the other reader's published design is known to decide the same way from the same sentence, that is not marked; where this design decides differently, the row says **differs**.

| # | Choice | Contract basis | Alternative not taken |
| --- | --- | --- | --- |
| IC-1 | Input is a set: all files, all members, all records are loaded before any query runs; the report is invariant under any permutation of files and records | line 92 | streaming with first-arrival resolution |
| IC-2 | A relationship exists only if an exported relationship record carries it with a named establishment method; a relationship record without a method is a loss, and the link is not used | line 62 | use the link, flag the missing method (**not addressed** in the other reader's published design, which carries the method in its relationship type but states no rule for its absence; a weaker reading is defensible; filed as a question on #51 against line 62 ([comment 5712718683](https://github.com/aaif/wg-observability-and-traceability/pull/51#issuecomment-5712718683)). Whether the mapping file may supply the method the way it supplies scope is decided here: it may not, the method must be on the exported relationship record, otherwise IC-2 would never fire on a well-mapped export) |
| IC-3 | Scope is read only from where the mapping file says the export carries it; absent scope means no join, never a default scope | line 49; section 9 item 10 | default to the file's producer as scope |
| IC-4 | R1 membership comes from the turn's exported conversation identity or an exported R1 record; trace ancestry, process, session and time never establish it | lines 55, 78 | fall back to trace id when conversation id is missing (forbidden by line 47) |
| IC-5 | Turn order and turn state are not answered in v0.2; the report carries the turn set and `order: not_answered` with the reason | lines 78, 134 | derive order from timestamps or span tree |
| IC-6 | A logical model call is one entity; attempts are observations on it, not calls; the count of exported calls per turn is the number of distinct call keys with an R2 record; unexported calls are unknown, not zero | lines 37, 56, 80 | count attempts as calls |
| IC-7 | Usage is reported per declared aggregation level; two levels without declared semantics give `usage: unknown` and both levels are shown; a failure exported without its success gives outcome unknown and usage unknown; line 161's "the call ... unknown" is read as outcome unknown with the call entity established by its failure record (C3), and that wording is filed against line 161 | lines 80, 161, 163 | sum, or prefer the total |
| IC-8 | Per proposal, decisions and executions are two independent sets; an execution referencing a denied decision is reported as `inconsistent_with_decision` with both records; more than one decision on a proposal is a conflict, because v0.2 defines no supersession | lines 82 to 86, 164 | resolve to the latest decision (**differs** in status: the other reader reports decision applicability as unresolved, this reader reports `conflict`; the contract is silent on a second decision, so neither reading is contract-derived; filed on #51 against line 39 ([comment 5712718367](https://github.com/aaif/wg-observability-and-traceability/pull/51#issuecomment-5712718367))) |
| IC-9 | Enforcement is never established: denial plus no execution gives `enforcement: unknown`; approval plus execution gives `executed: established`, `enforcement: unknown` | line 86 | infer enforcement from absence |
| IC-10 | R6 correlation requires the same scoped key on execution and receipt; same key value in another scope is another effect; a receipt with no resolvable execution is an observed effect with `correlation: unresolved` (that last answer is not in the contract and coincides with the other reader's design) | lines 60, 91 | global deduplication by key value |
| IC-11 | Two receipts with the same scoped key and equal content are one effect with two locators; unequal content is a conflict and the effect count for that key is `conflict`, not one and not two | lines 91, 93 | pick the first or the newest |
| IC-12 | No receipt gives `effect: unknown` with the execution still established | line 90 | report no effect |
| IC-13 | Report values are `established`, `unknown`, `conflict`, `not_answered` (question not answerable under v0.2, IC-5) and `not_evaluated` (processing incomplete); the last two are never counted as either agreement or disagreement by the comparator. The contract supports only that unknown is not zero (lines 15, 90); the five-value split is this reader's | lines 15, 90 | a single "unknown" bucket |
| IC-14 | The report never carries wall-clock time, host paths or absolute file names in its body; run metadata is a separate object with contract sha, reader commit, mapping digest, input digests, tooling | section 2 of this document | timestamps in the body |

## 6. Output

Two files, both canonical JSON (sorted keys, no insignificant whitespace, UTF-8, trailing newline). The body of `report.json` (everything except `basis`) is byte-identical across permuted or renamed input; the `basis` locators and `run.json` are not, because record ordinals, member names and input digests move with the input, and C7 to C9 compare the body only.

`report.json`: one entry per (question, subject) for every subject the tables contain, including subjects whose answer is `unknown`; a missing entry is a reader defect, not an answer. Each entry: question, subject key, status (IC-13), the answer set, the supporting locators, what is missing for a stronger answer, conflicts, losses that touch this subject.

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
- agreement with the expected answers and agreement with the other reader are two separate tables, never merged into one score.

## 8. Acceptance cases

The six degraded cases the contract itself lists (lines 157 to 164) are the first six rows; each has a positive twin (the same records with the degraded premise repaired). Rows after that are this reader's own, labeled as such until #42 publishes fixtures.

| # | Case | Required answer |
| --- | --- | --- |
| C1 | receipt delivered twice | one effect, two locators |
| C2 | receipt removed | `effect: unknown`, execution still established |
| C3 | M2 failure exported, success missing | line 161 says "the call and its usage are unknown"; read here as: the exported failure record establishes that a call was attempted, its outcome and usage are unknown; this reading is filed against line 161, which does not separate existence from outcome |
| C4 | second service returns ticket id 42 | two effects in two scopes, no merge, no dedup |
| C5 | M2 usage per attempt and as total, no declared aggregation | usage unknown, both levels shown |
| C6 | execution references a denied proposal | both kept, `inconsistent_with_decision`, enforcement unknown |
| C7 | every permutation of the section 10 example's records, exhaustive while the count stays under nine, otherwise seeded shuffles | byte-identical report body (locators excluded, section 2 item 2) |
| C8 | 200 seeded shuffles of a 50-record set | byte-identical report body (locators excluded) |
| C9 | every fixture renamed to a hash | byte-identical report body (locators excluded) |
| C10 | two receipts, same scoped key, different content | `conflict`, count neither one nor two |
| C11 | receipt present, execution absent | effect observed, correlation unresolved |
| C12 | turn without conversation identity | membership unknown, no synthesized conversation (line 47) |
| C13 | resumed work in a new session and trace with the same conversation id | joins the conversation; state `not_answered` |
| C14 | two decisions on one proposal | conflict; no latest-wins |
| C15 | relationship record without establishment method | link unused, loss recorded, dependent answer unknown |
| C16 | duplicate JSON key, `NaN`, BOM, depth over cap, size over cap | processing failure or partial; never a clean report |
| C17 | unknown record kind beside a valid baseline | loss recorded; baseline answers unchanged |
| C18 | usage counter as float or string | counter unknown, loss recorded |

**Must-fail controls on the reader.** Each is a small, named mutant of the reader that must turn at least one named case red: (m1) drop scope from the key, C4 must fail; (m2) index with overwrite instead of multi-value, C10 must fail; (m3) sum usage across levels, C5 must fail; (m4) drop an execution when its decision is a denial, C6 must fail; (m5) compare receipts with Python `==` or after array sorting, C10 with a `1` against `1.0` or a reordered-array difference must fail; (m6) resolve references in arrival order, C7 or C8 must fail; (m7) read the file name, C9 must fail. A mutant that survives is a defect in the case, not evidence about the reader.

These controls measure the sensitivity of specific cases. They do not establish that the case set covers the contract.

## 9. What this design does not settle, and where each goes

| Open point | Contract item | Handling here | Where it should be settled |
| --- | --- | --- | --- |
| Turn entry, suspend, resume, caller context | section 9 items 1 to 4 | `not_answered` | #41 revision, after #43/#44 |
| Scope representation | item 10 | mapping-declared; unresolved scope joins nothing | Task 9 upstream, #41 |
| Usage across providers, hidden retries | item 8 | unknown unless declared | #41 |
| Decision supersession | not in v0.2 | conflict | filed on #51, comment 5712718367 (IC-8) |
| Link without establishment method | line 62 is silent on the missing case | unused (IC-2) | filed on #51, comment 5712718683 |
| What "the same receipt" means | line 91 says "delivered twice", not what equality is | structural equality minus declared delivery fields (IC-11) | #42 fixture definition |
| OTel crosswalk | section 7, pinned revisions | not implemented in the first version; the reader reads the examples' exports through their mapping files, not raw OTel | later adapter, verified against the pinned revisions only |

## 10. Delivery sequence

1. This document is committed with the contract sha and file sha256 above. Later changes to sections 4, 5, 7 and 8 land as revisions with a reason.
2. Implementation starts only when #42 publishes its input format and expected-answer format, or when #43/#44 export records, whichever is first. Until then, the parser (section 3) and the four tables (section 4) can be written and tested against locally authored records, labeled as local.
3. The first implementation commit names language, standard library version, tooling and model family, and freezes the interpretation register version it implements.
4. Cases C1 to C18 and mutants m1 to m7 run locally before any comparison.
5. The comparison against expected answers runs once per pinned fixture revision; every disagreement between the readers is filed against a contract sentence on #41 or #42, and recorded in the report as a finding, not resolved between the readers.

## 11. Non-claims

The reader establishes what the exported records support under the pinned contract. It does not authenticate an export, establish that an export is complete, prove enforcement, prove that an effect occurred, verify hardware or software attestation, or score an agent. Agreement between the two readers is not evidence that the contract is unambiguous: two implementations can share a reading of an ambiguous sentence. The list of sentences they read differently is the result this task exists to produce.
