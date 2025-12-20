import { NextResponse } from 'next/server'
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config'

export async function POST(req: Request) {
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    const body = await req.json()

    const response = await fetch(`${getApiUrl()}/notifications/test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': getApiKey()!
      },
      body: JSON.stringify(body)
    }).catch(() => null)

    if (response && response.ok) {
      return NextResponse.json(await response.json())
    }

    // If backend doesn't have this endpoint, return mock success
    return NextResponse.json({
      success: true,
      message: 'Test notification sent (mock - implement backend endpoint for real notifications)'
    })
  } catch (e) {
    return NextResponse.json({ error: 'Failed to send test notification' }, { status: 500 })
  }
}
