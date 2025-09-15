import { NextRequest } from 'next/server'
import { BACKEND_BASE } from '@/lib/backend'

export async function GET(req: NextRequest) {
  const { search } = new URL(req.url)
  const url = `${BACKEND_BASE}/api/place${search}`
  const res = await fetch(url, { cache: 'no-store' })
  const data = await res.text()
  return new Response(data, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
}

