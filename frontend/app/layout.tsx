import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import { Playfair_Display, DM_Sans } from 'next/font/google';
import './globals.css';

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Kansi AI - Mental Health Screening',
  description: 'AI-powered mental health screening tool with privacy-first design',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en" className={`${playfair.variable} ${dmSans.variable}`}>
        <body className="font-body bg-white text-brown-900 antialiased">{children}</body>
      </html>
    </ClerkProvider>
  );
}
