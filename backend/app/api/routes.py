"""
FastAPI Routes for RouteForge: Routing, Spatial Indexing, Contraction Hierarchies, and VRPTW.
"""
import copy
import random
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import (
    OverpassLoadRequest,
    RouteLeg,
    RouteRequest,
    RouteResponse,
    RoutingBenchmarkRequest,
    RoutingBenchmarkResponse,
    ScenarioSelectRequest,
    VRPTWSolveRequest,
)
from app.algorithms.astar import run_astar
from app.algorithms.ch import ContractionHierarchy
from app.algorithms.dijkstra import run_dijkstra
from app.algorithms.vrptw_ga import VRPTWGeneticAlgorithm
from app.algorithms.vrptw_models import DeliveryStop, Depot, VRPTWProblem, evaluate_solution
from app.algorithms.vrptw_sa import VRPTWSimulatedAnnealing
from app.core.time_dependent import parse_time_to_seconds, format_seconds_to_time
from app.data.preset_cities import (
    generate_london_scenario,
    generate_manhattan_scenario,
    generate_san_francisco_scenario,
)

router = APIRouter(prefix="/api")

# In-Memory State Manager
class ScenarioState:
    def __init__(self):
        self.active_scenario_id = "san_francisco"
        self.graph = None
        self.problem = None
        self.metadata = None
        # Cache for Contraction Hierarchies: (scenario_id, mode, metric) -> ContractionHierarchy
        self.ch_cache: Dict[Tuple[str, str, str], ContractionHierarchy] = {}
        self.load_scenario("san_francisco")

    def load_scenario(self, scenario_id: str):
        if scenario_id == "san_francisco":
            self.graph, self.problem, self.metadata = generate_san_francisco_scenario()
        elif scenario_id == "manhattan":
            self.graph, self.problem, self.metadata = generate_manhattan_scenario()
        elif scenario_id == "london":
            self.graph, self.problem, self.metadata = generate_london_scenario()
        else:
            raise ValueError(f"Unknown scenario ID: {scenario_id}")
        self.active_scenario_id = scenario_id

    def get_or_build_ch(self, mode: str, cost_metric: str) -> ContractionHierarchy:
        key = (self.active_scenario_id, mode, cost_metric)
        if key not in self.ch_cache:
            ch = ContractionHierarchy(self.graph, mode=mode, cost_metric=cost_metric)
            ch.preprocess()
            self.ch_cache[key] = ch
        return self.ch_cache[key]


state = ScenarioState()


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.get("/scenarios")
def list_scenarios():
    return {
        "active_scenario": state.active_scenario_id,
        "scenarios": [
            {
                "id": "san_francisco",
                "name": "San Francisco (Financial District & SoMa)",
                "description": "Dense urban grid, Market Street arterial diagonal, highway connectors, and morning rush-hour bottlenecks.",
                "center": [37.7850, -122.4020],
                "zoom": 14,
                "default_mode": "driving"
            },
            {
                "id": "manhattan",
                "name": "Manhattan (Midtown & Hudson Yards)",
                "description": "High-density avenues, alternating one-way cross streets, Times Square Broadway crossing, and heavy delivery constraints.",
                "center": [40.7550, -73.9850],
                "zoom": 14,
                "default_mode": "delivery_van"
            },
            {
                "id": "london",
                "name": "London (Westminster & The City)",
                "description": "Historic Thames crossings, irregular road geometry, and multi-modal cycling delivery zones.",
                "center": [51.5080, -0.1080],
                "zoom": 14,
                "default_mode": "cycling"
            }
        ]
    }


@router.post("/scenarios/select")
def select_scenario(req: ScenarioSelectRequest):
    try:
        state.load_scenario(req.scenario_id)
        bounds = state.graph.get_bounds()
        return {
            "success": True,
            "scenario_id": state.active_scenario_id,
            "metadata": state.metadata,
            "node_count": len(state.graph.nodes),
            "edge_count": len(state.graph.edges),
            "bounds": bounds,
            "depot": {
                "id": state.problem.depot.id,
                "name": state.problem.depot.name,
                "lat": state.problem.depot.lat,
                "lon": state.problem.depot.lon,
                "start_time": format_seconds_to_time(state.problem.depot.start_time_s)
            },
            "stops": [
                {
                    "id": s.id,
                    "name": s.name,
                    "lat": s.lat,
                    "lon": s.lon,
                    "demand": s.demand,
                    "service_time_s": s.service_time_s,
                    "earliest_time": format_seconds_to_time(s.earliest_arrival_s),
                    "latest_time": format_seconds_to_time(s.latest_arrival_s)
                }
                for s in state.problem.stops
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/graph/info")
def get_graph_info():
    bounds = state.graph.get_bounds()
    return {
        "scenario_id": state.active_scenario_id,
        "name": state.graph.name,
        "node_count": len(state.graph.nodes),
        "edge_count": len(state.graph.edges),
        "bounds": bounds,
        "center": state.metadata.get("center", [(bounds["min_lat"] + bounds["max_lat"]) / 2, (bounds["min_lon"] + bounds["max_lon"]) / 2]),
        "zoom": state.metadata.get("default_zoom", 14),
        "modes": ["driving", "delivery_van", "cycling", "walking"],
        "algorithms": ["dijkstra", "astar", "contraction_hierarchies"]
    }


@router.get("/graph/viewport")
def get_graph_viewport(
    min_lat: float = Query(...),
    min_lon: float = Query(...),
    max_lat: float = Query(...),
    max_lon: float = Query(...),
    departure_time: str = Query("08:30"),
    mode: str = Query("driving"),
    max_edges: int = Query(800)
):
    dep_seconds = parse_time_to_seconds(departure_time)
    limit = max_edges.default if hasattr(max_edges, "default") else max_edges
    elements = state.graph.get_viewport_elements(
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        departure_time_seconds=dep_seconds,
        mode=mode,
        max_edges=int(limit)
    )
    return elements


@router.post("/route", response_model=RouteResponse)
def compute_route(req: RouteRequest):
    dep_seconds = parse_time_to_seconds(req.departure_time)

    # Snap coordinates to nearest nodes
    start_snap = state.graph.find_nearest_node(req.start.lat, req.start.lon)
    end_snap = state.graph.find_nearest_node(req.end.lat, req.end.lon)

    if not start_snap or not end_snap:
        raise HTTPException(status_code=400, detail="Could not snap start or end point to road graph")

    src_node_id, _ = start_snap
    tgt_node_id, _ = end_snap

    algo = req.algorithm.lower()

    if algo == "dijkstra":
        res = run_dijkstra(
            state.graph,
            src_node_id,
            tgt_node_id,
            mode=req.mode,
            departure_time_seconds=dep_seconds,
            cost_metric=req.cost_metric
        )
    elif algo in ("astar", "a*"):
        res = run_astar(
            state.graph,
            src_node_id,
            tgt_node_id,
            mode=req.mode,
            departure_time_seconds=dep_seconds,
            cost_metric=req.cost_metric
        )
    elif algo in ("ch", "contraction_hierarchies"):
        ch = state.get_or_build_ch(req.mode, req.cost_metric)
        res = ch.query(
            src_node_id,
            tgt_node_id,
            departure_time_seconds=dep_seconds
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported algorithm '{algo}'")

    legs_pydantic = [
        RouteLeg(
            from_node=l["from_node"],
            to_node=l["to_node"],
            road_name=l["road_name"],
            road_type=l["road_type"],
            distance_m=l["distance_m"],
            duration_s=l["duration_s"],
            speed_kmh=l["speed_kmh"],
            departure_time=l["departure_time"],
            arrival_time=l["arrival_time"]
        )
        for l in res.get("legs", [])
    ]

    return RouteResponse(
        found=res.get("found", False),
        algorithm=res.get("algorithm", algo),
        source_node=src_node_id,
        target_node=tgt_node_id,
        distance_m=res.get("distance_m", 0.0),
        duration_s=res.get("duration_s", 0.0),
        departure_time=req.departure_time,
        arrival_time=res.get("arrival_time"),
        nodes_settled=res.get("nodes_settled", 0),
        edges_relaxed=res.get("edges_relaxed", 0),
        execution_time_ms=res.get("execution_time_ms", 0.0),
        path_nodes=res.get("path_nodes", []),
        path_coords=res.get("path_coords", []),
        legs=legs_pydantic
    )


@router.post("/benchmark/routing", response_model=RoutingBenchmarkResponse)
def benchmark_routing(req: RoutingBenchmarkRequest):
    dep_seconds = parse_time_to_seconds(req.departure_time)
    node_ids = list(state.graph.nodes.keys())
    if len(node_ids) < 2:
        raise HTTPException(status_code=400, detail="Graph too small for benchmark")

    # Sample random pairs
    pairs = []
    attempts = 0
    while len(pairs) < req.pair_count and attempts < req.pair_count * 5:
        u, v = random.sample(node_ids, 2)
        pairs.append((u, v))
        attempts += 1

    # Pre-build Contraction Hierarchy and measure preprocessing time
    ch = state.get_or_build_ch(req.mode, req.cost_metric)

    results_dijkstra = []
    results_astar = []
    results_ch = []

    samples = []

    for idx, (u, v) in enumerate(pairs):
        r_dijk = run_dijkstra(state.graph, u, v, mode=req.mode, departure_time_seconds=dep_seconds, cost_metric=req.cost_metric)
        r_ast = run_astar(state.graph, u, v, mode=req.mode, departure_time_seconds=dep_seconds, cost_metric=req.cost_metric)
        r_ch = ch.query(u, v, departure_time_seconds=dep_seconds)

        if r_dijk.get("found"):
            results_dijkstra.append(r_dijk)
            results_astar.append(r_ast)
            results_ch.append(r_ch)

            if len(samples) < 5:
                samples.append({
                    "pair": f"{u} -> {v}",
                    "dijkstra": {"latency_ms": r_dijk["execution_time_ms"], "settled": r_dijk["nodes_settled"]},
                    "astar": {"latency_ms": r_ast["execution_time_ms"], "settled": r_ast["nodes_settled"]},
                    "ch": {"latency_ms": r_ch["execution_time_ms"], "settled": r_ch["nodes_settled"]},
                    "distance_m": r_dijk["distance_m"]
                })

    n = max(1, len(results_dijkstra))

    def compute_stats(name: str, res_list: List[Dict[str, Any]], baseline_time: float):
        lats = [r["execution_time_ms"] for r in res_list]
        settled = [r["nodes_settled"] for r in res_list]
        relaxed = [r["edges_relaxed"] for r in res_list]
        tot_time = sum(lats)
        avg_lat = tot_time / n
        sorted_lats = sorted(lats)
        median_lat = sorted_lats[len(sorted_lats) // 2] if sorted_lats else 0.0

        speedup = (baseline_time / max(0.001, tot_time)) if tot_time > 0 else 1.0

        return {
            "algorithm": name,
            "avg_latency_ms": round(avg_lat, 3),
            "median_latency_ms": round(median_lat, 3),
            "avg_nodes_settled": round(sum(settled) / n, 1),
            "avg_edges_relaxed": round(sum(relaxed) / n, 1),
            "total_time_ms": round(tot_time, 2),
            "speedup_vs_dijkstra": round(speedup, 2)
        }

    dijk_tot_time = sum(r["execution_time_ms"] for r in results_dijkstra)
    metrics = {
        "dijkstra": compute_stats("dijkstra", results_dijkstra, dijk_tot_time),
        "astar": compute_stats("astar", results_astar, dijk_tot_time),
        "contraction_hierarchies": compute_stats("contraction_hierarchies", results_ch, dijk_tot_time)
    }

    return RoutingBenchmarkResponse(
        queries_tested=n,
        mode=req.mode,
        metrics=metrics,
        query_samples=samples,
        ch_preprocessing_time_ms=ch.preprocessing_time_ms
    )


@router.post("/vrptw/solve")
def solve_vrptw(req: VRPTWSolveRequest):
    # Clone active problem or apply custom updates
    problem = copy.deepcopy(state.problem)
    problem.fleet_size = req.fleet_size
    problem.vehicle_capacity = req.vehicle_capacity
    problem.late_penalty_per_min = req.late_penalty_per_min

    # If custom depot / stops provided, update
    if req.depot:
        problem.depot.name = req.depot.name
        problem.depot.lat = req.depot.lat
        problem.depot.lon = req.depot.lon
        problem.depot.start_time_s = parse_time_to_seconds(req.depot.start_time)
        near_node = state.graph.find_nearest_node(req.depot.lat, req.depot.lon)
        if near_node:
            problem.depot.nearest_node_id = near_node[0]

    algo = req.algorithm.lower()
    results = {}

    if algo in ("genetic", "both"):
        ga = VRPTWGeneticAlgorithm(
            problem,
            population_size=req.population_size,
            generations=req.iterations
        )
        res_ga = ga.solve()
        results["genetic"] = res_ga

    if algo in ("simulated_annealing", "sa", "both"):
        sa = VRPTWSimulatedAnnealing(
            problem,
            iterations_per_temp=15,
            cooling_rate=0.985
        )
        res_sa = sa.solve()
        results["simulated_annealing"] = res_sa

    # Prepare response: if single chosen, promote it to top-level
    if algo != "both":
        chosen_key = "genetic" if algo == "genetic" else "simulated_annealing"
        chosen_res = results.get(chosen_key)
        return {
            "algorithm": chosen_key,
            "scenario": state.active_scenario_id,
            "fleet_size": problem.fleet_size,
            "vehicle_capacity": problem.vehicle_capacity,
            "depot": {
                "id": problem.depot.id,
                "name": problem.depot.name,
                "lat": problem.depot.lat,
                "lon": problem.depot.lon,
                "start_time": format_seconds_to_time(problem.depot.start_time_s)
            },
            "solution": chosen_res
        }
    else:
        return {
            "algorithm": "comparison",
            "scenario": state.active_scenario_id,
            "results": results
        }


@router.post("/vrptw/benchmark")
def benchmark_vrptw():
    """
    Runs both GA and SA on the active scenario and returns side-by-side trade-off curves.
    """
    problem = copy.deepcopy(state.problem)

    ga = VRPTWGeneticAlgorithm(problem, population_size=40, generations=80)
    res_ga = ga.solve()

    sa = VRPTWSimulatedAnnealing(problem, iterations_per_temp=15, cooling_rate=0.985)
    res_sa = sa.solve()

    return {
        "scenario": state.active_scenario_id,
        "genetic": {
            "execution_time_ms": res_ga["execution_time_ms"],
            "total_cost": res_ga["evaluation"]["total_cost"],
            "distance_m": res_ga["evaluation"]["total_distance_m"],
            "duration_s": res_ga["evaluation"]["total_duration_s"],
            "lateness_s": res_ga["evaluation"]["total_lateness_s"],
            "capacity_excess": res_ga["evaluation"]["total_capacity_excess"],
            "active_vehicles": res_ga["evaluation"]["active_vehicles"],
            "convergence": res_ga["convergence_history"]
        },
        "simulated_annealing": {
            "execution_time_ms": res_sa["execution_time_ms"],
            "total_cost": res_sa["evaluation"]["total_cost"],
            "distance_m": res_sa["evaluation"]["total_distance_m"],
            "duration_s": res_sa["evaluation"]["total_duration_s"],
            "lateness_s": res_sa["evaluation"]["total_lateness_s"],
            "capacity_excess": res_sa["evaluation"]["total_capacity_excess"],
            "active_vehicles": res_sa["evaluation"]["active_vehicles"],
            "convergence": res_sa["convergence_history"]
        }
    }
