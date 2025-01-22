import os
import sys
from operator import itemgetter

import numpy as np
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, Response, \
    render_template_string
from flask import send_file
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from pycparser.c_ast import Default
from skyfield.timelib import Timescale
from wtforms import StringField, MultipleFileField, SubmitField, RadioField, IntegerField
from wtforms.fields.numeric import DecimalField, FloatField
from wtforms.validators import Length, DataRequired
from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired

from spacetrack import SpaceTrackClient
from skyfield.earthlib import refraction
from skyfield import almanac
from skyfield.units import Angle
from skyfield.api import N, S, E, W, load, wgs84, utc, EarthSatellite
from datetime import datetime, timedelta
from skyfield.iokit import parse_tle_file
from io import BytesIO

from app import cache
from app.models import Satellite, db, Lightcurve, SatForView, User
from app.sat_utils import plot_lc_bokeh, process_lc_file, lsp_plot_bokeh, plot_lc_multi_bokeh, plot_phased_lc, \
    lc_to_file, plot_periods_bokeh

sat_view_bp = Blueprint('sat_view', __name__)
basedir = os.path.abspath(os.path.dirname(__file__))


def calc_t_twilight(site, date=None, h_sun=-12):
    """
    Calculate twilight time according to h_sun
    site: observational site. Create by api.Topos(lat, lon, elevation_m=elv) or api.wgs84(lat, lon, elevation_m=elv)
    date: is date in str format 'YYYY-MM-DD'
    h_sun: elevation of Sun below horizon. Default is -12 degrees.
    """
    ts = load.timescale()
    eph = load('de421.bsp')
    observer = eph['Earth'] + site

    if date is None:
        now = datetime.now()
    else:
        now = datetime.strptime(date, '%Y-%m-%d')

    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=utc)
    next_midnight = midnight + timedelta(days=2)
    t0 = ts.from_datetime(midnight)
    t1 = ts.from_datetime(next_midnight)

    t_set, y = almanac.find_settings(observer, eph['Sun'], t0, t1, horizon_degrees=h_sun)
    t_rise, y = almanac.find_risings(observer, eph['Sun'], t0, t1, horizon_degrees=h_sun)
    return t_set[0], t_rise[1]


@sat_view_bp.route('/sat_pas/sat_view.html', methods=["POST", "GET"])
def sat_passes(): #site, date_start, sat_selected, min_sat_h):
    """
    Calculate passes for all selected satellites
    """
    if request.method == "POST":
        locations = User.get_all_sites()
        loc_res = [(locations.index(loc) + 1, loc) for loc in locations]

        location_id = request.form.get('location')
        date_start = request.form.get('observation_date')
        min_sat_h = request.form.get('elevation')
        selected_sat = request.form.getlist('selected_satellites')

        my_loc = [loc[1] for loc in loc_res if loc[0] == int(location_id)]
        if my_loc:
            my_loc = my_loc[0]
            site = wgs84.latlon(my_loc['lat'], my_loc['lon'], my_loc['elev'])
        else:
            # Default site
            site = wgs84.latlon(48.5635505, 22.453751, 231)

        # site = wgs84.latlon(48.5635505, 22.453751, 231)
        # site = wgs84.latlon(my_loc['lat'], my_loc['lon'], my_loc['elev'])
        t0, t1 = calc_t_twilight(site, date_start)

        sats = SatForView.get_all()
        # leave only selecter Satellites
        sats = [sat for sat in sats if str(sat.norad) in selected_sat]

        passes = []
        for sat in sats:
            sp = sat.calc_passes(site, t0, t1, min_h=int(min_sat_h))
            passes.extend(sp)

        # # sorting
        # # https://stackoverflow.com/questions/62380562/sort-list-of-dicts-by-two-keys
        # passes = sorted(passes, key=lambda k: (k['priority'], -k['ts'].tdb ), reverse=True)

        return render_template('sat_pas/sat_view.html',
                               passes=passes,
                               site_name=my_loc['name'],
                               date_start=date_start
                               )
    else:
        # return render_template_string('PageNotFound {{ errorCode }}', errorCode='404'), 404
        return render_template_string('This entry goes not suppose to have respond for GET request'), 404


@sat_view_bp.route('/sat_pas/sat_select.html', methods=['GET', 'POST'])
@login_required
def sat_select():
    if current_user.sat_access:
        form = SatelliteTrackingForm()
        locations = User.get_all_sites()
        loc_res = [(locations.index(loc)+1, loc) for loc in locations]
        form.location.choices = [(locations.index(loc), loc['name']) for loc in locations]

        # if method = POST
        if form.validate_on_submit():
            # selected_satellites = request.form.getlist('selected_satellites')
            # observation_date = form.observation_date.data
            # elevation = form.elevation.data
            # location_id = form.location.data
        #     # Логіка обробки
            request.loc_res = loc_res
            return redirect(url_for('sat_view.sat_passes'))

        satellites = SatForView.query.all()

        today = datetime.now().strftime('%Y-%m-%d')  # Сьогоднішня дата
        return render_template('sat_pas/sat_select.html',
                               form=form,
                               satellites=satellites,
                               locations=loc_res,
                               today=today
                               )
    else:
        flash("User has no rights for Satellite section. Contact admin please.")
        return redirect(url_for('home.index'))


@sat_view_bp.route('/sat_pas/delete_satellite/<int:norad>', methods=['POST'])
def delete_satellite(norad):
    """
    Delete Sat_View from DataBase by norad number
    norad: int
    """
    satellite = SatForView.query.filter_by(norad=norad).first()
    if satellite:
        db.session.delete(satellite)
        db.session.commit()
        flash(f"Satellite with NORAD ID {norad} deleted successfully.", "success")
    else:
        flash(f"Satellite with NORAD ID {norad} not found.", "error")
    return redirect(url_for('sat_view.sat_select'))


@sat_view_bp.route('/sat_pas/add_satellite', methods=['POST'])
def add_satellite():
    """
    Add Sat_View to DataBase by Norad number and Priority
    """
    norad = request.form['norad']
    priority = request.form['priority']

    new_satellite = SatForView(norad=int(norad), cospar='', name='', priority=int(priority))
    db.session.add(new_satellite)
    db.session.commit()
    flash(f"Satellite {norad} added successfully.", "success")
    return redirect(url_for('sat_view.sat_select'))


class SatelliteTrackingForm(FlaskForm):
    observation_date = DateField('Observation Date', format='%Y-%m-%d', validators=[DataRequired()])
    elevation = IntegerField('Minimum Elevation (degrees)', validators=[DataRequired()])
    location = SelectField('Observation Location', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Submit')
