import React from 'react';
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {theme} from '../theme';

export type TextBlockProps = {
  text: string;
  x: number;
  y: number;
  width: number;
  size: number;
  color?: string;
  weight?: number;
  align?: 'left' | 'center' | 'right';
  enter?: 'fade' | 'up';
  delay?: number;
  lineHeight?: number;
  opacity?: number;
};

export const TextBlock: React.FC<TextBlockProps> = ({
  text,
  x,
  y,
  width,
  size,
  color = theme.colors.text,
  weight = theme.font.bodyWeight,
  align = 'left',
  enter = 'up',
  delay = 0,
  lineHeight = theme.font.lineHeight,
  opacity = 1,
}) => {
  const frame = useCurrentFrame();
  const {fps, height} = useVideoConfig();
  const local = Math.max(0, frame - delay);
  const p = spring({
    frame: local,
    fps,
    config: {damping: 18, stiffness: 110, mass: 0.7},
  });
  const a = interpolate(p, [0, 1], [0, 1]) * opacity;
  const ty = enter === 'up' ? interpolate(p, [0, 1], [28, 0]) : 0;

  return (
    <div
      style={{
        position: 'absolute',
        left: `${x * 100}%`,
        top: `${y * 100}%`,
        width: `${width * 100}%`,
        transform: `translateY(${ty}px)`,
        opacity: a,
        color,
        fontFamily: theme.font.family,
        fontSize: size * height,
        fontWeight: weight,
        lineHeight,
        textAlign: align,
        whiteSpace: 'pre-wrap',
        textShadow: '0 6px 30px rgba(0,0,0,0.40)',
      }}
    >
      {text}
    </div>
  );
};
