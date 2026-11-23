"""
A* Search Algorithm with Admissible Spatial and Time-Aware Lower-Bound Heuristics.
"""
import time
from typing import Any, Dict, List, Optional

from app.core.graph import Edge, MultiModalGraph
from app.core.priority_queue import IndexedPriorityQueue
from app.core.time_dependent import format_seconds_to_time
from app.algorithms.heuristics import time_aware_haversine_heuristic
from app.core.spatial_index import haversine_distance


def run_astar(
    graph: MultiModalGraph,
    source_id: str,
    target_id: str,
    mode: str = "driving",
    departure_time_seconds: float = 28800.0,
    cost_metric: str = "time"
) -> Dict[str, Any]:
    """
    Executes A* Search from source_id to target_id.
    Guarantees shortest path while settling significantly fewer nodes than Dijkstra.
    """
    start_cpu = time.perf_counter()
    source_id = str(source_id)
    target_id = str(target_id)

    if source_id not in graph.nodes:
        raise ValueError(f"Source node {source_id} not in graph")
    if target_id not in graph.nodes:
        raise ValueError(f"Target node {target_id} not in graph")

    target_node = graph.nodes[target_id]
    target_lat, target_lon = target_node.lat, target_node.lon

    def heuristic(lat: float, lon: float) -> float:
        if cost_metric == "time":
            return time_aware_haversine_heuristic(lat, lon, target_lat, target_lon, mode)
        else:
            return haversine_distance(lat, lon, target_lat, target_lon)

    pq = IndexedPriorityQueue()
    # g_score maps node_id -> exact cost from source
    g_score: Dict[str, float] = {source_id: 0.0}
    arrival_time: Dict[str, float] = {source_id: departure_time_seconds}
    
    prev_node: Dict[str, str] = {}
    prev_edge: Dict[str, Edge] = {}

    start_node = graph.nodes[source_id]
    f_start = heuristic(start_node.lat, start_node.lon)
    pq.push(source_id, f_start)

    nodes_settled = 0
    edges_relaxed = 0
    target_found = False

    while not pq.is_empty():
        curr_node, _, _ = pq.pop()
        nodes_settled += 1

        if curr_node == target_id:
            target_found = True
            break

        curr_g = g_score[curr_node]
        curr_time = arrival_time[curr_node]

        for edge in graph.adj.get(curr_node, []):
            if edge.is_shortcut:
                continue

            travel_time, speed_kmh = graph.get_edge_travel_cost(edge, mode, curr_time)
            if travel_time == float("inf"):
                continue

            edge_cost = travel_time if cost_metric == "time" else edge.distance_m
            tentative_g = curr_g + edge_cost

            v = edge.target
            old_g = g_score.get(v, float("inf"))

            if tentative_g < old_g:
                g_score[v] = tentative_g
                arrival_time[v] = (curr_time + travel_time) % 86400.0
                prev_node[v] = curr_node
                prev_edge[v] = edge
                edges_relaxed += 1

                v_node = graph.nodes[v]
                f_score = tentative_g + heuristic(v_node.lat, v_node.lon)

                if pq.contains(v):
                    pq.decrease_key(v, f_score)
                else:
                    pq.push(v, f_score)

    elapsed_ms = (time.perf_counter() - start_cpu) * 1000.0

    if not target_found:
        return {
            "found": False,
            "algorithm": "astar",
            "source": source_id,
            "target": target_id,
            "nodes_settled": nodes_settled,
            "edges_relaxed": edges_relaxed,
            "execution_time_ms": round(elapsed_ms, 3),
            "distance_m": 0.0,
            "duration_s": 0.0,
            "path_nodes": [],
            "path_coords": [],
            "legs": []
        }

    # Reconstruct path
    path_nodes: List[str] = []
    curr = target_id
    while curr in prev_node:
        path_nodes.append(curr)
        curr = prev_node[curr]
    path_nodes.append(source_id)
    path_nodes.reverse()

    path_coords = [[graph.nodes[nid].lat, graph.nodes[nid].lon] for nid in path_nodes]

    total_dist_m = 0.0
    legs = []
    curr_t = departure_time_seconds
    for i in range(len(path_nodes) - 1):
        u_id = path_nodes[i]
        v_id = path_nodes[i + 1]
        e = prev_edge[v_id]
        t_s, spd = graph.get_edge_travel_cost(e, mode, curr_t)
        total_dist_m += e.distance_m
        legs.append({
            "from_node": u_id,
            "to_node": v_id,
            "road_name": e.name or e.road_type,
            "road_type": e.road_type,
            "distance_m": round(e.distance_m, 1),
            "duration_s": round(t_s, 1),
            "speed_kmh": round(spd, 1),
            "departure_time": format_seconds_to_time(curr_t),
            "arrival_time": format_seconds_to_time(curr_t + t_s)
        })
        curr_t = (curr_t + t_s) % 86400.0

    total_duration_s = g_score.get(target_id, 0.0) if cost_metric == "time" else 0.0

    return {
        "found": True,
        "algorithm": "astar",
        "source": source_id,
        "target": target_id,
        "nodes_settled": nodes_settled,
        "edges_relaxed": edges_relaxed,
        "execution_time_ms": round(elapsed_ms, 3),
        "distance_m": round(total_dist_m, 1),
        "duration_s": round(total_duration_s, 1),
        "departure_time": format_seconds_to_time(departure_time_seconds),
        "arrival_time": format_seconds_to_time(arrival_time.get(target_id, departure_time_seconds)),
        "path_nodes": path_nodes,
        "path_coords": path_coords,
        "legs": legs
    }
