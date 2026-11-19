# video2remotion v3

把**成品视频 / 图片**转换成 **代码驱动、参数化可编辑的 Remotion 工程**。

不是把整段视频塞进 `<Video>`，也不是只给每帧截图。默认引擎会分析画面结构，把标题、正文、列表、色块、布局重新生成为 TSX 组件；实拍镜头才使用 `MediaLayer` 素材层。

## 两种引擎

| 引擎 | 命令 | 输出 |
| :-- | :-- | :-- |
| **code**（默认） | `--engine code` | 每个场景一个 `SceneXXX.tsx`，文字/布局/颜色/动画都是代码 |
| **media** | `--engine media` | 关键帧 + `<Sequence>` + Ken Burns，适合快速保真 |

## 代码驱动模式生成什么

```text
src/
├─ config.ts          # 画布、fps、时长、音频、预设
├─ theme.ts           # 全局颜色、字体、字重、圆角（设计 token）
├─ timeline.ts        # 每个场景的起止时间、类型、模式
├─ scenes/
│  ├─ Scene000.tsx    # 独立组件：标题 / 正文 / 列表 / 色块
│  ├─ Scene001.tsx
│  ├─ Scene002.tsx
│  └─ index.ts
├─ components/        # 可复用积木
│  ├─ SceneFrame.tsx  # 背景/暗角
│  ├─ TextBlock.tsx   # 归一化坐标 + 字号 + 入场动画
│  ├─ BulletList.tsx  # 逐条入场列表
│  ├─ Panel.tsx       # 圆角色块/卡片
│  ├─ MediaCard.tsx   # 静态图片/UI 区域
│  ├─ MotionCard.tsx  # 动态区域视频
│  ├─ ObjectImage.tsx # 静态抠像 PNG
│  ├─ ObjectCard.tsx  # 动态抠像 alpha WebM
│  └─ MediaLayer.tsx  # 实拍素材 + 运镜参数
└─ VideoFromFootage.tsx
```

生成的场景长这样，所有值都可以直接改：

```tsx
export const Scene000: React.FC = () => {
  return (
    <SceneFrame background={"#0b1223"}>
      <TextBlock
        text="一份规格两种引擎"
        x={0.1882} y={0.3191} width={0.6341}
        size={0.067} color="#ebf0fa"
        weight={800} align="center" enter="up" delay={4}
      />
      <TextBlock
        text="图片音频转场都由同一份 JSON 驱动"
        x={0.2622} y={0.5691} width={0.4861}
        size={0.028} color="#929ab5"
        weight={500} align="center" enter="fade" delay={8}
      />
    </SceneFrame>
  );
};
```

- `x / y / width` 是 0–1 归一化坐标，换 1080p / 4K / 竖屏都不用重算。
- `size` 是相对画面高度的字号。
- `delay` 是帧延迟，`enter` 是入场方式。
- `theme.ts` 改一次，全片颜色/字体跟着变。
- `timeline.ts` 还导出 `bpm` 和 `beats`（节拍帧），可以直接做卡点动画。

## 自动分析

- 镜头切点：低分辨率采样 + RGB 直方图差异
- 场景分类：`title` / `slide` / `screen` / `live` / `static` / `image`
- 文字布局：OCR 行框 → 标题、正文、段落、列表
- **OCR 纠错**：本地规则先过滤花字/纹理噪声，再交给多模态模型按图纠正错字、乱码、错误断行
- 字号：按 OCR 行高 + 文本长度/可用宽度双重约束，避免溢出
- 颜色：背景主色/渐变、文字颜色、强调色
- 色块：检测大面积、矩形度高的纯色区域，生成 `Panel`
- **复杂场景拆层**：照片/插图/UI 卡片自动裁成 `MediaCard`，和文字、背景分层组合，生成 `hybrid` 场景
- **动态区域提取**：如果检测到的区域在场景内移动/变化，会裁成区域视频，生成 `MotionCard`（`public/clips/*.mp4`）
- **对象级抠像**：GrabCut 首帧 + 模板跟踪 + 遮罩平移，静态对象生成 alpha PNG，动态对象生成 alpha WebM（`ObjectImage` / `ObjectCard`）
- 音频：BPM / 节拍检测；媒体场景按节拍脉冲
- 实拍：`MediaLayer` 保留素材，运镜/遮罩/叠字仍由代码控制

## 快速开始

```bash
cd /workspace/video2remotion

# 代码驱动（默认）
python3 video2remotion.py input.mp4 -o my-code-video

# 关键帧保真模式
python3 video2remotion.py input.mp4 -o my-media-video --engine media

# 图片文件夹 + 音频
python3 video2remotion.py ./images -o my-slides --audio bgm.mp3 --image-duration 2.5

cd my-code-video
npm install
npm run start     # Remotion Studio
npm run render    # out/video.mp4
```

## 示例

- [`examples/code-demo`](examples/code-demo) — 代码驱动：title + live + slide
- [`examples/code-preview.mp4`](examples/code-preview.mp4) — 实际渲染结果
- [`examples/code-frame-1.png`](examples/code-frame-1.png) — 代码生成的标题场景
- [`examples/code-frame-9.png`](examples/code-frame-9.png) — 代码生成的幻灯片场景
- [`examples/complex-demo`](examples/complex-demo) — **复杂场景 hybrid**：图片区域拆成 `MediaCard` + 文字代码
- [`examples/complex-preview.mp4`](examples/complex-preview.mp4) — 复杂场景渲染结果
- [`examples/complex-frame.png`](examples/complex-frame.png) — 复杂场景预览帧
- [`examples/complex-source.png`](examples/complex-source.png) — 合成的复杂幻灯片源图
- [`examples/dynamic-demo`](examples/dynamic-demo) — **动态区域工程**：移动图片裁成 `MotionCard` 视频
- [`examples/dynamic-preview.mp4`](examples/dynamic-preview.mp4) — 动态区域渲染结果
- [`examples/dynamic-frame-1.png`](examples/dynamic-frame-1.png)、[`examples/dynamic-frame-3.png`](examples/dynamic-frame-3.png) — 动态区域不同时间点
- [`examples/matte-demo`](examples/matte-demo) — **对象级抠像工程**：`ObjectCard` + alpha WebM
- [`examples/matte-preview.mp4`](examples/matte-preview.mp4) — 抠像渲染结果
- [`examples/matte-frame-1.png`](examples/matte-frame-1.png)、[`examples/matte-frame-3.png`](examples/matte-frame-3.png) — 抠像不同时间点
- [`examples/v2-demo`](examples/v2-demo) — media 引擎示例
- [`examples/v2-preview.mp4`](examples/v2-preview.mp4) — media 引擎渲染结果

```bash
cd examples/code-demo
npm install && npm run start
```

## 常用参数

```bash
python3 video2remotion.py input.mp4 -o out \
  --engine code          # code（默认） / media / auto
  --preset auto          # auto / cinematic / slides / social / minimal
  --captions auto        # off / auto / top / bottom
  --max-scenes 24        # 0 = 按时长自动
  --max-regions 2        # 每个复杂场景最多拆几个图片/UI 区域，0=关闭
  --no-dynamic           # 关闭区域动态检测（只用静态 MediaCard）
  --no-matting           # 关闭对象级抠像（退回矩形 MediaCard/MotionCard）
  --threshold 0.35       # 越大越不容易切镜
  --min-scene 0.8
  --fps 30
  --width 1080 --height 1920
  --lang chi_sim+eng
  --no-ocr-fix           # 关闭多模态 OCR 纠错（默认开启，失败自动回退）
  --no-audio
  --no-beat

# 图片模式
  --audio bgm.mp3
  --image-duration 3.0
```

## OCR 纠错

流水线是「本地过滤 → 多模态纠错」两步：

1. `ocr_details()`：放大/灰度/锐化后跑 tesseract，再按置信度、词形、单字符碎片等规则过滤噪声。
2. `fix_ocr_lines()`：把画面和 OCR 行一起发给多模态模型，按图纠正错字、乱码、错误断行；模型判定不存在的行会被丢弃。

接口地址和模型已内置；密钥不进仓库，按下面任一方式提供：

```bash
# 方式一：环境变量
export V2R_LLM_KEY=sk-...
# 方式二：项目根目录放 .llm-key（已在 .gitignore 中）
echo sk-... > .llm-key

# 可选覆盖
V2R_LLM_URL=https://bailucode.com/openapi/v1/messages
V2R_LLM_MODEL=bailu-2.8-fast
```

请求失败、超时或返回格式不对时自动回退到原始 OCR，不影响生成流程；`--no-ocr-fix` 可完全关闭（离线/批量可显著提速）。

## 能力边界

**能做的**

- 把标题卡、幻灯片、屏幕录制重建成可编辑的文字/色块/列表组件
- 保留实拍素材，但用代码控制裁切、缩放、平移、叠字
- 参数化改文字、坐标、字号、颜色、字重、入场延迟
- 自动分镜、音频节拍、字幕、预设风格

**不做承诺**

- 像素级还原原片（那需要逐帧视频或生成模型）
- 从零重建真实人物/复杂场景的像素内容
- 100% 正确的 OCR（已有多模态纠错，生成后仍可在 `SceneXXX.tsx` 里改字）
- 物体级跟踪、复杂的 3D 转场

一句话：**文字和版式是代码，实拍是素材；结构和参数都可编辑。**

## 依赖

- Python 3.10+
- `ffmpeg` / `ffprobe`
- `numpy`、`Pillow`、`opencv-python`
- 可选：`tesseract` + `chi_sim` / `eng`
- 渲染需要 Node.js 18+（推荐 22+）

```bash
pip install -r requirements.txt
```

## 开发

```bash
python3 -m py_compile video2remotion.py code_engine.py
bash tests/test_smoke.sh
bash tests/test_images.sh
bash tests/test_complex.sh
```

## License

MIT
