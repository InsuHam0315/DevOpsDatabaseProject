'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Plus, CreditCard as Edit, Trash2, Car } from 'lucide-react';
import { useStore } from '@/lib/store';
import { Vehicle } from '@/lib/types';

export default function VehicleManagement() {
  const { vehicles, addVehicle, updateVehicle, deleteVehicle } = useStore();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null);
  const [formData, setFormData] = useState({
    id: '',
    type: '',
    capacity_kg: 0,
    fuel: '',
    ef_gpkm: 0,
    idle_gps: 0
  });

  const fuelTypes = [
    { value: 'EV', label: '전기' },
    { value: 'HYBRID', label: '하이브리드' },
    { value: 'DIESEL', label: '디젤' },
    { value: 'GASOLINE', label: '휘발유' }
  ];

  const handleOpenDialog = (vehicle?: Vehicle) => {
    if (vehicle) {
      setEditingVehicle(vehicle);
      setFormData(vehicle);
    } else {
      setEditingVehicle(null);
      setFormData({
        id: '',
        type: '',
        capacity_kg: 0,
        fuel: '',
        ef_gpkm: 0,
        idle_gps: 0
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = () => {
    if (editingVehicle) {
      updateVehicle(editingVehicle.id, formData);
    } else {
      addVehicle(formData as Vehicle);
    }
    setDialogOpen(false);
    setEditingVehicle(null);
  };

  const handleDelete = (id: string) => {
    if (confirm('정말로 이 차량을 삭제하시겠습니까?')) {
      deleteVehicle(id);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Car className="w-5 h-5" />
          <h3 className="text-lg font-semibold">차량 관리 ({vehicles.length}대)</h3>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()}>
              <Plus className="w-4 h-4 mr-2" />
              차량 추가
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingVehicle ? '차량 수정' : '새 차량 등록'}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="vehicle-id">차량 ID</Label>
                <Input
                  id="vehicle-id"
                  value={formData.id}
                  onChange={(e) => setFormData(prev => ({ ...prev, id: e.target.value }))}
                  disabled={!!editingVehicle}
                />
              </div>
              
              <div>
                <Label htmlFor="vehicle-type">차량 타입</Label>
                <Input
                  id="vehicle-type"
                  value={formData.type}
                  onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value }))}
                  placeholder="예: EV_1t, HYBRID_1.5t"
                />
              </div>
              
              <div>
                <Label htmlFor="capacity">적재용량 (kg)</Label>
                <Input
                  id="capacity"
                  type="number"
                  value={formData.capacity_kg}
                  onChange={(e) => setFormData(prev => ({ ...prev, capacity_kg: parseInt(e.target.value) || 0 }))}
                />
              </div>
              
              <div>
                <Label>연료 타입</Label>
                <Select
                  value={formData.fuel}
                  onValueChange={(value) => setFormData(prev => ({ ...prev, fuel: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="연료 타입 선택" />
                  </SelectTrigger>
                  <SelectContent>
                    {fuelTypes.map((fuel) => (
                      <SelectItem key={fuel.value} value={fuel.value}>
                        {fuel.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div>
                <Label htmlFor="emission-factor">배출계수 (g/km)</Label>
                <Input
                  id="emission-factor"
                  type="number"
                  value={formData.ef_gpkm}
                  onChange={(e) => setFormData(prev => ({ ...prev, ef_gpkm: parseInt(e.target.value) || 0 }))}
                />
              </div>
              
              <div>
                <Label htmlFor="idle-emission">공회전 배출량 (g/s)</Label>
                <Input
                  id="idle-emission"
                  type="number"
                  value={formData.idle_gps}
                  onChange={(e) => setFormData(prev => ({ ...prev, idle_gps: parseInt(e.target.value) || 0 }))}
                />
              </div>
              
              <Button onClick={handleSubmit} className="w-full">
                {editingVehicle ? '수정' : '등록'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>차량 ID</TableHead>
              <TableHead>타입</TableHead>
              <TableHead>적재용량</TableHead>
              <TableHead>연료</TableHead>
              <TableHead>배출계수</TableHead>
              <TableHead>공회전</TableHead>
              <TableHead>작업</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {vehicles.map((vehicle) => (
              <TableRow key={vehicle.id}>
                <TableCell>
                  <Badge variant="outline">{vehicle.id}</Badge>
                </TableCell>
                <TableCell>{vehicle.type}</TableCell>
                <TableCell>{vehicle.capacity_kg}kg</TableCell>
                <TableCell>
                  <Badge 
                    variant="secondary"
                    className={
                      vehicle.fuel === 'EV' ? 'bg-green-100 text-green-800' :
                      vehicle.fuel === 'HYBRID' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }
                  >
                    {fuelTypes.find(f => f.value === vehicle.fuel)?.label || vehicle.fuel}
                  </Badge>
                </TableCell>
                <TableCell>{vehicle.ef_gpkm}g/km</TableCell>
                <TableCell>{vehicle.idle_gps}g/s</TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenDialog(vehicle)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(vehicle.id)}
                      className="text-destructive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}