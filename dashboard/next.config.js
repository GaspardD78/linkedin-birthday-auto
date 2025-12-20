/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Désactiver les features lourdes si nécessaire
  poweredByHeader: false,
  // Optimisation des images si on utilise le composant Image
  images: {
    unoptimized: true, // Moins de CPU utilisé pour le traitement d'images
  },
  // Optimisation de la compilation sur Raspberry Pi
  eslint: {
    // Ignore le linting pendant le build pour accélérer (le faire en CI/pre-commit)
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Ignore les erreurs TS pendant le build (le faire en CI/pre-commit)
    ignoreBuildErrors: true,
  },
  experimental: {
    // Optimisations possibles pour build plus léger
    optimizePackageImports: ['lucide-react', 'recharts', '@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
  },
  // Optimisations pour build time sur RPi4 avec peu de mémoire
  swcMinify: true, // Utiliser SWC au lieu de Terser pour la minification (plus rapide)
  compress: true, // Gzip compression côté serveur
  // REMOVED: Rewrite rule that was bypassing route handlers and their authentication
  // All API proxying is now handled by dedicated route handlers in app/api/*
  // which properly inject API keys for backend communication

  // ═══════════════════════════════════════════════════════════════
  // SECURITY HEADERS (Audit Sécurité 2025)
  // Protection contre XSS, Clickjacking, MIME sniffing, etc.
  // ═══════════════════════════════════════════════════════════════
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload'
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()'
          },
          {
            key: 'Content-Security-Policy',
            value: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none';"
          },
          {
            key: 'X-Robots-Tag',
            value: 'noindex, nofollow, noarchive, nosnippet, noimageindex, nocache'
          }
        ],
      },
    ];
  },
};

module.exports = nextConfig;
