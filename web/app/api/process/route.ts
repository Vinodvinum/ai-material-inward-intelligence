import { NextRequest, NextResponse } from 'next/server'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'https://ai-material-inward-intelligence.onrender.com').replace(/\/$/, '')

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest) {
  try {
    const incoming = await request.formData()
    const upstream = new FormData()

    const image = incoming.get('image')
    const ocrText = incoming.get('ocr_text')
    const persist = incoming.get('persist')

    if (image instanceof File) upstream.append('image', image, image.name)
    if (typeof ocrText === 'string') upstream.append('ocr_text', ocrText)
    upstream.append('persist', typeof persist === 'string' ? persist : 'true')

    const response = await fetch(`${API_BASE}/inward/process`, {
      method: 'POST',
      body: upstream,
      cache: 'no-store',
      signal: AbortSignal.timeout(120000),
    })

    const text = await response.text()
    return new NextResponse(text, {
      status: response.status,
      headers: { 'content-type': response.headers.get('content-type') || 'application/json' },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unable to reach processing backend'
    return NextResponse.json(
      { detail: `Backend proxy error: ${message}` },
      { status: 502 },
    )
  }
}
