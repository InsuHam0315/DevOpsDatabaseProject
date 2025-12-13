'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Brain, FileText, CircleCheck as CheckCircle, CircleAlert as AlertCircle } from 'lucide-react';
import type { Job } from '@/lib/types';

interface NaturalLanguageInputProps {
  onParsed: (request: ParsedResult | null) => void;
}

interface ParsedRun {
  run_date?: string;
  depot_address?: string | null;
  depot_lat?: number | null;
  depot_lon?: number | null;
  natural_language_input?: string;
  vehicle_model?: string;
  jobs: Job[];
}

interface ParsedResult {
  run_date?: string;
  vehicles?: string[];
  runs: ParsedRun[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000';

export default function NaturalLanguageInput({ onParsed }: NaturalLanguageInputProps) {
  const [input, setInput] = useState('');
  const [parsedResult, setParsedResult] = useState<ParsedResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleParseInput = async () => {
    if (!input.trim()) return;

    setIsProcessing(true);
    setError(null);
    setParsedResult(null);
    onParsed(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/parse-natural-language`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ natural_input: input })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.details || `API 오류 (${response.status})`);
      }

      const result = (await response.json()) as ParsedResult;
      if (!Array.isArray(result.runs)) result.runs = [];
      setParsedResult(result);
      onParsed(result);
    } catch (err: any) {
      console.error('자연어 파싱 오류:', err);
      setError(err.message || '자연어 입력을 처리하는 동안 오류가 발생했습니다.');
      setParsedResult(null);
      onParsed(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const exampleInput = `오늘은 부산82가1234 차량으로 오전 6시부터 12시 30분까지
군산 국제여객터미널에서 출발해서 부산신항으로 15000kg 배송할 거야.

내일은 인천88사5678 차량으로 오전 8시부터 12시까지
부산신항에서 출발해서 대전 신세계백화점으로 10000kg 배송할 거야.

각 운행은 차량 적재 한도를 넘지 않도록 하고, 각 운행별로 지정된 시간 안에만 도착하면 돼.
전체 CO2 배출량을 최소화하는 방향으로 경로를 계획해 줘.`;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Input Section */}
      <div className="space-y-4">
        <div className="space-y-2">
          <div className="space-y-1">
            <label htmlFor="natural-input" className="text-sm font-medium">
              자연어 입력
            </label>
            <p className="text-xs text-muted-foreground leading-relaxed">
              아래 정보를 모두 포함해서 자연스럽게 작성해 주세요. 한 문장에는
              <strong> 한 번의 운행(출발지 → 도착지)</strong>만 넣는 것을 권장합니다.
            </p>
            <ul className="text-xs text-muted-foreground list-disc list-inside space-y-0.5">
              <li>언제: 오늘/내일/또는 날짜 (예: 2025-12-10)</li>
              <li>어느 차량: 등록된 차량 번호 (예: 부산82가1234, 인천88사5678)</li>
              <li>운행 시간: 몇 시부터 몇 시까지 (예: 오전 6시부터 12시 30분까지)</li>
              <li>출발지/도착지: Kakao 지도에서 검색 가능한 실제 주소/장소명</li>
              <li>물량: 배송 중량 kg (예: 15000kg)</li>
            </ul>
          </div>
          <Textarea
            id="natural-input"
            placeholder="예) 오늘은 부산82가1234 차량으로 오전 6시부터 12시 30분까지 군산 국제여객터미널에서 출발해서 부산신항으로 15000kg 배송할 거야."
            className="min-h-[200px] resize-none"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
        </div>

        <div className="flex gap-2">
          <Button onClick={() => setInput(exampleInput)} variant="outline" size="sm">
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

        {input && !error && (
          <div className="text-sm text-muted-foreground bg-muted p-3 rounded-lg">
            <p className="font-medium mb-1">입력 설명</p>
            <p>LLM이 자연어를 분석해 경로 계획용 JSON 구조로 변환합니다.</p>
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
          {isProcessing ? (
            <div className="text-center py-8 text-muted-foreground">
              <div className="w-8 h-8 mx-auto border-4 border-primary border-t-transparent animate-spin rounded-full mb-3" />
              <p>LLM에 분석을 요청하는 중입니다...</p>
            </div>
          ) : !parsedResult && !error ? (
            <div className="text-center py-8 text-muted-foreground">
              <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>자연어를 입력한 뒤 &quot;요청&quot; 버튼을 눌러 주세요.</p>
            </div>
          ) : error ? (
            <div className="text-center py-8 text-destructive">
              <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>파싱 과정에서 오류가 발생했습니다.</p>
              <p className="text-xs mt-1">{error}</p>
            </div>
          ) : parsedResult ? (
            (() => {
              const totalJobCount =
                parsedResult.runs?.reduce((acc, run) => acc + (run.jobs?.length || 0), 0) || 0;

              return (
                <div className="space-y-4">
                  {/* Validation Status */}
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <span className="text-green-600 font-medium">파싱 성공</span>
                    <Badge variant="secondary" className="ml-auto">
                      {totalJobCount}개 작업 / {parsedResult.runs.length}개 운행
                    </Badge>
                  </div>
                  <Separator />

                  {/* Runs List */}
                  <div>
                    <p className="text-sm font-medium mb-2">운행별 작업 목록</p>
                    <div className="space-y-3 max-h-40 overflow-y-auto p-1">
                      {parsedResult.runs.map((run, runIndex) => (
                        <div key={runIndex} className="bg-muted p-2 rounded">
                          <p
                            className="text-xs font-semibold text-muted-foreground truncate"
                            title={run.depot_address || undefined}
                          >
                            출발 {runIndex + 1}: {run.depot_address || '출발지 미지정'}
                          </p>
                          <Separator className="my-1.5" />
                          <div className="space-y-1">
                            {run.jobs.map((job, jobIndex) => (
                              <div key={jobIndex} className="text-sm">
                                <div className="flex justify-between items-start">
                                  <span className="font-medium" title={job.address}>
                                    {job.address || job.sector_id || '도착지 미지정'}
                                  </span>
                                  <Badge variant="outline">{job.demand_kg}kg</Badge>
                                </div>
                              </div>
                            ))}
                            {run.jobs.length === 0 && (
                              <p className="text-xs text-center text-muted-foreground">
                                이 운행에 등록된 작업이 없습니다.
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Raw JSON View */}
                  <details className="group">
                    <summary className="cursor-pointer text-sm font-medium">
                      원본 JSON 보기
                    </summary>
                    <pre className="mt-2 p-3 bg-slate-100 rounded text-xs overflow-x-auto">
                      {JSON.stringify(parsedResult, null, 2)}
                    </pre>
                  </details>
                </div>
              );
            })()
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

