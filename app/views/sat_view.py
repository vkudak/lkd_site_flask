import os
import sys

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
import datetime

from app import cache
from app.models import Satellite, db, Lightcurve
from app.sat_utils import plot_lc_bokeh, process_lc_file, lsp_plot_bokeh, plot_lc_multi_bokeh, plot_phased_lc, \
    lc_to_file, plot_periods_bokeh

sat_view_bp = Blueprint('sat_view', __name__)
basedir = os.path.abspath(os.path.dirname(__file__))


@sat_view_bp.route('/sat_view.html', methods=["POST", "GET"])
def sat_pas_test():
    """
    TEST
    """
    from spacetrack import SpaceTrackClient
    from skyfield.earthlib import refraction
    from skyfield import almanac
    from skyfield.units import Angle
    from skyfield.api import N, S, E, W, load, wgs84, utc, EarthSatellite
    from datetime import datetime, timedelta
    from skyfield.iokit import parse_tle_file
    from io import BytesIO

    site = wgs84.latlon(48.5635505, 22.453751, 231)
    ts = load.timescale()
    # eph = load('de421.bsp')

    sat_list = [22076, 16908]

    st = SpaceTrackClient('labLKD', 'lablkdSpace2013')
    tle = st.tle_latest(norad_cat_id=sat_list, ordinal=1, epoch='>now-30', format='3le')
    f = BytesIO(str.encode(tle))
    sats = list(parse_tle_file(f, ts))


    t0 = ts.utc(2025, 1, 18)
    t1 = ts.utc(2025, 1, 19)
    # sat= EarthSatellite(tle[1], tle[2], tle[0], ts)

    passes = []

    for sat in sats:
        t, events = sat.find_events(site, t0, t1, altitude_degrees=20.0)
        te = [[ti, event] for ti, event in zip(t, events)]

        # *0 — Satellite rose above
        # * 1 — Satellite culminated
        # * 2 — Satellite fell below

        # first event should be RISE
        while te[0][1] != 0:
            print(f"Deleting event {te.pop(0)} for satellite {sat.model.satnum}")

        t, events = zip(*te)

        t_st = [ti for ti, event in zip(t, events) if event == 0 ]
        t_end = [ti for ti, event in zip(t, events) if event == 2 ]
        for tst, tend in zip(t_st, t_end):
            times = ts.linspace(t0=tst, t1=tend, num=100)
            # for t in times:
            difference = sat - site
            topocentric = difference.at(times)
            alt, az, distance = topocentric.altaz()
            pas = {'norad': sat.model.satnum, 'ts': tst, 'te': tend , "alt": alt.degrees, 'az': az.degrees, 'distance': distance.km}
            passes.append(pas)

        # for ti, event in zip(t, events):
        #     # name = event_names[event]
        #     print(sat.model.satnum, ti.utc_strftime('%Y %m %d %H:%M:%S'), event)

    # for pas in passes[0]:
    #     print(pas)


    sat_pas = {
        "time": ["2025-01-18T10:00:00", "2025-01-18T10:10:00", "2025-01-18T10:20:00",
                 "2025-01-18T10:30:00", "2025-01-18T10:40:00", "2025-01-18T10:50:00",
                 "2025-01-18T11:00:00", "2025-01-18T11:10:00", "2025-01-18T11:20:00", "2025-01-18T11:30:00"],
        "az": [0, 10, 20, 25, 30, 35, 40, 50, 60, 70 ],
        "alt": [30, 40, 50, 60, 70, 60, 50, 40, 35, 30]
    }

    return render_template('sat_view.html', data=sat_pas)