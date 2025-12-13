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
  vehicle_label?: string;
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
  total_time_min?: number;
  llm_explanation?: string | null;
}

export interface ChartData {
  weekly_co2: Array<{ date: string; co2: number }>;
  vehicle_distances: Array<{ vehicle: string; distance: number }>;
  sector_demands: Array<{ sector: string; demand: number }>;
}

export interface PolylinePoint {
  lat: number;
  lng: number;
}

export interface VehicleRouteStep {
  order?: number;
  name?: string;
  address?: string;
  sectorId?: string;
  arrivalTime?: string;
  departureTime?: string;
  distanceKm?: number;
  emissionKg?: number;
}

export interface VehicleRoute {
  vehicleId: string;
  vehicleName?: string;
  distanceKm?: number;
  emissionKg?: number;
  totalTimeMin?: number;
  steps?: VehicleRouteStep[];
  polyline?: PolylinePoint[];
}

export interface OptimizationSummary {
  route_name: string;
  total_distance_km?: number;
  total_co2_g?: number;
  total_time_min?: number;
  summary?: any;
  assignments?: any[];
  polyline?: number[][];
  start?: { lat: number; lng: number };
  end?: { lat: number; lng: number };
  [key: string]: any;
}

export interface ComparisonMetrics {
  co2_saving_g: number;
  co2_saving_pct: number;
  distance_diff_km?: number;
  distance_diff_pct?: number;
  time_diff_min?: number;
  baseline_route?: string;
  recommended_route?: string;
  baseline_provider?: string;
  recommended_provider?: string;
}

export interface BatchResult {
  status: 'success' | 'failed';
  run_id: string;
  optimization_result?: {
    status: string;
    run_id: string;
    results: OptimizationSummary[];
    comparison?: ComparisonMetrics;
  };
  message?: string;
  llm_explanation?: string | null;
}
