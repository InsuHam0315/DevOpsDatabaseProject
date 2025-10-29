'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Route, Car, MapPin, Clock, Zap, TrendingDown, Settings, Brain, ChartBar as BarChart3, Timer, Fuel } from 'lucide-react';
import { useStore } from '@/lib/store';
import KakaoMapPlaceholder from '@/components/ui/kakao-map-placeholder';

export default function RoutesPage() {
  const { routes, kpis, vehicles } = useStore();
  const [showScenarioDialog, setShowScenarioDialog] = useState(false);
  const [scenarioSettings, setScenarioSettings] = useState({
    extra_vehicle: false,
    extend_time_window: false,
    priority_weight: 1.0
  });

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

          {/* LLM Explanation */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5" />
                결과 설명 (LLM)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-blue-900">
                  🤖 <strong>최적화 분석:</strong> 총 2대의 차량으로 3개 섹터를 효율적으로 배송합니다. 
                  전기차(TRK01)를 우선 배치하여 CO₂ 배출량을 23.5% 절감했습니다.
                </p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <p className="text-sm text-green-900">
                  ⚡ <strong>친환경 효과:</strong> 기존 디젤 차량만 사용할 경우 대비 약 1.2kg의 CO₂를 절약합니다. 
                  이는 소나무 약 0.5그루가 1년간 흡수하는 양과 같습니다.
                </p>
              </div>
              <div className="bg-amber-50 p-4 rounded-lg">
                <p className="text-sm text-amber-900">
                  📈 <strong>최적화 포인트:</strong> 모든 시간창 제약을 만족하며, 
                  차량별 용량 활용률은 평균 85%로 효율적입니다.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Alternative Scenarios */}
          <div className="flex gap-3">
            <Dialog open={showScenarioDialog} onOpenChange={setShowScenarioDialog}>
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
                  <div>
                    <Label>추가 차량 투입</Label>
                    <Select 
                      value={scenarioSettings.extra_vehicle ? "true" : "false"}
                      onValueChange={(value) => setScenarioSettings(prev => ({ 
                        ...prev, extra_vehicle: value === "true" 
                      }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="false">현재 차량만 사용</SelectItem>
                        <SelectItem value="true">차량 +1대 추가</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>시간창 확대</Label>
                    <Select
                      value={scenarioSettings.extend_time_window ? "true" : "false"}
                      onValueChange={(value) => setScenarioSettings(prev => ({ 
                        ...prev, extend_time_window: value === "true" 
                      }))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="false">기본 시간창</SelectItem>
                        <SelectItem value="true">시간창 +2시간</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>우선순위 가중치</Label>
                    <Input
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="2.0"
                      value={scenarioSettings.priority_weight}
                      onChange={(e) => setScenarioSettings(prev => ({ 
                        ...prev, priority_weight: parseFloat(e.target.value) 
                      }))}
                    />
                  </div>
                  
                  <Button onClick={handleScenarioChange} className="w-full">
                    시나리오 적용
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            
            <Button variant="outline" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              상세 분석
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}