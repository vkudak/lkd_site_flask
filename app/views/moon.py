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


def get_planet_elevations(days=16):
    observer = ephem.Observer()
    observer.lat = str(UZHGOROD_LAT)
    observer.lon = str(UZHGOROD_LON)

    # Set time zone offset for Kyiv (UTC+3)
    kiev_tz = pytz.timezone('Europe/Kiev')
    today = datetime.now(tz=kiev_tz)
    planets_elevations = []
    for i in range(days):
        date = datetime.now(tz=kiev_tz) + timedelta(days=i)

        # Set the observer's date to 20:00 local time (UTC+3)
        observer.date = date.replace(hour=20, minute=0, second=0, microsecond=0)
        # Get elevation for Jupiter, Saturn, and Mars
        jupiter = ephem.Jupiter(observer)
        saturn = ephem.Saturn(observer)
        mars = ephem.Mars(observer)
        # Convert elevation from radians to degrees
        jupiter_elevation_degrees = jupiter.alt * (180.0 / 3.14159265)  # Convert radians to degrees
        saturn_elevation_degrees = saturn.alt * (180.0 / 3.14159265)
        mars_elevation_degrees = mars.alt * (180.0 / 3.14159265)
        planets_elevations.append({
            'date': date.strftime('%Y-%m-%d'),
            'jupiter_elevation': jupiter_elevation_degrees,  # Elevation in degrees
            'saturn_elevation': saturn_elevation_degrees,    # Elevation in degrees
            'mars_elevation': mars_elevation_degrees
        })
    return planets_elevations


# === Розрахунок фаз Місяця ===
def get_moon_phases(days=30):
    today = datetime.now()

    phases = []
    for i in range(days):
        moonrise_time, moonset_time, phase = get_moon_rise_set(UZHGOROD_LAT, UZHGOROD_LON, today + timedelta(days=i))

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

        phases.append({
            'day': today.date,
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
    planet_elevations = get_planet_elevations(days)  # Get planet elevations

    # Combine moon phases with weather data
    moon_calendar = {}
    for i in range(days):
        date_str = (datetime.utcnow() + timedelta(days=i)).strftime('%Y-%m-%d')

        # Check if day index is greater than available weather data
        if i < len(weather_data):  # If we have weather data for this day
            weather = weather_data[i]
        else:  # Use None for weather if day index exceeds available data
            weather = {'cloudcover': 'No data'}  # Use a string to indicate no data

        # Add planet elevations
        if i < len(planet_elevations):
            planets = planet_elevations[i]
        else:
            planets = {'jupiter_elevation': None, 'saturn_elevation': None, 'mars_elevation': None}

        moon_calendar[date_str] = {
            'day': moon_phases[i]['day'],
            'phase': moon_phases[i],
            'weather': weather,
            'jupiter_elevation': planets['jupiter_elevation'],  # in radians
            'saturn_elevation': planets['saturn_elevation'],  # in radians
            'mars_elevation': planets['mars_elevation']  # in radians
        }

    # print(moon_calendar)

    # return render_template("moon_phase/moon.html", moon_phases=moon_phases, weather=weather)
    return render_template("moon_phase/moon.html", moon_calendar=moon_calendar, elevation_unit='radians')

def get_moon_rise_set(latitude, longitude, calc_datetime):
    """
    Function calculates rise and set of the Moon for a given latitude and longitude and date
    Args:
        latitude: latitude of observation site
        longitude: latitude of observation site
        calc_datetime: datetime object to calculate rise and set

    Returns:
        rise, set, phase: set of values (str, str, float)
    """
    # Використовуємо pytz для визначення часової зони
    kiev_tz = pytz.timezone('Europe/Kiev')
    calc_datetime = calc_datetime.replace(hour=12, minute=00)
    # Створюємо дату, яка усвідомлює часову зону (aware datetime)
    date = kiev_tz.localize(calc_datetime)

    # ---- СКРИПТ ----
    obs = ephem.Observer()
    obs.lat = latitude
    obs.lon = longitude
    # висоту можна задати як obs.elev = 180 (метрів)

    # У PyEphem усі дати в UTC, тому передаємо 'naive' datetime
    # obs.date = date.replace(tzinfo=None) # або .astimezone(pytz.utc).replace(tzinfo=None)
    # Краще зробити обчислення в UTC
    obs.date = date.astimezone(pytz.utc)

    moon = ephem.Moon()

    # Час сходу та заходу
    moon_prev_rise_utc = obs.previous_rising(moon)
    moon_rise_utc = obs.next_rising(moon)
    moon_set_utc = obs.next_setting(moon)

    # Переводимо UTC дати в 'aware' локальний час
    moon_prev_rise_local = pytz.utc.localize(moon_prev_rise_utc.datetime()).astimezone(kiev_tz)
    moon_rise_local = pytz.utc.localize(moon_rise_utc.datetime()).astimezone(kiev_tz)
    moon_set_local = pytz.utc.localize(moon_set_utc.datetime()).astimezone(kiev_tz)

    times = {'rise': [moon_rise_local, abs(date - moon_rise_local)],
             'prev_rise': [moon_prev_rise_local, abs(date - moon_prev_rise_local)],
             'set': [moon_set_local, abs(date - moon_set_local)]
             }

    # Sort by the second element (index 1) of the value lists [1][1]
    sorted_times_items = sorted(times.items(), key=lambda item: item[1][1])

    # Знаходимо ключ найменш близького значення (третього елемента)
    farthest_key = sorted_times_items[2][0]

    # Визначаємо, який ключ потрібно видалити, згідно з новим правилом
    if farthest_key == 'set':
        key_to_remove = sorted_times_items[1][0]
    else:
        key_to_remove = farthest_key

    times[key_to_remove] = None

    phase = moon.phase

    if times['rise'] is not None:
        return times['rise'][0].strftime('%H:%M:%S'), times['set'][0].strftime('%H:%M:%S'), phase
    else:
        return times['prev_rise'][0].strftime('%H:%M:%S'), times['set'][0].strftime('%H:%M:%S'), phase
