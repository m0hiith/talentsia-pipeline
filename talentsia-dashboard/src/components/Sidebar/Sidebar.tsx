import styles from './Sidebar.module.css';

export default function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.topSection}>
        <div className={styles.navItem}>
          <span className={styles.rssIcon}></span>
          <span className={styles.navText}>LIVE FEED</span>
        </div>
      </div>
      
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>OVERVIEW</h3>
        <div className={styles.statsGrid}>
          <div className={styles.statBox}>
            <div className={styles.statLabel}>TOTAL SCORE</div>
            <div className={styles.statValue}>1,284</div>
          </div>
          <div className={styles.statBox}>
            <div className={styles.statLabel}>TOP SCORE</div>
            <div className={styles.statValueOrange}>9.8</div>
          </div>
          <div className={styles.statBox}>
            <div className={styles.statLabel}>AVG VIRAL</div>
            <div className={styles.statValue}>6.4</div>
          </div>
          <div className={styles.statBox}>
            <div className={styles.statLabel}>SOURCES</div>
            <div className={styles.statValue}>42</div>
          </div>
        </div>
      </div>

      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>TOP PICKS TODAY</h3>
        <ul className={styles.picksList}>
          <li className={styles.pickItem}>
            <div className={styles.pickHeader}>
              <span className={styles.pickRank}>#1</span>
              <span className={styles.pickDot}>·</span>
              <span className={styles.pickScore}>9.4 VIRALITY</span>
            </div>
            <p className={styles.pickDesc}>AI breakthrough in robotics labs at Stanford.</p>
          </li>
          <li className={styles.pickItem}>
            <div className={styles.pickHeader}>
              <span className={styles.pickRank}>#2</span>
              <span className={styles.pickDot}>·</span>
              <span className={styles.pickScore}>8.9 VIRALITY</span>
            </div>
            <p className={styles.pickDesc}>New job market trends for Gen Z graduates.</p>
          </li>
          <li className={styles.pickItem}>
            <div className={styles.pickHeader}>
              <span className={styles.pickRank}>#3</span>
              <span className={styles.pickDot}>·</span>
              <span className={styles.pickScore}>8.2 VIRALITY</span>
            </div>
            <p className={styles.pickDesc}>Student hackathon winners reveal green energy UI.</p>
          </li>
        </ul>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHeaderRow}>
          <h3 className={styles.sectionTitle}>SOURCES</h3>
          <button className={styles.editBtn}>EDIT</button>
        </div>
        <ul className={styles.sourceList}>
          <li className={`${styles.sourceItem} ${styles.sourceItemActive}`}>
            <span>All Sources</span>
            <span className={styles.sourceCountOrange}>42</span>
          </li>
          <li className={styles.sourceItem}>
            <span>TechCrunch</span>
            <span className={styles.sourceCount}>12</span>
          </li>
          <li className={styles.sourceItem}>
            <span>The Verge</span>
            <span className={styles.sourceCount}>8</span>
          </li>
          <li className={styles.sourceItem}>
            <span>GitHub Blog</span>
            <span className={styles.sourceCount}>4</span>
          </li>
        </ul>
      </div>
    </aside>
  );
}
