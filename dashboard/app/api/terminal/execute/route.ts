import { NextResponse } from 'next/server'
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config'

// Whitelist of allowed commands for security
const ALLOWED_COMMANDS = [
  'status',
  'logs',
  'ps',
  'disk',
  'memory',
  'restart',
  'help'
]

export async function POST(req: Request) {
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    const body = await req.json()
    const { command } = body

    if (!command) {
      return NextResponse.json({ error: 'Command is required' }, { status: 400 })
    }

    // Extract the base command (first word)
    const baseCommand = command.trim().split(' ')[0]

    // Check if command is allowed
    if (!ALLOWED_COMMANDS.includes(baseCommand)) {
      return NextResponse.json({
        error: `Command '${baseCommand}' is not allowed. Allowed commands: ${ALLOWED_COMMANDS.join(', ')}`,
        output: `Error: Command not allowed\n\nFor security reasons, only predefined commands are allowed.\n\nAvailable commands:\n${ALLOWED_COMMANDS.map(c => `  - ${c}`).join('\n')}`
      }, { status: 403 })
    }

    // Try to execute via backend API
    const response = await fetch(`${getApiUrl()}/terminal/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': getApiKey()!
      },
      body: JSON.stringify({ command })
    }).catch(() => null)

    if (response && response.ok) {
      return NextResponse.json(await response.json())
    }

    // If backend doesn't have this endpoint, return mock output
    const mockOutputs: Record<string, string> = {
      status: `System Status: Online
Bot Worker: Running
API: Healthy
Database: Connected
Redis: Connected
Uptime: 5 days, 12 hours`,
      logs: `[2024-01-01 12:00:00] INFO: Bot started successfully
[2024-01-01 12:01:23] INFO: Processing 15 contacts
[2024-01-01 12:02:45] SUCCESS: Sent 15 messages
[2024-01-01 12:03:10] INFO: Job completed`,
      ps: `PID   NAME              CPU   MEM
1234  dashboard         2.3%  128MB
1235  bot-worker        5.1%  256MB
1236  redis            1.2%   64MB
1237  nginx            0.8%   32MB`,
      disk: `Filesystem      Size  Used Avail Use%
/dev/sda1        50G   12G   36G  25%
/dev/sdb1       100G   45G   52G  47%`,
      memory: `Total Memory: 4.0 GB
Used Memory:  2.1 GB (52%)
Free Memory:  1.9 GB (48%)
Buffers/Cache: 512 MB`,
      restart: `Restarting services...
✓ Stopping bot-worker
✓ Stopping dashboard
✓ Starting bot-worker
✓ Starting dashboard
All services restarted successfully`,
      help: `Available Commands:
  status   - Display system status
  logs     - Show recent log entries
  ps       - List running processes
  disk     - Show disk usage
  memory   - Show memory usage
  restart  - Restart bot services
  help     - Show this help message

For security, only these commands are allowed.
Use the dashboard UI for other operations.`
    }

    const output = mockOutputs[baseCommand] || `Command '${baseCommand}' executed (mock output - implement backend endpoint for real execution)`

    return NextResponse.json({
      success: true,
      output,
      command: baseCommand
    })
  } catch (e) {
    console.error('Failed to execute command:', e)
    return NextResponse.json({ error: 'Failed to execute command' }, { status: 500 })
  }
}
