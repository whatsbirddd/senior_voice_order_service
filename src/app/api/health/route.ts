import { BACKEND_BASE } from '@/lib/backend'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_BASE}/health`, { cache: 'no-store' })
    const text = await res.text()
    return new Response(text, { status: res.status, headers: { 'content-type': res.headers.get('content-type') || 'application/json' } })
  } catch (e: any) {
    return new Response(JSON.stringify({ error: e?.message || 'unreachable' }), { status: 502, headers: { 'content-type': 'application/json' } })
  }
}

