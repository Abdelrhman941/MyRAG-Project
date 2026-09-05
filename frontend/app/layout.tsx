import { ThemeProvider } from '@/components/providers/theme-provider';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ConfigProvider } from '@/lib/config';
import { fetchAppConfig } from '@/lib/server-config';
import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { SplashScreen } from './_components/splash-screen';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  title: {
    default: 'RAG Assistant',
    template: '%s · RAG Assistant',
  },
  description: 'Ask focused questions and get answers grounded in your documents.',
  robots: {
    index: false,
    follow: false,
  },
};

export const viewport: Viewport = {
  colorScheme: 'light dark',
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const config = await fetchAppConfig();

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/favicon/favicon.ico" sizes="any" />
        <link rel="icon" type="image/svg+xml" href="/favicon/icon0.svg" />
        <link rel="icon" type="image/png" href="/favicon/icon1.png" />
        <link rel="apple-touch-icon" href="/favicon/apple-icon.png" />
        <link rel="manifest" href="/favicon/manifest.json" />
      </head>
      <body
        className={`${inter.className} min-h-screen bg-background text-foreground antialiased selection:bg-primary/20`}
      >
        <ThemeProvider>
          <ConfigProvider config={config}>
            <SplashScreen />
            <TooltipProvider>{children}</TooltipProvider>
            <Toaster />
          </ConfigProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
