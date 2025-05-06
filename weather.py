from flask import Flask, request, jsonify
import requests
from flask_cors import CORS  
import logging

app = Flask(__name__)
CORS(app)  

# Logging setup
logging.basicConfig(level=logging.DEBUG)

GEO_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

@app.route('/weather', methods=['GET'])
def get_weather():
    city = request.args.get('city', 'London')  
    logging.info(f"Fetching weather data for: {city}")

    # Step 1: Get latitude & longitude of the city
    try:
        geo_response = requests.get(f"{GEO_API_URL}?name={city}&count=1&format=json").json()
        if "results" not in geo_response or not geo_response["results"]:
            logging.warning(f"City '{city}' not found in geocoding API.")
            return jsonify({"error": f"City '{city}' not found"}), 404

        lat = geo_response["results"][0]["latitude"]
        lon = geo_response["results"][0]["longitude"]
    except Exception as e:
        logging.error(f"Geocoding API error: {e}")
        return jsonify({"error": "Failed to fetch city coordinates"}), 500

    # Step 2: Fetch weather data
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "uv_index_max", "sunrise", "sunset"],
        "hourly": ["relative_humidity_2m"],  # ❌ Removed "pm10" (Air Quality)
        "timezone": "auto"
    }

    try:
        weather_response = requests.get(WEATHER_API_URL, params=params).json()
        print(weather_response)
        if "current_weather" not in weather_response or "daily" not in weather_response:
            logging.error("Invalid weather data received from API.")
            return jsonify({"error": "Failed to fetch weather data"}), 500
    except Exception as e:
        logging.error(f"Weather API error: {e}")
        return jsonify({"error": "Weather API request failed"}), 500

    # Extract required data safely
    current_weather = weather_response["current_weather"]
    daily_forecast = weather_response["daily"]
    hourly_data = weather_response.get("hourly", {})

    # Handle missing hourly data
    humidity = hourly_data.get("relative_humidity_2m", [None])[0]  # Get first value or None

    result = {
        "city": city,
        "current": {
            "temperature": current_weather.get("temperature", "N/A"),
            "windspeed": current_weather.get("windspeed", "N/A"),
            "weathercode": current_weather.get("weathercode", "N/A"),
            "time": current_weather.get("time", "N/A"),
            "humidity": humidity if humidity is not None else "Data not available",
            "pressure": current_weather.get("pressure", "N/A"),
        },
        "forecast": []
    }

    # Construct the forecast list
    for i in range(len(daily_forecast["time"])):
        result["forecast"].append({
            "date": daily_forecast["time"][i],
            "max_temp": daily_forecast["temperature_2m_max"][i],
            "min_temp": daily_forecast["temperature_2m_min"][i],
            "precipitation": daily_forecast["precipitation_sum"][i],
            "uv_index": daily_forecast["uv_index_max"][i],
            "sunrise": daily_forecast["sunrise"][i],
            "sunset": daily_forecast["sunset"][i]
        })

    logging.info(f"Weather data successfully fetched for {city}")
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5002, debug=True)
