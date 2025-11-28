'use client'

import { Inter } from 'next/font/google'
import '../globals.css'
import { Sidebar } from '@/components/layout/Sidebar'
import { ThemeProvider } from '@/components/theme-provider'
import { Menu, X } from 'lucide-react'
import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const pathname = usePathname()

  // Fermer le menu mobile lors du changement de page
  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [pathname])

  return (
    <html lang="fr">
      <body className={`${inter.className} bg-slate-950 text-slate-100`}>
        {/* Provider pour le thème dark par défaut */}
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <div className="flex h-screen w-full overflow-hidden">
            {/* Bouton hamburger mobile */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-slate-800 text-slate-100 hover:bg-slate-700 transition-colors"
              aria-label="Toggle menu"
            >
              {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>

            {/* Overlay pour mobile */}
            {isMobileMenuOpen && (
              <div
                className="md:hidden fixed inset-0 bg-black/50 z-30"
                onClick={() => setIsMobileMenuOpen(false)}
              />
            )}

            {/* Sidebar fixe à gauche (desktop) et overlay (mobile) */}
            <aside className={`
              w-64 flex-col border-r border-slate-800 bg-slate-900 z-40
              md:flex
              ${isMobileMenuOpen ? 'flex fixed inset-y-0 left-0' : 'hidden'}
            `}>
              <Sidebar />
            </aside>

            {/* Zone principale scrollable */}
            <main className="flex-1 overflow-y-auto bg-slate-950 p-4 md:p-8 pt-16 md:pt-8">
              {children}
            </main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  )
}
