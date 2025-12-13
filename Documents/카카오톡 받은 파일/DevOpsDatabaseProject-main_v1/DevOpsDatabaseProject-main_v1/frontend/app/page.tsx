'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';

export default function Home() {
  const isAuthenticated = useStore((s) => s.isAuthenticated);
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) {
      router.replace('/plan');
    } else {
      router.replace('/login');
    }
  }, [isAuthenticated, router]);

  return <div>Redirecting...</div>;
}