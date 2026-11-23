"""
Unit tests for QuadTreeSpatialIndex and Haversine distance calculations.
"""
import pytest
from app.core.spatial_index import (
    BoundingBox,
    QuadTreeSpatialIndex,
    haversine_distance,
)


def test_haversine_distance():
    # Distance between NYC Empire State and Times Square is ~1.1 km
    d = haversine_distance(40.7484, -73.9857, 40.7580, -73.9855)
    assert 1000.0 < d < 1200.0


def test_quadtree_insert_and_nearest():
    bbox = BoundingBox(37.0, -123.0, 38.0, -122.0)
    index = QuadTreeSpatialIndex(bbox=bbox, capacity=4)

    # Insert points
    index.insert("sf_downtown", 37.7850, -122.4020, "Downtown")
    index.insert("sf_mission", 37.7600, -122.4200, "Mission")
    index.insert("sf_sunset", 37.7500, -122.4800, "Sunset")
    index.insert("sf_richmond", 37.7800, -122.4800, "Richmond")

    # Nearest neighbor to 37.7840, -122.4030 should be Downtown
    results = index.nearest_neighbor(37.7840, -122.4030, k=1)
    assert len(results) == 1
    nearest_id, dist_m, lat, lon, data = results[0]
    assert nearest_id == "sf_downtown"
    assert dist_m < 200.0


def test_quadtree_query_bbox():
    bbox = BoundingBox(0.0, 0.0, 10.0, 10.0)
    index = QuadTreeSpatialIndex(bbox=bbox, capacity=2)

    index.insert("p1", 1.0, 1.0)
    index.insert("p2", 2.0, 2.0)
    index.insert("p3", 8.0, 8.0)
    index.insert("p4", 9.0, 9.0)

    # Sub-box covering bottom-left
    found = index.query_bbox(0.5, 0.5, 3.0, 3.0)
    found_ids = {p[0] for p in found}
    assert found_ids == {"p1", "p2"}
