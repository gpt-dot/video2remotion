import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';

export const SceneFrame: React.FC<{
  background: string;
  children: React.ReactNode;
  vignette?: boolean;
  transition?: 'cut' | 'fade' | 'slide';
}> = ({background, children, vignette = true, transition = 'cut'}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, 9], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const opacity = transition === 'cut' ? 1 : p;
  const x = transition === 'slide' ? interpolate(p, [0, 1], [4, 0]) : 0;

  return (
    <AbsoluteFill
      style={{
        background,
        overflow: 'hidden',
        opacity,
        transform: transition === 'slide' ? `translateX(${x}%)` : undefined,
      }}
    >
      {children}
      {vignette ? (
        <AbsoluteFill
          style={{
            background:
              'radial-gradient(circle at 50% 46%, rgba(0,0,0,0) 42%, rgba(0,0,0,0.34) 100%)',
            pointerEvents: 'none',
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};
