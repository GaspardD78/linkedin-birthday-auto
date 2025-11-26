import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as path from 'path';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Chemins possibles pour le fichier de logs
    const possiblePaths = [
      path.join(process.cwd(), '..', 'logs', 'linkedin_bot.log'),  // Pour dev local
      '/app/logs/linkedin_bot.log',  // Pour Docker
      path.join(process.cwd(), 'logs', 'linkedin_bot.log'),  // Fallback
    ];

    let logFilePath: string | null = null;
    let fileContent = '';

    // Trouver le premier chemin qui existe
    for (const testPath of possiblePaths) {
      if (fs.existsSync(testPath)) {
        logFilePath = testPath;
        break;
      }
    }

    if (!logFilePath) {
      console.warn('Log file not found in any expected location');
      return NextResponse.json({
        logs: [{
          timestamp: new Date().toISOString(),
          level: 'WARN',
          message: 'Fichier de logs non trouvé. Le bot est-il démarré ?'
        }]
      });
    }

    // Lire le fichier
    fileContent = fs.readFileSync(logFilePath, 'utf-8');

    // Diviser en lignes et prendre les 50 dernières
    const lines = fileContent.split('\n').filter(line => line.trim() !== '');
    const lastLines = lines.slice(-50);

    // Transformer en format structuré pour le frontend
    const logs = lastLines.map(line => {
      // Essayer de parser le format [timestamp] [level] message
      const match = line.match(/^\[(.*?)\]\s*\[(.*?)\]\s*(.*)$/);

      if (match) {
        return {
          timestamp: match[1],
          level: match[2],
          message: match[3]
        };
      }

      // Si pas de match, retourner la ligne brute
      return {
        timestamp: new Date().toISOString(),
        level: 'INFO',
        message: line
      };
    });

    return NextResponse.json({ logs });

  } catch (error) {
    console.error('Error reading log file:', error);

    return NextResponse.json({
      logs: [{
        timestamp: new Date().toISOString(),
        level: 'ERROR',
        message: `Erreur lors de la lecture des logs: ${error instanceof Error ? error.message : 'Unknown error'}`
      }]
    });
  }
}
