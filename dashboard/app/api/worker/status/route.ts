import { NextResponse } from 'next/server';
import Redis from 'ioredis';

export const dynamic = 'force-dynamic';

// Connexion à l'instance Redis du bot
// Note : Le nom d'hôte 'redis-bot' est résolu par Docker Compose
const redis = new Redis({
  host: process.env.BOT_REDIS_HOST || 'redis-bot',
  port: parseInt(process.env.BOT_REDIS_PORT || '6379'),
  // Gérer les erreurs de connexion pour ne pas faire crasher le dashboard
  errorHandler: (error) => {
    return null; // Supprime les erreurs de reconnexion dans les logs
  },
});

export async function GET() {
  try {
    // Ping Redis pour vérifier la connexion
    await redis.ping();

    // Récupérer le nombre de tâches en attente
    const pendingTasks = await redis.llen('rq:queue:default');

    // Récupérer la liste des workers actifs (busy)
    const workers = await redis.smembers('rq:workers');
    let busyWorkers = 0;
    for (const workerKey of workers) {
        const state = await redis.hget(workerKey, 'state');
        if (state === 'busy') {
            busyWorkers++;
        }
    }

    let status = 'inactif';
    if (busyWorkers > 0) {
      status = 'actif';
    } else if (pendingTasks > 0) {
      status = 'en attente';
    }

    return NextResponse.json({
      status,
      pending_tasks: pendingTasks,
      busy_workers: busyWorkers,
    });

  } catch (error) {
    // Si Redis n'est pas accessible, retourner un état par défaut
    const errorMessage = error instanceof Error ? error.message : String(error);

    return NextResponse.json(
      {
        status: 'inconnu',
        pending_tasks: 0,
        busy_workers: 0,
        error: 'Impossible de se connecter à Redis.',
      },
      { status: 503 } // Service Unavailable
    );
  }
}
