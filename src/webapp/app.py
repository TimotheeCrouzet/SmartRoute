""""cd /Users/timcrouzet/Documents/SmartRoute
PYTHONPATH=. .venv/bin/python src/webapp/app.py
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
from scripts.generate_from_prompt import generate_from_prompt

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate-route", methods=["POST"])
def generate_route():
    data = request.get_json()
    prompt = data["prompt"]
    print(f" Reçu : {prompt}")

    try:
        result = generate_from_prompt(prompt)
        return jsonify(result)
    except Exception as e:
        print(f" Erreur génération : {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/outputs/<filename>")
def serve_outputs_gpx(filename):
    full_path = os.path.join(os.getcwd(), "outputs", filename)
    return send_file(full_path, mimetype="application/gpx+xml")

if __name__ == "__main__":
    app.run(debug=True)
