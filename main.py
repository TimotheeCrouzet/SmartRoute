# main.py (à la racine)
import os, sys

# ajoute la racine du projet au path pour trouver le package scripts/
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.webapp.app import app  # importe l’app Flask déjà configurée

if __name__ == "__main__":
    app.run(debug=True)
