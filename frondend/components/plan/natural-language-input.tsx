// frontend/src/components/plan/natural-language-input.tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

// 부모 컴포넌트로부터 받을 props의 타입을 정의합니다.
interface NaturalLanguageInputProps {
  onParsed: (data: any) => void; // 파싱 성공 시 호출할 함수
  setIsLoading: (loading: boolean) => void; // 로딩 상태를 부모에게 알릴 함수
}

export default function NaturalLanguageInput({ onParsed, setIsLoading }: NaturalLanguageInputProps) {
  const [naturalInput, setNaturalInput] = useState('');

  // "파싱 시뮬레이트" 버튼 클릭 시 실행될 함수
  const handleParseAndSave = async () => {
    if (!naturalInput.trim()) return;
    setIsLoading(true);
    onParsed(null); // 결과를 초기화하도록 부모에게 알림

    try {
      // Flask API #1 호출: 자연어 -> JSON 변환 -> DB 저장
      const response = await fetch('http://127.0.0.1:5001/api/parse-and-save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ natural_input: naturalInput }),
      });

      if (!response.ok) throw new Error('파싱 및 저장 서버 오류');
      const data = await response.json();
      
      // 💡 성공 시, props로 받은 onParsed 함수를 통해 부모 컴포넌트에 결과를 전달합니다.
      onParsed(data);

    } catch (error) {
      console.error('파싱/저장 중 오류:', error);
      alert('자연어 처리 및 저장 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Textarea
        placeholder="배송 요구사항을 자연스럽게 입력하세요..."
        value={naturalInput}
        onChange={(e) => setNaturalInput(e.target.value)}
        rows={10}
      />
      <div className="flex gap-2">
        <Button variant="outline">예시 입력</Button>
        <Button onClick={handleParseAndSave}>파싱 시뮬레이트</Button>
      </div>
    </div>
  );
}