# Architecture du Dashboard (Proposition)

Ce document décrit la structure du projet pour le nouveau Dashboard LinkedIn Bot, optimisé pour Raspberry Pi 4 et Synology.

## Structure des répertoires

```
dashboard/
├── docker-compose.yml             # Configuration Docker Compose (App + Redis)
├── Dockerfile.prod                # Image Docker optimisée pour Next.js (Standalone)
├── next.config.js                 # Configuration Next.js (Standalone)
├── package.json                   # Dépendances (React, Next, Puppeteer, etc.)
├── tsconfig.json                  # Configuration TypeScript
├── .env.production                # Variables d'environnement (Template)
├── app/                           # Next.js App Router
│   ├── layout.tsx                 # Layout principal (Sidebar, Providers)
│   ├── page.tsx                   # Dashboard Home (KPIs, Health)
│   ├── messages/                  # Page gestion messages
│   │   └── page.tsx
│   ├── contacts/                  # Page gestion contacts
│   │   └── page.tsx
│   ├── campaigns/                 # Page gestion campagnes
│   │   └── page.tsx
│   ├── settings/                  # Page configuration
│   │   └── page.tsx
│   ├── logs/                      # Page logs temps réel
│   │   └── page.tsx
│   └── api/                       # API Routes (Backend logic)
│       ├── bot/                   # Contrôle du bot (start/stop)
│       │   └── route.ts
│       ├── system/                # Infos système (RAM, Temp)
│       │   └── route.ts
│       └── logs/                  # Websocket upgrade / Log streaming
│           └── route.ts
├── components/                    # Composants React
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   └── Header.tsx
│   ├── dashboard/
│   │   ├── StatsCard.tsx
│   │   ├── HealthWidget.tsx       # Widget CPU/RAM
│   │   └── BotStatus.tsx          # Widget État Bot
│   ├── controls/
│   │   └── BotController.tsx      # Boutons Start/Stop/Kill
│   └── ui/                        # Composants shadcn/ui (Button, Card, etc.)
├── lib/                           # Logique métier et Utilitaires
│   ├── db.ts                      # Connexion MariaDB (Synology)
│   ├── redis.ts                   # Connexion Redis
│   ├── puppet-master.ts           # Singleton Puppeteer (Queue Manager)
│   ├── system-monitor.ts          # Lecture métriques RPi
│   └── logger.ts                  # Gestionnaire de logs
└── store/                         # Gestion d'état (Zustand)
    ├── useBotStore.ts
    └── useSettingsStore.ts
```

## Points Clés Architecture

1.  **Next.js Standalone**: Réduit la taille de l'image Docker et la consommation mémoire.
2.  **Puppeteer Singleton**: Un seul navigateur lancé à la fois, contrôlé par `puppet-master.ts` via une queue Redis pour éviter la saturation RAM.
3.  **Base de données Externe**: Connexion directe à MariaDB sur le NAS Synology.
4.  **Monitoring Hardware**: API locale pour lire `/sys/class/thermal/thermal_zone0/temp` et `os.freemem()` sur le Pi.
