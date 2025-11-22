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
  experimental: {
    // Optimisations possibles pour build plus léger
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
  webpack: (config) => {
    // Configuration spécifique si besoin (ex: exclusion de certaines libs côté client)
    return config;
  },
};

module.exports = nextConfig;
