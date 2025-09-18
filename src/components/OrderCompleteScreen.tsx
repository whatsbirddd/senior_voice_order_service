import { CheckCircle } from 'lucide-react';
import styles from './OrderCompleteScreen.module.css';

interface OrderCompleteScreenProps {
  orderNumber: string;
  onStartOver: () => void;
}

export function OrderCompleteScreen({ orderNumber, onStartOver }: OrderCompleteScreenProps) {
  return (
    <div className={styles.root}>
      <div className={styles.wrapper}>
        {/* 메인 완료 카드 */}
        <section className={styles.successCard}>
          <div className={styles.successHead}>
            <div className={styles.iconWrap}>
              <CheckCircle size={80} className={styles.icon} />
            </div>
            <h1 className={styles.title}>주문 완료!</h1>
          </div>

          {/* 주문번호 */}
          <div className={styles.numberCard}>
            <p className={styles.numberLabel}>주문번호</p>
            <p className={styles.numberValue}>{orderNumber}</p>
          </div>

          {/* 안내 메시지 */}
          <div className={styles.hints}>
            <p className={styles.hintLine}>맛있는 음식을 준비하고 있어요</p>
            <p className={styles.hintLine}>잠시만 기다려주세요! 😊</p>
          </div>
        </section>

        {/* 예상 시간 */}
        <section className={styles.etaCard}>
          <p className={styles.etaLabel}>예상 준비 시간</p>
          <p className={styles.etaValue}>15-20분</p>
        </section>

        {/* CTA */}
        <div className={styles.ctaBar}>
          <button className={styles.ctaButton} onClick={onStartOver}>
            새로 주문하기
          </button>
        </div>
      </div>
    </div>
  );
}
