'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useStore } from '@/lib/store';

export default function SignupPage() {
  const router = useRouter();
  const register = useStore((s) => s.register);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const ok = register(username.trim(), password);
      if (ok) {
        router.push('/login');
      } else {
        setError('이미 존재하는 사용자명입니다. 다른 이름을 사용하세요.');
      }
    } catch (err: any) {
      setError(err?.message || '회원가입 중 오류가 발생했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>회원가입</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1">사용자명</label>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" />
            </div>

            <div>
              <label className="text-sm font-medium block mb-1">비밀번호</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" />
            </div>

            {error && <div className="text-sm text-destructive">{error}</div>}

            <div className="flex items-center justify-between">
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? '처리중...' : '회원가입'}
              </Button>
            </div>

            <div className="text-sm text-muted-foreground text-center">
              이미 계정이 있으신가요?{' '}
              <Link href="/login" className="text-primary underline">
                로그인
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
