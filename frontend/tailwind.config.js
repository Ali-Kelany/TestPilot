/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx}',
  ],

  theme: {
    extend: {
      // Semantic aliases that map directly onto the backend's status strings
      // (passed | failed | error | running | aborted).
      // Use as: bg-status-passed, text-status-failed, border-status-running …
      colors: {
        status: {
          passed:  { DEFAULT: '#639922', bg: '#EAF3DE', text: '#3B6D11' },
          failed:  { DEFAULT: '#E24B4A', bg: '#FCEBEB', text: '#A32D2D' },
          error:   { DEFAULT: '#E24B4A', bg: '#FCEBEB', text: '#A32D2D' },
          running: { DEFAULT: '#378ADD', bg: '#E6F1FB', text: '#185FA5' },
          aborted: { DEFAULT: '#888780', bg: '#F1EFE8', text: '#5F5E5A' },
        },
        // Accent used for the primary action button and links.
        accent: {
          DEFAULT: '#1D9E75',
          hover:   '#0F6E56',
          subtle:  '#E1F5EE',
          text:    '#085041',
        },
      },

      fontFamily: {
        // Inherit the system stack — keeps the UI feeling native.
        sans: ['ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },

      fontSize: {
        // Extra-small label size used for run metadata.
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },

      borderWidth: {
        // Hairline borders for table rows and panel dividers.
        DEFAULT: '0.5px',
        '0.5':   '0.5px',
      },

      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },

  plugins: [],
}
