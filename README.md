# SmartRoute – AI-Powered MTB Route Generator
SmartRoute est une application web intelligente capable de générer automatiquement des boucles VTT personnalisées à partir d’un simple prompt en langage naturel. Le système combine deux approches complémentaires :

un modèle de Random Forest entraîné sur plus de 1500 traces GPX pour classifier la difficulté des segments (distance, D⁺, surface, popularité Strava),

un LLM (Claude 3.5 – Anthropic) pour comprendre l’intention de l’utilisateur et extraire des paramètres structurés.

À partir d’une demande telle que “Je veux une boucle VTT de 25 km niveau débutant autour de Fontainebleau”, SmartRoute sélectionne automatiquement le graphe adapté, applique des coûts personnalisés par profil, puis génère une boucle asymétrique (aller ≠ retour) grâce à un double Dijkstra. La trace finale est affichée dans une interface web interactive et peut être exportée en GPX.

SmartRoute montre comment IA, données géographiques et algorithmes de graphes peuvent être combinés pour proposer des parcours VTT réalistes, variés et véritablement personnalisés.

## Installation
### Cloner le projet
```bash
git clone https://github.com/TimotheeCrouzet/SmartRoute.git
cd SmartRoute
```
### Créer et activer un environnement virtuel
Depuis la racine du projet :
```bash
python -m venv .venv
```
Puis activer :
- macOS / Linux :
```bash
source .venv/bin/activate
```
- Windows (PowerShell) :
```bash
.venv\Scripts\Activate
```
### Installer les dépendances
```bash
pip install -r requirements.txt
```

### Télécharger les graphes OSM pré-processés (obligatoire)
SmartRoute repose sur deux graphes enrichis (OSM + Strava + coûts IA), pré-calculés hors-ligne.

Ces fichiers sont disponibles dans la section Releases du projet :
- [graphe classic](https://github.com/TimotheeCrouzet/SmartRoute/releases/download/v1.0.0/osm_graph_weighted_all_profiles_classic.gpickle)
- [graphe explore](https://github.com/TimotheeCrouzet/SmartRoute/releases/download/v1.0.0/osm_graph_weighted_all_profiles_explore.gpickle)

### Placer les fichiers dans le bon dossier
Créer l’arborescence suivante si elle n’existe pas déjà :
```bash
mkdir -p data/processed
```
Puis mettez les 2 graphes téléchargés dedans.

Au final:
```bash
SmartRoute/
└── data/
    └── processed/
        ├── osm_graph_weighted_all_profiles_classic.gpickle
        └── osm_graph_weighted_all_profiles_explore.gpickle
```

### Configurer votre clé Anthropic (ou autre API)
Le projet utilise Claude 3.5 pour analyser les prompts.
Éditez le fichier :
```bash
tim.yml
```
et remplacez:
```bash
ANTHROPIC_API_KEY: "VOTRE_CLE_API_ICI"
```
par votre propre clé.

Attention: ne jamais partager publiquement le tim.yml contenant une vraie clé API.

### Lancer l’application
#### Démarrer le backend Flask
```bash
python main.py
```
#### Ouvrir l’application dans votre navigateur
Une fois le serveur lancé, ouvrez simplement :
```bash
http://127.0.0.1:5000
```
#### Exemple d'utilisation
Prompt :
```bash
Je veux un parcours de 60 km autour de Fontainebleau, avec un max de d+
```
Le LLM renvoie un JSON structuré de ce type :
```bash
{
  "zone": "Fontainebleau",
  "distance": 60000,
  "profil": "expert",
  "mode": "explore"
}
```
SmartRoute génère ensuite :
- un point de départ adapté à la zone
- un waypoint à ~30–40 % de la distance cible
- un aller-retour asymétrique via deux Dijkstra
- une trace GPX affichée sur la carte et exportable

## Architecture du projet
```bash
SmartRoute/
│
├── main.py                          # Point d'entrée : démarre le serveur Flask
├── tim.yml                           # Placeholder pour la clé API Anthropic
├── requirements.txt                  # Dépendances Python
├── README.md
├── .gitignore
│
├── data/
│   ├── cache/                        # Cache local (non nécessaire pour l'utilisateur)
│   └── processed/                    # Graphes OSM pré-calculés (à télécharger via Releases)
│       ├── osm_graph_weighted_all_profiles_classic.gpickle
│       └── osm_graph_weighted_all_profiles_explore.gpickle
│
├── scripts/                          # Scripts utilitaires (appel LLM, parsing, génération)
│   ├── __init__.py
│   ├── anthropic_rooter.py           # Appel bas niveau à l'API Claude 3.5
│   ├── extract_vtt_request.py        # Parsing des paramètres de la requête VTT
│   ├── generate_from_prompt.py       # Pipeline : prompt → paramètres → requête structurée
│   └── main_generate_loop.py         # Logique de génération d'itinéraire (Dijkstra & coûts)
│
└── src/
    ├── __init__.py
    ├── app.py                        # Backend Flask : API /generate-route + rendu HTML
    └── webapp/
        ├── __pycache__/
        └── templates/
            └── index.html            # Interface web (Leaflet) servie par Flask
```


## Fonctionnement interne (résumé)

Analyse du prompt
Claude 3.5 (Anthropic) extrait : zone, distance, niveau (débutant/confirmé/expert), mode (classic/explore).

Sélection du graphe
Chargement d’un graphe OSM enrichi (classic ou explore) depuis data/processed.

Coûts par profil
Des modèles Random Forest pré-calculés ont été utilisés pour dériver des coûts par segment et par profil à partir de :
- distance
- dplus
- surface_score
- popularité Strava

Génération de la boucle
- Dijkstra Aller → waypoint (≈ 1/3 de la distance)
- Suppression temporaire des arêtes utilisées
- Dijkstra Retour → départ
- Fusion en une boucle asymétrique

Affichage & export
- Affichage sur la carte Leaflet
- Export de la trace en GPX

## Améliorations possibles

- Génération dynamique des graphes : construire automatiquement un graphe OSM en fonction de la zone demandée dans le prompt, pour sortir du cadre Fontainebleau et couvrir n’importe quelle région.

- Données Strava dynamiques : récupérer les tuiles de popularité à la volée selon la zone choisie.

- Waypoints plus intelligents : choisir automatiquement le meilleur point intermédiaire selon la densité du réseau et le profil utilisateur.

- Modèle de difficulté plus avancé : améliorer ou remplacer le Random Forest pour mieux prédire la difficulté réelle des segments.

- Déploiement serveur : héberger SmartRoute sur une plateforme cloud (Render / Railway / OVH) pour permettre une utilisation en ligne sans installation locale.

## Conclusion

SmartRoute montre comment combiner IA, données géographiques et algorithmes de graphes pour générer automatiquement des parcours VTT personnalisés.
Cette version publique se concentre sur l’essentiel : analyse du prompt, génération d’une boucle asymétrique, et visualisation web.
Une base solide et extensible pour explorer de nouvelles logiques de scoring, d’autres sports, ou un déploiement complet en production.