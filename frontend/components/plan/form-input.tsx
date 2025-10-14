'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Plus, Trash2, Calendar, Truck, MapPin, Weight, Clock } from 'lucide-react';
import { useStore } from '@/lib/store';
import { OptimizationRequest, Job } from '@/lib/types';

interface FormInputProps {
  onSubmit: (request: OptimizationRequest) => void;
}

export default function FormInput({ onSubmit }: FormInputProps) {
  const { vehicles, sectors } = useStore();
  const [formData, setFormData] = useState({
    run_date: '2024-01-15',
    selected_vehicles: [] as string[],
    jobs: [
      {
        sector_id: 'A',
        date: '2024-01-15', 
        demand_kg: 300,
        tw_start: '09:00',
        tw_end: '12:00',
        priority: 2
      }
    ] as Partial<Job>[]
  });

  const handleVehicleToggle = (vehicleId: string) => {
    setFormData(prev => ({
      ...prev,
      selected_vehicles: prev.selected_vehicles.includes(vehicleId)
        ? prev.selected_vehicles.filter(id => id !== vehicleId)
        : [...prev.selected_vehicles, vehicleId]
    }));
  };

  const addJob = () => {
    setFormData(prev => ({
      ...prev,
      jobs: [...prev.jobs, {
        sector_id: '',
        date: prev.run_date,
        demand_kg: 0,
        tw_start: '09:00', 
        tw_end: '17:00',
        priority: 2
      }]
    }));
  };

  const removeJob = (index: number) => {
    setFormData(prev => ({
      ...prev,
      jobs: prev.jobs.filter((_, i) => i !== index)
    }));
  };

  const updateJob = (index: number, field: keyof Job, value: any) => {
    setFormData(prev => ({
      ...prev,
      jobs: prev.jobs.map((job, i) => 
        i === index ? { ...job, [field]: value } : job
      )
    }));
  };

  const handleSubmit = () => {
    const completeJobs = formData.jobs.map(job => {
      const sector = sectors.find(s => s.id === job.sector_id);
      return {
        ...job,
        lat: sector?.lat || 0,
        lon: sector?.lon || 0,
        date: job.date || formData.run_date,
        sector_id: job.sector_id || '',
        demand_kg: job.demand_kg || 0,
        tw_start: job.tw_start || '09:00',
        tw_end: job.tw_end || '17:00',
        priority: job.priority || 2
      } as Job;
    }).filter(job => job.sector_id && job.demand_kg > 0);

    const request: OptimizationRequest = {
      run_date: formData.run_date,
      vehicles: formData.selected_vehicles,
      jobs: completeJobs
    };

    onSubmit(request);
  };

  const totalDemand = formData.jobs.reduce((sum, job) => sum + (job.demand_kg || 0), 0);
  const totalCapacity = formData.selected_vehicles.reduce((sum, vehicleId) => {
    const vehicle = vehicles.find(v => v.id === vehicleId);
    return sum + (vehicle?.capacity_kg || 0);
  }, 0);

  const isValid = formData.selected_vehicles.length > 0 && 
                 formData.jobs.length > 0 && 
                 totalDemand <= totalCapacity;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Form Section */}
      <div className="lg:col-span-2 space-y-6">
        {/* Date Selection */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="w-5 h-5" />
              실행 날짜
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Input
              type="date"
              value={formData.run_date}
              onChange={(e) => setFormData(prev => ({ ...prev, run_date: e.target.value }))}
            />
          </CardContent>
        </Card>

        {/* Vehicle Selection */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <Truck className="w-5 h-5" />
              차량 선택 ({formData.selected_vehicles.length}대)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {vehicles.map((vehicle) => (
                <div key={vehicle.id} className="flex items-center space-x-3 p-3 border rounded-lg">
                  <Checkbox
                    id={vehicle.id}
                    checked={formData.selected_vehicles.includes(vehicle.id)}
                    onCheckedChange={() => handleVehicleToggle(vehicle.id)}
                  />
                  <div className="flex-1">
                    <Label htmlFor={vehicle.id} className="font-medium cursor-pointer">
                      {vehicle.id}
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      {vehicle.type} | {vehicle.capacity_kg}kg | {vehicle.fuel}
                    </p>
                  </div>
                  <Badge variant="secondary" className="text-xs">
                    {vehicle.ef_gpkm}g/km
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Jobs */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-lg">
                <MapPin className="w-5 h-5" />
                배송 작업 ({formData.jobs.length}개)
              </CardTitle>
              <Button onClick={addJob} size="sm" variant="outline">
                <Plus className="w-4 h-4 mr-2" />
                작업 추가
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {formData.jobs.map((job, index) => (
                <div key={index} className="p-4 border rounded-lg space-y-4">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">작업 #{index + 1}</Badge>
                    {formData.jobs.length > 1 && (
                      <Button 
                        onClick={() => removeJob(index)}
                        variant="ghost" 
                        size="sm"
                        className="text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label>섹터</Label>
                      <Select
                        value={job.sector_id}
                        onValueChange={(value) => updateJob(index, 'sector_id', value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="섹터 선택" />
                        </SelectTrigger>
                        <SelectContent>
                          {sectors.map((sector) => (
                            <SelectItem key={sector.id} value={sector.id}>
                              {sector.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label className="flex items-center gap-2">
                        <Weight className="w-4 h-4" />
                        수요 (kg)
                      </Label>
                      <Input
                        type="number"
                        value={job.demand_kg || ''}
                        onChange={(e) => updateJob(index, 'demand_kg', parseInt(e.target.value) || 0)}
                        placeholder="0"
                        min="0"
                      />
                    </div>
                    
                    <div>
                      <Label className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        시작 시간
                      </Label>
                      <Input
                        type="time"
                        value={job.tw_start || ''}
                        onChange={(e) => updateJob(index, 'tw_start', e.target.value)}
                      />
                    </div>
                    
                    <div>
                      <Label>종료 시간</Label>
                      <Input
                        type="time"
                        value={job.tw_end || ''}
                        onChange={(e) => updateJob(index, 'tw_end', e.target.value)}
                      />
                    </div>
                    
                    <div>
                      <Label>우선순위</Label>
                      <Select
                        value={String(job.priority || 2)}
                        onValueChange={(value) => updateJob(index, 'priority', parseInt(value))}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">높음 (1)</SelectItem>
                          <SelectItem value="2">보통 (2)</SelectItem>
                          <SelectItem value="3">낮음 (3)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Summary Section */}
      <div className="space-y-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">요약</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm">총 차량 수</span>
                <Badge variant="secondary">{formData.selected_vehicles.length}대</Badge>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm">총 배송량</span>
                <Badge variant="secondary">{totalDemand}kg</Badge>
              </div>
              
              <div className="flex justify-between items-center">
                <span className="text-sm">총 용량</span>
                <Badge variant="secondary">{totalCapacity}kg</Badge>
              </div>
              
              <Separator />
              
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm">용량 제약</span>
                  {totalDemand <= totalCapacity ? (
                    <Badge variant="secondary" className="bg-green-100 text-green-800">
                      ✓ 충족
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      ✗ 초과
                    </Badge>
                  )}
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-sm">시간창 제약</span>
                  <Badge variant="secondary" className="bg-green-100 text-green-800">
                    ✓ 유효
                  </Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Button 
          onClick={handleSubmit}
          disabled={!isValid}
          className="w-full"
          size="lg"
        >
          최적화 실행 (더미)
        </Button>
      </div>
    </div>
  );
}