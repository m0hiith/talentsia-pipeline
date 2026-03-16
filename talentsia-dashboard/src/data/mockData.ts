export interface NewsArticle {
  id: string;
  title: string;
  source: string;
  timeAgo: string;
  viralScore: number;
  upvotes: string;
  comments: number;
  tags: string[];
  snippet: string;
}

export const mockFeed: NewsArticle[] = [
  {
    id: '1',
    title: "OpenAI announces 'Strawberry' reasoning model for enhanced logical deduction",
    source: 'TechCrunch',
    timeAgo: '4m ago',
    viralScore: 9.4,
    upvotes: '4.2k',
    comments: 284,
    tags: ['AI'],
    snippet: 'The new model architecture promises to bridge the gap between pattern matching and actual symbolic reasoning in large language models...'
  },
  {
    id: '2',
    title: "Spatial computing enters the main stage: Apple Vision Pro 2 rumors leak",
    source: 'The Verge',
    timeAgo: '12m ago',
    viralScore: 8.7,
    upvotes: '1.8k',
    comments: 112,
    tags: ['TECH'],
    snippet: 'Supply chain reports suggest a more lightweight design focusing on weight distribution and a significantly brighter micro-OLED array...'
  },
  {
    id: '3',
    title: 'The rise of the "Prompt Engineer" might already be fading, research says',
    source: 'LinkedIn News',
    timeAgo: '45m ago',
    viralScore: 7.2,
    upvotes: '940',
    comments: 42,
    tags: ['JOBS'],
    snippet: 'New data suggests that general software engineering skills combined with AI tools are becoming more valuable than specialized prompting roles...'
  }
];
