#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ffmpeg -y -v error -f lavfi -i "testsrc=size=320x240:rate=30" -t 2 \
  -pix_fmt yuv420p "$TMP/input.mp4"

python3 "$ROOT/video2remotion.py" "$TMP/input.mp4" -o "$TMP/out" \
  --max-scenes 4 --threshold 0.6 --captions off >/tmp/v2r-smoke.log

test -f "$TMP/out/src/timeline.ts"
test -f "$TMP/out/src/VideoFromFootage.tsx"
test -f "$TMP/out/src/theme.ts"
test -f "$TMP/out/src/config.ts"
test -f "$TMP/out/src/scenes/Scene000.tsx"
test -f "$TMP/out/src/components/TextBlock.tsx"
test -f "$TMP/out/public/frames/scene-000.jpg"
test -f "$TMP/out/package.json"
grep -q 'export const scenes' "$TMP/out/src/timeline.ts"
grep -q 'durationInFrames' "$TMP/out/src/timeline.ts"
grep -q 'TextBlock\|MediaLayer' "$TMP/out/src/scenes/Scene000.tsx"

echo "smoke test passed"
