export default function Home() {
  return (
    <div suppressHydrationWarning>
      <div className="container">
        <div className="header">
          <div className="title">음성 주문</div>
          <div className="step-dots">
            <span className="step-dot active" id="dot0" />
            <span className="step-dot" id="dot1" />
            <span className="step-dot" id="dot2" />
            <span className="step-dot" id="dot3" />
          </div>
        </div>

        <div id="stage" />

        <div className="card" style={{ marginTop: '12px' }}>
          <div id="assistTitle" style={{ fontWeight: 700, marginBottom: '6px' }}>안내</div>
          <div id="assistText" className="muted">버튼 또는 음성으로 진행하세요.</div>
        </div>
      </div>

      <div className="footer">
        <div className="inner">
          <input id="speechHint" placeholder="여기에 말할 안내가 표시돼요" />
          <button id="primaryAction" className="btn btn-dark">다음</button>
          <button id="voiceToggle" className="btn btn-primary">🎤 말하기</button>
        </div>
      </div>

      <div id="done" className="done">
        <div className="panel hero grad-green">
          <div className="check">✔</div>
          <h2 style={{ textAlign: 'center', fontSize: '28px', margin: '0 0 10px' }}>주문 완료!</h2>
          <div className="card" style={{ background: 'rgba(255,255,255,.35)', border: 'none' }}>
            <div className="muted" style={{ textAlign: 'center' }}>주문번호</div>
            <div id="doneNum" className="order-num">000</div>
          </div>
          <p style={{ textAlign: 'center', margin: '16px 0 6px', color: '#0b0f19' }}>맛있는 음식을 준비하고 있어요</p>
          <p style={{ textAlign: 'center', color: '#0b0f19', opacity: .8 }}>잠시만 기다려주세요! 😊</p>
          <div className="glass" style={{ marginTop: '14px', textAlign: 'center' }}>
            <div className="muted" style={{ opacity: .9 }}>예상 준비 시간</div>
            <div style={{ fontSize: '24px', fontWeight: 800, marginTop: '6px' }}>15–20분</div>
          </div>
        </div>
      </div>
    </div>
  );
}
