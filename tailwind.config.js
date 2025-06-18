/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './chart/templates/**/*.html',
    './static/src/**/*.js',
    './static/src/**/*.css',
    './**/*.html',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#250400',
        accent: '#cd8062',
        plum: '#5d4462',
        plum2: '#5d4464',
        dark: '#1b0220',
        dark2: '#1a021f',
      },
    },
  },
  plugins: [],
  safelist: [
    'bg-primary', 'bg-accent', 'bg-plum', 'bg-plum2', 'bg-dark', 'bg-dark2',
    'text-primary', 'text-accent', 'text-plum', 'text-plum2', 'text-dark', 'text-dark2',
    'border-primary', 'border-accent', 'border-plum', 'border-plum2', 'border-dark', 'border-dark2'
  ],
}

