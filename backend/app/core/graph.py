"""
Multi-Modal Directed Graph with Spatial Indexing and Time-Dependent Travel Times.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.spatial_index import BoundingBox, QuadTreeSpatialIndex, haversine_distance
from app.core.time_dependent import calculate_edge_travel_time, get_edge_speed_kmh


@dataclass
class Node:
    id: str
    lat: float
    lon: float
    name: Optional[str] = None


@dataclass
class Edge:
    id: int
    source: str
    target: str
    distance_m: float
    road_type: str = "residential"
    oneway: bool = False
    modes: Set[str] = field(default_factory=lambda: {"driving", "delivery_van", "cycling", "walking"})
    name: Optional[str] = None
    # For shortcuts generated during Contraction Hierarchies:
    is_shortcut: bool = False
    shortcut_via: Optional[str] = None
    base_weight: Optional[float] = None  # travel time in seconds at free-flow / contracted condition


class MultiModalGraph:
    def __init__(self, name: str = "default_graph"):
        self.name = name
        self.nodes: Dict[str, Node] = {}
        # Forward edges: source -> list of Edge
        self.adj: Dict[str, List[Edge]] = {}
        # Backward edges: target -> list of Edge
        self.rev_adj: Dict[str, List[Edge]] = {}
        self.edges: List[Edge] = []
        self._next_edge_id = 1
        self.spatial_index: Optional[QuadTreeSpatialIndex] = None

        # Node level/rank for Contraction Hierarchies
        self.ch_ranks: Dict[str, int] = {}
        self.is_ch_contracted = False

    def add_node(self, node_id: str, lat: float, lon: float, name: Optional[str] = None) -> Node:
        node = Node(id=str(node_id), lat=lat, lon=lon, name=name)
        self.nodes[node.id] = node
        if node.id not in self.adj:
            self.adj[node.id] = []
        if node.id not in self.rev_adj:
            self.rev_adj[node.id] = []
        return node

    def add_edge(
        self,
        source: str,
        target: str,
        distance_m: Optional[float] = None,
        road_type: str = "residential",
        oneway: bool = False,
        modes: Optional[Set[str]] = None,
        name: Optional[str] = None,
        is_shortcut: bool = False,
        shortcut_via: Optional[str] = None,
        base_weight: Optional[float] = None
    ) -> Edge:
        source = str(source)
        target = str(target)
        if source not in self.nodes or target not in self.nodes:
            raise ValueError(f"Nodes {source} and/or {target} do not exist in graph")

        if distance_m is None:
            u = self.nodes[source]
            v = self.nodes[target]
            distance_m = haversine_distance(u.lat, u.lon, v.lat, v.lon)

        if modes is None:
            # Default allowed modes based on road type
            if road_type in ("motorway", "trunk"):
                modes = {"driving", "delivery_van"}
            elif road_type in ("cycleway",):
                modes = {"cycling", "walking"}
            elif road_type in ("footway", "pedestrian"):
                modes = {"walking"}
            else:
                modes = {"driving", "delivery_van", "cycling", "walking"}

        edge_fwd = Edge(
            id=self._next_edge_id,
            source=source,
            target=target,
            distance_m=distance_m,
            road_type=road_type,
            oneway=oneway,
            modes=modes,
            name=name,
            is_shortcut=is_shortcut,
            shortcut_via=shortcut_via,
            base_weight=base_weight
        )
        self._next_edge_id += 1
        self.edges.append(edge_fwd)
        self.adj[source].append(edge_fwd)
        self.rev_adj[target].append(edge_fwd)

        if not oneway and not is_shortcut:
            edge_rev = Edge(
                id=self._next_edge_id,
                source=target,
                target=source,
                distance_m=distance_m,
                road_type=road_type,
                oneway=oneway,
                modes=modes,
                name=name
            )
            self._next_edge_id += 1
            self.edges.append(edge_rev)
            self.adj[target].append(edge_rev)
            self.rev_adj[source].append(edge_rev)

        return edge_fwd

    def build_spatial_index(self) -> QuadTreeSpatialIndex:
        """
        Constructs a QuadTree index covering all nodes in the graph.
        """
        if not self.nodes:
            self.spatial_index = QuadTreeSpatialIndex()
            return self.spatial_index

        lats = [n.lat for n in self.nodes.values()]
        lons = [n.lon for n in self.nodes.values()]
        # Add 0.01 degree padding (~1 km)
        padding = 0.01
        bbox = BoundingBox(
            min_lat=min(lats) - padding,
            min_lon=min(lons) - padding,
            max_lat=max(lats) + padding,
            max_lon=max(lons) + padding
        )
        qtree = QuadTreeSpatialIndex(bbox=bbox, capacity=16)
        for node in self.nodes.values():
            qtree.insert(node.id, node.lat, node.lon, node.name)

        self.spatial_index = qtree
        return qtree

    def find_nearest_node(self, lat: float, lon: float, k: int = 1) -> Optional[Tuple[str, float]]:
        """
        Returns (node_id, distance_m) of nearest graph node.
        """
        if self.spatial_index is None:
            self.build_spatial_index()
        results = self.spatial_index.nearest_neighbor(lat, lon, k=k)
        if results:
            # (point_id, distance_m, plat, plon, pdata)
            return results[0][0], results[0][1]
        return None

    def get_bounds(self) -> Dict[str, float]:
        if not self.nodes:
            return {"min_lat": 0.0, "min_lon": 0.0, "max_lat": 0.0, "max_lon": 0.0}
        lats = [n.lat for n in self.nodes.values()]
        lons = [n.lon for n in self.nodes.values()]
        return {
            "min_lat": min(lats),
            "min_lon": min(lons),
            "max_lat": max(lats),
            "max_lon": max(lons)
        }

    def get_edge_travel_cost(
        self,
        edge: Edge,
        mode: str = "driving",
        departure_time_seconds: float = 28800.0
    ) -> Tuple[float, float]:
        """
        Returns (travel_time_seconds, effective_speed_kmh).
        If edge cannot be traversed by mode, travel_time_seconds is float('inf').
        """
        if mode not in edge.modes:
            return float("inf"), 0.0

        if edge.is_shortcut and edge.base_weight is not None:
            # Shortcuts represent contracted paths with precomputed weights
            return edge.base_weight, 30.0

        return calculate_edge_travel_time(
            edge.distance_m,
            edge.road_type,
            mode,
            departure_time_seconds
        )

    def get_viewport_elements(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        departure_time_seconds: float = 28800.0,
        mode: str = "driving",
        max_edges: int = 1000
    ) -> Dict[str, Any]:
        """
        Fetches nodes and non-shortcut edges in the viewport for client-side map rendering.
        Includes current congestion color rating for visual inspection.
        """
        if self.spatial_index is None:
            self.build_spatial_index()

        nodes_in_box = self.spatial_index.query_bbox(min_lat, min_lon, max_lat, max_lon)
        node_ids = {n[0] for n in nodes_in_box}

        rendered_edges = []
        seen_edge_ids = set()

        for u_id in node_ids:
            for edge in self.adj.get(u_id, []):
                if edge.is_shortcut or edge.id in seen_edge_ids:
                    continue
                v_id = edge.target
                if v_id in self.nodes:
                    u = self.nodes[u_id]
                    v = self.nodes[v_id]
                    seen_edge_ids.add(edge.id)

                    time_s, speed_kmh = self.get_edge_travel_cost(edge, mode, departure_time_seconds)
                    base_speed = get_edge_speed_kmh(edge.road_type, mode, 0.0)  # free flow at midnight
                    congestion_ratio = (base_speed / speed_kmh) if speed_kmh > 0 else 1.0

                    rendered_edges.append({
                        "id": edge.id,
                        "source": u_id,
                        "target": v_id,
                        "coords": [[u.lat, u.lon], [v.lat, v.lon]],
                        "distance_m": round(edge.distance_m, 1),
                        "road_type": edge.road_type,
                        "speed_kmh": round(speed_kmh, 1),
                        "congestion_ratio": round(congestion_ratio, 2),
                        "oneway": edge.oneway
                    })
                    if len(rendered_edges) >= max_edges:
                        break
            if len(rendered_edges) >= max_edges:
                break

        return {
            "node_count": len(node_ids),
            "edge_count": len(rendered_edges),
            "edges": rendered_edges
        }
