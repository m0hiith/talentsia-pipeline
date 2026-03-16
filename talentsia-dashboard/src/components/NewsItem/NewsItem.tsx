import { MessageSquare, Triangle } from 'lucide-react';
import { NewsArticle } from '../../data/mockData';
import styles from './NewsItem.module.css';

interface NewsItemProps {
  article: NewsArticle;
}

export default function NewsItem({ article }: NewsItemProps) {
  return (
    <article className={styles.newsCard}>
      <div className={styles.viralitySection}>
        <div className={styles.scoreValue}>{article.viralScore.toFixed(1)}</div>
        <div className={styles.scoreLabel}>VIRAL</div>
        <div className={styles.scoreBarContainer}>
          <div 
            className={styles.scoreBarFill} 
            style={{ width: `${(article.viralScore / 10) * 100}%` }}
          ></div>
        </div>
      </div>

      <div className={styles.contentSection}>
        <div className={styles.metaInfo}>
          {article.tags.map(tag => (
            <span key={tag} className={styles.tag}>{tag}</span>
          ))}
          <span className={styles.sourceInfo}>
            {article.source} <span className={styles.dot}>·</span> {article.timeAgo}
          </span>
        </div>
        
        <h2 className={styles.title}>{article.title}</h2>
        <p className={styles.snippet}>{article.snippet}</p>
      </div>

      <div className={styles.actionSection}>
        <div className={styles.metrics}>
          <div className={styles.metric}>
            <Triangle size={12} className={styles.upvoteIcon} />
            {article.upvotes}
          </div>
          <div className={styles.metric}>
            <MessageSquare size={12} className={styles.commentIcon} />
            {article.comments}
          </div>
        </div>
        <button className={styles.openBtn}>
          OPEN <span className={styles.arrowIcon}>↗</span>
        </button>
      </div>
    </article>
  );
}
