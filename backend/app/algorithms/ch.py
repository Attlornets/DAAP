"""
Contraction Hierarchies (CH) Algorithm.

Includes:
1. Preprocessing / Node Contraction with Witness Path Search
2. Bidirectional Upward Query Search
3. Recursive Shortcut Unpacking for Exact Trajectory Reconstruction
"""
import copy
import heapq
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.graph import Edge, MultiModalGraph
from app.core.priority_queue import IndexedPriorityQueue
from app.core.time_dependent import format_seconds_to_time


class ContractionHierarchy:
    def __init__(self, graph: MultiModalGraph, mode: str = "driving", cost_metric: str = "time"):
        self.graph = graph
        self.mode = mode
        self.cost_metric = cost_metric

        # Rank of each node: 0 is lowest level (contracted first), N-1 is highest
        self.ranks: Dict[str, int] = {}
        # Forward upward edges: node -> list of (target, cost, edge)
        self.fwd_upward: Dict[str, List[Tuple[str, float, Edge]]] = {nid: [] for nid in graph.nodes}
        # Backward upward edges: node -> list of (source, cost, edge)
        self.bwd_upward: Dict[str, List[Tuple[str, float, Edge]]] = {nid: [] for nid in graph.nodes}
        
        # Shortcuts mapping: (source, target, cost) -> via_node
        self.shortcuts: Dict[Tuple[str, str, float], str] = {}
        self.preprocessing_time_ms = 0.0
        self.shortcuts_count = 0
        self.is_ready = False

    def _get_base_edge_cost(self, edge: Edge) -> float:
        cost, _ = self.graph.get_edge_travel_cost(edge, self.mode, 28800.0)
        if cost == float("inf"):
            return float("inf")
        return cost if self.cost_metric == "time" else edge.distance_m

    def _witness_search(
        self,
        source: str,
        target: str,
        max_cost: float,
        contracted_node: str,
        contracted_set: Set[str],
        max_settled: int = 40
    ) -> float:
        """
        Runs local Dijkstra from source to target without traversing contracted_node or contracted_set.
        Returns the shortest cost found (or inf if > max_cost or not reachable).
        """
        if source == target:
            return 0.0

        pq: List[Tuple[float, str]] = [(0.0, source)]
        dist: Dict[str, float] = {source: 0.0}
        settled = 0

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, float("inf")):
                continue
            settled += 1
            if settled > max_settled:
                break
            if u == target:
                return d
            if d > max_cost:
                break

            for edge in self.graph.adj.get(u, []):
                v = edge.target
                if v == contracted_node or v in contracted_set:
                    continue
                w = self._get_base_edge_cost(edge)
                if w == float("inf"):
                    continue
                new_d = d + w
                if new_d < dist.get(v, float("inf")) and new_d <= max_cost:
                    dist[v] = new_d
                    heapq.heappush(pq, (new_d, v))

        return dist.get(target, float("inf"))

    def preprocess(self) -> Dict[str, Any]:
        """
        Executes node ordering and contraction.
        """
        start_time = time.perf_counter()
        contracted_set: Set[str] = set()
        node_ids = list(self.graph.nodes.keys())
        n = len(node_ids)

        # Estimate node priority based on edge difference + contracted neighbors
        contracted_neighbors: Dict[str, int] = {nid: 0 for nid in node_ids}

        def compute_priority(nid: str) -> Tuple[int, int]:
            in_deg = sum(1 for e in self.graph.rev_adj.get(nid, []) if e.source not in contracted_set)
            out_deg = sum(1 for e in self.graph.adj.get(nid, []) if e.target not in contracted_set)
            # Rough edge difference: max potential shortcuts (in * out) - (in + out)
            edge_diff = (in_deg * out_deg) - (in_deg + out_deg)
            return edge_diff + contracted_neighbors[nid], nid

        pq: List[Tuple[int, str]] = []
        for nid in node_ids:
            p, _ = compute_priority(nid)
            heapq.heappush(pq, (p, nid))

        current_rank = 0
        shortcuts_added = 0

        while pq:
            p, v = heapq.heappop(pq)
            if v in contracted_set:
                continue

            # Lazy evaluation: verify if priority is still accurate
            new_p, _ = compute_priority(v)
            if pq and new_p > pq[0][0]:
                heapq.heappush(pq, (new_p, v))
                continue

            # Contract node v:
            # Find incoming edges from uncontracted nodes
            in_edges = [
                e for e in self.graph.rev_adj.get(v, [])
                if e.source not in contracted_set and self._get_base_edge_cost(e) < float("inf")
            ]
            # Find outgoing edges to uncontracted nodes
            out_edges = [
                e for e in self.graph.adj.get(v, [])
                if e.target not in contracted_set and self._get_base_edge_cost(e) < float("inf")
            ]

            for in_e in in_edges:
                u = in_e.source
                cost_uv = self._get_base_edge_cost(in_e)
                if cost_uv == float("inf"):
                    continue

                for out_e in out_edges:
                    w = out_e.target
                    if u == w:
                        continue
                    cost_vw = self._get_base_edge_cost(out_e)
                    if cost_vw == float("inf"):
                        continue

                    path_cost = cost_uv + cost_vw
                    # Witness search to check if shortcut is needed
                    witness_cost = self._witness_search(u, w, path_cost, v, contracted_set)

                    if witness_cost > path_cost:
                        # Shortcut is strictly required!
                        shortcut_dist = in_e.distance_m + out_e.distance_m
                        shortcut_edge = self.graph.add_edge(
                            source=u,
                            target=w,
                            distance_m=shortcut_dist,
                            road_type="secondary",
                            oneway=True,
                            modes={self.mode},
                            is_shortcut=True,
                            shortcut_via=v,
                            base_weight=path_cost
                        )
                        self.shortcuts[(u, w, round(path_cost, 4))] = v
                        shortcuts_added += 1

            self.ranks[v] = current_rank
            contracted_set.add(v)
            current_rank += 1

            for e in self.graph.adj.get(v, []):
                contracted_neighbors[e.target] += 1
            for e in self.graph.rev_adj.get(v, []):
                contracted_neighbors[e.source] += 1

        # Build forward and backward upward graphs
        for u in self.graph.nodes:
            u_rank = self.ranks[u]
            for edge in self.graph.adj.get(u, []):
                v = edge.target
                if v in self.ranks and self.ranks[v] > u_rank:
                    cost = self._get_base_edge_cost(edge)
                    if cost < float("inf"):
                        self.fwd_upward[u].append((v, cost, edge))

            for edge in self.graph.rev_adj.get(u, []):
                v = edge.source
                if v in self.ranks and self.ranks[v] > u_rank:
                    cost = self._get_base_edge_cost(edge)
                    if cost < float("inf"):
                        self.bwd_upward[u].append((v, cost, edge))

        self.preprocessing_time_ms = (time.perf_counter() - start_time) * 1000.0
        self.shortcuts_count = shortcuts_added
        self.is_ready = True

        return {
            "node_count": n,
            "shortcuts_added": shortcuts_added,
            "preprocessing_time_ms": round(self.preprocessing_time_ms, 2),
            "mode": self.mode,
            "cost_metric": self.cost_metric
        }

    def query(
        self,
        source_id: str,
        target_id: str,
        departure_time_seconds: float = 28800.0
    ) -> Dict[str, Any]:
        """
        Bidirectional upward query search using Contraction Hierarchies.
        """
        if not self.is_ready:
            self.preprocess()

        start_cpu = time.perf_counter()
        source_id = str(source_id)
        target_id = str(target_id)

        if source_id == target_id:
            return {
                "found": True,
                "algorithm": "contraction_hierarchies",
                "source": source_id,
                "target": target_id,
                "nodes_settled": 1,
                "edges_relaxed": 0,
                "execution_time_ms": 0.05,
                "distance_m": 0.0,
                "duration_s": 0.0,
                "departure_time": format_seconds_to_time(departure_time_seconds),
                "arrival_time": format_seconds_to_time(departure_time_seconds),
                "path_nodes": [source_id],
                "path_coords": [[self.graph.nodes[source_id].lat, self.graph.nodes[source_id].lon]],
                "legs": []
            }

        # Forward priority queue and distances
        pq_f = IndexedPriorityQueue()
        dist_f: Dict[str, float] = {source_id: 0.0}
        parent_f: Dict[str, Tuple[str, Edge]] = {}
        pq_f.push(source_id, 0.0)

        # Backward priority queue and distances
        pq_b = IndexedPriorityQueue()
        dist_b: Dict[str, float] = {target_id: 0.0}
        parent_b: Dict[str, Tuple[str, Edge]] = {}
        pq_b.push(target_id, 0.0)

        best_cost = float("inf")
        meeting_node: Optional[str] = None
        nodes_settled = 0
        edges_relaxed = 0

        while not pq_f.is_empty() or not pq_b.is_empty():
            min_f = pq_f.peek()[1] if not pq_f.is_empty() else float("inf")
            min_b = pq_b.peek()[1] if not pq_b.is_empty() else float("inf")

            # In Contraction Hierarchies, if min_f >= best_cost and min_b >= best_cost,
            # no shorter path can be found via remaining unrelaxed upward nodes.
            if min_f >= best_cost and min_b >= best_cost:
                break

            # Forward step
            if not pq_f.is_empty():
                u, d_u, _ = pq_f.pop()
                nodes_settled += 1

                if d_u < best_cost:
                    # Also check if u is already reached by backward search
                    if u in dist_b:
                        cand = d_u + dist_b[u]
                        if cand < best_cost:
                            best_cost = cand
                            meeting_node = u

                    for v, cost_uv, edge in self.fwd_upward.get(u, []):
                        new_d = d_u + cost_uv
                        edges_relaxed += 1
                        if new_d < dist_f.get(v, float("inf")):
                            dist_f[v] = new_d
                            parent_f[v] = (u, edge)
                            pq_f.update(v, new_d)

                            if v in dist_b:
                                cand_cost = new_d + dist_b[v]
                                if cand_cost < best_cost:
                                    best_cost = cand_cost
                                    meeting_node = v

            # Backward step
            if not pq_b.is_empty():
                w, d_w, _ = pq_b.pop()
                nodes_settled += 1

                if d_w < best_cost:
                    # Also check if w is already reached by forward search
                    if w in dist_f:
                        cand = dist_f[w] + d_w
                        if cand < best_cost:
                            best_cost = cand
                            meeting_node = w

                    for x, cost_xw, edge in self.bwd_upward.get(w, []):
                        new_d = d_w + cost_xw
                        edges_relaxed += 1
                        if new_d < dist_b.get(x, float("inf")):
                            dist_b[x] = new_d
                            parent_b[x] = (w, edge)
                            pq_b.update(x, new_d)

                            if x in dist_f:
                                cand_cost = dist_f[x] + new_d
                                if cand_cost < best_cost:
                                    best_cost = cand_cost
                                    meeting_node = x

        elapsed_ms = (time.perf_counter() - start_cpu) * 1000.0

        if meeting_node is None or best_cost == float("inf"):
            return {
                "found": False,
                "algorithm": "contraction_hierarchies",
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

        # Path unpacking: reconstruct forward path from source to meeting_node
        fwd_edges: List[Edge] = []
        curr = meeting_node
        while curr != source_id:
            p, edge = parent_f[curr]
            fwd_edges.append(edge)
            curr = p
        fwd_edges.reverse()

        # Reconstruct backward path from meeting_node to target
        bwd_edges: List[Edge] = []
        curr = meeting_node
        while curr != target_id:
            p, edge = parent_b[curr]
            bwd_edges.append(edge)
            curr = p

        all_edges = fwd_edges + bwd_edges

        # Recursively unpack shortcuts into original road edges
        unpacked_edges: List[Edge] = []

        def unpack_edge(edge: Edge):
            if not edge.is_shortcut or edge.shortcut_via is None:
                unpacked_edges.append(edge)
                return
            # Find the two constituent edges forming (edge.source -> via -> edge.target)
            via = edge.shortcut_via
            # Locate first half: source -> via
            first_edge = None
            for e in self.graph.adj.get(edge.source, []):
                if e.target == via:
                    first_edge = e
                    break
            # Locate second half: via -> target
            second_edge = None
            for e in self.graph.adj.get(via, []):
                if e.target == edge.target:
                    second_edge = e
                    break

            if first_edge is not None and second_edge is not None:
                unpack_edge(first_edge)
                unpack_edge(second_edge)
            else:
                unpacked_edges.append(edge)

        for e in all_edges:
            unpack_edge(e)

        # Assemble node list and coordinates
        path_nodes = [source_id]
        total_dist_m = 0.0
        legs = []
        curr_t = departure_time_seconds

        for e in unpacked_edges:
            path_nodes.append(e.target)
            t_s, spd = self.graph.get_edge_travel_cost(e, self.mode, curr_t)
            total_dist_m += e.distance_m
            legs.append({
                "from_node": e.source,
                "to_node": e.target,
                "road_name": e.name or e.road_type,
                "road_type": e.road_type,
                "distance_m": round(e.distance_m, 1),
                "duration_s": round(t_s, 1),
                "speed_kmh": round(spd, 1),
                "departure_time": format_seconds_to_time(curr_t),
                "arrival_time": format_seconds_to_time(curr_t + t_s)
            })
            curr_t = (curr_t + t_s) % 86400.0

        path_coords = [[self.graph.nodes[nid].lat, self.graph.nodes[nid].lon] for nid in path_nodes]

        return {
            "found": True,
            "algorithm": "contraction_hierarchies",
            "source": source_id,
            "target": target_id,
            "meeting_node": meeting_node,
            "nodes_settled": nodes_settled,
            "edges_relaxed": edges_relaxed,
            "execution_time_ms": round(elapsed_ms, 3),
            "preprocessing_time_ms": round(self.preprocessing_time_ms, 2),
            "shortcuts_count": self.shortcuts_count,
            "distance_m": round(total_dist_m, 1),
            "duration_s": round(best_cost if self.cost_metric == "time" else sum(l["duration_s"] for l in legs), 1),
            "departure_time": format_seconds_to_time(departure_time_seconds),
            "arrival_time": format_seconds_to_time(curr_t),
            "path_nodes": path_nodes,
            "path_coords": path_coords,
            "legs": legs
        }
