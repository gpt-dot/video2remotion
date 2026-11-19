// 由 video2remotion v2 自动生成。可直接修改分镜数据，或在组件里加自己的动画。
export type CaptionData = {
  text: string;
  position: 'top' | 'bottom';
};

export type Scene = {
  id: string;
  from: number;
  durationInFrames: number;
  src: string;
  fit: 'cover' | 'contain';
  background: string;
  accent: string;
  kind: 'title' | 'slide' | 'screen' | 'live' | 'static' | 'image';
  zoom: {from: number; to: number};
  pan: {x: number; y: number};
  fade: number;
  titleLines: string[];
  caption: CaptionData | null;
  pulse: number;
};

export type VideoMeta = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  background: string;
  audio: string | null;
  source: string;
  scenes: number;
  preset: string;
  letterbox: boolean;
  captionStyle: string;
  bpm: number;
  beats: number[];
};

export const video: VideoMeta = {
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "durationInFrames": 390,
  "background": "#05070d",
  "audio": "audio/audio.m4a",
  "source": "aivideokit-媒体能力演示.remotion.mp4",
  "scenes": 3,
  "preset": "auto",
  "letterbox": false,
  "captionStyle": "bold",
  "bpm": 187.5,
  "beats": [
    6,
    16,
    31,
    39,
    46,
    53,
    70,
    77,
    102,
    112,
    127,
    135,
    144,
    154,
    167,
    177,
    185,
    195,
    208,
    227,
    238,
    262,
    269,
    278,
    287,
    294,
    302,
    310,
    323,
    334
  ]
};

export const scenes: Scene[] = [
  {
    "id": "scene-000",
    "from": 0,
    "durationInFrames": 90,
    "src": "frames/scene-000.jpg",
    "fit": "cover",
    "background": "#07080b",
    "accent": "#56beff",
    "kind": "title",
    "zoom": {
      "from": 1.0,
      "to": 1.055
    },
    "pan": {
      "x": 0.0,
      "y": 0.0
    },
    "fade": 0.28,
    "titleLines": [
      "一份规格两种引擎",
      "图片音频转场都由同一份 JSON 驱动"
    ],
    "caption": null,
    "pulse": 0.4
  },
  {
    "id": "scene-001",
    "from": 90,
    "durationInFrames": 98,
    "src": "frames/scene-001.jpg",
    "fit": "cover",
    "background": "#07080a",
    "accent": "#4e87f3",
    "kind": "live",
    "zoom": {
      "from": 1.09,
      "to": 1.0
    },
    "pan": {
      "x": -1.1,
      "y": 0.7
    },
    "fade": 0.2,
    "titleLines": [],
    "caption": null,
    "pulse": 1.0
  },
  {
    "id": "scene-002",
    "from": 188,
    "durationInFrames": 202,
    "src": "frames/scene-002.jpg",
    "fit": "cover",
    "background": "#07080b",
    "accent": "#56beff",
    "kind": "slide",
    "zoom": {
      "from": 1.0,
      "to": 1.025
    },
    "pan": {
      "x": 0.0,
      "y": 0.0
    },
    "fade": 0.14,
    "titleLines": [],
    "caption": null,
    "pulse": 0.4
  }
];
