import { ImageWithFallback } from './figma/ImageWithFallback';

interface CategoryScreenProps {
  onSelectCategory: (category: string) => void;
}

const categories = [
  {
    id: 'main',
    name: '메인 요리',
    image: 'https://images.unsplash.com/photo-1708388064959-7f29be02a819?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBidWxnb2dpJTIwYmVlZnxlbnwxfHx8fDE3NTc5MTA2NTd8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    description: '불고기, 갈비, 삼겹살'
  },
  {
    id: 'soup',
    name: '국물 요리', 
    image: 'https://images.unsplash.com/photo-1714782380594-d857b46265fc?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBraW1jaGklMjBqamlnYWUlMjBzdGV3fGVufDF8fHx8MTc1NzkxMDY2MHww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    description: '김치찌개, 된장찌개, 미역국'
  },
  {
    id: 'rice',
    name: '밥류',
    image: 'https://images.unsplash.com/photo-1718777791239-c473e9ce7376?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxrb3JlYW4lMjBiaWJpbWJhcCUyMHJpY2UlMjBib3dsfGVufDF8fHx8MTc1NzkxMDY2M3ww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
    description: '비빔밥, 볶음밥, 덮밥'
  }
];

export function CategoryScreen({ onSelectCategory }: CategoryScreenProps) {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-md mx-auto">
        {/* 헤더 */}
        <div className="text-center mb-8 pt-8">
          <h1 className="text-4xl mb-4">메뉴 선택</h1>
          <p className="text-2xl text-gray-600">원하시는 종류를 선택해주세요</p>
        </div>

        {/* 카테고리 목록 */}
        <div className="space-y-6">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => onSelectCategory(category.id)}
              className="w-full bg-white rounded-3xl shadow-lg overflow-hidden border-2 border-gray-200 hover:border-orange-300 transition-all duration-200 active:scale-[0.98]"
            >
              {/* 이미지 영역 */}
              <div className="bg-orange-100 p-8 rounded-t-3xl">
                <ImageWithFallback 
                  src={category.image}
                  alt={category.name}
                  className="w-full h-48 object-cover rounded-2xl"
                />
              </div>
              
              {/* 텍스트 영역 */}
              <div className="bg-pink-100 p-8 rounded-b-3xl">
                <h2 className="text-3xl mb-3">{category.name}</h2>
                <p className="text-xl text-gray-700">{category.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}