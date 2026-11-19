#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/images"
python3 - "$TMP/images" <<'PY'
import sys
from PIL import Image, ImageDraw
for i, color in enumerate([(30, 50, 90), (90, 30, 50), (30, 90, 60)]):
    im = Image.new("RGB", (480, 854), color)
    d = ImageDraw.Draw(im)
    d.rectangle([50, 320, 430, 520], fill=(245, 245, 245))
    im.save(f"{sys.argv[1]}/s{i}.png")
PY
ffmpeg -y -v error -f lavfi -i "sine=frequency=220:duration=4" -c:a aac "$TMP/bgm.m4a"

python3 "$ROOT/video2remotion.py" "$TMP/images" -o "$TMP/out" \
  --audio "$TMP/bgm.m4a" --image-duration 2 --preset social >/tmp/v2r-image-smoke.log

test -f "$TMP/out/src/timeline.ts"
test -f "$TMP/out/public/audio/audio.m4a"
test -f "$TMP/out/public/frames/scene-000.png"
grep -q '"kind": "image"' "$TMP/out/src/timeline.ts"
grep -q 'export const beats' "$TMP/out/src/timeline.ts"

echo "image smoke test passed"
