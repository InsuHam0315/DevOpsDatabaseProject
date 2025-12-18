'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Database, Truck, Map, Briefcase, RefreshCw, AlertCircle, Plus, Save, X } from 'lucide-react';

//-------------------------------------------------------------------------- 변경부분
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000';
//-------------------------------------------------------------------------- 

interface Vehicle { vehicle_id: string; vehicle_type: string; model_name: string; capacity_kg: number; }
interface Sector { sector_name: string; lat: number; lon: number; }
interface Job { job_id: number; address: string; demand_kg: number; tw_start?: string; tw_end?: string; }

export default function AdminPage() {
  // --- 데이터 상태 ---
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- UI 상태 ---
  const [isAdding, setIsAdding] = useState(false); // 입력창 열림/닫힘
  const [activeTab, setActiveTab] = useState("vehicles"); // 현재 탭

  // --- 입력값 상태 (작업 추가는 제거됨) ---
  const [newVehicle, setNewVehicle] = useState({ vehicle_id: '', vehicle_type: '', model_name: '', capacity_kg: 0 });
  const [newSector, setNewSector] = useState({ sector_name: '', lat: 0, lon: 0 });

  // --- 데이터 불러오기 ---
  const fetchData = async () => {
    setLoading(true);
    try {
      const [vRes, sRes, jRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/vehicles`),
        fetch(`${API_BASE_URL}/api/sectors`),
        fetch(`${API_BASE_URL}/api/jobs`)
      ]);
      if (vRes.ok && sRes.ok && jRes.ok) {
        setVehicles(await vRes.json());
        setSectors(await sRes.json());
        setJobs(await jRes.json());
      } else {
        throw new Error("데이터 조회 실패");
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // --- 저장 핸들러 (작업 관련 로직 삭제) ---
  const handleSave = async () => {
    let url = '';
    let body = {};

    if (activeTab === 'vehicles') {
      url = `${API_BASE_URL}/api/vehicles/add`;
      body = newVehicle;
    } else if (activeTab === 'sectors') {
      url = `${API_BASE_URL}/api/sectors/add`;
      body = newSector;
    } else {
      return; // Jobs 탭에서는 저장 동작 안 함
    }

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || '저장 실패');
      }

      alert("저장되었습니다!");
      setIsAdding(false);
      fetchData();

      // 입력창 초기화
      setNewVehicle({ vehicle_id: '', vehicle_type: '', model_name: '', capacity_kg: 0 });
      setNewSector({ sector_name: '', lat: 0, lon: 0 });

    } catch (err: any) {
      alert(`에러 발생: ${err.message}`);
    }
  };

  const formatTime = (timeStr?: string) => timeStr ? timeStr.replace('T', ' ').substring(0, 16) : '-';

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* --- 페이지 헤더 --- */}
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Database className="w-8 h-8 text-blue-600" /> 데이터 관리
          </h1>
          <p className="text-muted-foreground">Oracle 데이터베이스 현황판</p>
        </div>
        <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors">
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> 새로고침
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5" /> {error}
        </div>
      )}

      {/* --- 탭 섹션 --- */}
      <Tabs defaultValue="vehicles" className="w-full" onValueChange={(val) => { setActiveTab(val); setIsAdding(false); }}>
        <TabsList className="grid w-full grid-cols-3 mb-8">
          <TabsTrigger value="vehicles" className="gap-2"><Truck className="w-4 h-4" /> 차량 (Vehicles)</TabsTrigger>
          <TabsTrigger value="sectors" className="gap-2"><Map className="w-4 h-4" /> 구역 (Sectors)</TabsTrigger>
          <TabsTrigger value="jobs" className="gap-2"><Briefcase className="w-4 h-4" /> 작업 (Jobs)</TabsTrigger>
        </TabsList>

        {/* 1. 차량 탭 */}
        <TabsContent value="vehicles">
          <Card>
            {/* 헤더에 버튼 배치 */}
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>차량 목록 ({vehicles.length})</CardTitle>
                <CardDescription>보유 중인 운송 차량 리스트</CardDescription>
              </div>
              <button
                onClick={() => setIsAdding(!isAdding)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${isAdding ? 'bg-red-50 text-red-600' : 'bg-green-600 text-white hover:bg-green-700'}`}
              >
                {isAdding ? <><X className="w-4 h-4" /> 취소</> : <><Plus className="w-4 h-4" /> 차량 추가</>}
              </button>
            </CardHeader>

            <CardContent>
              {/* 입력 폼 (isAdding일 때만 표시) */}
              {isAdding && (
                <div className="mb-6 p-4 bg-green-50 rounded-lg border border-green-200 animate-in slide-in-from-top-2">
                  <h3 className="font-bold text-green-800 mb-3 flex items-center gap-2"><Plus className="w-4 h-4" /> 새 차량 등록</h3>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-3">
                    <input placeholder="차량번호 (예: 서울12가3456)" className="p-2 border rounded"
                      value={newVehicle.vehicle_id} onChange={e => setNewVehicle({ ...newVehicle, vehicle_id: e.target.value })} />
                    <input placeholder="타입 (예: TRACTOR)" className="p-2 border rounded"
                      value={newVehicle.vehicle_type} onChange={e => setNewVehicle({ ...newVehicle, vehicle_type: e.target.value })} />
                    <input placeholder="모델명 (예: 엑시언트)" className="p-2 border rounded"
                      value={newVehicle.model_name} onChange={e => setNewVehicle({ ...newVehicle, model_name: e.target.value })} />
                    <input type="number" placeholder="용량(kg)" className="p-2 border rounded"
                      value={newVehicle.capacity_kg} onChange={e => setNewVehicle({ ...newVehicle, capacity_kg: Number(e.target.value) })} />
                  </div>
                  <button onClick={handleSave} className="w-full py-2 bg-green-600 text-white rounded hover:bg-green-700 flex justify-center items-center gap-2">
                    <Save className="w-4 h-4" /> 저장하기
                  </button>
                </div>
              )}

              {/* 목록 테이블 */}
              <div className="relative overflow-x-auto border rounded-lg">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-gray-50">
                    <tr><th className="px-6 py-3">ID</th><th className="px-6 py-3">모델 / 타입</th><th className="px-6 py-3">용량</th></tr>
                  </thead>
                  <tbody>
                    {vehicles.map((v, i) => (
                      <tr key={i} className="border-b bg-white hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium">{v.vehicle_id}</td>
                        <td className="px-6 py-4">{v.model_name} <span className="text-gray-400 text-xs">({v.vehicle_type})</span></td>
                        <td className="px-6 py-4">{v.capacity_kg} kg</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 2. 구역 탭 */}
        <TabsContent value="sectors">
          <Card>
            {/* 헤더에 버튼 배치 */}
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>구역 목록 ({sectors.length})</CardTitle>
                <CardDescription>배송 권역 데이터</CardDescription>
              </div>
              <button
                onClick={() => setIsAdding(!isAdding)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors text-sm font-medium ${isAdding ? 'bg-red-50 text-red-600' : 'bg-green-600 text-white hover:bg-green-700'}`}
              >
                {isAdding ? <><X className="w-4 h-4" /> 취소</> : <><Plus className="w-4 h-4" /> 구역 추가</>}
              </button>
            </CardHeader>

            <CardContent>
              {/* 입력 폼 */}
              {isAdding && (
                <div className="mb-6 p-4 bg-green-50 rounded-lg border border-green-200 animate-in slide-in-from-top-2">
                  <h3 className="font-bold text-green-800 mb-3 flex items-center gap-2"><Plus className="w-4 h-4" /> 새 구역 등록</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                    <input placeholder="구역명 (예: 강남A)" className="p-2 border rounded"
                      value={newSector.sector_name} onChange={e => setNewSector({ ...newSector, sector_name: e.target.value })} />
                    <input type="number" placeholder="위도 (Lat)" className="p-2 border rounded"
                      value={newSector.lat} onChange={e => setNewSector({ ...newSector, lat: Number(e.target.value) })} />
                    <input type="number" placeholder="경도 (Lon)" className="p-2 border rounded"
                      value={newSector.lon} onChange={e => setNewSector({ ...newSector, lon: Number(e.target.value) })} />
                  </div>
                  <button onClick={handleSave} className="w-full py-2 bg-green-600 text-white rounded hover:bg-green-700 flex justify-center items-center gap-2">
                    <Save className="w-4 h-4" /> 저장하기
                  </button>
                </div>
              )}

              {/* 목록 테이블 */}
              <div className="relative overflow-x-auto border rounded-lg">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-gray-50">
                    <tr><th className="px-6 py-3">구역명</th><th className="px-6 py-3">좌표 (Lat, Lon)</th></tr>
                  </thead>
                  <tbody>
                    {sectors.map((s, i) => (
                      <tr key={i} className="border-b bg-white hover:bg-gray-50">
                        <td className="px-6 py-4 font-medium">{s.sector_name}</td>
                        <td className="px-6 py-4 text-gray-500">{s.lat}, {s.lon}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 3. 작업 탭 (추가 버튼 없음) */}
        <TabsContent value="jobs">
          <Card>
            <CardHeader>
              <CardTitle>작업 목록 ({jobs.length})</CardTitle>
              <CardDescription>현재 등록된 배송 작업 요청 리스트 (조회 전용)</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative overflow-x-auto border rounded-lg">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-gray-50">
                    <tr><th className="px-6 py-3">ID</th><th className="px-6 py-3">주소</th><th className="px-6 py-3">물량</th><th className="px-6 py-3">시간</th></tr>
                  </thead>
                  <tbody>
                    {jobs.map((j, i) => (
                      <tr key={i} className="border-b bg-white hover:bg-gray-50">
                        <td className="px-6 py-4 font-bold text-blue-600">{j.job_id}</td>
                        <td className="px-6 py-4">{j.address}</td>
                        <td className="px-6 py-4">{j.demand_kg?.toLocaleString()} kg</td>
                        <td className="px-6 py-4 text-xs">
                          <span className="text-green-600 block">S: {formatTime(j.tw_start)}</span>
                          <span className="text-red-500 block">E: {formatTime(j.tw_end)}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}