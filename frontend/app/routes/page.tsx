'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Route, Car, MapPin, Clock, Zap, TrendingDown, Brain, Timer, Fuel } from 'lucide-react';
import { useStore } from '@/lib/store';
import KakaoMapPlaceholder from '@/components/ui/kakao-map-placeholder';

export default function RoutesPage() {
  const { routes, kpis, vehicles, batchResults } = useStore();

  const kpiCards = [
    {
      title: '총 주행거리',
      value: `${kpis.total_distance_km}km`,
      icon: Route,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      title: '총 CO₂ 배출량',
      value: `${kpis.total_co2_kg}kg`,
      icon: Zap,
      color: 'text-green-600', 
      bgColor: 'bg-green-50'
    },
    {
      title: '총 소요시간',
      value: `${Math.floor(kpis.total_time_min / 60)}시간 ${kpis.total_time_min % 60}분`,
      icon: Timer,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    },
    {
      title: '절감율',
      value: `${kpis.saving_percent}%`,
      icon: TrendingDown,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50'
    }
  ];

  const handleScenarioChange = () => {
    // Mock scenario recalculation
    setShowScenarioDialog(false);
    // In real app, would trigger new optimization with scenario params
  };

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <Route className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold">경로 결과</h1>
        </div>
        <p className="text-muted-foreground">
          최적화된 경로와 성과 지표를 확인하고 대안 시나리오를 비교해보세요.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((kpi) => (
          <Card key={kpi.title}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{kpi.title}</p>
                  <p className="text-2xl font-bold">{kpi.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${kpi.bgColor}`}>
                  <kpi.icon className={`w-6 h-6 ${kpi.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Map Section */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                경로 지도
              </CardTitle>
            </CardHeader>
            <CardContent>
              <KakaoMapPlaceholder 
                className="h-[500px]"
                showControls={true}
              />
            </CardContent>
          </Card>
        </div>

        {/* Route Details Section */}
        <div className="space-y-6">
          {/* Vehicle Routes */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Car className="w-5 h-5" />
                차량별 경로 ({routes.length}대)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="space-y-2">
                {routes.map((route) => {
                  const vehicle = vehicles.find(v => v.id === route.vehicle_id);
                  return (
                    <AccordionItem key={route.vehicle_id} value={route.vehicle_id}>
                      <AccordionTrigger className="hover:no-underline">
                        <div className="flex items-center justify-between w-full mr-4">
                          <div className="flex items-center gap-3">
                            <Badge variant="secondary">{route.vehicle_id}</Badge>
                            <span className="text-sm text-muted-foreground">
                              {vehicle?.type}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>{route.total_distance_km}km</span>
                            <span>{route.total_co2_kg}kg CO₂</span>
                          </div>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-3 pl-4">
                          {route.steps.map((step, index) => (
                            <div key={index} className="flex items-center gap-4 p-3 bg-muted rounded-lg">
                              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm font-medium">
                                {index + 1}
                              </div>
                              <div className="flex-1">
                                <p className="font-medium">{step.sector_id}구역</p>
                                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                  <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {step.arrival_time} ~ {step.departure_time}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Route className="w-3 h-3" />
                                    {step.distance_km}km
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Fuel className="w-3 h-3" />
                                    {step.co2_kg}kg
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            </CardContent>
          </Card>
{/*------------------------------------------------------------------------------------- LLM 결과표출 추가로 인한 수정 */}     
          {/* LLM Explanation */}
          <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5" />
            결과 설명 (LLM)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">

          {/* [수정] 하드코딩된 <div> 3개를 지우고 아래 로직으로 대체합니다. */}

          {batchResults && batchResults.length > 0 ? (
            // batchResults 배열을 순회 (여러 Run 결과가 있을 수 있으므로)
            batchResults.map((result) => (
              <div 
                key={result.run_id} 
                className="bg-blue-50 p-4 rounded-lg prose prose-sm max-w-none text-blue-900 whitespace-pre-line"
              >
                {result.status === 'success' ? (
                  <>
                    <strong className="text-blue-900">
                      [Run ID: ...{result.run_id.slice(-6)}] 분석 결과:
                    </strong>
                    <p>{result.llm_explanation || "LLM 분석 텍스트가 없습니다."}</p>
                  </>
                ) : (
                  <>
                    <strong className="text-red-700">
                      [Run ID: ...{result.run_id.slice(-6)}] 실행 실패:
                    </strong>
                    <p className="text-red-700">{result.message || "알 수 없는 오류"}</p>
                  </>
                )}
              </div>
            ))
          ) : (
            // store에 결과가 없을 경우
            <p className="text-sm text-gray-500 italic">
              표시할 LLM 분석 결과가 없습니다.
            </p>
          )}

        </CardContent>
      </Card>
      {/*------------------------------------------------------------------------------------- LLM 결과표출 추가로 인한 수정 */}    
        </div>
      </div>
    </div>
  );
}