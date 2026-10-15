import re

import requests
from flask import Flask, render_template, request

app = Flask(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ZIP_URL = "https://api.zippopotam.us/us/{zip_code}"
SAN_JOSE = {"latitude": 37.3382, "longitude": -121.8863}

# WMO weather interpretation codes used by Open-Meteo.
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class ZipNotFound(Exception):
    pass


def fetch_weather(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code",
        "temperature_unit": "fahrenheit",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    current = response.json()["current"]
    return {
        "temperature": round(current["temperature_2m"]),
        "description": WEATHER_CODES.get(current["weather_code"], "Unknown"),
    }


def lookup_zip(zip_code):
    response = requests.get(ZIP_URL.format(zip_code=zip_code), timeout=10)
    if response.status_code == 404:
        raise ZipNotFound(zip_code)
    response.raise_for_status()
    place = response.json()["places"][0]
    return {
        "name": f"{place['place name']}, {place['state']}",
        "latitude": float(place["latitude"]),
        "longitude": float(place["longitude"]),
    }


@app.route("/")
def index():
    try:
        weather = fetch_weather(**SAN_JOSE)
        error = None
    except (requests.RequestException, KeyError, ValueError):
        weather = None
        error = "Couldn't load the weather right now. Please try again later."
    return render_template("index.html", weather=weather, error=error)


@app.route("/zip", methods=["GET", "POST"])
def zip_lookup():
    zip_code = request.form.get("zip", "").strip()
    place = weather = error = None
    if request.method == "POST":
        if not re.fullmatch(r"\d{5}", zip_code):
            error = "Please enter a 5-digit US zip code."
        else:
            try:
                place = lookup_zip(zip_code)
                weather = fetch_weather(place["latitude"], place["longitude"])
            except ZipNotFound:
                place = None
                error = f"The zip code {zip_code} doesn't exist."
            except (requests.RequestException, KeyError, IndexError, ValueError):
                place = None
                error = "Couldn't load the weather right now. Please try again later."
    return render_template(
        "zip.html", zip_code=zip_code, place=place, weather=weather, error=error
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
