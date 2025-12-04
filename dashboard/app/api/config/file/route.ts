import { NextResponse } from 'next/server'
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config'

export async function GET() {
  // Validate API key is configured
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    const res = await fetch(`${getApiUrl()}/config/yaml`, {
      headers: { 'X-API-Key': getApiKey()! }
    })

    if (!res.ok) {
      const errorText = await res.text()
      return NextResponse.json({ error: errorText }, { status: res.status })
    }

    const data = await res.json()

    // Convert the JSON config back to YAML format for editing
    // The backend should return the raw YAML content
    return NextResponse.json({
      content: data.yaml_content || JSON.stringify(data, null, 2),
      last_modified: data.last_modified || new Date().toISOString()
    })
  } catch (e) {
    console.error('Failed to fetch config file:', e)
    return NextResponse.json({ error: 'Failed to fetch config file' }, { status: 500 })
  }
}

export async function PUT(req: Request) {
  // Validate API key is configured
  const validationError = validateApiKey()
  if (validationError) return validationError

  try {
    const body = await req.json()

    if (!body.content) {
      return NextResponse.json({ error: 'Content is required' }, { status: 400 })
    }

    // Send the raw YAML content to the backend
    const res = await fetch(`${getApiUrl()}/config/yaml`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': getApiKey()!
      },
      body: JSON.stringify({ yaml_content: body.content })
    })

    if (!res.ok) {
      const errorText = await res.text()
      return NextResponse.json({ error: errorText }, { status: res.status })
    }

    return NextResponse.json({
      success: true,
      message: 'Configuration saved successfully'
    })
  } catch (e) {
    console.error('Failed to save config file:', e)
    return NextResponse.json({ error: 'Failed to save config file' }, { status: 500 })
  }
}
