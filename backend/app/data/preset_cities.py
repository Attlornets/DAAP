"""
High-Fidelity Realistic City Road Networks and Preset Delivery Scenarios.

Features:
- San Francisco (Downtown, SoMa, Financial District, Embarcadero)
- Manhattan (Midtown, Broadway, Grand Central, Herald Square)
- London (Westminster, City of London, Thames Bridges, Covent Garden)
"""
from typing import Any, Dict, List, Tuple
from app.core.graph import MultiModalGraph
from app.algorithms.vrptw_models import DeliveryStop, Depot, VRPTWProblem
from app.core.time_dependent import parse_time_to_seconds


def generate_san_francisco_scenario() -> Tuple[MultiModalGraph, VRPTWProblem, Dict[str, Any]]:
    graph = MultiModalGraph(name="San Francisco - Downtown & SoMa")

    # Grid definition:
    # Avenues (SW-NE parallel to Market): Mission, Howard, Folsom, Harrison, Bryant, Brannan, Townsend, The Embarcadero
    # Cross Streets (NW-SE): The Embarcadero, 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th
    # North of Market (Financial District / Union Square): Market, Geary, Post, Sutter, Bush, California, Pine
    # North Cross Streets: Montgomery, Kearny, Grant, Stockton, Powell

    # Reference coordinates (lat, lon)
    # Origin approx: 8th & Townsend (37.7715, -122.4045)
    nodes_data = {}
    
    # 1. SoMa Grid: 8 avenues x 8 cross streets
    avenues = [
        ("Townsend", 37.7720, -122.3950, "secondary"),
        ("Brannan",  37.7745, -122.3975, "secondary"),
        ("Bryant",   37.7770, -122.4000, "primary"),     # Bryant connects to Bay Bridge
        ("Harrison", 37.7795, -122.4025, "primary"),
        ("Folsom",   37.7820, -122.4050, "secondary"),
        ("Howard",   37.7845, -122.4075, "primary"),
        ("Mission",  37.7870, -122.4100, "primary"),
        ("Market",   37.7895, -122.4125, "primary")      # Market St diagonal axis
    ]

    streets = [
        ("8th", 0.000, 0.000),
        ("7th", 0.0018, 0.0022),
        ("6th", 0.0036, 0.0044),
        ("5th", 0.0054, 0.0066),
        ("4th", 0.0072, 0.0088),
        ("3rd", 0.0090, 0.0110),
        ("2nd", 0.0108, 0.0132),
        ("1st", 0.0126, 0.0154),
        ("Embarcadero", 0.0150, 0.0180)
    ]

    for av_idx, (av_name, base_lat, base_lon, av_type) in enumerate(avenues):
        for st_idx, (st_name, lat_off, lon_off) in enumerate(streets):
            node_id = f"sf_{av_name}_{st_name}".lower()
            lat = round(base_lat + lat_off, 6)
            lon = round(base_lon + lon_off, 6)
            graph.add_node(node_id, lat, lon, name=f"{av_name} St & {st_name} St")
            nodes_data[(av_idx, st_idx)] = node_id

    # Add Edges for SoMa:
    # Avenues run along SW <-> NE
    for av_idx, (av_name, _, _, av_type) in enumerate(avenues):
        # Mission and Market have bus/transit lanes, Howard/Folsom alternate one-ways
        is_oneway = (av_name in ("Howard", "Folsom", "Bush", "Pine"))
        for st_idx in range(len(streets) - 1):
            u = nodes_data[(av_idx, st_idx)]
            v = nodes_data[(av_idx, st_idx + 1)]
            graph.add_edge(u, v, road_type=av_type, oneway=is_oneway, name=av_name)

    # Cross streets run NW <-> SE
    for st_idx, (st_name, _, _) in enumerate(streets):
        road_type = "primary" if st_name in ("3rd", "4th", "Embarcadero") else "secondary"
        for av_idx in range(len(avenues) - 1):
            u = nodes_data[(av_idx, st_idx)]
            v = nodes_data[(av_idx + 1, st_idx)]
            # 3rd is one-way north, 4th is one-way south
            oneway = (st_name in ("3rd", "4th"))
            graph.add_edge(u, v, road_type=road_type, oneway=oneway, name=st_name)

    # 2. Financial District / Union Square Grid (North of Market)
    north_streets = ["Geary", "Post", "Sutter", "Bush", "California", "Pine"]
    cross_north = ["Powell", "Stockton", "Grant", "Kearny", "Montgomery", "Sansome", "Battery", "Davis"]

    fidi_nodes = {}
    base_fidi_lat = 37.7885
    base_fidi_lon = -122.4060

    for r_idx, r_name in enumerate(north_streets):
        for c_idx, c_name in enumerate(cross_north):
            nid = f"sf_{r_name}_{c_name}".lower()
            lat = round(base_fidi_lat + (r_idx * 0.0016), 6)
            lon = round(base_fidi_lon + (c_idx * 0.0022), 6)
            graph.add_node(nid, lat, lon, name=f"{r_name} St & {c_name} St")
            fidi_nodes[(r_idx, c_idx)] = nid

    for r_idx, r_name in enumerate(north_streets):
        for c_idx in range(len(cross_north) - 1):
            u = fidi_nodes[(r_idx, c_idx)]
            v = fidi_nodes[(r_idx, c_idx + 1)]
            graph.add_edge(u, v, road_type="secondary", oneway=(r_name in ("Bush", "Pine")), name=r_name)

    for c_idx, c_name in enumerate(cross_north):
        for r_idx in range(len(north_streets) - 1):
            u = fidi_nodes[(r_idx, c_idx)]
            v = fidi_nodes[(r_idx + 1, c_idx)]
            graph.add_edge(u, v, road_type="secondary", oneway=(c_name in ("Montgomery", "Sansome")), name=c_name)

    # Connect Market Street to FiDi
    connectors = [
        (nodes_data[(7, 4)], fidi_nodes[(0, 0)], "Powell Cable Car Line"),
        (nodes_data[(7, 5)], fidi_nodes[(0, 2)], "Grant Ave Gateway"),
        (nodes_data[(7, 6)], fidi_nodes[(0, 4)], "Montgomery Station Corridor"),
        (nodes_data[(7, 7)], fidi_nodes[(0, 6)], "Battery St Arterial")
    ]
    for u, v, c_name in connectors:
        graph.add_edge(u, v, road_type="primary", oneway=False, name=c_name)

    # 3. Add Motorway / Highway segment (I-80 Bay Bridge Approach & Embarcadero Expressway)
    i80_nodes = [
        ("sf_i80_us101_split", 37.7680, -122.4080, "I-80 / US-101 Interchange"),
        ("sf_i80_7th",         37.7735, -122.4040, "I-80 at 7th St Exit"),
        ("sf_i80_4th",         37.7780, -122.3990, "I-80 at 4th St Ramp"),
        ("sf_i80_fremont",     37.7850, -122.3910, "I-80 Fremont / Bay Bridge Toll Plaza")
    ]
    for nid, lat, lon, name in i80_nodes:
        graph.add_node(nid, lat, lon, name=name)

    for i in range(len(i80_nodes) - 1):
        graph.add_edge(i80_nodes[i][0], i80_nodes[i+1][0], road_type="motorway", oneway=False, name="I-80 Skyway")

    # Connect Highway to City Grid
    graph.add_edge("sf_i80_7th", nodes_data[(2, 1)], road_type="trunk", oneway=True, name="Bryant St Offramp")
    graph.add_edge(nodes_data[(3, 3)], "sf_i80_4th", road_type="trunk", oneway=True, name="Harrison St Onramp")
    graph.add_edge("sf_i80_fremont", nodes_data[(0, 8)], road_type="primary", oneway=False, name="Fremont Connector")

    graph.build_spatial_index()

    # Define Preset VRPTW Depot & Delivery Stops
    depot = Depot(
        id="sf_depot_soma",
        name="SoMa Central Dispatch Hub",
        lat=37.7795,
        lon=-122.4025,
        start_time_s=parse_time_to_seconds("08:00")
    )
    depot.nearest_node_id = graph.find_nearest_node(depot.lat, depot.lon)[0]

    stops_raw = [
        {"id": "sf_stop_01", "name": "Salesforce Tower (Mission & Fremont)", "lat": 37.7897, "lon": -122.3972, "demand": 18.0, "serv": 360, "e": "08:15", "l": "09:15"},
        {"id": "sf_stop_02", "name": "Ferry Building Artisanal Market",      "lat": 37.7955, "lon": -122.3937, "demand": 24.0, "serv": 480, "e": "08:30", "l": "09:45"},
        {"id": "sf_stop_03", "name": "Union Square Retail Plaza",            "lat": 37.7879, "lon": -122.4075, "demand": 30.0, "serv": 600, "e": "09:00", "l": "10:30"},
        {"id": "sf_stop_04", "name": "Moscone Convention Center",           "lat": 37.7842, "lon": -122.4016, "demand": 35.0, "serv": 720, "e": "08:45", "l": "10:00"},
        {"id": "sf_stop_05", "name": "Transamerica Pyramid Commercial",     "lat": 37.7952, "lon": -122.4028, "demand": 15.0, "serv": 300, "e": "09:15", "l": "10:45"},
        {"id": "sf_stop_06", "name": "Oracle Park Ballpark Deliveries",      "lat": 37.7786, "lon": -122.3893, "demand": 28.0, "serv": 500, "e": "08:20", "l": "09:30"},
        {"id": "sf_stop_07", "name": "LinkedIn HQ SF Office",               "lat": 37.7865, "lon": -122.3995, "demand": 12.0, "serv": 300, "e": "08:45", "l": "10:15"},
        {"id": "sf_stop_08", "name": "Rincon Hill Luxury Residences",        "lat": 37.7860, "lon": -122.3920, "demand": 16.0, "serv": 360, "e": "09:30", "l": "11:00"},
        {"id": "sf_stop_09", "name": "Yerba Buena Center for the Arts",     "lat": 37.7855, "lon": -122.4035, "demand": 20.0, "serv": 420, "e": "08:30", "l": "09:50"},
        {"id": "sf_stop_10", "name": "California Cable Car Terminal",        "lat": 37.7930, "lon": -122.4045, "demand": 14.0, "serv": 300, "e": "09:45", "l": "11:15"},
        {"id": "sf_stop_11", "name": "Embarcadero Center Complex",           "lat": 37.7947, "lon": -122.3980, "demand": 22.0, "serv": 450, "e": "09:00", "l": "10:15"},
        {"id": "sf_stop_12", "name": "Uber Mission Bay HQ",                  "lat": 37.7685, "lon": -122.3910, "demand": 19.0, "serv": 400, "e": "08:15", "l": "09:30"}
    ]

    stops: List[DeliveryStop] = []
    for s in stops_raw:
        near_node, _ = graph.find_nearest_node(s["lat"], s["lon"])
        stop_obj = DeliveryStop(
            id=s["id"],
            name=s["name"],
            lat=s["lat"],
            lon=s["lon"],
            demand=s["demand"],
            service_time_s=s["serv"],
            earliest_arrival_s=parse_time_to_seconds(s["e"]),
            latest_arrival_s=parse_time_to_seconds(s["l"]),
            nearest_node_id=near_node
        )
        stops.append(stop_obj)

    # Build Distance and Duration Matrix using Dijkstra on our graph
    all_points = [depot] + stops
    n_pts = len(all_points)
    dist_matrix = [[0.0] * n_pts for _ in range(n_pts)]
    time_matrix = [[0.0] * n_pts for _ in range(n_pts)]

    from app.algorithms.dijkstra import run_dijkstra

    for i in range(n_pts):
        src_node = all_points[i].nearest_node_id
        res = run_dijkstra(graph, src_node, target_id=None, mode="driving", departure_time_seconds=depot.start_time_s)
        distances = res.get("all_distances", {})

        for j in range(n_pts):
            if i == j:
                continue
            tgt_node = all_points[j].nearest_node_id
            travel_time = distances.get(tgt_node, 600.0)
            # Approximate road distance based on travel time and avg city speed (25 km/h)
            dist_m = travel_time * (25.0 / 3.6)
            dist_matrix[i][j] = dist_m
            time_matrix[i][j] = travel_time

    problem = VRPTWProblem(
        depot=depot,
        stops=stops,
        fleet_size=3,
        vehicle_capacity=85.0,
        late_penalty_per_min=2.5,
        dist_matrix=dist_matrix,
        time_matrix=time_matrix
    )

    metadata = {
        "city": "San Francisco",
        "description": "Downtown SF Financial District, SoMa & Embarcadero with morning rush hour congestion.",
        "center": [37.7850, -122.4020],
        "default_zoom": 14,
        "default_mode": "driving"
    }

    return graph, problem, metadata


def generate_manhattan_scenario() -> Tuple[MultiModalGraph, VRPTWProblem, Dict[str, Any]]:
    graph = MultiModalGraph(name="Manhattan - Midtown & Hudson Yards")

    # Avenues (running roughly N-S): 11th, 10th, 9th, 8th, 7th, 6th (Americas), 5th, Madison, Park, Lexington
    # Cross streets (running W-E): 34th, 36th, 38th, 40th, 42nd, 44th, 46th, 48th, 50th
    # Broadway runs diagonally cutting 42nd at Times Square!

    avenues = [
        ("11th", -74.0040, "primary", True),     # One-way South
        ("10th", -74.0000, "primary", False),    # One-way North
        ("9th",  -73.9960, "primary", True),     # South
        ("8th",  -73.9910, "primary", False),    # North
        ("7th",  -73.9860, "primary", True),     # South
        ("6th",  -73.9820, "primary", False),    # North
        ("5th",  -73.9770, "primary", True),     # South
        ("Mad",  -73.9740, "secondary", False),  # North
        ("Park", -73.9700, "primary", False),    # Two-way
        ("Lex",  -73.9660, "secondary", True)    # South
    ]

    streets = [
        ("34th", 40.7500, "primary", False),   # Two-way major arterial
        ("36th", 40.7525, "secondary", True),  # Westbound
        ("38th", 40.7550, "secondary", False), # Eastbound
        ("40th", 40.7575, "secondary", True),  # Westbound
        ("42nd", 40.7600, "primary", False),   # Two-way major corridor
        ("44th", 40.7625, "secondary", False), # Eastbound
        ("46th", 40.7650, "secondary", True),  # Westbound
        ("48th", 40.7675, "secondary", False), # Eastbound
        ("50th", 40.7700, "primary", False)    # Two-way
    ]

    grid_nodes = {}
    for a_idx, (a_name, a_lon, a_type, _) in enumerate(avenues):
        for s_idx, (s_name, s_lat, s_type, _) in enumerate(streets):
            nid = f"nyc_{s_name}_{a_name}".lower()
            lat = round(s_lat, 6)
            lon = round(a_lon, 6)
            graph.add_node(nid, lat, lon, name=f"{s_name} St & {a_name} Ave")
            grid_nodes[(a_idx, s_idx)] = nid

    # Add Avenue edges
    for a_idx, (a_name, _, a_type, south_bound) in enumerate(avenues):
        for s_idx in range(len(streets) - 1):
            u = grid_nodes[(a_idx, s_idx)]
            v = grid_nodes[(a_idx, s_idx + 1)]
            if a_name == "Park":
                graph.add_edge(u, v, road_type=a_type, oneway=False, name=f"{a_name} Ave")
            elif south_bound:
                graph.add_edge(v, u, road_type=a_type, oneway=True, name=f"{a_name} Ave (Southbound)")
            else:
                graph.add_edge(u, v, road_type=a_type, oneway=True, name=f"{a_name} Ave (Northbound)")

    # Add Street edges
    for s_idx, (s_name, _, s_type, west_bound) in enumerate(streets):
        for a_idx in range(len(avenues) - 1):
            east_node = grid_nodes[(a_idx, s_idx)]
            west_node = grid_nodes[(a_idx + 1, s_idx)]
            if s_name in ("34th", "42nd", "50th"):
                graph.add_edge(east_node, west_node, road_type=s_type, oneway=False, name=f"{s_name} St")
            elif west_bound:
                graph.add_edge(west_node, east_node, road_type=s_type, oneway=True, name=f"{s_name} St (Westbound)")
            else:
                graph.add_edge(east_node, west_node, road_type=s_type, oneway=True, name=f"{s_name} St (Eastbound)")

    # Add Broadway Diagonal
    broadway_cuts = [
        ("nyc_bway_34th", 40.7505, -73.9880, "Broadway at Herald Square"),
        ("nyc_bway_38th", 40.7540, -73.9860, "Broadway at 38th St"),
        ("nyc_bway_42nd", 40.7580, -73.9845, "Broadway at Times Square"),
        ("nyc_bway_46th", 40.7620, -73.9830, "Broadway at Duffy Square"),
        ("nyc_bway_50th", 40.7660, -73.9815, "Broadway at 50th Theater Dist")
    ]
    for nid, lat, lon, name in broadway_cuts:
        graph.add_node(nid, lat, lon, name=name)

    for i in range(len(broadway_cuts) - 1):
        graph.add_edge(broadway_cuts[i][0], broadway_cuts[i+1][0], road_type="primary", oneway=True, name="Broadway Diagonal (Southbound)")

    # Connect Broadway into avenues
    graph.add_edge("nyc_bway_42nd", grid_nodes[(4, 4)], road_type="primary", oneway=False, name="Times Square Crossing")
    graph.add_edge("nyc_bway_34th", grid_nodes[(3, 0)], road_type="primary", oneway=False, name="Herald Sq Connector")

    graph.build_spatial_index()

    depot = Depot(
        id="nyc_depot_hudson",
        name="Hudson Yards Fleet Depot",
        lat=40.7545,
        lon=-74.0020,
        start_time_s=parse_time_to_seconds("08:00")
    )
    depot.nearest_node_id = graph.find_nearest_node(depot.lat, depot.lon)[0]

    stops_raw = [
        {"id": "nyc_stop_01", "name": "Empire State Building Logistics",   "lat": 40.7484, "lon": -73.9857, "demand": 25.0, "serv": 480, "e": "08:15", "l": "09:30"},
        {"id": "nyc_stop_02", "name": "Grand Central Terminal Express",    "lat": 40.7527, "lon": -73.9772, "demand": 30.0, "serv": 600, "e": "08:30", "l": "10:00"},
        {"id": "nyc_stop_03", "name": "Times Square Visitor Center",       "lat": 40.7580, "lon": -73.9855, "demand": 18.0, "serv": 360, "e": "08:45", "l": "09:50"},
        {"id": "nyc_stop_04", "name": "Bryant Park Public Library",        "lat": 40.7536, "lon": -73.9832, "demand": 15.0, "serv": 300, "e": "09:00", "l": "10:15"},
        {"id": "nyc_stop_05", "name": "Rockefeller Center Concourse",      "lat": 40.7587, "lon": -73.9787, "demand": 22.0, "serv": 450, "e": "09:15", "l": "10:30"},
        {"id": "nyc_stop_06", "name": "Penn Station Delivery Bay",         "lat": 40.7505, "lon": -73.9934, "demand": 35.0, "serv": 600, "e": "08:15", "l": "09:15"},
        {"id": "nyc_stop_07", "name": "Macy's Herald Square Retail",       "lat": 40.7510, "lon": -73.9890, "demand": 28.0, "serv": 500, "e": "08:30", "l": "09:45"},
        {"id": "nyc_stop_08", "name": "Javits Center Freight Gate",        "lat": 40.7570, "lon": -74.0025, "demand": 40.0, "serv": 720, "e": "08:00", "l": "09:00"},
        {"id": "nyc_stop_09", "name": "Madison Square Garden Cargo",       "lat": 40.7505, "lon": -73.9935, "demand": 20.0, "serv": 400, "e": "09:30", "l": "10:45"},
        {"id": "nyc_stop_10", "name": "Chrysler Building Loading Dock",    "lat": 40.7516, "lon": -73.9754, "demand": 17.0, "serv": 360, "e": "09:45", "l": "11:00"}
    ]

    stops: List[DeliveryStop] = []
    for s in stops_raw:
        near_node, _ = graph.find_nearest_node(s["lat"], s["lon"])
        stops.append(DeliveryStop(
            id=s["id"],
            name=s["name"],
            lat=s["lat"],
            lon=s["lon"],
            demand=s["demand"],
            service_time_s=s["serv"],
            earliest_arrival_s=parse_time_to_seconds(s["e"]),
            latest_arrival_s=parse_time_to_seconds(s["l"]),
            nearest_node_id=near_node
        ))

    from app.algorithms.dijkstra import run_dijkstra
    all_points = [depot] + stops
    n_pts = len(all_points)
    dist_matrix = [[0.0] * n_pts for _ in range(n_pts)]
    time_matrix = [[0.0] * n_pts for _ in range(n_pts)]

    for i in range(n_pts):
        src_node = all_points[i].nearest_node_id
        res = run_dijkstra(graph, src_node, target_id=None, mode="driving", departure_time_seconds=depot.start_time_s)
        distances = res.get("all_distances", {})
        for j in range(n_pts):
            if i == j:
                continue
            tgt_node = all_points[j].nearest_node_id
            travel_time = distances.get(tgt_node, 500.0)
            dist_matrix[i][j] = travel_time * (22.0 / 3.6)
            time_matrix[i][j] = travel_time

    problem = VRPTWProblem(
        depot=depot,
        stops=stops,
        fleet_size=3,
        vehicle_capacity=95.0,
        late_penalty_per_min=3.0,
        dist_matrix=dist_matrix,
        time_matrix=time_matrix
    )

    metadata = {
        "city": "Manhattan",
        "description": "Midtown Manhattan one-way grid, Broadway crossing, and heavy delivery congestion.",
        "center": [40.7550, -73.9850],
        "default_zoom": 14,
        "default_mode": "delivery_van"
    }

    return graph, problem, metadata


def generate_london_scenario() -> Tuple[MultiModalGraph, VRPTWProblem, Dict[str, Any]]:
    graph = MultiModalGraph(name="London - Westminster & The City")

    # London irregular historic network with Thames crossings
    nodes = [
        ("ldn_depot_waterloo", 51.5030, -0.1140, "Waterloo Logistics Hub"),
        ("ldn_westminster_bridge_s", 51.5015, -0.1200, "Westminster Bridge South"),
        ("ldn_westminster_bridge_n", 51.5010, -0.1245, "Westminster Bridge North / Big Ben"),
        ("ldn_parliament_sq",        51.5005, -0.1265, "Parliament Square"),
        ("ldn_whitehall",            51.5045, -0.1260, "Whitehall Government Offices"),
        ("ldn_trafalgar_sq",         51.5080, -0.1280, "Trafalgar Square"),
        ("ldn_strand",               51.5110, -0.1200, "The Strand"),
        ("ldn_covent_garden",        51.5118, -0.1235, "Covent Garden Market"),
        ("ldn_waterloo_bridge_n",    51.5105, -0.1170, "Waterloo Bridge North"),
        ("ldn_waterloo_bridge_s",    51.5070, -0.1150, "Waterloo Bridge South"),
        ("ldn_blackfriars_bridge_s", 51.5085, -0.1030, "Blackfriars Bridge South"),
        ("ldn_blackfriars_bridge_n", 51.5120, -0.1040, "Blackfriars Bridge North"),
        ("ldn_fleet_st",             51.5140, -0.1090, "Fleet Street Historic Press"),
        ("ldn_st_pauls",             51.5138, -0.0983, "St. Paul's Cathedral"),
        ("ldn_bank",                 51.5134, -0.0890, "Bank of England Junction"),
        ("ldn_london_wall",          51.5175, -0.0910, "London Wall North"),
        ("ldn_london_bridge_n",      51.5090, -0.0865, "London Bridge North / Monument"),
        ("ldn_london_bridge_s",      51.5050, -0.0880, "London Bridge South / Borough"),
        ("ldn_borough_market",       51.5055, -0.0910, "Borough Market Artisanal"),
        ("ldn_tate_modern",          51.5076, -0.0994, "Tate Modern South Bank")
    ]

    for nid, lat, lon, name in nodes:
        graph.add_node(nid, lat, lon, name=name)

    # Connections / Edges
    edges = [
        ("ldn_depot_waterloo", "ldn_waterloo_bridge_s", "primary", False, "Waterloo Rd"),
        ("ldn_depot_waterloo", "ldn_westminster_bridge_s", "primary", False, "York Rd"),
        ("ldn_westminster_bridge_s", "ldn_westminster_bridge_n", "primary", False, "Westminster Bridge"),
        ("ldn_westminster_bridge_n", "ldn_parliament_sq", "primary", False, "Bridge St"),
        ("ldn_parliament_sq", "ldn_whitehall", "primary", False, "Whitehall"),
        ("ldn_whitehall", "ldn_trafalgar_sq", "primary", False, "Whitehall North"),
        ("ldn_trafalgar_sq", "ldn_strand", "primary", False, "Strand West"),
        ("ldn_strand", "ldn_covent_garden", "secondary", False, "Southampton St"),
        ("ldn_strand", "ldn_waterloo_bridge_n", "primary", False, "Aldwych"),
        ("ldn_waterloo_bridge_n", "ldn_waterloo_bridge_s", "primary", False, "Waterloo Bridge"),
        ("ldn_waterloo_bridge_n", "ldn_fleet_st", "secondary", False, "Fleet St Link"),
        ("ldn_fleet_st", "ldn_blackfriars_bridge_n", "primary", False, "Ludgate Circus"),
        ("ldn_blackfriars_bridge_n", "ldn_blackfriars_bridge_s", "primary", False, "Blackfriars Bridge"),
        ("ldn_blackfriars_bridge_s", "ldn_tate_modern", "secondary", False, "Southwark St"),
        ("ldn_tate_modern", "ldn_borough_market", "secondary", False, "Bankside"),
        ("ldn_borough_market", "ldn_london_bridge_s", "secondary", False, "Borough High St"),
        ("ldn_london_bridge_s", "ldn_london_bridge_n", "primary", False, "London Bridge"),
        ("ldn_blackfriars_bridge_n", "ldn_st_pauls", "primary", False, "Ludgate Hill"),
        ("ldn_st_pauls", "ldn_bank", "primary", False, "Cheapside"),
        ("ldn_bank", "ldn_london_bridge_n", "primary", False, "King William St"),
        ("ldn_bank", "ldn_london_wall", "primary", False, "Princes St / Moorgate")
    ]

    for u, v, r_type, oneway, name in edges:
        graph.add_edge(u, v, road_type=r_type, oneway=oneway, name=name)

    graph.build_spatial_index()

    depot = Depot(
        id="ldn_depot_waterloo",
        name="Waterloo Multi-Modal Hub",
        lat=51.5030,
        lon=-0.1140,
        start_time_s=parse_time_to_seconds("08:00")
    )
    depot.nearest_node_id = "ldn_depot_waterloo"

    stops_raw = [
        {"id": "ldn_stop_01", "name": "Covent Garden Market Hall",         "lat": 51.5118, "lon": -0.1235, "demand": 22.0, "serv": 420, "e": "08:20", "l": "09:30"},
        {"id": "ldn_stop_02", "name": "St. Paul's Cathedral Visitors",     "lat": 51.5138, "lon": -0.0983, "demand": 18.0, "serv": 360, "e": "08:45", "l": "10:00"},
        {"id": "ldn_stop_03", "name": "Bank of England Vaults",            "lat": 51.5134, "lon": -0.0890, "demand": 25.0, "serv": 500, "e": "09:15", "l": "10:30"},
        {"id": "ldn_stop_04", "name": "Borough Market Food Logistics",     "lat": 51.5055, "lon": -0.0910, "demand": 30.0, "serv": 600, "e": "08:15", "l": "09:15"},
        {"id": "ldn_stop_05", "name": "Tate Modern Gallery Store",         "lat": 51.5076, "lon": -0.0994, "demand": 15.0, "serv": 300, "e": "09:30", "l": "11:00"},
        {"id": "ldn_stop_06", "name": "Parliament Square Press Courier",    "lat": 51.5005, "lon": -0.1265, "demand": 12.0, "serv": 240, "e": "08:30", "l": "09:45"},
        {"id": "ldn_stop_07", "name": "Trafalgar Square Gallery Hub",       "lat": 51.5080, "lon": -0.1280, "demand": 20.0, "serv": 400, "e": "09:00", "l": "10:15"},
        {"id": "ldn_stop_08", "name": "London Wall Corporate Center",       "lat": 51.5175, "lon": -0.0910, "demand": 26.0, "serv": 480, "e": "09:30", "l": "10:45"}
    ]

    stops: List[DeliveryStop] = []
    for s in stops_raw:
        near_node, _ = graph.find_nearest_node(s["lat"], s["lon"])
        stops.append(DeliveryStop(
            id=s["id"],
            name=s["name"],
            lat=s["lat"],
            lon=s["lon"],
            demand=s["demand"],
            service_time_s=s["serv"],
            earliest_arrival_s=parse_time_to_seconds(s["e"]),
            latest_arrival_s=parse_time_to_seconds(s["l"]),
            nearest_node_id=near_node
        ))

    from app.algorithms.dijkstra import run_dijkstra
    all_points = [depot] + stops
    n_pts = len(all_points)
    dist_matrix = [[0.0] * n_pts for _ in range(n_pts)]
    time_matrix = [[0.0] * n_pts for _ in range(n_pts)]

    for i in range(n_pts):
        src_node = all_points[i].nearest_node_id
        res = run_dijkstra(graph, src_node, target_id=None, mode="cycling", departure_time_seconds=depot.start_time_s)
        distances = res.get("all_distances", {})
        for j in range(n_pts):
            if i == j:
                continue
            tgt_node = all_points[j].nearest_node_id
            travel_time = distances.get(tgt_node, 400.0)
            dist_matrix[i][j] = travel_time * (18.0 / 3.6)
            time_matrix[i][j] = travel_time

    problem = VRPTWProblem(
        depot=depot,
        stops=stops,
        fleet_size=2,
        vehicle_capacity=75.0,
        late_penalty_per_min=2.0,
        dist_matrix=dist_matrix,
        time_matrix=time_matrix
    )

    metadata = {
        "city": "London",
        "description": "Westminster, Covent Garden, The City & Southwark bridges with cargo cycle delivery options.",
        "center": [51.5080, -0.1080],
        "default_zoom": 14,
        "default_mode": "cycling"
    }

    return graph, problem, metadata
