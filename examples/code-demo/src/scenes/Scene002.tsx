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

export const Scene002: React.FC = () => {
  return (
    <SceneFrame background={"#0b1223"} transition="cut">
      <TextBlock text={"体扩展的边界"} x={0.1398} y={0.2747} width={0.2632} size={0.067} color="#ecf0f7" weight={800} align="left" enter="up" delay={4} />
      <TextBlock text={"图片构建时内联为 data URI， 两个引擎零配置"} x={0.1091} y={0.3997} width={0.5835} size={0.0377} color="#e2e6f0" weight={500} align="left" enter="fade" delay={8} />
      <TextBlock text={"音频染后由 ffmpeg 混流不重编码画面"} x={0.1091} y={0.5553} width={0.5419} size={0.026} color="#e3e7f0" weight={500} align="left" enter="fade" delay={12} />
      <TextBlock text={"只允许本地素材保证离线可复现"} x={0.1091} y={0.6479} width={0.4372} size={0.0377} color="#e3e7f0" weight={500} align="left" enter="fade" delay={16} />
    </SceneFrame>
  );
};
