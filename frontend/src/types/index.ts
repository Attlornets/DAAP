export type TransportMode = "driving" | "delivery_van" | "cycling" | "walking";
export type RoutingAlgorithm = "dijkstra" | "astar" | "ch";
export type VRPAlgorithm = "genetic" | "simulated_annealing" | "both";
export type CostMetric = "time" | "distance";

export interface ScenarioInfo {
  id: string;
  name: string;
  description: string;
  center: [number, number];
  zoom: number;
  default_mode: TransportMode;
}

export interface Depot {
  id: string;
  name: string;
  lat: number;
  lon: number;
  start_time: string;
}

export interface DeliveryStop {
  id: string;
  name: string;
  lat: number;
  lon: number;
  demand: number;
  service_time_s: number;
  earliest_time: string;
  latest_time: string;
}

export interface RouteLeg {
  from_node: string;
  to_node: string;
  road_name: string;
  road_type: string;
  distance_m: number;
  duration_s: number;
  speed_kmh: number;
  departure_time: string;
  arrival_time: string;
}

export interface RouteResponse {
  found: boolean;
  algorithm: string;
  source_node: string;
  target_node: string;
  distance_m: number;
  duration_s: number;
  departure_time: string;
  arrival_time?: string;
  nodes_settled: number;
  edges_relaxed: number;
  execution_time_ms: number;
  path_nodes: string[];
  path_coords: [number, number][];
  legs: RouteLeg[];
}

export interface BenchmarkMetric {
  algorithm: string;
  avg_latency_ms: number;
  median_latency_ms: number;
  avg_nodes_settled: number;
  avg_edges_relaxed: number;
  total_time_ms: number;
  speedup_vs_dijkstra: number;
}

export interface RoutingBenchmarkResponse {
  queries_tested: number;
  mode: TransportMode;
  metrics: Record<string, BenchmarkMetric>;
  query_samples: Array<{
    pair: string;
    dijkstra: { latency_ms: number; settled: number };
    astar: { latency_ms: number; settled: number };
    ch: { latency_ms: number; settled: number };
    distance_m: number;
  }>;
  ch_preprocessing_time_ms: number;
}

export interface StopTimelineEntry {
  stop_id: string;
  name: string;
  type: "depot_start" | "delivery" | "depot_end";
  arrival_time: string;
  departure_time: string;
  waiting_s: number;
  service_s: number;
  lat: number;
  lon: number;
  demand: number;
  load_remaining: number;
  earliest_time?: string;
  latest_time?: string;
  is_late: boolean;
  lateness_s: number;
}

export interface VehicleSchedule {
  vehicle_id: number;
  stop_count: number;
  total_distance_m: number;
  total_duration_s: number;
  travel_time_s: number;
  waiting_time_s: number;
  service_time_s: number;
  lateness_s: number;
  total_demand: number;
  capacity: number;
  capacity_utilization_pct: number;
  capacity_violation: number;
  timeline: StopTimelineEntry[];
}

export interface ConvergencePoint {
  generation?: number;
  step?: number;
  temperature?: number;
  best_cost: number;
  avg_cost?: number;
  current_cost?: number;
  best_distance_m: number;
  best_duration_s: number;
  lateness_s: number;
  capacity_excess: number;
  is_feasible: boolean;
  active_vehicles: number;
}

export interface VRPTWEvaluation {
  is_feasible: boolean;
  total_cost: number;
  total_distance_m: number;
  total_duration_s: number;
  total_travel_time_s: number;
  total_waiting_time_s: number;
  total_service_time_s: number;
  total_lateness_s: number;
  total_capacity_excess: number;
  active_vehicles: number;
  fleet_utilization_pct: number;
  late_penalty_cost: number;
  vehicle_schedules: VehicleSchedule[];
}

export interface VRPTWSolutionResult {
  algorithm: string;
  execution_time_ms: number;
  generations_run?: number;
  total_steps?: number;
  best_solution_routes: number[][];
  evaluation: VRPTWEvaluation;
  convergence_history: ConvergencePoint[];
}

export interface RoadEdgeViewport {
  id: number;
  source: string;
  target: string;
  coords: [number, number][];
  distance_m: number;
  road_type: string;
  speed_kmh: number;
  congestion_ratio: number;
  oneway: boolean;
}
