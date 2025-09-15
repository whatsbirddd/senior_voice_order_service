import { ImageWithFallback } from './figma/ImageWithFallback';
import { ArrowLeft, Trash2 } from 'lucide-react';

interface CartItem {
  id: string;
  name: string;
  price: number;
  image: string;
  quantity: number;
}

interface CartScreenProps {
  cart: CartItem[];
  onRemoveFromCart: (id: string) => void;
  onPlaceOrder: () => void;
  onBack: () => void;
}

export function CartScreen({ cart, onRemoveFromCart, onPlaceOrder, onBack }: CartScreenProps) {
  const totalPrice = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);

  if (cart.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-md mx-auto">
          {/* 헤더 */}
          <div className="flex items-center mb-8 pt-8">
            <button 
              onClick={onBack}
              className="p-3 rounded-full bg-white shadow-md mr-4 hover:bg-gray-50 active:scale-95"
            >
              <ArrowLeft size={24} />
            </button>
            <div>
              <h1 className="text-4xl mb-2">장바구니</h1>
              <p className="text-2xl text-gray-600">주문할 메뉴를 확인해주세요</p>
            </div>
          </div>

          {/* 빈 장바구니 */}
          <div className="bg-white rounded-3xl shadow-lg p-12 text-center">
            <p className="text-3xl text-gray-500 mb-4">장바구니가 비어있습니다</p>
            <p className="text-xl text-gray-400">메뉴를 선택해주세요</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-md mx-auto">
        {/* 헤더 */}
        <div className="flex items-center mb-8 pt-8">
          <button 
            onClick={onBack}
            className="p-3 rounded-full bg-white shadow-md mr-4 hover:bg-gray-50 active:scale-95"
          >
            <ArrowLeft size={24} />
          </button>
          <div>
            <h1 className="text-4xl mb-2">장바구니</h1>
            <p className="text-2xl text-gray-600">주문할 메뉴를 확인해주세요</p>
          </div>
        </div>

        {/* 장바구니 아이템들 */}
        <div className="space-y-6 mb-8">
          {cart.map((item) => (
            <div key={item.id} className="bg-white rounded-3xl shadow-lg overflow-hidden border-2 border-gray-200">
              {/* 이미지 영역 */}
              <div className="bg-orange-100 p-6 rounded-t-3xl">
                <ImageWithFallback 
                  src={item.image}
                  alt={item.name}
                  className="w-full h-32 object-cover rounded-2xl"
                />
              </div>
              
              {/* 텍스트 영역 */}
              <div className="bg-pink-100 p-6 rounded-b-3xl">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="text-2xl mb-2">{item.name}</h3>
                    <p className="text-xl text-gray-600 mb-2">수량: {item.quantity}개</p>
                    <p className="text-2xl text-orange-600">{(item.price * item.quantity).toLocaleString()}원</p>
                  </div>
                  <button
                    onClick={() => onRemoveFromCart(item.id)}
                    className="p-3 rounded-full bg-red-100 text-red-600 hover:bg-red-200 active:scale-95"
                  >
                    <Trash2 size={20} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 총 가격과 주문 버튼 */}
        <div className="bg-white rounded-3xl shadow-lg p-8">
          <div className="text-center mb-6">
            <p className="text-2xl text-gray-600 mb-2">총 결제 금액</p>
            <p className="text-5xl text-orange-600 mb-6">{totalPrice.toLocaleString()}원</p>
          </div>
          
          <button
            onClick={onPlaceOrder}
            className="w-full bg-green-500 text-white py-6 rounded-2xl text-3xl hover:bg-green-600 active:scale-[0.98] transition-all duration-200"
          >
            주문하기
          </button>
        </div>
      </div>
    </div>
  );
}