import React from 'react';
import {OffthreadVideo, staticFile, useVideoConfig} from 'remotion';

export const ObjectCard: React.FC<{
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
  fit?: 'contain' | 'cover';
}> = ({src, x, y, width, height, fit = 'contain'}) => {
  const {height: canvasH} = useVideoConfig();
  return (
    <div
      style={{
        position: 'absolute',
        left: `${x * 100}%`,
        top: `${y * 100}%`,
        width: `${width * 100}%`,
        height: `${height * 100}%`,
        filter: 'drop-shadow(0 18px 34px rgba(0,0,0,0.35))',
      }}
    >
      <OffthreadVideo
        src={staticFile(src)}
        muted
        transparent
        style={{width: '100%', height: '100%', objectFit: fit}}
      />
    </div>
  );
};
