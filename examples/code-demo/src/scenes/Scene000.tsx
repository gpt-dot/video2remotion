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

export const Scene000: React.FC = () => {
  return (
    <SceneFrame background={"#0b1223"} transition="cut">
      <TextBlock text={"一份规格两种引擎"} x={0.1882} y={0.3191} width={0.6341} size={0.11} color="#ebf0fa" weight={800} align="center" enter="up" delay={4} />
      <TextBlock text={"图片音频转场都由同一份 JSON 驱动"} x={0.2622} y={0.5691} width={0.4861} size={0.026} color="#929ab5" weight={500} align="center" enter="fade" delay={8} />
    </SceneFrame>
  );
};
