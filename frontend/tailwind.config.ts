import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ISRO institutional palette (retinted from the original space-dashboard
        // tokens — same semantic names so every existing page picks it up
        // without per-component edits).
        'space-black': '#eef1f6', // page background (was near-black)
        'space-dark': '#ffffff', // card/panel background (was dark navy)
        'space-blue': '#1a3d8f', // ISRO navy — primary accent, borders, links
        'space-purple': '#5b3fa0',
        'space-cyan': '#0e7490',
        'space-teal': '#0f766e',
        'space-indigo': '#3730a3',
        'space-violet': '#7e22ce',
        'space-fuchsia': '#a21caf',
        'space-pink': '#be185d',
        'space-gray': '#475569', // secondary text (was light gray, now slate for light bg)
        'space-light': '#0f172a', // primary text (was near-white, now near-black)
        'space-white': '#0f172a',
        'space-green': '#15803d',
        'space-yellow': '#a16207',
        'space-orange': '#c2410c',
        // ISRO/Government of India accent colors used by the new shell
        'isro-navy': '#0b2a5b',
        'isro-navy-dark': '#071c3d',
        'isro-saffron': '#ff9933',
        'isro-green': '#138808',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'monospace'],
      },
      boxShadow: {
        // Glassmorphism effects
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3), backdrop-filter: blur(10px) contrast(1.2)',
        'glass-sm': '0 4px 16px rgba(0, 0, 0, 0.2), backdrop-filter: blur(8px) contrast(1.1)',
        'glass-lg': '0 12px 48px rgba(0, 0, 0, 0.4), backdrop-filter: blur(12px) contrast(1.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'marquee': 'marquee 35s linear infinite',
      },
      keyframes: {
        float: {
          '0%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
          '100%': { transform: 'translateY(0px)' },
        },
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
      }
    },
  },
  plugins: [],
}

export default config