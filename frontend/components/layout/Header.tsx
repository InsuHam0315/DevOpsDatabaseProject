'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Leaf, Menu, TrendingUp, Route as RouteIcon, Clock, Zap, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
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
      <div className="container flex h-auto items-center py-3">
        <Link href="/" className="flex items-center space-x-2 mr-6">
          <Leaf className="h-6 w-6 text-green-600" />
          <span className="font-bold text-lg">Eco Logistics Optimizer</span>
        </Link>

        <div className="flex-1 flex flex-col md:flex-row md:items-center gap-4">
          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "transition-colors hover:text-foreground/80",
                  pathname === item.href ? "text-foreground" : "text-foreground/60"
                )}
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* KPI Summary moved to dashboard */}

          {/* User Info & Logout */}
          {isAuthenticated && (
            <div className="hidden md:flex items-center gap-3 ml-4">
              <span className="text-sm text-muted-foreground">{currentUser}</span>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="w-4 h-4 mr-2" />
                로그아웃
              </Button>
            </div>
          )}
        </div>

        {/* Mobile Navigation */}
        <Sheet>
          <SheetTrigger asChild>
            <Button
              variant="ghost"
              className="md:hidden ml-auto"
              size="sm"
            >
              <Menu className="h-5 w-5" />
              <span className="sr-only">Toggle Menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="right">
            <Link href="/" className="flex items-center space-x-2 mb-6">
              <Leaf className="h-6 w-6 text-green-600" />
              <span className="font-bold">Eco Logistics</span>
            </Link>
            <nav className="flex flex-col space-y-4">
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
          </SheetContent>
        </Sheet>
      </div>
    </header>
  );
}