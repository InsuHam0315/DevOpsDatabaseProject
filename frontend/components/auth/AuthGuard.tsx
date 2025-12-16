'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';

/**
 * 전역 인증 가드: 로그인되지 않았으면 /login으로 리다이렉트합니다.
 * 예외 경로: /login, /signup, API 경로 등
 */
export default function AuthGuard() {
  const isAuthenticated = useStore((s) => s.isAuthenticated);
  const router = useRouter();
  const pathname = usePathname() || '/';

  useEffect(() => {
    try {
      const allowlist = ['/login', '/signup', '/public', '/api', '/_next', '/favicon.ico'];
      const isAllowed = allowlist.some((p) => pathname.startsWith(p));

      if (!isAuthenticated && !isAllowed) {
        // replace로 히스토리에 남기지 않고 리다이렉트
        router.replace('/login');
      }
    } catch (e) {
      // 실패 시 안전하게 noop
      console.error('AuthGuard 예외:', e);
    }
  }, [isAuthenticated, pathname, router]);

  // 렌더링할 UI 필요 없음(레이아웃에서 전역으로 동작)
  return null;
}
