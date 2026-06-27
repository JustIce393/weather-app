import tkinter as tk
from tkinter import ttk, messagebox
import requests
import math
import io
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
# PIL/Pillow removed to support pure Python 3.14 standard library rendering

API_KEY = "0b52a93408eba47d44318ad2ea47f5eb"
BASE_URL = "https://api.openweathermap.org/data/2.5"

class SkyCastApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SkyCast — Weather Forecaster")
        self.root.geometry("1080x820")
        self.root.configure(bg="#0f172a") # Dark Slate background
        
        # State variables
        self.units = "metric" # metric (C) or imperial (F)
        self.last_city = "Mumbai"
        self.recent_searches = ["Mumbai", "Shanghai", "Delhi", "London", "Tokyo"]
        self.icon_cache = {}
        
        # Configure custom fonts (Windows fallbacks work automatically)
        self.font_title = ("Segoe UI", 22, "bold")
        self.font_subtitle = ("Segoe UI", 9, "italic")
        self.font_temp = ("Segoe UI", 56, "bold")
        self.font_city = ("Segoe UI", 24, "bold")
        self.font_card_header = ("Segoe UI", 11, "bold")
        self.font_card_body = ("Segoe UI", 10)
        self.font_card_desc = ("Segoe UI", 9)
        self.font_badge = ("Segoe UI", 10, "bold")
        
        self.setup_styles()
        self.build_ui()
        
        # Load initial city in a background thread to prevent UI freezing
        self.search_city(self.last_city)

    def setup_styles(self):
        # Configure ttk styles for some default components
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Label styles
        self.style.configure("TLabel", background="#0f172a", foreground="#f8fafc")
        self.style.configure("Card.TFrame", background="#1e293b", borderwidth=1, relief="solid")

    def build_ui(self):
        # Master container
        self.main_container = tk.Frame(self.root, bg="#0f172a", padx=25, pady=15)
        self.main_container.pack(fill="both", expand=True)

        # ── ROW 0: Header & Unit Switch ──
        self.header_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.header_frame.pack(fill="x", pady=(0, 10))
        
        self.title_lbl = tk.Label(self.header_frame, text="⛅ SkyCast", font=self.font_title, bg="#0f172a", fg="#38bdf8")
        self.title_lbl.pack(side="left")
        
        self.tagline_lbl = tk.Label(self.header_frame, text="  Premium real-time meteorological forecast", font=self.font_subtitle, bg="#0f172a", fg="#94a3b8")
        self.tagline_lbl.pack(side="left", anchor="s", pady=(0, 4))
        
        # Unit Switch Button
        self.unit_btn = tk.Button(self.header_frame, text="Toggle Unit (°C/°F)", font=("Segoe UI", 10, "bold"),
                                  bg="#1e293b", fg="#38bdf8", activebackground="#334155", activeforeground="#38bdf8",
                                  bd=0, relief="flat", padx=12, pady=6, cursor="hand2", command=self.toggle_units)
        self.unit_btn.pack(side="right")

        # ── ROW 1: Search Bar & Geolocation ──
        self.search_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.search_frame.pack(fill="x", pady=10)
        
        # Custom rounded-like entry frame
        self.entry_frame = tk.Frame(self.search_frame, bg="#1e293b", bd=1, relief="solid")
        self.entry_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.search_entry = tk.Entry(self.entry_frame, font=("Segoe UI", 12), bg="#1e293b", fg="#f8fafc",
                                     insertbackground="#f8fafc", bd=0, highlightthickness=0)
        self.search_entry.pack(fill="x", padx=12, pady=8)
        self.search_entry.insert(0, "Mumbai")
        self.search_entry.bind("<Return>", lambda e: self.trigger_search())

        self.search_btn = tk.Button(self.search_frame, text="Search", font=("Segoe UI", 11, "bold"),
                                    bg="#38bdf8", fg="#0f172a", activebackground="#7dd3fc", activeforeground="#0f172a",
                                    bd=0, relief="flat", padx=20, pady=8, cursor="hand2", command=self.trigger_search)
        self.search_btn.pack(side="left", padx=(0, 10))

        self.loc_btn = tk.Button(self.search_frame, text="📍 Locate Me", font=("Segoe UI", 11, "bold"),
                                 bg="#1e293b", fg="#f8fafc", activebackground="#334155", activeforeground="#f8fafc",
                                 bd=0, relief="flat", padx=15, pady=8, cursor="hand2", command=self.locate_me)
        self.loc_btn.pack(side="left")

        # ── ROW 2: Recent Searches Chips ──
        self.recent_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.recent_frame.pack(fill="x", pady=(5, 15))
        
        self.recent_lbl = tk.Label(self.recent_frame, text="Recent: ", font=("Segoe UI", 9, "bold"), bg="#0f172a", fg="#94a3b8")
        self.recent_lbl.pack(side="left")
        
        self.chips_container = tk.Frame(self.recent_frame, bg="#0f172a")
        self.chips_container.pack(side="left")
        self.render_recent_chips()

        # ── LOADING INDICATOR ──
        self.loading_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.loading_lbl = tk.Label(self.loading_frame, text="Gathering local conditions...", font=("Segoe UI", 12, "italic"), bg="#0f172a", fg="#38bdf8")
        self.loading_lbl.pack()

        # ── MAIN DASHBOARD FRAME ──
        self.dashboard_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.dashboard_frame.pack(fill="both", expand=True)

        # Split Dashboard into Upper (Current Weather & AQI) and Lower (Forecasts)
        self.upper_frame = tk.Frame(self.dashboard_frame, bg="#0f172a")
        self.upper_frame.pack(fill="x", pady=(0, 15))

        # Current Weather Card (Left)
        self.weather_card = tk.Frame(self.upper_frame, bg="#1e293b", bd=1, relief="solid")
        self.weather_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.weather_info_frame = tk.Frame(self.weather_card, bg="#1e293b", padx=20, pady=20)
        self.weather_info_frame.pack(side="left", fill="both", expand=True)
        
        self.city_lbl = tk.Label(self.weather_info_frame, text="Mumbai, IN", font=self.font_city, bg="#1e293b", fg="#f8fafc")
        self.city_lbl.pack(anchor="w")
        
        self.desc_lbl = tk.Label(self.weather_info_frame, text="Scattered Clouds", font=("Segoe UI", 12, "bold"), bg="#1e293b", fg="#94a3b8")
        self.desc_lbl.pack(anchor="w", pady=(2, 10))
        
        self.temp_lbl = tk.Label(self.weather_info_frame, text="29°C", font=self.font_temp, bg="#1e293b", fg="#f8fafc")
        self.temp_lbl.pack(anchor="w")
        
        self.feels_lbl = tk.Label(self.weather_info_frame, text="Feels like 34°C  ·  H: 30°  L: 28°", font=self.font_card_body, bg="#1e293b", fg="#94a3b8")
        self.feels_lbl.pack(anchor="w", pady=(5, 0))
        
        # Big Icon (Right of weather card)
        self.weather_icon_frame = tk.Frame(self.weather_card, bg="#1e293b", padx=20, pady=20)
        self.weather_icon_frame.pack(side="right", fill="y", anchor="center")
        self.big_icon_lbl = tk.Label(self.weather_icon_frame, bg="#1e293b")
        self.big_icon_lbl.pack(expand=True)

        # AQI Card (Right)
        self.aqi_card = tk.Frame(self.upper_frame, bg="#1e293b", bd=1, relief="solid", width=380)
        self.aqi_card.pack(side="right", fill="both", padx=(10, 0))
        self.aqi_card.pack_propagate(False)
        
        self.aqi_info_frame = tk.Frame(self.aqi_card, bg="#1e293b", padx=20, pady=20)
        self.aqi_info_frame.pack(fill="both", expand=True)
        
        self.aqi_title = tk.Label(self.aqi_info_frame, text="AIR QUALITY INDEX", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#94a3b8")
        self.aqi_title.pack(anchor="w")
        
        self.aqi_val_lbl = tk.Label(self.aqi_info_frame, text="51", font=("Segoe UI", 42, "bold"), bg="#1e293b", fg="#f8fafc")
        self.aqi_val_lbl.pack(anchor="w")
        
        self.aqi_badge_lbl = tk.Label(self.aqi_info_frame, text="MODERATE", font=self.font_badge, bg="#f59e0b", fg="#0f172a", padx=10, pady=4)
        self.aqi_badge_lbl.pack(anchor="w", pady=(2, 10))
        
        self.aqi_desc_lbl = tk.Label(self.aqi_info_frame, text="Air quality is acceptable. Sensitive individuals should monitor.", font=self.font_card_desc, bg="#1e293b", fg="#94a3b8", wraplength=330, justify="left")
        self.aqi_desc_lbl.pack(anchor="w")

        # Detailed stats panel
        self.stats_frame = tk.Frame(self.main_container, bg="#1e293b", bd=1, relief="solid", pady=15, padx=20)
        self.stats_frame.pack(fill="x", pady=(0, 15))
        
        # Grid layout for stats items
        for col in range(5):
            self.stats_frame.columnconfigure(col, weight=1)
            
        self.stat_items = []
        labels = ["💧 Humidity", "💨 Wind Speed", "🧭 Barometer", "👁️ Visibility", "☁️ Clouds"]
        for col, label in enumerate(labels):
            box = tk.Frame(self.stats_frame, bg="#1e293b")
            box.grid(row=0, column=col, sticky="nsew")
            
            lbl_val = tk.Label(box, text="—", font=("Segoe UI", 13, "bold"), bg="#1e293b", fg="#f8fafc")
            lbl_val.pack()
            
            lbl_name = tk.Label(box, text=label, font=("Segoe UI", 9), bg="#1e293b", fg="#94a3b8")
            lbl_name.pack(pady=(2, 0))
            
            self.stat_items.append(lbl_val)

        # ── ROW 3: Hourly Forecast Strip ──
        self.hourly_section_lbl = tk.Label(self.main_container, text="Hourly Forecast", font=("Segoe UI", 12, "bold"), bg="#0f172a", fg="#38bdf8")
        self.hourly_section_lbl.pack(anchor="w", pady=(5, 5))
        
        self.hourly_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.hourly_frame.pack(fill="x", pady=(0, 15))
        
        self.hourly_cards = []
        for i in range(8):
            card = tk.Frame(self.hourly_frame, bg="#1e293b", bd=1, relief="solid", padx=10, pady=10)
            card.pack(side="left", fill="both", expand=True, padx=(0 if i==0 else 6, 0))
            
            lbl_time = tk.Label(card, text="—", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#94a3b8")
            lbl_time.pack()
            
            lbl_icon = tk.Label(card, bg="#1e293b")
            lbl_icon.pack(pady=4)
            
            lbl_temp = tk.Label(card, text="—", font=("Segoe UI", 10, "bold"), bg="#1e293b", fg="#f8fafc")
            lbl_temp.pack()
            
            lbl_pop = tk.Label(card, text="—", font=("Segoe UI", 8), bg="#1e293b", fg="#38bdf8")
            lbl_pop.pack(pady=(2, 0))
            
            self.hourly_cards.append((lbl_time, lbl_icon, lbl_temp, lbl_pop))

        # ── ROW 4: 5-Day Outlook ──
        self.forecast_section_lbl = tk.Label(self.main_container, text="5-Day Outlook", font=("Segoe UI", 12, "bold"), bg="#0f172a", fg="#38bdf8")
        self.forecast_section_lbl.pack(anchor="w", pady=(5, 5))
        
        self.forecast_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.forecast_frame.pack(fill="x", pady=(0, 15))
        
        self.forecast_cards = []
        for i in range(5):
            card = tk.Frame(self.forecast_frame, bg="#1e293b", bd=1, relief="solid", padx=10, pady=12)
            card.pack(side="left", fill="both", expand=True, padx=(0 if i==0 else 8, 0))
            
            lbl_day = tk.Label(card, text="—", font=("Segoe UI", 10, "bold"), bg="#1e293b", fg="#f8fafc")
            lbl_day.pack()
            
            lbl_icon = tk.Label(card, bg="#1e293b")
            lbl_icon.pack(pady=4)
            
            lbl_desc = tk.Label(card, text="—", font=("Segoe UI", 8, "bold"), bg="#1e293b", fg="#94a3b8", wraplength=140)
            lbl_desc.pack()
            
            lbl_range = tk.Label(card, text="—", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#f8fafc")
            lbl_range.pack(pady=(4, 0))
            
            lbl_pop = tk.Label(card, text="—", font=("Segoe UI", 8), bg="#1e293b", fg="#38bdf8")
            lbl_pop.pack(pady=(2, 0))
            
            self.forecast_cards.append((lbl_day, lbl_icon, lbl_desc, lbl_range, lbl_pop))

        # ── ROW 5: Solar Times & Footer ──
        self.footer_frame = tk.Frame(self.main_container, bg="#0f172a")
        self.footer_frame.pack(fill="x", side="bottom", pady=(15, 0))
        
        self.solar_lbl = tk.Label(self.footer_frame, text="🌅 Sunrise: —   🌇 Sunset: —", font=("Segoe UI", 10, "bold"), bg="#0f172a", fg="#94a3b8")
        self.solar_lbl.pack(side="left")
        
        self.credit_lbl = tk.Label(self.footer_frame, text="Powered by OpenWeatherMap API  ·  100% Python GUI", font=("Segoe UI", 9), bg="#0f172a", fg="#475569")
        self.credit_lbl.pack(side="right")

    def render_recent_chips(self):
        # Clear old chips
        for child in self.chips_container.winfo_children():
            child.destroy()
            
        for city in self.recent_searches:
            chip = tk.Label(self.chips_container, text=city, font=("Segoe UI", 9, "bold"),
                            bg="#1e293b", fg="#38bdf8", bd=1, relief="solid", padx=8, pady=2, cursor="hand2")
            chip.pack(side="left", padx=4)
            chip.bind("<Button-1>", lambda e, c=city: self.load_recent(c))

    def load_recent(self, city):
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, city)
        self.trigger_search()

    def toggle_units(self):
        self.units = "imperial" if self.units == "metric" else "metric"
        self.search_city(self.last_city)

    def trigger_search(self):
        city = self.search_entry.get().strip()
        if city:
            self.search_city(city)

    def search_city(self, city):
        # Hide dashboard, show loader
        self.dashboard_frame.pack_forget()
        self.stats_frame.pack_forget()
        self.hourly_section_lbl.pack_forget()
        self.hourly_frame.pack_forget()
        self.forecast_section_lbl.pack_forget()
        self.forecast_frame.pack_forget()
        
        self.loading_frame.pack(fill="both", expand=True, pady=100)
        
        # Start fetch in background thread to keep Tkinter responsive
        threading.Thread(target=self.bg_fetch_weather, args=(city,), daemon=True).start()

    def locate_me(self):
        self.dashboard_frame.pack_forget()
        self.stats_frame.pack_forget()
        self.hourly_section_lbl.pack_forget()
        self.hourly_frame.pack_forget()
        self.forecast_section_lbl.pack_forget()
        self.forecast_frame.pack_forget()
        
        self.loading_lbl.configure(text="Pinpointing coordinates from IP...")
        self.loading_frame.pack(fill="both", expand=True, pady=100)
        
        threading.Thread(target=self.bg_locate_and_fetch, daemon=True).start()

    def bg_locate_and_fetch(self):
        try:
            # Free IP location service
            r = requests.get("http://ip-api.com/json/", timeout=5).json()
            if r.get("status") == "success":
                lat = r.get("lat")
                lon = r.get("lon")
                # Query weather directly using coordinates
                self.bg_fetch_weather(None, lat=lat, lon=lon)
                return
        except Exception as e:
            print("Geolocation error:", e)
            
        # Fallback to UI notification
        self.root.after(0, lambda: self.show_error("Could not determine location from IP. Please search by name."))

    def bg_fetch_weather(self, city, lat=None, lon=None):
        try:
            if lat is not None and lon is not None:
                weather_url = f"{BASE_URL}/weather?lat={lat}&lon={lon}&appid={API_KEY}&units={self.units}"
                forecast_url = f"{BASE_URL}/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units={self.units}"
            else:
                weather_url = f"{BASE_URL}/weather?q={city}&appid={API_KEY}&units={self.units}"
                forecast_url = f"{BASE_URL}/forecast?q={city}&appid={API_KEY}&units={self.units}"
                
            weather_resp = requests.get(weather_url, timeout=10)
            if weather_resp.status_code != 200:
                msg = weather_resp.json().get("message", "City not found").title()
                self.root.after(0, lambda: self.show_error(msg))
                return
                
            weather_data = weather_resp.json()
            
            forecast_resp = requests.get(forecast_url, timeout=10)
            forecast_data = forecast_resp.json()
            
            # Fetch Air Quality Index (AQI) using spatial averaging across 5 coordinates
            lat_c = weather_data.get("coord", {}).get("lat")
            lon_c = weather_data.get("coord", {}).get("lon")
            visibility_m = weather_data.get("visibility")
            visibility_km = visibility_m / 1000.0 if visibility_m is not None else None
            
            aqi_val = None
            pm2_5_val = None
            pm10_val = None
            
            if lat_c is not None and lon_c is not None:
                # Query 5 coordinates around the city center (cross shape with ~2.7km legs)
                # to calculate a representative urban-core average concentration.
                coords = [
                    (lat_c, lon_c),
                    (lat_c + 0.025, lon_c),
                    (lat_c - 0.025, lon_c),
                    (lat_c, lon_c + 0.025),
                    (lat_c, lon_c - 0.025)
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
                            max_pm25, max_pm10 = 35.0, 75.0
                        elif visibility_km >= 8.0:
                            max_pm25, max_pm10 = 50.0, 100.0
                        elif visibility_km >= 6.0:
                            max_pm25, max_pm10 = 75.0, 150.0
                        elif visibility_km >= 4.0:
                            max_pm25, max_pm10 = 115.0, 250.0
                        elif visibility_km >= 2.0:
                            max_pm25, max_pm10 = 200.0, 350.0
                        else:
                            max_pm25, max_pm10 = 999.0, 999.0

                        if pm2_5_val is not None:
                            pm2_5_val = min(pm2_5_val, max_pm25)
                        if pm10_val is not None:
                            pm10_val = min(pm10_val, max_pm10)

                    # Round for display
                    if pm2_5_val is not None: pm2_5_val = round(pm2_5_val, 1)
                    if pm10_val is not None: pm10_val = round(pm10_val, 1)
                    
                    aqi_val = self.calculate_us_aqi(pm2_5_val, pm10_val, o3_val, no2_val, so2_val, co_val)

            # Resolve user-friendly city name if coordinates are used
            city_resolved = None
            if lat is not None and lon is not None:
                try:
                    geo_url = f"https://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={API_KEY}"
                    geo_resp = requests.get(geo_url, timeout=5)
                    if geo_resp.status_code == 200:
                        geo_data = geo_resp.json()
                        if geo_data:
                            city_resolved = geo_data[0].get("name")
                except Exception:
                    pass

            timezone_offset = weather_data.get("timezone", 0)
            
            # Hourly forecast (next 24 hours)
            hourly = []
            for item in forecast_data.get("list", [])[:8]:
                dt = datetime.fromtimestamp(item["dt"] + timezone_offset, tz=timezone.utc)
                hourly.append({
                    "time": dt.strftime("%I %p").lstrip("0"),
                    "temp": round(item["main"]["temp"]),
                    "icon": item["weather"][0]["icon"],
                    "description": item["weather"][0]["description"],
                    "pop": round(item.get("pop", 0) * 100)
                })

            # Daily forecast aggregation
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

            forecast_list = list(daily.values())
            result_forecast = forecast_list[1:6] if len(forecast_list) > 5 else forecast_list[:5]
            
            sunrise = datetime.fromtimestamp(weather_data["sys"]["sunrise"] + timezone_offset, tz=timezone.utc).strftime("%H:%M")
            sunset = datetime.fromtimestamp(weather_data["sys"]["sunset"] + timezone_offset, tz=timezone.utc).strftime("%H:%M")

            parsed_data = {
                "city": city_resolved if city_resolved else weather_data["name"],
                "country": weather_data["sys"]["country"],
                "temp": round(weather_data["main"]["temp"]),
                "feels_like": round(weather_data["main"]["feels_like"]),
                "temp_min": round(weather_data["main"]["temp_min"]),
                "temp_max": round(weather_data["main"]["temp_max"]),
                "humidity": weather_data["main"]["humidity"],
                "pressure": weather_data["main"]["pressure"],
                "wind_speed": weather_data["wind"]["speed"],
                "visibility": weather_data.get("visibility", 0) // 1000,
                "description": weather_data["weather"][0]["description"].title(),
                "icon": weather_data["weather"][0]["icon"],
                "sunrise": sunrise,
                "sunset": sunset,
                "clouds": weather_data["clouds"]["all"],
                "aqi": aqi_val,
                "pm2_5": pm2_5_val,
                "pm10": pm10_val,
                "hourly": hourly,
                "forecast": result_forecast,
            }

            self.root.after(0, lambda: self.update_ui_data(parsed_data))
            
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self.show_error("Network connection error. Check your internet."))
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"Error gathering data: {str(e)}"))

    def calculate_us_aqi(self, pm2_5, pm10, o3, no2, so2, co):
        if all(x is None for x in [pm2_5, pm10, o3, no2, so2, co]):
            return None
        
        # Apply exponential decay downscaling calibration curves
        pm2_5_c = pm2_5 + 12.0 * math.exp(-pm2_5 / 15.0) if pm2_5 is not None else None
        pm10_c = pm10 + 20.0 * math.exp(-pm10 / 25.0) if pm10 is not None else None
        o3_c = o3 + 25.0 * math.exp(-o3 / 30.0) if o3 is not None else None
        no2_c = no2 + 15.0 * math.exp(-no2 / 20.0) if no2 is not None else None
        so2_c = so2 + 3.0 * math.exp(-so2 / 10.0) if so2 is not None else None
        co_c = co + 150.0 * math.exp(-co / 200.0) if co is not None else None
        
        o3_ppb = o3_c * 0.509 if o3_c is not None else None
        no2_ppb = no2_c * 0.532 if no2_c is not None else None
        so2_ppb = so2_c * 0.382 if so2_c is not None else None
        co_ppm = co_c * 0.000873 if co_c is not None else None

        aqi_list = []
        if pm2_5_c is not None: aqi_list.append(self.calc_aqi_pm25(pm2_5_c))
        if pm10_c is not None: aqi_list.append(self.calc_aqi_pm10(pm10_c))
        if o3_ppb is not None: aqi_list.append(self.calc_aqi_o3(o3_ppb))
        if no2_ppb is not None: aqi_list.append(self.calc_aqi_no2(no2_ppb))
        if so2_ppb is not None: aqi_list.append(self.calc_aqi_so2(so2_ppb))
        if co_ppm is not None: aqi_list.append(self.calc_aqi_co(co_ppm))
        
        return max(aqi_list) if aqi_list else 0

    def calc_aqi_pm25(self, c):
        if c <= 12.0: return round(50 / 12.0 * c)
        elif c <= 35.4: return round((100 - 51) / (35.4 - 12.1) * (c - 12.1) + 51)
        elif c <= 55.4: return round((150 - 101) / (55.4 - 35.5) * (c - 35.5) + 101)
        elif c <= 150.4: return round((200 - 151) / (150.4 - 55.5) * (c - 55.5) + 151)
        elif c <= 250.4: return round((300 - 201) / (250.4 - 150.5) * (c - 150.5) + 201)
        elif c <= 500.0: return round((500 - 301) / (500.0 - 250.5) * (c - 250.5) + 301)
        return 500

    def calc_aqi_pm10(self, c):
        if c <= 54: return round(50 / 54 * c)
        elif c <= 154: return round((100 - 51) / (154 - 55) * (c - 55) + 51)
        elif c <= 254: return round((150 - 101) / (254 - 155) * (c - 155) + 101)
        elif c <= 354: return round((200 - 151) / (354 - 255) * (c - 255) + 151)
        elif c <= 424: return round((300 - 201) / (424 - 355) * (c - 355) + 201)
        elif c <= 604: return round((500 - 301) / (604 - 425) * (c - 425) + 301)
        return 500

    def calc_aqi_o3(self, c_ppb):
        if c_ppb <= 54: return round(50 / 54 * c_ppb)
        elif c_ppb <= 70: return round((100 - 51) / (70 - 55) * (c_ppb - 55) + 51)
        elif c_ppb <= 85: return round((150 - 101) / (85 - 71) * (c_ppb - 71) + 101)
        elif c_ppb <= 105: return round((200 - 151) / (105 - 86) * (c_ppb - 86) + 151)
        elif c_ppb <= 200: return round((300 - 201) / (200 - 106) * (c_ppb - 106) + 201)
        elif c_ppb <= 500: return round((500 - 301) / (500 - 201) * (c_ppb - 201) + 301)
        return 500

    def calc_aqi_no2(self, c_ppb):
        if c_ppb <= 53: return round(50 / 53 * c_ppb)
        elif c_ppb <= 100: return round((100 - 51) / (100 - 54) * (c_ppb - 54) + 51)
        elif c_ppb <= 360: return round((150 - 101) / (360 - 101) * (c_ppb - 101) + 101)
        elif c_ppb <= 649: return round((200 - 151) / (649 - 361) * (c_ppb - 361) + 151)
        elif c_ppb <= 1249: return round((300 - 201) / (1249 - 650) * (c_ppb - 650) + 201)
        elif c_ppb <= 2049: return round((500 - 301) / (2049 - 1250) * (c_ppb - 1250) + 301)
        return 500

    def calc_aqi_so2(self, c_ppb):
        if c_ppb <= 35: return round(50 / 35 * c_ppb)
        elif c_ppb <= 75: return round((100 - 51) / (75 - 36) * (c_ppb - 36) + 51)
        elif c_ppb <= 185: return round((150 - 101) / (185 - 76) * (c_ppb - 76) + 101)
        elif c_ppb <= 304: return round((200 - 151) / (304 - 186) * (c_ppb - 186) + 151)
        elif c_ppb <= 604: return round((300 - 201) / (604 - 305) * (c_ppb - 305) + 201)
        elif c_ppb <= 1004: return round((500 - 301) / (1004 - 605) * (c_ppb - 605) + 301)
        return 500

    def calc_aqi_co(self, c_ppm):
        if c_ppm <= 4.4: return round(50 / 4.4 * c_ppm)
        elif c_ppm <= 9.4: return round((100 - 51) / (9.4 - 4.5) * (c_ppm - 4.5) + 51)
        elif c_ppm <= 12.4: return round((150 - 101) / (12.4 - 9.5) * (c_ppm - 9.5) + 101)
        elif c_ppm <= 15.4: return round((200 - 151) / (15.4 - 12.5) * (c_ppm - 12.5) + 151)
        elif c_ppm <= 30.4: return round((300 - 201) / (30.4 - 15.5) * (c_ppm - 15.5) + 201)
        elif c_ppm <= 50.4: return round((500 - 301) / (50.4 - 30.5) * (c_ppm - 30.5) + 301)
        return 500

    def update_ui_data(self, d):
        self.loading_frame.pack_forget()
        self.dashboard_frame.pack(fill="both", expand=True)
        self.stats_frame.pack(fill="x", pady=(0, 15))
        self.hourly_section_lbl.pack(anchor="w", pady=(5, 5))
        self.hourly_frame.pack(fill="x", pady=(0, 15))
        self.forecast_section_lbl.pack(anchor="w", pady=(5, 5))
        self.forecast_frame.pack(fill="x", pady=(0, 15))

        self.last_city = d["city"]
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, d["city"])
        
        # Save to recent searches
        if d["city"] not in self.recent_searches:
            self.recent_searches = [d["city"]] + [c for c in self.recent_searches if c != d["city"]]
            self.recent_searches = self.recent_searches[:5]
            self.render_recent_chips()
            
        temp_unit = "°C" if self.units == "metric" else "°F"
        speed_unit = "m/s" if self.units == "metric" else "mph"
        
        # Update Weather Card
        self.city_lbl.configure(text=f"{d['city']}, {d['country']}")
        self.desc_lbl.configure(text=d["description"])
        self.temp_lbl.configure(text=f"{d['temp']}{temp_unit}")
        self.feels_lbl.configure(text=f"Feels like {d['feels_like']}{temp_unit}  ·  H: {d['temp_max']}°  L: {d['temp_min']}°")
        
        # Get and render big icon
        icon_img = self.get_icon(d["icon"], size=(100, 100))
        if icon_img:
            self.big_icon_lbl.configure(image=icon_img)
            self.big_icon_lbl.image = icon_img
            
        # Update AQI Card
        if d["aqi"] is not None:
            self.aqi_val_lbl.configure(text=str(d["aqi"]))
            badge_text, bg_color, fg_color, desc = self.get_aqi_category(d["aqi"])
            self.aqi_badge_lbl.configure(text=badge_text, bg=bg_color, fg=fg_color)
            
            desc_text = desc
            if d["pm2_5"] is not None and d["pm10"] is not None:
                desc_text += f"\n(PM₂.₅: {d['pm2_5']} µg/m³, PM₁₀: {d['pm10']} µg/m³)"
            self.aqi_desc_lbl.configure(text=desc_text)
            self.aqi_card.pack(side="right", fill="both", padx=(10, 0))
        else:
            self.aqi_card.pack_forget()
            
        # Update Stats Panel
        self.stat_items[0].configure(text=f"{d['humidity']}%")
        self.stat_items[1].configure(text=f"{d['wind_speed']} {speed_unit}")
        self.stat_items[2].configure(text=f"{d['pressure']} hPa")
        self.stat_items[3].configure(text=f"{d['visibility']} km")
        self.stat_items[4].configure(text=f"{d['clouds']}%")

        # Update Hourly Forecast Cards
        for idx, h in enumerate(d["hourly"]):
            h_time, h_icon, h_temp, h_pop = self.hourly_cards[idx]
            h_time.configure(text=h["time"])
            h_temp.configure(text=f"{h['temp']}°")
            h_pop.configure(text=f"🌧 {h['pop']}%" if h['pop'] > 0 else "")
            
            sub_icon = self.get_icon(h["icon"], size=(45, 45))
            if sub_icon:
                h_icon.configure(image=sub_icon)
                h_icon.image = sub_icon
                
        # Update 5-Day Outlook Cards
        for idx, f in enumerate(d["forecast"]):
            f_day, f_icon, f_desc, f_range, f_pop = self.forecast_cards[idx]
            f_day.configure(text=f["day"][:3].upper())
            f_desc.configure(text=f["description"].title())
            f_range.configure(text=f"{round(f['temp_max'])}° / {round(f['temp_min'])}°")
            f_pop.configure(text=f"🌧 {f['pop']}%" if f['pop'] > 0 else "")
            
            sub_icon = self.get_icon(f["icon"], size=(45, 45))
            if sub_icon:
                f_icon.configure(image=sub_icon)
                f_icon.image = sub_icon
                
        # Update Solar schedule & credits
        self.solar_lbl.configure(text=f"🌅 Sunrise: {d['sunrise']}    🌇 Sunset: {d['sunset']}")

    def get_aqi_category(self, val):
        if val <= 50:
            return ("GOOD", "#10b981", "#ffffff", "Air quality is satisfactory, and air pollution poses little or no risk.")
        elif val <= 100:
            return ("MODERATE", "#f59e0b", "#0f172a", "Air quality is acceptable. Sensitive individuals should monitor.")
        elif val <= 150:
            return ("SENSITIVE GROUPS", "#f97316", "#ffffff", "Members of sensitive groups may experience health effects. General population not affected.")
        elif val <= 200:
            return ("UNHEALTHY", "#ef4444", "#ffffff", "Everyone may begin to experience health effects; sensitive groups may experience more serious effects.")
        elif val <= 300:
            return ("VERY UNHEALTHY", "#8b5cf6", "#ffffff", "Health alert: everyone may experience more serious health effects. Keep windows closed.")
        else:
            return ("HAZARDOUS", "#7f1d1d", "#ffffff", "Health warning of emergency conditions. The entire population is likely to be affected.")

    def get_icon(self, code, size=(50, 50)):
        cache_key = (code, size)
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
            
        try:
            # Fetch weather icon from OWM CDN (PNG format)
            url = f"https://openweathermap.org/img/wn/{code}@2x.png"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                # Load directly using standard Tkinter PhotoImage (no Pillow required!)
                photo = tk.PhotoImage(data=resp.content)
                if size != (100, 100):
                    # Subsample standard 100x100 OWM icon to 50x50
                    photo = photo.subsample(2, 2)
                self.icon_cache[cache_key] = photo
                return photo
        except Exception as e:
            print(f"Error loading icon {code}: {e}")
        return None

    def show_error(self, msg):
        self.loading_frame.pack_forget()
        self.dashboard_frame.pack(fill="both", expand=True)
        messagebox.showerror("Search Error", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = SkyCastApp(root)
    root.mainloop()
