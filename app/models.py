import os

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import and_

from datetime import datetime, timedelta, timezone, date
import ephem
from scipy.signal import find_peaks
from astropy.timeseries import LombScargle
import pandas as pd

from app.period.find_period import find_period
from app.star_util import t2phases, phase2str
from flask import current_app

from spacetrack import SpaceTrackClient
from skyfield.iokit import parse_tle_file
from skyfield.api import load
from io import BytesIO


db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

    site_name = db.Column(db.String(80), nullable=False)
    site_lat = db.Column(db.Float, nullable=False)
    site_lon = db.Column(db.Float, nullable=False)
    site_elev = db.Column(db.Float, nullable=False)

    eb_access = db.Column(db.Boolean, nullable=False, default=False)
    sat_access = db.Column(db.Boolean, nullable=False, default=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    # https://stackoverflow.com/questions/33705697/alembic-integrityerror-column-contains-null-values-when-adding-non-nullable

    @classmethod
    def get_all(cls):
        """
        Return all Users
        """
        users = db.session.query(cls).order_by(cls.id).all()
        return users

    @classmethod
    def get_all_sites(cls):
        """
        Return all Sites of all Users
        Return: list where all site are represented as dits
            {"name": name, "lat": lat, "lon": lon, "elev": elev}
        """
        site_names, site_lats, site_lons, site_elevs = [], [], [], []
        for user in cls.get_all():
            site_names.append(user.site_name)
            site_lats.append(user.site_lat)
            site_lons.append(user.site_lon)
            site_elevs.append(user.site_elev)

        sites_data = [
            {"name": name, "lat": lat, "lon": lon, "elev": elev}
            for name, lat, lon, elev in zip(site_names, site_lats, site_lons, site_elevs)
        ]
        return sites_data


class Star(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    star_name = db.Column(db.String(30), nullable=False, unique=True)
    ra = db.Column(db.String(15), nullable=False)
    dec = db.Column(db.String(15), nullable=False)
    mag = db.Column(db.Float, nullable=False)
    period = db.Column(db.Float, nullable=False)
    epoch = db.Column(db.Float, nullable=False)
    n_lc_TESS = db.Column(db.Integer, nullable=False)
    publications = db.Column(db.Integer, nullable=True)
    observations = db.relationship('Observation', backref='star', cascade='all, delete, delete-orphan')
    done = db.Column(db.Boolean, nullable=False, default=False)

    def add_obs(self, start_date, end_date):
        obs = Observation(start_date=start_date, end_date=end_date, star_id=self.id)
        db.session.add(obs)
        db.session.commit()

    @classmethod
    def return_all(cls):
        """
        Return all Stars
        """
        stars = db.session.query(cls).order_by(cls.done).all()
        return stars

    @classmethod
    def delete_by_id(cls, id):
        star = db.session.query(cls).filter_by(id=id).first()
        db.session.delete(star)
        db.session.commit()

    @classmethod
    def get_by_id(cls, id):
        star = db.session.query(cls).filter_by(id=id).first()
        return star

    def rise(self, user, get_timestamp=False):
        rise, _, _ = self.rise_pass_sdate(user)
        if get_timestamp:
            if rise == "alw up":
                return 0  # return smallest possible value
            return datetime.strptime(rise, "%Y-%m-%d %H:%M:%S").timestamp()
        return rise

    def pas(self, user, get_timestamp=False):
        _, pas, _ = self.rise_pass_sdate(user)
        if get_timestamp:
            if pas == "alw up":
                return 9.9e10  # return biggest value
            return datetime.strptime(pas, "%Y-%m-%d %H:%M:%S").timestamp()
        return pas

    def rise_pass_sdate(self, user):
        """
        Args:
            user: user info -> lat, lon, alt

        Returns:
            risetime: String
            passtime: String
            sort_date: Timestamp (Float)
        """
        site = ephem.Observer()
        today = datetime.today()
        site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
        site.lat = str(user.site_lat)  # "48.63" #loc.lat
        site.lon = str(user.site_lon)  # "22.33" #loc.lon
        site.horizon = '25'

        obj = ephem.FixedBody()
        obj.name = self.star_name
        obj._ra = ephem.hours(self.ra.replace("h", ":").replace("m", ":")[:-1])
        obj._dec = ephem.degrees(self.dec.replace("d", ":").replace("m", ":")[:-1])
        obj.compute(site)

        try:
            rise = site.previous_rising(obj)
            pas = site.next_setting(obj)
            rise_txt = str(rise).replace("/", "-")
            pass_txt = str(pas).replace("/", "-")
            sort_date = datetime.strptime(rise_txt, "%Y-%m-%d %H:%M:%S").timestamp()
        except ephem.AlwaysUpError:
            rise_txt = "alw up"
            pass_txt = "alw up"
            sort_date = (datetime.now() + timedelta(days=10)).timestamp()

        return rise_txt, pass_txt, sort_date


class Observation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Float)  # JD
    end_date = db.Column(db.Float)  # JD
    star_id = db.Column(db.Integer, db.ForeignKey('star.id'))

    def __repr__(self):
        return f'<"{self.start_date}:{self.end_date}">'

    def date0(self):
        """
        JD to python datetime and to Str
        Returns:
            Date: String
        """
        dt_offset = 2400000.500  # 1858-11-17
        dt = datetime(1858, 11, 17, tzinfo=timezone.utc) + timedelta(self.start_date - dt_offset)
        return dt.date().strftime("%Y-%m-%d")

    def phase_st(self):
        star = Star.get_by_id(self.star_id)
        return t2phases([self.start_date], star.period, star.epoch)[0]

    def phase_end(self):
        star = Star.get_by_id(self.star_id)
        return t2phases([self.end_date], star.period, star.epoch)[0]

    def asterix(self):
        star = Star.get_by_id(self.star_id)
        d_time = self.end_date - self.start_date
        if d_time >= star.period:
            return "[" + "*" * 50 + "]"
        else:
            return phase2str([self.phase_st(), self.phase_end()])


class Satellite(db.Model):
    """ Additional clas to lightcurve class"""
    id = db.Column(db.Integer, primary_key=True)
    norad = db.Column(db.Integer, nullable=False)
    cospar = db.Column(db.String(15), nullable=False)
    name = db.Column(db.String(35), nullable=False)
    updated = db.Column(db.DateTime, nullable=True)
    # lcs = db.relationship('Lightcurve', backref='satellite', cascade='all, delete, delete-orphan')

    @classmethod
    def count_sat(cls, start=None, stop=None):
        q = db.session.query(cls).order_by(cls.norad)
        q = q.slice(start, stop)
        # if limit:
        #     q = q.limit(limit)
        # if offset:
        #     q = q.offset(offset * limit)
        sats = q.all()
        num = q.count()
        # num = db.session.query(cls).order_by(cls.norad).count()
        return sats, num

    @classmethod
    def search_sat(cls, search_string, start=None, stop=None):
        data = db.session.query(cls).filter(
                                            (db.func.lower(cls.name).ilike(search_string.lower())) |
                                            (cls.norad.ilike(search_string)) |
                                            (cls.cospar.ilike(search_string))
        )

        data = data.slice(start, stop)
        sats = data.all()
        num = data.count()
        return sats, num

    @classmethod
    def get_by_id(cls, id):
        """
        Return all Satellites
        """
        sat = db.session.query(cls).filter_by(id=id).first()
        return sat

    @classmethod
    def get_all(cls):
        """
        Return all Satellites
        """
        sats = db.session.query(cls).order_by(cls.norad).all()
        return sats

    @classmethod
    def get_by_norad(cls, norad):
        """
        Return all Satellites with defined norad number
        """
        sat = db.session.query(cls).filter_by(norad=norad).first()
        return sat

    @classmethod
    def get_by_cospar(cls, cospar):
        """
        Return all Satellites with defined COSPAR number
        """
        sat = db.session.query(cls).filter_by(cospar=cospar).first()
        return sat

    @classmethod
    def get_by_name(cls, name):
        """
        Return all Satellites with defined name
        """
        # sat = db.session.query(cls).filter_by(name=name).all()
        sats = db.session.query(cls).filter(db.func.lower(cls.name).ilike(f'%{name.replace(" ", "%")}%'.lower())).all()
        return sats

    @classmethod
    def clear_empty_records(cls):
        """
        Search Satellites without LCs and delete it from DB
        return: list of deleted satellites, or empty list
        """
        deleted = []
        sats = db.session.query(cls).order_by(cls.norad).all()
        for sat in sats:
            # print(f"{sat.norad} \n {sat.get_lcs()} \n {not sat.get_lcs()}")
            # if not sat.get_lcs():
            if sat.count_lcs() == 0:
                # delete satellite
                # print(f"Delete sat_rec with NORAD={sat.norad}")
                db.session.delete(sat)
                db.session.commit()
                deleted.append(sat.norad)
        return deleted

    def get_lcs(self):
        lcs = db.session.query(Lightcurve).filter(Lightcurve.sat.has(norad=self.norad)).all()
        return lcs

    def count_lcs(self):
        n = db.session.query(Lightcurve).filter(Lightcurve.sat.has(norad=self.norad)).count()
        return n

    def get_last_lc_time(self):
        qry = db.session.query(Lightcurve).filter(Lightcurve.sat.has(norad=self.norad))
        lc = qry.order_by(Lightcurve.ut_start.desc()).first()
        return lc.ut_start

    def update_updated(self):
        self.updated = self.get_last_lc_time()
        db.session.commit()


class Lightcurve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # sat_id = db.Column(db.Integer, db.ForeignKey('satellite.id'))

    sat_id = db.Column(db.Integer, db.ForeignKey('satellite.id'))
    sat = db.relationship('Satellite',
                          backref=db.backref('lightcurve', lazy='dynamic'))
    #  https://stackoverflow.com/questions/30142881/many-to-one-flask-sqlalchemy-rendering

    tle = db.Column(db.Text)  # TLE strings 0,1,2 with \n
    ut_start = db.Column(db.DateTime, nullable=False)
    ut_end = db.Column(db.DateTime, nullable=False)
    dt = db.Column(db.Float, nullable=False)
    band = db.Column(db.String(5), nullable=False)

    date_time = db.Column(db.PickleType, nullable=False)

    flux = db.Column(db.PickleType, nullable=False)
    flux_err = db.Column(db.PickleType, nullable=True)
    mag = db.Column(db.PickleType, nullable=False)
    mag_err = db.Column(db.PickleType, nullable=True)

    az = db.Column(db.PickleType, nullable=True)
    el = db.Column(db.PickleType, nullable=True)
    rg = db.Column(db.PickleType, nullable=True)

    site = db.Column(db.String(50), nullable=True)
    lsp_period = db.Column(db.Float, nullable=True)

    @classmethod
    def get_by_lc_start(cls, norad, ut_start, bands=False):
        """
        Return all LC with start_time and NORAD
        """
        # https://stackoverflow.com/questions/8561470/sqlalchemy-filtering-by-relationship-attribute
        # cls.sat.has(norad=norad),
        lcs = db.session.query(cls).filter_by(ut_start=ut_start).filter(cls.sat.has(norad=norad)).all()
        if bands:
            bands = [lc.band for lc in lcs]
            return lcs, bands
        else:
            return lcs

        # return lc

    @classmethod
    def report_lcs(cls, date_from, date_to):
        # start_date = date(year, month, 1)
        # end_date = date(year, month + 1, 1) - timedelta(days=1)

        lcs = db.session.query(cls).filter(
            and_(cls.ut_start >= date_from,
                 cls.ut_start <= date_to)
        )
        return lcs.all()

    @classmethod
    def get_by_id(cls, id):
        lc = db.session.query(cls).filter_by(id=id).first()
        return lc

    @classmethod
    def get_synch_lc(cls, id, diff_in_sec):
        lc = db.session.query(cls).filter_by(id=id).first()
        lcs = db.session.query(cls).filter_by(sat_id=lc.sat_id)
        # print(lcs)
        lcs2 = [x for x in lcs if abs((x.ut_start-lc.ut_start).total_seconds()) < diff_in_sec ]
        return lcs2

    @classmethod
    def get_all(cls):
        """
        Return all Lightcurves
        """
        return db.session.query(cls).order_by(cls.id).all()

    def detect_period(self):
        if len(self.mag) < 100:
            return -1
        d = {'date': self.date_time, 'value': self.mag * -1}
        df = pd.DataFrame(data=d)
        try:
            res = find_period(df,
                              tol_norm_diff=10 ** (-3),
                              number_steps=50000,
                              minimum_number_of_relevant_shifts=2,
                              minimum_number_of_datapoints_for_correlation_test=100,
                              minimum_ratio_of_datapoints_for_shift_autocorrelation=0.003,
                              consider_only_significant_correlation=False,
                              level_of_significance_for_pearson=1e-7,
                              )
        except Exception as e:
            print("Could not detect period due to {}".format(e))
            return -1

        if res[-1] > 0.3:
            return res[0] * 60
        else:
            return -1

    def calc_period(self, detected_period=-1):
        lctime = self.date_time

        lctime = [x.timestamp() for x in lctime]

        # try to detect Period with find_period function and use +/-0.2 boundaries
        det_p = detected_period
        if det_p != -1:
            min_p = det_p - (0.2 * det_p)
            max_freq = 1 / min_p

            max_p = det_p + (0.2 * det_p)
            min_freq = 1 / max_p
        else:  # if period not detected use clear LS method and wide boundaries

            if self.dt < 1:
                max_freq = 0.83  # 1.2 sec
            else:
                max_freq = 1 / (2 * self.dt)

            min_freq = 1 / ((lctime[-1] - lctime[0]) / 2)

        if self.mag_err is not None:
            ls = LombScargle(lctime, self.mag, self.mag_err)
        else:
            ls = LombScargle(lctime, self.mag)

        frequency, power = ls.autopower(
            # nyquist_factor=0.5,
            minimum_frequency=min_freq,
            maximum_frequency=max_freq,
            samples_per_peak=30,
            normalization='standard')

        periods = 1.0 / frequency

        probabilities = [0.0001]  # 0.01 %
        fap = ls.false_alarm_level(probabilities)
        peaks, _ = find_peaks(power, height=fap[0])

        if not peaks.any():
            self.lsp_period = None
        else:
            zipped_lists = zip(power[peaks], periods[peaks])
            sorted_pairs = sorted(zipped_lists, reverse=True)

            # Return period with higher power
            self.lsp_period = sorted_pairs[0][1]

        db.session.commit()
        db.session.refresh(self)


class SatForView(db.Model):
    """ Class for sat view section. Not connected to other classes """
    __tablename__ = 'sat_for_view'
    id = db.Column(db.Integer, primary_key=True)
    norad = db.Column(db.Integer, nullable=False, unique=True)
    cospar = db.Column(db.String(15), nullable=False, unique=True)
    name = db.Column(db.String(35), nullable=False, default='')
    priority = db.Column(db.Integer, nullable=False, default=0)
    tle = db.Column(db.Text)

    @classmethod
    def get_all(cls):
        """
        Return all Sats for View
        """
        sats = db.session.query(cls).order_by(cls.id).all()
        return sats

    def get_tle(self, t=None):
        if t is None:
            t_st = 'now'
        else:
            t_st = t.utc_datetime().strftime("%Y-%m-%d")

        try:
            username = os.getenv('ST_USERNAME')
            password = os.getenv('ST_PASSWORD')
            st = SpaceTrackClient(username, password)
            # data = st.tle_latest(norad_cat_id=[self.norad], ordinal=1, epoch='>now-30', format='3le')
            data = st.tle(norad_cat_id=[self.norad], epoch=f'<={t_st}',  orderby='epoch desc', limit=1, format='3le')
            if data:
                self.tle = data
                db.session.commit()
            else:
                return False

        except Exception as e:
            current_app.logger.error(f" {e}, {e.args}\nCant read SpaceTrack username and password")
            return False

        return True

    def get_tle_epoch(self):
        if self.tle == '':
            return 999
        else:
            f = BytesIO(str.encode(self.tle))
            ts = load.timescale()
            sat = list(parse_tle_file(f, ts))
            sat = sat[0]
            return sat.epoch

    def calc_passes(self, site, t1, t2, min_h=20):
        # if TLE are 3 days old then get new TLE
        if self.tle == '' or abs(self.get_tle_epoch() - t1) > 3:
            self.get_tle(t1)

        # Calc Passes
        ts = load.timescale()
        eph = load('de421.bsp')
        earth = eph['Earth']
        moon = eph['Moon']
        f = BytesIO(str.encode(self.tle))
        sat = list(parse_tle_file(f, ts))
        sat = sat[0]
        if self.name == '' or self.cospar == '':
            self.name = sat.name
            self.cospar = sat.model.intldesg
            db.session.commit()
        passes = []

        t, events = sat.find_events(site, t1, t2, altitude_degrees=min_h)
        te = [[ti, event] for ti, event in zip(t, events)]
        # *0 — rise, 1 - culm, 3 - sets

        # Moon AltAz
        m_site = earth + site
        m_alt, m_az, _ = m_site.at(t1).observe(moon).apparent().altaz()
        # print(m_az.degrees, m_alt.degrees)

        if te: # if there are some transits
            # first event should be RISE
            while te[0][1] != 0:
                current_app.logger.warning(f"Deleting event {te.pop(0)} for satellite {sat.model.satnum}")

            t, events = zip(*te)

            t_st = [ti for ti, event in zip(t, events) if event == 0]
            t_end = [ti for ti, event in zip(t, events) if event == 2]
            for tst, tend in zip(t_st, t_end):
                times = ts.linspace(t0=tst, t1=tend, num=300)
                # for t in times:
                difference = sat - site
                topocentric = difference.at(times)
                alt, az, distance = topocentric.altaz()
                sunlit = sat.at(times).is_sunlit(eph)
                sunl = sunlit.tolist()
                sunl = [int(z) for z in sunl]

                if any(sunlit):  # if at least one point is at sunlight add RSO pass to list
                    pas = {'norad': sat.model.satnum,
                           'name': sat.name,
                           'priority': int(self.priority),
                           'ts': tst,
                           'te': tend,
                           "alt": alt.degrees.tolist(),
                           'az': az.degrees.tolist(),
                           'distance': distance.km.tolist(),
                           'sunlighted': sunl,
                           'moon':[m_alt.degrees, m_az.degrees]
                           }
                    passes.append(pas)
        return passes