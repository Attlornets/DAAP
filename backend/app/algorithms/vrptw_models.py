"""
Data models and route simulation evaluator for Vehicle Routing Problem with Time Windows (VRPTW).
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from app.core.time_dependent import format_seconds_to_time


@dataclass
class DeliveryStop:
    id: str
    name: str
    lat: float
    lon: float
    demand: float = 10.0  # e.g., kg or parcel units
    service_time_s: float = 300.0  # 5 minutes
    earliest_arrival_s: float = 28800.0  # 08:00
    latest_arrival_s: float = 36000.0    # 10:00
    nearest_node_id: Optional[str] = None


@dataclass
class Depot:
    id: str
    name: str
    lat: float
    lon: float
    start_time_s: float = 28800.0  # 08:00
    nearest_node_id: Optional[str] = None


@dataclass
class VRPTWProblem:
    depot: Depot
    stops: List[DeliveryStop]
    fleet_size: int = 3
    vehicle_capacity: float = 100.0
    late_penalty_per_min: float = 2.0
    capacity_penalty_multiplier: float = 100.0
    time_window_penalty_multiplier: float = 5.0
    # Matrices: distance in meters and travel time in seconds between [depot, stop_0, ..., stop_N-1]
    # Index 0 is depot, Index i+1 is stop[i]
    dist_matrix: List[List[float]] = field(default_factory=list)
    time_matrix: List[List[float]] = field(default_factory=list)


def evaluate_solution(
    problem: VRPTWProblem,
    routes: List[List[int]]  # each route is a list of stop indices [0..len(stops)-1]
) -> Dict[str, Any]:
    """
    Evaluates a candidate solution (set of routes, one per vehicle).
    Returns total cost, fitness, constraint violations, and per-vehicle timeline.
    """
    total_travel_time_s = 0.0
    total_distance_m = 0.0
    total_waiting_time_s = 0.0
    total_service_time_s = 0.0
    total_lateness_s = 0.0
    total_capacity_excess = 0.0
    active_vehicles = 0

    vehicle_schedules: List[Dict[str, Any]] = []

    for v_idx, route in enumerate(routes):
        if not route:
            continue
        active_vehicles += 1

        route_dist_m = 0.0
        route_travel_s = 0.0
        route_wait_s = 0.0
        route_service_s = 0.0
        route_lateness_s = 0.0
        route_demand = sum(problem.stops[idx].demand for idx in route)

        cap_violation = max(0.0, route_demand - problem.vehicle_capacity)
        total_capacity_excess += cap_violation

        curr_time = problem.depot.start_time_s
        curr_loc_idx = 0  # 0 is depot
        stops_timeline = []

        # Start from depot
        stops_timeline.append({
            "stop_id": problem.depot.id,
            "name": f"Depot ({problem.depot.name})",
            "type": "depot_start",
            "arrival_time": format_seconds_to_time(curr_time),
            "departure_time": format_seconds_to_time(curr_time),
            "waiting_s": 0.0,
            "service_s": 0.0,
            "lat": problem.depot.lat,
            "lon": problem.depot.lon,
            "demand": 0.0,
            "load_remaining": route_demand,
            "is_late": False,
            "lateness_s": 0.0
        })

        rem_load = route_demand

        for stop_idx in route:
            matrix_to_idx = stop_idx + 1
            stop = problem.stops[stop_idx]

            leg_dist = problem.dist_matrix[curr_loc_idx][matrix_to_idx]
            leg_time = problem.time_matrix[curr_loc_idx][matrix_to_idx]

            route_dist_m += leg_dist
            route_travel_s += leg_time
            curr_time += leg_time

            arrival_s = curr_time
            wait_s = max(0.0, stop.earliest_arrival_s - arrival_s)
            route_wait_s += wait_s

            start_service_s = arrival_s + wait_s
            lateness_s = max(0.0, start_service_s - stop.latest_arrival_s)
            route_lateness_s += lateness_s

            serv_s = stop.service_time_s
            route_service_s += serv_s
            finish_service_s = start_service_s + serv_s
            curr_time = finish_service_s

            rem_load -= stop.demand

            stops_timeline.append({
                "stop_id": stop.id,
                "name": stop.name,
                "type": "delivery",
                "arrival_time": format_seconds_to_time(arrival_s),
                "departure_time": format_seconds_to_time(finish_service_s),
                "waiting_s": round(wait_s, 1),
                "service_s": round(serv_s, 1),
                "lat": stop.lat,
                "lon": stop.lon,
                "demand": stop.demand,
                "load_remaining": max(0.0, rem_load),
                "earliest_time": format_seconds_to_time(stop.earliest_arrival_s),
                "latest_time": format_seconds_to_time(stop.latest_arrival_s),
                "is_late": lateness_s > 0.0,
                "lateness_s": round(lateness_s, 1)
            })

            curr_loc_idx = matrix_to_idx

        # Return to depot
        return_dist = problem.dist_matrix[curr_loc_idx][0]
        return_time = problem.time_matrix[curr_loc_idx][0]
        route_dist_m += return_dist
        route_travel_s += return_time
        curr_time += return_time

        stops_timeline.append({
            "stop_id": problem.depot.id,
            "name": f"Depot Return ({problem.depot.name})",
            "type": "depot_end",
            "arrival_time": format_seconds_to_time(curr_time),
            "departure_time": format_seconds_to_time(curr_time),
            "waiting_s": 0.0,
            "service_s": 0.0,
            "lat": problem.depot.lat,
            "lon": problem.depot.lon,
            "demand": 0.0,
            "load_remaining": 0.0,
            "is_late": False,
            "lateness_s": 0.0
        })

        total_route_duration_s = curr_time - problem.depot.start_time_s

        vehicle_schedules.append({
            "vehicle_id": v_idx + 1,
            "stop_count": len(route),
            "total_distance_m": round(route_dist_m, 1),
            "total_duration_s": round(total_route_duration_s, 1),
            "travel_time_s": round(route_travel_s, 1),
            "waiting_time_s": round(route_wait_s, 1),
            "service_time_s": round(route_service_s, 1),
            "lateness_s": round(route_lateness_s, 1),
            "total_demand": round(route_demand, 1),
            "capacity": problem.vehicle_capacity,
            "capacity_utilization_pct": round(min(100.0, (route_demand / problem.vehicle_capacity) * 100.0), 1),
            "capacity_violation": round(cap_violation, 1),
            "timeline": stops_timeline
        })

        total_travel_time_s += route_travel_s
        total_distance_m += route_dist_m
        total_waiting_time_s += route_wait_s
        total_service_time_s += route_service_s
        total_lateness_s += route_lateness_s

    # Penalties calculation
    late_penalty_cost = (total_lateness_s / 60.0) * problem.late_penalty_per_min
    capacity_penalty = total_capacity_excess * problem.capacity_penalty_multiplier
    time_window_penalty = (total_lateness_s / 60.0) * problem.time_window_penalty_multiplier

    # Composite cost objective: Travel time + Distance weight + Fleet fixed weight + Violations
    total_cost = (
        (total_travel_time_s / 60.0) * 1.0 +
        (total_distance_m / 1000.0) * 1.5 +
        active_vehicles * 50.0 +
        capacity_penalty +
        time_window_penalty +
        late_penalty_cost
    )

    is_feasible = (total_capacity_excess <= 1e-4 and total_lateness_s <= 1e-4)

    return {
        "is_feasible": is_feasible,
        "total_cost": round(total_cost, 2),
        "total_distance_m": round(total_distance_m, 1),
        "total_duration_s": round(total_travel_time_s + total_waiting_time_s + total_service_time_s, 1),
        "total_travel_time_s": round(total_travel_time_s, 1),
        "total_waiting_time_s": round(total_waiting_time_s, 1),
        "total_service_time_s": round(total_service_time_s, 1),
        "total_lateness_s": round(total_lateness_s, 1),
        "total_capacity_excess": round(total_capacity_excess, 1),
        "active_vehicles": active_vehicles,
        "fleet_utilization_pct": round((active_vehicles / problem.fleet_size) * 100.0, 1) if problem.fleet_size > 0 else 0.0,
        "late_penalty_cost": round(late_penalty_cost, 2),
        "vehicle_schedules": vehicle_schedules
    }
