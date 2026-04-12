import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['Playfair Display', 'Georgia', 'serif'],
        body: ['DM Sans', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Brown & White theme
        brown: {
          50: '#FAF8F5',
          100: '#F5F0EB',
          200: '#E8DCCA',
          300: '#D2B48C',
          400: '#B89F6D',
          500: '#8B4513', // Saddle brown
          600: '#7A3E11',
          700: '#5F2F0E',
          800: '#4A260B',
          900: '#331B08',
        },
        cream: {
          50: '#FFFFFF',
          100: '#FEFEFE',
          200: '#F8F8F8',
          300: '#F0F0F0',
          400: '#E8E8E8',
        },
        glass: 'rgba(255,255,255,0.45)',
      },
      backdropBlur: {
        xs: '4px',
      },
      boxShadow: {
        glass: '0 8px 32px rgba(139, 69, 19, 0.08)',
        inner: 'inset 0 1px 1px rgba(255, 255, 255, 0.8)',
      },
      borderRadius: {
        'glass': '20px',
      },
      animation: {
        'float': 'float 20s ease-in-out infinite',
        'breathe': 'breathe 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '25%': { transform: 'translate(30px, -20px) scale(1.05)' },
          '50%': { transform: 'translate(-15px, 15px) scale(0.95)' },
          '75%': { transform: 'translate(20px, 25px) scale(1.02)' },
        },
        breathe: {
          '0%, 100%': { opacity: '0.8', transform: 'scale(1)' },
          '50%': { opacity: '1', transform: 'scale(1.02)' },
        },
      },
    },
  },
  plugins: [],
};
export default config;
