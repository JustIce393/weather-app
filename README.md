# SkyCast — Weather Forecaster

> A premium meteorological desktop application built in **Python 3** using **Tkinter** that queries **OpenWeatherMap API** to deliver real-time weather, forecast details, and air quality index analytics.

![Language](https://img.shields.io/badge/language-Python%203-blue)
![GUI](https://img.shields.io/badge/framework-Tkinter-lightgrey)
![API](https://img.shields.io/badge/API-OpenWeatherMap-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 📌 What is this Project?

**SkyCast** is a modern desktop weather forecaster. It showcases SDE concepts including:
1. **Asynchronous Multithreading:** Offloads network requests to background threads, ensuring a highly responsive GUI that never freezes.
2. **IP-Based Geolocation:** Integrates location-detection APIs to find the user's city automatically.
3. **Pillow-free Standard Render:** Built using native Tkinter Canvas capabilities and standard widgets, avoiding complex external library setups.
4. **Clean UI & Caching:** Designed using custom dark slate palettes (`#0f172a`), flex-like layouts, and weather icon caching.

---

## 🏗️ System Architecture

SkyCast separates network I/O from the GUI event loop using a **Multithreaded Task Delegation Model**:

```
┌────────────────────────────────────────────────────────┐
│                   Tkinter Main Thread                  │
│                     (root.mainloop)                    │
│   • Renders UI Cards & Charts   • Handles Mouse Clicks │
└───────────┬────────────────────────────────────▲───────┘
            │                                    │
            │ Dispatches worker                  │ Callback
            ▼                                    │ (via UI update)
┌────────────────────────────────────────────────┴───────┐
│                 Background Worker Thread               │
│                 (ThreadPoolExecutor / Thread)          │
│   • Queries http://ip-api.com (Geolocation)           │
│   • Queries OpenWeatherMap API (Weather & Forecast)    │
│   • Downloads & parses icon assets                     │
└────────────────────────────────────────────────────────┘
```

---

## ✨ Features

* **Real-Time Weather Metrics:** Displays Temperature, Feels Like, Wind Speed, Humidity, Air Quality Index (AQI), and Sunrise/Sunset times.
* **5-Day Forecast:** Dynamic cards displaying upcoming weather conditions.
* **Auto-Locate (IP Geolocation):** Estimate user coordinates and fetch weather with one click.
* **Recent Searches:** Remembers recently searched cities for quick navigation.
* **Dual Unit Support:** Smoothly toggle between Metric (°C, m/s) and Imperial (°F, mph).

---

## 🚀 How to Run

1. Clone or download the repository.
2. Navigate to the `Weather Forecaster` folder:
   ```bash
   cd "Weather Forecaster"
   ```
3. Run the batch helper:
   ```bash
   "Weather Forecaster.bat"
   ```
   Or run the Python file directly:
   ```bash
   python "Weather Forecaster.py"
   ```

---

## 📁 Project Structure

```
weather-app/
├── .gitignore
└── Weather Forecaster/
    ├── Weather Forecaster.py    <- Main Python application
    ├── Weather Forecaster.bat   <- One-click launch script
    ├── requirements.txt         <- Dependency list (requests)
    └── venv/                    <- Local Python virtual environment
```

---

## 💡 SDE Interview Q&A

### Q1: How did you ensure the GUI doesn't freeze when searching for a city?
> API calls are synchronous blocking operations. If run directly inside the main UI thread, Tkinter would block on the socket read, causing the window to freeze, stop updating animations, and show as "Not Responding" to the OS. I resolved this by spawning all network calls (using `requests.get`) inside background threads using Python's `threading.Thread` or `ThreadPoolExecutor`. The main thread continues running the event loop smoothly, rendering a loading indicator, and updates the display once the background thread returns the data.

### Q2: How does the "Locate Me" feature estimate coordinates without GPS hardware?
> Since desktop machines lack GPS hardware, the app queries an IP geolocation API (`http://ip-api.com/json`). This API maps the user's public IP address to local ISP routing records and returns the approximate latitude, longitude, and city name. The app then parses this response and makes a follow-up call to the OpenWeatherMap API using the exact coordinates, returning hyper-local weather statistics.

### Q3: Why did you implement an icon cache?
> Weather icons are fetched dynamically from OpenWeatherMap servers. To avoid fetching the same image file repeatedly when toggling units or searching the same cities, I created a dictionary-based `icon_cache`. When an icon is requested, the code first checks this cache. If found, it displays the cached image, saving network bandwidth, reducing API traffic, and speeding up render times.
