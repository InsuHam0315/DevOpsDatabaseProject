import { create } from 'zustand';

import {
  Vehicle,
  Sector,
  Job,
  Route,
  OptimizationRequest,
  KPIs,
  RunHistory,
  ChartData,
  BatchResult,
  VehicleRoute
} from './types';

import {
  mockVehicles,
  mockSectors,
  mockJobs,
  mockRoutes,
  mockKPIs,
  mockRunHistory,
  mockChartData
} from './mock-data';

const DEFAULT_KPIS: KPIs = {
  total_distance_km: 0,
  total_co2_kg: 0,
  total_time_min: 0,
  saving_percent: 0
};

const ensureKpis = (value?: Partial<KPIs> | null): KPIs => ({
  ...DEFAULT_KPIS,
  ...(value || {})
});

const toNumber = (value: any, divider = 1): number => {
  if (value === null || value === undefined) return 0;
  const numeric = typeof value === 'number' ? value : parseFloat(value);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  return divider !== 1 ? numeric / divider : numeric;
};

const parseDistanceKm = (route: any): number => {
  return toNumber(
    route?.total_distance_km ??
      route?.distance_km ??
      route?.total_distance ??
      route?.distance ??
      route?.summary?.total_distance_km ??
      route?.summary?.distance_km
  );
};

const parseCo2Kg = (route: any): number => {
  if (route?.total_co2_kg !== undefined) return toNumber(route.total_co2_kg);
  if (route?.co2_kg !== undefined) return toNumber(route.co2_kg);
  if (route?.emission_kg !== undefined) return toNumber(route.emission_kg);
  if (route?.summary?.total_co2_kg !== undefined) return toNumber(route.summary.total_co2_kg);
  if (route?.summary?.co2_kg !== undefined) return toNumber(route.summary.co2_kg);

  const gramsSource =
    route?.total_co2_g ??
    route?.co2_g ??
    route?.summary?.total_co2_g ??
    route?.summary?.co2_g;

  if (gramsSource !== undefined) {
    return toNumber(gramsSource, 1000);
  }
  return 0;
};

const toPolylinePoints = (route: any): { lat: number; lng: number }[] => {
  const rawPolyline = route?.polyline ?? route?.path ?? route?.coordinates ?? route?.points;
  const fromArrayPairs =
    Array.isArray(rawPolyline) && rawPolyline.every((point: any) => Array.isArray(point) && point.length >= 2);
  if (fromArrayPairs) {
    return (rawPolyline as any[])
      .map((point) => {
        const [lng, lat] = point;
        if (typeof lat === 'number' && typeof lng === 'number') {
          return { lat, lng };
        }
        return null;
      })
      .filter(Boolean) as { lat: number; lng: number }[];
  }

  if (Array.isArray(rawPolyline)) {
    return rawPolyline
      .map((point: any) => {
        const lat = point?.lat ?? point?.latitude;
        const lng = point?.lng ?? point?.lon ?? point?.longitude;
        if (typeof lat === 'number' && typeof lng === 'number') {
          return { lat, lng };
        }
        return null;
      })
      .filter(Boolean) as { lat: number; lng: number }[];
  }

  const steps = Array.isArray(route?.steps) ? route.steps : Array.isArray(route?.assignments) ? route.assignments : [];
  if (steps.length) {
    return steps
      .map((step: any) => {
        const lat = step?.lat ?? step?.latitude ?? step?.end_lat;
        const lng = step?.lng ?? step?.lon ?? step?.longitude ?? step?.end_lng;
        if (typeof lat === 'number' && typeof lng === 'number') {
          return { lat, lng };
        }
        return null;
      })
      .filter(Boolean) as { lat: number; lng: number }[];
  }

  return [];
};

const buildVehicleRoutes = (routes: any[] | undefined, vehicles: Vehicle[]): VehicleRoute[] => {
  if (!Array.isArray(routes)) return [];
  return routes
    .map((route, index) => {
      const vehicleId =
        route?.vehicle_id ??
        route?.vehicleId ??
        route?.vehicle ??
        route?.route_name ??
        route?.id ??
        `vehicle-${index + 1}`;
      if (!vehicleId) return null;
      const vehicleMeta = vehicles.find((v) => v.id === vehicleId);
      const label =
        route?.vehicle_label ||
        route?.vehicle_name ||
        route?.vehicle_type ||
        vehicleMeta?.type ||
        vehicleMeta?.id ||
        vehicleId;

      const polyline = toPolylinePoints(route);
      const totalTime =
        route?.total_time_min ??
        route?.total_time ??
        route?.summary?.total_time_min ??
        route?.summary?.total_time ??
        undefined;

      const steps = Array.isArray(route?.steps)
        ? route.steps.map((step: any, stepIndex: number) => {
            const rawDistance = step?.distance_km ?? step?.distanceKm ?? step?.distance;
            const rawEmission =
              step?.co2_kg ??
              step?.emission_kg ??
              (step?.co2_g !== undefined ? step.co2_g / 1000 : undefined);
            return {
              order: step?.order ?? step?.step_order ?? stepIndex + 1,
              name: step?.name ?? step?.label ?? step?.sector_id ?? step?.sectorId,
              address: step?.address ?? step?.resolved_address,
              sectorId: step?.sector_id ?? step?.sectorId,
              arrivalTime: step?.arrival_time ?? step?.arrivalTime,
              departureTime: step?.departure_time ?? step?.departureTime,
              distanceKm: rawDistance !== undefined ? toNumber(rawDistance) : undefined,
              emissionKg: rawEmission !== undefined ? toNumber(rawEmission) : undefined
            };
          })
        : undefined;

      return {
        vehicleId,
        vehicleName: label,
        distanceKm: Math.round(parseDistanceKm(route) * 100) / 100,
        emissionKg: Math.round(parseCo2Kg(route) * 1000) / 1000,
        totalTimeMin: totalTime !== undefined ? Math.round(toNumber(totalTime) * 100) / 100 : undefined,
        polyline: polyline.length ? polyline : undefined,
        steps
      } as VehicleRoute;
    })
    .filter((summary): summary is VehicleRoute => Boolean(summary));
};

const collectVehicleRouteCandidatesFromBatch = (results: BatchResult[] | undefined | null): any[] => {
  if (!Array.isArray(results)) return [];
  const candidates: any[] = [];
  results.forEach((batchResult) => {
    const optimization: any = batchResult?.optimization_result;
    if (!optimization) return;
    const directCandidates = [
      optimization.vehicle_routes,
      optimization.routes,
      optimization.assignments,
      optimization.optimized_routes
    ].filter(Array.isArray);
    directCandidates.forEach((arr) => candidates.push(...arr));

    if (Array.isArray(optimization.results)) {
      optimization.results.forEach((summary: any) => {
        if (Array.isArray(summary)) {
          candidates.push(...summary);
          return;
        }
        [summary.vehicle_routes, summary.routes, summary.assignments].filter(Array.isArray).forEach((arr: any[]) => {
          candidates.push(...arr);
        });
        if (summary?.summary) {
          candidates.push({ ...summary.summary, route_name: summary.route_name });
        }
      });
    }
  });
  return candidates;
};

const parseKpisFromExplanation = (expl?: string): { total_distance_km?: number; total_co2_kg?: number; total_time_min?: number } | null => {
  if (!expl) return null;
  try {
    const textValue = String(expl);
    const num = (s: string) => parseFloat(s.replace(/,/g, ''));
    const co2Match = textValue.match(/([0-9]{1,3}(?:[,\d]*)(?:\.\d+)?)\s*(?:kg|킬로그램)\b/i);
    const total_co2_kg = co2Match ? num(co2Match[1]) : undefined;
    const distMatch = textValue.match(/([0-9]{1,3}(?:[,\d]*)(?:\.\d+)?)\s*(?:km|킬로미터)\b/i);
    const total_distance_km = distMatch ? num(distMatch[1]) : undefined;
    const hoursMatch = textValue.match(/([0-9]{1,3}(?:\.\d+)?)\s*(?:시간|hour|hours|hrs?)/i);
    const minsMatch = textValue.match(/([0-9]{1,3}(?:\.\d+)?)\s*(?:분|minutes?|mins?)/i);
    let total_time_min: number | undefined = undefined;
    if (hoursMatch || minsMatch) {
      const h = hoursMatch ? num(hoursMatch[1]) : 0;
      const m = minsMatch ? num(minsMatch[1]) : 0;
      total_time_min = Math.round((h * 60 + m) * 100) / 100;
    } else {
      const onlyMin = textValue.match(/([0-9]{1,3}(?:\.\d+)?)\s*(?:분|minutes?|mins?)/i);
      if (onlyMin) total_time_min = num(onlyMin[1]);
    }
    return { total_distance_km, total_co2_kg, total_time_min };
  } catch (e) {
    return null;
  }
};

interface DashboardPayload {
  kpis?: Partial<KPIs> | null;
  runHistory?: RunHistory[] | null;
}

interface AppStore {
  vehicles: Vehicle[];
  sectors: Sector[];
  jobs: Job[];
  routes: Route[];
  vehicleRoutes: VehicleRoute[];
  kpis: KPIs;
  runHistory: RunHistory[];
  chartData: ChartData;
  batchResults: BatchResult[];
  dashboardKpis: KPIs;
  dashboardRunHistory: RunHistory[];

  selectedVehicles: string[];
  selectedSectors: string[];
  currentRequest: OptimizationRequest | null;
  isOptimizing: boolean;
  isAuthenticated: boolean;
  currentUser: string | null;
  users: { username: string; password: string }[];

  setVehicles: (vehicles: Vehicle[]) => void;
  setSectors: (sectors: Sector[]) => void;
  setJobs: (jobs: Job[]) => void;
  setSelectedVehicles: (vehicles: string[]) => void;
  setSelectedSectors: (sectors: string[]) => void;
  setCurrentRequest: (request: OptimizationRequest | null) => void;
  setBatchResults: (results: BatchResult[]) => void;
  setDashboardData: (payload: DashboardPayload) => void;

  runOptimization: (request: OptimizationRequest) => Promise<void>;

  addVehicle: (vehicle: Vehicle) => void;
  updateVehicle: (id: string, vehicle: Partial<Vehicle>) => void;
  deleteVehicle: (id: string) => void;

  addSector: (sector: Sector) => void;
  updateSector: (id: string, sector: Partial<Sector>) => void;
  deleteSector: (id: string) => void;

  addJob: (job: Job) => void;
  updateJob: (index: number, job: Partial<Job>) => void;
  deleteJob: (index: number) => void;

  login: (username: string, password: string) => boolean;
  register: (username: string, password: string) => boolean;
  logout: () => void;
}

export const useStore = create<AppStore>((set, get) => ({
  vehicles: mockVehicles,
  sectors: mockSectors,
  jobs: mockJobs,
  routes: mockRoutes,
  vehicleRoutes: buildVehicleRoutes(mockRoutes, mockVehicles),
  kpis: mockKPIs,
  runHistory: mockRunHistory,
  chartData: mockChartData,
  batchResults: [],
  dashboardKpis: mockKPIs,
  dashboardRunHistory: mockRunHistory,

  selectedVehicles: [],
  selectedSectors: [],
  currentRequest: null,
  isOptimizing: false,
  isAuthenticated: false,
  currentUser: null,
  users: [{ username: 'admin', password: '1234' }],

  setVehicles: (vehicles) => set({ vehicles }),
  setSectors: (sectors) => set({ sectors }),
  setJobs: (jobs) => set({ jobs }),
  setSelectedVehicles: (vehicles) => set({ selectedVehicles: vehicles }),
  setSelectedSectors: (sectors) => set({ selectedSectors: sectors }),
  setCurrentRequest: (request) => set({ currentRequest: request }),

  setBatchResults: (results) =>
    set((state) => {
      const safeResults = Array.isArray(results) ? results : [];
      const runHistoryEntries = safeResults
        .map((br) => {
          const optimization: any = br.optimization_result;
          const summaries = Array.isArray(optimization?.results) ? optimization.results : [];
          if (!summaries.length) return null;
          const totals = summaries.reduce(
            (acc: { distance: number; co2: number; time: number }, summary: any) => {
              acc.distance += toNumber(summary.total_distance_km ?? summary.total_distance);
              if (summary.total_co2_g !== undefined) {
                acc.co2 += toNumber(summary.total_co2_g, 1000);
              } else {
                acc.co2 += toNumber(summary.total_co2_kg ?? summary.total_co2);
              }
              acc.time += toNumber(summary.total_time_min ?? summary.total_time);
              return acc;
            },
            { distance: 0, co2: 0, time: 0 }
          );
          return {
            run_id: br.run_id || optimization?.run_id || `run_${Date.now()}`,
            date: new Date().toISOString(),
            total_distance: Math.round(totals.distance * 100) / 100,
            total_co2: Math.round(totals.co2 * 100) / 100,
            total_time_min: Math.round(totals.time * 100) / 100,
            served_jobs: summaries.length,
            llm_explanation: br.llm_explanation ?? null
          } as RunHistory;
        })
        .filter(Boolean) as RunHistory[];

      const combinedRunHistory = [...runHistoryEntries, ...state.runHistory];
      const aggregate = combinedRunHistory.reduce(
        (acc, entry) => {
          acc.total_distance += toNumber(entry.total_distance);
          acc.total_co2 += toNumber(entry.total_co2);
          acc.served_jobs += toNumber(entry.served_jobs);
          acc.total_time_min += toNumber((entry as any).total_time_min);
          return acc;
        },
        { total_distance: 0, total_co2: 0, served_jobs: 0, total_time_min: 0 }
      );

      const baseKpis = ensureKpis({
        total_distance_km: Math.round(aggregate.total_distance * 100) / 100,
        total_co2_kg: Math.round(aggregate.total_co2 * 100) / 100,
        total_time_min: Math.round(aggregate.total_time_min * 100) / 100,
        saving_percent:
          safeResults?.[0]?.optimization_result?.comparison?.co2_saving_pct ??
          state.kpis.saving_percent ??
          0
      });

      const explanationKpis = parseKpisFromExplanation(
        safeResults.find((item) => typeof item.llm_explanation === 'string')?.llm_explanation ?? undefined
      );

      const vehicleRouteCandidates = collectVehicleRouteCandidatesFromBatch(safeResults);
      const vehicleRoutes = buildVehicleRoutes(vehicleRouteCandidates, state.vehicles);

      return {
        batchResults: safeResults,
        runHistory: combinedRunHistory,
        kpis: explanationKpis ? ensureKpis({ ...baseKpis, ...explanationKpis }) : baseKpis,
        vehicleRoutes
      };
    }),

  setDashboardData: (payload) =>
    set((state) => ({
      dashboardKpis: ensureKpis(payload?.kpis ?? state.dashboardKpis),
      dashboardRunHistory: Array.isArray(payload?.runHistory) ? payload!.runHistory : state.dashboardRunHistory
    })),

  addVehicle: (vehicle) => set((state) => ({ vehicles: [...state.vehicles, vehicle] })),
  updateVehicle: (id, updates) =>
    set((state) => ({
      vehicles: state.vehicles.map((vehicle) => (vehicle.id === id ? { ...vehicle, ...updates } : vehicle))
    })),
  deleteVehicle: (id) =>
    set((state) => ({
      vehicles: state.vehicles.filter((vehicle) => vehicle.id !== id)
    })),

  addSector: (sector) => set((state) => ({ sectors: [...state.sectors, sector] })),
  updateSector: (id, updates) =>
    set((state) => ({
      sectors: state.sectors.map((sector) => (sector.id === id ? { ...sector, ...updates } : sector))
    })),
  deleteSector: (id) =>
    set((state) => ({
      sectors: state.sectors.filter((sector) => sector.id !== id)
    })),

  addJob: (job) => set((state) => ({ jobs: [...state.jobs, job] })),
  updateJob: (index, updates) =>
    set((state) => ({
      jobs: state.jobs.map((job, i) => (i === index ? { ...job, ...updates } : job))
    })),
  deleteJob: (index) =>
    set((state) => ({
      jobs: state.jobs.filter((_, i) => i !== index)
    })),

  runOptimization: async (request) => {
    set({ isOptimizing: true, currentRequest: request });
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5000';
      const response = await fetch(`${apiBase}/api/optimize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      const normalizedRoutes = Array.isArray(result.routes) ? result.routes : [];
      const vehicleRoutes = buildVehicleRoutes(normalizedRoutes, get().vehicles);
      const historyEntry = result.run_history_entry
        ? [{ ...result.run_history_entry } as RunHistory]
        : [];

      set((state) => ({
        routes: normalizedRoutes as Route[],
        vehicleRoutes,
        kpis: ensureKpis(result.kpis),
        runHistory: historyEntry.length ? [...historyEntry, ...state.runHistory] : state.runHistory,
        isOptimizing: false
      }));
    } catch (error) {
      console.error('Optimization failed:', error);
      set({ isOptimizing: false });
    }
  },

  login: (username, password) => {
    const users = get().users || [];
    const user = users.find((u) => u.username === username && u.password === password);
    if (user) {
      set({ isAuthenticated: true, currentUser: username });
      return true;
    }
    return false;
  },

  register: (username, password) => {
    const users = get().users || [];
    if (users.find((u) => u.username === username)) return false;
    set({ users: [...users, { username, password }] });
    return true;
  },

  logout: () => set({ isAuthenticated: false, currentUser: null })
}));

