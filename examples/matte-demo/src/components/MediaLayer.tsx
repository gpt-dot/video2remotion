import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export type MediaLayerProps = {
  src: string;
  fit?: 'cover' | 'contain';
  scaleFrom?: number;
  scaleTo?: number;
  panX?: number;
  panY?: number;
  filter?: string;
  opacity?: number;
};

export const MediaLayer: React.FC<MediaLayerProps> = ({
  src,
  fit = 'cover',
  scaleFrom = 1,
  scaleTo = 1,
  panX = 0,
  panY = 0,
  filter = 'none',
  opacity = 1,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const p = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const scale = interpolate(p, [0, 1], [scaleFrom, scaleTo]);
  const x = interpolate(p, [0, 1], [0, panX]);
  const y = interpolate(p, [0, 1], [0, panY]);

  return (
    <AbsoluteFill style={{opacity}}>
      <AbsoluteFill style={{transform: `scale(${scale}) translate(${x}%, ${y}%)`}}>
        <Img
          src={staticFile(src)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: fit,
            filter,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
