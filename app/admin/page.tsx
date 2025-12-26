'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Settings, Database } from 'lucide-react';
import VehicleManagement from '@/components/admin/vehicle-management';
import SectorManagement from '@/components/admin/sector-management';
import JobManagement from '@/components/admin/job-management';

export default function AdminPage() {
  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3">
          <Settings className="w-8 h-8 text-gray-600" />
          <h1 className="text-3xl font-bold">데이터 관리</h1>
        </div>
        <p className="text-muted-foreground">
          차량, 섹터, 작업 데이터를 관리하고 시스템 설정을 조정하세요.
        </p>
      </div>

      {/* Main Content */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            마스터 데이터 관리
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="vehicles" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="vehicles">차량 (Vehicles)</TabsTrigger>
              <TabsTrigger value="sectors">섹터 (Sectors)</TabsTrigger>
              <TabsTrigger value="jobs">작업 (Jobs)</TabsTrigger>
            </TabsList>
            
            <TabsContent value="vehicles" className="mt-6">
              <VehicleManagement />
            </TabsContent>
            
            <TabsContent value="sectors" className="mt-6">
              <SectorManagement />
            </TabsContent>
            
            <TabsContent value="jobs" className="mt-6">
              <JobManagement />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}