# Code-driven Remotion 工程

这是 **代码驱动版**：不是把整段视频逐帧塞进 Remotion，而是把画面拆成参数化组件。

- 源文件：`aivideokit-媒体能力演示.remotion.mp4`
- 时长：13.00s / 30fps / 390 帧
- 分辨率：1920×1080
- 场景：3 个（live×1 / slide×1 / title×1）
- 重建方式：graphic×2 / media×1
- 动态区域：0 个（裁成区域视频，使用 `MotionCard`）
- BPM：187.5

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
