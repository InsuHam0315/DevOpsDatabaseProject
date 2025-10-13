// frontend/src/app/plan/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MapPin, MessageSquare, FileText } from 'lucide-react';
import NaturalLanguageInput from '@/components/plan/natural-language-input';
import FormInput from '@/components/plan/form-input';

// DB에 저장된 Plan 데이터의 타입을 정의합니다. (any로 단순화)
type PlanData = any;

export default function PlanPage() {
  const router = useRouter();
  const [parsedPlan, setParsedPlan] = useState<PlanData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header (기존과 동일) */}
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

      {/* Main Content */}
      <Card>
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
              <div className="grid grid-cols-2 gap-4">
                {/* 💡 자식에게 onParsed와 setIsLoading 함수를 props로 전달 */}
                <NaturalLanguageInput onParsed={setParsedPlan} setIsLoading={setIsLoading} />
                
                {/* 💡 입력 분석 Card를 부모 컴포넌트에서 직접 관리 */}
                <Card>
                  <CardHeader>
                    <CardTitle>입력 분석</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="p-4 bg-gray-100 rounded-md h-full overflow-auto text-sm">
                      {isLoading
                        ? "분석 및 저장 중..."
                        : parsedPlan
                          ? JSON.stringify({
                              ...parsedPlan,
                              vehicles: JSON.parse(parsedPlan.vehicles || '[]'),
                              jobs: JSON.parse(parsedPlan.jobs || '[]')
                            }, null, 2)
                          : "LLM이 자연어를 구조화된 JSON으로 변환합니다"
                      }
                    </pre>
                  </CardContent>
                </Card>
              </div>

              {/* 파싱된 데이터(parsedPlan)가 있을 때만 "최적화 실행" 버튼을 보여줌 */}
              {parsedPlan && (
                <div className="mt-6 pt-6 border-t">
                  <div className="flex justify-center">
                    <button
                      onClick={() => router.push(`/routes?planId=${parsedPlan.id}`)}
                      className="px-8 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
                    >
                      최적화 실행
                    </button>
                  </div>
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="form" className="mt-6">
              {/* <FormInput onSubmit={handleOptimize} /> */}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}