import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { ThemeProvider } from '@/components/theme-provider';
import { GlobalAuthAlert } from '@/components/layout/GlobalAuthAlert';
import { Toaster } from "@/components/ui/toaster";
import { ErrorBoundary } from '@/components/ErrorBoundary';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'LinkedIn Bot Dashboard',
  description: 'Control center for LinkedIn Automation on Raspberry Pi',
  // 🔒 SECURITY: Empêcher l'indexation par les moteurs de recherche
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      follow: false,
      noimageindex: true,
      'max-video-preview': -1,
      'max-image-preview': 'none',
      'max-snippet': -1,
    },
  },
  // Pas de référencement
  alternates: {},
  // Pas de Open Graph (partage réseaux sociaux)
  openGraph: undefined,
  twitter: undefined,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body className={`${inter.className} bg-slate-950 text-slate-100`}>
        <ErrorBoundary>
          <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
            <GlobalAuthAlert />
            {children}
            <Toaster />
          </ThemeProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
