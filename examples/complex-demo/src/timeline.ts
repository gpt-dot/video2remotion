export type SceneMeta = {
  id: string;
  from: number;
  durationInFrames: number;
  kind: string;
  accent: string;
  transition: string;
  mode: 'graphic' | 'media' | 'hybrid';
};

export const scenes: SceneMeta[] = [
  {
    "id": "scene-000",
    "from": 0,
    "durationInFrames": 120,
    "kind": "slide",
    "accent": "#72829f",
    "transition": "cut",
    "mode": "hybrid"
  }
];

export const bpm = 0.0;
export const beats: number[] = [];
