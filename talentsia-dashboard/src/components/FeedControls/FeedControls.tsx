import { Search } from 'lucide-react';
import styles from './FeedControls.module.css';

export default function FeedControls() {
  return (
    <div className={styles.controlsContainer}>
      <div className={styles.topRow}>
        <div className={styles.tabs}>
          <button className={`${styles.tab} ${styles.tabActive}`}>ALL</button>
          <button className={styles.tab}>AI</button>
          <button className={styles.tab}>TECH</button>
          <button className={styles.tab}>JOBS</button>
          <button className={styles.tab}>HACKATHONS</button>
        </div>
        
        <div className={styles.sliderGroup}>
          <span className={styles.sliderLabel}>MIN VIRAL</span>
          <div className={styles.sliderTrackWrapper}>
            <input type="range" min="0" max="10" step="0.1" defaultValue="5.0" className={styles.slider} />
            <div className={styles.sliderProgress} style={{ width: '50%' }}></div>
            <div className={styles.sliderThumb} style={{ left: '50%' }}></div>
          </div>
          <span className={styles.sliderValue}>5.0</span>
        </div>
      </div>

      <div className={styles.searchRow}>
        <div className={styles.searchBox}>
          <Search size={16} className={styles.searchIcon} />
          <input 
            type="text" 
            placeholder="SEARCH INTELLIGENCE DATABASE..." 
            className={styles.searchInput} 
          />
        </div>
      </div>
    </div>
  );
}
