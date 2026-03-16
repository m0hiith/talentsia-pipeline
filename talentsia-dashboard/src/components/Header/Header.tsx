import styles from './Header.module.css';
import { Search, Settings } from 'lucide-react';

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.brandGroup}>
        <div className={styles.logo}>
          <span className={styles.logoIcon}></span>
          TALENTSIA<span className={styles.logoDot}>.</span>
        </div>
        <div className={styles.liveIndicator}>
          <div className={styles.liveDot}></div>
          LIVE
        </div>
      </div>
      
      <div className={styles.actionsGroup}>
        <button className={styles.textButton}>RE-RANK</button>
        <button className={styles.primaryButton}>
          <span className={styles.playIcon}>▶</span> PULL NEWS
        </button>
        <button className={styles.iconButton}>
          <Search size={18} />
        </button>
        <button className={styles.iconButton}>
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}
