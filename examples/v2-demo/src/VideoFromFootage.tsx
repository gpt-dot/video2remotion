import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {SceneView} from './components/SceneView';
import {scenes, video} from './timeline';

export const VideoFromFootage: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: video.background}}>
      {video.audio ? <Audio src={staticFile(video.audio)} /> : null}
      {scenes.map((scene) => (
        <Sequence
          key={scene.id}
          from={scene.from}
          durationInFrames={scene.durationInFrames}
          name={`${scene.id}-${scene.kind}`}
        >
          <SceneView scene={scene} />
        </Sequence>
      ))}
      {video.letterbox ? (
        <>
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '6%',
              background: '#000',
              zIndex: 20,
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '6%',
              background: '#000',
              zIndex: 20,
            }}
          />
        </>
      ) : null}
    </AbsoluteFill>
  );
};
