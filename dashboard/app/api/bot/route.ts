import { NextResponse } from 'next/server';
import { puppetMaster, BotTask } from '@/lib/puppet-master';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action } = body;

    if (action === 'START') {
      // Exemple: Lancer une tâche de vérification des messages
      const task: BotTask = {
        id: Date.now().toString(),
        type: 'CHECK_MESSAGES',
        payload: {},
        timestamp: Date.now()
      };

      // Note: Dans une vraie implémentation, on pousserait ça dans une queue Redis
      // Ici on lance direct pour la démo, mais attention à ne pas bloquer la réponse HTTP
      // Idéalement, puppetMaster consommerait la queue en arrière plan.

      // Pour l'instant, on simule juste le status update
      return NextResponse.json({ success: true, message: 'Bot start requested' });
    }

    if (action === 'STOP') {
      await puppetMaster.killSwitch();
      return NextResponse.json({ success: true, message: 'Bot stopped' });
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error) {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export async function GET() {
  const status = await puppetMaster.getStatus();
  return NextResponse.json(status || { state: 'IDLE' });
}
