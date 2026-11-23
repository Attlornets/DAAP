"""
Custom Spatial Index (2D Quadtree) with Branch-and-Bound Nearest-Neighbor
and Viewport Bounding Box Range Search.
"""
import heapq
import math
from typing import Any, Dict, List, Optional, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth (in meters).
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class BoundingBox:
    def __init__(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float):
        self.min_lat = min_lat
        self.min_lon = min_lon
        self.max_lat = max_lat
        self.max_lon = max_lon

    def contains(self, lat: float, lon: float) -> bool:
        return (self.min_lat <= lat <= self.max_lat and
                self.min_lon <= lon <= self.max_lon)

    def intersects(self, other: "BoundingBox") -> bool:
        return not (self.max_lat < other.min_lat or
                    self.min_lat > other.max_lat or
                    self.max_lon < other.min_lon or
                    self.min_lon > other.max_lon)

    def min_distance_to_point(self, lat: float, lon: float) -> float:
        """
        Minimum Euclidean/spherical approximate distance in meters from point (lat, lon) to this box.
        Used as lower bound in branch-and-bound nearest-neighbor search.
        """
        clamped_lat = max(self.min_lat, min(lat, self.max_lat))
        clamped_lon = max(self.min_lon, min(lon, self.max_lon))
        return haversine_distance(lat, lon, clamped_lat, clamped_lon)


class QuadTreeNode:
    def __init__(self, bbox: BoundingBox, capacity: int = 16):
        self.bbox = bbox
        self.capacity = capacity
        # Points stored as: (point_id, lat, lon, data)
        self.points: List[Tuple[Any, float, float, Any]] = []
        self.is_leaf = True
        # Children: NW, NE, SW, SE
        self.nw: Optional["QuadTreeNode"] = None
        self.ne: Optional["QuadTreeNode"] = None
        self.sw: Optional["QuadTreeNode"] = None
        self.se: Optional["QuadTreeNode"] = None

    def subdivide(self) -> None:
        mid_lat = (self.bbox.min_lat + self.bbox.max_lat) / 2.0
        mid_lon = (self.bbox.min_lon + self.bbox.max_lon) / 2.0

        self.nw = QuadTreeNode(BoundingBox(mid_lat, self.bbox.min_lon, self.bbox.max_lat, mid_lon), self.capacity)
        self.ne = QuadTreeNode(BoundingBox(mid_lat, mid_lon, self.bbox.max_lat, self.bbox.max_lon), self.capacity)
        self.sw = QuadTreeNode(BoundingBox(self.bbox.min_lat, self.bbox.min_lon, mid_lat, mid_lon), self.capacity)
        self.se = QuadTreeNode(BoundingBox(self.bbox.min_lat, mid_lon, mid_lat, self.bbox.max_lon), self.capacity)

        self.is_leaf = False
        points_to_reinsert = self.points
        self.points = []
        for pid, plat, plon, pdata in points_to_reinsert:
            self._insert_child(pid, plat, plon, pdata)

    def _insert_child(self, pid: Any, lat: float, lon: float, data: Any) -> bool:
        if self.nw.bbox.contains(lat, lon):
            return self.nw.insert(pid, lat, lon, data)
        if self.ne.bbox.contains(lat, lon):
            return self.ne.insert(pid, lat, lon, data)
        if self.sw.bbox.contains(lat, lon):
            return self.sw.insert(pid, lat, lon, data)
        if self.se.bbox.contains(lat, lon):
            return self.se.insert(pid, lat, lon, data)
        # On boundary fallback
        return self.nw.insert(pid, lat, lon, data)

    def insert(self, pid: Any, lat: float, lon: float, data: Any) -> bool:
        if not self.bbox.contains(lat, lon):
            return False

        if self.is_leaf:
            if len(self.points) < self.capacity:
                self.points.append((pid, lat, lon, data))
                return True
            else:
                self.subdivide()
                return self._insert_child(pid, lat, lon, data)
        else:
            return self._insert_child(pid, lat, lon, data)


class QuadTreeSpatialIndex:
    """
    2D Quadtree index for spatial queries on geographical coordinates.
    """
    def __init__(self, bbox: Optional[BoundingBox] = None, capacity: int = 16):
        if bbox is None:
            # Default global bounding box
            bbox = BoundingBox(-90.0, -180.0, 90.0, 180.0)
        self.root = QuadTreeNode(bbox, capacity)
        self.point_lookup: Dict[Any, Tuple[float, float, Any]] = {}
        self.size = 0

    def insert(self, pid: Any, lat: float, lon: float, data: Any = None) -> bool:
        success = self.root.insert(pid, lat, lon, data)
        if success:
            self.point_lookup[pid] = (lat, lon, data)
            self.size += 1
        return success

    def nearest_neighbor(self, lat: float, lon: float, k: int = 1, max_dist_m: Optional[float] = None) -> List[Tuple[Any, float, float, float, Any]]:
        """
        Branch-and-bound Best-First Search for k nearest neighbors.
        Returns list of (point_id, distance_m, lat, lon, data) sorted by distance.
        """
        if self.size == 0 or k <= 0:
            return []

        # Min-heap of search elements: (lower_bound_dist, is_point, payload)
        # For nodes: payload is QuadTreeNode
        # For points: payload is (point_id, plat, plon, pdata)
        heap: List[Tuple[float, bool, Any]] = []

        root_dist = self.root.bbox.min_distance_to_point(lat, lon)
        heapq.heappush(heap, (root_dist, False, self.root))

        # Max-heap (storing negative distances) for best k points found so far
        # Each entry: (-dist, point_id, plat, plon, pdata)
        best_k: List[Tuple[float, Any, float, float, Any]] = []

        while heap:
            min_dist, is_point, item = heapq.heappop(heap)

            # If we already have k points and this item's lower bound >= kth best distance, prune
            if len(best_k) == k and min_dist >= -best_k[0][0]:
                break

            if max_dist_m is not None and min_dist > max_dist_m:
                break

            if is_point:
                pid, plat, plon, pdata = item
                actual_dist = min_dist
                if len(best_k) < k:
                    heapq.heappush(best_k, (-actual_dist, pid, plat, plon, pdata))
                elif actual_dist < -best_k[0][0]:
                    heapq.heapreplace(best_k, (-actual_dist, pid, plat, plon, pdata))
            else:
                node: QuadTreeNode = item
                if node.is_leaf:
                    for pid, plat, plon, pdata in node.points:
                        p_dist = haversine_distance(lat, lon, plat, plon)
                        if max_dist_m is None or p_dist <= max_dist_m:
                            heapq.heappush(heap, (p_dist, True, (pid, plat, plon, pdata)))
                else:
                    for child in (node.nw, node.ne, node.sw, node.se):
                        if child is not None:
                            c_dist = child.bbox.min_distance_to_point(lat, lon)
                            if len(best_k) < k or c_dist < -best_k[0][0]:
                                heapq.heappush(heap, (c_dist, False, child))

        results = []
        while best_k:
            neg_dist, pid, plat, plon, pdata = heapq.heappop(best_k)
            results.append((pid, -neg_dist, plat, plon, pdata))
        results.reverse()  # from smallest distance to largest
        return results

    def query_bbox(self, min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> List[Tuple[Any, float, float, Any]]:
        """
        Find all points inside the given bounding box.
        """
        query_box = BoundingBox(min_lat, min_lon, max_lat, max_lon)
        results: List[Tuple[Any, float, float, Any]] = []

        def search_node(node: QuadTreeNode):
            if not node.bbox.intersects(query_box):
                return
            if node.is_leaf:
                for pid, plat, plon, pdata in node.points:
                    if query_box.contains(plat, plon):
                        results.append((pid, plat, plon, pdata))
            else:
                if node.nw: search_node(node.nw)
                if node.ne: search_node(node.ne)
                if node.sw: search_node(node.sw)
                if node.se: search_node(node.se)

        search_node(self.root)
        return results
