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
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
  // REMOVED: Rewrite rule that was bypassing route handlers and their authentication
  // All API proxying is now handled by dedicated route handlers in app/api/*
  // which properly inject API keys for backend communication
};

module.exports = nextConfig;
