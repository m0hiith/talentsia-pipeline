import { ReactNode } from 'react';
import Header from '../Header/Header';
import Sidebar from '../Sidebar/Sidebar';
import styles from './DashboardLayout.module.css';

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className={styles.container}>
      <Header />
      <div className={styles.mainWrapper}>
        <Sidebar />
        <main className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
}
