import os
import sys
import time
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


def space_track_callback(until):
    duration = int(round(until - time.monotonic()))
    current_app.logger.info('Sleeping for {:d} seconds.'.format(duration))


def filter_latest_tle(data):
    """
    Приймає список словників (JSON від Space-Track).
    Повертає список словників, де для кожного NORAD_CAT_ID
    залишено лише один запис з найновішою EPOCH.
    """
    # 1. Сортуємо весь список за EPOCH (від старіших до новіших)
    # Це гарантує, що при ітерації новіший запис замінить старий у словнику
    sorted_data = sorted(data, key=lambda x: x['EPOCH'])

    # 2. Використовуємо словник, де ключем є ID супутника
    temp_map = {}
    for record in sorted_data:
        norad_id = record['NORAD_CAT_ID']
        temp_map[norad_id] = record  # Останній (найсвіжіший) запис перезапише попередні

    # 3. Перетворюємо значення словника назад у список
    return list(temp_map.values())


def wait_for_safe_time():
    """
    Перевіряє час. Якщо ми в піковому періоді (:00-:05 або :30-:35),
    чекає до моменту безпечного запуску.
    """
    while True:
        now = datetime.now()
        minute = now.minute

        # Визначаємо небезпечні вікна
        is_busy_start = (0 <= minute <= 5)
        is_busy_middle = (30 <= minute <= 35)

        if is_busy_start or is_busy_middle:
            # Розраховуємо, скільки секунд залишилося до кінця "червоної зони"
            wait_minutes = 6 - minute if is_busy_start else 36 - minute
            current_app.logger.info(f"[{now.strftime('%H:%M:%S')}] Peak load time on Space-Track. Waiting {wait_minutes} minutes.")
            # print(f"[{now.strftime('%H:%M:%S')}] Peak load time on Space-Track. Waiting {wait_minutes} minutes.")
            flash(f"[{now.strftime('%H:%M:%S')}] Peak load time on Space-Track. Waiting {wait_minutes} minutes.")

            # Чекаємо 30 секунд перед наступною перевіркою, щоб не вантажити CPU
            time.sleep(30)
        else:
            # print(f"[{now.strftime('%H:%M:%S')}] Safe time. Stating query to space-track...")
            current_app.logger.info(f"[{now.strftime('%H:%M:%S')}] Safe time. Stating query to space-track...")
            break


def update_tle(old_tle, t2):
    if len(old_tle) == 0:
        return True
    try:
        username = os.getenv('ST_USERNAME')
        password = os.getenv('ST_PASSWORD')

        # Викликаємо очікування перед будь-яким зверненням до API
        wait_for_safe_time()

        st = SpaceTrackClient(username, password)
        st.callback = space_track_callback
        # t1 = t2 - timedelta(days=5)
        current_app.logger.info(f"Retrieving TLE for objects {old_tle}")
        # t1s = t1.utc_strftime("%Y-%m-%d")
        # t2s = t2.utc_strftime("%Y-%m-%d")
        t_limit = (t2 - timedelta(days=5)).utc_strftime("%Y-%m-%d %H:%M:%S")
        # data = st.gp(norad_cat_id=old_tle, epoch=f'{t1s}--{t2s}', orderby='epoch desc') # JSON

        data = st.gp(norad_cat_id=old_tle, epoch=f'>{t_limit}')  # JSON
        # Sort obtained data on our side, less load on space-track
        data = filter_latest_tle(data) # Маємо чистий список з унікальними ID

        for nor in old_tle:
            current_app.logger.info(f"Search TLE for object {nor}")
            tles = [tl for tl in data if tl['NORAD_CAT_ID']==str(nor)]
            if len(tles) >= 1:
                new_list = sorted(tles, key=lambda d: d['EPOCH'], reverse=True)
                sc = SatForView.get_by_norad(str(nor))
                sc.tle = new_list[0]['TLE_LINE0'] + '\n' + new_list[0]['TLE_LINE1'] + '\n' + new_list[0]['TLE_LINE2']
                db.session.commit()
                current_app.logger.info(f"TLE for object {nor} updated, TLE epoch {new_list[0]['EPOCH']}")
            else:
                current_app.logger.info(f"No TLE for object {nor}. Keeping old TLE.")
        return True

    except Exception as e:
        current_app.logger.error(f"Cant read TLE from SpaceTrack")
        current_app.logger.error(f" {e}, {e.args}")
        return False


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
        min_sun_h = request.form.get('sun_h')
        selected_sat = request.form.getlist('selected_satellites')

        # print(request.form)

        my_loc = [loc[1] for loc in loc_res if loc[0] == int(location_id)]
        if my_loc:
            my_loc = my_loc[0]
            site = wgs84.latlon(my_loc['lat'], my_loc['lon'], my_loc['elev'])
        else:
            # Default site
            site = wgs84.latlon(48.5635505, 22.453751, 231)

        # site = wgs84.latlon(48.5635505, 22.453751, 231)
        # site = wgs84.latlon(my_loc['lat'], my_loc['lon'], my_loc['elev'])
        t0, t1 = calc_t_twilight(site, date_start, h_sun=int(min_sun_h))

        sats = SatForView.get_all()
        # leave only selected Satellites
        sats = [sat for sat in sats if str(sat.norad) in selected_sat]

        old_tle = []
        for sat in sats:
            if sat.tle == '' or sat.tle is None:
                old_tle.append(sat.norad)
            else:
                # check TLE epoch
                f = BytesIO(str.encode(sat.tle))
                ts = load.timescale()
                m_sat = list(parse_tle_file(f, ts))
                if m_sat:
                    m_sat_epoch = m_sat[0].epoch
                    if abs(m_sat_epoch - t0) > 3:
                        old_tle.append(sat.norad)

        # Update all old TLEs
        if update_tle(old_tle, t0):
            passes = []
            for sat in sats:
                sp, mes = sat.calc_passes(site, t0, t1, min_h=int(min_sat_h))
                if mes:
                    flash(mes)
                passes.extend(sp)

            # # sorting
            # # https://stackoverflow.com/questions/62380562/sort-list-of-dicts-by-two-keys
            # passes = sorted(passes, key=lambda k: (k['priority'], -k['ts'].tdb ), reverse=True)

            return render_template('sat_pas/sat_view.html',
                                   passes=passes,
                                   site=my_loc,
                                   date_start=date_start)
        else:
            flash('Error in TLE download. See logs for more details.')
            return redirect(url_for('sat_view.sat_select'))
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

        today = datetime.now().strftime('%Y-%m-%d')  # Default date
        return render_template('sat_pas/sat_select.html',
                               form=form,
                               satellites=satellites,
                               locations=loc_res,
                               today=today
                               )
    else:
        flash("User has no rights for Satellite section. Contact admin please.")
        return redirect(url_for('home.index'))


@sat_view_bp.route('/sat_pas/delete_satellite/<string:norad>', methods=['POST'])
def delete_satellite(norad):
    """
    Delete Sat_View from DataBase by norad number
    norad: str
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
    cospar = request.form['cospar']
    priority = request.form['priority']

    # check if satellite exists
    if SatForView.query.filter_by(norad=norad).first() or SatForView.query.filter_by(cospar=cospar).first():
        flash(f"Satellite with NORAD={norad} or COSPAR={cospar} already exist.", "error")
        current_app.logger.error(f"Cant add sat. Satellite with NORAD={norad} or COSPAR={cospar} already exist.")
        return redirect(url_for('sat_view.sat_select'))

    new_satellite = SatForView(norad=norad, cospar=cospar, name='', priority=int(priority))
    db.session.add(new_satellite)
    db.session.commit()
    flash(f"Satellite {norad} added successfully.", "success")
    return redirect(url_for('sat_view.sat_select'))


class SatelliteTrackingForm(FlaskForm):
    observation_date = DateField('Observation Date', format='%Y-%m-%d', validators=[DataRequired()])
    elevation = IntegerField('Minimum Elevation (degrees)', validators=[DataRequired()])
    sun_h = IntegerField('Minimum Sun Elevation (degrees)', validators=[DataRequired()])
    location = SelectField('Observation Location', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Submit')
