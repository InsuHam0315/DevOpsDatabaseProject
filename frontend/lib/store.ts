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

    try {
      // --------------------------------------------------------
      // 1. 여기가 바로 app.py (백엔드)로 JSON을 전송하는 부분입니다.
      // --------------------------------------------------------
      const response = await fetch('http://localhost:5000/api/optimize', { // ⬅️ (1) app.py의 API 주소
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request), // ⬅️ (2) "경로 계획" 폼 데이터를 JSON으로 보냄
      });

      if (!response.ok) {
        // 백엔드에서 에러가 났을 때
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // --------------------------------------------------------
      // 2. 여기가 app.py가 돌려준 진짜 JSON 결과를 파싱(분해)하는 부분입니다.
      // --------------------------------------------------------
      const result = await response.json(); // ⬅️ (3) 백엔드가 준 JSON 결과를 받음
      const { routes, kpis, run_history_entry } = result; // ⬅️ (4) JSON 분해

      // 3. 받은 "진짜" 데이터로 화면을 업데이트합니다. (표현하기)
      set({ 
        routes: routes,     // ⬅️ (5) 진짜 경로
        kpis: kpis,         // ⬅️ (6) 진짜 지표
        isOptimizing: false,
        runHistory: [run_history_entry, ...get().runHistory] // ⬅️ (7) 진짜 실행 이력
      });

    } catch (error) {
      // fetch나 파싱 과정에서 에러가 났을 때
      console.error("최적화 실패 (Optimization failed):", error);
      set({ isOptimizing: false });
    }
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