'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Plus, CreditCard as Edit, Trash2, MapPin, Clock } from 'lucide-react';
import { useStore } from '@/lib/store';
import { Sector } from '@/lib/types';

export default function SectorManagement() {
  const { sectors, addSector, updateSector, deleteSector } = useStore();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSector, setEditingSector] = useState<Sector | null>(null);
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    lat: 0,
    lon: 0,
    tw_start: '09:00',
    tw_end: '17:00',
    priority: 2
  });

  const handleOpenDialog = (sector?: Sector) => {
    if (sector) {
      setEditingSector(sector);
      setFormData(sector);
    } else {
      setEditingSector(null);
      setFormData({
        id: '',
        name: '',
        lat: 0,
        lon: 0,
        tw_start: '09:00',
        tw_end: '17:00',
        priority: 2
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = () => {
    if (editingSector) {
      updateSector(editingSector.id, formData);
    } else {
      addSector(formData as Sector);
    }
    setDialogOpen(false);
    setEditingSector(null);
  };

  const handleDelete = (id: string) => {
    if (confirm('정말로 이 섹터를 삭제하시겠습니까?')) {
      deleteSector(id);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5" />
          <h3 className="text-lg font-semibold">섹터 관리 ({sectors.length}개)</h3>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()}>
              <Plus className="w-4 h-4 mr-2" />
              섹터 추가
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingSector ? '섹터 수정' : '새 섹터 등록'}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="sector-id">섹터 ID</Label>
                <Input
                  id="sector-id"
                  value={formData.id}
                  onChange={(e) => setFormData(prev => ({ ...prev, id: e.target.value }))}
                  disabled={!!editingSector}
                />
              </div>
              
              <div>
                <Label htmlFor="sector-name">섹터 이름</Label>
                <Input
                  id="sector-name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="예: 군산A구역"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="latitude">위도</Label>
                  <Input
                    id="latitude"
                    type="number"
                    step="0.000001"
                    value={formData.lat}
                    onChange={(e) => setFormData(prev => ({ ...prev, lat: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
                
                <div>
                  <Label htmlFor="longitude">경도</Label>
                  <Input
                    id="longitude"
                    type="number"
                    step="0.000001"
                    value={formData.lon}
                    onChange={(e) => setFormData(prev => ({ ...prev, lon: parseFloat(e.target.value) || 0 }))}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="tw-start">시작 시간</Label>
                  <Input
                    id="tw-start"
                    type="time"
                    value={formData.tw_start}
                    onChange={(e) => setFormData(prev => ({ ...prev, tw_start: e.target.value }))}
                  />
                </div>
                
                <div>
                  <Label htmlFor="tw-end">종료 시간</Label>
                  <Input
                    id="tw-end"
                    type="time"
                    value={formData.tw_end}
                    onChange={(e) => setFormData(prev => ({ ...prev, tw_end: e.target.value }))}
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="priority">우선순위</Label>
                <Input
                  id="priority"
                  type="number"
                  min="1"
                  max="5"
                  value={formData.priority}
                  onChange={(e) => setFormData(prev => ({ ...prev, priority: parseInt(e.target.value) || 2 }))}
                />
              </div>
              
              <Button onClick={handleSubmit} className="w-full">
                {editingSector ? '수정' : '등록'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>섹터 ID</TableHead>
              <TableHead>이름</TableHead>
              <TableHead>좌표</TableHead>
              <TableHead>시간창</TableHead>
              <TableHead>우선순위</TableHead>
              <TableHead>작업</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sectors.map((sector) => (
              <TableRow key={sector.id}>
                <TableCell>
                  <Badge variant="outline">{sector.id}</Badge>
                </TableCell>
                <TableCell className="font-medium">{sector.name}</TableCell>
                <TableCell className="font-mono text-sm">
                  {sector.lat.toFixed(4)}, {sector.lon.toFixed(4)}
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 text-sm">
                    <Clock className="w-3 h-3" />
                    {sector.tw_start} ~ {sector.tw_end}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge 
                    variant="secondary"
                    className={
                      sector.priority === 1 ? 'bg-red-100 text-red-800' :
                      sector.priority === 2 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }
                  >
                    {sector.priority === 1 ? '높음' : sector.priority === 2 ? '보통' : '낮음'}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenDialog(sector)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(sector.id)}
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