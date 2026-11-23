import {
  CostMetric,
  DeliveryStop,
  Depot,
  RoadEdgeViewport,
  RouteResponse,
  RoutingAlgorithm,
  RoutingBenchmarkResponse,
  ScenarioInfo,
  TransportMode,
  VRPTWSolutionResult,
} from "../types";

const API_BASE = "/api";

export async function fetchScenarios(): Promise<{
  active_scenario: string;
  scenarios: ScenarioInfo[];
}> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error("Failed to fetch scenarios");
  return res.json();
}

export async function selectScenario(scenarioId: string): Promise<{
  success: boolean;
  scenario_id: string;
  metadata: any;
  node_count: number;
  edge_count: number;
  bounds: { min_lat: number; min_lon: number; max_lat: number; max_lon: number };
  depot: Depot;
  stops: DeliveryStop[];
}> {
  const res = await fetch(`${API_BASE}/scenarios/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!res.ok) throw new Error("Failed to switch scenario");
  return res.json();
}

export async function fetchGraphInfo(): Promise<{
  scenario_id: string;
  name: string;
  node_count: number;
  edge_count: number;
  bounds: { min_lat: number; min_lon: number; max_lat: number; max_lon: number };
  center: [number, number];
  zoom: number;
}> {
  const res = await fetch(`${API_BASE}/graph/info`);
  if (!res.ok) throw new Error("Failed to fetch graph info");
  return res.json();
}

export async function fetchGraphViewport(
  bounds: { min_lat: number; min_lon: number; max_lat: number; max_lon: number },
  departureTime: string = "08:30",
  mode: TransportMode = "driving"
): Promise<{
  node_count: number;
  edge_count: number;
  edges: RoadEdgeViewport[];
}> {
  const params = new URLSearchParams({
    min_lat: bounds.min_lat.toString(),
    min_lon: bounds.min_lon.toString(),
    max_lat: bounds.max_lat.toString(),
    max_lon: bounds.max_lon.toString(),
    departure_time: departureTime,
    mode: mode,
    max_edges: "600",
  });
  const res = await fetch(`${API_BASE}/graph/viewport?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch graph viewport");
  return res.json();
}

export async function computeRoute(
  start: { lat: number; lon: number },
  end: { lat: number; lon: number },
  algorithm: RoutingAlgorithm = "astar",
  mode: TransportMode = "driving",
  departureTime: string = "08:30",
  costMetric: CostMetric = "time"
): Promise<RouteResponse> {
  const res = await fetch(`${API_BASE}/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      start,
      end,
      algorithm,
      mode,
      departure_time: departureTime,
      cost_metric: costMetric,
    }),
  });
  if (!res.ok) throw new Error("Routing failed");
  return res.json();
}

export async function runRoutingBenchmark(
  pairCount: number = 25,
  mode: TransportMode = "driving",
  departureTime: string = "08:30",
  costMetric: CostMetric = "time"
): Promise<RoutingBenchmarkResponse> {
  const res = await fetch(`${API_BASE}/benchmark/routing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pair_count: pairCount,
      mode,
      departure_time: departureTime,
      cost_metric: costMetric,
    }),
  });
  if (!res.ok) throw new Error("Benchmark failed");
  return res.json();
}

export async function solveVRPTW(
  algorithm: "genetic" | "simulated_annealing" | "both" = "genetic",
  fleetSize: number = 3,
  vehicleCapacity: number = 90.0,
  depot?: Depot,
  stops?: DeliveryStop[],
  iterations: number = 80,
  populationSize: number = 40
): Promise<{
  algorithm: string;
  scenario: string;
  fleet_size: number;
  vehicle_capacity: number;
  depot: Depot;
  solution?: VRPTWSolutionResult;
  results?: {
    genetic: VRPTWSolutionResult;
    simulated_annealing: VRPTWSolutionResult;
  };
}> {
  const res = await fetch(`${API_BASE}/vrptw/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      algorithm,
      fleet_size: fleetSize,
      vehicle_capacity: vehicleCapacity,
      depot: depot
        ? {
            id: depot.id,
            name: depot.name,
            lat: depot.lat,
            lon: depot.lon,
            start_time: depot.start_time,
          }
        : undefined,
      stops: stops
        ? stops.map((s) => ({
            id: s.id,
            name: s.name,
            lat: s.lat,
            lon: s.lon,
            demand: s.demand,
            service_time_s: s.service_time_s,
            earliest_time: s.earliest_time,
            latest_time: s.latest_time,
          }))
        : undefined,
      iterations,
      population_size: populationSize,
    }),
  });
  if (!res.ok) throw new Error("VRPTW optimization failed");
  return res.json();
}

export async function benchmarkVRPTW(): Promise<{
  scenario: string;
  genetic: any;
  simulated_annealing: any;
}> {
  const res = await fetch(`${API_BASE}/vrptw/benchmark`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("VRPTW benchmark failed");
  return res.json();
}
