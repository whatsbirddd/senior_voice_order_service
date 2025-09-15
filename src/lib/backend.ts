export const BACKEND_BASE = process.env.BACKEND_BASE || process.env.NEXT_PUBLIC_BACKEND_BASE || 'http://localhost:5173';

export async function proxyJSON(path: string, init?: RequestInit) {
  const url = `${BACKEND_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    // Do not forward next internal headers
    cache: 'no-store',
  });
  const body = await res.text();
  const isJSON = (res.headers.get('content-type') || '').includes('application/json');
  return new Response(isJSON ? body : JSON.stringify({ raw: body }), {
    status: res.status,
    headers: { 'content-type': 'application/json' },
  });
}

