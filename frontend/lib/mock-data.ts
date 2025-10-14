import { Vehicle, Sector, Job, Route, RouteStep, KPIs, RunHistory, ChartData } from './types';

export const mockVehicles: Vehicle[] = [
  {
    id: "TRK01",
    type: "EV_1t",
    capacity_kg: 1000,
    fuel: "EV",
    ef_gpkm: 60,
    idle_gps: 12
  },
  {
    id: "TRK02", 
    type: "HYBRID_1.5t",
    capacity_kg: 1500,
    fuel: "HYBRID",
    ef_gpkm: 120,
    idle_gps: 8
  },
  {
    id: "TRK03",
    type: "DIESEL_2t", 
    capacity_kg: 2000,
    fuel: "DIESEL",
    ef_gpkm: 180,
    idle_gps: 15
  }
];

export const mockSectors: Sector[] = [
  {
    id: "A",
    name: "군산A구역",
    lat: 35.9737,
    lon: 126.7414,
    tw_start: "09:00",
    tw_end: "12:00", 
    priority: 2
  },
  {
    id: "B",
    name: "군산B구역",
    lat: 35.9502,
    lon: 126.7043,
    tw_start: "08:30",
    tw_end: "12:00",
    priority: 1
  },
  {
    id: "C", 
    name: "익산C구역",
    lat: 35.9428,
    lon: 127.0273,
    tw_start: "10:00",
    tw_end: "15:00",
    priority: 3
  },
  {
    id: "D",
    name: "전주D구역", 
    lat: 35.8242,
    lon: 127.1480,
    tw_start: "13:00",
    tw_end: "17:00",
    priority: 2
  }
];

export const mockJobs: Job[] = [
  {
    sector_id: "A",
    date: "2024-01-15",
    demand_kg: 300,
    tw_start: "09:00", 
    tw_end: "12:00",
    priority: 2,
    lat: 35.9737,
    lon: 126.7414
  },
  {
    sector_id: "B",
    date: "2024-01-15", 
    demand_kg: 400,
    tw_start: "08:30",
    tw_end: "12:00",
    priority: 1,
    lat: 35.9502,
    lon: 126.7043
  },
  {
    sector_id: "C",
    date: "2024-01-15",
    demand_kg: 250,
    tw_start: "10:00",
    tw_end: "15:00", 
    priority: 3,
    lat: 35.9428,
    lon: 127.0273
  }
];

export const mockRoutes: Route[] = [
  {
    vehicle_id: "TRK01",
    steps: [
      {
        sector_id: "A",
        arrival_time: "09:30",
        departure_time: "10:15",
        distance_km: 12.3,
        co2_kg: 0.74
      },
      {
        sector_id: "B", 
        arrival_time: "11:00",
        departure_time: "11:45",
        distance_km: 8.7,
        co2_kg: 0.52
      }
    ],
    total_distance_km: 21.0,
    total_co2_kg: 1.26,
    total_time_min: 195,
    polyline: [
      [126.7414, 35.9737],
      [126.7200, 35.9600],
      [126.7043, 35.9502]
    ]
  },
  {
    vehicle_id: "TRK02",
    steps: [
      {
        sector_id: "C",
        arrival_time: "10:30",
        departure_time: "11:15", 
        distance_km: 15.2,
        co2_kg: 1.82
      }
    ],
    total_distance_km: 15.2,
    total_co2_kg: 1.82,
    total_time_min: 105,
    polyline: [
      [127.0273, 35.9428],
      [127.0100, 35.9300]
    ]
  }
];

export const mockKPIs: KPIs = {
  total_distance_km: 36.2,
  total_co2_kg: 3.08,
  total_time_min: 300,
  saving_percent: 23.5
};

export const mockRunHistory: RunHistory[] = [
  {
    run_id: "RUN_20240115_001",
    date: "2024-01-15", 
    total_distance: 36.2,
    total_co2: 3.08,
    served_jobs: 3
  },
  {
    run_id: "RUN_20240114_001",
    date: "2024-01-14",
    total_distance: 42.1, 
    total_co2: 3.85,
    served_jobs: 4
  },
  {
    run_id: "RUN_20240113_001",
    date: "2024-01-13",
    total_distance: 38.9,
    total_co2: 3.42,
    served_jobs: 3
  }
];

export const mockChartData: ChartData = {
  weekly_co2: [
    { date: "2024-01-08", co2: 4.2 },
    { date: "2024-01-09", co2: 3.8 },
    { date: "2024-01-10", co2: 4.1 },
    { date: "2024-01-11", co2: 3.9 },
    { date: "2024-01-12", co2: 3.6 },
    { date: "2024-01-13", co2: 3.4 },
    { date: "2024-01-14", co2: 3.85 },
    { date: "2024-01-15", co2: 3.08 }
  ],
  vehicle_distances: [
    { vehicle: "TRK01", distance: 21.0 },
    { vehicle: "TRK02", distance: 15.2 },
    { vehicle: "TRK03", distance: 0 }
  ],
  sector_demands: [
    { sector: "A구역", demand: 300 },
    { sector: "B구역", demand: 400 },
    { sector: "C구역", demand: 250 },
    { sector: "D구역", demand: 0 }
  ]
};