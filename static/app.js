// Simple voice-first flow using Web Speech API (STT) and SpeechSynthesis (TTS)

const qs = (sel) => document.querySelector(sel);
const qsa = (sel) => Array.from(document.querySelectorAll(sel));

const state = {
  store: "옥소반 마곡본점",
  selectedItems: [],
  history: JSON.parse(localStorage.getItem("history") || "[]"),
  recognizing: false,
  recognition: null,
  sessionId: localStorage.getItem('sessionId') || (() => { const id = 'sess_' + Date.now(); localStorage.setItem('sessionId', id); return id; })(),
  step: 0, // 0: welcome, 1: recommend, 2: quantity, 3: confirm, 4: done
  menu: [],
  featured: null,
  currentIdx: 0,
  qty: 1,
  lastHeard: '',
};

function speak(text) {
  try {
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "ko-KR";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  } catch (e) {
    console.warn("TTS not available", e);
  }
}

function initSTT() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Web Speech API not supported");
    return null;
  }
  const rec = new SpeechRecognition();
  rec.lang = "ko-KR";
  rec.interimResults = true;
  rec.continuous = true;
  rec.onstart = () => {
    state.recognizing = true;
    speak("말씀해 주세요. 중지하려면 멈춰 라고 말해 주세요.");
    const vt = qs('#voiceToggle'); if (vt) vt.textContent = '■ 중지';
  };
  rec.onerror = (e) => {
    console.warn("STT error", e);
  };
  rec.onend = () => {
    state.recognizing = false;
    const vt = qs('#voiceToggle'); if (vt) vt.textContent = '🎤 말하기';
  };
  rec.onresult = (event) => {
    let finalTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      const transcript = event.results[i][0].transcript.trim();
      if (event.results[i].isFinal) {
        finalTranscript += transcript + " ";
      }
    }
    if (finalTranscript) {
      state.lastHeard = finalTranscript.trim();
      render();
      callAgent(finalTranscript);
      // simple intent shortcuts
      const t = finalTranscript.replace(/\s+/g,'');
      if (t.includes('멈춰')||t.includes('중지')||t.includes('스탑')) { state.recognition?.stop(); return; }
      if (t.includes('다음')) { nextStep(); return; }
      if (t.includes('이걸로')||t.includes('선택')) { selectCurrent(); return; }
    }
  };
  return rec;
}

async function callAgent(message) {
  // Prepare selected item names to inform agent
  const menuListEls = qsa('#menuResult .menu li');
  const selectedNames = state.selectedItems.map(idx => {
    const li = menuListEls[idx];
    return li ? li.querySelector('.name').textContent : null;
  }).filter(Boolean);

  const payload = {
    message,
    store: state.store || (qs('#storeInput').value || '').trim(),
    history: state.history,
    selectedNames,
    sessionId: state.sessionId,
  };
  const res = await fetch('/api/agent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();

  // Apply state updates
  if (data.state?.store) {
    state.store = data.state.store;
    qs('#storeInput').value = state.store;
  }

  // Render UI from agent output
  if (data.ui?.summary || data.ui?.reviews) {
    const reviews = data.ui.reviews || [];
    const summary = data.ui.summary || '';
    qs('#reviewsResult').innerHTML = `
      <div class="summary">${summary}</div>
      <ul>${reviews.map(r => `<li>${r}</li>`).join('')}</ul>
    `;
  }
  if (data.ui?.menu) {
    const menu = data.ui.menu;
    state.selectedItems = [];
    qs('#menuResult').innerHTML = `
      <ul class="menu">
        ${menu.map((m, idx) => `
          <li>
            <label>
              <input type="checkbox" data-idx="${idx}" />
              <span class="name">${m.name}</span>
              <span class="price">${m.price.toLocaleString()}원</span>
            </label>
            <div class="desc">${m.desc}</div>
          </li>
        `).join('')}
      </ul>
    `;
    qsa('#menuResult input[type="checkbox"]').forEach((el) => {
      el.addEventListener('change', () => {
        const idx = parseInt(el.dataset.idx, 10);
        if (el.checked) state.selectedItems.push(idx);
        else state.selectedItems = state.selectedItems.filter(i => i !== idx);
      });
    });
  }
  if (data.ui?.recommendations) {
    qs('#recommendResult').innerHTML = `추천: ${data.ui.recommendations.map(s => `<span class="pill">${s}</span>`).join(' ')}`;
  }
  if (data.ui?.mapUrl) {
    qs('#mapNote').textContent = '네이버 지도를 새 창에서 열었습니다.';
    window.open(data.ui.mapUrl, '_blank');
  }
  if (data.ui?.payment) {
    const pay = data.ui.payment;
    qs('#payResult').textContent = `모의 결제 성공 • ${pay.amount.toLocaleString()}원`;
    // Update simple history with the first purchased item
    const likedMenu = pay.items?.[0]?.name;
    if (likedMenu) {
      state.history.push({ time: Date.now(), store: state.store, likedMenu });
      localStorage.setItem('history', JSON.stringify(state.history));
    }
    // show done overlay
    showDone(Math.floor(100+Math.random()*900));
  }

  if (data.reply) speak(data.reply);
}

// ---------------- UI (screens) ----------------
function setDots(active){ ['dot0','dot1','dot2','dot3'].forEach((id,i)=>{ const el=qs('#'+id); if(!el) return; el.classList.toggle('active', i===active); });}

function render(){
  setDots(Math.min(state.step,3));
  const s = qs('#stage');
  if(!s) return;
  if(state.step===0){
    s.innerHTML = `
    <section class="hero grad-yellow">
      <div class="hero-body">
        <h2 style="text-align:center; font-size:28px; margin:4px 0 12px;">어서오세요!</h2>
        <img id="heroImg0" class="hero-img" alt="welcome" src="https://images.unsplash.com/photo-1701009203098-3bab61afe474?q=80&w=1080&auto=format&fit=crop"/>
        <p class="glass hint" style="margin-top:12px; text-align:center;">'주문할게요'라고 말씀해 주세요</p>
      </div>
    </section>`;
    qs('#assistTitle').textContent = '환영합니다';
    qs('#assistText').textContent = (state.lastHeard ? `방금 말씀: “${state.lastHeard}”\n` : '') + '음성 버튼을 누르거나 아래 주문하기 버튼을 눌러 진행하세요.';
  } else if(state.step===1){
    const item = state.menu[state.currentIdx] || state.featured || {name:'메뉴', price:0};
    s.innerHTML = `
    <section class="hero grad-pink">
      <div class="hero-body">
        <h2 style="text-align:center; font-size:24px; margin:0 0 12px;">메뉴 추천</h2>
        ${item.image ? `<img class="hero-img" src="${item.image}" alt="${item.name}"/>` : `<div class="hero-img"></div>`}
        <div class="hero-title" style="text-align:center;">${item.name}</div>
        <div class="hero-sub" style="text-align:center;">${item.description||''}</div>
        <div style="text-align:center; font-size:20px; font-weight:800; margin-top:6px; color:#0b0f19;">${(item.price||0).toLocaleString()}원</div>
        <div class="qty-wrap" style="margin-top:12px; gap:12px; justify-content:space-between;">
          <button class="icon-btn" id="prev">‹</button>
          <button class="btn btn-dark" id="choose">이 메뉴로 선택</button>
          <button class="icon-btn" id="next">›</button>
        </div>
      </div>
    </section>`;
    qs('#assistTitle').textContent = '추천 안내';
    qs('#assistText').textContent = (state.lastHeard ? `방금 말씀: “${state.lastHeard}”\n` : '') + "오늘의 추천이에요. '이걸로 할게요' 또는 '다음'이라고 말해보세요.";
    qs('#prev').onclick = () => { state.currentIdx = (state.currentIdx-1+state.menu.length)%state.menu.length; render(); };
    qs('#next').onclick = () => { state.currentIdx = (state.currentIdx+1)%state.menu.length; render(); };
    qs('#choose').onclick = selectCurrent;
  } else if(state.step===2){
    const item = currentItem();
    s.innerHTML = `
    <section class="hero grad-blue">
      <div class="hero-body">
        <h2 style="text-align:center; font-size:24px; margin:0 0 12px;">수량 선택</h2>
        ${item.image ? `<img class="hero-img" src="${item.image}" alt="${item.name}"/>` : `<div class="hero-img"></div>`}
        <div class="hero-title" style="text-align:center;">${item.name}</div>
        <div class="hero-sub" style="text-align:center;">${item.description||''}</div>
        <div style="text-align:center; font-size:20px; font-weight:800; margin-top:6px; color:#0b0f19;">${(item.price||0).toLocaleString()}원</div>
        <div class="qty-wrap" style="margin-top:12px;">
          <button class="icon-btn" id="minus">−</button>
          <div class="qty" id="qty">${state.qty}</div>
          <button class="icon-btn" id="plus">＋</button>
        </div>
        <div style="text-align:center; margin-top:12px;"><button class="btn btn-dark" id="toConfirm">수량 확인</button></div>
      </div>
    </section>`;
    qs('#assistTitle').textContent = '얼마나 드릴까요?';
    qs('#assistText').textContent = (state.lastHeard ? `방금 말씀: “${state.lastHeard}”\n` : '') + "'두 개', '세 개' 처럼 말씀해도 돼요.";
    qs('#minus').onclick = () => { state.qty = Math.max(1, state.qty-1); qs('#qty').textContent = state.qty; };
    qs('#plus').onclick = () => { state.qty += 1; qs('#qty').textContent = state.qty; };
    qs('#toConfirm').onclick = () => { state.step=3; render(); };
  } else if(state.step===3){
    const item = currentItem();
    const total = (item.price||0)*state.qty;
    s.innerHTML = `
    <section class="hero grad-green">
      <div class="hero-body">
        ${item.image ? `<img class="hero-img" src="${item.image}" alt="${item.name}"/>` : `<div class="hero-img"></div>`}
        <div class="hero-title" style="text-align:center;">${item.name}</div>
        <div class="hero-sub" style="text-align:center;">${item.description||''}</div>
        <div style="text-align:center; font-size:20px; font-weight:800; margin-top:6px; color:#0b0f19;">${(item.price||0).toLocaleString()}원</div>
        <div class="card" style="background:rgba(255,255,255,.35); border:none; margin-top:12px;">
          <div class="muted" style="text-align:center;">총 결제 금액</div>
          <div style="text-align:center; font-size:32px; font-weight:800; color:#0b0f19;">${total.toLocaleString()}원</div>
        </div>
        <div style="text-align:center; margin-top:12px; display:flex; gap:8px; justify-content:center;">
          <button class="btn btn-dark" id="backQty">다시 선택</button>
          <button class="btn btn-primary" id="orderBtn">주문하기</button>
        </div>
      </div>
    </section>`;
    qs('#assistTitle').textContent = `${item.name} ${state.qty}개 맞나요?`;
    qs('#assistText').textContent = (state.lastHeard ? `방금 말씀: “${state.lastHeard}”\n` : '') + "'네, 주문할게요' 혹은 '다시 선택할게요'라고 말해보세요.";
    qs('#backQty').onclick = () => { state.step=2; render(); };
    qs('#orderBtn').onclick = doOrder;
  }
}

function currentItem(){ return state.menu[state.currentIdx] || state.featured || {name:'메뉴',price:0}; }
function nextStep(){ state.step = Math.min(3, state.step+1); render(); }
function selectCurrent(){ state.step=2; render(); }
async function doOrder(){
  const item = currentItem();
  const payload = { store: state.store, items: [{ name: item.name, price: item.price }] };
  await fetch('/api/pay',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  showDone(Math.floor(100+Math.random()*900));
}
function showDone(num){
  const d=qs('#done'); qs('#doneNum').textContent = String(num).padStart(3,'0'); d.classList.add('done-show');
  setTimeout(()=> d.classList.remove('done-show'), 6000);
}

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

async function fetchReviews() {
  const store = (qs('#storeInput').value || state.store || '').trim();
  if (!store) {
    speak('가게 이름을 알려주세요.');
    return;
  }
  state.store = store;
  const data = await fetchJSON(`/api/reviews?store=${encodeURIComponent(store)}`);
  qs('#reviewsResult').innerHTML = `
    <div class="summary">${data.summary}</div>
    <ul>${data.reviews.map(r => `<li>${r}</li>`).join('')}</ul>
  `;
  speak(data.summary);
}

async function loadMenu() {
  const store = (qs('#storeInput').value || state.store || '').trim();
  if (!store) { speak('가게 이름이 필요해요.'); return; }
  state.store = store;
  const data = await fetchJSON(`/api/menu?store=${encodeURIComponent(store)}`);
  state.selectedItems = [];
  qs('#menuResult').innerHTML = `
    <ul class="menu">
      ${data.menu.map((m, idx) => `
        <li>
          <label>
            <input type="checkbox" data-idx="${idx}" />
            <span class="name">${m.name}</span>
            <span class="price">${m.price.toLocaleString()}원</span>
          </label>
          <div class="desc">${m.desc}</div>
        </li>
      `).join('')}
    </ul>
  `;
  speak(`${store}의 메뉴를 불러왔어요.`);

  // Wire checkbox selection
  qsa('#menuResult input[type="checkbox"]').forEach((el) => {
    el.addEventListener('change', () => {
      const idx = parseInt(el.dataset.idx, 10);
      if (el.checked) {
        state.selectedItems.push(idx);
      } else {
        state.selectedItems = state.selectedItems.filter(i => i !== idx);
      }
    });
  });
}

async function loadRecommendations() {
  const store = (qs('#storeInput').value || state.store || '').trim();
  if (!store) { speak('가게 이름이 필요해요.'); return; }
  state.store = store;
  const data = await fetchJSON('/api/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ store, history: state.history }),
  });
  qs('#recommendResult').innerHTML = `추천: ${data.suggested.map(s => `<span class="pill">${s}</span>`).join(' ')}`;
  speak(`${data.suggested.join(', ')} 메뉴를 추천해요.`);
}

async function openMap() {
  const store = (qs('#storeInput').value || state.store || '').trim();
  if (!store) { speak('가게 이름이 필요해요.'); return; }
  const data = await fetchJSON(`/api/place?store=${encodeURIComponent(store)}`);
  qs('#mapNote').textContent = data.note;
  window.open(data.mapUrl, '_blank');
  speak('네이버 지도를 새 창에서 열었습니다.');
}

async function pay() {
  const store = (qs('#storeInput').value || state.store || '').trim();
  if (!store) { speak('가게 이름이 필요해요.'); return; }
  // Derive items from selected checkboxes
  const menuListEls = qsa('#menuResult .menu li');
  const items = state.selectedItems.map((idx) => {
    const li = menuListEls[idx];
    const name = li.querySelector('.name').textContent;
    const priceText = li.querySelector('.price').textContent.replace(/[,원]/g, '');
    const price = parseInt(priceText, 10) || 0;
    return { name, price };
  });

  const data = await fetchJSON('/api/pay', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ store, items }),
  });
  qs('#payResult').textContent = `${data.message} • ${data.amount.toLocaleString()}원`;
  speak(`결제가 완료되었습니다. 총 ${data.amount}원.`);

  // Save to simple history
  if (items.length) {
    const likedMenu = items[0]?.name;
    state.history.push({ time: Date.now(), store, likedMenu });
    localStorage.setItem('history', JSON.stringify(state.history));
  }
}

function wireUI() {
  // Attach voice toggle
  state.recognition = initSTT();
  const v = qs('#voiceToggle');
  v?.addEventListener('click', () => {
    if (!state.recognition) return;
    if (state.recognizing) state.recognition.stop();
    else state.recognition.start();
  });

  // Primary action button (changes by step)
  const p = qs('#primaryAction');
  function setPrimary(label, handler){ if(!p) return; p.textContent = label; p.onclick = handler; }

  // Adjust primary action per step on every render
  const oldRender = render;
  render = function patchedRender(){
    oldRender();
    if (!p) return;
    if (state.step===0) setPrimary('주문하기', () => { state.step=1; render(); });
    else if (state.step===1) setPrimary('이 메뉴로 선택', selectCurrent);
    else if (state.step===2) setPrimary('수량 확인', () => { state.step=3; render(); });
    else if (state.step===3) setPrimary('주문하기', doOrder);
  }

  // Load menu for store
  (async () => {
    try{
      const data = await fetchJSON(`/api/menu?store=${encodeURIComponent(state.store)}`);
      state.menu = data.menu || [];
      state.featured = data.featured || null;
    } catch{}
    state.step = 0; state.qty = 1; state.currentIdx = 0; render();
  })();
}

document.addEventListener('DOMContentLoaded', wireUI);
