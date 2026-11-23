"""
Time-Dependent Traffic Congestion and Multi-Modal Speed Profile Engine.

Computes time-of-day congestion multipliers and travel times across
different transportation modes and road classifications.
"""
import math
from typing import Dict, Optional, Set, Tuple

MODES: Set[str] = {"driving", "delivery_van", "cycling", "walking"}

# Base free-flow speeds in km/h by road type and transport mode
BASE_SPEEDS_KMH: Dict[str, Dict[str, float]] = {
    "motorway": {
        "driving": 100.0,
        "delivery_van": 85.0,
        "cycling": 0.0,    # Not permitted
        "walking": 0.0     # Not permitted
    },
    "trunk": {
        "driving": 80.0,
        "delivery_van": 70.0,
        "cycling": 0.0,
        "walking": 0.0
    },
    "primary": {
        "driving": 50.0,
        "delivery_van": 45.0,
        "cycling": 18.0,
        "walking": 4.5
    },
    "secondary": {
        "driving": 40.0,
        "delivery_van": 38.0,
        "cycling": 18.0,
        "walking": 4.5
    },
    "tertiary": {
        "driving": 35.0,
        "delivery_van": 32.0,
        "cycling": 16.0,
        "walking": 4.5
    },
    "residential": {
        "driving": 25.0,
        "delivery_van": 22.0,
        "cycling": 15.0,
        "walking": 4.5
    },
    "service": {
        "driving": 15.0,
        "delivery_van": 15.0,
        "cycling": 12.0,
        "walking": 4.0
    },
    "cycleway": {
        "driving": 0.0,
        "delivery_van": 0.0,
        "cycling": 20.0,
        "walking": 4.0
    },
    "footway": {
        "driving": 0.0,
        "delivery_van": 0.0,
        "cycling": 0.0,
        "walking": 4.8
    },
    "pedestrian": {
        "driving": 0.0,
        "delivery_van": 5.0,  # restricted delivery loading
        "cycling": 10.0,
        "walking": 4.8
    }
}

DEFAULT_BASE_SPEED_KMH = {
    "driving": 35.0,
    "delivery_van": 30.0,
    "cycling": 15.0,
    "walking": 4.5
}

# Road type sensitivity to traffic congestion (0.0 = completely immune, 1.0 = highly vulnerable)
ROAD_CONGESTION_SENSITIVITY: Dict[str, float] = {
    "motorway": 0.95,
    "trunk": 0.90,
    "primary": 0.85,
    "secondary": 0.70,
    "tertiary": 0.50,
    "residential": 0.30,
    "service": 0.15,
    "cycleway": 0.0,
    "footway": 0.0,
    "pedestrian": 0.0
}


def parse_time_to_seconds(time_str: str) -> float:
    """
    Parses 'HH:MM' or 'HH:MM:SS' into seconds from midnight (0 to 86399).
    """
    parts = time_str.strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    seconds = float(parts[2]) if len(parts) > 2 else 0.0
    return ((hours * 3600) + (minutes * 60) + seconds) % 86400.0


def format_seconds_to_time(seconds: float) -> str:
    """
    Formats seconds from midnight to 'HH:MM:SS'.
    """
    total_sec = int(round(seconds)) % 86400
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_base_congestion_factor(seconds_from_midnight: float) -> float:
    """
    Continuous traffic congestion curve across 24 hours.
    Returns a congestion multiplier >= 1.0 (1.0 = free flow, 2.2 = heavy gridlock).
    """
    hours = (seconds_from_midnight % 86400.0) / 3600.0

    # Gaussian peak 1: Morning Rush Hour centered at 08:30 (sigma ~ 1.1 hours, peak factor +1.2)
    morning_peak = 1.25 * math.exp(-0.5 * ((hours - 8.5) / 1.15) ** 2)

    # Gaussian peak 2: Evening Rush Hour centered at 17:30 (sigma ~ 1.3 hours, peak factor +1.4)
    evening_peak = 1.40 * math.exp(-0.5 * ((hours - 17.5) / 1.35) ** 2)

    # Mild lunch hump centered at 12:45
    lunch_hump = 0.35 * math.exp(-0.5 * ((hours - 12.75) / 0.9) ** 2)

    # Baseline factor is 1.0 (free flow during late night/early morning)
    factor = 1.0 + morning_peak + evening_peak + lunch_hump
    return max(1.0, factor)


def get_edge_speed_kmh(
    road_type: str,
    mode: str = "driving",
    departure_time_seconds: float = 28800.0  # default 08:00
) -> float:
    """
    Calculates the effective speed in km/h for a given road type, mode, and time.
    Returns 0.0 if the mode cannot traverse this road type.
    """
    speeds = BASE_SPEEDS_KMH.get(road_type, DEFAULT_BASE_SPEED_KMH)
    base_speed = speeds.get(mode, DEFAULT_BASE_SPEED_KMH.get(mode, 25.0))
    if base_speed <= 0.0:
        return 0.0

    # Walking and cycling are not affected by vehicular gridlock
    if mode in ("walking", "cycling"):
        return base_speed

    # For vehicular traffic (driving, delivery_van):
    base_factor = get_base_congestion_factor(departure_time_seconds)
    sensitivity = ROAD_CONGESTION_SENSITIVITY.get(road_type, 0.5)

    # Effective multiplier scaled by road sensitivity
    # e.g., if base_factor is 2.2 (peak) and sensitivity is 0.85:
    # effective_factor = 1.0 + (2.2 - 1.0) * 0.85 = 2.02
    effective_factor = 1.0 + (base_factor - 1.0) * sensitivity
    effective_speed = base_speed / effective_factor

    # Ensure reasonable lower bound so speed doesn't drop to 0
    min_speed = 5.0 if mode == "driving" else 4.0
    return max(min_speed, effective_speed)


def calculate_edge_travel_time(
    distance_m: float,
    road_type: str,
    mode: str = "driving",
    departure_time_seconds: float = 28800.0
) -> Tuple[float, float]:
    """
    Returns (travel_time_seconds, effective_speed_kmh).
    Returns (float('inf'), 0.0) if edge cannot be traversed.
    """
    speed_kmh = get_edge_speed_kmh(road_type, mode, departure_time_seconds)
    if speed_kmh <= 0.0:
        return float("inf"), 0.0

    speed_mps = speed_kmh / 3.6  # convert km/h to m/s
    travel_time_s = distance_m / speed_mps
    return travel_time_s, speed_kmh
