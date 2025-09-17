'use client';

import { chatWithAgent, generateSessionId, AgentResponse } from '../lib/agent';
import React, { useState, useEffect, useRef, useCallback } from 'react';
import styles from './VoiceOrderScreen.module.css';
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';


interface MenuItem {
  id: string;
  name: string;
  price: number;
  description: string;
  category: string;
}

interface OrderItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

interface VoiceOrderScreenProps {
  onOrderComplete: (orderNumber: string) => void;
}

const VoiceOrderScreen: React.FC<VoiceOrderScreenProps> = ({ onOrderComplete }) => {
  const [sessionId] = useState(() => generateSessionId());
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [selectedStore, setSelectedStore] = useState('옥소반 마곡본점');
  const [currentStep, setCurrentStep] = useState<'store' | 'menu' | 'order' | 'confirm'>('store');
  const [isProcessing, setIsProcessing] = useState(false);
  // const recognitionRef = useRef<any>(null);
  // const speechRef = useRef<SpeechSynthesisUtterance | null>(null);
  const [latestAgentMessage, setLatestAgentMessage] = useState('안녕하세요. 옥소반 마곡본점이에요. 메뉴 추천 도와드릴까요?');

  // ★ Agent 대화 상태(시니어 친화 안내)
  const [agentMessages, setAgentMessages] = useState<{ role: 'assistant' | 'user'; content: string }[]>([
    { role: 'assistant', content: '안녕하세요. 옥소반 마곡본점이에요. 메뉴 추천 도와드릴까요?' },
  ]);
  const [agentLoading, setAgentLoading] = useState(false);

  const storeImages: Record<string, string> = {
    '옥소반 마곡본점': 'https://images.unsplash.com/photo-1527169402691-feff5539e52c?auto=format&fit=crop&w=960&q=80',
  };

  const heroImage = storeImages[selectedStore] || 'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=960&q=80';
  const synthesizerRef = useRef<sdk.SpeechSynthesizer | null>(null);

  const ensureAzureTTS = async () => {
    // ensureAzure() 안에서 만든 speechConfig 재활용
    await ensureAzure();
    if (!synthesizerRef.current) {
      const audioOut = sdk.AudioConfig.fromDefaultSpeakerOutput();
      synthesizerRef.current = new sdk.SpeechSynthesizer(speechConfigRef.current!, audioOut);
      // 선택: 목소리 지정
      speechConfigRef.current!.speechSynthesisVoiceName = 'ko-KR-SunHiNeural';
    }
  };

  const speak = useCallback(async (text: string) => {
    if (!text) return;
    try {
      await ensureAzureTTS();
      await new Promise<void>((resolve, reject) => {
        synthesizerRef.current!.speakTextAsync(text, () => resolve(), (e) => reject(e));
      });
    } catch (e) { console.error('[Azure TTS error]', e); }
  }, []);
  // const speak = useCallback((text: string) => {
  //   if (typeof window === 'undefined' || !text) {
  //     return;
  //   }
  //   const synth = window.speechSynthesis;
  //   if (!synth) {
  //     return;
  //   }
  //   synth.cancel();
  //   const utterance = new SpeechSynthesisUtterance(text);
  //   utterance.lang = 'ko-KR';
  //   utterance.rate = 0.95;
  //   speechRef.current = utterance;
  //   synth.speak(utterance);
  // }, []);

  useEffect(() => {
    speak(latestAgentMessage);
  }, [latestAgentMessage, speak]);

  // useEffect(() => {
  //   return () => {
  //     if (typeof window !== 'undefined') {
  //       window.speechSynthesis?.cancel();
  //     }
  //   };
  // }, []);

  // Azure STT 객체
  const recognizerRef = useRef<sdk.SpeechRecognizer | null>(null);
  const speechConfigRef = useRef<sdk.SpeechConfig | null>(null);
  const tokenExpireAtRef = useRef(0);

  // 토큰/객체 보장
  const ensureAzure = async () => {
    const now = Date.now();
    if (speechConfigRef.current && now < tokenExpireAtRef.current - 30_000) return;

    const r = await fetch('/api/audio/transcribe', { method: 'GET', cache: 'no-store' });
    const ct = r.headers.get('content-type') || '';
    const body = ct.includes('application/json') ? await r.json() : { errorText: await r.text() };


    if (!r.ok || !(body as any)?.token) {
      console.error('[token error]', r.status, body);
      throw new Error((body as any)?.error || (body as any)?.errorText || 'Azure token failed');
    }

    const { token, region, endpoint, expiresInSec } = body as any;

    let speechConfig: sdk.SpeechConfig;

    if (endpoint) {
      // endpoint 우선 사용 가능
      speechConfig = sdk.SpeechConfig.fromEndpoint(new URL(endpoint));
      // 브라우저에는 '키' 대신 '토큰'만 주입
      (speechConfig as any).authorizationToken = token;
    } else {
      speechConfig = sdk.SpeechConfig.fromAuthorizationToken(token, region);
    }

    speechConfig.speechRecognitionLanguage = 'ko-KR';
    speechConfig.speechSynthesisVoiceName = 'ko-KR-SeoHyeonNeural';

    speechConfigRef.current = speechConfig;
    tokenExpireAtRef.current = now + (expiresInSec ?? 600) * 1000;

    // 새 객체로 재생성
    recognizerRef.current?.close();
    recognizerRef.current = new sdk.SpeechRecognizer(
      speechConfig,
      sdk.AudioConfig.fromDefaultMicrophoneInput()
    );

    synthesizerRef.current?.close();
    synthesizerRef.current = new sdk.SpeechSynthesizer(
      speechConfig,
      sdk.AudioConfig.fromDefaultSpeakerOutput()
    );
  };


  // 시니어 친화적 메뉴 데이터
  const sampleMenuItems: MenuItem[] = [
    { id: '1', name: '불고기정식', price: 15000, description: '부드러운 불고기와 반찬', category: '정식' },
    { id: '2', name: '김치찌개', price: 12000, description: '얼큰한 김치찌개', category: '찌개' },
    { id: '3', name: '된장찌개', price: 11000, description: '구수한 된장찌개', category: '찌개' },
    { id: '4', name: '비빔밥', price: 13000, description: '영양만점 비빔밥', category: '밥' },
    { id: '5', name: '냉면', price: 14000, description: '시원한 냉면', category: '면' },
    { id: '6', name: '갈비탕', price: 18000, description: '진한 갈비탕', category: '탕' }
  ];

  useEffect(() => {
    setMenuItems(sampleMenuItems);
  }, []);



  // ---- Helper: find menu by name (normalized) ----
  const findMenuItemByName = useCallback((name?: string | null) => {
    if (!name) return null;
    const normalized = name.replace(/\s+/g, '').toLowerCase();
    return (menuItems.find(m => m.name.replace(/\s+/g, '').toLowerCase() === normalized) || null);
  }, [menuItems]);

  // Pending selection for quantity actions
  const pendingItemRef = useRef<MenuItem | null>(null);

  const ensureOrderItem = useCallback((menuItem: MenuItem, quantity: number) => {
    setOrderItems((prev) => {
      const existing = prev.find((i) => i.id === menuItem.id);
      if (existing) {
        return prev.map((i) => i.id === menuItem.id ? { ...i, quantity } : i);
      }
      return [...prev, { id: menuItem.id, name: menuItem.name, price: menuItem.price, quantity }];
    });
  }, []);

  const adjustPendingQuantity = useCallback((delta: number) => {
    const pending = pendingItemRef.current;
    if (!pending) return;
    setOrderItems((prev) => {
      const existing = prev.find((i) => i.id === pending.id);
      if (!existing) {
        if (delta > 0) {
          return [...prev, { id: pending.id, name: pending.name, price: pending.price, quantity: 1 }];
        }
        return prev;
      }
      const nextQty = Math.max(1, existing.quantity + delta);
      return prev.map((i) => i.id === existing.id ? { ...i, quantity: nextQty } : i);
    });
  }, []);

  // ---- Agent actions → UI state ----
  const handleAgentActions = useCallback((actions: any[] | undefined) => {
    if (!Array.isArray(actions)) return;
    actions.forEach((act) => {
      if (!act || typeof act !== 'object') return;
      switch (act.type) {
        case 'NAVIGATE': {
          const target = String(act.target || '').toLowerCase();
          if (target === 'home') setCurrentStep('store');
          else if (target) setCurrentStep('menu');
          break;
        }
        case 'SHOW_RECOMMENDATIONS': {
          const items = Array.isArray(act.items) ? act.items : [];
          const names = items.map((i: any) => i?.name).filter(Boolean) as string[];
          if (names.length) {
            const priority = new Set(names.map((n) => n.replace(/\s+/g, '').toLowerCase()));
            const sorted = [...menuItems].sort((a, b) => {
              const A = priority.has(a.name.replace(/\s+/g, '').toLowerCase()) ? 0 : 1;
              const B = priority.has(b.name.replace(/\s+/g, '').toLowerCase()) ? 0 : 1;
              return A - B;
            });
            setMenuItems(sorted);
            setCurrentStep('menu');
          }
          break;
        }
        case 'SELECT_MENU_BY_NAME': {
          const name = act.name || act.menu_name;
          const item = findMenuItemByName(name);
          if (item) pendingItemRef.current = item;
          break;
        }
        case 'SET_QTY': {
          const qty = Number(act.value ?? act.qty ?? act.quantity);
          const item = pendingItemRef.current;
          if (item && Number.isFinite(qty) && qty > 0) ensureOrderItem(item, qty);
          break;
        }
        case 'INCREMENT_QTY': {
          adjustPendingQuantity(1);
          break;
        }
        case 'DECREMENT_QTY': {
          adjustPendingQuantity(-1);
          break;
        }
        case 'ADD_TO_CART': {
          const item = pendingItemRef.current;
          if (item) ensureOrderItem(item, 1);
          break;
        }
        case 'REMOVE_FROM_CART': {
          const id = String(act.menu_id || act.id || '');
          if (!id) break;
          setOrderItems((prev) => prev.filter((i) => i.id !== id));
          break;
        }
        case 'READ_BACK_SUMMARY': {
          const total = getTotalAmount();
          const summary = orderItems.length
            ? `현재 장바구니는 ${orderItems.map(i => `${i.name} ${i.quantity}개`).join(', ')}. 총 금액은 ${total.toLocaleString()}원입니다.`
            : '장바구니가 비어 있어요.';
          setLatestAgentMessage(summary);
          break;
        }
        case 'ORDER': {
          handleOrderComplete();
          break;
        }
        default:
          break;
      }
    });
  }, [adjustPendingQuantity, ensureOrderItem, findMenuItemByName, getTotalAmount, menuItems, orderItems.length]);


  // ★ Agent 호출(내부적으로 chatWithAgent 사용)
  const askAgent = async (prompt: string) => {
    try {
      setAgentLoading(true);
      setAgentMessages((m) => [...m, { role: 'user', content: prompt }]);
      const res: AgentResponse | any = await chatWithAgent({
        sessionId,
        store: selectedStore,
        message: prompt,
      });
      const reply = (res && (res.speak || res.reply || res.message || res.text)) ?? '안내를 불러오지 못했어요. 잠시 뒤 다시 시도해주세요.';
      setAgentMessages((m) => [...m, { role: 'assistant', content: reply }]);
      setLatestAgentMessage(reply);
      // Apply agent UI actions if present
      try { handleAgentActions((res as any)?.actions); } catch { }
    } catch {
      setAgentMessages((m) => [...m, { role: 'assistant', content: '지금은 안내가 어려워요. 잠시 뒤 다시 시도해주세요.' }]);
      setLatestAgentMessage('지금은 안내가 어려워요. 잠시 뒤 다시 시도해주세요.');
    } finally {
      setAgentLoading(false);
    }
  };

  // ---- STT start/stop and processing ----
  const startListening = async () => {
    try {
      await ensureAzure();
      setTranscript('');
      setIsListening(true);

      const rec = recognizerRef.current!;
      rec.recognizing = (_s, e) => {
        // 중간결과 보고 싶으면 사용
        setTranscript(e.result.text);
      };
      rec.recognized = (_s, e) => {
        if (e.result.reason === sdk.ResultReason.RecognizedSpeech) {
          const text = e.result.text?.trim();
          if (text) {
            setTranscript(text);
            processVoiceCommand(text);  // 기존 로직 재사용
          }
        }
      };
      rec.canceled = (_s, e) => {
        console.warn('[Azure STT canceled]', e.errorDetails);
        setIsListening(false);
      };
      rec.sessionStopped = () => setIsListening(false);

      rec.startContinuousRecognitionAsync();
    } catch (err) {
      console.error('[Azure STT start error]', err);
      setIsListening(false);
    }
  };

  const stopListening = () => {
    const rec = recognizerRef.current;
    if (!rec) return;
    rec.stopContinuousRecognitionAsync(
      () => setIsListening(false),
      (err) => { console.error('[Azure STT stop error]', err); setIsListening(false); }
    );
  };


  // ★ 음성 명령: store(소개) 단계와 menu(주문) 단계 모두 처리
  const processVoiceCommand = (command: string) => {
    setIsProcessing(true);
    const lower = command.toLowerCase().trim();

    // 소개 화면에서의 명령
    if (currentStep === 'store') {
      {
        askAgent(`요청: ${command}`);
      }
    }

    // 메뉴 선택 화면에서의 명령(기존 로직 유지)
    if (currentStep === 'menu') {
      menuItems.forEach(item => {
        if (lower.includes(item.name.toLowerCase())) {
          addToOrder(item);
        }
      });
      if (/주문(하기)?|결제/.test(lower) && orderItems.length > 0) {
        handleOrderComplete();
      }
      if (/뒤로|매장/.test(lower)) {
        setCurrentStep('store');
      }
    }

    // 보조적으로, 에이전트가 앱 액션을 주도하도록 사용자 발화를 항상 전달
    try { askAgent(command); } catch { }

    setTimeout(() => setIsProcessing(false), 600);
  };

  const addToOrder = (menuItem: MenuItem) => {
    setOrderItems(prev => {
      const existingItem = prev.find(item => item.id === menuItem.id);
      if (existingItem) {
        return prev.map(item =>
          item.id === menuItem.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      } else {
        return [...prev, {
          id: menuItem.id,
          name: menuItem.name,
          price: menuItem.price,
          quantity: 1
        }];
      }
    });
  };

  const removeFromOrder = (itemId: string) => {
    setOrderItems(prev => {
      const existingItem = prev.find(item => item.id === itemId);
      if (existingItem && existingItem.quantity > 1) {
        return prev.map(item =>
          item.id === itemId
            ? { ...item, quantity: item.quantity - 1 }
            : item
        );
      } else {
        return prev.filter(item => item.id !== itemId);
      }
    });
  };

  function getTotalAmount() {
    return orderItems.reduce((total, item) => total + (item.price * item.quantity), 0);
  }

  const handleOrderComplete = () => {
    if (orderItems.length > 0) {
      const orderNumber = `ORDER-${Date.now()}`; onOrderComplete(orderNumber);
    }
  };

  // ★ 새 소개 화면 렌더러(훅 사용 없음)
  const renderStoreIntro = () => {
    return (
      <div className={styles.heroWrapper}>
        <div className={styles.heroHeader}>
          <h1 className={styles.heroGreeting}>어서오세요!</h1>
          <div className={styles.progressDots}>
            <span className={styles.progressDotActive} />
            <span className={styles.progressDot} />
            <span className={styles.progressDot} />
          </div>
        </div>

        <div className={styles.heroCard}>
          <img src={heroImage} alt={`${selectedStore} 매장 사진`} className={styles.heroImage} />
        </div>

        <div className={styles.agentCard}>
          <p className={styles.agentMessage}>{latestAgentMessage}</p>
          <p className={styles.agentHint}>"주문할게요" 라고 말씀해 주세요.</p>
          <button
            className={styles.agentActionButton}
            onClick={() => askAgent('이 가게의 대표 메뉴와 추천 메뉴에 대해 자세히 설명해주세요')}
            disabled={agentLoading}
          >
            {agentLoading ? '안내 불러오는 중...' : '추천 메뉴 듣기'}
          </button>
        </div>

        <div className={styles.voiceCta}>
          <button
            onClick={isListening ? stopListening : startListening}
            className={styles.voiceCtaButton}
            disabled={agentLoading}
          >
            {isListening ? '듣고 있어요…' : '🎤 음성으로 말하기'}
          </button>
          {transcript && <p className={styles.transcript}>"{transcript}"</p>}
        </div>

        <button className={styles.secondaryLink} onClick={() => setCurrentStep('menu')}>
          메뉴 목록 보기
        </button>
      </div>
    );
  };

  const renderMenuSelection = () => (
    <div className={styles.animateFadeIn}>
      <div className={styles.sectionHeader}>
        <h1 className={styles.sectionTitle}>메뉴를 선택해주세요</h1>
        <p className={styles.sectionSubtitle}>{selectedStore}</p>
      </div>

      <div className={styles.menuList}>
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => addToOrder(item)}
            className={styles.menuItem}
          >
            <div>
              <h3 className={styles.menuHeading}>{item.name}</h3>
              <p className={styles.menuDescription}>{item.description}</p>
              <p className={styles.menuPrice}>{item.price.toLocaleString()}원</p>
            </div>
            <div className={styles.menuEmoji}>🍽️</div>
          </button>
        ))}
      </div>

      {orderItems.length > 0 && (
        <div className={styles.summaryCard}>
          <h3 className={styles.summaryTitle}>주문 내역</h3>
          {orderItems.map((item) => (
            <div key={item.id} className={styles.summaryItem}>
              <div className={styles.summaryInfo}>
                <span>{item.name}</span>
                <span>×{item.quantity}</span>
              </div>
              <div className={styles.summaryInfo}>
                <span className={styles.summaryPrice}>
                  {(item.price * item.quantity).toLocaleString()}원
                </span>
                <button
                  onClick={() => removeFromOrder(item.id)}
                  className={styles.removeButton}
                >
                  -
                </button>
              </div>
            </div>
          ))}
          <div className={styles.summaryDivider} />
          <div className={styles.summaryTotalRow}>
            <span className={styles.summaryTotalLabel}>총 금액</span>
            <span className={styles.summaryTotalValue}>
              {getTotalAmount().toLocaleString()}원
            </span>
          </div>
        </div>
      )}

      <div className={styles.voiceBlock}>
        <button
          onClick={isListening ? stopListening : startListening}
          className={[styles.voiceButton, isListening ? styles.recording : ''].filter(Boolean).join(' ')}
          disabled={isProcessing}
        >
          {isListening ? '🎤' : '🗣️'}
        </button>
        <p className={styles.voiceHint}>
          {isListening ? '주문을 듣고 있습니다...' : '음성으로 주문하기'}
        </p>
        {transcript && (
          <p className={styles.transcript}>
            "{transcript}"
          </p>
        )}
      </div>

      <div className={styles.actions}>
        {orderItems.length > 0 && (
          <button
            onClick={handleOrderComplete}
            className="btn btn-primary"
          >
            <span>주문하기</span>
            <span role="img" aria-hidden="true" className={styles.orderButtonIcon}>🛒</span>
          </button>
        )}

        <button
          onClick={() => setCurrentStep('store')}
          className="btn btn-dark"
        >
          매장 소개로 돌아가기
        </button>
      </div>
    </div>
  );

  if (currentStep === 'store') {
    return renderStoreIntro();
  }

  return (
    <div className={styles.voiceOrderScreen}>
      {renderMenuSelection()}
    </div>
  );
};
export default VoiceOrderScreen;
