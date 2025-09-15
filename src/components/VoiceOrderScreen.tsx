'use client';

import React, { useState, useEffect, useRef } from 'react';

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
  onOrderComplete: (orderItems: OrderItem[], totalAmount: number) => void;
}

const VoiceOrderScreen: React.FC<VoiceOrderScreenProps> = ({ onOrderComplete }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [orderItems, setOrderItems] = useState<OrderItem[]>([]);
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [selectedStore, setSelectedStore] = useState('옥소반 마곡본점');
  const [currentStep, setCurrentStep] = useState<'store' | 'menu' | 'order' | 'confirm'>('store');
  const [isProcessing, setIsProcessing] = useState(false);
  const recognitionRef = useRef<any>(null);

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

  const processVoiceCommand = (command: string) => {
    setIsProcessing(true);
    
    // 간단한 음성 명령 처리
    const lowerCommand = command.toLowerCase();
    
    if (currentStep === 'menu') {
      // 메뉴 주문 처리
      menuItems.forEach(item => {
        if (lowerCommand.includes(item.name)) {
          addToOrder(item);
        }
      });
    }
    
    setTimeout(() => {
      setIsProcessing(false);
    }, 1000);
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
      onOrderComplete(orderItems, getTotalAmount());
    }
  };

  const renderStoreSelection = () => (
    <div className="animate-fade-in">
      <div className="text-center mb-8">
        <h1 className="text-large mb-4 text-gray-900">매장을 선택해주세요</h1>
        <p className="text-regular text-gray-600">음성으로 말씀하시거나 터치해주세요</p>
      </div>
      
      <div className="space-y-4 mb-8">
        {['옥소반 마곡본점', '옥소반 강남점', '옥소반 홍대점'].map((store) => (
          <button
            key={store}
            onClick={() => {
              setSelectedStore(store);
              setCurrentStep('menu');
            }}
            className={`w-full card-hover p-6 rounded-2xl border-3 text-left ${
              selectedStore === store 
                ? 'border-orange-400 bg-orange-50' 
                : 'border-gray-200 bg-white'
            }`}
          >
            <div className="text-medium font-bold text-gray-900">{store}</div>
            <div className="text-regular text-gray-600 mt-2">영업시간: 11:00 - 22:00</div>
          </button>
        ))}
      </div>

      <div className="text-center">
        <button
          onClick={isListening ? stopListening : startListening}
          className={`voice-button ${isListening ? 'recording' : ''}`}
          disabled={isProcessing}
        >
          {isListening ? '🎤' : '🗣️'}
        </button>
        <p className="text-regular text-gray-600 mt-4">
          {isListening ? '듣고 있습니다...' : '음성으로 매장 선택하기'}
        </p>
      </div>
    </div>
  );

  const renderMenuSelection = () => (
    <div className="animate-fade-in">
      <div className="text-center mb-6">
        <h1 className="text-large mb-2 text-gray-900">메뉴를 선택해주세요</h1>
        <p className="text-regular text-gray-600">{selectedStore}</p>
      </div>

      <div className="grid gap-4 mb-6">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => addToOrder(item)}
            className="menu-item text-left"
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h3 className="text-medium font-bold text-gray-900 mb-2">{item.name}</h3>
                <p className="text-regular text-gray-600 mb-3">{item.description}</p>
                <p className="text-medium font-bold text-orange-600">
                  {item.price.toLocaleString()}원
                </p>
              </div>
              <div className="ml-4 text-4xl">🍽️</div>
            </div>
          </button>
        ))}
      </div>

      {orderItems.length > 0 && (
        <div className="card mb-6 bg-orange-50 border-orange-200">
          <h3 className="text-medium font-bold text-gray-900 mb-4">주문 내역</h3>
          {orderItems.map((item) => (
            <div key={item.id} className="flex justify-between items-center mb-3 last:mb-0">
              <div className="flex-1">
                <span className="text-regular font-semibold text-gray-900">{item.name}</span>
                <span className="text-regular text-gray-600 ml-2">x{item.quantity}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-regular font-bold text-orange-600">
                  {(item.price * item.quantity).toLocaleString()}원
                </span>
                <button
                  onClick={() => removeFromOrder(item.id)}
                  className="w-8 h-8 rounded-full bg-red-500 text-white text-sm font-bold"
                >
                  -
                </button>
              </div>
            </div>
          ))}
          <div className="border-t-2 border-orange-200 pt-4 mt-4">
            <div className="flex justify-between items-center">
              <span className="text-medium font-bold text-gray-900">총 금액</span>
              <span className="text-large font-bold text-orange-600">
                {getTotalAmount().toLocaleString()}원
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="text-center">
          <button
            onClick={isListening ? stopListening : startListening}
            className={`voice-button ${isListening ? 'recording' : ''}`}
            disabled={isProcessing}
          >
            {isListening ? '🎤' : '🗣️'}
          </button>
          <p className="text-regular text-gray-600 mt-4">
            {isListening ? '주문을 듣고 있습니다...' : '음성으로 주문하기'}
          </p>
          {transcript && (
            <p className="text-regular text-orange-600 mt-2 font-semibold">
              "{transcript}"
            </p>
          )}
        </div>

        {orderItems.length > 0 && (
          <button
            onClick={handleOrderComplete}
            className="btn-primary w-full"
          >
            <span>주문하기</span>
            <span className="text-xl">🛒</span>
          </button>
        )}

        <button
          onClick={() => setCurrentStep('store')}
          className="btn-secondary w-full"
        >
          <span>매장 다시 선택</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="mobile-shell">
      <div className="p-6 min-h-screen bg-gray-50">
        {currentStep === 'store' && renderStoreSelection()}
        {currentStep === 'menu' && renderMenuSelection()}
      </div>
    </div>
  );
};

export default VoiceOrderScreen;
