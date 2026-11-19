#!/usr/bin/env python3
"""代码驱动引擎：把分镜分析结果生成参数化 Remotion 组件。

设计：
  - 标题 / 幻灯片 / 屏幕录制：文字、列表、色块、布局全部生成 TSX，不依赖整帧截图
  - 实拍 / 图片：生成 MediaLayer 组件（图片是素材，但布局/动画/参数仍是代码）
  - 全局主题、时间线、每个场景一个可编辑的 SceneXXX.tsx
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

TEMPLATES = Path(__file__).resolve().parent / "templates_code"

BULLET_RE = re.compile(r"^\s*[•·●▪◦\-–—*]\s*")


def _hex(rgb) -> str:
    r, g, b = [max(0, min(255, int(v))) for v in rgb]
    return f"#{r:02x}{g:02x}{b:02x}"


def _dist(a, b) -> float:
    return float(np.linalg.norm(np.array(a, dtype=np.float32) - np.array(b, dtype=np.float32)))


def _sample(img, x, y, w, h):
    hgt, wid = img.shape[:2]
    x0, y0 = max(0, int(x * wid)), max(0, int(y * hgt))
    x1, y1 = min(wid, max(x0 + 1, int((x + w) * wid))), min(hgt, max(y0 + 1, int((y + h) * hgt)))
    patch = img[y0:y1, x0:x1].reshape(-1, 3)
    return patch.mean(axis=0) if patch.size else np.array([0, 0, 0])


def background_css(path: str) -> str:
    img = cv2.imread(path)
    if img is None:
        return "#05070d"
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    top = img[: max(1, h // 12)].reshape(-1, 3).mean(axis=0)
    bottom = img[-max(1, h // 12):].reshape(-1, 3).mean(axis=0)
    if _dist(top, bottom) > 24:
        return f"linear-gradient(180deg, {_hex(top)} 0%, {_hex(bottom)} 100%)"
    small = cv2.resize(img, (80, 80)).reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
    _, labels, centers = cv2.kmeans(small, 3, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.ravel(), minlength=3)
    return _hex(centers[int(np.argmax(counts))])


def text_color(path: str, line: dict, bg_rgb) -> str:
    img = cv2.imread(path)
    if img is None:
        return "#f7fbff"
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    x0, y0 = max(0, int(line["x0"] * w)), max(0, int(line["y0"] * h))
    x1, y1 = min(w, int(line["x1"] * w)), min(h, int(line["y1"] * h))
    if x1 <= x0 or y1 <= y0:
        return "#f7fbff"
    patch = img[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
    if len(patch) < 8:
        return "#f7fbff"
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.0)
    _, labels, centers = cv2.kmeans(patch, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    c0, c1 = centers[0], centers[1]
    picked = c0 if _dist(c0, bg_rgb) >= _dist(c1, bg_rgb) else c1
    # 避免文字颜色和背景太近
    if _dist(picked, bg_rgb) < 28:
        return "#f7fbff"
    return _hex(picked)


def detect_panels(path: str, bg_hex: str) -> list[dict]:
    """检测大面积、矩形度高的纯色块（卡片/侧栏/色带）。"""
    img = cv2.imread(path)
    if img is None:
        return []
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    scale = 320 / max(1, w)
    small = cv2.resize(img, (320, max(1, int(h * scale))))
    sh, sw = small.shape[:2]
    z = small.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 14, 1.0)
    _, labels, centers = cv2.kmeans(z, 6, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    bg = np.array([int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)])
    panels = []
    for k in range(6):
        center = centers[k]
        if _dist(center, bg) < 22:
            continue
        mask = (labels.ravel() == k).reshape(sh, sw).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if area <= 0:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            ratio = area / max(1, bw * bh)
            frac = area / (sw * sh)
            if ratio < 0.72 or not (0.025 < frac < 0.5):
                continue
            if bw < 12 or bh < 12:
                continue
            panels.append({
                "x": x / sw, "y": y / sh, "w": bw / sw, "h": bh / sh,
                "fill": _hex(center), "radius": 0.018, "opacity": 0.92,
                "area": frac,
            })
    panels.sort(key=lambda p: p["area"], reverse=True)
    # 去重/重叠
    out = []
    for p in panels:
        if all(abs(p["x"] - q["x"]) > 0.03 or abs(p["y"] - q["y"]) > 0.03 for q in out):
            out.append(p)
        if len(out) >= 2:
            break
    for p in out:
        p.pop("area", None)
    return out


def detect_media_regions(path: str, lines: list[dict], crops_dir: Path,
                         scene_id: str, max_regions: int = 2) -> list[dict]:
    """检测画面里高信息量的矩形区域（照片/插图/UI 卡片），裁成素材卡片。"""
    if max_regions <= 0:
        return []
    img = cv2.imread(path)
    if img is None:
        return []
    h, w = img.shape[:2]

    # 文字遮罩（像素级），用于排除 OCR 区域
    text_mask = np.zeros((h, w), dtype=np.uint8)
    for line in lines:
        x0 = max(0, int(line["x0"] * w) - 10)
        y0 = max(0, int(line["y0"] * h) - 10)
        x1 = min(w, int(line["x1"] * w) + 10)
        y1 = min(h, int(line["y1"] * h) + 10)
        cv2.rectangle(text_mask, (x0, y0), (x1, y1), 255, -1)
    text_mask = cv2.dilate(text_mask, np.ones((19, 19), np.uint8), iterations=1)

    # 块级显著度：颜色方差 + 拉普拉斯边缘。平滑渐变照片也能被抓到，
    # 单纯文字/纯色背景会被文字遮罩或低方差过滤掉。
    bs = 48
    gh = max(1, math.ceil(h / bs))
    gw = max(1, math.ceil(w / bs))
    scores = np.zeros((gh, gw), dtype=np.float32)
    text_blocks = np.zeros((gh, gw), dtype=bool)
    for gy in range(gh):
        for gx in range(gw):
            y0, y1 = gy * bs, min(h, (gy + 1) * bs)
            x0, x1 = gx * bs, min(w, (gx + 1) * bs)
            block = img[y0:y1, x0:x1]
            if block.size == 0:
                continue
            color_std = float(block.reshape(-1, 3).astype(np.float32).std(axis=0).mean())
            gray = cv2.cvtColor(block, cv2.COLOR_BGR2GRAY)
            edge = float(cv2.Laplacian(gray, cv2.CV_32F).var() ** 0.5)
            scores[gy, gx] = color_std * 0.75 + edge * 0.55
            if text_mask[y0:y1, x0:x1].mean() > 12:
                text_blocks[gy, gx] = True

    valid = scores[~text_blocks]
    if valid.size == 0:
        return []
    thr = max(7.0, float(valid.mean() + 0.55 * valid.std()))
    block_mask = (scores >= thr) & (~text_blocks)
    mask_img = cv2.resize(block_mask.astype(np.uint8) * 255, (w, h), interpolation=cv2.INTER_NEAREST)
    k = max(15, bs)
    mask_img = cv2.morphologyEx(mask_img, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    mask_img = cv2.morphologyEx(mask_img, cv2.MORPH_OPEN, np.ones((k // 2, k // 2), np.uint8))
    contours, _ = cv2.findContours(mask_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for c in contours:
        area = cv2.contourArea(c)
        if area <= 0:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        frac = area / (w * h)
        ratio = area / max(1, bw * bh)
        if not (0.035 < frac < 0.42) or ratio < 0.42:
            continue
        if bw < 40 or bh < 40 or bw / bh > 4.5 or bh / bw > 4.5:
            continue
        pad = 0.008
        nx = max(0.0, x / w - pad)
        ny = max(0.0, y / h - pad)
        nw = min(1.0 - nx, bw / w + pad * 2)
        nh = min(1.0 - ny, bh / h + pad * 2)
        if nw < 0.08 or nh < 0.08:
            continue
        regions.append({"x": nx, "y": ny, "w": nw, "h": nh, "area": frac})
    regions.sort(key=lambda r: r["area"], reverse=True)
    regions = regions[:max_regions]
    out = []
    crops_dir.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(regions):
        x0 = max(0, int(r["x"] * w))
        y0 = max(0, int(r["y"] * h))
        x1 = min(w, int((r["x"] + r["w"]) * w))
        y1 = min(h, int((r["y"] + r["h"]) * h))
        crop = img[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        max_w = 900
        if crop.shape[1] > max_w:
            scale = max_w / crop.shape[1]
            crop = cv2.resize(crop, (max_w, max(1, int(crop.shape[0] * scale))))
        name = f"{scene_id}-r{i}.jpg"
        cv2.imwrite(str(crops_dir / name), crop, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        out.append({
            "type": "media", "src": f"crops/{name}",
            "x": round(r["x"], 4), "y": round(r["y"], 4),
            "w": round(r["w"], 4), "h": round(r["h"], 4),
            "radius": 0.014, "depth": 0.25 + i * 0.1,
        })
    return out


def _extract_clip(source: Path, scene: dict, box: dict, out: Path) -> bool:
    """按归一化 box 从源视频裁出一段区域视频。"""
    try:
        start = float(scene["start"])
        dur = max(0.2, float(scene["end"]) - start)
        # 需要视频尺寸
        probe = cv2.VideoCapture(str(source))
        vw = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH))
        vh = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT))
        probe.release()
        if vw <= 0 or vh <= 0:
            return False
        x = max(0, int(box["x"] * vw))
        y = max(0, int(box["y"] * vh))
        w = min(vw - x, int(box["w"] * vw))
        h = min(vh - y, int(box["h"] * vh))
        w -= w % 2
        h -= h % 2
        if w < 24 or h < 24:
            return False
        out.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}",
            "-t", f"{dur:.3f}", "-i", str(source),
            "-vf", f"crop={w}:{h}:{x}:{y}", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", str(out),
        ])
        return out.exists() and out.stat().st_size > 0
    except Exception:
        return False


def run_ffmpeg(cmd: list[str]) -> None:
    import subprocess
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_dynamic_element(source: Path, scene: dict, element: dict, path: str,
                         clips_dir: Path, fps: int) -> dict:
    """判断区域是否在场景内运动；运动则裁成区域视频，生成 clip 元素。"""
    if element.get("type") != "media":
        return element
    img = cv2.imread(path)
    if img is None:
        return element
    h, w = img.shape[:2]
    x = max(0, int(element["x"] * w))
    y = max(0, int(element["y"] * h))
    cw = max(1, int(element["w"] * w))
    ch = max(1, int(element["h"] * h))
    template = img[y:y + ch, x:x + cw]
    if template.size == 0:
        return element

    # 在场景的 3 个时间点搜索同一模板，估计移动范围
    boxes = []
    cap = cv2.VideoCapture(str(source))
    for frac in (0.12, 0.5, 0.88):
        t = float(scene["start"]) + (float(scene["end"]) - float(scene["start"])) * frac
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, maxloc = cv2.minMaxLoc(res)
        if maxv < 0.25:
            continue
        boxes.append({
            "x": maxloc[0] / w, "y": maxloc[1] / h,
            "w": cw / w, "h": ch / h, "score": maxv,
        })
    cap.release()
    if not boxes:
        return element

    xs = [b["x"] for b in boxes] + [element["x"]]
    ys = [b["y"] for b in boxes] + [element["y"]]
    x0, y0 = max(0.0, min(xs) - 0.01), max(0.0, min(ys) - 0.01)
    x1 = min(1.0, max(b["x"] + b["w"] for b in boxes) + 0.01)
    y1 = min(1.0, max(b["y"] + b["h"] for b in boxes) + 0.01)
    union = {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}
    movement = max(max(xs) - min(xs), max(ys) - min(ys))
    dynamic = movement > 0.012 or min(b["score"] for b in boxes) < 0.72
    if not dynamic or union["w"] * union["h"] > 0.55:
        return element

    name = f"{Path(path).stem}-clip.mp4"
    if not _extract_clip(source, scene, union, clips_dir / name):
        return element
    return {
        "type": "clip", "src": f"clips/{name}",
        "x": round(union["x"], 4), "y": round(union["y"], 4),
        "w": round(union["w"], 4), "h": round(union["h"], 4),
        "radius": element.get("radius", 0.014),
        "movement": round(movement, 4),
    }


def _grabcut_mask(frame, element: dict) -> np.ndarray | None:
    h, w = frame.shape[:2]
    x = max(0, int(element["x"] * w))
    y = max(0, int(element["y"] * h))
    bw = min(w - x, int(element["w"] * w))
    bh = min(h - y, int(element["h"] * h))
    if bw < 28 or bh < 28:
        return None
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(frame, mask, (x, y, bw, bh), bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    frac = float(fg.mean() / 255)
    if not (0.025 < frac < 0.88):
        return None
    return fg


def _mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    if w < 24 or h < 24:
        return None
    return x, y, w, h


def make_static_object(frame_path: str, element: dict, objects_dir: Path,
                       scene_id: str) -> dict | None:
    frame = cv2.imread(frame_path)
    if frame is None:
        return None
    mask = _grabcut_mask(frame, element)
    if mask is None:
        return None
    box = _mask_bbox(mask)
    if box is None:
        return None
    h, w = frame.shape[:2]
    x, y, bw, bh = box
    pad = 4
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(w, x + bw + pad), min(h, y + bh + pad)
    alpha = mask[y0:y1, x0:x1]
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    bgra = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2BGRA)
    bgra[..., 3] = alpha
    objects_dir.mkdir(parents=True, exist_ok=True)
    name = f"{scene_id}-object.png"
    cv2.imwrite(str(objects_dir / name), bgra)
    return {
        "type": "object", "src": f"objects/{name}",
        "x": round(x0 / w, 4), "y": round(y0 / h, 4),
        "w": round((x1 - x0) / w, 4), "h": round((y1 - y0) / h, 4),
    }


def make_object_clip(source: Path, scene: dict, element: dict, frame_path: str,
                     objects_dir: Path, scene_id: str, fps: int) -> dict | None:
    """GrabCut 首帧 + 模板跟踪 + 遮罩平移，输出带 alpha 的 WebM。"""
    frame0 = cv2.imread(frame_path)
    if frame0 is None:
        return None
    mask0 = _grabcut_mask(frame0, element)
    if mask0 is None:
        return None
    h, w = frame0.shape[:2]
    x0 = max(0, int(element["x"] * w))
    y0 = max(0, int(element["y"] * h))
    bw = min(w - x0, int(element["w"] * w))
    bh = min(h - y0, int(element["h"] * h))
    template = frame0[y0:y0 + bh, x0:x0 + bw]
    if template.size == 0:
        return None

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_MSEC, float(scene["start"]) * 1000)
    boxes = []
    prev = (x0, y0, bw, bh)
    for _ in range(max(1, int((scene["end"] - scene["start"]) * fps))):
        ok, frame = cap.read()
        if not ok:
            break
        pad = int(max(prev[2], prev[3]) * 0.45)
        sx = max(0, prev[0] - pad)
        sy = max(0, prev[1] - pad)
        ex = min(w, prev[0] + prev[2] + pad)
        ey = min(h, prev[1] + prev[3] + pad)
        search = frame[sy:ey, sx:ex]
        if search.shape[0] < bh or search.shape[1] < bw:
            boxes.append(prev)
            continue
        res = cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED)
        _, score, _, loc = cv2.minMaxLoc(res)
        if score >= 0.22:
            prev = (sx + loc[0], sy + loc[1], bw, bh)
        boxes.append(prev)
    cap.release()
    if len(boxes) < 5:
        return None

    xs = [b[0] for b in boxes]
    ys = [b[1] for b in boxes]
    ux0, uy0 = max(0, min(xs) - 8), max(0, min(ys) - 8)
    ux1 = min(w, max(b[0] + b[2] for b in boxes) + 8)
    uy1 = min(h, max(b[1] + b[3] for b in boxes) + 8)
    uw, uh = ux1 - ux0, uy1 - uy0
    uw -= uw % 2
    uh -= uh % 2
    if uw < 24 or uh < 24 or (uw * uh) / (w * h) > 0.65:
        return None

    objects_dir.mkdir(parents=True, exist_ok=True)
    name = f"{scene_id}-object.webm"
    out_path = objects_dir / name
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{uw}x{uh}",
        "-r", str(fps), "-i", "-",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
        "-auto-alt-ref", "0", "-b:v", "0", "-crf", "30",
        "-metadata:s:v:0", "alpha_mode=1", str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    cap = cv2.VideoCapture(str(source))
    cap.set(cv2.CAP_PROP_POS_MSEC, float(scene["start"]) * 1000)
    idx = 0
    while idx < len(boxes):
        ok, frame = cap.read()
        if not ok:
            break
        bx, by = boxes[idx][0], boxes[idx][1]
        dx, dy = bx - x0, by - y0
        m = np.float32([[1, 0, dx], [0, 1, dy]])
        shifted = cv2.warpAffine(mask0, m, (w, h), flags=cv2.INTER_NEAREST)
        crop = frame[uy0:uy0 + uh, ux0:ux0 + uw]
        alpha = shifted[uy0:uy0 + uh, ux0:ux0 + uw]
        alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
        rgba = cv2.cvtColor(crop, cv2.COLOR_BGR2RGBA)
        rgba[..., 3] = alpha
        try:
            proc.stdin.write(rgba.tobytes())
        except BrokenPipeError:
            break
        idx += 1
    cap.release()
    try:
        proc.stdin.close()
    except Exception:
        pass
    proc.wait()
    if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        return None
    return {
        "type": "objectClip", "src": f"objects/{name}",
        "x": round(ux0 / w, 4), "y": round(uy0 / h, 4),
        "w": round(uw / w, 4), "h": round(uh / h, 4),
    }


def make_object_element(source: Path, scene: dict, element: dict, frame_path: str,
                        objects_dir: Path, scene_id: str, fps: int,
                        dynamic: bool) -> dict:
    if element.get("type") != "media":
        return element
    if dynamic:
        obj = make_object_clip(source, scene, element, frame_path, objects_dir, scene_id, fps)
    else:
        obj = make_static_object(frame_path, element, objects_dir, scene_id)
    return obj or element


def _bbox(lines: list[dict]) -> dict:
    return {
        "x0": min(l["x0"] for l in lines),
        "y0": min(l["y0"] for l in lines),
        "x1": max(l["x1"] for l in lines),
        "y1": max(l["y1"] for l in lines),
    }


def _text_element(text: str, line: dict, path: str, bg_rgb, delay: int, role: str,
                  line_height: float | None = None) -> dict:
    h = max(0.012, line_height if line_height is not None else (line["y1"] - line["y0"]))
    factor = 0.64 if role == "title" else 0.36
    size = max(0.018, min(0.11, h * factor))
    width = max(0.12, min(0.95, (line["x1"] - line["x0"]) + 0.02))
    # 按最长一行估算“不换行”的最大字号，避免 OCR 框高度导致字号过大
    img = cv2.imread(path)
    if img is not None:
        fh, fw = img.shape[:2]
        max_line = max(1, max(len(x) for x in text.split("\n")))
        fit = (width * fw) / (max_line * 1.02) / max(1, fh)
        floor = 0.04 if role == "title" else 0.026
        size = max(floor, min(size, fit))
    center = (line["x0"] + line["x1"]) / 2
    align = "center" if abs(center - 0.5) < 0.07 and width > 0.3 else ("right" if line["x1"] > 0.9 else "left")
    return {
        "type": "text", "text": text,
        "x": round(max(0.02, line["x0"] - 0.005), 4),
        "y": round(max(0.01, line["y0"] - 0.004), 4),
        "w": round(width, 4), "size": round(size, 4),
        "color": text_color(path, line, bg_rgb),
        "weight": 800 if role == "title" else 500,
        "align": align, "enter": "up" if role == "title" else "fade",
        "delay": delay,
    }


def build_elements(scene: dict, path: str, crops_dir: Path,
                   scene_id: str, max_regions: int = 2) -> tuple[str, list[dict]]:
    bg_css = background_css(path)
    bg_hex = bg_css if bg_css.startswith("#") else "#05070d"
    bg_rgb = np.array([int(bg_hex[1:3], 16), int(bg_hex[3:5], 16), int(bg_hex[5:7], 16)])
    lines = [l for l in (scene.get("lines") or []) if l.get("text")]
    if not lines:
        return bg_css, []

    lines.sort(key=lambda l: (l["y0"], l["x0"]))
    bullet_groups: list[list[dict]] = []
    rest: list[dict] = []
    for line in lines:
        text = line["text"].strip()
        if BULLET_RE.match(text):
            item = BULLET_RE.sub("", text).strip()
            if not item:
                continue
            if bullet_groups:
                g = bullet_groups[-1]
                last = g[-1]
                if abs(line["x0"] - last["x0"]) < 0.06 and line["y0"] - last["y1"] < max(0.035, (last["y1"] - last["y0"]) * 2.2):
                    g.append(line)
                    continue
            bullet_groups.append([line])
        else:
            rest.append(line)

    elements: list[dict] = []
    # 段落聚合：相同左边、垂直间距小、字号接近
    groups: list[list[dict]] = []
    for line in rest:
        line_h = max(0.012, line["y1"] - line["y0"])
        if groups:
            g = groups[-1]
            last = g[-1]
            h = max(0.012, last["y1"] - last["y0"])
            same_size = 0.72 <= line_h / h <= 1.38
            # 大字号标题行不跟后面的正文合并
            title_line = h >= 0.055 or line_h >= 0.055
            if (not title_line and same_size
                    and abs(line["x0"] - last["x0"]) < 0.035
                    and line["y0"] - last["y1"] < max(0.022, h * 1.35)):
                g.append(line)
                continue
        groups.append([line])

    for gi, g in enumerate(groups[:4]):
        text = "\n".join(l["text"] for l in g)
        b = _bbox(g)
        line_h = float(np.median([max(0.012, l["y1"] - l["y0"]) for l in g]))
        # 第一个文本组当标题，其余当正文；避免把所有 OCR 行都放大
        role = "title" if gi == 0 else "body"
        line = {"x0": b["x0"], "y0": b["y0"], "x1": b["x1"], "y1": b["y1"]}
        elements.append(_text_element(text, line, path, bg_rgb, 4 + len(elements) * 4,
                                      role, line_height=line_h))

    for g in bullet_groups[:2]:
        b = _bbox(g)
        items = [BULLET_RE.sub("", l["text"]).strip() for l in g]
        items = [i for i in items if i]
        if len(items) < 2:
            # 单条 bullet 当正文
            line = {"x0": b["x0"], "y0": b["y0"], "x1": b["x1"], "y1": b["y1"]}
            elements.append(_text_element(items[0] if items else "", line, path, bg_rgb, 12, "body"))
            continue
        h = max(0.018, b["y1"] - b["y0"])
        size = max(0.018, min(0.06, h / max(2.2, len(items) * 1.55)))
        elements.append({
            "type": "bullets", "items": items,
            "x": round(max(0.03, b["x0"] - 0.005), 4),
            "y": round(max(0.02, b["y0"] - 0.004), 4),
            "w": round(max(0.2, min(0.94, b["x1"] - b["x0"] + 0.02)), 4),
            "size": round(size, 4),
            "color": text_color(path, g[0], bg_rgb),
            "bulletColor": scene.get("accent", "#56beff"),
            "gap": round(max(0.008, min(0.03, h / max(3, len(items) * 1.8))), 4),
            "delay": 10 + len(elements) * 3,
        })

    # 色块放在文字前（文字绘制在上层）
    panels = detect_panels(path, bg_hex) if scene.get("kind") in ("slide", "screen") else []
    media = []
    if scene.get("kind") in ("title", "slide", "screen"):
        media = detect_media_regions(path, lines, crops_dir, scene_id, max_regions)
    return bg_css, media + panels + elements


def _num(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".")


def render_scene(index: int, scene: dict, bg: str, elements: list[dict],
                 media: bool, zoom_from: float, zoom_to: float,
                 pan_x: float, pan_y: float, caption: dict | None,
                 transition: str = "cut") -> str:
    imports = [
        "import React from 'react';",
        "import {staticFile} from 'remotion';",
        "import {SceneFrame} from '../components/SceneFrame';",
        "import {TextBlock} from '../components/TextBlock';",
        "import {BulletList} from '../components/BulletList';",
        "import {Panel} from '../components/Panel';",
        "import {MediaLayer} from '../components/MediaLayer';",
        "import {MediaCard} from '../components/MediaCard';",
        "import {MotionCard} from '../components/MotionCard';",
        "import {ObjectCard} from '../components/ObjectCard';",
        "import {ObjectImage} from '../components/ObjectImage';",
        "import {theme} from '../theme';",
    ]
    body = []
    if media:
        body.append(f"      <MediaLayer src={json.dumps(scene['src'])} fit=\"cover\" scaleFrom={{{_num(zoom_from)}}} scaleTo={{{_num(zoom_to)}}} panX={{{_num(pan_x)}}} panY={{{_num(pan_y)}}} />")
        if caption:
            body.append(
                f"      <TextBlock text={{{json.dumps(caption['text'], ensure_ascii=False)}}} "
                f"x={{0.08}} y={{0.80}} width={{0.84}} size={{0.028}} "
                f"color={{theme.colors.text}} weight={{600}} align=\"center\" enter=\"fade\" delay={{10}} />"
            )
    else:
        for e in elements:
            if e["type"] == "panel":
                body.append(
                    f"      <Panel x={{{_num(e['x'])}}} y={{{_num(e['y'])}}} width={{{_num(e['w'])}}} height={{{_num(e['h'])}}} "
                    f"fill={json.dumps(e['fill'])} radius={{{_num(e.get('radius', 0.018))}}} opacity={{{_num(e.get('opacity', 1))}}} />"
                )
            elif e["type"] == "text":
                body.append(
                    f"      <TextBlock text={{{json.dumps(e['text'], ensure_ascii=False)}}} "
                    f"x={{{_num(e['x'])}}} y={{{_num(e['y'])}}} width={{{_num(e['w'])}}} size={{{_num(e['size'])}}} "
                    f"color={json.dumps(e['color'])} weight={{{e['weight']}}} align={json.dumps(e['align'])} "
                    f"enter={json.dumps(e['enter'])} delay={{{e['delay']}}} />"
                )
            elif e["type"] == "bullets":
                items = json.dumps(e["items"], ensure_ascii=False)
                body.append(
                    f"      <BulletList items={{{items}}} x={{{_num(e['x'])}}} y={{{_num(e['y'])}}} width={{{_num(e['w'])}}} "
                    f"size={{{_num(e['size'])}}} color={json.dumps(e['color'])} bulletColor={json.dumps(e['bulletColor'])} "
                    f"gap={{{_num(e['gap'])}}} delay={{{e['delay']}}} />"
                )
            elif e["type"] == "media":
                body.append(
                    f"      <MediaCard src={json.dumps(e['src'])} x={{{_num(e['x'])}}} y={{{_num(e['y'])}}} "
                    f"width={{{_num(e['w'])}}} height={{{_num(e['h'])}}} fit=\"cover\" "
                    f"radius={{{_num(e.get('radius', 0.014))}}} depth={{{_num(e.get('depth', 0.25))}}} />"
                )
            elif e["type"] == "clip":
                body.append(
                    f"      <MotionCard src={json.dumps(e['src'])} x={{{_num(e['x'])}}} y={{{_num(e['y'])}}} "
                    f"width={{{_num(e['w'])}}} height={{{_num(e['h'])}}} fit=\"cover\" "
                    f"radius={{{_num(e.get('radius', 0.014))}}} />"
                )
            elif e["type"] == "object":
                body.append(
                    f"      <ObjectImage src={json.dumps(e['src'])} x={{{_num(e['x'])}}} y={{{_num(e['y'])}}} "
                    f"width={{{_num(e['w'])}}} height={{{_num(e['h'])}}} fit=\"contain\" />"
                )
            elif e["type"] == "objectClip":
                body.append(
                    f"      <ObjectCard src={json.dumps(e['src'])} x={{{_num(e['x'])}}} y={{{_num(e['y'])}}} "
                    f"width={{{_num(e['w'])}}} height={{{_num(e['h'])}}} fit=\"contain\" />"
                )
    if not body:
        body.append(f"      <MediaLayer src={json.dumps(scene['src'])} fit=\"cover\" />")

    bg_expr = json.dumps(bg) if not bg.startswith("theme.") else bg
    return "\n".join(imports) + f"""

export const Scene{index:03d}: React.FC = () => {{
  return (
    <SceneFrame background={{{bg_expr}}} transition={json.dumps(transition)}>
""" + "\n".join(body) + """
    </SceneFrame>
  );
};
"""


def _copy_templates(out: Path) -> None:
    for src in TEMPLATES.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(TEMPLATES)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def generate_project(out: Path, info: dict, raw: list[dict], fps: int, total_frames: int,
                     preset: str, captions: str, audio_bpm: float, beats: list[float],
                     letterbox: bool, max_regions: int = 2,
                     source_path: Path | None = None, dynamic: bool = True,
                     matting: bool = True) -> dict:
    _copy_templates(out)
    (out / "src" / "scenes").mkdir(parents=True, exist_ok=True)
    (out / "public" / "frames").mkdir(parents=True, exist_ok=True)
    crops_dir = out / "public" / "crops"
    clips_dir = out / "public" / "clips"
    objects_dir = out / "public" / "objects"

    # 全局主题
    accents = [s.get("accent") for s in raw if s.get("accent")]
    accent = accents[0] if accents else "#56beff"
    bg0 = raw[0].get("bg", "#05070d") if raw else "#05070d"
    theme = f'''export const theme = {{
  colors: {{
    background: {json.dumps(bg0)},
    text: '#f7fbff',
    muted: '#9fb3c8',
    accent: {json.dumps(accent)},
    panel: 'rgba(10, 18, 32, 0.72)',
    panelBorder: 'rgba(255, 255, 255, 0.10)',
  }},
  font: {{
    family: '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif',
    titleWeight: 800,
    bodyWeight: 500,
    lineHeight: 1.3,
  }},
  radius: 18,
}} as const;

export type Theme = typeof theme;
'''
    (out / "src" / "theme.ts").write_text(theme, encoding="utf-8")

    config = f'''export const config = {{
  fps: {fps},
  width: {info["width"]},
  height: {info["height"]},
  durationInFrames: {total_frames},
  background: {json.dumps(bg0)},
  audio: {json.dumps("audio/audio.m4a" if info.get("has_audio") else None)},
  preset: {json.dumps(preset)},
  letterbox: {str(bool(letterbox)).lower()},
}} as const;
'''
    (out / "src" / "config.ts").write_text(config, encoding="utf-8")

    scene_meta = []
    imports = []
    components = []
    clip_count = 0
    object_count = 0
    cursor = 0
    n = len(raw)
    for i, s in enumerate(raw):
        from_frame = cursor
        to_frame = total_frames if i == n - 1 else max(cursor + 1, round(s["end"] * fps))
        dur = max(1, to_frame - from_frame)
        cursor = from_frame + dur

        kind = s.get("kind", "live")
        graphic = kind in ("title", "slide", "screen")
        frame_path = str(out / "public" / s["src"])
        if graphic:
            bg, elements = build_elements(
                s, frame_path, crops_dir, f"scene-{i:03d}", max_regions)
            if source_path and source_path.is_file() and dynamic:
                converted = []
                for e in elements:
                    if e.get("type") == "media":
                        if matting:
                            e = make_object_element(source_path, s, e, frame_path,
                                                    objects_dir, f"scene-{i:03d}", fps, True)
                        else:
                            e = make_dynamic_element(source_path, s, e, frame_path, clips_dir, fps)
                    converted.append(e)
                elements = converted
            elif matting:
                converted = []
                for e in elements:
                    if e.get("type") == "media":
                        e = make_object_element(source_path or Path(frame_path), s, e, frame_path,
                                                objects_dir, f"scene-{i:03d}", fps, False)
                    converted.append(e)
                elements = converted
        else:
            bg, elements = s.get("bg", bg0), []
        if graphic and not elements:
            graphic = False
        media = not graphic
        has_media = any(e.get("type") in ("media", "clip", "object", "objectClip") for e in elements)
        clip_count += sum(1 for e in elements if e.get("type") == "clip")
        object_count += sum(1 for e in elements if e.get("type") in ("object", "objectClip"))
        mode = "media" if media else ("hybrid" if has_media else "graphic")

        amp = {"title": 0.055, "slide": 0.025, "screen": 0.035,
               "live": 0.09, "static": 0.018, "image": 0.05}.get(kind, 0.05)
        if preset == "cinematic":
            amp *= 0.85
        elif preset == "slides":
            amp *= 0.25
        elif preset == "social":
            amp *= 1.25
        elif preset == "minimal":
            amp *= 0.45
        if i % 2 == 0:
            zoom_from, zoom_to = 1.0, 1.0 + amp
        else:
            zoom_from, zoom_to = 1.0 + amp, 1.0
        pan_x = 0 if graphic else (1.1 if i % 3 == 0 else -1.1)
        pan_y = 0 if graphic else (-0.7 if i % 2 == 0 else 0.7)

        caption = None
        if captions in ("top", "bottom") and s.get("text"):
            caption = {"text": s["text"][:64], "position": captions}
        elif captions == "auto" and media and s.get("text") and float(s.get("area") or 0) < 0.02:
            caption = {"text": s["text"][:64], "position": "bottom"}

        transition = s.get("transition", {}).get("type", "cut")
        code = render_scene(i, s, bg, elements, media, zoom_from, zoom_to, pan_x, pan_y,
                            caption, transition)
        (out / "src" / "scenes" / f"Scene{i:03d}.tsx").write_text(code, encoding="utf-8")
        imports.append(f"import {{Scene{i:03d}}} from './Scene{i:03d}';")
        components.append(f"Scene{i:03d}")
        scene_meta.append({
            "id": f"scene-{i:03d}", "from": from_frame, "durationInFrames": dur,
            "kind": kind, "accent": s.get("accent", accent),
            "transition": s.get("transition", {}).get("type", "cut"),
            "mode": mode,
        })

    (out / "src" / "scenes" / "index.ts").write_text(
        "\n".join(imports) + "\n\nexport const sceneComponents = [" + ", ".join(components) + "];\n",
        encoding="utf-8")
    beat_frames = [round(b * fps) for b in beats if 0 <= b * fps < total_frames]
    (out / "src" / "timeline.ts").write_text(f'''export type SceneMeta = {{
  id: string;
  from: number;
  durationInFrames: number;
  kind: string;
  accent: string;
  transition: string;
  mode: 'graphic' | 'media' | 'hybrid';
}};

export const scenes: SceneMeta[] = {json.dumps(scene_meta, ensure_ascii=False, indent=2)};

export const bpm = {audio_bpm};
export const beats: number[] = {json.dumps(beat_frames)};
''', encoding="utf-8")

    (out / "analysis.json").write_text(json.dumps({
        "source": info,
        "scenes": [{k: v for k, v in s.items() if k != "lines"} for s in raw],
        "timeline": {"scenes": scene_meta, "bpm": audio_bpm, "beats": beat_frames},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    kinds = {}
    for s in scene_meta:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    kind_text = " / ".join(f"{k}×{n}" for k, n in sorted(kinds.items()))
    modes = {}
    for s in scene_meta:
        modes[s["mode"]] = modes.get(s["mode"], 0) + 1
    mode_text = " / ".join(f"{k}×{n}" for k, n in sorted(modes.items()))
    (out / "README.md").write_text(f"""# Code-driven Remotion 工程

这是 **代码驱动版**：不是把整段视频逐帧塞进 Remotion，而是把画面拆成参数化组件。

- 源文件：`{info.get('source', '')}`
- 时长：{info['duration']:.2f}s / {fps}fps / {total_frames} 帧
- 分辨率：{info['width']}×{info['height']}
- 场景：{len(scene_meta)} 个（{kind_text}）
- 重建方式：{mode_text}
- 动态区域：{clip_count} 个（裁成区域视频，使用 `MotionCard`）
- 对象抠像：{object_count} 个（GrabCut + 跟踪，使用 `ObjectImage` / `ObjectCard`）
- BPM：{audio_bpm or '未检测到'}

## 结构

```text
src/
├─ config.ts          # 画布、fps、时长、音频、预设
├─ theme.ts           # 颜色、字体、字重、圆角
├─ timeline.ts        # 每个场景的起止时间
├─ scenes/
│  ├─ Scene000.tsx    # 每个场景一个独立组件
│  └─ index.ts
├─ components/        # 可复用积木
│  ├─ SceneFrame.tsx
│  ├─ TextBlock.tsx
│  ├─ BulletList.tsx
│  ├─ Panel.tsx
│  ├─ MediaCard.tsx     # 复杂场景拆出的静态图片/UI 区域
│  ├─ MotionCard.tsx    # 动态区域视频
│  ├─ ObjectImage.tsx   # 静态抠像 PNG
│  ├─ ObjectCard.tsx    # 动态抠像 alpha WebM
│  └─ MediaLayer.tsx
└─ VideoFromFootage.tsx
```

## 怎么改

- 改文字：打开 `src/scenes/SceneXXX.tsx`，直接改 `text` / `items`。
- 改布局：调 `x` / `y` / `width` / `size`（都是 0–1 的归一化值）。
- 改颜色：改 `src/theme.ts`，或场景里的 `color`。
- 改节奏：改 `src/timeline.ts` 的 `from` / `durationInFrames`；`bpm` / `beats` 是检测到的节拍帧。
- 加动画：在场景里用 `useCurrentFrame()` + `interpolate()`，或在 `TextBlock` 里加参数。
- 实拍场景：`MediaLayer` 只负责素材，运镜、遮罩、叠字仍然在代码里。

## 渲染

```bash
npm install
npm run start
npm run render
```
""", encoding="utf-8")

    return {"scenes": scene_meta, "graphic": modes.get("graphic", 0),
            "media": modes.get("media", 0), "hybrid": modes.get("hybrid", 0),
            "clips": clip_count, "objects": object_count}
