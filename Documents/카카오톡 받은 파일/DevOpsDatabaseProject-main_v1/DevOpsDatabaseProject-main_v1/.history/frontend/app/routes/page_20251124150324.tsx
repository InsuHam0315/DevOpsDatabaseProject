'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Route, MapPin, Zap, TrendingDown, Brain, Timer } from 'lucide-react';
import { useStore } from '@/lib/store';
import KakaoMapPlaceholder from '@/components/ui/kakao-map-placeholder';
import VehicleRoutesCard from '@/components/routes/vehicle-routes-card';

export default function RoutesPage() {
  const { kpis, batchResults, vehicleRoutes } = useStore();

  // ✅ vehicleRoutes가 undefined여도 항상 []로 처리
  const safeVehicleRoutes = vehicleRoutes ?? [];

  const getNumericValue = (value: unknown): number | null => {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    return null;
  };

  const totalDistanceKm = getNumericValue(kpis?.total_distance_km);
  const totalCo2Kg = getNumericValue(kpis?.total_co2_kg);
  const totalTimeMin = getNumericValue(kpis?.total_time_min);
  const savingPercent = getNumericValue(kpis?.saving_percent);

  const totalHours =
    totalTimeMin !== null ? Math.floor(totalTimeMin / 60) : null;
  const minutesRaw = totalTimeMin !== null ? totalTimeMin % 60 : null;
  const formattedMinutes =
    minutesRaw !== null ? (Math.round(minutesRaw * 10) / 10).toFixed(1) : null;

  const totalDistanceDisplay =
    totalDistanceKm !== null ? `${totalDistanceKm.toFixed(1)} km` : '– km';
  const totalCo2Display =
    totalCo2Kg !== null ? `${totalCo2Kg.toFixed(1)} kg` : '– kg';
  const totalTimeDisplay =
    totalHours !== null && formattedMinutes !== null
      ? `${totalHours}시간 ${formattedMinutes}분`
      : '– 분';
  const savingPercentDisplay =
    savingPercent !== null ? `${savingPercent.toFixed(1)}%` : '– %';

  const normalizeLLMExplanation = (text?: string | null) => {
    if (!text) return 'LLM 분석 응답이 없습니다.';
    const prefix = 'ELO 경로는';
    const patterns = [
      /ELO\s*추천\s*경로/gi,
      /Eco\s*Optimal\s*Route/gi,
      /Eco\s*Logistics\s*Optimizer\s*경로/gi,
      /추천\s*경로/gi,
      /추천\s*루트/gi
    ];
    let normalized = text.trim();
    patterns.forEach((pattern) => {
      normalized = normalized.replace(pattern, prefix);
    });
    if (!normalized.includes(prefix)) {
      normalized = `${prefix} ${normalized}`;
    }
    return normalized;
  };

  const kpiCards = [
    {
      title: '총 주행거리',
      value: totalDistanceDisplay,
      icon: Route,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      title: '총 CO₂ 배출량',
      value: totalCo2Display,
      icon: Zap,
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      title: '총 소요시간',
      value: totalTimeDisplay,
      icon: Timer,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    },
    {
      title: '절감률',
      value: savingPercentDisplay,
      icon: TrendingDown,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50'
    }
  ];

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
                  <p className="text-sm font-medium text-muted-foreground">
                    {kpi.title}
                  </p>
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
                // ✅ 안전한 vehicleRoutes 사용
                routes={safeVehicleRoutes}
              />
            </CardContent>
          </Card>
        </div>

        {/* Route Details Section */}
        <div className="space-y-6">
          {/* ✅ 안전한 vehicleRoutes 사용 */}
          <VehicleRoutesCard routes={safeVehicleRoutes} />

          {/* LLM Explanation */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5" />
                결과 설명 (LLM)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {batchResults && batchResults.length > 0 ? (
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
                        <p>{normalizeLLMExplanation(result.llm_explanation)}</p>
                      </>
                    ) : (
                      <>
                        <strong className="text-red-700">
                          [Run ID: ...{result.run_id.slice(-6)}] 실행 실패:
                        </strong>
                        <p className="text-red-700">
                          {result.message || '알 수 없는 오류'}
                        </p>
                      </>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 italic">
                  표시할 LLM 분석 결과가 없습니다.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
