import { useState } from 'react';
import { VoiceOrderScreen } from './components/VoiceOrderScreen';
import { OrderCompleteScreen } from './components/OrderCompleteScreen';

type Screen = 'voice-order' | 'complete';

export default function App() {
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
    <div className="relative">
      {/* 화면 렌더링 */}
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