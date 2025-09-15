import type { Metadata, Viewport } from 'next';
// Import Figma-exported CSS only to avoid conflicts
import '../index.css';
// Minimal tokens/overrides (kept light to not override Figma styles)
import './globals.css';

export const metadata: Metadata = {
  title: '점원 Agent - 말 걸면 다 해주는 똑똑한 점원',
  description: '음성 인식으로 메뉴 추천, 주문, 결제까지 한 번에! 아이폰 16 최적화',
  keywords: ['음성 주문', '메뉴 추천', '삼성페이', 'QR 코드', '아이폰 16'],
  authors: [{ name: 'LG Prompthon Team' }],
  creator: 'LG Prompthon Team',
  publisher: 'LG Prompthon',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: '점원 Agent',
    startupImage: [
      {
        url: '/splash-iphone16.png',
        media: '(device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3)',
      },
      {
        url: '/splash-iphone16-pro-max.png', 
        media: '(device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3)',
      },
    ],
  },
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#1f2937' },
  ],
};

const noto = { className: '' } as any;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="점원 Agent" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="msapplication-TileColor" content="#f97316" />
        <meta name="msapplication-tap-highlight" content="no" />
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
        <link rel="mask-icon" href="/safari-pinned-tab.svg" color="#f97316" />
      </head>
      <body className={`antialiased ${noto.className} bg-gray-50`}>
        <div className="mobile-shell min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
