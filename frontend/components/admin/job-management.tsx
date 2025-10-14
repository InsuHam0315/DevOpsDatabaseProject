'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Plus, CreditCard as Edit, Trash2, Upload, Briefcase, Clock } from 'lucide-react';
import { useStore } from '@/lib/store';
import { Job } from '@/lib/types';

export default function JobManagement() {
  const { jobs, sectors, addJob, updateJob, deleteJob } = useStore();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [formData, setFormData] = useState({
    sector_id: '',
    date: '2024-01-15',
    demand_kg: 0,
    tw_start: '09:00',
    tw_end: '17:00',
    priority: 2,
    lat: 0,
    lon: 0
  });

  const handleOpenDialog = (job?: Job, index?: number) => {
    if (job && index !== undefined) {
      setEditingIndex(index);
      setFormData(job);
    } else {
      setEditingIndex(null);
      setFormData({
        sector_id: '',
        date: '2024-01-15',
        demand_kg: 0,
        tw_start: '09:00',
        tw_end: '17:00',
        priority: 2,
        lat: 0,
        lon: 0
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = () => {
    const sector = sectors.find(s => s.id === formData.sector_id);
    const completeJob = {
      ...formData,
      lat: sector?.lat || formData.lat,
      lon: sector?.lon || formData.lon
    } as Job;

    if (editingIndex !== null) {
      updateJob(editingIndex, completeJob);
    } else {
      addJob(completeJob);
    }
    setDialogOpen(false);
    setEditingIndex(null);
  };

  const handleDelete = (index: number) => {
    if (confirm('정말로 이 작업을 삭제하시겠습니까?')) {
      deleteJob(index);
    }
  };

  const handleCSVUpload = () => {
    // Mock CSV upload
    const mockJobs: Job[] = [
      {
        sector_id: "A",
        date: "2024-01-16",
        demand_kg: 350,
        tw_start: "08:00",
        tw_end: "11:00",
        priority: 1,
        lat: 35.9737,
        lon: 126.7414
      },
      {
        sector_id: "B",
        date: "2024-01-16",
        demand_kg: 280,
        tw_start: "13:00",
        tw_end: "16:00",
        priority: 2,
        lat: 35.9502,
        lon: 126.7043
      }
    ];
    
    mockJobs.forEach(job => addJob(job));
    alert('CSV 파일에서 2개의 작업이 추가되었습니다.');
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Briefcase className="w-5 h-5" />
          <h3 className="text-lg font-semibold">작업 관리 ({jobs.length}개)</h3>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleCSVUpload}>
            <Upload className="w-4 h-4 mr-2" />
            CSV 업로드 (더미)
          </Button>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button onClick={() => handleOpenDialog()}>
                <Plus className="w-4 h-4 mr-2" />
                작업 추가
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {editingIndex !== null ? '작업 수정' : '새 작업 등록'}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>섹터</Label>
                  <Select
                    value={formData.sector_id}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, sector_id: value }))}
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
                  <Label htmlFor="job-date">날짜</Label>
                  <Input
                    id="job-date"
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))}
                  />
                </div>
                
                <div>
                  <Label htmlFor="demand">수요량 (kg)</Label>
                  <Input
                    id="demand"
                    type="number"
                    value={formData.demand_kg}
                    onChange={(e) => setFormData(prev => ({ ...prev, demand_kg: parseInt(e.target.value) || 0 }))}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="job-tw-start">시작 시간</Label>
                    <Input
                      id="job-tw-start"
                      type="time"
                      value={formData.tw_start}
                      onChange={(e) => setFormData(prev => ({ ...prev, tw_start: e.target.value }))}
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="job-tw-end">종료 시간</Label>
                    <Input
                      id="job-tw-end"
                      type="time"
                      value={formData.tw_end}
                      onChange={(e) => setFormData(prev => ({ ...prev, tw_end: e.target.value }))}
                    />
                  </div>
                </div>
                
                <div>
                  <Label>우선순위</Label>
                  <Select
                    value={String(formData.priority)}
                    onValueChange={(value) => setFormData(prev => ({ ...prev, priority: parseInt(value) }))}
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
                
                <Button onClick={handleSubmit} className="w-full">
                  {editingIndex !== null ? '수정' : '등록'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>날짜</TableHead>
              <TableHead>섹터</TableHead>
              <TableHead>수요량</TableHead>
              <TableHead>시간창</TableHead>
              <TableHead>우선순위</TableHead>
              <TableHead>작업</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job, index) => {
              const sector = sectors.find(s => s.id === job.sector_id);
              return (
                <TableRow key={index}>
                  <TableCell>{job.date}</TableCell>
                  <TableCell>
                    <div>
                      <Badge variant="outline">{job.sector_id}</Badge>
                      {sector && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {sector.name}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{job.demand_kg}kg</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1 text-sm">
                      <Clock className="w-3 h-3" />
                      {job.tw_start} ~ {job.tw_end}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge 
                      variant="secondary"
                      className={
                        job.priority === 1 ? 'bg-red-100 text-red-800' :
                        job.priority === 2 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }
                    >
                      {job.priority === 1 ? '높음' : job.priority === 2 ? '보통' : '낮음'}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenDialog(job, index)}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(index)}
                        className="text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}