import { NextRequest } from 'next/server'
import { proxyJSON } from '@/lib/backend'

export async function POST(req: NextRequest) {
  const body = await req.text()
  return proxyJSON('/agent/chat', { method: 'POST', body })
}

