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
    <SceneFrame background={"#09111e"} transition="cut">
      <MotionCard src="clips/scene-000-clip.mp4" x={0} y={0.1511} width={0.5965} height={0.6181} fit="cover" radius={0.014} />
      <TextBlock text={"区域提取测试"} x={0.5585} y={0.3108} width={0.2283} size={0.0403} color="#e3e8f0" weight={800} align="left" enter="up" delay={4} />
      <TextBlock text={"图片区域应成区域视频"} x={0.5481} y={0.4108} width={0.2471} size={0.034} color="#aeb5c5" weight={500} align="left" enter="fade" delay={8} />
      <TextBlock text={"背景仍然由代码生成"} x={0.5481} y={0.4849} width={0.2085} size={0.034} color="#adb4c5" weight={500} align="left" enter="fade" delay={12} />
    </SceneFrame>
  );
};
