'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Settings, Database } from 'lucide-react';
import VehicleManagement from '@/components/admin/vehicle-management';
import SectorManagement from '@/components/admin/sector-management';
import JobManagement from '@/components/admin/job-management';

import Protected from '@/components/auth/Protected';

export default function AdminPage() {
  return (
    <Protected>
    <div className="container max-w-7xl mx-auto p-6 space-y-6 bg-background">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex items-center justify-center gap-2">
          <Settings className="w-7 h-7 text-muted-foreground" />
          <h1 className="text-2xl font-semibold text-foreground">데이터 관리</h1>
        </div>
        <p className="text-muted-foreground">
          차량, 섹터, 작업 데이터를 관리하고 시스템 설정을 조정하세요.
        </p>
      </div>

      {/* Main Content */}
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Database className="w-5 h-5 text-gray-600" />
            마스터 데이터 관리
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="vehicles" className="w-full">
            <TabsList className="grid w-full grid-cols-3 h-11">
              <TabsTrigger value="vehicles" className="text-sm">차량 (Vehicles)</TabsTrigger>
              <TabsTrigger value="sectors" className="text-sm">섹터 (Sectors)</TabsTrigger>
              <TabsTrigger value="jobs" className="text-sm">작업 (Jobs)</TabsTrigger>
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
    </Protected>
  );
}