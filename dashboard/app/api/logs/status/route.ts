import { NextResponse } from 'next/server';
import * as fs from 'fs';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const LOG_FILE = '/app/logs/linkedin_bot.log';

    // Vérifier si le fichier existe
    const exists = fs.existsSync(LOG_FILE);

    if (!exists) {
      return NextResponse.json({
        connected: false,
        message: "Volume logs non accessible"
      });
    }

    // Vérifier si le fichier est lisible
    try {
      fs.accessSync(LOG_FILE, fs.constants.R_OK);

      return NextResponse.json({
        connected: true,
        message: "Système de logs connecté",
        path: LOG_FILE
      });
    } catch {
      return NextResponse.json({
        connected: false,
        message: "Fichier logs non lisible (permissions)"
      });
    }

  } catch (error) {
    return NextResponse.json({
      connected: false,
      message: `Erreur: ${error instanceof Error ? error.message : 'Unknown'}`
    });
  }
}
