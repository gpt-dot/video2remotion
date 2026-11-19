import React from 'react';
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {theme} from '../theme';

export type BulletListProps = {
  items: string[];
  x: number;
  y: number;
  width: number;
  size: number;
  color?: string;
  bulletColor?: string;
  gap?: number;
  delay?: number;
};

export const BulletList: React.FC<BulletListProps> = ({
  items,
  x,
  y,
  width,
  size,
  color = theme.colors.text,
  bulletColor = theme.colors.accent,
  gap = 0.018,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const fontSize = size * height;
  const bulletSize = fontSize * 0.72;

  return (
    <div
      style={{
        position: 'absolute',
        left: `${x * 100}%`,
        top: `${y * 100}%`,
        width: `${width * 100}%`,
        display: 'flex',
        flexDirection: 'column',
        gap: gap * height,
        fontFamily: theme.font.family,
        fontSize,
        lineHeight: 1.35,
        color,
      }}
    >
      {items.map((item, i) => {
        const local = Math.max(0, frame - delay - i * 5);
        const p = spring({
          frame: local,
          fps,
          config: {damping: 18, stiffness: 120, mass: 0.6},
        });
        return (
          <div
            key={`${i}-${item}`}
            style={{
              display: 'flex',
              gap: fontSize * 0.55,
              alignItems: 'flex-start',
              opacity: interpolate(p, [0, 1], [0, 1]),
              transform: `translateX(${interpolate(p, [0, 1], [-18, 0])}px)`,
            }}
          >
            <span
              style={{
                color: bulletColor,
                fontSize: bulletSize,
                lineHeight: 1.55,
                flexShrink: 0,
              }}
            >
              ●
            </span>
            <span style={{whiteSpace: 'pre-wrap'}}>{item}</span>
          </div>
        );
      })}
    </div>
  );
};
