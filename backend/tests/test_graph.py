"""
Unit tests for MultiModalGraph and time-dependent congestion calculations.
"""
import pytest
from app.core.graph import MultiModalGraph
from app.core.time_dependent import (
    calculate_edge_travel_time,
    get_base_congestion_factor,
    get_edge_speed_kmh,
    parse_time_to_seconds,
)


def test_time_congestion_curve():
    midnight_s = parse_time_to_seconds("02:00")
    morning_peak_s = parse_time_to_seconds("08:30")
    evening_peak_s = parse_time_to_seconds("17:30")

    factor_night = get_base_congestion_factor(midnight_s)
    factor_morning = get_base_congestion_factor(morning_peak_s)
    factor_evening = get_base_congestion_factor(evening_peak_s)

    # Congestion during rush hours must exceed baseline free-flow
    assert factor_night == pytest.approx(1.0, rel=0.05)
    assert factor_morning > 1.8
    assert factor_evening > 2.0


def test_multi_modal_speed_and_travel_time():
    # Motorway during rush hour
    peak_s = parse_time_to_seconds("08:30")
    night_s = parse_time_to_seconds("03:00")

    spd_night = get_edge_speed_kmh("motorway", "driving", night_s)
    spd_peak = get_edge_speed_kmh("motorway", "driving", peak_s)
    assert spd_night > spd_peak

    # Walking speed is invariant to vehicular traffic
    walk_night = get_edge_speed_kmh("footway", "walking", night_s)
    walk_peak = get_edge_speed_kmh("footway", "walking", peak_s)
    assert walk_night == walk_peak

    # Cycling on motorways should not be permitted
    bike_motorway = get_edge_speed_kmh("motorway", "cycling", night_s)
    assert bike_motorway == 0.0


def test_graph_construction_and_viewport():
    graph = MultiModalGraph("test_city")
    graph.add_node("n1", 37.78, -122.40, "Node 1")
    graph.add_node("n2", 37.79, -122.39, "Node 2")
    graph.add_edge("n1", "n2", road_type="primary", oneway=False)
    graph.build_spatial_index()

    bounds = graph.get_bounds()
    assert bounds["min_lat"] <= 37.78 <= bounds["max_lat"]

    viewport = graph.get_viewport_elements(37.77, -122.41, 37.80, -122.38)
    assert viewport["node_count"] == 2
    assert viewport["edge_count"] >= 1
