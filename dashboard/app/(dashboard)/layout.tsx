import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'
import { ThemeProvider } from '@/components/theme-provider'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'LinkedIn Bot Dashboard',
  description: 'Control center for LinkedIn Automation on Raspberry Pi',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr">
      <body className={`${inter.className} bg-slate-950 text-slate-100 overflow-hidden`}>
        {/* Provider pour le thème dark par défaut */}
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <div className="flex h-screen w-full">
            {/* Sidebar fixe à gauche */}
            <aside className="hidden md:flex w-64 flex-col border-r border-slate-800 bg-slate-900">
              <Sidebar />
            </aside>

            {/* Zone principale scrollable */}
            <main className="flex-1 overflow-y-auto bg-slate-950 p-4 md:p-8">
              {children}
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  )
}
