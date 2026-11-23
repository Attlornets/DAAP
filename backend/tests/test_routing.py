"""
Unit tests for Dijkstra, A*, and Contraction Hierarchies.
Verifies exact distance/duration optimality and equivalence across algorithms.
"""
import pytest
from app.algorithms.astar import run_astar
from app.algorithms.ch import ContractionHierarchy
from app.algorithms.dijkstra import run_dijkstra
from app.data.preset_cities import generate_san_francisco_scenario


@pytest.fixture(scope="module")
def sf_scenario():
    graph, problem, _ = generate_san_francisco_scenario()
    return graph, problem


def test_dijkstra_vs_astar_equivalence(sf_scenario):
    graph, _ = sf_scenario
    source = "sf_townsend_8th"
    target = "sf_pine_davis"

    res_dijkstra = run_dijkstra(graph, source, target, mode="driving", departure_time_seconds=28800.0)
    res_astar = run_astar(graph, source, target, mode="driving", departure_time_seconds=28800.0)

    assert res_dijkstra["found"] is True
    assert res_astar["found"] is True

    # A* and Dijkstra must find identical shortest durations (or within 0.1% floating tolerance)
    assert res_dijkstra["duration_s"] == pytest.approx(res_astar["duration_s"], rel=1e-3)
    assert res_dijkstra["distance_m"] == pytest.approx(res_astar["distance_m"], rel=1e-3)

    # A* must settle fewer (or at most equal) nodes than Dijkstra
    assert res_astar["nodes_settled"] <= res_dijkstra["nodes_settled"]


def test_contraction_hierarchies_preprocess_and_query(sf_scenario):
    graph, _ = sf_scenario
    ch = ContractionHierarchy(graph, mode="driving", cost_metric="distance")
    prep_stats = ch.preprocess()

    assert prep_stats["shortcuts_added"] > 0
    assert prep_stats["node_count"] == len(graph.nodes)

    source = "sf_townsend_8th"
    target = "sf_pine_davis"

    res_ch = ch.query(source, target)
    res_dijkstra = run_dijkstra(graph, source, target, mode="driving", cost_metric="distance")

    assert res_ch["found"] is True
    # CH shortest distance matches Dijkstra baseline
    assert res_ch["distance_m"] == pytest.approx(res_dijkstra["distance_m"], rel=1e-3)

    # CH query visits fewer nodes than full Dijkstra
    assert res_ch["nodes_settled"] < res_dijkstra["nodes_settled"]
    assert len(res_ch["path_nodes"]) >= 2
    assert res_ch["path_nodes"][0] == source
    assert res_ch["path_nodes"][-1] == target
