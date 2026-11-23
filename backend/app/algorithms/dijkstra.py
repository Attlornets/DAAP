"""
Time-Dependent Dijkstra's Algorithm using Indexed Priority Queue.
"""
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.graph import Edge, MultiModalGraph
from app.core.priority_queue import IndexedPriorityQueue
from app.core.time_dependent import parse_time_to_seconds, format_seconds_to_time


def run_dijkstra(
    graph: MultiModalGraph,
    source_id: str,
    target_id: Optional[str] = None,
    mode: str = "driving",
    departure_time_seconds: float = 28800.0,
    cost_metric: str = "time"  # 'time' (seconds) or 'distance' (meters)
) -> Dict[str, Any]:
    """
    Executes Dijkstra's algorithm from source_id to target_id.
    If target_id is None, computes shortest paths to all reachable nodes.
    """
    start_cpu = time.perf_counter()
    source_id = str(source_id)
    if target_id is not None:
        target_id = str(target_id)

    if source_id not in graph.nodes:
        raise ValueError(f"Source node {source_id} not in graph")
    if target_id is not None and target_id not in graph.nodes:
        raise ValueError(f"Target node {target_id} not in graph")

    pq = IndexedPriorityQueue()
    # dist maps node_id -> best cost (seconds or meters) from source
    dist: Dict[str, float] = {source_id: 0.0}
    # arrival_time maps node_id -> absolute time of day in seconds
    arrival_time: Dict[str, float] = {source_id: departure_time_seconds}
    
    prev_node: Dict[str, str] = {}
    prev_edge: Dict[str, Edge] = {}

    pq.push(source_id, 0.0)

    nodes_settled = 0
    edges_relaxed = 0
    target_found = False

    while not pq.is_empty():
        curr_node, curr_cost, _ = pq.pop()
        nodes_settled += 1

        if target_id is not None and curr_node == target_id:
            target_found = True
            break

        curr_time = arrival_time[curr_node]

        for edge in graph.adj.get(curr_node, []):
            if edge.is_shortcut:
                continue

            travel_time, speed_kmh = graph.get_edge_travel_cost(edge, mode, curr_time)
            if math_is_inf(travel_time):
                continue

            edge_cost = travel_time if cost_metric == "time" else edge.distance_m
            new_cost = curr_cost + edge_cost

            v = edge.target
            old_cost = dist.get(v, float("inf"))

            if new_cost < old_cost:
                dist[v] = new_cost
                arrival_time[v] = (curr_time + travel_time) % 86400.0
                prev_node[v] = curr_node
                prev_edge[v] = edge
                edges_relaxed += 1

                if pq.contains(v):
                    pq.decrease_key(v, new_cost)
                else:
                    pq.push(v, new_cost)

    elapsed_ms = (time.perf_counter() - start_cpu) * 1000.0

    # Build result
    if target_id is not None and not target_found:
        return {
            "found": False,
            "algorithm": "dijkstra",
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

    # If target is specified, reconstruct path
    path_nodes: List[str] = []
    path_coords: List[List[float]] = []
    legs: List[Dict[str, Any]] = []
    total_dist_m = 0.0

    if target_id is not None:
        curr = target_id
        while curr in prev_node:
            p = prev_node[curr]
            e = prev_edge[curr]
            path_nodes.append(curr)
            curr = p
        path_nodes.append(source_id)
        path_nodes.reverse()

        for nid in path_nodes:
            n = graph.nodes[nid]
            path_coords.append([n.lat, n.lon])

        # Step-by-step legs
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

    total_duration_s = dist.get(target_id, 0.0) if (target_id and cost_metric == "time") else 0.0

    return {
        "found": True if target_id is None or target_found else False,
        "algorithm": "dijkstra",
        "source": source_id,
        "target": target_id,
        "nodes_settled": nodes_settled,
        "edges_relaxed": edges_relaxed,
        "execution_time_ms": round(elapsed_ms, 3),
        "distance_m": round(total_dist_m, 1),
        "duration_s": round(total_duration_s, 1),
        "departure_time": format_seconds_to_time(departure_time_seconds),
        "arrival_time": format_seconds_to_time(arrival_time.get(target_id, departure_time_seconds)) if target_id else None,
        "path_nodes": path_nodes,
        "path_coords": path_coords,
        "legs": legs,
        "all_distances": dist if target_id is None else None
    }


def math_is_inf(val: float) -> bool:
    return val == float("inf") or val != val
