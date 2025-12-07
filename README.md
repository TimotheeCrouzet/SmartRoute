# 🧠 SmartRoute – Générateur d’itinéraires intelligent

Projet de fin d’année E3 – ESIEE Paris (2024–2025)

## 👥 Équipe

- Antoine CHEN  
- Adam NOUARI  
- Mohamed SEBBAR  
- Nikola MILOSAVLJEVIC  
- Timothée CROUZET  

## 🎯 Objectif

Créer un générateur d’itinéraires intelligent capable de proposer des parcours adaptés à l’utilisateur, en se basant sur :
- les **données cartographiques d’OpenStreetMap**,
- la **popularité issue de la heatmap Strava**,
- et une couche **IA pour apprendre les préférences utilisateurs**.

# 📁 Architecture du projet SmartRoute

Ce document décrit le rôle de chaque dossier et fichier dans l’environnement de développement du projet **SmartRoute**.

---

## 📁 `data/` – Données

Contient toutes les **données utilisées ou générées** par le projet.

- `raw_osm/` : Graphes OSM bruts téléchargés via `osmnx`.
- `strava_tiles/` : Tuiles PNG de la heatmap Strava.
- `processed/` : Données enrichies (graphes pondérés, fusion Strava + OSM).
- `user_data/` : Traces GPS d’utilisateurs (fictifs ou réels).
- `cache/` : Données temporaires (ex : zones déjà téléchargées).

---

## 📁 `src/` – Code source principal

Organisé par logique fonctionnelle.

### 📁 `data_collection/`
- `download_osm.py` : Téléchargement de données OpenStreetMap.
- `download_strava.py` : Téléchargement et assemblage des tuiles Strava.
- `tile_utils.py` : Conversion coordonnées ↔ tuiles + calculs géographiques.

### 📁 `preprocessing/`
- `preprocessing_init.py` : Code hérité de l’ancien système à traces simulées.
- `heatmap_to_mask.py` : Convertit une image PNG de heatmap en matrice d’intensité.
- `overlay_strava_osm.py` : Fusionne heatmap et graphe OSM pour pondérer les segments.

### 📁 `routing/`
- `pathfinding.py` : Dijkstra / A* pour trouver un chemin dans le graphe.
- `route_generator.py` : Génère un itinéraire (boucle, préférences, distance, etc.).

### 📁 `models/`
- `profile_model.py` : Modèle de profil utilisateur pour personnalisation.
- `model_training.py` : Entraînement du modèle sur des traces/retours.
- `learning_utils.py` : Outils ML (normalisation, split, métriques...).

### 📁 `utils/`
- `geo.py` : Fonctions de géométrie : haversine, bbox, conversions.
- `visual.py` : Visualisation des graphes et routes (`matplotlib`, `folium`...).

---

## 📁 `scripts/` – Scripts exécutables

- `run_download_area.py` : Récupère automatiquement OSM + Strava pour une zone.
- `run_generate_route.py` : Génère un itinéraire complet.
- `train_model.py` : Entraîne un modèle IA de préférence utilisateur.

---

## 📁 `notebooks/` – Exploration rapide

- `exploration.ipynb` : Tests manuels (affichage, données, debug…).
- `model_testing.ipynb` : Analyse des performances du modèle.

---

## 📄 Fichiers de configuration

- `requirements.txt` : Dépendances Python.
- `.gitignore` : Exclusions Git.
- `.gitattributes` : Configuration EOL (fin de ligne) et fichiers binaires.
- `README.md` : Description générale du projet.


## ▶️ Démarrage rapide

```bash
# Installer les dépendances
pip install -r requirements.txt

