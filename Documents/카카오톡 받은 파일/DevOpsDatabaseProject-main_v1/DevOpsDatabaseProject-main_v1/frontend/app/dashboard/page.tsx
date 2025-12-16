'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ChartBar as BarChart3, TrendingUp, Filter, Eye, Download, Route as RouteIcon, Zap, Clock } from 'lucide-react';
import { useStore } from '@/lib/store';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

import Protected from '@/components/auth/Protected';

type WeeklyCo2Point = {
  date: string;
  co2_kg: number;
};

type VehicleDistancePoint = {
  vehicle_id: string;
  distance_km: number;
};

const formatRunDate = (value?: string) => {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

const calculateDateRange = (rangeKey: string) => {
  const end = new Date();
  const start = new Date(end);
  switch (rangeKey) {
    case 'month':
      start.setMonth(start.getMonth() - 1);
      break;
    case 'quarter':
      start.setMonth(start.getMonth() - 3);
      break;
    default:
      start.setDate(start.getDate() - 6);
  }
  const toISO = (date: Date) => date.toISOString().split('T')[0];
  return { fromDate: toISO(start), toDate: toISO(end) };
};

export default function DashboardPage() {
  const { dashboardRunHistory, vehicles, sectors, dashboardKpis } = useStore();
  const setDashboardData = useStore((s) => s.setDashboardData);
  const [dateRange, setDateRange] = useState('week');
  const [selectedVehicle, setSelectedVehicle] = useState('all');
  const [selectedSector, setSelectedSector] = useState('all');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);
  const [weeklyCo2Data, setWeeklyCo2Data] = useState<WeeklyCo2Point[]>([]);
  const [vehicleDistanceData, setVehicleDistanceData] = useState<VehicleDistancePoint[]>([]);
  const [chartLoading, setChartLoading] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000';

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoadError(null);
        const res = await fetch(`${apiBase}/api/dashboard`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setDashboardData({
          kpis: data.kpis,
          runHistory: data.run_history || []
        });
      } catch (err: any) {
        console.error('/api/dashboard 요청 실패', err);
        setLoadError(err.message || '대시보드 데이터를 불러오지 못했습니다.');
      }
    };
    fetchDashboard();
  }, [apiBase, setDashboardData]);

  useEffect(() => {
    const fetchCharts = async () => {
      const { fromDate, toDate } = calculateDateRange(dateRange);
      const params = new URLSearchParams({ fromDate, toDate });
      if (selectedVehicle !== 'all') {
        params.append('vehicleId', selectedVehicle);
      }
      if (selectedSector !== 'all') {
        params.append('sectorId', selectedSector);
      }

      setChartLoading(true);
      setChartError(null);
      try {
        const queryString = params.toString();
        const [weeklyRes, distanceRes] = await Promise.all([
          fetch(`${apiBase}/api/dashboard/weekly-co2?${queryString}`),
          fetch(`${apiBase}/api/dashboard/vehicle-distance?${queryString}`)
        ]);
        if (!weeklyRes.ok) throw new Error(`weekly-co2 ${weeklyRes.status}`);
        if (!distanceRes.ok) throw new Error(`vehicle-distance ${distanceRes.status}`);

        const weeklyJson = await weeklyRes.json();
        const distanceJson = await distanceRes.json();

        setWeeklyCo2Data(
          Array.isArray(weeklyJson)
            ? weeklyJson.map((item: any) => ({
                date: item.date,
                co2_kg: Number(item.co2_kg ?? 0)
              }))
            : []
        );

        setVehicleDistanceData(
          Array.isArray(distanceJson)
            ? distanceJson.map((item: any) => ({
                vehicle_id: item.vehicle_id,
                distance_km: Number(item.distance_km ?? 0)
              }))
            : []
        );
      } catch (err: any) {
        console.error('대시보드 차트 데이터 조회 실패', err);
        setChartError(err.message || '차트 데이터를 불러오지 못했습니다.');
        setWeeklyCo2Data([]);
        setVehicleDistanceData([]);
      } finally {
        setChartLoading(false);
      }
    };
    fetchCharts();
  }, [apiBase, dateRange, selectedVehicle, selectedSector]);

  const renderChartState = (hasData: boolean, chartElement: JSX.Element) => {
    if (chartError && !chartLoading) {
      return <p className="text-sm text-destructive py-12 text-center">{chartError}</p>;
    }
    if (chartLoading) {
      return <p className="text-sm text-muted-foreground py-12 text-center">차트 데이터를 불러오는 중...</p>;
    }
    if (!hasData) {
      return <p className="text-sm text-muted-foreground py-12 text-center">표시할 데이터가 없습니다.</p>;
    }
    return chartElement;
  };

  return (
    <Protected>
      <div className="container mx-auto py-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <BarChart3 className="w-8 h-8 text-blue-600" />
              <h1 className="text-3xl font-bold">대시보드</h1>
            </div>
            <p className="text-muted-foreground">물류 운영 성과와 친환경 지표를 한눈에 모니터링하세요.</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
                <RouteIcon className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-900">{dashboardKpis.total_distance_km}km</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-lg">
                <Zap className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-green-900">{dashboardKpis.total_co2_kg}kg CO₂</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 rounded-lg">
                <Clock className="w-4 h-4 text-purple-600" />
                <span className="text-sm font-medium text-purple-900">
                  {Math.floor(dashboardKpis.total_time_min / 60)}h {dashboardKpis.total_time_min % 60}m
                </span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-lg">
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                  <span className="text-sm font-medium text-emerald-900">{dashboardKpis.saving_percent}%</span>
              </div>
            </div>
          </div>
          <Button variant="outline" className="flex items-center gap-2">
            <Download className="w-4 h-4" />
            리포트 다운로드
          </Button>
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Filter className="w-5 h-5" />
              필터
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">기간</label>
                <Select value={dateRange} onValueChange={setDateRange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="week">지난 주</SelectItem>
                    <SelectItem value="month">최근 30일</SelectItem>
                    <SelectItem value="quarter">최근 90일</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">차량</label>
                <Select value={selectedVehicle} onValueChange={setSelectedVehicle}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">전체 차량</SelectItem>
                    {vehicles.map((vehicle) => (
                      <SelectItem key={vehicle.id} value={vehicle.id}>
                        {vehicle.id} ({vehicle.type})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">센터</label>
                <Select value={selectedSector} onValueChange={setSelectedSector}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">전체 센터</SelectItem>
                    {sectors.map((sector) => (
                      <SelectItem key={sector.id} value={sector.id}>
                        {sector.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {loadError && (
          <div className="text-sm text-destructive bg-destructive/10 px-4 py-2 rounded-lg">
            {loadError}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-600" />
                주간 CO₂ 배출량 추이
              </CardTitle>
            </CardHeader>
            <CardContent>
              {renderChartState(
                weeklyCo2Data.length > 0,
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={weeklyCo2Data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => new Date(value).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip
                      labelFormatter={(value) => `날짜: ${new Date(value).toLocaleDateString('ko-KR')}`}
                      formatter={(value: number) => [`${value}kg`, 'CO₂ 배출량']}
                    />
                    <Line
                      type="monotone"
                      dataKey="co2_kg"
                      stroke="#22c55e"
                      strokeWidth={2}
                      dot={{ fill: '#22c55e', strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-600" />
                차량별 주행거리
              </CardTitle>
            </CardHeader>
            <CardContent>
              {renderChartState(
                vehicleDistanceData.length > 0,
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={vehicleDistanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="vehicle_id" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(value: number) => [`${value}km`, '주행거리']} />
                    <Bar dataKey="distance_km" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>최근 실행 목록</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>실행 ID</TableHead>
                  <TableHead>일시</TableHead>
                  <TableHead>총 주행거리</TableHead>
                  <TableHead>총 CO₂ 배출량</TableHead>
                  <TableHead>처리 작업 수</TableHead>
                  <TableHead>작업</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dashboardRunHistory.map((run) => (
                  <TableRow key={run.run_id}>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {run.run_id}
                      </Badge>
                    </TableCell>
                    <TableCell>{formatRunDate(run.date)}</TableCell>
                    <TableCell>{run.total_distance}km</TableCell>
                    <TableCell>{run.total_co2}kg</TableCell>
                    <TableCell>{run.served_jobs ?? 0}건</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" className="flex items-center gap-2">
                        <Eye className="w-4 h-4" />
                        상세보기
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </Protected>
  );
}
