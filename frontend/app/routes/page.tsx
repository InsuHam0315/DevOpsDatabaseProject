// frontend/app/routes/page.tsx
'use client';
import { useState, useEffect } from 'react'; // useEffect 추가
import { useSearchParams } from 'next/navigation'; // useSearchParams 추가
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Route, Car, MapPin, Clock, Zap, TrendingDown, Settings, Brain, BarChart3, Timer, Fuel, Loader2, AlertCircle } from 'lucide-react'; // Loader2, AlertCircle 추가
// import { useStore } from '@/lib/store'; // 💡 직접 API 호출하므로 제거 가능 또는 선택적 사용
import KakaoMapPlaceholder from '@/components/ui/kakao-map-placeholder';
// 💡 결과 데이터 타입을 import
import { Route as RouteType, KPIs, Vehicle } from '@/lib/types';
import { useRouter } from 'next/navigation';

// 💡 백엔드 API 기본 URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000';

// 💡 API 응답 타입 정의 (필요시 lib/types.ts로 이동)
interface RouteResultResponse {
  run_id: string;
  kpis: KPIs;
  llm_explanation: string;
  routes: RouteType[];
  // 필요시 vehicles, sectors 정보도 포함 가능
}

export default function RoutesPage() {
  const router = useRouter(); // router 객체 초기화
  // const { routes: storeRoutes, kpis: storeKpis, vehicles: storeVehicles } = useStore(); // 💡 제거 또는 기본값으로 사용
  const searchParams = useSearchParams(); // URL 파라미터 접근
  const runId = searchParams.get('run_id'); // run_id 가져오기

  // 💡 API 결과 상태 관리
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultData, setResultData] = useState<RouteResultResponse | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]); // 💡 차량 정보 상태 추가 (API에서 받거나 store에서 가져옴)

  // 💡 시나리오 관련 상태 (기존과 동일)
  const [showScenarioDialog, setShowScenarioDialog] = useState(false);
  const [scenarioSettings, setScenarioSettings] = useState({
    extra_vehicle: false,
    extend_time_window: false,
    priority_weight: 1.0
  });

  // 💡 runId 변경 시 API 호출
  useEffect(() => {
    // 💡 Zustand store에서 차량 정보 가져오기 (API에서 함께 주지 않는 경우)
    // const { vehicles: initialVehicles } = useStore.getState();
    // setVehicles(initialVehicles);

    if (runId) {
      setLoading(true);
      setError(null);
      fetch(`${API_BASE_URL}/api/get-results/${runId}`)
        .then(async (res) => {
          if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.details || `결과 조회 실패 (${res.status})`);
          }
          return res.json();
        })
        .then((data: RouteResultResponse) => {
          setResultData(data);
          // 💡 API 응답에 차량 정보가 포함되지 않으면 store에서 가져온 것을 사용
          // 여기서는 예시로 API 응답에 없다고 가정하고 store의 mock data 사용
          const { vehicles: mockVehicles } = require('@/lib/mock-data'); // 실제로는 store에서 가져오는 것이 좋음
          setVehicles(mockVehicles);
        })
        .catch((err: any) => {
          console.error("결과 조회 오류:", err);
          setError(err.message || "결과를 불러오는 중 오류가 발생했습니다.");
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setError("조회할 실행 ID(run_id)가 없습니다.");
      setLoading(false);
    }
  }, [runId]); // runId가 변경될 때마다 실행

  // 💡 로딩 상태 표시
  if (loading) {
    return (
      <div className="container mx-auto py-8 flex justify-center items-center min-h-[calc(100vh-theme(space.14))]">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
        <p className="ml-4 text-muted-foreground">결과 데이터를 불러오는 중...</p>
      </div>
    );
  }

  // 💡 오류 상태 표시
  if (error || !resultData) {
    return (
       <div className="container mx-auto py-8 text-center min-h-[calc(100vh-theme(space.14))] flex flex-col justify-center items-center">
         <AlertCircle className="w-12 h-12 text-destructive mb-4" />
         <h2 className="text-xl font-semibold mb-2">오류 발생</h2>
         <p className="text-muted-foreground">{error || "결과 데이터를 불러올 수 없습니다."}</p>
         <Button variant="outline" className="mt-6" onClick={() => router.push('/plan')}>
           계획 페이지로 돌아가기
         </Button>
       </div>
    );
  }

  // 💡 resultData에서 KPI 및 경로 정보 사용
  const { kpis, routes, llm_explanation } = resultData;

  // KPI 카드 데이터 생성 (resultData 기반)
   const kpiCards = [
     {
       title: '총 주행거리',
       // 💡 kpis.total_distance_km이 null이나 undefined일 수 있으므로 기본값 0 처리
       value: `${(kpis.total_distance_km || 0).toFixed(1)}km`,
       icon: Route,
       color: 'text-blue-600',
       bgColor: 'bg-blue-50'
     },
     {
       title: '총 CO₂ 배출량',
       value: `${(kpis.total_co2_kg || 0).toFixed(2)}kg`, // kg 단위 사용
       icon: Zap,
       color: 'text-green-600',
       bgColor: 'bg-green-50'
     },
     {
       title: '총 소요시간',
       value: `${Math.floor((kpis.total_time_min || 0) / 60)}시간 ${(kpis.total_time_min || 0) % 60}분`,
       icon: Timer,
       color: 'text-purple-600',
       bgColor: 'bg-purple-50'
     },
     {
       title: '절감율',
       value: `${(kpis.saving_percent || 0).toFixed(1)}%`,
       icon: TrendingDown,
       color: 'text-emerald-600',
       bgColor: 'bg-emerald-50'
     }
   ];


  // ... (시나리오 관련 함수는 동일) ...
  const handleScenarioChange = () => {
     // Mock scenario recalculation
     setShowScenarioDialog(false);
     // In real app, would trigger new optimization with scenario params
     // 여기서는 임시로 alert 표시
     alert("시나리오 변경 기능은 아직 구현되지 않았습니다.");
   };


  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* ... (Header 부분 동일) ... */}
       <div className="text-center space-y-4">
         <div className="flex items-center justify-center gap-3">
           <Route className="w-8 h-8 text-blue-600" />
           <h1 className="text-3xl font-bold">경로 결과</h1>
           {/* 💡 Run ID 표시 */}
           <Badge variant="outline" className="text-sm">{runId}</Badge>
         </div>
         <p className="text-muted-foreground">
           최적화된 경로와 성과 지표를 확인하고 대안 시나리오를 비교해보세요.
         </p>
       </div>

      {/* KPI Cards (resultData 기반으로 렌더링) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((kpi) => (
          <Card key={kpi.title}>
            {/* ... (KPI 카드 내용은 동일) ... */}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ... (Map 섹션은 동일) ... */}
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
                 // 💡 실제 경로 데이터를 전달하도록 수정 가능 (KakaoMapPlaceholder 구현에 따라)
                 // routesData={routes}
               />
             </CardContent>
           </Card>
         </div>

        {/* Route Details Section */}
        <div className="space-y-6">
          {/* Vehicle Routes (resultData 기반) */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Car className="w-5 h-5" />
                차량별 경로 ({routes.length}대)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* 💡 경로가 없을 경우 메시지 표시 */}
              {routes.length === 0 ? (
                <p className="text-muted-foreground text-center py-4">
                  (실제 최적화가 수행되지 않아 경로 정보가 없습니다)
                </p>
              ) : (
                <Accordion type="single" collapsible className="space-y-2">
                  {routes.map((route) => {
                    // 💡 vehicles 상태에서 차량 정보 찾기
                    const vehicle = vehicles.find(v => v.id === route.vehicle_id);
                    // ... (Accordion 내용은 동일하나, route와 vehicle 데이터를 resultData에서 가져옴) ...
                     return (
                      <AccordionItem key={route.vehicle_id} value={route.vehicle_id}>
                        {/* ... (AccordionTrigger 내용 동일) ... */}
                          <AccordionTrigger className="hover:no-underline">
                           <div className="flex items-center justify-between w-full mr-4">
                             <div className="flex items-center gap-3">
                               <Badge variant="secondary">{route.vehicle_id}</Badge>
                               <span className="text-sm text-muted-foreground">
                                 {vehicle?.type || '정보 없음'} {/* vehicle 정보 없을 경우 대비 */}
                               </span>
                             </div>
                             <div className="flex items-center gap-4 text-sm text-muted-foreground">
                               <span>{(route.total_distance_km || 0).toFixed(1)}km</span>
                               <span>{(route.total_co2_kg || 0).toFixed(2)}kg CO₂</span>
                             </div>
                           </div>
                         </AccordionTrigger>
                        <AccordionContent>
                          <div className="space-y-3 pl-4">
                            {route.steps.map((step, index) => (
                              // ... (Step 내용 동일) ...
                               <div key={index} className="flex items-center gap-4 p-3 bg-muted rounded-lg">
                                 <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm font-medium">
                                   {index + 1}
                                 </div>
                                 <div className="flex-1">
                                   <p className="font-medium">{step.sector_id}구역</p> {/* sector_id 사용 */}
                                   <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                     <span className="flex items-center gap-1">
                                       <Clock className="w-3 h-3" />
                                       {step.arrival_time || '??:??'} ~ {step.departure_time || '??:??'}
                                     </span>
                                     <span className="flex items-center gap-1">
                                       <Route className="w-3 h-3" />
                                       {(step.distance_km || 0).toFixed(1)}km
                                     </span>
                                     <span className="flex items-center gap-1">
                                       <Fuel className="w-3 h-3" />
                                       {(step.co2_kg || 0).toFixed(2)}kg
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
              )}
            </CardContent>
          </Card>

          {/* LLM Explanation (resultData 기반) */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5" />
                결과 설명 (LLM)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 💡 llm_explanation을 표시 */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-blue-900 whitespace-pre-wrap"> {/* whitespace-pre-wrap 추가 */}
                  {llm_explanation || "LLM 분석 결과를 불러올 수 없습니다."}
                </p>
              </div>
              {/* 💡 기존 하드코딩된 설명 제거 */}
            </CardContent>
          </Card>

          {/* ... (Alternative Scenarios 부분은 동일) ... */}
           <div className="flex gap-3">
             <Dialog open={showScenarioDialog} onOpenChange={setShowScenarioDialog}>
               {/* ... (DialogTrigger, DialogContent 등 동일) ... */}
               <DialogTrigger asChild>
                 <Button variant="outline" className="flex items-center gap-2">
                   <Settings className="w-4 h-4" />
                   대안 시나리오
                 </Button>
               </DialogTrigger>
               <DialogContent>
                 <DialogHeader>
                   <DialogTitle>시나리오 설정</DialogTitle>
                 </DialogHeader>
                 <div className="space-y-4">
                   {/* ... (시나리오 설정 폼 동일) ... */}
                   <Button onClick={handleScenarioChange} className="w-full">
                     시나리오 적용 (미구현)
                   </Button>
                 </div>
               </DialogContent>
             </Dialog>

             <Button variant="outline" className="flex items-center gap-2" disabled> {/* 상세 분석 비활성화 예시 */}
               <BarChart3 className="w-4 h-4" />
               상세 분석 (미구현)
             </Button>
           </div>
        </div>
      </div>
    </div>
  );
}