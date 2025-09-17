'use client';

import { chatWithAgent, transcribeAudio, generateSessionId, AgentResponse } from '../lib/agent';
import React, { useState, useEffect, useRef } from 'react';
import styles from './VoiceOrderScreen.module.css';

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
  const recognitionRef = useRef<any>(null);

  // ★ Agent 대화 상태(시니어 친화 안내)
  const [agentMessages, setAgentMessages] = useState<{ role: 'assistant' | 'user'; content: string }[]>([
    { role: 'assistant', content: '안녕하세요. 옥소반 마곡본점이에요. 메뉴 추천 도와드릴까요?' },
  ]);
  const [agentLoading, setAgentLoading] = useState(false);

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

  // ★ Agent 호출(내부적으로 chatWithAgent 사용)
  // const askAgent = async (prompt: string) => {
  //   try {
  //     setAgentLoading(true);
  //     setAgentMessages((m) => [...m, { role: 'user', content: prompt }]);
  //     const res: AgentResponse | any = await chatWithAgent({
  //       sessionId,
  //       store: selectedStore,
  //       message: prompt,
  //     });
  //     const reply = (res && (res.reply || res.message || res.text)) ?? '안내를 불러오지 못했어요. 잠시 뒤 다시 시도해주세요.';
  //     setAgentMessages((m) => [...m, { role: 'assistant', content: reply }]);
  //   } catch {
  //     setAgentMessages((m) => [...m, { role: 'assistant', content: '지금은 안내가 어려워요. 잠시 뒤 다시 시도해주세요.' }]);
  //   } finally {
  //     setAgentLoading(false);
  //   }
  // };
  // ★ Agent 호출(내부적으로 chatWithAgent 사용)
  const askAgent = async (prompt: string) => {
    try {
      setAgentLoading(true);
      setAgentMessages((m) => [...m, { role: 'user', content: prompt }]);

      // ✅ message → prompt 로 변경
      const res: AgentResponse | any = await chatWithAgent({ store: selectedStore, prompt });

      // ✅ 다양한 응답 타입 대비 + 콘솔로그로 디버깅
      console.log('[chatWithAgent][res]:', res);
      const reply =
        (typeof res === 'string' && res) ||
        res?.reply ||
        res?.message ||   // 서버가 message로 줄 수도 있으니 fallback은 유지
        res?.text ||
        '안내를 불러오지 못했어요. 잠시 뒤 다시 시도해주세요.';

      setAgentMessages((m) => [...m, { role: 'assistant', content: reply }]);
    } catch (e) {
      console.error('[chatWithAgent][error]:', e); // ✅ 에러 내용을 확인
      setAgentMessages((m) => [
        ...m,
        { role: 'assistant', content: '지금은 안내가 어려워요. 잠시 뒤 다시 시도해주세요.' },
      ]);
    } finally {
      setAgentLoading(false);
    }
  };


  const startListening = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = 'ko-KR';

      recognitionRef.current.onstart = () => {
        setIsListening(true);
        setTranscript('');
      };

      recognitionRef.current.onresult = (event: any) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          setTranscript(finalTranscript);
          processVoiceCommand(finalTranscript);
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('음성 인식 오류:', event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current.start();
    } else {
      alert('이 브라우저는 음성 인식을 지원하지 않습니다.');
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
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

    setTimeout(() => setIsProcessing(false), 800);
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

  const getTotalAmount = () => {
    return orderItems.reduce((total, item) => total + (item.price * item.quantity), 0);
  };

  const handleOrderComplete = () => {
    if (orderItems.length > 0) {
      const orderNumber = `ORDER-${Date.now()}`; onOrderComplete(orderNumber);
    }
  };

  // ★ 새 소개 화면 렌더러(훅 사용 없음)
  // ★ 새 소개 화면 렌더러(훅 사용 없음)
  const renderStoreIntro = () => {
    return (
      <div className={styles.animateFadeIn}>
        <div className={styles.sectionHeader}>
          <h1 className={styles.sectionTitle}>옥소반 마곡본점</h1>
          <p className={styles.sectionSubtitle}>어서 오세요</p>
        </div>

        <div className={styles.infoCard}>
          <button
            className={styles.primaryButton}
            onClick={() => askAgent('이 가게의 대표 메뉴와 추천 메뉴에 대해 자세히 설명해주세요')}
            disabled={agentLoading}
          >
            {agentLoading ? '메뉴 정보 불러오는 중...' : '추천 메뉴'}
          </button>
        </div>

        {agentMessages.length > 1 && (
          <div className={styles.agentChat}>
            {agentMessages.slice(1).map((m, idx) => (
              <div
                key={idx}
                className={m.role === 'assistant' ? styles.chatBubbleAssistant : styles.chatBubbleUser}
              >
                {m.content}
              </div>
            ))}
            {agentLoading && <div className={styles.chatBubbleAssistant}>잠시만 기다려주세요…</div>}
          </div>
        )}

        <div className={styles.voiceBlock}>
          <button
            onClick={isListening ? stopListening : startListening}
            className={[styles.voiceButton, isListening ? styles.recording : ''].filter(Boolean).join(' ')}
            disabled={isProcessing || agentLoading}
          >
            {isListening ? '🎤' : '🗣️'}
          </button>
          <p className={styles.voiceHint}>
            {isListening ? '듣고 있어요…' : '말씀해 보세요 (예: "메뉴 추천")'}
          </p>
          {transcript && <p className={styles.transcript}>"{transcript}"</p>}
        </div>

        <div className={styles.ctaBar}>
          <button className={styles.primaryButton} onClick={() => setCurrentStep('menu')}>
            메뉴 정보 확인하기
          </button>
        </div>
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

  return (
    <div className={styles.mobileShell}>
      <div className={styles.inner}>
        {/* ★ 기존 renderStoreSelection() → 새 소개 화면 */}
        {currentStep === 'store' && renderStoreIntro()}
        {currentStep === 'menu' && renderMenuSelection()}
      </div>
    </div>
  );
};
export default VoiceOrderScreen;
