import os
from flask import Blueprint, render_template
from datetime import datetime, timedelta
import ephem
import pytz

import requests_cache
import openmeteo_requests
from retry_requests import retry


# bp = Blueprint('moon', __name__)

moon_bp = Blueprint('moon', __name__)
basedir = os.path.abspath(os.path.dirname(__file__))


UZHGOROD_LAT = '48.6239'
UZHGOROD_LON = '22.2950'
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


# Set up the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
# Function to get weather data
def get_weather_data(days=16):  # Set to 16 to match the API's limit
    params = {
        "latitude": UZHGOROD_LAT,
        "longitude": UZHGOROD_LON,
        "hourly": "cloud_cover",  # Use hourly data for cloud cover
        "timezone": "Europe/Kiev",
        "forecast_days": days,
    }
    # Call the Open-Meteo API
    responses = openmeteo.weather_api("https://api.open-meteo.com/v1/forecast", params=params)
    # Create a list to hold weather data
    weather_data = []
    # Ensure we have at least one response
    if responses:
        hourly = responses[0].Hourly()  # Get the first response
        hourly_cloud_cover = hourly.Variables(0).ValuesAsNumpy()  # Get cloud cover values
        # print(hourly_cloud_cover)
        # Get the specific time for each day (20:00 is the 20th hour)
        # Assuming the data is returned in the order per day
        # hours = hourly.Time()  # Time in seconds since epoch
        for i in range(days):
            # Find the index for 20:00 (8 PM) on each day
            # Each day has 24 hours of data, so for each day 'i', 20:00 would be at 'i*24 + 20'
            index = i * 24 + 20
            if index < len(hourly_cloud_cover):
                # Append the cloud cover for 20:00 to weather data
                weather_data.append({'cloudcover': hourly_cloud_cover[index]})
    return weather_data


# === Розрахунок фаз Місяця ===
def get_moon_phases(days=30):
    observer = ephem.Observer()
    observer.lat = UZHGOROD_LAT
    observer.lon = UZHGOROD_LON

    # Define Kiev timezone
    kiev_tz = pytz.timezone('Europe/Kiev')

    today = datetime.now(tz=kiev_tz)
    # print(today)

    phases = []
    for i in range(days):
        date = today.replace(hour=22, minute=00) + timedelta(days=i-1)

        # Set the observer's date to the current date in the loop
        observer.date = today.replace(hour=22, minute=00) + timedelta(days=i)

        moon = ephem.Moon(observer)

        # Calculate phase and times
        phase = moon.phase  # in percentage\
        moonrise = observer.next_rising(moon)
        moonset = observer.next_setting(moon)

        # Convert times to UTC
        moonrise_utc = moonrise.datetime()
        moonset_utc = moonset.datetime()
        # Localize to Kiev timezone
        moonrise_time = moonrise_utc.replace(tzinfo=pytz.utc).astimezone(kiev_tz).strftime('%H:%M:%S')
        moonset_time = moonset_utc.replace(tzinfo=pytz.utc).astimezone(kiev_tz).strftime('%H:%M:%S')

    # print(moonrise_time, moonset_time)
        # Determine phase name (simplified)
        if phase < 1:
            phase_name = 'New Moon'
        elif phase < 50:
            phase_name = 'Waxing Crescent'
        elif 49 <= phase < 51:
            phase_name = 'First Quarter'
        elif phase < 99:
            phase_name = 'Waxing Gibbous'
        elif phase >= 99:
            phase_name = 'Full Moon'
        elif 50 < phase < 99:
            phase_name = 'Waning Gibbous'
        elif 49 <= phase < 51:
            phase_name = 'Last Quarter'
        else:
            phase_name = 'Waning Crescent'

        # print(date.day, moonrise_time, moonset_time)
        phases.append({
            'day': date.day,
            'illumination': round(phase, 1),
            'phase': phase_name,
            'moonrise': moonrise_time,
            'moonset': moonset_time,
            # 'img': f"/static/moon/{phase_name.replace(' ', '').lower()}.png",
            'img': f"{phase_name.replace(' ', '_').lower()}.png"
        })
    return phases


@moon_bp.route('/moon_phase/moon.html', methods=["POST", "GET"])
def moon_view():
    days = 30  # Get data for the next 30 days
    moon_phases = get_moon_phases(days)
    weather_data = get_weather_data()
    # Combine moon phases with weather data
    moon_calendar = {}
    for i in range(days):
        date_str = (datetime.utcnow() + timedelta(days=i)).strftime('%Y-%m-%d')

        # Check if day index is greater than available weather data
        if i < len(weather_data):  # If we have weather data for this day
            weather = weather_data[i]
        else:  # Use None for weather if day index exceeds available data
            weather = {'cloudcover': 'No data'}  # Use a string to indicate no data

        moon_calendar[date_str] = {
            'day': moon_phases[i]['day'],
            'phase': moon_phases[i],
            'weather': weather
        }

    # print(moon_calendar)

    # return render_template("moon_phase/moon.html", moon_phases=moon_phases, weather=weather)
    return render_template("moon_phase/moon.html", moon_calendar=moon_calendar)