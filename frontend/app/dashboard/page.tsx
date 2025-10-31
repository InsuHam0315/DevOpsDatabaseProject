'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ChartBar as BarChart3, TrendingUp, Filter, Calendar, Eye, Download, Route as RouteIcon, Zap, Clock } from 'lucide-react';
import { useStore } from '@/lib/store';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';

export default function DashboardPage() {
  const { chartData, runHistory, vehicles, sectors, kpis } = useStore();
  const [dateRange, setDateRange] = useState('week');
  const [selectedVehicle, setSelectedVehicle] = useState('all');
  const [selectedSector, setSelectedSector] = useState('all');

  const pieColors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'];

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <BarChart3 className="w-8 h-8 text-blue-600" />
            <h1 className="text-3xl font-bold">대시보드</h1>
          </div>
          <p className="text-muted-foreground">
            물류 운영 성과와 친환경 지표를 모니터링하세요.
          </p>
          {/* KPI Summary moved here */}
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
              <RouteIcon className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-900">{kpis.total_distance_km}km</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 rounded-lg">
              <Zap className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-green-900">{kpis.total_co2_kg}kg CO₂</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 rounded-lg">
              <Clock className="w-4 h-4 text-purple-600" />
              <span className="text-sm font-medium text-purple-900">{Math.floor(kpis.total_time_min / 60)}h {kpis.total_time_min % 60}m</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-lg">
              <TrendingUp className="w-4 h-4 text-emerald-600" />
              <span className="text-sm font-medium text-emerald-900">{kpis.saving_percent}%</span>
            </div>
          </div>
        </div>
        <Button variant="outline" className="flex items-center gap-2">
          <Download className="w-4 h-4" />
          리포트 다운로드
        </Button>
      </div>

      {/* Filters */}
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
                  <SelectItem value="day">오늘</SelectItem>
                  <SelectItem value="week">지난 주</SelectItem>
                  <SelectItem value="month">지난 달</SelectItem>
                  <SelectItem value="quarter">분기</SelectItem>
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
              <label className="text-sm font-medium mb-2 block">섹터</label>
              <Select value={selectedSector} onValueChange={setSelectedSector}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">전체 섹터</SelectItem>
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

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CO2 Trend Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-600" />
              주간 CO₂ 배출량 추이
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData.weekly_co2}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => new Date(value).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  labelFormatter={(value) => `날짜: ${new Date(value).toLocaleDateString('ko-KR')}`}
                  formatter={(value: any) => [`${value}kg`, 'CO₂ 배출량']}
                />
                <Line
                  type="monotone"
                  dataKey="co2"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={{ fill: '#22c55e', strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Vehicle Distance Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-600" />
              차량별 주행거리
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData.vehicle_distances}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="vehicle" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value: any) => [`${value}km`, '주행거리']} />
                <Bar dataKey="distance" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Runs Table */}
      <Card>
        <CardHeader>
          <CardTitle>최근 실행 목록</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>실행 ID</TableHead>
                <TableHead>날짜</TableHead>
                <TableHead>총 주행거리</TableHead>
                <TableHead>총 CO₂ 배출량</TableHead>
                <TableHead>처리 작업 수</TableHead>
                <TableHead>작업</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runHistory.map((run) => (
                <TableRow key={run.run_id}>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {run.run_id}
                    </Badge>
                  </TableCell>
                  <TableCell>{run.date}</TableCell>
                  <TableCell>{run.total_distance}km</TableCell>
                  <TableCell>{run.total_co2}kg</TableCell>
                  <TableCell>{run.served_jobs}개</TableCell>
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
  );
}