import React from 'react'
import VoiceFab from '@/components/VoiceFab'

async function getMenu() {
  try {
    const res = await fetch(`/api/menu?store=${encodeURIComponent('옥소반 마곡본점')}`, { cache: 'no-store' })
    if (!res.ok) return null
    return await res.json()
  } catch { return null }
}

export default async function Home() {
  const data = await getMenu()
  const menu = Array.isArray(data?.menu) ? data!.menu : []
  const featured = data?.featured

  return (
    <div className="min-h-dvh bg-white">
      <div className="mx-auto w-[430px] max-w-full">
        {/* Header */}
        <div className="px-4 pt-6 pb-2">
          <h1 className="text-3xl font-semibold tracking-tight text-gray-900">옥소반 마곡본점</h1>
          <p className="text-gray-600 mt-1">음성으로 주문하고, 추천을 받아보세요</p>
        </div>

        {/* Hero Featured */}
        <div className="px-4">
          <div className="rounded-3xl p-4 shadow-md bg-gradient-to-br from-yellow-300 to-pink-300">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-lg font-semibold text-gray-900">대표 메뉴</div>
                <span className="inline-block text-xs px-2 py-1 rounded-full bg-white/70 text-gray-800 mt-2">추천</span>
              </div>
              <VoiceFab />
            </div>
            <div className="mt-3 overflow-hidden rounded-2xl bg-white">
              {featured?.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={featured.image} alt={featured?.name||'featured'} className="w-full h-[220px] object-cover" />
              ) : (
                <div className="w-full h-[220px] bg-gray-100" />
              )}
              <div className="p-3">
                <div className="text-xl font-semibold text-gray-900">{featured?.name || '대표 메뉴'}</div>
                {typeof featured?.price === 'number' && <div className="text-gray-600 mt-1">{featured.price.toLocaleString()}원</div>}
              </div>
            </div>
          </div>
        </div>

        {/* Menu Grid */}
        <div className="px-4 mt-4">
          <div className="rounded-3xl border border-gray-200 bg-white shadow-sm p-4">
            <h3 className="text-xl font-semibold mb-3">메뉴</h3>
            <div className="grid grid-cols-2 gap-3">
              {menu.slice(0,8).map((m:any, idx:number)=> (
                <div className="border border-gray-200 rounded-2xl overflow-hidden bg-white" key={idx}>
                  {m.image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img className="w-full aspect-square object-cover" src={m.image} alt={m.name||'menu'} />
                  ) : (<div className="w-full aspect-square bg-gray-100" />)}
                  <div className="p-2">
                    <div className="font-semibold text-gray-900 truncate">{m.name}</div>
                    <div className="text-gray-600 mt-1">{(m.price||0).toLocaleString()}원</div>
                  </div>
                </div>
              ))}
              {menu.length===0 && (
                <div className="col-span-2 text-gray-500">메뉴가 아직 등록되지 않았어요. 관리자에서 업로드해 주세요.</div>
              )}
            </div>
          </div>
        </div>

        {/* Map Section */}
        <div className="px-4 mt-4 pb-24">
          <div className="rounded-3xl border border-gray-200 bg-white shadow-sm p-4">
            <h3 className="text-xl font-semibold mb-3">지도/위치</h3>
            <div className="flex items-center justify-between">
              <div className="text-gray-600">네이버 지도로 매장 위치 보기</div>
              <a href={"https://map.naver.com/v5/search/"+encodeURIComponent('옥소반 마곡본점')} target="_blank" className="btn btn-dark">지도로 열기</a>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white/95 backdrop-blur">
          <div className="mx-auto w-[430px] max-w-full px-4 py-3 flex items-center justify-between text-lg text-gray-600">
            <span className="font-medium text-gray-800">Figma 스타일 적용</span>
            <span>iPhone 16 레이아웃</span>
          </div>
        </div>
      </div>
    </div>
  )
}
