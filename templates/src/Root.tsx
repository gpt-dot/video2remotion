import React from 'react';
import {Composition} from 'remotion';
import {VideoFromFootage} from './VideoFromFootage';
import {video} from './timeline';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoFromFootage"
      component={VideoFromFootage}
      durationInFrames={video.durationInFrames}
      fps={video.fps}
      width={video.width}
      height={video.height}
    />
  );
};
