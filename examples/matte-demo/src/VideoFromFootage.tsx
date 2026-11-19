import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {config} from './config';
import {scenes} from './timeline';
import {sceneComponents} from './scenes';

export const VideoFromFootage: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: config.background}}>
      {config.audio ? <Audio src={staticFile(config.audio)} /> : null}
      {scenes.map((scene, i) => {
        const SceneComponent = sceneComponents[i];
        return (
          <Sequence
            key={scene.id}
            from={scene.from}
            durationInFrames={scene.durationInFrames}
            name={`${scene.id}-${scene.kind}`}
          >
            <SceneComponent />
          </Sequence>
        );
      })}
      {config.letterbox ? (
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
