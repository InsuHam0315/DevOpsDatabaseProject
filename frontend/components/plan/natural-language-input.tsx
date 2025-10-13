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
  onParsed: (request: OptimizationRequest) => void;
}

export default function NaturalLanguageInput({ onParsed }: NaturalLanguageInputProps) {
  const [input, setInput] = useState('');
  const [parsedResult, setParsedResult] = useState<OptimizationRequest | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleParseInput = async () => {
    if (!input.trim()) return;
    
    setIsProcessing(true);
    
    // Simulate LLM parsing delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Mock parsing result based on input
    const mockResult: OptimizationRequest = {
      run_date: "2024-01-15",
      vehicles: ["TRK01", "TRK02"],
      jobs: [
        {
          sector_id: "A",
          date: "2024-01-15",
          demand_kg: 300,
          tw_start: "09:00",
          tw_end: "12:00",
          priority: 2,
          lat: 35.9737,
          lon: 126.7414
        },
        {
          sector_id: "B", 
          date: "2024-01-15",
          demand_kg: 400,
          tw_start: "08:30",
          tw_end: "12:00",
          priority: 1,
          lat: 35.9502,
          lon: 126.7043
        }
      ]
    };
    
    setParsedResult(mockResult);
    onParsed(mockResult);
    setIsProcessing(false);
  };

  const exampleInput = `내일(1월 15일) 전기차 2대로 군산A구역과 B구역에 배송하고 싶어.
A구역은 300kg 배송하고 9시부터 12시까지 가능해.
B구역은 400kg이고 8시30분부터 12시까지야.
가장 친환경적인 경로로 최적화해줘.`;

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
                파싱 시뮬레이트
              </>
            )}
          </Button>
        </div>

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
          {!parsedResult ? (
            <div className="text-center py-8 text-muted-foreground">
              <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>자연어 입력 후 파싱 버튼을 클릭하세요</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Validation Status */}
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-green-600 font-medium">파싱 성공</span>
                <Badge variant="secondary" className="ml-auto">
                  {parsedResult.jobs.length}개 작업
                </Badge>
              </div>
              
              <Separator />
              
              {/* Parsed Data Summary */}
              <div className="space-y-3">
                <div>
                  <p className="text-sm font-medium mb-1">실행 날짜</p>
                  <Badge variant="outline">{parsedResult.run_date}</Badge>
                </div>
                
                <div>
                  <p className="text-sm font-medium mb-1">차량 ({parsedResult.vehicles.length}대)</p>
                  <div className="flex gap-1 flex-wrap">
                    {parsedResult.vehicles.map(vehicle => (
                      <Badge key={vehicle} variant="secondary">{vehicle}</Badge>
                    ))}
                  </div>
                </div>
                
                <div>
                  <p className="text-sm font-medium mb-2">작업 목록</p>
                  <div className="space-y-2 max-h-32 overflow-y-auto">
                    {parsedResult.jobs.map((job, index) => (
                      <div key={index} className="bg-muted p-2 rounded text-sm">
                        <div className="flex justify-between items-start mb-1">
                          <span className="font-medium">{job.sector_id}구역</span>
                          <Badge size="sm" variant="outline">{job.demand_kg}kg</Badge>
                        </div>
                        <p className="text-muted-foreground text-xs">
                          {job.tw_start} ~ {job.tw_end} | 우선순위: {job.priority}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              {/* JSON Code */}
              <details className="group">
                <summary className="cursor-pointer text-sm font-medium">원본 JSON 보기</summary>
                <pre className="mt-2 p-3 bg-slate-100 rounded text-xs overflow-x-auto">
{JSON.stringify(parsedResult, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}