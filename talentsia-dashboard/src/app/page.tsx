import DashboardLayout from '@/components/DashboardLayout/DashboardLayout';
import FeedControls from '@/components/FeedControls/FeedControls';
import NewsItem from '@/components/NewsItem/NewsItem';
import { mockFeed } from '@/data/mockData';

export default function Home() {
  return (
    <DashboardLayout>
      <FeedControls />
      
      <div style={{ marginTop: '16px' }}>
        {mockFeed.map(article => (
          <NewsItem key={article.id} article={article} />
        ))}
        
        <div style={{ 
          padding: '40px', 
          textAlign: 'center', 
          color: 'var(--text-tertiary)',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          letterSpacing: '2px'
        }}>
          LOAD 50 MORE STORIES
        </div>
      </div>
    </DashboardLayout>
  );
}
