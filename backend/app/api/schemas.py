"""
Pydantic Request and Response Schemas for RouteForge API.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LatLonPoint(BaseModel):
    lat: float
    lon: float


class RouteRequest(BaseModel):
    start: LatLonPoint
    end: LatLonPoint
    algorithm: str = Field(default="astar", description="dijkstra, astar, or ch")
    mode: str = Field(default="driving", description="driving, delivery_van, cycling, or walking")
    departure_time: str = Field(default="08:30", description="HH:MM format")
    cost_metric: str = Field(default="time", description="time or distance")


class RouteLeg(BaseModel):
    from_node: str
    to_node: str
    road_name: str
    road_type: str
    distance_m: float
    duration_s: float
    speed_kmh: float
    departure_time: str
    arrival_time: str


class RouteResponse(BaseModel):
    found: bool
    algorithm: str
    source_node: str
    target_node: str
    distance_m: float
    duration_s: float
    departure_time: str
    arrival_time: Optional[str]
    nodes_settled: int
    edges_relaxed: int
    execution_time_ms: float
    path_nodes: List[str]
    path_coords: List[List[float]]
    legs: List[RouteLeg]


class RoutingBenchmarkRequest(BaseModel):
    pair_count: int = Field(default=25, ge=5, le=100)
    mode: str = Field(default="driving")
    departure_time: str = Field(default="08:30")
    cost_metric: str = Field(default="time")


class BenchmarkMetric(BaseModel):
    algorithm: str
    avg_latency_ms: float
    median_latency_ms: float
    avg_nodes_settled: float
    avg_edges_relaxed: float
    total_time_ms: float
    speedup_vs_dijkstra: float


class RoutingBenchmarkResponse(BaseModel):
    queries_tested: int
    mode: str
    metrics: Dict[str, BenchmarkMetric]
    query_samples: List[Dict[str, Any]]
    ch_preprocessing_time_ms: float


class DeliveryStopSchema(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    demand: float = 10.0
    service_time_s: float = 300.0
    earliest_time: str = "08:30"
    latest_time: str = "10:00"


class DepotSchema(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    start_time: str = "08:00"


class VRPTWSolveRequest(BaseModel):
    algorithm: str = Field(default="genetic", description="genetic, simulated_annealing, or both")
    fleet_size: int = Field(default=3, ge=1, le=10)
    vehicle_capacity: float = Field(default=90.0, ge=10.0, le=1000.0)
    late_penalty_per_min: float = Field(default=2.5, ge=0.0)
    depot: Optional[DepotSchema] = None
    stops: Optional[List[DeliveryStopSchema]] = None
    iterations: int = Field(default=80, ge=10, le=300)
    population_size: int = Field(default=40, ge=10, le=150)


class ScenarioSelectRequest(BaseModel):
    scenario_id: str = Field(..., description="san_francisco, manhattan, or london")


class OverpassLoadRequest(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    name: str = "Custom OSM Region"
