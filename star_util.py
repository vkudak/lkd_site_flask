import csv
# import sys
import os
import matplotlib.pyplot as plt
import astropy.units as u
from astropy.coordinates import EarthLocation, SkyCoord, AltAz, Angle
from astropy.coordinates import get_sun, get_moon
from pytz import timezone
from astropy.time import Time
import ephem
# import ast
import numpy as np
from datetime import datetime
import time
from pylab import rcParams
import matplotlib.dates as mdates
from operator import itemgetter
rcParams['figure.figsize'] = 10, 6


def phase2str(ph):
    pstart = round(ph[0]*10)
    pend = round(ph[1]*10)
    s = "["
    scale = 5
    if pstart <= pend:
        xr = range(1, 10*scale+1)
        rever = False
    else:
        xr = range(10*scale, 1-1, -1)
        rever = True
    for i in xr:
        if rever:
            if pstart * scale >= i >= pend * scale:
                s += "*"
            else:
                s += "-"
        else:
            if pstart*scale <= i <= pend*scale:
                s += "*"
            else:
                s += "-"
    if rever:
        s = "[" + s[::-1][:-1] + "]"
    else:
        s = s[:-1] + "]"
    return s


def t2phases(dt, P0, E0):
    aph = []
    P0 = float(P0)
    E0 = 2400000 + float(E0)
    for x in dt:
        tm = Time(x)
        ph = np.mod(tm.jd - E0, P0) / float(P0)  # phase
        aph.append(ph)
    return aph


def read_stars(filename, gcvs_filename, user):
    stars = []
    site = ephem.Observer()
    today = datetime.today()
    site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
    site.lat = str(user.site_lat)  # "48.63" #loc.lat
    site.lon = str(user.site_lon)  # "22.33" #loc.lon
    # print("lat = ", site.lat)
    # print("lon = ", site.lon)
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row["Name"] = ' '.join(row["Name"].split())
            row["Epoch"] = row["Epoch"].strip()
            if row["Phase"].strip() != "":
                row["Phase"] = row["Phase"].strip()
                row["Phase"] = [tuple(x.split(":")) for x in row["Phase"].split(";")]
                row["Phase"] = [(x, y.strip('][').split(',')) for x, y in row["Phase"]]
                row["Phase"] = [(x, [float(z) for z in y]) for x,y in row["Phase"]]
                row["Phase"] = [(x, y, phase2str(y)) for x, y in row["Phase"]]
            else:
                row["Phase"] = ""

            if row["Period"] == "None":
                with open(gcvs_filename) as gf:
                    for line in gf:
                        if line[0] != "#":
                            l = line.split("|")
                            cat_Name = l[0].strip()
                            # cat_Name = ' '.join(cat_Name.split())
                            if cat_Name == row["Name"].strip():
                                ra = l[2]
                                dec = l[3]
                                mag = l[5]
                                row["Mag"] = mag
                                row["RA"] = ra[0:2] + "h" + ra[3:5] + "m" + ra[6:] + "s"
                                row["DEC"] = dec[:3] + "d" + dec[4:6] + "m" + dec[7:] + "s"
                                row["Period"] = float(l[7])
                                if row["Epoch"].strip() == "None":
                                    row["Epoch"] = float(l[6])
            # calc hours above horizon
            obj = ephem.FixedBody()
            obj.name = row["Name"]
            obj._ra = ephem.hours(row["RA"].replace("h", ":").replace("m", ":")[:-1])
            obj._dec = ephem.degrees(row["DEC"].replace("d", ":").replace("m", ":")[:-1])
            obj.compute(site)
            # print(obj.name, obj._ra, obj._dec, obj.alt, obj.az)
            try:
                rise = site.previous_rising(obj)
                pas = site.next_setting(obj)
                if pas > rise:
                    dur = pas - rise
                else:
                    dur = rise - pas
                # print(row["Name"], rise, pas)
                row["Dur"] = "%1.3f" % (dur * 24.0)
            except ephem.AlwaysUpError:
                row["Dur"] = "alw up"
            ##
            stars.append(row)
    # stars is list of dict [{.star_rec with keys..},{...}, {...}]
    return sorted(stars, key=lambda k: k['Mag'])


def plot2(star, lon, lat, elev):
    # https: // docs.astropy.org / en / stable / generated / examples / coordinates / plot_obs - planning.html
    name, ra, dec = star["Name"], star["RA"], star["DEC"]

    location = EarthLocation.from_geodetic(lon, lat, elev)
    obj = SkyCoord(ra, dec, frame='icrs')

    today = datetime.today()
    midnight = datetime(today.year, today.month, today.day, 23, 59, 0)
    midnight = Time(midnight)
    delta_midnight = np.linspace(-10, 10, 500) * u.hour
    times_delta = midnight + delta_midnight
    frames = AltAz(obstime=times_delta, location=location)
    obj_altazs = obj.transform_to(frames)


    #get Sun, Moon
    sun_altazs = get_sun(times_delta).transform_to(frames)
    moon_altazs = get_moon(times_delta).transform_to(frames)

    # CUT sun < -12
    tmp = zip(delta_midnight.value, sun_altazs.alt.value,
              times_delta.value, obj_altazs.alt.value, obj_altazs.az.value, moon_altazs.alt.value)
    ntmp = [x for x in list(tmp) if x[1] < -12 if x[3] > 25]  # Sun.h < -12 , obj.h > 25
    delta_midnight, sun_alt, t_delta, obj_alt, obj_az, moon_alt = list(zip(*ntmp))

    ####PLOT
    # plt.plot(delta_midnight.value, sun_altazs.alt.value, color='r', label='Sun') # dont need , Sun is < -12

    plt.plot(t_delta, moon_alt, color="y", ls='--', label='Moon')
    plt.scatter(t_delta, obj_alt, c=obj_az, label=name, lw=0, s=8, cmap='viridis')

    # plt.plot(delta_midnight, moon_alt, color="y", ls='--', label='Moon')
    # plt.scatter(delta_midnight, obj_alt, c=obj_az, label=name, lw=0, s=8, cmap='viridis')

    plt.colorbar().set_label('Azimuth [deg]')
    plt.legend(loc='upper left')

    myfmt = mdates.DateFormatter('%y-%m-%d %H:%M')
    plt.gca().xaxis.set_major_formatter(myfmt)
    plt.gcf().autofmt_xdate()

    plt.ylim(25, max(obj_alt))
    plt.xlabel('Time (UTC)')
    plt.ylabel('Altitude [deg]')
    # plt.subplots_adjust(top=0.88)  # to leave the title and not cut it !
    name2 = name + "_" + str(time.time()) + ".png"
    name3 = f'{os.path.join("static", "tmp", name2)}'

    for gfile in os.listdir(os.path.join("static", "tmp")):
        # if gfile.startswith(name + '_'):  # not to remove other images
        #     os.remove(os.path.join("static", "tmp", gfile))
        os.remove(os.path.join("static", "tmp", gfile))

    plt.savefig(name3, bbox_inches='tight')
    # plt.clf()
    return f'{os.path.join("tmp", name2)}'
    ############


def plot3(star, user):
    # https: // docs.astropy.org / en / stable / generated / examples / coordinates / plot_obs - planning.html
    name, ra, dec = star["Name"], star["RA"], star["DEC"]
    lat, lon, elev = user.site_lat, user.site_lon, user.site_elev

    # location = EarthLocation(lat=48.6 * u.deg, lon=22.45 * u.deg, height=290 * u.m)
    location = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=elev * u.m)
    obj = SkyCoord(ra, dec, frame='icrs')

    today = datetime.today()
    midnight = datetime(today.year, today.month, today.day, 23, 59, 0)
    midnight = Time(midnight)
    delta_midnight = np.linspace(-10, 10, 500) * u.hour
    times_delta = midnight + delta_midnight
    frames = AltAz(obstime=times_delta, location=location)
    obj_altazs = obj.transform_to(frames)

    # get Sun, Moon
    sun_altazs = get_sun(times_delta).transform_to(frames)
    moon_altazs = get_moon(times_delta).transform_to(frames)

    # CUT sun < -12
    # print(min(times_delta.value), max(times_delta.value))
    tmp = zip (delta_midnight.value, sun_altazs.alt.value, times_delta.value, obj_altazs.alt.value, obj_altazs.az.value, moon_altazs.alt.value)
    # ntmp = [x for x in list(tmp) if x[1] < -12 if x[3] > 25]  # Sun.h < -12 , obj.h > 25
    ntmp = [x for x in list(tmp) if x[1] < -12]  # Sun.h < -12 , obj.h > 25
    delta_midnight, sun_alt, t_delta, obj_alt, obj_az, moon_alt = list(zip(*ntmp))
    # print(min(t_delta), max(t_delta))

    t_phase = t2phases(t_delta, star["Period"], star["Epoch"])
    ####PLOT
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    # ax2 = ax1.twiny()

    ax1.plot(t_delta, moon_alt, color="y", ls='--', label='Moon')
    mappable = ax1.scatter(t_delta, obj_alt, c=obj_az, label=name, lw=0, s=8, cmap='viridis')

    myfmt = mdates.DateFormatter('%H:%M')  # %Y-%m-%d
    ax1.xaxis.set_major_formatter(myfmt)
    plt.gcf().autofmt_xdate()

    # Azimuth axis----------------------------------
    ax2 = ax1.twiny()
    ax2.set_xlim(ax1.get_xlim())
    numElems = 10  # 10 elements evenly spaced on ax2 on the top
    tt_idx = np.round(np.linspace(0, len(t_delta) - 1, numElems)).astype(int)
    t_delta = np.array(t_delta)
    phs = ["%1.2f" % x for x in t_phase]
    phs = np.array(phs)

    ax2.set_xticks(t_delta[tt_idx])
    ax2.set_xticklabels(phs[tt_idx])
    ax2.set_xlabel(r"Phase")
    ax2.tick_params(axis='x', which='major', pad=0)
    # -------------------------------------------------

    ax2.plot(t_phase, np.ones(len(t_phase)))

    plt.colorbar(mappable, ax=ax1).set_label('Azimuth [deg]')
    # plt.legend(loc='upper left')

    ax1.set_ylim(25, max(obj_alt) + 3)
    ax1.legend()
    ax1.set_xlabel('Time (UTC) \n' \
                   + t_delta[0].strftime("%Y-%m-%d") + " -- " + t_delta[-1].strftime("%Y-%m-%d"))
    ax1.set_ylabel('Altitude [deg]')

    # plt.subplots_adjust(top=0.88)  # to leave the title and not cut it !
    name2 = name + "_" + str(time.time()) + ".png"
    name3 = f'{os.path.join("static", "tmp", name2)}'

    for gfile in os.listdir(os.path.join("static", "tmp")):
        # if gfile.startswith(name + '_'):  # not to remove other images
        #     os.remove(os.path.join("static", "tmp", gfile))
        os.remove(os.path.join("static", "tmp", gfile))

    fig.savefig(name3, bbox_inches='tight')
    # plt.clf()
    return f'{os.path.join("tmp", name2)}'
    ############


def plot_alt(obj_data, lon, lat, elev, tz=timezone("GMT0"), observe_time=Time.now()):
    name, ra, dec = obj_data
    # https://astroplan.readthedocs.io/en/latest/tutorials/plots.html

# >>> from datetime import datetime
# >>> today = datetime.today()
# >>> now = datetime(today.year, today.month, today.day, 0,0,0 )
# >>> now


    location = EarthLocation.from_geodetic(lon, lat, elev)

    observer = Observer(name='Subaru Telescope',
               location=location,
               pressure=0.615 * u.bar,
               relative_humidity=0.11,
               temperature=0 * u.deg_C,
               timezone=tz,  # timezone('US/Hawaii'),
               description="Subaru Telescope on Maunakea, Hawaii")

    # observe_time = Time('2000-06-15 23:30:00')
    observe_time = observe_time + np.linspace(-10, 10, 55)*u.hour  # +- 5 hours

    target = FixedTarget(name=name, coord=SkyCoord(ra, dec, frame='icrs'))
    plot_altitude(target, observer, observe_time, airmass_yaxis=True, style_kwargs={'fmt':"k"})

    ## Sun and Moon
    sun = FixedTarget(name="Sun", coord=get_sun(observe_time))
    plot_altitude(sun, observer, observe_time, airmass_yaxis=True, style_kwargs={'fmt':"r"})

    moon = FixedTarget(name="Moon", coord=get_moon(observe_time))
    # plot_altitude(moon, observer, observe_time, airmass_yaxis=True, style_kwargs={'fmt':"y-"})
    plot_altitude(moon, observer, observe_time, airmass_yaxis=True, style_kwargs={'fmt':"y"})
    ####

    # plt.xlabel(['label1','label2'])

    plt.legend()

    plt.tight_layout()
    plt.subplots_adjust(top=0.88)  # to leave the title and not cut it !
    plt.title(name)
    plt.savefig(f'{name}.png')
    # plt.show()