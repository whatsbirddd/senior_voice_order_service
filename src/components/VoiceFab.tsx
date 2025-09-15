"use client";
import { useRef, useState } from 'react';

export default function VoiceFab() {
  const [listening, setListening] = useState(false);
  const recRef = useRef<any>(null);

  const toggle = () => {
    const SpeechRecognition: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('이 브라우저는 음성 인식을 지원하지 않아요.');
      return;
    }
    if (!listening) {
      const rec = new SpeechRecognition();
      rec.lang = 'ko-KR'; rec.interimResults = true; rec.continuous = true;
      recRef.current = rec;
      rec.onresult = async (e: any) => {
        let finalText = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const t = e.results[i][0].transcript.trim();
          const n = t.replace(/\s+/g,'');
          if (n.includes('멈춰')||n.includes('중지')||n.includes('스탑')) {
            recRef.current?.stop(); setListening(false); return;
          }
          if (e.results[i].isFinal) finalText += t + ' ';
        }
        if (finalText) {
          try {
            await fetch('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'sess_'+Date.now(),message:finalText.trim(),store:'옥소반 마곡본점'})});
          } catch {}
        }
      };
      rec.onend = () => setListening(false);
      rec.start(); setListening(true);
    } else {
      recRef.current?.stop(); setListening(false);
    }
  };

  return (
    <button onClick={toggle} className={`btn ${listening? 'btn-danger':'btn-accent'}`}>{listening? '■ 중지':'🎤 말하기'}</button>
  );
}

