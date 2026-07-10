import type { Config } from 'tailwindcss';

export default {
  content: ['./src/**/*.{tsx,ts,jsx,js}', './index.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        sage: {
          bg: '#1a1b26',
          sidebar: '#16161e',
          surface: '#24283b',
          elevated: '#1f2335',
          purple: '#8b5cf6',
          blue: '#3b82f6',
          green: '#4ade80',
          red: '#f87171',
          amber: '#fbbf24',
          text: '#ededec',
          muted: '#a0a0a0',
          dim: '#6b6b6b',
          user: '#c084fc',
          border: '#333648',
          'border-active': '#8b5cf6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config;
