# Bounded rerun of AAIF O&T PR #57

Kit: `8fa732e3ec597e04a8b667c3669d3ac537e3e98a`.
Contract reader: `6582b65`; reports frozen in `9f1c0fb` BEFORE opening expected
answers. Separate signature implementation/results frozen in `bf39cb2`, also
before expected-answer inspection. These are local commits, not publication.
The README already exposed intended answers; this run was expected-file-blind,
not answer-blind. No run.py or generate.py source was read in this rerun.
Earlier exposure is documented in FINDINGS.md. No independent reviewer claim.

| Case | Contract reader | Separate Ed25519 check |
| --- | --- | --- |
| receipt twice | one scoped effect, two deliveries | both deliveries valid |
| receipt missing | execution established, effect unknown | no receipt to check |
| evidence pair verifies | outside supported contract, not evaluated | valid |
| evidence pair fails | outside supported contract, not evaluated | invalid |

For both R-7 records the re-derived signing input is 126 bytes with SHA-256
`194b732ee70ed682521af21c94fcfedd176ea6240e26fecf6fdaeb3df8a19f22`.
`signatures.json` retains the actual bytes and the supplied key digest. Validity
under this synthetic key is not proof of an independent real service or effect.

## Expected-answer comparison

After freezing the results, all four expected files were read. Their digests,
contents, and the manual field-level assessment are in comparison.json.
There is deliberately no overall pass and no claim of a completed general
DESIGN section 7 comparator or other-reader comparison.

- The two supported cases agree on the narrow observation: one effect despite
  duplicate delivery, and unknown/unconfirmed when the receipt is absent.
- Exact outputs do not match: the reader reports receipt identity/count, not a
  `confirmed_tickets` list. Do not manufacture that list from inputs after the
  report was frozen. This is a reader output/mapping limitation, not an upstream
  defect established by this run.
- Both effects expectations carry `externally_verified` (true for the positive
  case). The v0.7 contract at line 112 says receipts are correlation evidence,
  not cryptographic attestation. Its meaning needs a declared mapping or a
  separate assessment axis before this field can be scored against that reader.
  This is an unresolved basis/meaning question, not proof the kit is wrong.
- The two evidence-grade cases are excluded, not counted as passing contract
  cases. The separate byte check distinguishes their signatures as described.
- Other reader questions remain in the reports and are explicitly unscored by
  this narrow comparison; no fields were deleted to manufacture agreement.

## Verification and remaining limits

62 tests passed (`python3 -m unittest discover -s tests -v`). All 16 existing
mutants killed by assertions. Two further isolated mutants were also killed:
bypass the basis gate; accept every signature. Logs retained here.
`cryptography==46.0.7` is needed only for the separate signature check/tests;
the contract reader remains standard-library-only. Runtime recorded in
signatures.json. No live services, models, agent rankings or coverage claims.

F1's missing machine-readable basis is addressed at this kit pin; local scope
routing is now exercised. F2's missing signing prose is addressed and its ASCII
example actually verified. The bounded string serializer also has a Unicode
escape test, but the prose is not treated as a general canonical-JSON standard.
F3/F4 mapping/default-method/execution-correlation limitations remain.

No external comment was sent. The smallest useful reply would report the scope
fix, the 126-byte verification, and ask what `externally_verified` means for the
ordinary effects cases before claiming a full comparison.
