"""TruthGraph v0 htmx Frontend - Flask Application."""

import os

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
app.config["API_URL"] = API_URL


@app.route("/")
def index():
    """Main page with claim submission form and history."""
    return render_template("index.html")


@app.route("/claims", methods=["GET"])
def get_claims():
    """Get paginated list of claims (htmx endpoint)."""
    skip = int(request.args.get("skip", 0))
    limit = int(request.args.get("limit", 20))

    try:
        response = requests.get(
            f"{API_URL}/api/v1/claims", params={"skip": skip, "limit": limit}, timeout=5
        )
        response.raise_for_status()
        data = response.json()

        return render_template(
            "claim_list.html", claims=data["items"], total=data["total"], skip=skip, limit=limit
        )
    except Exception as e:
        return render_template("error.html", error=str(e)), 500


@app.route("/claims/submit", methods=["POST"])
def submit_claim():
    """Submit a new claim (htmx endpoint)."""
    text = request.form.get("text", "").strip()
    source_url = request.form.get("source_url", "").strip() or None

    if not text:
        return render_template("error.html", error="Claim text is required"), 400

    try:
        response = requests.post(
            f"{API_URL}/api/v1/claims", json={"text": text, "source_url": source_url}, timeout=10
        )
        response.raise_for_status()
        claim = response.json()

        return render_template("claim_submitted.html", claim=claim)
    except Exception as e:
        return render_template("error.html", error=str(e)), 500


@app.route("/health")
def health():
    """Health check endpoint."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        api_status = "ok" if response.status_code == 200 else "error"
    except Exception:
        api_status = "unreachable"

    return jsonify({"status": "ok", "api_status": api_status})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG", "0") == "1")
