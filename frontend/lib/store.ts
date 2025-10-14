import { create } from 'zustand';
import { Vehicle, Sector, Job, Route, OptimizationRequest, KPIs, RunHistory, ChartData } from './types';
import { mockVehicles, mockSectors, mockJobs, mockRoutes, mockKPIs, mockRunHistory, mockChartData } from './mock-data';

interface AppStore {
  // Data
  vehicles: Vehicle[];
  sectors: Sector[];
  jobs: Job[];
  routes: Route[];
  kpis: KPIs;
  runHistory: RunHistory[];
  chartData: ChartData;
  
  // UI State
  selectedVehicles: string[];
  selectedSectors: string[];
  currentRequest: OptimizationRequest | null;
  isOptimizing: boolean;
  
  // Actions
  setVehicles: (vehicles: Vehicle[]) => void;
  setSectors: (sectors: Sector[]) => void;
  setJobs: (jobs: Job[]) => void;
  setSelectedVehicles: (vehicles: string[]) => void;
  setSelectedSectors: (sectors: string[]) => void;
  setCurrentRequest: (request: OptimizationRequest) => void;
  runOptimization: (request: OptimizationRequest) => void;
  addVehicle: (vehicle: Vehicle) => void;
  updateVehicle: (id: string, vehicle: Partial<Vehicle>) => void;
  deleteVehicle: (id: string) => void;
  addSector: (sector: Sector) => void;
  updateSector: (id: string, sector: Partial<Sector>) => void;
  deleteSector: (id: string) => void;
  addJob: (job: Job) => void;
  updateJob: (index: number, job: Partial<Job>) => void;
  deleteJob: (index: number) => void;
}

export const useStore = create<AppStore>((set, get) => ({
  // Initial data
  vehicles: mockVehicles,
  sectors: mockSectors, 
  jobs: mockJobs,
  routes: mockRoutes,
  kpis: mockKPIs,
  runHistory: mockRunHistory,
  chartData: mockChartData,
  
  // Initial UI state
  selectedVehicles: [],
  selectedSectors: [],
  currentRequest: null,
  isOptimizing: false,
  
  // Actions
  setVehicles: (vehicles) => set({ vehicles }),
  setSectors: (sectors) => set({ sectors }),
  setJobs: (jobs) => set({ jobs }),
  setSelectedVehicles: (vehicles) => set({ selectedVehicles: vehicles }),
  setSelectedSectors: (sectors) => set({ selectedSectors: sectors }),
  setCurrentRequest: (request) => set({ currentRequest: request }),
  
  runOptimization: async (request) => {
    set({ isOptimizing: true, currentRequest: request });
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Generate mock results based on request
    const routes = mockRoutes.filter(route => 
      request.vehicles.includes(route.vehicle_id)
    );
    
    const kpis = {
      total_distance_km: routes.reduce((sum, route) => sum + route.total_distance_km, 0),
      total_co2_kg: routes.reduce((sum, route) => sum + route.total_co2_kg, 0),
      total_time_min: Math.max(...routes.map(route => route.total_time_min)),
      saving_percent: Math.random() * 30 + 10 // 10-40% savings
    };
    
    set({ 
      routes,
      kpis,
      isOptimizing: false,
      runHistory: [
        {
          run_id: `RUN_${new Date().toISOString().split('T')[0].replace(/-/g, '')}_${String(Math.floor(Math.random() * 999)).padStart(3, '0')}`,
          date: request.run_date,
          total_distance: kpis.total_distance_km,
          total_co2: kpis.total_co2_kg,
          served_jobs: request.jobs.length
        },
        ...get().runHistory
      ]
    });
  },
  
  addVehicle: (vehicle) => set(state => ({ 
    vehicles: [...state.vehicles, vehicle] 
  })),
  
  updateVehicle: (id, updates) => set(state => ({
    vehicles: state.vehicles.map(v => v.id === id ? { ...v, ...updates } : v)
  })),
  
  deleteVehicle: (id) => set(state => ({
    vehicles: state.vehicles.filter(v => v.id !== id)
  })),
  
  addSector: (sector) => set(state => ({
    sectors: [...state.sectors, sector]
  })),
  
  updateSector: (id, updates) => set(state => ({
    sectors: state.sectors.map(s => s.id === id ? { ...s, ...updates } : s)
  })),
  
  deleteSector: (id) => set(state => ({
    sectors: state.sectors.filter(s => s.id !== id)
  })),
  
  addJob: (job) => set(state => ({
    jobs: [...state.jobs, job]
  })),
  
  updateJob: (index, updates) => set(state => ({
    jobs: state.jobs.map((job, i) => i === index ? { ...job, ...updates } : job)
  })),
  
  deleteJob: (index) => set(state => ({
    jobs: state.jobs.filter((_, i) => i !== index)
  }))
}));