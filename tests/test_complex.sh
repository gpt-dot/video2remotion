#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 - "$TMP/slide.png" <<'PY'
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
W, H = 960, 540
img = Image.new("RGB", (W, H), (10, 16, 30))
d = ImageDraw.Draw(img)
yy, xx = np.mgrid[0:340, 0:380]
arr = np.zeros((340, 380, 3), dtype=np.uint8)
for c, (base, amp) in enumerate([(30, 180), (90, 120), (140, 100)]):
    arr[..., c] = (base + amp * (0.5 + 0.5 * np.sin(xx / 35 + c) + 0.3 * np.cos(yy / 28 + c))).clip(0, 255)
img.paste(Image.fromarray(arr), (40, 95))
f = ImageFont.truetype("/workspace/ai-video-kit/hyperframes-app/assets/fonts/NotoSansCJKsc-bold.otf", 34)
fb = ImageFont.truetype("/workspace/ai-video-kit/hyperframes-app/assets/fonts/NotoSansCJKsc-regular.otf", 20)
d.text((470, 150), "复杂场景也能转成代码", font=f, fill=(245, 248, 255))
d.text((470, 225), "图片区域自动拆成 MediaCard", font=fb, fill=(210, 220, 240))
d.text((470, 265), "文字位置颜色全部参数化", font=fb, fill=(210, 220, 240))
img.save(sys.argv[1])
PY
ffmpeg -y -v error -loop 1 -i "$TMP/slide.png" -t 3 -r 30 -pix_fmt yuv420p "$TMP/in.mp4"

python3 "$ROOT/video2remotion.py" "$TMP/in.mp4" -o "$TMP/out" \
  --engine code --captions off --max-scenes 4 >/tmp/v2r-complex-smoke.log

test -f "$TMP/out/src/scenes/Scene000.tsx"
grep -q "MediaCard" "$TMP/out/src/scenes/Scene000.tsx"
grep -q "TextBlock" "$TMP/out/src/scenes/Scene000.tsx"
test -n "$(find "$TMP/out/public/crops" -name '*.jpg' -print -quit)"

echo "complex smoke test passed"
