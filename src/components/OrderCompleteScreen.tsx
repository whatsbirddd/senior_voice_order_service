import { CheckCircle } from 'lucide-react';

interface OrderCompleteScreenProps {
  orderNumber: string;
  onStartOver: () => void;
}

export function OrderCompleteScreen({ orderNumber, onStartOver }: OrderCompleteScreenProps) {
  return (
    <div className="min-h-screen bg-background text-foreground p-6 flex items-center justify-center">
      <div className="max-w-md mx-auto w-full">
        {/* 메인 완료 카드 */}
        <div 
          className="rounded-[40px] p-12 text-center mb-8 relative overflow-hidden"
          style={{ background: 'var(--gradient-green)' }}
        >
          {/* 완료 아이콘 */}
          <div className="mb-8">
            <div className="w-32 h-32 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle size={80} className="text-white" />
            </div>
            <h1 className="text-4xl mb-4 text-black/90">주문 완료!</h1>
          </div>

          {/* 주문번호 */}
          <div className="bg-white/20 backdrop-blur-sm rounded-3xl p-6 mb-6">
            <p className="text-xl text-black/70 mb-3">주문번호</p>
            <p className="text-6xl text-black/90 mb-4">{orderNumber}</p>
          </div>

          {/* 안내 메시지 */}
          <div className="space-y-2">
            <p className="text-xl text-black/70">맛있는 음식을 준비하고 있어요</p>
            <p className="text-xl text-black/70">잠시만 기다려주세요! 😊</p>
          </div>
        </div>

        {/* 예상 시간 카드 */}
        <div className="bg-card rounded-3xl p-6 mb-6 text-center">
          <p className="text-lg text-muted-foreground mb-2">예상 준비 시간</p>
          <p className="text-3xl text-card-foreground">15-20분</p>
        </div>

        {/* 새로 주문하기 버튼 */}
        <button
          onClick={onStartOver}
          className="w-full bg-white text-black py-4 rounded-2xl text-xl hover:bg-gray-100 active:scale-[0.98] transition-all duration-200"
        >
          새로 주문하기
        </button>
      </div>
    </div>
  );
}