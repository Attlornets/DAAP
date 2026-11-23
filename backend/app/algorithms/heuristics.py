"""
Admissible and Consistent Spatial Heuristics for A* and Goal-Directed Search.
"""
from typing import Dict
from app.core.spatial_index import haversine_distance

# Theoretical maximum speeds in m/s for each transport mode to guarantee admissibility
MAX_MODE_SPEED_MPS: Dict[str, float] = {
    "driving": 120.0 / 3.6,        # ~33.33 m/s (120 km/h)
    "delivery_van": 100.0 / 3.6,   # ~27.78 m/s (100 km/h)
    "cycling": 30.0 / 3.6,         # ~8.33 m/s (30 km/h)
    "walking": 6.0 / 3.6           # ~1.67 m/s (6 km/h)
}


def time_aware_haversine_heuristic(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    mode: str = "driving"
) -> float:
    """
    Computes an admissible lower bound on the travel time (in seconds) between two coordinates.
    h(u, target) = distance_haversine(u, target) / max_speed(mode).
    
    Proof of admissibility:
    - Straight-line great-circle distance is strictly <= any physical road path.
    - No edge or vehicle can exceed max_mode_speed.
    - Therefore, distance / max_speed <= road_distance / road_speed = actual_travel_time.
    """
    dist_m = haversine_distance(lat1, lon1, lat2, lon2)
    max_mps = MAX_MODE_SPEED_MPS.get(mode, 33.33)
    return dist_m / max_mps
