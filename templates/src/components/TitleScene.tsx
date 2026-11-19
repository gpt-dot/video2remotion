import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {Scene} from '../timeline';

export const TitleScene: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const enter = spring({
    frame,
    fps,
    config: {damping: 20, stiffness: 90, mass: 0.8},
  });
  const bgScale = interpolate(enter, [0, 1], [1.08, 1.0]);
  const baseSize = Math.max(28, Math.min(88, width / 16));
  const longest = Math.max(1, ...scene.titleLines.map((l) => l.length));
  const fontSize = longest > 18 ? baseSize * 0.72 : longest > 11 ? baseSize * 0.86 : baseSize;

  return (
    <AbsoluteFill style={{backgroundColor: scene.background, overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${bgScale})`}}>
        <Img
          src={staticFile(scene.src)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            filter: 'blur(24px) brightness(0.42) saturate(1.15)',
          }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(circle at 50% 44%, rgba(0,0,0,0.04) 0%, rgba(0,0,0,0.58) 100%)',
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          padding: '0 10%',
        }}
      >
        <div style={{textAlign: 'center'}}>
          {scene.titleLines.map((line, i) => {
            const start = 4 + i * 6;
            const p = interpolate(frame, [start, start + 14], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div
                key={`${i}-${line}`}
                style={{
                  color: '#f7fbff',
                  fontFamily:
                    '"Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif',
                  fontSize,
                  fontWeight: 800,
                  lineHeight: 1.28,
                  letterSpacing: 2,
                  textShadow: '0 8px 40px rgba(0,0,0,0.65)',
                  opacity: p,
                  transform: `translateY(${(1 - p) * 26}px)`,
                }}
              >
                {line}
              </div>
            );
          })}
          <div
            style={{
              width: 86,
              height: 5,
              margin: '30px auto 0',
              borderRadius: 3,
              background: scene.accent,
              opacity: interpolate(frame, [18, 34], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }),
              transform: `scaleX(${interpolate(frame, [18, 34], [0.2, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              })})`,
            }}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
