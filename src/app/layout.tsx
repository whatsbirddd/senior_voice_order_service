import type { Metadata } from 'next';

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
        <link rel="stylesheet" href="/static/styles.css" />
        <script src="/static/app.js" defer />
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
