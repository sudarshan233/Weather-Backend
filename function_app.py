import azure.functions as func
import logging
import requests
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

GEO_API_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

@app.route(route="fetchWeather")
def fetchWeather(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing /fetchWeather request.')

    city = req.params.get('city')
    if not city:
        try:
            req_body = req.get_json()
            city = req_body.get('city')
        except:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'city' parameter"}),
                status_code=400,
                mimetype="application/json"
            )
    try:
        geo_response = requests.get(f"{GEO_API_URL}?name={city}&count=1&format=json").json()
        if "results" not in geo_response or not geo_response["results"]:
            return func.HttpResponse(
                json.dumps({"error": f"City '{city}' not found"}),
                status_code=404,
                mimetype="application/json"
            )

        lat = geo_response["results"][0]["latitude"]
        lon = geo_response["results"][0]["longitude"]
    except Exception as e:
        logging.error(f"Geocoding error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to get coordinates"}),
            status_code=500,
            mimetype="application/json"
        )

    # Step 2: Fetch weather data
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "uv_index_max", "sunrise", "sunset"],
        "hourly": ["relative_humidity_2m"],
        "timezone": "auto"
    }

    try:
        weather_response = requests.get(WEATHER_API_URL, params=params).json()
        if "current_weather" not in weather_response or "daily" not in weather_response:
            return func.HttpResponse(
                json.dumps({"error": "Incomplete weather data"}),
                status_code=500,
                mimetype="application/json"
            )
    except Exception as e:
        logging.error(f"Weather API error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to fetch weather"}),
            status_code=500,
            mimetype="application/json"
        )

    current = weather_response["current_weather"]
    daily = weather_response["daily"]
    hourly = weather_response.get("hourly", {})
    humidity = hourly.get("relative_humidity_2m", [None])[0]

    result = {
        "city": city,
        "current": {
            "temperature": current.get("temperature", "N/A"),
            "windspeed": current.get("windspeed", "N/A"),
            "weathercode": current.get("weathercode", "N/A"),
            "time": current.get("time", "N/A"),
            "humidity": humidity if humidity is not None else "N/A",
            "pressure": current.get("pressure", "N/A")
        },
        "forecast": []
    }

    for i in range(len(daily["time"])):
        result["forecast"].append({
            "date": daily["time"][i],
            "max_temp": daily["temperature_2m_max"][i],
            "min_temp": daily["temperature_2m_min"][i],
            "precipitation": daily["precipitation_sum"][i],
            "uv_index": daily["uv_index_max"][i],
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i]
        })

    return func.HttpResponse(
        json.dumps(result),
        mimetype="application/json"
    )