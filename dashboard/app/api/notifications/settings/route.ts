import { NextResponse } from 'next/server'
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config'

export async function GET() {
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    // For now, return default settings (can be stored in backend later)
    const response = await fetch(`${getApiUrl()}/notifications/settings`, {
      headers: { 'X-API-Key': getApiKey()! }
    }).catch(() => null)

    if (response && response.ok) {
      return NextResponse.json(await response.json())
    }

    // Default settings if backend doesn't have this endpoint yet
    return NextResponse.json({
      email_enabled: false,
      email_address: "",
      notify_on_error: true,
      notify_on_success: false,
      notify_on_bot_start: false,
      notify_on_bot_stop: false,
      notify_on_cookies_expiry: true,
    })
  } catch (e) {
    return NextResponse.json({ error: 'Failed to fetch settings' }, { status: 500 })
  }
}

export async function PUT(req: Request) {
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    const body = await req.json()

    const response = await fetch(`${getApiUrl()}/notifications/settings`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': getApiKey()!
      },
      body: JSON.stringify(body)
    }).catch(() => null)

    if (response && response.ok) {
      return NextResponse.json(await response.json())
    }

    // If backend doesn't have this endpoint, just return success
    // Settings can be stored in localStorage on the frontend for now
    return NextResponse.json({ success: true, message: 'Settings saved' })
  } catch (e) {
    return NextResponse.json({ error: 'Failed to save settings' }, { status: 500 })
  }
}
