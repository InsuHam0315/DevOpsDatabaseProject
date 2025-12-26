'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MapPin, MessageSquare, FileText } from 'lucide-react';
import { useStore } from '@/lib/store';
import { OptimizationRequest } from '@/lib/types';
import NaturalLanguageInput from '@/components/plan/natural-language-input';
import FormInput from '@/components/plan/form-input';

export default function PlanPage() {
  const router = useRouter();
  const { runOptimization } = useStore();
  const [parsedRequest, setParsedRequest] = useState<OptimizationRequest | null>(null);

  const handleOptimize = async (request: OptimizationRequest) => {
    await runOptimization(request);
    router.push('/routes');
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
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
              <NaturalLanguageInput onParsed={setParsedRequest} />
              
              {parsedRequest && (
                <div className="mt-6 pt-6 border-t">
                  <div className="flex justify-center">
                    <button
                      onClick={() => handleOptimize(parsedRequest)}
                      className="px-8 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
                    >
                      최적화 실행
                    </button>
                  </div>
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="form" className="mt-6">
              <FormInput onSubmit={handleOptimize} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}