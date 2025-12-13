'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Route as RouteIcon, MapPin, Zap, TrendingDown, Brain, Timer } from 'lucide-react';
import { useStore } from '@/lib/store';
import KakaoMapPlaceholder from '@/components/ui/kakao-map-placeholder';
import VehicleRoutesCard from '@/components/routes/vehicle-routes-card';

type SummaryLike = Record<string, any> | undefined | null;

const toNumber = (value: unknown, divider = 1): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value / divider;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    if (Number.isFinite(parsed)) return parsed / divider;
  }
  return null;
};

const normalizeSummary = (summary: SummaryLike) => {
  if (!summary) return { distance: null, co2kg: null, time: null };
  const src = (summary as any).summary ?? summary;
  return {
    distance:
      toNumber(src?.total_distance_km) ??
      toNumber(src?.total_distance) ??
      toNumber(src?.distance_km) ??
      toNumber(src?.distance),
    co2kg:
      toNumber(src?.total_co2_kg) ??
      toNumber(src?.co2_kg) ??
      toNumber(src?.total_co2_g, 1000) ??
      toNumber(src?.co2_g, 1000),
    time: toNumber(src?.total_time_min) ?? toNumber(src?.total_time)
  };
};

const formatTime = (minutes: number | null) => {
  if (minutes === null) return '데이터 없음';
  const hours = Math.floor(minutes / 60);
  const mins = Math.round((minutes % 60) * 10) / 10;
  return `${hours}시간 ${mins.toFixed(1)}분`;
};

export default function RoutesPage() {
  const { kpis, batchResults, vehicleRoutes } = useStore();
  const safeVehicleRoutes = Array.isArray(vehicleRoutes) ? vehicleRoutes : [];

  const latestOptimization =
    Array.isArray(batchResults) && batchResults.length > 0 ? batchResults[0]?.optimization_result : null;
  const comparison = latestOptimization?.comparison;
  const summaries: any[] = Array.isArray(latestOptimization?.results) ? latestOptimization.results : [];

  const findSummaryByName = (name?: string | null): SummaryLike => {
    if (!name) return null;
    const target = summaries.find((s) => {
      const n = (s?.route_option_name ?? s?.route_name ?? '').toLowerCase();
      return n === name.toLowerCase();
    });
    return target ?? null;
  };

  const recommendedName =
    comparison?.recommended_route ?? summaries[0]?.route_option_name ?? summaries[0]?.route_name ?? null;
  const baselineName =
    comparison?.baseline_route ??
    summaries.find((s) => (s?.route_option_name ?? s?.route_name) !== recommendedName)?.route_option_name ??
    null;

  const recommendedSummaryRaw = findSummaryByName(recommendedName) ?? summaries[0] ?? null;
  const baselineSummaryRaw = findSummaryByName(baselineName);

  const recommendedTotals = normalizeSummary(recommendedSummaryRaw);
  const baselineTotals = normalizeSummary(baselineSummaryRaw);

  const totalDistanceKm =
    recommendedTotals.distance ?? toNumber(kpis?.total_distance_km) ?? toNumber(kpis?.total_distance);
  const totalCo2Kg =
    recommendedTotals.co2kg ??
    (typeof recommendedTotals.co2kg === 'number' ? recommendedTotals.co2kg : null) ??
    toNumber(kpis?.total_co2_kg);
  const totalTimeMin = recommendedTotals.time ?? toNumber(kpis?.total_time_min);

  const co2SavingPct = toNumber(comparison?.co2_saving_pct) ?? toNumber(kpis?.saving_percent);
  const co2SavingG = toNumber(comparison?.co2_saving_g);
  const distanceDiffPct = toNumber(comparison?.distance_diff_pct);
  const distanceDiffKm = toNumber(comparison?.distance_diff_km);

  const baselineProvider =
    comparison?.baseline_provider ??
    (baselineName ? (baselineName.toLowerCase().includes('ors') ? 'ors' : 'kakao') : null);
  const comparisonLabelPrefix =
    baselineProvider === 'ors' ? 'ORS 대비' : baselineProvider === 'kakao' ? 'Kakao 대비' : '비교 기준';

  const totalDistanceDisplay =
    totalDistanceKm !== null ? `${(totalDistanceKm ?? 0).toFixed(1)} km` : '데이터 없음';
  const totalCo2Display =
    totalCo2Kg !== null ? `${(totalCo2Kg ?? 0).toFixed(1)} kg` : '데이터 없음';
  const totalTimeDisplay = formatTime(totalTimeMin);

  const savingPercentDisplay =
    co2SavingPct !== null && co2SavingPct !== undefined ? `${co2SavingPct.toFixed(1)}%` : '데이터 없음';
  const distanceIncreaseDisplay =
    distanceDiffPct !== null && distanceDiffPct !== undefined
      ? `${distanceDiffPct.toFixed(1)}%${distanceDiffKm !== null ? ` (${distanceDiffKm.toFixed(2)} km)` : ''}`
      : '데이터 없음';

  const normalizeLLMExplanation = (text?: string | null) => {
    if (!text) return 'LLM 분석 결과가 아직 없습니다.';
    const prefix = 'ELO 추천 경로';
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
      icon: RouteIcon,
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
      title: '총 소요 시간',
      value: totalTimeDisplay,
      icon: Timer,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    },
    {
      title: `${comparisonLabelPrefix} CO₂ 절감율`,
      value:
        co2SavingG !== null && co2SavingG !== undefined
          ? `${savingPercentDisplay} (${(co2SavingG / 1000).toFixed(2)} kg)`
          : savingPercentDisplay,
      icon: TrendingDown,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50'
    },
    {
      title: `${comparisonLabelPrefix} 거리 증감율`,
      value: distanceIncreaseDisplay,
      icon: MapPin,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50'
    }
  ];

  return (
    <div className="container mx-auto py-8 space-y-8">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <RouteIcon className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold">경로 결과</h1>
        </div>
        <p className="text-muted-foreground">
          최적화된 경로 결과와 LLM 분석 리포트를 확인할 수 있습니다.
        </p>
      </div>

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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                경로 지도
              </CardTitle>
            </CardHeader>
            <CardContent>
              <KakaoMapPlaceholder className="h-[500px]" showControls routes={safeVehicleRoutes} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <VehicleRoutesCard routes={safeVehicleRoutes} />

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
                          [Run ID: ...{result.run_id.slice(-6)}] 분석 결과
                        </strong>
                        <p>{normalizeLLMExplanation(result.llm_explanation)}</p>
                      </>
                    ) : (
                      <>
                        <strong className="text-red-700">
                          [Run ID: ...{result.run_id.slice(-6)}] 실행 실패
                        </strong>
                        <p className="text-red-700">
                          {result.message || '알 수 없는 오류가 발생했습니다.'}
                        </p>
                      </>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 italic">아직 LLM 분석 결과가 없습니다.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
