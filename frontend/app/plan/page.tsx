'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MapPin, MessageSquare, FileText, AlertCircle } from 'lucide-react'; // AlertCircle 추가
// import { useStore } from '@/lib/store'; // 💡 runOptimization은 직접 호출하지 않으므로 제거 가능
import { OptimizationRequest, BatchResult } from '@/lib/types'; //LLM 결과표출 추가로 인한 수정
import NaturalLanguageInput from '@/components/plan/natural-language-input';
import FormInput from '@/components/plan/form-input';
import { useStore } from '@/lib/store'

// 💡 알림(Toast) 사용을 위해 import (선택 사항)
import { toast } from 'sonner'; //LLM 결과표출 추가로 인한 수정

// 💡 백엔드 API 기본 URL (natural-language-input.tsx와 동일하게 사용)
// 기본값을 로컬호스트 대신 개발 서버 네트워크 IP로 설정하여 다른 디바이스에서 접근 가능하게 함
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000';

export default function PlanPage() {
  const router = useRouter();
  // const { runOptimization } = useStore(); // 💡 제거
  // parsedResult는 NaturalLanguageInput에서 전달되는 ParsedResult를 그대로 받습니다.
  const [parsedRequest, setParsedRequest] = useState<any | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false); // 💡 제출 로딩 상태
  const [submitError, setSubmitError] = useState<string | null>(null); // 💡 제출 오류 상태
  const [isOptimizing, setIsOptimizing] = useState(false); //LLM 결과표출 추가로 인한 수정
  const setBatchResults = useStore((state) => state.setBatchResults); //LLM 결과표출 추가로 인한 수정
  // 💡 폼 입력에서도 사용할 수 있도록 onParsed 핸들러를 분리
  const handleParsed = (request: any | null) => {
    setParsedRequest(request);
    setSubmitError(null); // 새로운 파싱 결과 받으면 오류 초기화
  };

  // 💡 API 호출 함수 (폼 입력에서도 사용 가능하도록 수정)
  const handleOptimize = async (request: any | null) => {
    if (!request) {
      setSubmitError('파싱된 요청이 없습니다.');
      return;
    }

    setIsOptimizing(true);
    setSubmitError(null);
    toast.loading('최적화가 시작되었습니다. 잠시만 기다려주세요...', {
      id: 'optimization-toast',
    });
    try {
      // 💡 백엔드 /api/save-plan-and-analyze 호출
      const response = await fetch(`${API_BASE_URL}/api/save-plan-and-analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // request는 ParsedResult 구조(백엔드에서 기대하는 runs 포함)입니다.
        body: JSON.stringify(request),
      });
      //------------------------------------------------------------------------------------- LLM 결과표출 추가로 인한 수정
      if (response.ok) {
        // 성공 시
        const data: { message: string; batch_results: BatchResult[] } = await response.json();

        // 2단계에서 만든 store에 결과 저장
        setBatchResults(data.batch_results || []);

        toast.success('최적화 성공!', {
          id: 'optimization-toast',
          description: data.message || '결과 페이지로 이동합니다.',
        });

        router.push('/routes'); // 결과 페이지로 이동

      } else {
        // 실패 시
        const errorData = await response.json();
        throw new Error(errorData.details || `API 오류 (${response.status})`);
      }

    } catch (err: any) {
      console.error('최적화 요청 실패:', err);
      setSubmitError(err.message || '서버 오류가 발생했습니다.');
      toast.error('최적화 실패', {
        id: 'optimization-toast',
        description: err.message,
      });
    } finally {
      setIsOptimizing(false); // ⬅️ [수정] isSubmitting 대신 isOptimizing 사용
    }
  };
  //-------------------------------------------------------------------------------------
  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* ... (Header는 동일) ... */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <MapPin className="w-8 h-8 text-green-600" />
          <h1 className="text-3xl font-bold">경로 계획</h1>
        </div>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          자연어로 배송 요구사항을 입력하거나 상세 폼을 통해 경로 최적화를 설정하세요.
          LLM이 여러분의 요구사항을 이해하고 최적의 친환경 경로를 제안합니다.
        </p>
      </div>

      <Card>
        {/* ... (CardHeader, TabsList는 동일) ... */}
        <CardHeader>
          <CardTitle className="text-xl">배송 계획 입력</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="natural" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="natural" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                자연어 입력
              </TabsTrigger>
              <TabsTrigger value="form" className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                폼 입력
              </TabsTrigger>
            </TabsList>

            <TabsContent value="natural" className="mt-6">
              {/* 💡 onParsed 핸들러 전달 */}
              <NaturalLanguageInput onParsed={handleParsed} />

              {/* 💡 parsedRequest가 있을 때만 버튼 표시 */}
              {parsedRequest && (
                <div className="mt-6 pt-6 border-t">
                  {/* 💡 제출 오류 메시지 표시 */}
                  {submitError && (
                    <div className="mb-4 text-sm text-destructive bg-destructive/10 p-3 rounded-lg flex items-center justify-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      {submitError}
                    </div>
                  )}
                  <div className="flex justify-center">
                    <button
                      onClick={() => handleOptimize(parsedRequest)}
                      // 💡 로딩 상태에 따라 비활성화 및 텍스트 변경
                      disabled={isOptimizing}
                      className="px-8 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {isOptimizing ? (
                        <>
                          <div className="w-4 h-4 border-2 border-current border-t-transparent animate-spin rounded-full" />
                          <span>처리 중...</span>
                        </>
                      ) : (
                        "최적화 실행" // 💡 버튼 텍스트 변경
                      )}
                    </button>
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="form" className="mt-6">
              {/* 💡 폼 입력 결과도 handleOptimize로 전달 */}
              <FormInput onSubmit={handleOptimize} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}