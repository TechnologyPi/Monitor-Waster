from flask import Flask, request, jsonify, send_from_directory
import requests
from functools import lru_cache
from datetime import datetime, timedelta

app = Flask(__name__)

@lru_cache(maxsize=256)
def geocode_city(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    results = data.get("results")
    if not results: return None
    top = results[0]
    return {
        "name": f"{top.get('name')}{', ' + top.get('country_code','') if top.get('country_code') else ''}",
        "lat": top["latitude"],
        "lon": top["longitude"]
    }

def fetch_openmeteo_current(lat: float, lon: float):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,precipitation",
        "hourly": "precipitation,snowfall",
        "timezone": "auto"
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
WMO_TO_MAIN = {
    0: "Clear",
    1: "Clear", 2: "Clouds", 3: "Clouds",
    45: "Clouds", 48: "Clouds",
    51: "Rain", 53: "Rain", 55: "Rain",
    56: "Rain", 57: "Rain",
    61: "Rain", 63: "Rain", 65: "Rain",
    66: "Rain", 67: "Rain",
    71: "Snow", 73: "Snow", 75: "Snow",
    77: "Snow",
    80: "Rain", 81: "Rain", 82: "Rain",
    85: "Snow", 86: "Snow",
    95: "Rain", 96: "Rain", 99: "Rain"
}
MAIN_TO_ID = {"Clear": 800, "Clouds": 802, "Rain": 500, "Snow": 600}

def normalize_response(name: str, payload: dict):
    cur = payload.get("current", {})
    temp = cur.get("temperature_2m")
    wcode = cur.get("weather_code", 0)
    main = WMO_TO_MAIN.get(wcode, "Clouds")
    desc = main.lower()
    return {
        "name": name,
        "main": {"temp": temp},
        "weather": [{
            "description": desc,
            "main": main,
            "id": MAIN_TO_ID.get(main, 802)
        }]
    }

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/weather")
def weather_by_city():
    city = (request.args.get("city") or "").strip()

    loc = geocode_city(city)

    data = fetch_openmeteo_current(loc["lat"], loc["lon"])
    name = loc["name"]
    return jsonify(normalize_response(name, data))

if __name__ == "__main__":
    app.run(debug=True)
