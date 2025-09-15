import { NextRequest } from 'next/server'

export async function POST(req: NextRequest) {
  const { url } = await req.json()
  try {
    const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' } })
    const html = await res.text()
    return new Response(JSON.stringify({ html }), { status: 200, headers: { 'content-type': 'application/json' } })
  } catch (e: any) {
    return new Response(JSON.stringify({ error: e?.message || 'fetch failed' }), { status: 500, headers: { 'content-type': 'application/json' } })
  }
}

