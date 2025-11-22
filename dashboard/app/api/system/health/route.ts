import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import os from 'os';

export const dynamic = 'force-dynamic'; // Pour ne pas cacher cette route

export async function GET() {
  try {
    let cpuTemp = 0;

    // Lecture de la température CPU sur Raspberry Pi
    try {
      const tempFile = await fs.readFile('/sys/class/thermal/thermal_zone0/temp', 'utf-8');
      cpuTemp = parseInt(tempFile) / 1000;
    } catch (e) {
      // Fallback pour dev local (non-RPi)
      cpuTemp = 45;
    }

    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const usedMem = totalMem - freeMem;

    // Conversion en GB
    const memoryUsageGB = usedMem / (1024 * 1024 * 1024);
    const totalMemoryGB = totalMem / (1024 * 1024 * 1024);

    return NextResponse.json({
      cpuTemp,
      memoryUsage: memoryUsageGB,
      totalMemory: totalMemoryGB,
      uptime: os.uptime()
    });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch system stats' }, { status: 500 });
  }
}
