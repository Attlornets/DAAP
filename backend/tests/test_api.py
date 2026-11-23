"""
API Integration tests (direct endpoint invocation).
"""
import pytest
from app.api.routes import (
    compute_route,
    get_graph_info,
    get_graph_viewport,
    health,
    list_scenarios,
    select_scenario,
    solve_vrptw,
)
from app.api.schemas import (
    LatLonPoint,
    RouteRequest,
    ScenarioSelectRequest,
    VRPTWSolveRequest,
)


def test_health():
    res = health()
    assert res["status"] == "healthy"


def test_list_scenarios():
    data = list_scenarios()
    assert "scenarios" in data
    assert len(data["scenarios"]) >= 3


def test_select_scenario():
    res = select_scenario(ScenarioSelectRequest(scenario_id="manhattan"))
    assert res["success"] is True
    assert res["scenario_id"] == "manhattan"
    assert res["node_count"] > 10

    # Switch back to san_francisco
    select_scenario(ScenarioSelectRequest(scenario_id="san_francisco"))


def test_graph_info_and_viewport():
    info = get_graph_info()
    assert info["node_count"] > 10
    bounds = info["bounds"]

    vp = get_graph_viewport(
        min_lat=bounds["min_lat"],
        min_lon=bounds["min_lon"],
        max_lat=bounds["max_lat"],
        max_lon=bounds["max_lon"],
        departure_time="08:30",
        mode="driving"
    )
    assert vp["node_count"] > 0
    assert "edges" in vp


def test_compute_route():
    req = RouteRequest(
        start=LatLonPoint(lat=37.7795, lon=-122.4025),
        end=LatLonPoint(lat=37.7897, lon=-122.3972),
        algorithm="astar",
        mode="driving",
        departure_time="08:30"
    )
    res = compute_route(req)
    assert res.found is True
    assert res.distance_m > 0
    assert len(res.path_coords) >= 2


def test_solve_vrptw():
    req = VRPTWSolveRequest(
        algorithm="genetic",
        fleet_size=3,
        vehicle_capacity=90.0,
        iterations=15,
        population_size=15
    )
    res = solve_vrptw(req)
    assert "solution" in res
    assert "evaluation" in res["solution"]
