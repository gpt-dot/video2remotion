#!/usr/bin/env python3
"""
video2remotion v2 — 万能视频/图片转 Remotion 工程。

支持输入：
  - 视频（mp4/mov/webm/mkv/gif...）
  - 单张图片
  - 图片文件夹（幻灯片）
  - 图片/文件夹 + 外部音频

自动能力：
  - 镜头切点检测、硬切/淡入淡出判断
  - 场景分类：title / slide / screen / live / static / image
  - 每个场景独立的重建策略与 Ken Burns 参数
  - OCR（tesseract）提取标题/字幕
  - 音频节拍检测，生成画面脉冲
  - 预设：auto / cinematic / slides / social / minimal

用法：
  python3 video2remotion.py input.mp4 -o out
  python3 video2remotion.py input.mp4 -o out --preset cinematic --captions bottom
  python3 video2remotion.py ./images -o out --audio bgm.mp3 --image-duration 2.5
  python3 video2remotion.py cover.png -o out --audio voice.m4a
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

import code_engine

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".gif"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

PRESETS = {
    "auto": {"zoom": 1.0, "fade": 1.0, "caption": "bold", "pulse": 1.0},
    "cinematic": {"zoom": 0.85, "fade": 1.5, "caption": "minimal", "pulse": 0.5, "letterbox": True},
    "slides": {"zoom": 0.25, "fade": 0.8, "caption": "clean", "pulse": 0.0, "letterbox": False},
    "social": {"zoom": 1.25, "fade": 1.0, "caption": "bold", "pulse": 1.3, "letterbox": False},
    "minimal": {"zoom": 0.45, "fade": 0.7, "caption": "off", "pulse": 0.0, "letterbox": False},
}


def die(msg: str) -> None:
    print(f"错误：{msg}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, check=True, text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
    )


def ffprobe(path: Path) -> dict:
    p = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ], capture=True)
    return json.loads(p.stdout)


def parse_fps(rate: str | None) -> float:
    if not rate or rate == "0/0":
        return 30.0
    if "/" in rate:
        a, b = rate.split("/", 1)
        return float(a) / float(b or 1)
    return float(rate)


def media_info(path: Path, kind: str = "video") -> dict:
    data = ffprobe(path)
    streams = data.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration") or 0)
    if kind == "audio":
        duration = duration or float((a or {}).get("duration") or 0)
        return {"duration": duration, "has_audio": a is not None, "width": 0, "height": 0,
                "fps": 30.0, "video_codec": "", "audio_codec": (a or {}).get("codec_name") or ""}
    if not v:
        die("输入文件里没有视频流")
    if duration <= 0:
        duration = float(v.get("duration") or 0)
    if duration <= 0:
        die("读不到媒体时长")
    fps = parse_fps(v.get("avg_frame_rate") or v.get("r_frame_rate"))
    if fps <= 0 or fps > 120:
        fps = 30.0
    return {
        "duration": duration,
        "width": int(v.get("width") or 0),
        "height": int(v.get("height") or 0),
        "fps": fps,
        "has_audio": a is not None,
        "video_codec": v.get("codec_name") or "",
        "audio_codec": (a or {}).get("codec_name") or "",
    }


# ---------------------------------------------------------------------------
# 视频分析
# ---------------------------------------------------------------------------
def extract_samples(path: Path, tmp: Path, sample_fps: float) -> list[Path]:
    out = tmp / "samples"
    out.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-i", str(path),
        "-vf", f"fps={sample_fps},scale=160:-2",
        "-q:v", "4", str(out / "%05d.jpg"),
    ])
    return sorted(out.glob("*.jpg"))


def hist_vector(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB").resize((64, 64))
    arr = np.asarray(im, dtype=np.float32)
    hist, _ = np.histogramdd(
        arr.reshape(-1, 3), bins=(6, 6, 6),
        range=((0, 256), (0, 256), (0, 256)),
    )
    hist = hist.ravel().astype(np.float32)
    total = hist.sum()
    return hist / total if total else hist


def detect_scenes(samples: list[Path], duration: float, sample_fps: float,
                  threshold: float, min_scene: float) -> list[tuple[float, float]]:
    if not samples:
        return [(0.0, duration)]
    hists = [hist_vector(p) for p in samples]
    cuts = [0.0]
    last_cut = 0.0
    for i in range(1, len(hists)):
        diff = float(np.abs(hists[i] - hists[i - 1]).sum() / 2)
        t = i / sample_fps
        if diff >= threshold and t - last_cut >= min_scene:
            cuts.append(t)
            last_cut = t
    cuts.append(duration)

    scenes = [(a, b) for a, b in zip(cuts, cuts[1:]) if b - a > 0.05]
    if len(scenes) > 1 and scenes[0][1] - scenes[0][0] < min_scene:
        scenes[1] = (scenes[0][0], scenes[1][1])
        scenes.pop(0)
    return scenes or [(0.0, duration)]


def merge_to_max(scenes: list[tuple[float, float]], max_scenes: int) -> list[tuple[float, float]]:
    scenes = list(scenes)
    while len(scenes) > max_scenes > 0 and len(scenes) > 1:
        costs = [(scenes[i + 1][1] - scenes[i][0], i) for i in range(len(scenes) - 1)]
        _, i = min(costs)
        scenes[i] = (scenes[i][0], scenes[i + 1][1])
        scenes.pop(i + 1)
    return scenes


def extract_frame(path: Path, t: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{max(0, t):.3f}",
        "-i", str(path), "-frames:v", "1", "-q:v", "2", str(out),
    ])


# 允许出现的超短英文词（缺元音也可能是真实文字）
_SHORT_WORDS = {
    "AI", "UI", "UX", "TV", "VR", "AR", "MR", "XR", "3D", "4K", "8K", "HD", "UHD",
    "OK", "ID", "QR", "PC", "APP", "API", "SDK", "JS", "TS", "CSS", "HTML", "PDF",
    "CPU", "GPU", "RAM", "USB", "WIFI", "LTE", "GPS", "DIY", "VLOG", "MV", "IP",
    "A", "I", "V", "X", "Y", "Z", "C", "R", "K", "S", "M", "B", "Q",
}
_CJK = re.compile(r"[\u4e00-\u9fff]")
_ALNUM = re.compile(r"[0-9A-Za-z]")
_VOWEL = re.compile(r"[AEIOUYaeiouy]")
_WORD_BAD_CHAR = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff&+.'’\-_]")


def _word_ok(word: str) -> bool:
    """判断 OCR 词是否像正常文字，过滤花字/照片纹理噪声。"""
    clean = word.strip(".,:;!?()[]{}\"'“”‘’·•|/\\")
    if not clean:
        return False
    if _CJK.search(clean):
        return True
    if not _ALNUM.search(clean):
        return False
    if _WORD_BAD_CHAR.search(clean):
        return False
    letters = re.sub(r"[^A-Za-z]", "", clean)
    if not letters:
        return True
    if len(letters) == 1:
        # 单字母只放行常见缩写；带数字的字母数字混合码（A890）不算
        return clean.upper() in _SHORT_WORDS or bool(re.search(r"\d", clean))
    if not _VOWEL.search(letters):
        # 全辅音串（MLL / TSI / XKQ）基本是误识别
        return clean.upper() in _SHORT_WORDS
    return True


def _clean_line(words: list[tuple[str, float]], conf: float) -> tuple[str, bool]:
    """返回清洗后的整行文字，以及该行是否可信。"""
    if not words:
        return "", False
    kept: list[str] = []
    hard_bad = 0
    for w, _c in words:
        if _word_ok(w):
            kept.append(w)
        else:
            letters = re.sub(r"[^A-Za-z]", "", w)
            if len(letters) >= 3 and not _VOWEL.search(letters):
                hard_bad += 1
    ratio = len(kept) / len(words)
    text = re.sub(r"\s+", " ", " ".join(kept)).strip()
    # 中文被 tesseract 拆成单字时，去掉汉字之间的空格
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"^[\s\-–—:;,.|/]+|[\s\-–—:;,.|/]+$", "", text).strip()
    useful = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    if len(useful) < 2:
        return "", False
    if conf < 55 or ratio < 0.7:
        return "", False
    # 行内出现纯辅音长串，且可信词不足八成：整行按噪声丢弃
    if hard_bad and ratio < 0.8:
        return "", False
    # 大量单字符碎片，典型的花字/纹理误识别（中文逐字切分不算）
    singletons = sum(
        1 for w, _c in words
        if len(re.sub(r"\W", "", w)) <= 1 and not _CJK.search(w)
    )
    if len(words) >= 3 and singletons / len(words) > 0.4:
        return "", False
    # 全大写短行（型号/设备标签/花字误读）：元音太少且置信度不高就丢弃
    if not _CJK.search(text):
        tokens = text.split()
        letters = "".join(re.sub(r"[^A-Za-z]", "", t) for t in tokens if not re.search(r"\d", t))
        if (tokens and not any(c.islower() for c in text) and len(tokens) <= 3
                and len(letters) >= 3 and len(_VOWEL.findall(letters)) / len(letters) < 0.34
                and conf < 88):
            return "", False
    return text, True


def _ocr_image(path: Path) -> tuple[Path, bool]:
    """放大 + 灰度 + 锐化，提高小字/花字识别率。返回临时文件路径。"""
    try:
        im = Image.open(path).convert("L")
        w, h = im.size
        scale = max(1.0, 1600.0 / max(1, w))
        if scale > 1.0:
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        im = ImageOps.autocontrast(im, cutoff=1)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=3))
        fd, name = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        im.save(name)
        return Path(name), True
    except Exception:
        return path, False


def ocr_details(path: Path, lang: str) -> dict:
    """返回文字、行框、文字面积占比。失败时返回空结构。"""
    empty = {"text": "", "lines": [], "title_lines": [], "area": 0.0, "conf": 0.0}
    if not shutil.which("tesseract"):
        return empty
    ocr_path, is_temp = _ocr_image(path)
    try:
        p = run([
            "tesseract", str(ocr_path), "stdout", "-l", lang, "--psm", "6",
            "-c", "tessedit_char_blacklist=£¥€|<>{}[]~^©®™", "tsv",
        ], capture=True)
    except subprocess.CalledProcessError:
        return empty
    finally:
        if is_temp:
            try:
                ocr_path.unlink()
            except OSError:
                pass
    rows = list(csv.DictReader(io.StringIO(p.stdout or ""), delimiter="\t"))
    grouped: dict[tuple, dict] = {}
    for row in rows:
        txt = (row.get("text") or "").strip()
        if not txt:
            continue
        try:
            conf = float(row.get("conf") or -1)
        except ValueError:
            conf = -1
        if conf < 45:
            continue
        useful = re.sub(r"[^\w\u4e00-\u9fff]", "", txt)
        if len(useful) < 1:
            continue
        key = (row.get("block_num"), row.get("par_num"), row.get("line_num"))
        left = int(float(row.get("left") or 0))
        top = int(float(row.get("top") or 0))
        w = int(float(row.get("width") or 0))
        h = int(float(row.get("height") or 0))
        g = grouped.setdefault(key, {"words": [], "x0": left, "y0": top, "x1": left + w,
                                      "y1": top + h, "conf": []})
        g["words"].append((txt, conf))
        g["x0"] = min(g["x0"], left)
        g["y0"] = min(g["y0"], top)
        g["x1"] = max(g["x1"], left + w)
        g["y1"] = max(g["y1"], top + h)
        g["conf"].append(conf)

    with Image.open(path) as im:
        fw, fh = im.size
    lines = []
    for g in grouped.values():
        conf = sum(g["conf"]) / len(g["conf"])
        text, ok = _clean_line(g["words"], conf)
        if not ok:
            continue
        lines.append({
            "text": text,
            "x0": g["x0"] / fw, "y0": g["y0"] / fh,
            "x1": g["x1"] / fw, "y1": g["y1"] / fh,
            "conf": conf,
        })
    lines.sort(key=lambda x: (x["y0"], x["x0"]))
    # 去掉同一位置的重复行
    deduped = []
    for l in lines:
        if any(l["text"] == q["text"] and abs(l["y0"] - q["y0"]) < 0.02 for q in deduped):
            continue
        deduped.append(l)
    lines = deduped
    area = sum(max(0, l["x1"] - l["x0"]) * max(0, l["y1"] - l["y0"]) for l in lines)
    text = " ".join(l["text"] for l in lines[:3])[:120]
    return {
        "text": text,
        "lines": lines,
        "title_lines": [l["text"] for l in lines[:3]][:3],
        "area": min(1.0, area),
        "conf": float(np.mean([l["conf"] for l in lines])) if lines else 0.0,
    }


def color_info(path: Path) -> tuple[str, str]:
    im = Image.open(path).convert("RGB").resize((96, 96))
    q = im.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    palette = q.getpalette() or []
    counts = sorted(q.getcolors() or [], reverse=True)
    colors = []
    for count, idx in counts:
        r, g, b = palette[idx * 3: idx * 3 + 3]
        colors.append((count, (r, g, b)))
    if not colors:
        return "#05070d", "#56beff"

    def sat(c):
        return (max(c) - min(c)) / 255

    accent = max(colors, key=lambda x: sat(x[1]) * (x[0] ** 0.35))[1]
    if max(accent) < 120:
        accent = (86, 190, 255)
    base = colors[0][1]
    bg = tuple(int(v * 0.16 + 6) for v in base)
    return "#%02x%02x%02x" % bg, "#%02x%02x%02x" % accent


def motion_amount(samples: list[Path], start: float, end: float, sample_fps: float) -> float:
    a = max(0, int(start * sample_fps))
    b = min(len(samples) - 1, int(end * sample_fps))
    if b <= a:
        return 0.0
    im1 = np.asarray(Image.open(samples[a]).convert("L").resize((64, 64)), dtype=np.float32)
    im2 = np.asarray(Image.open(samples[b]).convert("L").resize((64, 64)), dtype=np.float32)
    return float(np.abs(im1 - im2).mean() / 255.0)


def edge_density(path: Path) -> float:
    im = Image.open(path).convert("L").resize((160, 160)).filter(ImageFilter.FIND_EDGES)
    return float(np.asarray(im, dtype=np.float32).mean() / 255.0)


def classify_scene(motion: float, ocr: dict, edges: float) -> str:
    text = ocr.get("text") or ""
    lines = ocr.get("lines") or []
    area = float(ocr.get("area") or 0)
    n = len(lines)
    text_len = len(re.sub(r"[^\w\u4e00-\u9fff]", "", text))
    # 大字号、少量行：优先按标题卡重建（即使有入场动画）
    if 1 <= n <= 3 and area >= 0.035 and text_len >= 3:
        return "title"
    if n >= 4 and area >= 0.025:
        return "screen" if edges > 0.09 else "slide"
    if n >= 2 and area >= 0.012 and motion < 0.06:
        return "slide"
    if motion >= 0.09:
        return "live"
    if text_len >= 3 and motion < 0.055:
        return "title"
    if motion < 0.012:
        return "static"
    return "live"


def detect_transitions(hists: list[np.ndarray], scenes: list[tuple[float, float]],
                       sample_fps: float) -> list[dict]:
    out = []
    for i in range(len(scenes)):
        if i == len(scenes) - 1:
            out.append({"type": "cut", "duration": 0.0})
            continue
        t = scenes[i][1]
        idx = min(len(hists) - 1, max(1, int(t * sample_fps)))
        d = float(np.abs(hists[idx] - hists[idx - 1]).sum() / 2)
        around = [
            float(np.abs(hists[j] - hists[j - 1]).sum() / 2)
            for j in range(max(1, idx - 3), min(len(hists), idx + 4))
        ]
        baseline = float(np.mean(around)) if around else d
        sharpness = d / (baseline + 1e-6)
        if d >= 0.50 or sharpness >= 2.2:
            out.append({"type": "cut", "duration": 0.0})
        elif d >= 0.24:
            out.append({"type": "fade", "duration": 0.22})
        else:
            out.append({"type": "fade", "duration": 0.12})
    return out


# ---------------------------------------------------------------------------
# 音频节拍
# ---------------------------------------------------------------------------
def extract_wav(path: Path, out: Path) -> bool:
    try:
        run([
            "ffmpeg", "-y", "-v", "error", "-i", str(path),
            "-vn", "-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", str(out),
        ])
        return True
    except subprocess.CalledProcessError:
        return False


def analyze_beats(wav_path: Path) -> dict:
    empty = {"bpm": 0.0, "beats": []}
    try:
        with wave.open(str(wav_path), "rb") as wf:
            sr = wf.getframerate()
            n = wf.getnframes()
            raw = wf.readframes(n)
    except Exception:
        return empty
    if not raw:
        return empty
    audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    win = max(256, int(sr * 0.04))
    hop = max(128, win // 2)
    frames = max(0, 1 + (len(audio) - win) // hop)
    if frames < 4:
        return empty
    rms = np.array([
        float(np.sqrt(np.mean(audio[i * hop: i * hop + win] ** 2)))
        for i in range(frames)
    ], dtype=np.float32)
    onset = np.maximum(0, np.diff(rms))
    if not onset.size:
        return empty
    kernel = np.ones(3, dtype=np.float32) / 3
    onset = np.convolve(onset, kernel, mode="same")
    thresh = float(onset.mean() + 0.9 * onset.std())
    peaks = []
    min_gap = max(1, int(0.22 * sr / hop))
    last = -min_gap
    for i in range(1, len(onset) - 1):
        if onset[i] >= thresh and onset[i] >= onset[i - 1] and onset[i] >= onset[i + 1]:
            if i - last >= min_gap:
                peaks.append(i * hop / sr)
                last = i
    if len(peaks) < 2:
        return empty
    gaps = np.diff(peaks)
    gaps = gaps[(gaps > 0.2) & (gaps < 2.0)]
    bpm = float(60 / np.median(gaps)) if len(gaps) else 0.0
    if bpm < 50:
        bpm *= 2
    if bpm > 190:
        bpm /= 2
    return {"bpm": round(bpm, 1), "beats": [round(float(b), 3) for b in peaks[:400]]}


# ---------------------------------------------------------------------------
# 图片输入
# ---------------------------------------------------------------------------
def image_paths(path: Path) -> list[Path]:
    if path.is_dir():
        items = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
        return sorted(items, key=lambda p: p.name.lower())
    if path.suffix.lower() in IMAGE_EXTS:
        return [path]
    return []


def prepare_images(paths: list[Path], out: Path, fps: int, image_duration: float,
                   audio: Path | None) -> tuple[dict, list[dict], list[str], list[tuple[str, str]]]:
    if not paths:
        die("图片目录为空")
    first = Image.open(paths[0]).convert("RGB")
    width, height = first.size
    audio_dur = 0.0
    has_audio = False
    if audio:
        ai = media_info(audio, "audio")
        audio_dur = ai["duration"]
        has_audio = audio_dur > 0
    total = audio_dur if has_audio else len(paths) * image_duration
    if total <= 0:
        total = len(paths) * image_duration
    per_image = total if (len(paths) == 1 and has_audio) else image_duration
    count = max(1, math.ceil(total / max(0.2, per_image)))
    seq = [paths[i % len(paths)] for i in range(count)]

    frames_dir = out / "public" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    scenes = []
    srcs, colors = [], []
    for i, p in enumerate(seq):
        key = str(p.resolve())
        if key not in copied:
            dst = frames_dir / f"scene-{i:03d}{p.suffix.lower()}"
            shutil.copy2(p, dst)
            copied[key] = f"frames/{dst.name}"
        src = copied[key]
        srcs.append(src)
        bg, accent = color_info(p)
        colors.append((bg, accent))
        start = i * per_image
        end = min(total, (i + 1) * per_image)
        if end - start < 0.1:
            continue
        scenes.append({
            "start": start, "end": end, "src": src, "kind": "image",
            "text": "", "title_lines": [], "lines": [], "area": 0.0, "motion": 0.0,
            "edges": 0.0, "transition": {"type": "fade", "duration": 0.25},
            "bg": bg, "accent": accent,
        })
    info = {"duration": total, "width": width, "height": height, "fps": fps,
            "has_audio": has_audio, "video_codec": "image", "audio_codec": "",
            "source": paths[0].parent.name if len(paths) > 1 else paths[0].name}
    return info, scenes, srcs, colors


# ---------------------------------------------------------------------------
# 时间线与生成
# ---------------------------------------------------------------------------
def build_timeline(info: dict, scenes_raw: list[dict], fps: int, total_frames: int,
                   preset: str, captions: str, beats: list[float]) -> dict:
    p = PRESETS.get(preset, PRESETS["auto"])
    scenes = []
    cursor = 0
    n = len(scenes_raw)
    kind_amp = {"title": 0.055, "slide": 0.025, "screen": 0.035,
                "live": 0.09, "static": 0.018, "image": 0.05}
    kind_fade = {"title": 0.28, "slide": 0.14, "screen": 0.14,
                 "live": 0.20, "static": 0.16, "image": 0.24}
    for i, s in enumerate(scenes_raw):
        from_frame = cursor
        if i == n - 1:
            to_frame = total_frames
        else:
            to_frame = max(cursor + 1, round(s["end"] * fps))
        dur = max(1, to_frame - from_frame)
        cursor = from_frame + dur

        kind = s.get("kind", "live")
        amp = kind_amp.get(kind, 0.06) * p["zoom"]
        amp = max(0.0, min(0.14, amp))
        fade = kind_fade.get(kind, 0.18) * p["fade"]
        if s.get("transition", {}).get("type") == "fade":
            fade = max(fade, s["transition"].get("duration", 0.15))
        fade = max(0.04, min(0.8, fade))
        if i % 2 == 0:
            zoom_from, zoom_to = 1.0, 1.0 + amp
        else:
            zoom_from, zoom_to = 1.0 + amp, 1.0
        pan_x = 0.0 if kind in ("slide", "screen", "title") else (1.1 if i % 3 == 0 else -1.1)
        pan_y = 0.0 if kind in ("slide", "screen", "title") else (-0.7 if i % 2 == 0 else 0.7)

        caption = None
        if captions in ("top", "bottom") and s.get("text"):
            # 显式要求时才给所有场景加字幕（包括标题/幻灯片）
            caption = {"text": s["text"][:64], "position": captions}
        elif captions == "auto" and s.get("text") and kind == "live":
            # 智能模式：只给“文字占画面很小”的实拍/口播镜头补字幕，避免和幻灯片文字重复
            if float(s.get("area") or 0) < 0.02:
                caption = {"text": s["text"][:64], "position": "bottom"}

        scenes.append({
            "id": f"scene-{i:03d}",
            "from": from_frame,
            "durationInFrames": dur,
            "src": s["src"],
            "fit": "cover",
            "background": s.get("bg", "#05070d"),
            "accent": s.get("accent", "#56beff"),
            "kind": kind,
            "zoom": {"from": round(zoom_from, 4), "to": round(zoom_to, 4)},
            "pan": {"x": round(pan_x, 2), "y": round(pan_y, 2)},
            "fade": round(fade, 3),
            "titleLines": s.get("title_lines", []) if kind == "title" else [],
            "caption": caption,
            "pulse": round(p["pulse"] * (1.0 if kind in ("live", "static", "image") else 0.4), 2),
        })

    return {
        "video": {
            "fps": fps,
            "width": info["width"],
            "height": info["height"],
            "durationInFrames": total_frames,
            "background": "#05070d",
            "audio": "audio/audio.m4a" if info["has_audio"] else None,
            "source": info.get("source", ""),
            "scenes": len(scenes),
            "preset": preset,
            "letterbox": bool(p.get("letterbox", False)),
            "captionStyle": p["caption"],
            "bpm": 0.0,
            "beats": [round(b * fps) for b in beats if 0 <= b * fps < total_frames],
        },
        "scenes": scenes,
    }


def write_timeline(out: Path, timeline: dict) -> None:
    video = json.dumps(timeline["video"], ensure_ascii=False, indent=2)
    scenes = json.dumps(timeline["scenes"], ensure_ascii=False, indent=2)
    content = f'''// 由 video2remotion v2 自动生成。可直接修改分镜数据，或在组件里加自己的动画。
export type CaptionData = {{
  text: string;
  position: 'top' | 'bottom';
}};

export type Scene = {{
  id: string;
  from: number;
  durationInFrames: number;
  src: string;
  fit: 'cover' | 'contain';
  background: string;
  accent: string;
  kind: 'title' | 'slide' | 'screen' | 'live' | 'static' | 'image';
  zoom: {{from: number; to: number}};
  pan: {{x: number; y: number}};
  fade: number;
  titleLines: string[];
  caption: CaptionData | null;
  pulse: number;
}};

export type VideoMeta = {{
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  background: string;
  audio: string | null;
  source: string;
  scenes: number;
  preset: string;
  letterbox: boolean;
  captionStyle: string;
  bpm: number;
  beats: number[];
}};

export const video: VideoMeta = {video};

export const scenes: Scene[] = {scenes};
'''
    (out / "src" / "timeline.ts").write_text(content, encoding="utf-8")


def copy_templates(out: Path) -> None:
    for src in TEMPLATES.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATES)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def write_readme(out: Path, info: dict, timeline: dict, args) -> None:
    v = timeline["video"]
    kinds = {}
    for s in timeline["scenes"]:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    kind_text = " / ".join(f"{k}×{n}" for k, n in sorted(kinds.items()))
    lines = [
        "# Video → Remotion 工程（v2 万能模式）",
        "",
        f"- 源文件：`{Path(args.input).name}`",
        f"- 时长：{info['duration']:.2f}s / {v['fps']}fps / {v['durationInFrames']} 帧",
        f"- 分辨率：{v['width']}×{v['height']}",
        f"- 分镜：{len(timeline['scenes'])} 个（{kind_text}）",
        f"- 预设：`{v['preset']}`",
        f"- BPM：{v['bpm'] or '未检测到'}",
        f"- 音频：{'已提取' if v['audio'] else '无'}",
        f"- OCR 字幕：{'已生成' if args.captions != 'off' else '未生成'}",
        "",
        "## 使用",
        "",
        "```bash",
        "npm install",
        "npm run start      # Remotion Studio",
        "npm run render     # out/video.mp4",
        "```",
        "",
        "## 结构",
        "",
        "```text",
        "public/frames/              每个镜头的关键帧/图片",
        "public/audio/               源音轨",
        "src/timeline.ts             分镜时间线（可直接改）",
        "src/VideoFromFootage.tsx    主合成",
        "src/components/SceneView.tsx 按场景类型渲染",
        "src/components/TitleScene.tsx 文字标题场景",
        "src/components/Caption.tsx  字幕层",
        "```",
        "",
        "## 调整建议",
        "",
        "- 改节奏：调 `timeline.ts` 里的 `from` / `durationInFrames`。",
        "- 改运镜：调 `zoom` / `pan`；想完全静止就把两个 zoom 都设 1.0。",
        "- 改转场：`fade` 是淡入淡出秒数；想要硬切就设 0.04。",
        "- 改标题：`kind: 'title'` 的场景会把 OCR 文字重新排版，`titleLines` 可手改。",
        "- 关节拍：`video.beats` 是检测到的节拍帧；`pulse` 控制脉冲强度。",
        "",
        "> v2 会按场景类型选择策略：文字卡重新排版、幻灯片轻微推近、屏幕录制稳定呈现、实拍 Ken Burns。",
        "> 不是像素级还原；OCR 可能有错字，生成后可在 `timeline.ts` 里修。",
        "",
    ]
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="万能视频/图片 → Remotion 工程")
    ap.add_argument("input", help="视频、GIF、图片或图片文件夹")
    ap.add_argument("-o", "--output", help="输出目录")
    ap.add_argument("--preset", choices=list(PRESETS), default="auto")
    ap.add_argument("--engine", choices=["code", "media", "auto"], default="code",
                    help="code=参数化组件（默认）；media=关键帧 Sequence；auto=同 code")
    ap.add_argument("--fps", type=float, help="输出帧率（默认跟随源视频）")
    ap.add_argument("--width", type=int, help="输出宽度")
    ap.add_argument("--height", type=int, help="输出高度")
    ap.add_argument("--threshold", type=float, default=0.35, help="镜头切点阈值")
    ap.add_argument("--min-scene", type=float, default=0.8, help="最短镜头秒数")
    ap.add_argument("--max-scenes", type=int, default=24, help="最多镜头数，0=自动")
    ap.add_argument("--sample-fps", type=float, default=4.0, help="采样帧率")
    ap.add_argument("--captions", choices=["off", "auto", "top", "bottom"], default="off")
    ap.add_argument("--lang", default="chi_sim+eng", help="OCR 语言包")
    ap.add_argument("--audio", help="图片/图片文件夹模式使用的音频")
    ap.add_argument("--image-duration", type=float, default=3.0, help="每张图片秒数")
    ap.add_argument("--no-audio", action="store_true", help="不提取音频")
    ap.add_argument("--no-beat", action="store_true", help="不检测节拍")
    ap.add_argument("--max-regions", type=int, default=2,
                    help="每个复杂场景最多拆出几个图片/UI 区域（0=关闭）")
    ap.add_argument("--no-dynamic", dest="dynamic", action="store_false",
                    help="关闭区域动态检测（不裁区域视频，只用静态 MediaCard）")
    ap.add_argument("--no-matting", dest="matting", action="store_false",
                    help="关闭对象级抠像（使用矩形 MediaCard/MotionCard）")
    args = ap.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        die("需要 ffmpeg / ffprobe，请先安装")
    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        die(f"找不到输入：{src}")

    if src.is_dir():
        imgs = image_paths(src)
        if not imgs:
            die(f"目录里没有支持的图片：{src}")
    else:
        imgs = image_paths(src) if src.suffix.lower() in IMAGE_EXTS else []
    is_image_mode = bool(imgs)
    audio_path = Path(args.audio).expanduser().resolve() if args.audio else None
    if audio_path and not audio_path.is_file():
        die(f"找不到音频：{audio_path}")

    out = Path(args.output).expanduser().resolve() if args.output else src.with_name(
        (src.stem if src.is_file() else src.name) + "-remotion")
    if out.exists() and any(out.iterdir()):
        die(f"输出目录非空：{out}")
    out.mkdir(parents=True, exist_ok=True)

    if is_image_mode:
        fps = int(round(args.fps or 30))
        info, raw, _, _ = prepare_images(imgs, out, fps, args.image_duration, audio_path)
        if args.width:
            info["width"] = args.width
        if args.height:
            info["height"] = args.height
        print(f"输入：{len(imgs)} 张图片  {info['width']}×{info['height']}  总时长 {info['duration']:.2f}s  {fps}fps")
    else:
        info = media_info(src)
        info["source"] = src.name
        fps = int(round(args.fps or info["fps"]))
        print(f"输入：{src.name}  {info['width']}×{info['height']}  {info['duration']:.2f}s  {fps}fps")
        print("检测镜头切点...")
        with tempfile.TemporaryDirectory(prefix="v2r-") as td:
            tmp = Path(td)
            samples = extract_samples(src, tmp, args.sample_fps)
            raw_ranges = detect_scenes(samples, info["duration"], args.sample_fps,
                                       args.threshold, args.min_scene)
            max_scenes = args.max_scenes
            if max_scenes <= 0:
                max_scenes = max(4, min(60, int(info["duration"] / 2)))
            raw_ranges = merge_to_max(raw_ranges, max_scenes)
            hists = [hist_vector(p) for p in samples]
            transitions = detect_transitions(hists, raw_ranges, args.sample_fps)
            print(f"检测到 {len(raw_ranges)} 个镜头")

            public_frames = out / "public" / "frames"
            public_frames.mkdir(parents=True, exist_ok=True)
            raw = []
            for i, ((start, end), tr) in enumerate(zip(raw_ranges, transitions)):
                t = start + (end - start) * 0.35
                frame_path = public_frames / f"scene-{i:03d}.jpg"
                extract_frame(src, t, frame_path)
                ocr = ocr_details(frame_path, args.lang)
                motion = motion_amount(samples, start, end, args.sample_fps)
                edges = edge_density(frame_path)
                kind = classify_scene(motion, ocr, edges)
                bg, accent = color_info(frame_path)
                raw.append({
                    "start": start, "end": end, "src": f"frames/{frame_path.name}",
                    "kind": kind, "text": ocr["text"], "title_lines": ocr["title_lines"],
                    "lines": ocr["lines"], "area": ocr["area"], "motion": motion, "edges": edges,
                    "transition": tr, "bg": bg, "accent": accent,
                })
                if i % 8 == 0 or i == len(raw_ranges) - 1:
                    print(f"  场景 {i + 1}/{len(raw_ranges)}  {kind}")

    fps = max(1, min(60, int(round(args.fps or info["fps"])) if not is_image_mode else fps))
    if args.width:
        info["width"] = args.width
    if args.height:
        info["height"] = args.height
    if info["width"] <= 0 or info["height"] <= 0:
        die("读不到分辨率")

    total_frames = max(1, int(round(info["duration"] * fps)))

    # 音频提取 & 节拍
    beats: list[float] = []
    audio_bpm = 0.0
    audio_src = audio_path if is_image_mode else (src if info.get("has_audio") else None)
    if audio_src and not args.no_audio:
        audio_dir = out / "public" / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        print("提取音频...")
        run(["ffmpeg", "-y", "-v", "error", "-i", str(audio_src), "-vn",
             "-c:a", "aac", "-b:a", "192k", str(audio_dir / "audio.m4a")])
        info["has_audio"] = True
        if not args.no_beat:
            print("检测节拍...")
            with tempfile.TemporaryDirectory(prefix="v2r-audio-") as td:
                wav = Path(td) / "a.wav"
                if extract_wav(audio_src, wav):
                    b = analyze_beats(wav)
                    beats = b["beats"]
                    audio_bpm = b["bpm"]
                    print(f"  BPM≈{b['bpm'] or 'N/A'}，{len(beats)} 个节拍")
    else:
        info["has_audio"] = False

    if args.engine in ("code", "auto"):
        print("生成代码驱动组件...")
        letterbox = bool(PRESETS.get(args.preset, {}).get("letterbox", False))
        result = code_engine.generate_project(
            out, info, raw, fps, total_frames, args.preset, args.captions,
            audio_bpm, beats, letterbox, args.max_regions,
            None if is_image_mode else src, args.dynamic, args.matting,
        )
        print()
        print(f"完成：{out}")
        print(f"  分镜 {len(result['scenes'])} 个，{total_frames} 帧，{fps}fps")
        print(f"  纯代码 {result['graphic']} 个 / 混合 {result['hybrid']} 个 / 素材 {result['media']} 个")
        if result.get("clips"):
            print(f"  动态区域 {result['clips']} 个（已裁成 MotionCard 视频）")
        if result.get("objects"):
            print(f"  对象抠像 {result['objects']} 个（ObjectImage / ObjectCard）")
        print("  每个场景都是独立 TSX，可直接改文字、位置、颜色、动画。")
        print("  下一步：")
        print(f"    cd {out}")
        print("    npm install && npm run start")
        return

    timeline = build_timeline(info, raw, fps, total_frames, args.preset, args.captions, beats)
    timeline["video"]["bpm"] = audio_bpm

    copy_templates(out)
    write_timeline(out, timeline)
    (out / "analysis.json").write_text(json.dumps({
        "source": info, "timeline": timeline,
        "scenes": [{k: v for k, v in s.items()} for s in raw],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    write_readme(out, info, timeline, args)

    print()
    print(f"完成：{out}")
    print(f"  分镜 {len(timeline['scenes'])} 个，{total_frames} 帧，{fps}fps")
    print(f"  类型：{', '.join(sorted({s['kind'] for s in timeline['scenes']}))}")
    print("  下一步：")
    print(f"    cd {out}")
    print("    npm install && npm run start")


if __name__ == "__main__":
    main()
