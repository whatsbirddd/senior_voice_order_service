import { NextRequest } from 'next/server'
import { BACKEND_BASE } from '@/lib/backend'

export async function POST(req: NextRequest) {
  const formData = await req.formData()
  const res = await fetch(`${BACKEND_BASE}/api/audio/transcribe`, {
    method: 'POST',
    body: formData,
  })
  const text = await res.text()
  const contentType = res.headers.get('content-type') || 'application/json'
  return new Response(text, { status: res.status, headers: { 'content-type': contentType } })
}
