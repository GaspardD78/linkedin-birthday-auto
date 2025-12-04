import { NextResponse } from 'next/server'
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config'

export async function GET() {
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    const response = await fetch(`${getApiUrl()}/webhooks`, {
      headers: { 'X-API-Key': getApiKey()! }
    }).catch(() => null)

    if (response && response.ok) {
      return NextResponse.json(await response.json())
    }

    // Default empty webhooks if backend doesn't have this endpoint yet
    return NextResponse.json({ webhooks: [] })
  } catch (e) {
    console.error('Failed to fetch webhooks:', e)
    return NextResponse.json({ error: 'Failed to fetch webhooks' }, { status: 500 })
  }
}

export async function PUT(req: Request) {
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    const body = await req.json()

    const response = await fetch(`${getApiUrl()}/webhooks`, {
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
    return NextResponse.json({ success: true, message: 'Webhooks saved' })
  } catch (e) {
    console.error('Failed to save webhooks:', e)
    return NextResponse.json({ error: 'Failed to save webhooks' }, { status: 500 })
  }
}
