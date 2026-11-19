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
      <MediaCard src="crops/scene-000-r0.jpg" x={0.018} y={0.1244} width={0.441} height={0.7123} fit="cover" radius={0.014} depth={0.25} />
      <TextBlock text={"复杂场景也能转成代码"} x={0.4804} y={0.2932} width={0.382} size={0.0403} color="#ecf0f7" weight={800} align="left" enter="up" delay={4} />
      <TextBlock text={"图片区域自动拆成 MediaCard\n文字位置颜色全部参数化\n改一行代码就能重新排版"} x={0.4804} y={0.421} width={0.3065} size={0.026} color="#c3cbda" weight={500} align="left" enter="fade" delay={8} />
    </SceneFrame>
  );
};
