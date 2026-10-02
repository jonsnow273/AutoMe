/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0a0f',
          800: '#111118',
          700: '#1a1a24',
          600: '#242433',
          500: '#2e2e42',
        },
        accent: {
          600: '#5a4de0',
          500: '#7c6af0',
          400: '#9d8ff5',
          300: '#bdb4f8',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      animation: {
        'spin-slow': 'spin 1.5s linear infinite',
      }
    },
  },
  plugins: [],
}
