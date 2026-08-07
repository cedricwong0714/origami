#!/usr/bin/env sh
# Build GitLab Pages artifact from web/ static demos.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-public}"
rm -rf "$OUT"
mkdir -p "$OUT"
cp "$ROOT/web/index.html" "$OUT/index.html"
cp "$ROOT/web/ctpr_scaffold_optimizer.html" "$OUT/ctpr_scaffold_optimizer.html"
cp "$ROOT/web/README.md" "$OUT/README.md"
echo "Pages artifact written to $OUT"
