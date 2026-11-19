# Video → Remotion 工程（v2 万能模式）

- 源文件：`aivideokit-媒体能力演示.remotion.mp4`
- 时长：13.00s / 30fps / 390 帧
- 分辨率：1920×1080
- 分镜：3 个（live×1 / slide×1 / title×1）
- 预设：`auto`
- BPM：187.5
- 音频：已提取
- OCR 字幕：已生成

## 使用

```bash
npm install
npm run start      # Remotion Studio
npm run render     # out/video.mp4
```

## 结构

```text
public/frames/              每个镜头的关键帧/图片
public/audio/               源音轨
src/timeline.ts             分镜时间线（可直接改）
src/VideoFromFootage.tsx    主合成
src/components/SceneView.tsx 按场景类型渲染
src/components/TitleScene.tsx 文字标题场景
src/components/Caption.tsx  字幕层
```

## 调整建议

- 改节奏：调 `timeline.ts` 里的 `from` / `durationInFrames`。
- 改运镜：调 `zoom` / `pan`；想完全静止就把两个 zoom 都设 1.0。
- 改转场：`fade` 是淡入淡出秒数；想要硬切就设 0.04。
- 改标题：`kind: 'title'` 的场景会把 OCR 文字重新排版，`titleLines` 可手改。
- 关节拍：`video.beats` 是检测到的节拍帧；`pulse` 控制脉冲强度。

> v2 会按场景类型选择策略：文字卡重新排版、幻灯片轻微推近、屏幕录制稳定呈现、实拍 Ken Burns。
> 不是像素级还原；OCR 可能有错字，生成后可在 `timeline.ts` 里修。
