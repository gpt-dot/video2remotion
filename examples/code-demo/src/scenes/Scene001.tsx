import React from 'react';
import {staticFile} from 'remotion';
import {SceneFrame} from '../components/SceneFrame';
import {TextBlock} from '../components/TextBlock';
import {BulletList} from '../components/BulletList';
import {Panel} from '../components/Panel';
import {MediaLayer} from '../components/MediaLayer';
import {MediaCard} from '../components/MediaCard';
import {MotionCard} from '../components/MotionCard';
import {theme} from '../theme';

export const Scene001: React.FC = () => {
  return (
    <SceneFrame background={"#07080a"} transition="cut">
      <MediaLayer src="frames/scene-001.jpg" fit="cover" scaleFrom={1.09} scaleTo={1} panX={-1.1} panY={0.7} />
    </SceneFrame>
  );
};
