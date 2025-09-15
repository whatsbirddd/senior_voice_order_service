"use client";
import { useState } from 'react';

type Item = { name: string; desc?: string; price?: number; image?: string };

export default function ImportPage() {
  const [store, setStore] = useState('한마음 식당');
  const [link, setLink] = useState('https://naver.me/5oE5C3Vw');
  const [items, setItems] = useState<Item[]>([{ name: '', desc: '', price: 0, image: '' }]);
  const [log, setLog] = useState('');

  const addRow = () => setItems([...items, { name: '', desc: '', price: 0, image: '' }]);
  const delRow = (i: number) => setItems(items.filter((_, idx) => idx !== i));
  const update = (i: number, key: keyof Item, val: any) => {
    const next = items.slice();
    (next[i] as any)[key] = key === 'price' ? Number(val||0) : val;
    setItems(next);
  };

  async function tryParse() {
    setLog('링크에서 정보를 가져오는 중...');
    try {
      // Best-effort: fetch HTML and attempt trivial extraction; if not possible, just guide manual entry
      const res = await fetch('/api/proxy', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: link }) });
      const data = await res.json();
      const html: string = data.html || '';
      const title = /<title>(.*?)<\/title>/i.exec(html)?.[1] || '';
      setLog(`가져오기 완료. title=${title || 'N/A'}. 필요 시 아래 표에 직접 입력하세요.`);
    } catch (e: any) {
      setLog('자동 가져오기 실패. 아래 표에 직접 입력해 주세요.');
    }
  }

  async function submit() {
    const filtered = items.filter(it => it.name && (it.price||0) >= 0);
    const payload = { store, menu: filtered };
    const res = await fetch('/api/menu/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const out = await res.json();
    setLog(`업로드 응답: ${res.status} ${JSON.stringify(out).slice(0,200)}`);
  }

  return (
    <div className="max-w-[720px] mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">메뉴/사진 임포트</h1>
      <p className="text-muted-foreground">네이버 링크 내용을 바탕으로 메뉴명/가격/이미지 URL을 입력해 업로드합니다.</p>

      <div className="grid gap-2">
        <label className="text-sm">가게 이름</label>
        <input className="border rounded-md px-3 py-2" value={store} onChange={e=>setStore(e.target.value)} placeholder="가게 이름" />
      </div>
      <div className="grid gap-2">
        <label className="text-sm">네이버 링크(선택)</label>
        <div className="flex gap-2">
          <input className="border rounded-md px-3 py-2 flex-1" value={link} onChange={e=>setLink(e.target.value)} placeholder="https://naver.me/..." />
          <button className="px-3 py-2 rounded-md bg-gray-800 text-white" onClick={tryParse}>가져오기 시도</button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className="p-2">이름</th>
              <th className="p-2">설명</th>
              <th className="p-2">가격</th>
              <th className="p-2">이미지 URL</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, i) => (
              <tr key={i}>
                <td className="p-2"><input className="border rounded-md px-2 py-1 w-full" value={it.name} onChange={e=>update(i,'name',e.target.value)} /></td>
                <td className="p-2"><input className="border rounded-md px-2 py-1 w-full" value={it.desc||''} onChange={e=>update(i,'desc',e.target.value)} /></td>
                <td className="p-2"><input className="border rounded-md px-2 py-1 w-28" type="number" value={it.price||0} onChange={e=>update(i,'price',e.target.value)} /></td>
                <td className="p-2"><input className="border rounded-md px-2 py-1 w-full" value={it.image||''} onChange={e=>update(i,'image',e.target.value)} /></td>
                <td className="p-2"><button className="px-2 py-1 text-red-600" onClick={()=>delRow(i)}>삭제</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2">
        <button className="px-3 py-2 rounded-md bg-gray-200" onClick={addRow}>행 추가</button>
        <button className="px-3 py-2 rounded-md bg-green-600 text-white" onClick={submit}>업로드</button>
      </div>

      {log && <pre className="bg-gray-100 p-3 rounded-md whitespace-pre-wrap text-xs">{log}</pre>}
    </div>
  );
}

