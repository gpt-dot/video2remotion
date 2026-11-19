import React from 'react';
import {useVideoConfig} from 'remotion';

export const Panel: React.FC<{
  x: number;
  y: number;
  width: number;
  height: number;
  fill: string;
  radius?: number;
  border?: string;
  opacity?: number;
}> = ({x, y, width, height, fill, radius = 0.018, border, opacity = 1}) => {
  const {height: h} = useVideoConfig();
  return (
    <div
      style={{
        position: 'absolute',
        left: `${x * 100}%`,
        top: `${y * 100}%`,
        width: `${width * 100}%`,
        height: `${height * 100}%`,
        background: fill,
        borderRadius: radius * h,
        border: border ? `1px solid ${border}` : undefined,
        opacity,
        boxShadow: '0 18px 60px rgba(0,0,0,0.28)',
      }}
    />
  );
};
