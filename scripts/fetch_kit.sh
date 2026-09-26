#!/bin/sh
# Fetch the pinned test-kit records and trust key into inputs/. Expected
# answers are fetched into a separate directory the reader never reads.
set -eu
H=afc26fdd2199844bf7dff23879739e941fa81107
R=aaif/wg-observability-and-traceability
cd "$(dirname "$0")/.."
for f in $(gh pr view 57 --repo "$R" --json files --jq '.files[].path'); do
  case "$f" in
    *expected.json) d="inputs/expected-$H/${f#test-kit/cases/}" ;;
    *records.otlp.json|*trust/*|*README.md|*TEMPLATE/*) d="inputs/test-kit-$H/${f#test-kit/}" ;;
    *) continue ;;
  esac
  mkdir -p "$(dirname "$d")"
  gh api "repos/$R/contents/$f?ref=$H" --jq .content | base64 -d > "$d"
done
shasum -a 256 -c inputs.sha256
