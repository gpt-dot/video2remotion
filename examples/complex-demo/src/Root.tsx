import React from 'react';
import {Composition} from 'remotion';
import {VideoFromFootage} from './VideoFromFootage';
import {config} from './config';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoFromFootage"
      component={VideoFromFootage}
      durationInFrames={config.durationInFrames}
      fps={config.fps}
      width={config.width}
      height={config.height}
    />
  );
};
