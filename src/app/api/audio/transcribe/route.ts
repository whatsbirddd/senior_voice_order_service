import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

export async function GET() {
  const key = process.env.SPEECH_SUBSCRIPTION_KEY;
  const region = process.env.AZURE_SPEECH_REGION; // ex) "eastus"
  if (!key || !region) {
    return NextResponse.json({ error: 'Missing SPEECH_SUBSCRIPTION_KEY/AZURE_SPEECH_REGION' }, { status: 500 });
  }

  // ✅ 반드시 /sts/v1.0/issueToken 로 호출해야 함
  const r = await fetch(`https://${region}.api.cognitive.microsoft.com/sts/v1.0/issueToken`, {
    method: 'POST',
    headers: { 'Ocp-Apim-Subscription-Key': key },
    cache: 'no-store',
  });

  if (!r.ok) {
    const t = await r.text().catch(() => '');
    return NextResponse.json({ error: `Token issue failed: ${r.status} ${t}` }, { status: 500 });
  }

  const token = await r.text();
  // 토큰 유효시간은 보통 10분
  return NextResponse.json({ token, region, expiresInSec: 600 });
}