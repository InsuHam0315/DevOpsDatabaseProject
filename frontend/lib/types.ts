export interface Vehicle {
  id: string;
  type: string;
  capacity_kg: number;
  fuel: string;
  ef_gpkm: number; // emission factor grams per km
  idle_gps: number; // idle grams per second
}

export interface Sector {
  id: string;
  name: string;
  lat: number;
  lon: number;
  tw_start: string;
  tw_end: string;
  priority: number;
}

export interface Job {
  sector_id: string;
  date: string;
  demand_kg: number;
  tw_start: string;
  tw_end: string;
  priority: number;
  lat: number;
  lon: number;
}

export interface Route {
  vehicle_id: string;
  steps: RouteStep[];
  total_distance_km: number;
  total_co2_kg: number;
  total_time_min: number;
  polyline: number[][];
}

export interface RouteStep {
  sector_id: string;
  arrival_time: string;
  departure_time: string;
  distance_km: number;
  co2_kg: number;
}

export interface OptimizationRequest {
  run_date: string;
  vehicles: string[];
  jobs: Job[];
}

export interface KPIs {
  total_distance_km: number;
  total_co2_kg: number;
  total_time_min: number;
  saving_percent: number;
}

export interface RunHistory {
  run_id: string;
  date: string;
  total_distance: number;
  total_co2: number;
  served_jobs: number;
}

export interface ChartData {
  weekly_co2: Array<{ date: string; co2: number }>;
  vehicle_distances: Array<{ vehicle: string; distance: number }>;
  sector_demands: Array<{ sector: string; demand: number }>;
}

//------------------------------------------------LLM 결과표출
export interface OptimizationSummary {
  route_name: string;
  total_distance_km: number;
  total_co2_g: number;
  total_time_min: number;
}


export interface BatchResult {
  status: 'success' | 'failed';
  run_id: string;
  optimization_result?: {
    status: string;
    run_id: string;
    results: OptimizationSummary[];
    comparison?: {
      co2_saving_g: number;
      co2_saving_pct: number;
    };
  };
  message?: string;
  llm_explanation?: string | null;
}
//------------------------------------------------