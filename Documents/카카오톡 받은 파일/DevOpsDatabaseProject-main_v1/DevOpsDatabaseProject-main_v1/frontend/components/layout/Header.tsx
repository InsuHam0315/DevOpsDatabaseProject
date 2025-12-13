'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Leaf, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useStore } from '@/lib/store';

const navigation = [
  { name: '경로 계획', href: '/plan' },
  { name: '경로 결과', href: '/routes' },
  { name: '대시보드', href: '/dashboard' },
  { name: '데이터 관리', href: '/admin' }
];

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { kpis, isAuthenticated, currentUser, logout } = useStore();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-auto items-center py-3 justify-between">
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-2">
            <Leaf className="h-6 w-6 text-green-600" />
            <span className="font-bold text-lg">Eco Logistics Optimizer</span>
          </Link>

          <nav className="flex items-center space-x-6 text-sm font-medium">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "transition-colors hover:text-foreground/80",
                  pathname === item.href ? "text-foreground font-medium" : "text-foreground/60"
                )}
              >
                {item.name}
              </Link>
            ))}
          </nav>
        </div>

        {/* Right-most single auth control (web only) */}
        <div className="flex items-center gap-3">
          {isAuthenticated && (
            <>
              <span className="text-sm text-muted-foreground">{currentUser}</span>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="w-4 h-4 mr-2" />
                로그아웃
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}