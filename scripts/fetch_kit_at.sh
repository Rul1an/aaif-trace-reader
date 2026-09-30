#!/bin/sh
# Fetch the test-kit inputs a reader may use at one pinned kit revision:
# records, basis files, mapping files, README and trust key. Expected answers
# go to a separate directory the reader never reads; run.py and generate.py
# are not fetched, because they carry another reader's source (DESIGN.md s.2).
# Usage: scripts/fetch_kit_at.sh <full kit commit sha>
set -eu
H=$1
R=aaif/wg-observability-and-traceability
cd "$(dirname "$0")/.."
for f in $(gh api "repos/$R/git/trees/$H?recursive=1" --jq '.tree[] | select(.type=="blob") | .path' | grep '^test-kit/'); do
  case "$f" in
    *expected.json) d="inputs/expected-$H/${f#test-kit/cases/}" ;;
    *records.otlp.json|*basis.json|*trust/*|*README.md|*mapping.md) d="inputs/test-kit-$H/${f#test-kit/}" ;;
    *) continue ;;
  esac
  mkdir -p "$(dirname "$d")"
  gh api "repos/$R/contents/$f?ref=$H" --jq .content | base64 -d > "$d"
done
