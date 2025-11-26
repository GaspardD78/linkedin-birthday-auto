import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Chemin absolu Docker en priorité (CRITIQUE pour Docker)
    // Ce chemin est monté via docker-compose volumes
    const dockerLogPath = '/app/logs/linkedin_bot.log';

    // Chemins de fallback pour dev local
    const possiblePaths = [
      dockerLogPath,  // Docker (prioritaire)
      path.join(process.cwd(), '..', 'logs', 'linkedin_bot.log'),  // Dev local (parent)
      path.join(process.cwd(), 'logs', 'linkedin_bot.log'),  // Dev local (current)
    ];

    console.log('📋 [LOGS API] Recherche des logs dans:', possiblePaths);

    let logFilePath: string | null = null;
    let fileContent = '';

    // Trouver le premier chemin qui existe
    for (const testPath of possiblePaths) {
      if (fs.existsSync(testPath)) {
        logFilePath = testPath;
        console.log(`✅ [LOGS API] Fichier trouvé: ${testPath}`);
        break;
      }
    }

    if (!logFilePath) {
      console.warn('⚠️  [LOGS API] Fichier de logs non trouvé dans aucun emplacement');
      return NextResponse.json({
        logs: [
          "[INFO] En attente des logs système...",
          "[INFO] Le fichier de logs sera créé au premier démarrage du bot",
          "[INFO] Vérifiez que le conteneur API est démarré"
        ]
      });
    }

    // Lire le fichier
    fileContent = fs.readFileSync(logFilePath, 'utf-8');

    if (!fileContent || fileContent.trim() === '') {
      console.warn('⚠️  [LOGS API] Fichier de logs vide');
      return NextResponse.json({
        logs: [
          "[INFO] En attente des logs système...",
          "[INFO] Le fichier existe mais est vide"
        ]
      });
    }

    // Diviser en lignes et prendre les 50 dernières lignes non vides
    const lines = fileContent.split('\n').filter(line => line.trim() !== '');
    const lastLines = lines.slice(-50);

    console.log(`📋 [LOGS API] ${lastLines.length} lignes de logs retournées`);

    // Retourner les lignes brutes (le frontend peut les parser)
    return NextResponse.json({ logs: lastLines });

  } catch (error) {
    console.error('❌ [LOGS API] Erreur lors de la lecture des logs:', error);

    return NextResponse.json({
      logs: [
        `[ERROR] Erreur lors de la lecture des logs: ${error instanceof Error ? error.message : 'Unknown error'}`,
        "[INFO] Vérifiez les permissions du fichier de logs"
      ]
    });
  }
}
