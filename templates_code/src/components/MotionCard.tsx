import React from 'react';
import {OffthreadVideo, staticFile, useVideoConfig} from 'remotion';
import {theme} from '../theme';

export const MotionCard: React.FC<{
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
  fit?: 'cover' | 'contain';
  radius?: number;
  shadow?: boolean;
}> = ({src, x, y, width, height, fit = 'cover', radius = 0.014, shadow = true}) => {
  const {height: canvasH} = useVideoConfig();
  return (
    <div
      style={{
        position: 'absolute',
        left: `${x * 100}%`,
        top: `${y * 100}%`,
        width: `${width * 100}%`,
        height: `${height * 100}%`,
        borderRadius: radius * canvasH,
        overflow: 'hidden',
        boxShadow: shadow ? '0 22px 70px rgba(0,0,0,0.38)' : undefined,
        border: `1px solid ${theme.colors.panelBorder}`,
        background: '#05070d',
      }}
    >
      <OffthreadVideo
        src={staticFile(src)}
        muted
        style={{width: '100%', height: '100%', objectFit: fit}}
      />
    </div>
  );
};
