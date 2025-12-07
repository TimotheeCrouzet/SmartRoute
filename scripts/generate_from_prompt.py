import os
import yaml
import json
import pickle
import requests
import networkx as nx
from pathlib import Path
from math import radians, cos, sin, asin, sqrt
from scripts.anthropic_rooter import AnthropicRooter

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1)*cos(lat2)*sin(dlon / 2)**2
    return 2 * R * asin(sqrt(a))

def geocode_place(place_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "limit": 1}
    headers = {"User-Agent": "SmartRouteBot/1.0"}
    resp = requests.get(url, params=params, headers=headers)
    if resp.status_code == 200 and resp.json():
        lat = float(resp.json()[0]["lat"])
        lon = float(resp.json()[0]["lon"])
        return lat, lon
    return None, None

def compute_waypoint(lat, lon, dist_meters, angle_deg):
    angle_rad = radians(angle_deg)
    delta_lat = (dist_meters * cos(angle_rad)) / 111000
    delta_lon = (dist_meters * sin(angle_rad)) / (111000 * cos(radians(lat)))
    return lat + delta_lat, lon + delta_lon

def find_nearest_node(G, lat, lon):
    return min(G.nodes, key=lambda n: haversine(lat, lon, G.nodes[n]["y"], G.nodes[n]["x"]))

def spatial_ratio(path, G):
    if len(path) < 2:
        return 1
    lat1, lon1 = G.nodes[path[0]]["y"], G.nodes[path[0]]["x"]
    lat2, lon2 = G.nodes[path[-1]]["y"], G.nodes[path[-1]]["x"]
    direct = haversine(lat1, lon1, lat2, lon2)
    path_len = sum(
        haversine(G.nodes[a]["y"], G.nodes[a]["x"], G.nodes[b]["y"], G.nodes[b]["x"])
        for a, b in zip(path[:-1], path[1:])
    )
    return direct / path_len if path_len > 0 else 1

def node_diversity(path):
    return len(set(path)) / len(path) if path else 0

def total_distance(G, path):
    return sum(
        haversine(G.nodes[a]["y"], G.nodes[a]["x"], G.nodes[b]["y"], G.nodes[b]["x"])
        for a, b in zip(path[:-1], path[1:])
    )

def generate_forced_loop(G, start, lat_start, lon_start, target_dist, profil, angle):
    attr = f"cost_{profil}"
    radius = target_dist / 3
    lat_wp, lon_wp = compute_waypoint(lat_start, lon_start, radius, angle)
    waypoint = find_nearest_node(G, lat_wp, lon_wp)

    try:
        _, path_out = nx.single_source_dijkstra(G, start, waypoint, weight=attr, cutoff=radius * 1.5)
    except nx.NetworkXNoPath:
        return None

    edges_out = [(path_out[i], path_out[i+1]) for i in range(len(path_out)-1)]
    G.remove_edges_from(edges_out)

    try:
        _, path_back = nx.single_source_dijkstra(G, waypoint, start, weight=attr, cutoff=radius * 1.5)
    except nx.NetworkXNoPath:
        G.add_edges_from(edges_out)
        return None

    G.add_edges_from(edges_out)
    return path_out, path_back

def export_gpx(G, path, filename="outputs/route_from_prompt.gpx"):
    from lxml import etree as ET
    gpx = ET.Element("gpx", version="1.1", creator="SmartRoute")
    trk = ET.SubElement(gpx, "trk")
    trkseg = ET.SubElement(trk, "trkseg")

    for node in path:
        lat, lon = G.nodes[node]["y"], G.nodes[node]["x"]
        ET.SubElement(trkseg, "trkpt", lat=str(lat), lon=str(lon))

    tree = ET.ElementTree(gpx)
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    tree.write(filename, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    return filename

def generate_from_prompt(prompt: str) -> dict:
    with open("tim.yml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    ia = AnthropicRooter(config["ANTHROPIC_API_KEY"])
    params = ia.user_prompt_2_json(prompt)

    mode = params["mode"]
    profil = params["profil"]
    ville = params["zone"]
    distance_cible = params["distance"]

    graph_path = Path(f"data/processed/osm_graph_weighted_all_profiles_{mode}.gpickle")
    if not graph_path.exists():
        raise FileNotFoundError(f"Graphe introuvable : {graph_path}")
    with open(graph_path, "rb") as f:
        G = pickle.load(f)

    lat, lon = geocode_place(ville)
    if lat is None:
        raise ValueError("Lieu non reconnu")

    # === Vérification avec marge de sécurité ===
    LAT_MIN, LAT_MAX = 48.145309, 48.954693
    LON_MIN, LON_MAX = 2.188650, 3.411287
    MARGIN = 0.01  # ≈ 1 km
    if not ((LAT_MIN - MARGIN) <= lat <= (LAT_MAX + MARGIN) and (LON_MIN - MARGIN) <= lon <= (LON_MAX + MARGIN)):
        raise ValueError(
            "❌ Zone hors couverture : SmartRoute ne couvre actuellement que la région Île-de-France. "
            "Essayez avec Fontainebleau, Nemours, Melun..."
        )

    start_node = find_nearest_node(G, lat, lon)

    best_score = -1
    best_path = None
    best_distance = 0

    for angle in [60, 90, 120, 150, 180]:
        loop = generate_forced_loop(G, start_node, lat, lon, distance_cible, profil, angle)
        if loop:
            full_path = loop[0] + loop[1][1:]
            distance = total_distance(G, full_path)

            if not (0.7 * distance_cible <= distance <= 1.3 * distance_cible):
                continue

            diversity = node_diversity(full_path)
            linearity = spatial_ratio(full_path, G)
            score = 0.5 * diversity + 0.5 * (1 - linearity)

            if score > best_score:
                best_score = score
                best_path = full_path
                best_distance = distance

    if best_path is None:
        raise RuntimeError("Aucune boucle générée")

    gpx_path = export_gpx(G, best_path)
    return {
        "map_url": f"/outputs/{os.path.basename(gpx_path)}",
        "distance": best_distance
    }
