export const theme = {
  colors: {
    background: "#07080b",
    text: '#f7fbff',
    muted: '#9fb3c8',
    accent: "#56beff",
    panel: 'rgba(10, 18, 32, 0.72)',
    panelBorder: 'rgba(255, 255, 255, 0.10)',
  },
  font: {
    family: '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif',
    titleWeight: 800,
    bodyWeight: 500,
    lineHeight: 1.3,
  },
  radius: 18,
} as const;

export type Theme = typeof theme;
