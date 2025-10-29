'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Brain, FileText, CircleCheck as CheckCircle, CircleAlert as AlertCircle } from 'lucide-react';
import { OptimizationRequest } from '@/lib/types';

interface NaturalLanguageInputProps {
  onParsed: (request: OptimizationRequest | null) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000';

export default function NaturalLanguageInput({ onParsed }: NaturalLanguageInputProps) {
  const [input, setInput] = useState('');
  const [parsedResult, setParsedResult] = useState<OptimizationRequest | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null); // 오류 상태 추가

  const handleParseInput = async () => {
    if (!input.trim()) return;

    setIsProcessing(true);
    setError(null); // 오류 초기화
    setParsedResult(null); // 이전 결과 초기화
    onParsed(null); // 부모 컴포넌트에도 초기화 알림

    try {
      const response = await fetch(`${API_BASE_URL}/api/parse-natural-language`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ natural_input: input }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.details || `API 오류 (${response.status})`);
      }

      const result: OptimizationRequest = await response.json();
      setParsedResult(result);
      onParsed(result); // 성공 시 부모 컴포넌트에 파싱 결과 전달
      // 💡 성공 알림 (선택 사항)
      // toast({ title: "파싱 성공", description: "요청 내용이 JSON으로 변환되었습니다." });

    } catch (err: any) {
      console.error("파싱 오류:", err);
      setError(err.message || "자연어 처리 중 오류가 발생했습니다.");
      setParsedResult(null);
      onParsed(null);
      // 💡 오류 알림 (선택 사항)
      // toast({ variant: "destructive", title: "파싱 실패", description: err.message });
    } finally {
      setIsProcessing(false);
    }
  };

  const exampleInput = `오늘 V001 차량으로 군산 국제여객터미널에서에서 출발해서 부산A에 150kg 배송할거고 내일은 V002 차량으로 서울A에서 출발해서 대전 신세계백화점으로 100kg 배송할거야.`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Section */}
      <div className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="natural-input" className="text-sm font-medium">
            자연어 입력
          </label>
          <Textarea
            id="natural-input"
            placeholder="배송 요구사항을 자연스럽게 입력하세요..."
            className="min-h-[200px] resize-none"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
        </div>
        
        <div className="flex gap-2">
          <Button 
            onClick={() => setInput(exampleInput)}
            variant="outline" 
            size="sm"
          >
            예시 입력
          </Button>
          <Button 
            onClick={handleParseInput}
            disabled={!input.trim() || isProcessing}
            className="flex items-center gap-2"
          >
            {isProcessing ? (
              <>
                <div className="w-4 h-4 border-2 border-current border-t-transparent animate-spin rounded-full" />
                파싱 중...
              </>
            ) : (
              <>
                <Brain className="w-4 h-4" />
                요청
              </>
            )}
          </Button>
        </div>
        {error && (
          <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}
        {input && (
          <div className="text-sm text-muted-foreground bg-muted p-3 rounded-lg">
            <p className="font-medium mb-1">💡 입력 분석:</p>
            <p>LLM이 자연어를 구조화된 JSON으로 변환합니다</p>
          </div>
        )}
      </div>

      {/* Preview Section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileText className="w-5 h-5" />
            JSON 미리보기
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* 💡 로딩 중 표시 추가 */}
          {isProcessing ? (
             <div className="text-center py-8 text-muted-foreground">
                 <div className="w-8 h-8 mx-auto border-4 border-primary border-t-transparent animate-spin rounded-full mb-3" />
                 <p>LLM이 요청을 분석하고 있습니다...</p>
             </div>
          ) : !parsedResult && !error ? ( // 💡 초기 상태 또는 오류 없을 때만 기본 메시지
            <div className="text-center py-8 text-muted-foreground">
              <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>자연어 입력 후 파싱 버튼을 클릭하세요</p>
            </div>
          ) : error ? ( // 💡 오류 발생 시 메시지
             <div className="text-center py-8 text-destructive">
                 <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                 <p>파싱 중 오류가 발생했습니다.</p>
                 <p className="text-xs mt-1">{error}</p>
             </div>
          ) : parsedResult ? ( // 💡💡💡 parsedResult가 null이 아닐 때만 이 블록을 렌더링
            <div className="space-y-4">
              {/* Validation Status */}
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-green-600 font-medium">파싱 성공</span>
                {/* 💡 Optional chaining 사용 또는 parsedResult가 있음을 확신하므로 그대로 사용 가능 */}
                <Badge variant="secondary" className="ml-auto">
                  {parsedResult.jobs.length}개 작업
                </Badge>
              </div>
              <Separator />

              {/* Parsed Data Summary */}
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium mb-1">실행 날짜</p>
                  {/* 💡 parsedResult가 null이 아님 */}
                  <Badge variant="outline">{parsedResult.run_date}</Badge>
                </div>

                <div>
                  {/* 💡 parsedResult가 null이 아님 */}
                  <p className="text-sm font-medium mb-1">차량 ({parsedResult.vehicles.length}대)</p>
                  <div className="flex gap-1 flex-wrap">
                    {/* 💡 parsedResult가 null이 아님 */}
                    {parsedResult.vehicles.map((vehicle) => (
                      <Badge key={vehicle} variant="secondary">{vehicle}</Badge>
                    ))}
                  </div>
                </div>

                 <div>
                  <p className="text-sm font-medium mb-2">작업 목록</p>
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {/* 💡 parsedResult가 null이 아님 */}
                    {parsedResult.jobs.map((job, index) => (
                      <div key={index} className="bg-muted p-2 rounded text-sm">
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium">{job.sector_id}</span>
                          <Badge variant="outline">{job.demand_kg}kg</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <details className="group">
                <summary className="cursor-pointer text-sm font-medium">원본 JSON 보기</summary>
                <pre className="mt-2 p-3 bg-slate-100 rounded text-xs overflow-x-auto">
                  {/* 💡 parsedResult가 null이 아님 */}
                  {JSON.stringify(parsedResult, null, 2)}
                </pre>
              </details>
            </div>
          ) : (
            // 초기 상태 표시 (동일)
            <div className="text-center py-8 text-muted-foreground">
              <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>자연어 입력 후 파싱 버튼을 클릭하세요</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}