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
  typescript: {
    // Ignore les erreurs TS pendant le build (le faire en CI/pre-commit)
    ignoreBuildErrors: true,
  },
  experimental: {
    // Optimisations possibles pour build plus léger
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
  // CRITIQUE : Exposer les variables d'environnement pour le runtime serveur
  // Sans cette config, les variables d'env Docker ne sont pas accessibles dans les API routes
  env: {
    BOT_API_URL: process.env.BOT_API_URL || 'http://linkedin-bot-api:8000',
    BOT_API_KEY: process.env.BOT_API_KEY || 'internal_secret_key',
    BOT_REDIS_HOST: process.env.BOT_REDIS_HOST || 'redis-bot',
    BOT_REDIS_PORT: process.env.BOT_REDIS_PORT || '6379',
    BOT_REDIS_URL: process.env.BOT_REDIS_URL || 'redis://redis-bot:6379',
  },
};

module.exports = nextConfig;
