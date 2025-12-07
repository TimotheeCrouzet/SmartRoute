# pip install anthropic

from anthropic import Anthropic
import os
import json
import time


class AnthropicRooter:

    def __init__(self, anthropic_key):
        os.environ['ANTHROPIC_API_KEY'] = anthropic_key
        self.set_model("Claude-haiku")
        self.set_temp(0.4)

    def set_temp(self, temp):
        self.temp = temp

    def set_model(self, model):
        if model == "Claude-3-5":
            self.model = "claude-3-5-sonnet-20241022"
        elif model == "Claude-3-7":
            self.model = "claude-3-7-sonnet-20250219"
        elif model == "Claude-haiku":
            self.model = "claude-3-5-haiku-20241022"
        elif model == "Claude-4":
            self.model = "claude-opus-4-20250514"
        else:
            exit("No model selected")

        self.max_tokens = 8192
        self.max_size = 7000

    def save_json(self, state_file, state):
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)

    def anthropic_call(self, system, question, context=None, files=None):
        messages = []

        if context:
            messages.append({
                "role": "assistant",
                "content": f"Contexte de référence :\n\n{context}"
            })

        user_content_parts = []

        if files:
            user_content_parts.append("=== FICHIERS À ANALYSER ===")
            for file_info in files:
                if 'content' in file_info:
                    file_content = file_info['content']
                else:
                    file_content = self.get_prompt(file_info['path'])
                user_content_parts.append(f"--- {file_info['path']} ---\n{file_content}\n")
            user_content_parts.append("=== FIN DES FICHIERS ===\n")

        user_content_parts.append(question)
        messages.append({
            "role": "user",
            "content": "\n".join(user_content_parts)
        })

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                client = Anthropic()
                print(f"iaCall {self.model} (tentative {attempt + 1})")

                stream = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temp,
                    system=system,
                    messages=messages,
                    stream=True
                )

                response_text = ""
                for chunk in stream:
                    if chunk.type == "content_block_delta":
                        response_text += chunk.delta.text

                return response_text

            except Exception as e:
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ["overloaded", "rate limit", "too many requests"]):
                    if attempt < max_retries - 1:
                        print(f"API surchargée, nouvelle tentative dans {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue

                print(f"Erreur Claude API (tentative {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    print("Échec après toutes les tentatives")
                    return None

                time.sleep(1)

        return None

    def safe_parse_json(self, text):
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except Exception as e:
            print(" Erreur parsing JSON brut :", e)
            print(" Texte reçu :", text)
            return None

    def user_prompt_2_json(self, user_prompt):
        system = """"
        Tu es un assistant spécialisé dans l'analyse de demande de parcours VTT. 
        Ton rôle est d'extraire les paramètres clés d'une demande utilisateur et de les retourner au format JSON strict suivant:

        {
          "zone": "nom_de_la_zone",
          "distance": distance_en_metres,
          "profil": "débutant|confirmé|expert", 
          "mode": "explore|classic"
        }

        RÈGLES D'EXTRACTION :

        1. ZONE :
        - Extraire le nom de la ville/région/lieu mentionné
        - Si plusieurs lieux : prendre le principal ou le point de départ
        - Si aucun lieu précis : retourner null

        2. DISTANCE :
        - Convertir TOUJOURS en mètres
        - Exemples : "30 km" → 30000, "15 kilomètres" → 15000, "2h de vélo" → estimer selon profil
        - Si non mentionnée : retourner null

        3. PROFIL :
        - "débutant" : mots-clés comme "débutant", "facile", "tranquille", "famille", "première fois"
        - "confirmé" : mots-clés comme "intermédiaire", "moyen", "habituel", "régulier" 
        - "expert" : mots-clés comme "expert", "difficile", "technique", "sportif", "challenge", "dur"
        - Si non mentionné : analyser le contexte ou retourner "confirmé" par défaut

        4. MODE :
        - "explore" : mots-clés comme "explorer", "découvrir", "sortir des sentiers battus", "aventure", "nouveau", "caché", "secret", "inédit"
        - "classic" : mots-clés comme "classique", "connu", "sûr", "habituel", "traditionnel", "sans risque", "balisé"
        - Si non mentionné : retourner "classic" par défaut

        EXEMPLES :

        Requête : "Je veux un parcours VTT débutant de 30 km autour de Fontainebleau"
        Réponse : {"zone": "Fontainebleau", "distance": 30000, "profil": "débutant", "mode": "classic"}

        Requête : "Trouve-moi une sortie technique de 2h vers Chamonix, j'aimerais découvrir de nouveaux spots"
        Réponse : {"zone": "Chamonix", "distance": 40000, "profil": "expert", "mode": "explore"}

        Requête : "Balade familiale facile de 15 km près de Lyon"
        Réponse : {"zone": "Lyon", "distance": 15000, "profil": "débutant", "mode": "classic"}

        IMPORTANT : 
        - Retourne UNIQUEMENT le JSON, aucun autre texte
        - Si une information est ambiguë, privilégie la sécurité (profil moins élevé, mode classic)
        - Pour estimer une distance à partir d'une durée : débutant=10km/h, confirmé=15km/h, expert=20km/h
        """
        raw = self.anthropic_call(system, user_prompt)
        return self.safe_parse_json(raw)
