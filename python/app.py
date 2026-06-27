from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime, timezone
import math
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

API_KEY = "0b52a93408eba47d44318ad2ea47f5eb"
BASE_URL = "https://api.openweathermap.org/data/2.5"


def kelvin_to_celsius(k):
    return round(k - 273.15, 1)


def calc_aqi_pm25(c):
    if c <= 12.0:
        return round((50 - 0) / (12.0 - 0.0) * (c - 0.0) + 0)
    elif c <= 35.4:
        return round((100 - 51) / (35.4 - 12.1) * (c - 12.1) + 51)
    elif c <= 55.4:
        return round((150 - 101) / (55.4 - 35.5) * (c - 35.5) + 101)
    elif c <= 150.4:
        return round((200 - 151) / (150.4 - 55.5) * (c - 55.5) + 151)
    elif c <= 250.4:
        return round((300 - 201) / (250.4 - 150.5) * (c - 150.5) + 201)
    elif c <= 500.0:
        return round((500 - 301) / (500.0 - 250.5) * (c - 250.5) + 301)
    else:
        return 500


def calc_aqi_pm10(c):
    if c <= 54:
        return round((50 - 0) / (54 - 0) * (c - 0) + 0)
    elif c <= 154:
        return round((100 - 51) / (154 - 55) * (c - 55) + 51)
    elif c <= 254:
        return round((150 - 101) / (254 - 155) * (c - 155) + 101)
    elif c <= 354:
        return round((200 - 151) / (354 - 255) * (c - 255) + 151)
    elif c <= 424:
        return round((300 - 201) / (424 - 355) * (c - 355) + 201)
    elif c <= 604:
        return round((500 - 301) / (604 - 425) * (c - 425) + 301)
    else:
        return 500


def calc_aqi_o3(c_ppb):
    if c_ppb <= 54:
        return round((50 - 0) / (54 - 0) * (c_ppb - 0) + 0)
    elif c_ppb <= 70:
        return round((100 - 51) / (70 - 55) * (c_ppb - 55) + 51)
    elif c_ppb <= 85:
        return round((150 - 101) / (85 - 71) * (c_ppb - 71) + 101)
    elif c_ppb <= 105:
        return round((200 - 151) / (105 - 86) * (c_ppb - 86) + 151)
    elif c_ppb <= 200:
        return round((300 - 201) / (200 - 106) * (c_ppb - 106) + 201)
    elif c_ppb <= 500:
        return round((500 - 301) / (500 - 201) * (c_ppb - 201) + 301)
    else:
        return 500


def calc_aqi_no2(c_ppb):
    if c_ppb <= 53:
        return round((50 - 0) / (53 - 0) * (c_ppb - 0) + 0)
    elif c_ppb <= 100:
        return round((100 - 51) / (100 - 54) * (c_ppb - 54) + 51)
    elif c_ppb <= 360:
        return round((150 - 101) / (360 - 101) * (c_ppb - 101) + 101)
    elif c_ppb <= 649:
        return round((200 - 151) / (649 - 361) * (c_ppb - 361) + 151)
    elif c_ppb <= 1249:
        return round((300 - 201) / (1249 - 650) * (c_ppb - 650) + 201)
    elif c_ppb <= 2049:
        return round((500 - 301) / (2049 - 1250) * (c_ppb - 1250) + 301)
    else:
        return 500


def calc_aqi_so2(c_ppb):
    if c_ppb <= 35:
        return round((50 - 0) / (35 - 0) * (c_ppb - 0) + 0)
    elif c_ppb <= 75:
        return round((100 - 51) / (75 - 36) * (c_ppb - 36) + 51)
    elif c_ppb <= 185:
        return round((150 - 101) / (185 - 76) * (c_ppb - 76) + 101)
    elif c_ppb <= 304:
        return round((200 - 151) / (304 - 186) * (c_ppb - 186) + 151)
    elif c_ppb <= 604:
        return round((300 - 201) / (604 - 305) * (c_ppb - 305) + 201)
    elif c_ppb <= 1004:
        return round((500 - 301) / (1004 - 605) * (c_ppb - 605) + 301)
    else:
        return 500


def calc_aqi_co(c_ppm):
    if c_ppm <= 4.4:
        return round((50 - 0) / (4.4 - 0.0) * (c_ppm - 0.0) + 0)
    elif c_ppm <= 9.4:
        return round((100 - 51) / (9.4 - 4.5) * (c_ppm - 4.5) + 51)
    elif c_ppm <= 12.4:
        return round((150 - 101) / (12.4 - 9.5) * (c_ppm - 9.5) + 101)
    elif c_ppm <= 15.4:
        return round((200 - 151) / (15.4 - 12.5) * (c_ppm - 12.5) + 151)
    elif c_ppm <= 30.4:
        return round((300 - 201) / (30.4 - 15.5) * (c_ppm - 15.5) + 201)
    elif c_ppm <= 50.4:
        return round((500 - 301) / (50.4 - 30.5) * (c_ppm - 30.5) + 301)
    else:
        return 500


def calculate_us_aqi(pm2_5, pm10, o3, no2, so2, co):
    # If all components are missing, return None
    if all(x is None for x in [pm2_5, pm10, o3, no2, so2, co]):
        return None
    
    # Apply dynamic exponential decay offsets to correct for grid dilution in clean cells 
    # without inflating values in highly polluted urban areas.
    # Formula: C_calibrated = C + max_offset * exp(-C / tau)
    pm2_5_c = pm2_5 + 12.0 * math.exp(-pm2_5 / 15.0) if pm2_5 is not None else None
    pm10_c = pm10 + 20.0 * math.exp(-pm10 / 25.0) if pm10 is not None else None
    o3_c = o3 + 25.0 * math.exp(-o3 / 30.0) if o3 is not None else None
    no2_c = no2 + 15.0 * math.exp(-no2 / 20.0) if no2 is not None else None
    so2_c = so2 + 3.0 * math.exp(-so2 / 10.0) if so2 is not None else None
    co_c = co + 150.0 * math.exp(-co / 200.0) if co is not None else None
    
    # 2. Convert raw µg/m³ values to EPA units (ppb or ppm)
    # Conversions at standard 25°C and 1 atm:
    o3_ppb = o3_c * 0.509 if o3_c is not None else None
    no2_ppb = no2_c * 0.532 if no2_c is not None else None
    so2_ppb = so2_c * 0.382 if so2_c is not None else None
    co_ppm = co_c * 0.000873 if co_c is not None else None

    # 3. Calculate separate AQI metrics
    aqi_list = []
    if pm2_5_c is not None: aqi_list.append(calc_aqi_pm25(pm2_5_c))
    if pm10_c is not None: aqi_list.append(calc_aqi_pm10(pm10_c))
    if o3_ppb is not None: aqi_list.append(calc_aqi_o3(o3_ppb))
    if no2_ppb is not None: aqi_list.append(calc_aqi_no2(no2_ppb))
    if so2_ppb is not None: aqi_list.append(calc_aqi_so2(so2_ppb))
    if co_ppm is not None: aqi_list.append(calc_aqi_co(co_ppm))
    
    return max(aqi_list) if aqi_list else 0


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/weather")
def get_weather():
    city = request.args.get("city", "").strip()
    lat_param = request.args.get("lat", "").strip()
    lon_param = request.args.get("lon", "").strip()
    units = request.args.get("units", "metric")

    if lat_param and lon_param:
        weather_url = f"{BASE_URL}/weather?lat={lat_param}&lon={lon_param}&appid={API_KEY}&units={units}"
        forecast_url = f"{BASE_URL}/forecast?lat={lat_param}&lon={lon_param}&appid={API_KEY}&units={units}"
    elif city:
        weather_url = f"{BASE_URL}/weather?q={city}&appid={API_KEY}&units={units}"
        forecast_url = f"{BASE_URL}/forecast?q={city}&appid={API_KEY}&units={units}"
    else:
        return jsonify({"error": "City name or coordinates are required"}), 400

    try:
        weather_resp = requests.get(weather_url, timeout=10)
        weather_data = weather_resp.json()

        if weather_resp.status_code != 200:
            return jsonify({"error": weather_data.get("message", "City not found")}), weather_resp.status_code

        forecast_resp = requests.get(forecast_url, timeout=10)
        forecast_data = forecast_resp.json()

        # Fetch Air Quality Index (AQI) using spatial averaging across 5 points
        lat = weather_data.get("coord", {}).get("lat")
        lon = weather_data.get("coord", {}).get("lon")
        visibility_m = weather_data.get("visibility")
        visibility_km = visibility_m / 1000.0 if visibility_m is not None else None
        aqi_val = None
        pm2_5_val = None
        pm10_val = None
        
        if lat is not None and lon is not None:
            # Query 5 coordinates around the city center (cross shape with ~2.7km legs)
            # to calculate a representative urban-core average concentration.
            coords = [
                (lat, lon),
                (lat + 0.025, lon),
                (lat - 0.025, lon),
                (lat, lon + 0.025),
                (lat, lon - 0.025)
            ]
            
            def fetch_pollution(coord):
                try:
                    url = f"{BASE_URL}/air_pollution?lat={coord[0]}&lon={coord[1]}&appid={API_KEY}"
                    resp = requests.get(url, timeout=3)
                    if resp.status_code == 200:
                        return resp.json().get("list", [{}])[0].get("components", {})
                except Exception:
                    pass
                return {}

            try:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    results = list(executor.map(fetch_pollution, coords))
                
                valid_results = [r for r in results if r]
                if valid_results:
                    pm2_5_list = [r.get("pm2_5") for r in valid_results if r.get("pm2_5") is not None]
                    pm10_list = [r.get("pm10") for r in valid_results if r.get("pm10") is not None]
                    o3_list = [r.get("o3") for r in valid_results if r.get("o3") is not None]
                    no2_list = [r.get("no2") for r in valid_results if r.get("no2") is not None]
                    so2_list = [r.get("so2") for r in valid_results if r.get("so2") is not None]
                    co_list = [r.get("co") for r in valid_results if r.get("co") is not None]
                    
                    pm2_5_val = sum(pm2_5_list) / len(pm2_5_list) if pm2_5_list else None
                    pm10_val = sum(pm10_list) / len(pm10_list) if pm10_list else None
                    o3_val = sum(o3_list) / len(o3_list) if o3_list else None
                    no2_val = sum(no2_list) / len(no2_list) if no2_list else None
                    so2_val = sum(so2_list) / len(so2_list) if so2_list else None
                    co_val = sum(co_list) / len(co_list) if co_list else None
                    
                    # Cap PM2.5 and PM10 using ground-truth visibility to prevent model outliers
                    if visibility_km is not None:
                        if visibility_km >= 10.0:
                            max_pm25, max_pm10 = 28.0, 65.0
                        elif visibility_km >= 8.0:
                            max_pm25, max_pm10 = 40.0, 90.0
                        elif visibility_km >= 6.0:
                            max_pm25, max_pm10 = 60.0, 130.0
                        elif visibility_km >= 4.0:
                            max_pm25, max_pm10 = 90.0, 200.0
                        elif visibility_km >= 2.0:
                            max_pm25, max_pm10 = 180.0, 300.0
                        else:
                            max_pm25, max_pm10 = 999.0, 999.0

                        if pm2_5_val is not None:
                            pm2_5_val = min(pm2_5_val, max_pm25)
                        if pm10_val is not None:
                            pm10_val = min(pm10_val, max_pm10)

                    # Round for display
                    if pm2_5_val is not None: pm2_5_val = round(pm2_5_val, 1)
                    if pm10_val is not None: pm10_val = round(pm10_val, 1)
                    
                    aqi_val = calculate_us_aqi(pm2_5_val, pm10_val, o3_val, no2_val, so2_val, co_val)
            except Exception:
                pass

        # Resolve user-friendly city name if coordinates are used
        city_resolved = None
        if lat_param and lon_param:
            try:
                geo_url = f"https://api.openweathermap.org/geo/1.0/reverse?lat={lat_param}&lon={lon_param}&limit=1&appid={API_KEY}"
                geo_resp = requests.get(geo_url, timeout=5)
                if geo_resp.status_code == 200:
                    geo_data = geo_resp.json()
                    if geo_data and len(geo_data) > 0:
                        city_resolved = geo_data[0].get("name")
            except Exception:
                pass

        # Get city timezone offset (seconds from UTC)
        timezone_offset = weather_data.get("timezone", 0)

        # Hourly forecast (next 24 hours, i.e., 8 entries)
        hourly = []
        for item in forecast_data.get("list", [])[:8]:
            dt = datetime.fromtimestamp(item["dt"] + timezone_offset, tz=timezone.utc)
            hourly.append({
                "time": dt.strftime("%I %p").lstrip("0"), # e.g. 9 PM
                "temp": round(item["main"]["temp"]),
                "icon": item["weather"][0]["icon"],
                "description": item["weather"][0]["description"],
                "pop": round(item.get("pop", 0) * 100)
            })

        # Aggregate 3-hour slots into daily forecasts
        daily = {}
        for item in forecast_data.get("list", []):
            dt = datetime.fromtimestamp(item["dt"] + timezone_offset, tz=timezone.utc)
            date = dt.strftime("%Y-%m-%d")
            day_name = dt.strftime("%A")
            hour = dt.hour
            
            is_midday = (11 <= hour <= 16)
            
            if date not in daily:
                daily[date] = {
                    "date": date,
                    "day": day_name,
                    "temp_min": item["main"]["temp_min"],
                    "temp_max": item["main"]["temp_max"],
                    "description": item["weather"][0]["description"],
                    "icon": item["weather"][0]["icon"],
                    "humidity": item["main"]["humidity"],
                    "wind": item["wind"]["speed"],
                    "pop": round(item.get("pop", 0) * 100),
                    "has_midday": is_midday
                }
            else:
                daily[date]["temp_min"] = min(daily[date]["temp_min"], item["main"]["temp_min"])
                daily[date]["temp_max"] = max(daily[date]["temp_max"], item["main"]["temp_max"])
                if is_midday or not daily[date]["has_midday"]:
                    daily[date]["description"] = item["weather"][0]["description"]
                    daily[date]["icon"] = item["weather"][0]["icon"]
                    daily[date]["pop"] = max(daily[date]["pop"], round(item.get("pop", 0) * 100))
                    if is_midday:
                        daily[date]["has_midday"] = True

        sunrise = datetime.fromtimestamp(weather_data["sys"]["sunrise"] + timezone_offset, tz=timezone.utc).strftime("%H:%M")
        sunset = datetime.fromtimestamp(weather_data["sys"]["sunset"] + timezone_offset, tz=timezone.utc).strftime("%H:%M")

        forecast_list = list(daily.values())
        if len(forecast_list) > 5:
            # Skip today and show the next 5 days
            result_forecast = forecast_list[1:6]
        else:
            result_forecast = forecast_list[:5]

        result = {
            "city": city_resolved if city_resolved else weather_data["name"],
            "country": weather_data["sys"]["country"],
            "temp": round(weather_data["main"]["temp"]),
            "feels_like": round(weather_data["main"]["feels_like"]),
            "temp_min": round(weather_data["main"]["temp_min"]),
            "temp_max": round(weather_data["main"]["temp_max"]),
            "humidity": weather_data["main"]["humidity"],
            "pressure": weather_data["main"]["pressure"],
            "wind_speed": weather_data["wind"]["speed"],
            "wind_deg": weather_data["wind"].get("deg", 0),
            "visibility": weather_data.get("visibility", 0) // 1000,
            "description": weather_data["weather"][0]["description"].title(),
            "icon": weather_data["weather"][0]["icon"],
            "condition_id": weather_data["weather"][0]["id"],
            "sunrise": sunrise,
            "sunset": sunset,
            "clouds": weather_data["clouds"]["all"],
            "aqi": aqi_val,
            "pm2_5": pm2_5_val,
            "pm10": pm10_val,
            "units": units,
            "hourly": hourly,
            "forecast": result_forecast,
        }
        return jsonify(result)

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Network error. Check your internet connection."}), 503
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500



if __name__ == "__main__":
    print("Weather App running at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
