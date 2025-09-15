import { useState } from 'react';
import { ImageWithFallback } from './figma/ImageWithFallback';
import { ArrowLeft, Minus, Plus } from 'lucide-react';

interface MenuItem {
  id: string;
  name: string;
  price: number;
  image: string;
  description: string;
}

interface QuantityScreenProps {
  menu: MenuItem;
  onAddToCart: (menu: MenuItem, quantity: number) => void;
  onBack: () => void;
}

export function QuantityScreen({ menu, onAddToCart, onBack }: QuantityScreenProps) {
  const [quantity, setQuantity] = useState(1);

  const handleQuantityChange = (change: number) => {
    const newQuantity = quantity + change;
    if (newQuantity >= 1) {
      setQuantity(newQuantity);
    }
  };

  const handleAddToCart = () => {
    onAddToCart(menu, quantity);
  };

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
            <h1 className="text-4xl mb-2">수량 선택</h1>
            <p className="text-2xl text-gray-600">몇 개를 주문하시겠어요?</p>
          </div>
        </div>

        {/* 선택된 메뉴 */}
        <div className="bg-white rounded-3xl shadow-lg overflow-hidden border-2 border-gray-200 mb-8">
          {/* 이미지 영역 */}
          <div className="bg-orange-100 p-8 rounded-t-3xl">
            <ImageWithFallback 
              src={menu.image}
              alt={menu.name}
              className="w-full h-48 object-cover rounded-2xl"
            />
          </div>
          
          {/* 텍스트 영역 */}
          <div className="bg-pink-100 p-8 rounded-b-3xl">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-3xl">{menu.name}</h2>
              <span className="text-3xl text-orange-600">{menu.price.toLocaleString()}원</span>
            </div>
            <p className="text-xl text-gray-700">{menu.description}</p>
          </div>
        </div>

        {/* 수량 선택 */}
        <div className="bg-white rounded-3xl shadow-lg p-8 mb-8">
          <div className="flex items-center justify-center space-x-8">
            <button
              onClick={() => handleQuantityChange(-1)}
              className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center hover:bg-gray-300 active:scale-95 disabled:opacity-50"
              disabled={quantity <= 1}
            >
              <Minus size={32} />
            </button>
            
            <span className="text-6xl min-w-[120px] text-center">{quantity}</span>
            
            <button
              onClick={() => handleQuantityChange(1)}
              className="w-16 h-16 rounded-full bg-orange-200 flex items-center justify-center hover:bg-orange-300 active:scale-95"
            >
              <Plus size={32} />
            </button>
          </div>
        </div>

        {/* 총 가격과 장바구니 버튼 */}
        <div className="bg-white rounded-3xl shadow-lg p-8">
          <div className="text-center mb-6">
            <p className="text-2xl text-gray-600 mb-2">총 가격</p>
            <p className="text-5xl text-orange-600">{(menu.price * quantity).toLocaleString()}원</p>
          </div>
          
          <button
            onClick={handleAddToCart}
            className="w-full bg-orange-500 text-white py-6 rounded-2xl text-3xl hover:bg-orange-600 active:scale-[0.98] transition-all duration-200"
          >
            장바구니에 담기
          </button>
        </div>
      </div>
    </div>
  );
}