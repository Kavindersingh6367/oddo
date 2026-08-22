# -*- coding: utf-8 -*-
"""
GlobeTrotter Weather Intelligence & Dynamic Itinerary Adjustment Service.
Integrates live weather forecasting (Open-Meteo API with deterministic fallback),
hazard detection (rain, thunderstorms, heatwaves, strong winds),
activity outdoor/indoor classification, and smart itinerary re-scheduling.
"""

import requests
import logging
from datetime import datetime, date, timedelta
import math
import hashlib

_logger = logging.getLogger("globetrotter.weather")

WMO_WEATHER_MAP = {
    0: {"label": "Clear Sky", "icon": "fa-sun", "type": "clear", "hazard": None},
    1: {"label": "Mainly Clear", "icon": "fa-cloud-sun", "type": "clear", "hazard": None},
    2: {"label": "Partly Cloudy", "icon": "fa-cloud-sun", "type": "cloudy", "hazard": None},
    3: {"label": "Overcast", "icon": "fa-cloud", "type": "cloudy", "hazard": None},
    45: {"label": "Foggy", "icon": "fa-smog", "type": "fog", "hazard": "low_visibility"},
    48: {"label": "Depositing Rime Fog", "icon": "fa-smog", "type": "fog", "hazard": "low_visibility"},
    51: {"label": "Light Drizzle", "icon": "fa-cloud-rain", "type": "rain", "hazard": "drizzle"},
    53: {"label": "Moderate Drizzle", "icon": "fa-cloud-rain", "type": "rain", "hazard": "drizzle"},
    55: {"label": "Dense Drizzle", "icon": "fa-cloud-rain", "type": "rain", "hazard": "rain"},
    61: {"label": "Slight Rain", "icon": "fa-cloud-showers-heavy", "type": "rain", "hazard": "rain"},
    63: {"label": "Moderate Rain", "icon": "fa-cloud-showers-heavy", "type": "rain", "hazard": "rain"},
    65: {"label": "Heavy Rain", "icon": "fa-cloud-showers-heavy", "type": "rain", "hazard": "heavy_rain"},
    71: {"label": "Slight Snowfall", "icon": "fa-snowflake", "type": "snow", "hazard": "snow"},
    73: {"label": "Moderate Snowfall", "icon": "fa-snowflake", "type": "snow", "hazard": "snow"},
    75: {"label": "Heavy Snowfall", "icon": "fa-snowflake", "type": "snow", "hazard": "heavy_snow"},
    80: {"label": "Light Rain Showers", "icon": "fa-cloud-sun-rain", "type": "rain", "hazard": "rain"},
    81: {"label": "Moderate Rain Showers", "icon": "fa-cloud-showers-heavy", "type": "rain", "hazard": "heavy_rain"},
    82: {"label": "Violent Rain Showers", "icon": "fa-cloud-showers-water", "type": "rain", "hazard": "heavy_rain"},
    95: {"label": "Thunderstorm", "icon": "fa-bolt-lightning", "type": "thunderstorm", "hazard": "thunderstorm"},
    96: {"label": "Thunderstorm with Hail", "icon": "fa-cloud-bolt", "type": "thunderstorm", "hazard": "thunderstorm"},
    99: {"label": "Severe Thunderstorm with Heavy Hail", "icon": "fa-cloud-bolt", "type": "thunderstorm", "hazard": "thunderstorm"}
}

OUTDOOR_KEYWORDS = [
    "walk", "walking", "trek", "trekking", "hike", "hiking", "beach", "safari",
    "fort", "gardens", "garden", "park", "lake", "boating", "cruise", "open-air",
    "outdoor", "desert", "climbing", "viewpoint", "waterfall", "bazaar", "monument",
    "sightseeing", "cycle", "cycling", "ruins", "canyon", "valley", "temple courtyard"
]

INDOOR_KEYWORDS = [
    "museum", "gallery", "palace interior", "spa", "wellness", "mall", "shopping center",
    "indoor", "aquarium", "dining", "cooking class", "theater", "show", "auditorium",
    "planetarium", "arcade", "art center", "exhibition", "cafe"
]

class WeatherService:
    @staticmethod
    def is_outdoor_activity(category, name="", description=""):
        """Classifies if an activity is outdoor/weather-sensitive based on category and text context."""
        text = f"{name} {description}".lower()
        
        # Check explicit indoor keywords first
        for kw in INDOOR_KEYWORDS:
            if kw in text:
                return False
                
        # Check explicit outdoor keywords
        for kw in OUTDOOR_KEYWORDS:
            if kw in text:
                return True

        if category in ['adventure', 'nature']:
            return True
        elif category in ['food', 'shopping', 'relaxation', 'entertainment', 'culture']:
            return False
        elif category == 'sightseeing':
            return True
            
        return True

    @classmethod
    def fetch_weather_forecast(cls, latitude, longitude, start_date_str=None, end_date_str=None, city_name=""):
        """
        Fetches live forecast from Open-Meteo API or produces accurate deterministic simulation.
        Handles date range slicing, daily metrics, and hourly detail.
        """
        lat = float(latitude or 28.6139)
        lon = float(longitude or 77.2090)

        # Default to 7 days from today if dates not provided
        today = date.today()
        if not start_date_str:
            s_date = today
        else:
            try:
                s_date = datetime.strptime(str(start_date_str)[:10], '%Y-%m-%d').date()
            except Exception:
                s_date = today

        if not end_date_str:
            e_date = s_date + timedelta(days=6)
        else:
            try:
                e_date = datetime.strptime(str(end_date_str)[:10], '%Y-%m-%d').date()
            except Exception:
                e_date = s_date + timedelta(days=6)

        if e_date < s_date:
            e_date = s_date + timedelta(days=1)

        days_count = min(16, max(1, (e_date - s_date).days + 1))
        
        forecast_days = []
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,windspeed_10m_max&hourly=temperature_2m,precipitation_probability,precipitation,weathercode,windspeed_10m&timezone=auto"
            res = requests.get(url, timeout=3.5)
            if res.status_code == 200:
                data = res.json()
                daily = data.get("daily", {})
                dates = daily.get("time", [])
                wcodes = daily.get("weathercode", [])
                t_max = daily.get("temperature_2m_max", [])
                t_min = daily.get("temperature_2m_min", [])
                precip = daily.get("precipitation_sum", [])
                precip_prob = daily.get("precipitation_probability_max", [])
                winds = daily.get("windspeed_10m_max", [])

                for idx, d_str in enumerate(dates):
                    cur_d = datetime.strptime(d_str, "%Y-%m-%d").date()
                    if s_date <= cur_d <= e_date:
                        wcode = int(wcodes[idx]) if idx < len(wcodes) and wcodes[idx] is not None else 0
                        info = WMO_WEATHER_MAP.get(wcode, WMO_WEATHER_MAP[0])
                        forecast_days.append({
                            "date": d_str,
                            "day_name": cur_d.strftime("%a"),
                            "weather_code": wcode,
                            "condition": info["label"],
                            "icon": info["icon"],
                            "weather_type": info["type"],
                            "temp_max": round(float(t_max[idx]) if idx < len(t_max) and t_max[idx] is not None else 28.0, 1),
                            "temp_min": round(float(t_min[idx]) if idx < len(t_min) and t_min[idx] is not None else 18.0, 1),
                            "temp_avg": round(((float(t_max[idx] or 28) + float(t_min[idx] or 18)) / 2), 1),
                            "precipitation_mm": round(float(precip[idx]) if idx < len(precip) and precip[idx] is not None else 0.0, 1),
                            "precipitation_probability": int(precip_prob[idx]) if idx < len(precip_prob) and precip_prob[idx] is not None else 0,
                            "wind_speed_kmh": round(float(winds[idx]) if idx < len(winds) and winds[idx] is not None else 12.0, 1),
                            "hazard": info["hazard"]
                        })
        except Exception as e:
            _logger.warning(f"Open-Meteo live query notice ({e}). Using seasonal weather synthesis.")

        # Fallback or synthetic generation if API returned empty or dates are outside live window
        if not forecast_days:
            forecast_days = cls._generate_synthetic_forecast(lat, lon, s_date, e_date, city_name)

        return {
            "city_name": city_name,
            "latitude": lat,
            "longitude": lon,
            "start_date": str(s_date),
            "end_date": str(e_date),
            "days": forecast_days
        }

    @classmethod
    def _generate_synthetic_forecast(cls, lat, lon, s_date, e_date, city_name=""):
        """Generates realistic, deterministic seasonal weather forecasts for testing & offline mode."""
        days = []
        cur = s_date
        day_idx = 0
        while cur <= e_date and len(days) < 30:
            d_str = str(cur)
            # Create deterministic seed hash
            h_input = f"{city_name}-{lat:.2f}-{lon:.2f}-{d_str}"
            h_val = int(hashlib.md5(h_input.encode('utf-8')).hexdigest()[:6], 16)
            
            # Base seasonal temperature (warmer near tropics, cooler near poles/winter)
            month = cur.month
            is_summer = 4 <= month <= 8
            base_temp = 30.0 if is_summer else 22.0
            
            # Introduce weather pattern variations
            pattern = (h_val + day_idx * 17) % 100
            
            if pattern < 45:
                # Sunny / Clear
                wcode = 0 if pattern < 25 else 1
                precip = 0.0
                precip_prob = 5
                temp_max = base_temp + (pattern % 5)
                temp_min = temp_max - 9.0
                wind = 8.0 + (pattern % 10)
            elif pattern < 70:
                # Partly Cloudy
                wcode = 2
                precip = 0.0
                precip_prob = 20
                temp_max = base_temp + (pattern % 4) - 2.0
                temp_min = temp_max - 8.0
                wind = 12.0 + (pattern % 12)
            elif pattern < 88:
                # Rain / Showers
                wcode = 61 if pattern < 80 else 63
                precip = round(2.5 + (pattern % 12) * 0.8, 1)
                precip_prob = 75 + (pattern % 20)
                temp_max = base_temp - 5.0
                temp_min = temp_max - 5.0
                wind = 22.0 + (pattern % 15)
            elif pattern < 95:
                # Thunderstorm
                wcode = 95
                precip = round(12.0 + (pattern % 15), 1)
                precip_prob = 90
                temp_max = base_temp - 4.0
                temp_min = temp_max - 6.0
                wind = 36.0 + (pattern % 18)
            else:
                # Extreme Heat
                wcode = 0
                precip = 0.0
                precip_prob = 0
                temp_max = 39.5 + (pattern % 4) * 0.5
                temp_min = temp_max - 10.0
                wind = 10.0

            info = WMO_WEATHER_MAP.get(wcode, WMO_WEATHER_MAP[0])
            days.append({
                "date": d_str,
                "day_name": cur.strftime("%a"),
                "weather_code": wcode,
                "condition": info["label"],
                "icon": info["icon"],
                "weather_type": info["type"],
                "temp_max": round(temp_max, 1),
                "temp_min": round(temp_min, 1),
                "temp_avg": round((temp_max + temp_min) / 2, 1),
                "precipitation_mm": precip,
                "precipitation_probability": precip_prob,
                "wind_speed_kmh": round(wind, 1),
                "hazard": info["hazard"]
            })
            cur += timedelta(days=1)
            day_idx += 1
            
        return days

    @classmethod
    def analyze_activity_risk(cls, activity, day_forecast):
        """
        Evaluates weather hazard risks for an activity on a given day.
        Returns risk assessment dictionary with severity, reason, and tags.
        """
        cat = activity.get('category', 'sightseeing')
        name = activity.get('name', '')
        desc = activity.get('description', '')
        is_outdoor = cls.is_outdoor_activity(cat, name, desc)

        if not day_forecast:
            return {
                "is_outdoor": is_outdoor,
                "risk_level": "safe",
                "hazard_type": None,
                "alert_title": "Normal Conditions",
                "alert_description": "No adverse weather forecasted.",
                "weather_icon": "fa-sun",
                "weather_condition": "Clear"
            }

        precip = day_forecast.get('precipitation_mm', 0.0)
        precip_prob = day_forecast.get('precipitation_probability', 0)
        temp_max = day_forecast.get('temp_max', 25.0)
        wind = day_forecast.get('wind_speed_kmh', 10.0)
        wcode = day_forecast.get('weather_code', 0)
        cond = day_forecast.get('condition', 'Clear')
        icon = day_forecast.get('icon', 'fa-sun')

        # Indoor activities are generally resilient to weather
        if not is_outdoor:
            return {
                "is_outdoor": False,
                "risk_level": "safe",
                "hazard_type": None,
                "alert_title": "Indoor Activity (Weather-Safe)",
                "alert_description": f"Scheduled indoors at {cond} ({temp_max}°C). Completely safe from adverse weather.",
                "weather_icon": icon,
                "weather_condition": cond
            }

        # Outdoor activity hazard analysis
        if wcode in [95, 96, 99]:
            return {
                "is_outdoor": True,
                "risk_level": "high",
                "hazard_type": "thunderstorm",
                "alert_title": "⚠️ Severe Thunderstorm Alert",
                "alert_description": f"Thunderstorms and lightning predicted ({precip}mm rain, {wind} km/h wind). Outdoor exploration is hazardous.",
                "weather_icon": "fa-bolt-lightning",
                "weather_condition": cond
            }
        elif precip >= 4.0 or precip_prob >= 70 or wcode in [63, 65, 81, 82]:
            return {
                "is_outdoor": True,
                "risk_level": "high",
                "hazard_type": "rain",
                "alert_title": "⚠️ Heavy Rain & Showers Alert",
                "alert_description": f"Heavy rain forecasted ({precip}mm, {precip_prob}% chance). Outdoor walking and sightseeing will be heavily disrupted.",
                "weather_icon": "fa-cloud-showers-heavy",
                "weather_condition": cond
            }
        elif precip >= 1.5 or precip_prob >= 50 or wcode in [51, 53, 55, 61, 80]:
            return {
                "is_outdoor": True,
                "risk_level": "moderate",
                "hazard_type": "rain",
                "alert_title": "⚠️ Rain & Drizzle Advisory",
                "alert_description": f"Wet conditions expected ({precip}mm rain, {precip_prob}% probability). Consider rescheduling or carrying wet weather gear.",
                "weather_icon": "fa-cloud-rain",
                "weather_condition": cond
            }
        elif temp_max >= 38.0:
            return {
                "is_outdoor": True,
                "risk_level": "moderate",
                "hazard_type": "extreme_heat",
                "alert_title": "🌡️ Extreme Heatwave Warning",
                "alert_description": f"High temperatures ({temp_max}°C) expected. Outdoor strenuous activity may cause heat exhaustion.",
                "weather_icon": "fa-temperature-high",
                "weather_condition": "Extreme Heat"
            }
        elif wind >= 35.0:
            return {
                "is_outdoor": True,
                "risk_level": "moderate",
                "hazard_type": "strong_winds",
                "alert_title": "💨 High Wind Advisory",
                "alert_description": f"Strong gusty winds ({wind} km/h) forecasted. Outdoor viewpoints and open waters may be restricted.",
                "weather_icon": "fa-wind",
                "weather_condition": "High Winds"
            }
        else:
            return {
                "is_outdoor": True,
                "risk_level": "safe",
                "hazard_type": None,
                "alert_title": "☀️ Ideal Weather Conditions",
                "alert_description": f"Clear and favorable weather ({cond}, {temp_max}°C). Perfect for outdoor plans.",
                "weather_icon": icon,
                "weather_condition": cond
            }

    @classmethod
    def generate_trip_weather_intelligence(cls, trip_dict, stops, activities, catalog_activities_by_city):
        """
        Comprehensive trip weather analysis engine:
        1. Queries forecast for each stop / city.
        2. Evaluates weather risks for each activity.
        3. Formulates smart adjustments (move to sunny day or substitute with indoor activity).
        """
        # Map stops by stop_id and city_id
        stops_by_id = {s['id']: s for s in stops}
        city_coords = {}
        for s in stops:
            cid = s.get('city_id')
            if cid:
                city_coords[cid] = {
                    "city_name": s.get('city_name', ''),
                    "lat": s.get('latitude') or 28.6139,
                    "lon": s.get('longitude') or 77.2090,
                    "arrival": s.get('arrival_date'),
                    "departure": s.get('departure_date')
                }

        # Fetch forecasts per stop city
        city_forecasts = {}
        for cid, info in city_coords.items():
            f_data = cls.fetch_weather_forecast(
                latitude=info['lat'],
                longitude=info['lon'],
                start_date_str=trip_dict.get('start_date'),
                end_date_str=trip_dict.get('end_date'),
                city_name=info['city_name']
            )
            city_forecasts[cid] = f_data

        # Map day numbers to dates
        trip_start = trip_dict.get('start_date')
        if isinstance(trip_start, str):
            try:
                trip_start = datetime.strptime(trip_start[:10], '%Y-%m-%d').date()
            except Exception:
                trip_start = date.today()
        elif isinstance(trip_start, datetime):
            trip_start = trip_start.date()
        elif not trip_start:
            trip_start = date.today()

        day_date_map = {}
        duration_days = int(trip_dict.get('duration_days') or 1)
        for d in range(1, duration_days + 1):
            day_date_map[d] = trip_start + timedelta(days=d - 1)

        # Analyze each scheduled activity
        evaluated_activities = []
        high_risk_count = 0
        mod_risk_count = 0
        safe_count = 0

        for act in activities:
            stop = stops_by_id.get(act.get('stop_id'))
            cid = stop.get('city_id') if stop else None
            c_forecast = city_forecasts.get(cid, {}) if cid else None
            
            day_num = int(act.get('day_number') or 1)
            act_date = day_date_map.get(day_num, trip_start)
            act_date_str = str(act_date)

            # Match day forecast
            day_fc = None
            if c_forecast and 'days' in c_forecast:
                for df in c_forecast['days']:
                    if df.get('date') == act_date_str:
                        day_fc = df
                        break

            risk = cls.analyze_activity_risk(act, day_fc)
            if risk['risk_level'] == 'high':
                high_risk_count += 1
            elif risk['risk_level'] == 'moderate':
                mod_risk_count += 1
            else:
                safe_count += 1

            # Prepare smart adjustment suggestions for affected activities
            suggestions = []
            if risk['risk_level'] in ['high', 'moderate'] and risk['is_outdoor']:
                # Suggestion Option 1: Move to a better day in the trip within the same city
                best_alternative_day = None
                if c_forecast and 'days' in c_forecast:
                    for df in c_forecast['days']:
                        df_date_str = df.get('date')
                        # Check which day number this corresponds to
                        for d_no, d_val in day_date_map.items():
                            if str(d_val) == df_date_str and d_no != day_num:
                                # Check if this day is sunny/safe
                                if df.get('precipitation_mm', 0) < 1.0 and df.get('weather_code', 0) in [0, 1, 2] and df.get('temp_max', 25) < 36.0:
                                    best_alternative_day = {
                                        "day_number": d_no,
                                        "date": df_date_str,
                                        "condition": df.get('condition'),
                                        "temp_max": df.get('temp_max'),
                                        "icon": df.get('icon')
                                    }
                                    break
                        if best_alternative_day:
                            break

                if best_alternative_day:
                    suggestions.append({
                        "type": "move_day",
                        "title": f"Move to Day {best_alternative_day['day_number']} ({best_alternative_day['condition']})",
                        "description": f"Day {best_alternative_day['day_number']} ({best_alternative_day['date']}) has clear weather ({best_alternative_day['temp_max']}°C, 0mm rain). Moving this activity ensures a sunny outdoor experience.",
                        "target_day_number": best_alternative_day['day_number'],
                        "target_day_date": best_alternative_day['date'],
                        "badge": "Recommended Move",
                        "action_label": f"Move to Day {best_alternative_day['day_number']}"
                    })

                # Suggestion Option 2: Swap with an indoor cultural/culinary/museum alternative in the same city
                available_indoor = []
                if cid and cid in catalog_activities_by_city:
                    for ca in catalog_activities_by_city[cid]:
                        if not cls.is_outdoor_activity(ca.get('category', ''), ca.get('name', ''), ca.get('description', '')):
                            if ca.get('name') != act.get('name'):
                                available_indoor.append(ca)

                if available_indoor:
                    # Pick the top rated indoor activity
                    top_indoor = available_indoor[0]
                    suggestions.append({
                        "type": "swap_indoor",
                        "title": f"Replace with {top_indoor['name']} (Indoor)",
                        "description": f"Switch this outdoor plan with {top_indoor['name']} ({top_indoor.get('category', 'cultural').capitalize()}). Perfect indoor attraction that avoids weather disruptions entirely.",
                        "substitute_activity": top_indoor,
                        "badge": "Indoor Alternative",
                        "action_label": f"Swap with {top_indoor['name'][:22]}..."
                    })

            evaluated_activities.append({
                **act,
                "day_date": act_date_str,
                "weather_forecast": day_fc,
                "risk_analysis": risk,
                "suggestions": suggestions
            })

        # Calculate trip weather score
        total_acts = len(activities)
        if total_acts == 0:
            weather_health_score = 100
        else:
            weather_health_score = max(20, int(100 - (high_risk_count * 25 + mod_risk_count * 10)))

        return {
            "trip_id": trip_dict.get('id'),
            "weather_health_score": weather_health_score,
            "total_activities": total_acts,
            "high_risk_count": high_risk_count,
            "moderate_risk_count": mod_risk_count,
            "safe_count": safe_count,
            "city_forecasts": city_forecasts,
            "evaluated_activities": evaluated_activities
        }
