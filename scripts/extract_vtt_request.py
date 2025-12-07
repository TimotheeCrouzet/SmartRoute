import os
import yaml
import json
from scripts.anthropic_rooter import AnthropicRooter

# Nettoyage console
os.system("clear")

# Charger clé API depuis tim.yml
with open("tim.yml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Initialisation du modèle IA
ia = AnthropicRooter(config["ANTHROPIC_API_KEY"])

# Demande utilisateur
question = input("📝 Quelle est ta demande VTT ?\n> ")

# Appel au modèle
extracted_json = ia.user_prompt_2_json(question)

# Vérification
if not extracted_json:
    print(" Aucune réponse obtenue.")
else:
    print("\n SON extrait :", extracted_json)

    # Sauvegarde dans params.json
    with open("params.json", "w", encoding="utf-8") as f:
        json.dump(extracted_json, f, ensure_ascii=False, indent=2)

    print("💾 Paramètres enregistrés dans params.json")
