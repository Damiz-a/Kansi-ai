/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['var(--font-playfair)', 'Georgia', 'serif'],
        body: ['var(--font-dm-sans)', 'system-ui', 'sans-serif'],
        sans: ['var(--font-dm-sans)', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Rich Brown & White theme
        brown: {
          50:  '#FDF9F6',
          100: '#F5E9DF',
          200: '#E8CDB8',
          300: '#D4A882',
          400: '#B8855A',
          500: '#8B5E3C',  // medium brown — accents
          600: '#6B3A2A',  // PRIMARY — navbar, buttons
          700: '#4E2617',  // dark brown — headings
          800: '#3A1C10',
          900: '#28130A',
        },
      },
    },
  },
  plugins: [],
};
