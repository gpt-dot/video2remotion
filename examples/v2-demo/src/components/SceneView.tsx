import React from 'react';
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import type {Scene} from '../timeline';
import {video} from '../timeline';
import {Caption} from './Caption';
import {TitleScene} from './TitleScene';

export const SceneView: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const dur = Math.max(1, scene.durationInFrames);
  const last = Math.max(1, dur - 1);

  if (scene.kind === 'title' && scene.titleLines.length > 0) {
    return <TitleScene scene={scene} />;
  }

  const progress = interpolate(frame, [0, last], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const scale = interpolate(progress, [0, 1], [scene.zoom.from, scene.zoom.to]);
  const x = interpolate(progress, [0, 1], [0, scene.pan.x]);
  const y = interpolate(progress, [0, 1], [0, scene.pan.y]);

  let pulse = 1;
  if (scene.pulse > 0 && video.beats.length > 0) {
    const globalFrame = scene.from + frame;
    let nearest = 999;
    for (const b of video.beats) {
      const d = Math.abs(globalFrame - b);
      if (d < nearest) nearest = d;
    }
    if (nearest < 10) {
      pulse = 1 + scene.pulse * 0.02 * Math.exp(-nearest / 3.5);
    }
  }

  const fade = Math.max(1, Math.round(scene.fade * fps));
  const opacity = interpolate(
    frame,
    [0, fade, Math.max(fade + 1, dur - fade), dur],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: scene.background,
        opacity,
        overflow: 'hidden',
      }}
    >
      <AbsoluteFill
        style={{
          transform: `scale(${scale * pulse}) translate(${x}%, ${y}%)`,
          transformOrigin: 'center center',
        }}
      >
        <Img
          src={staticFile(scene.src)}
          style={{
            width: '100%',
            height: '100%',
            objectFit: scene.fit,
          }}
        />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(0,0,0,0.16) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 70%, rgba(0,0,0,0.30) 100%)',
          pointerEvents: 'none',
        }}
      />

      {scene.caption ? (
        <Caption
          caption={scene.caption}
          accent={scene.accent}
          durationInFrames={dur}
        />
      ) : null}
    </AbsoluteFill>
  );
};
