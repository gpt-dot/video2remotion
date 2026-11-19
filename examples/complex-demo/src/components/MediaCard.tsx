import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {theme} from '../theme';

export const MediaCard: React.FC<{
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
  fit?: 'cover' | 'contain';
  radius?: number;
  shadow?: boolean;
  depth?: number;
}> = ({src, x, y, width, height, fit = 'cover', radius = 0.018, shadow = true, depth = 0.3}) => {
  const frame = useCurrentFrame();
  const {durationInFrames, height: canvasH} = useVideoConfig();
  const p = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const scale = 1 + depth * 0.035 * p;
  const tx = depth * 0.8 * p;

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
      }}
    >
      <AbsoluteFill style={{transform: `scale(${scale}) translateX(${tx}%)`}}>
        <Img
          src={staticFile(src)}
          style={{width: '100%', height: '100%', objectFit: fit}}
        />
      </AbsoluteFill>
    </div>
  );
};
