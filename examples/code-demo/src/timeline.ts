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
    "durationInFrames": 90,
    "kind": "title",
    "accent": "#56beff",
    "transition": "cut",
    "mode": "graphic"
  },
  {
    "id": "scene-001",
    "from": 90,
    "durationInFrames": 98,
    "kind": "live",
    "accent": "#4e87f3",
    "transition": "cut",
    "mode": "media"
  },
  {
    "id": "scene-002",
    "from": 188,
    "durationInFrames": 202,
    "kind": "slide",
    "accent": "#56beff",
    "transition": "cut",
    "mode": "graphic"
  }
];

export const bpm = 187.5;
export const beats: number[] = [6, 16, 31, 39, 46, 53, 70, 77, 102, 112, 127, 135, 144, 154, 167, 177, 185, 195, 208, 227, 238, 262, 269, 278, 287, 294, 302, 310, 323, 334];
