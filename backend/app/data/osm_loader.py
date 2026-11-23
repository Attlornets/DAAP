"""
OpenStreetMap (OSM) Graph Loader via Overpass API and JSON Importer.
"""
import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Set

from app.core.graph import MultiModalGraph
from app.core.spatial_index import haversine_distance

logger = logging.getLogger(__name__)

# Standard OSM highway tags mapped to internal road classifications
OSM_HIGHWAY_MAPPING = {
    "motorway": "motorway",
    "motorway_link": "motorway",
    "trunk": "trunk",
    "trunk_link": "trunk",
    "primary": "primary",
    "primary_link": "primary",
    "secondary": "secondary",
    "secondary_link": "secondary",
    "tertiary": "tertiary",
    "tertiary_link": "tertiary",
    "residential": "residential",
    "living_street": "residential",
    "service": "service",
    "unclassified": "residential",
    "cycleway": "cycleway",
    "footway": "footway",
    "pedestrian": "pedestrian",
    "path": "footway"
}


def load_osm_from_json_data(data: Dict[str, Any], graph_name: str = "OSM Graph") -> MultiModalGraph:
    """
    Parses Overpass / OSM JSON elements (nodes and ways) into MultiModalGraph.
    """
    graph = MultiModalGraph(name=graph_name)

    nodes_dict: Dict[int, Dict[str, Any]] = {}
    ways_list: List[Dict[str, Any]] = []

    for element in data.get("elements", []):
        el_type = element.get("type")
        if el_type == "node":
            nodes_dict[element["id"]] = {
                "lat": element["lat"],
                "lon": element["lon"],
                "tags": element.get("tags", {})
            }
        elif el_type == "way":
            ways_list.append(element)

    # Add referenced nodes to graph
    used_node_ids: Set[int] = set()
    for way in ways_list:
        tags = way.get("tags", {})
        highway = tags.get("highway")
        if highway and highway in OSM_HIGHWAY_MAPPING:
            for nid in way.get("nodes", []):
                used_node_ids.add(nid)

    for nid in used_node_ids:
        if nid in nodes_dict:
            n = nodes_dict[nid]
            graph.add_node(
                node_id=str(nid),
                lat=n["lat"],
                lon=n["lon"],
                name=n["tags"].get("name")
            )

    # Add edges from ways
    for way in ways_list:
        tags = way.get("tags", {})
        highway = tags.get("highway")
        if not highway or highway not in OSM_HIGHWAY_MAPPING:
            continue

        road_type = OSM_HIGHWAY_MAPPING[highway]
        road_name = tags.get("name", road_type)
        oneway_tag = tags.get("oneway", "no")
        is_oneway = oneway_tag in ("yes", "1", "true")

        way_nodes = way.get("nodes", [])
        for i in range(len(way_nodes) - 1):
            u_id = str(way_nodes[i])
            v_id = str(way_nodes[i + 1])

            if u_id in graph.nodes and v_id in graph.nodes:
                graph.add_edge(
                    source=u_id,
                    target=v_id,
                    road_type=road_type,
                    oneway=is_oneway,
                    name=road_name
                )

    graph.build_spatial_index()
    return graph


def fetch_osm_overpass(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    timeout_s: int = 25
) -> Dict[str, Any]:
    """
    Fetches real OpenStreetMap street graph elements via public Overpass API endpoint.
    """
    query = f"""
    [out:json][timeout:{timeout_s}];
    (
      way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|service|cycleway|footway"]
         ({min_lat},{min_lon},{max_lat},{max_lon});
      >;
    );
    out body;
    """
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "RouteForge-LogisticsOptimizer/1.0"}
    )

    with urllib.request.urlopen(req, timeout=timeout_s + 5) as response:
        content = response.read().decode("utf-8")
        return json.loads(content)
