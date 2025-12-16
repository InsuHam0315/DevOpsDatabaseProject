'use client';

import { ReactNode, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';

export default function Protected({ children }: { children: ReactNode }) {
  const isAuthenticated = useStore((s) => s.isAuthenticated);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isAuthenticated) {
      // avoid redirect loop
      const current = pathname || '';
      if (current !== '/login' && current !== '/signup') {
        // replace로 변경하여 브라우저 history에 이전 페이지를 남기지 않음
        router.replace('/login');
      }
    }
  }, [isAuthenticated, pathname, router]);

  // 리다이렉트 처리 중엔 null 대신 간단한 로딩 메시지를 표시
  if (!isAuthenticated) return <div aria-busy>Redirecting to login...</div>;
  return <>{children}</>;
}
