import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '음성 주문 • 옥소반 마곡본점',
  description: '시니어를 위한 음성 주문 데모',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
