import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {CaptionData} from '../timeline';
import {video} from '../timeline';

export const Caption: React.FC<{
  caption: CaptionData;
  accent: string;
  durationInFrames: number;
}> = ({caption, accent, durationInFrames}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({
    frame,
    fps,
    config: {damping: 18, stiffness: 120, mass: 0.6},
  });

  const fadeOut = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames],
    [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  if (video.captionStyle === 'off') {
    return null;
  }

  const top = caption.position === 'top';
  const y = interpolate(enter, [0, 1], [top ? -24 : 24, 0]);
  const opacity = interpolate(enter, [0, 1], [0, 1]) * fadeOut;
  const base =
    caption.text.length > 36 ? 30 : caption.text.length > 22 ? 36 : 42;
  const style = video.captionStyle;
  const fontSize = style === 'minimal' ? base * 0.82 : style === 'clean' ? base * 0.92 : base;
  const padding = style === 'minimal' ? '12px 20px' : '18px 26px';
  const background =
    style === 'bold'
      ? 'rgba(4, 8, 16, 0.76)'
      : style === 'clean'
        ? 'rgba(4, 8, 16, 0.58)'
        : 'rgba(4, 8, 16, 0.36)';
  const border = style === 'minimal' ? `2px solid ${accent}` : `5px solid ${accent}`;

  return (
    <AbsoluteFill
      style={{
        justifyContent: top ? 'flex-start' : 'flex-end',
        alignItems: 'center',
        padding: top ? '9% 8% 0' : '0 8% 9%',
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          maxWidth: '86%',
          padding,
          borderRadius: 18,
          background,
          borderLeft: border,
          boxShadow: style === 'minimal' ? 'none' : '0 12px 40px rgba(0,0,0,0.35)',
          color: '#f7fbff',
          fontFamily:
            '"Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif',
          fontSize,
          lineHeight: 1.35,
          fontWeight: 700,
          letterSpacing: 1,
          textAlign: 'center',
          transform: `translateY(${y}px)`,
          opacity,
        }}
      >
        {caption.text}
      </div>
    </AbsoluteFill>
  );
};
