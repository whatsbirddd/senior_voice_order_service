import { ImageWithFallback } from './figma/ImageWithFallback';
import { ArrowLeft } from 'lucide-react';

interface MenuItem {
  id: string;
  name: string;
  price: number;
  image: string;
  description: string;
}

interface MenuScreenProps {
  category: string;
  onSelectMenu: (menu: MenuItem) => void;
  onBack: () => void;
}

const menuData: Record<string, MenuItem[]> = {
  main: [
    {
      id: 'bulgogi',
      name: '불고기',
      price: 18000,
      image: 'https://images.unsplash.com/photo-1708388064959-7f29be02a819?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBidWxnb2dpJTIwYmVlZnxlbnwxfHx8fDE3NTc5MTA2NTd8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
      description: '달콤한 양념에 재운 소고기'
    },
    {
      id: 'chicken',
      name: '치킨',
      price: 16000,
      image: 'https://images.unsplash.com/photo-1741004418691-e68682816528?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBmcmllZCUyMGNoaWNrZW4lMjBjcmlzcHl8ZW58MXx8fHwxNzU3OTEwNjY2fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
      description: '바삭하고 맛있는 프라이드 치킨'
    }
  ],
  soup: [
    {
      id: 'kimchi-jjigae',
      name: '김치찌개',
      price: 12000,
      image: 'https://images.unsplash.com/photo-1714782380594-d857b46265fc?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBraW1jaGklMjBqamlnYWUlMjBzdGV3fGVufDF8fHx8MTc1NzkxMDY2MHww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
      description: '시원하고 얼큰한 김치찌개'
    }
  ],
  rice: [
    {
      id: 'bibimbap',
      name: '비빔밥',
      price: 14000,
      image: 'https://images.unsplash.com/photo-1718777791239-c473e9ce7376?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBiaWJpbWJhcCUyMHJpY2UlMjBib3dsfGVufDF8fHx8MTc1NzkxMDY2M3ww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
      description: '영양 만점 나물과 밥'
    }
  ]
};

const categoryNames: Record<string, string> = {
  main: '메인 요리',
  soup: '국물 요리',
  rice: '밥류'
};

export function MenuScreen({ category, onSelectMenu, onBack }: MenuScreenProps) {
  const menus = menuData[category] || [];
  const categoryName = categoryNames[category] || '메뉴';

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
            <h1 className="text-4xl mb-2">{categoryName}</h1>
            <p className="text-2xl text-gray-600">메뉴를 선택해주세요</p>
          </div>
        </div>

        {/* 메뉴 목록 */}
        <div className="space-y-6">
          {menus.map((menu) => (
            <button
              key={menu.id}
              onClick={() => onSelectMenu(menu)}
              className="w-full bg-white rounded-3xl shadow-lg overflow-hidden border-2 border-gray-200 hover:border-orange-300 transition-all duration-200 active:scale-[0.98]"
            >
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
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}