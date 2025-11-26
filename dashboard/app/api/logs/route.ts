import { NextResponse } from 'next/server';
import * as fs from 'fs';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Cible uniquement le chemin Docker (volume garanti monté)
    const LOG_FILE = '/app/logs/linkedin_bot.log';

    console.log('📋 [LOGS API] Lecture des logs depuis:', LOG_FILE);

    // Vérifier si le fichier existe
    if (!fs.existsSync(LOG_FILE)) {
      console.warn('⚠️  [LOGS API] Fichier de logs non trouvé');
      return NextResponse.json({
        logs: ["[SYSTÈME] En attente de logs du worker..."]
      });
    }

    // Lire le fichier
    const fileContent = fs.readFileSync(LOG_FILE, 'utf-8');

    if (!fileContent || fileContent.trim() === '') {
      console.warn('⚠️  [LOGS API] Fichier de logs vide');
      return NextResponse.json({
        logs: ["[SYSTÈME] En attente de logs du worker..."]
      });
    }

    // Diviser en lignes et prendre les 50 dernières lignes non vides
    const lines = fileContent.split('\n').filter(line => line.trim() !== '');
    const lastLines = lines.slice(-50);

    console.log(`✅ [LOGS API] ${lastLines.length} lignes de logs retournées`);

    return NextResponse.json({ logs: lastLines });

  } catch (error) {
    console.error('❌ [LOGS API] Erreur lors de la lecture des logs:', error);

    return NextResponse.json({
      logs: [
        `[ERROR] Erreur: ${error instanceof Error ? error.message : 'Unknown error'}`,
        "[SYSTÈME] Vérifiez que le volume ./logs est bien monté"
      ]
    });
  }
}
