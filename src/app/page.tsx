"use client";

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { OrderCompleteScreen } from '../components/OrderCompleteScreen';

const VoiceOrderScreen = dynamic(() => import('../components/VoiceOrderScreen'), {
  ssr: false,
  loading: () => <div className="loading">화면을 불러오고 있어요...</div>,
});

type Screen = 'voice-order' | 'complete';

export default function Page() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('voice-order');
  const [orderNumber, setOrderNumber] = useState<string>('');

  const handleOrderComplete = (orderNum: string) => {
    setOrderNumber(orderNum);
    setCurrentScreen('complete');
  };

  const handleStartOver = () => {
    setOrderNumber('');
    setCurrentScreen('voice-order');
  };

  return (
    <div className="container px pt pb">
      {currentScreen === 'voice-order' && (
        <VoiceOrderScreen onOrderComplete={handleOrderComplete} />
      )}

      {currentScreen === 'complete' && (
        <OrderCompleteScreen
          orderNumber={orderNumber}
          onStartOver={handleStartOver}
        />
      )}
    </div>
  );
}
