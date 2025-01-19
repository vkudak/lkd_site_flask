import os
import sys
from operator import itemgetter

import numpy as np
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, Response
from flask import send_file
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from pycparser.c_ast import Default
from skyfield.timelib import Timescale
from wtforms import StringField, MultipleFileField, SubmitField, RadioField, IntegerField
from wtforms.fields.numeric import DecimalField, FloatField
from wtforms.validators import Length, DataRequired
# import datetime

from spacetrack import SpaceTrackClient
from skyfield.earthlib import refraction
from skyfield import almanac
from skyfield.units import Angle
from skyfield.api import N, S, E, W, load, wgs84, utc, EarthSatellite
from datetime import datetime, timedelta
from skyfield.iokit import parse_tle_file
from io import BytesIO

from app import cache
from app.models import Satellite, db, Lightcurve
from app.sat_utils import plot_lc_bokeh, process_lc_file, lsp_plot_bokeh, plot_lc_multi_bokeh, plot_phased_lc, \
    lc_to_file, plot_periods_bokeh

sat_view_bp = Blueprint('sat_view', __name__)
basedir = os.path.abspath(os.path.dirname(__file__))


def calc_t_twilight(site, h_sun=-12):
    """
    Calculate twilight time according to h_sun
    site: observational site. Create by api.Topos(lat, lon, elevation_m=elv) or api.wgs84(lat, lon, elevation_m=elv)
    h_sun: elevation of Sun below horizon. Default is -12 degrees.
    """
    ts = load.timescale()
    eph = load('de421.bsp')
    observer = eph['Earth'] + site

    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=utc)
    next_midnight = midnight + timedelta(days=2)
    t0 = ts.from_datetime(midnight)
    t1 = ts.from_datetime(next_midnight)

    t_set, y = almanac.find_settings(observer, eph['Sun'], t0, t1, horizon_degrees=h_sun)
    t_rise, y = almanac.find_risings(observer, eph['Sun'], t0, t1, horizon_degrees=h_sun)
    return t_set[0], t_rise[1]


@sat_view_bp.route('/sat_pas/sat_view.html', methods=["POST", "GET"])
def sat_pas_test():
    """
    TEST
    """
    # TODO: make controls to select RSOs SITE & DATE on webpage

    site = wgs84.latlon(48.5635505, 22.453751, 231)
    ts = load.timescale()
    eph = load('de421.bsp')
    t0, t1 = calc_t_twilight(site)
    # print(t1.utc_datetime().strftime("%Y-%m-%d %H:%M:%S"), t2.utc_datetime().strftime("%Y-%m-%d %H:%M:%S"))


    sat_list = [22076, 16908, 25544]

    st = SpaceTrackClient('labLKD', 'lablkdSpace2013')
    tle = st.tle_latest(norad_cat_id=sat_list, ordinal=1, epoch='>now-30', format='3le')
    f = BytesIO(str.encode(tle))
    sats = list(parse_tle_file(f, ts))

    passes = []
    for sat in sats:
        t, events = sat.find_events(site, t0, t1, altitude_degrees=20.0)
        te = [[ti, event] for ti, event in zip(t, events)]

        # *0 — Satellite rose above
        # * 1 — Satellite culminated
        # * 2 — Satellite fell below

        # first event should be RISE
        while te[0][1] != 0:
            current_app.logger.warning(f"Deleting event {te.pop(0)} for satellite {sat.model.satnum}")

        t, events = zip(*te)

        t_st = [ti for ti, event in zip(t, events) if event == 0 ]
        t_end = [ti for ti, event in zip(t, events) if event == 2 ]
        for tst, tend in zip(t_st, t_end):
            times = ts.linspace(t0=tst, t1=tend, num=1000)
            # for t in times:
            difference = sat - site
            topocentric = difference.at(times)
            alt, az, distance = topocentric.altaz()
            sunlit = sat.at(times).is_sunlit(eph)

            if sat.model.satnum == 22076:
                prior = 3
            elif sat.model.satnum == 25544:
                prior = 1
            else:
                prior = 0

            if any(sunlit): # if at least one point is at sunlight add RSO pass to list
                pas = {'norad': sat.model.satnum,
                       'priority': prior,
                       'ts': tst, 'te': tend ,
                       "alt": alt.degrees.tolist(), 'az': az.degrees.tolist(),
                       'distance': distance.km.tolist(), 'sunlighted': sunlit.tolist()
                       }
                passes.append(pas)

    # https://stackoverflow.com/questions/62380562/sort-list-of-dicts-by-two-keys
    passes = sorted(passes, key=lambda k: (-k['ts'].tdb, k['priority']), reverse=True)

    return render_template('sat_pas/sat_view.html', passes=passes)