"""PYTHONPATH=. .venv/bin/python scripts/main_generate_loop.py
"""

import os
import pickle
import json
import requests
import networkx as nx
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

# === Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# === Fonctions utilitaires ===

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

def save_loop_as_gpx(G, path_tuple, filename="route_manual.gpx"):
    if not path_tuple:
        return None

    full_path = path_tuple[0] + path_tuple[1][1:]
    path = OUTPUT_DIR / filename

    with open(path, "w", encoding="utf-8") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<gpx version="1.1" creator="SmartRoute" xmlns="http://www.topografix.com/GPX/1/1">
<trk><name>SmartRoute Loop</name><trkseg>\n""")
        for node in full_path:
            lat, lon = G.nodes[node]["y"], G.nodes[node]["x"]
            f.write(f'<trkpt lat="{lat}" lon="{lon}"></trkpt>\n')
        f.write("</trkseg></trk>\n</gpx>")

    return str(path.relative_to(BASE_DIR))

# === MAIN : Mode manuel ===

def main():
    ville = input("🏙️ Ville ou zone de départ : ").strip()
    distance = int(input("📏 Distance cible (mètres, ex: 20000) : "))
    profil = input("👤 Niveau (debutant / confirme / expert) : ").strip().lower()
    mode = input("🧭 Mode (classic / explore) : ").strip().lower()

    graph_path = GRAPH_DIR / f"osm_graph_weighted_all_profiles_{mode}.gpickle"
    if not graph_path.exists():
        print(f"Graphe introuvable : {graph_path}")
        return

    with open(graph_path, "rb") as f:
        G = pickle.load(f)

    lat, lon = geocode_place(ville)
    if lat is None:
        print("Erreur géocodage")
        return

    start_node = find_nearest_node(G, lat, lon)
    print(f"Départ depuis le nœud {start_node}")

    best_score = -1
    best_path = None

    for angle in [60, 90, 120, 150, 180]:
        loop = generate_forced_loop(G, start_node, lat, lon, distance, profil, angle)
        if loop:
            full = loop[0] + loop[1][1:]
            div = node_diversity(full)
            lin = spatial_ratio(full, G)
            score = 0.5 * div + 0.5 * (1 - lin)
            print(f"↪️ Angle {angle}° → diversité={div:.2f} / linéarité={lin:.2f} / score={score:.2f}")
            if score > best_score:
                best_score = score
                best_path = loop

    if best_path:
        gpx_path = save_loop_as_gpx(G, best_path)
        print(f"Boucle exportée dans : {gpx_path}")
    else:
        print("Aucune boucle valide générée.")

if __name__ == "__main__":
    main()
