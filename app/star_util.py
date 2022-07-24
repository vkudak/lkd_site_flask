import csv
import sys
import os
import matplotlib.pyplot as plt
import ephem
import numpy as np
from datetime import datetime, timedelta
import time
import math
from pylab import rcParams
import matplotlib.dates as mdates
import json
import zipfile
rcParams['figure.figsize'] = 10, 6


def get_julian_datetime(date):
    """
    Convert a datetime object into julian float.
    Args:
        date: datetime-object of date in question

    Returns: float - Julian calculated datetime.
    Raises:
        TypeError : Incorrect parameter type
        ValueError: Date out of range of equation
    """

    # Ensure correct format
    if not isinstance(date, datetime):
        raise TypeError('Invalid type for parameter "date" - expecting datetime')
    elif date.year < 1801 or date.year > 2099:
        raise ValueError('Datetime must be between year 1801 and 2099')

    # Perform the calculation
    julian_datetime = 367 * date.year - int((7 * (date.year + int((date.month + 9) / 12.0))) / 4.0) + int(
        (275 * date.month) / 9.0) + date.day + 1721013.5 + (
                          date.hour + date.minute / 60.0 + date.second / math.pow(60,
                                                                                  2)) / 24.0 - 0.5 * math.copysign(
        1, 100 * date.year + date.month - 190002.5) + 0.5

    return julian_datetime


def phase2str(ph):
    pstart = round(ph[0]*10)
    pend = round(ph[1]*10)
    s = "["
    scale = 5
    if pstart <= pend:
        xr = range(1-1, 10*scale+1)
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
        # --***--  change to  **---**
        s = s.replace("*", "+")
        s = s.replace("-", "*")
        s = s.replace("+", "-")
    else:
        s = s[:-1] + "]"
    return s


def t2phases(dt, P0, E0):
    aph = []
    P0 = float(P0)
    if E0 < 2400000:
        E0 = 2400000 + float(E0)
    for x in dt:
        # ph = np.mod(tm.jd - E0, P0) / float(P0)  # phase
        ph = np.mod(x - E0, P0) / float(P0)  # phase
        aph.append(ph)
    return aph


def read_stars(filename, gcvs_filename, user):
    stars = []
    site = ephem.Observer()
    today = datetime.today()
    site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
    site.lat = str(user.site_lat)  # "48.63" #loc.lat
    site.lon = str(user.site_lon)  # "22.33" #loc.lon
    site.horizon = '25'
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row["Done"] = row["Done"].strip()
            if row["Done"] == "":
                row["Done"] = False
            else:
                row["Done"] = True

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
                row["Rise"] = str(rise).replace("/", "-")
                row["Pass"] = str(pas).replace("/", "-")
                row["sort_date"] = datetime.strptime(row['Rise'], "%Y-%m-%d %H:%M:%S").timestamp()
            except ephem.AlwaysUpError:
                row["Rise"] = "alw up"
                row["Pass"] = "alw up"
                row["sort_date"] = (datetime.now() + timedelta(days=10)).timestamp()
            ##
            stars.append(row)
    # stars is list of dict [{.star_rec with keys..},{...}, {...}]

    # todo How to sort stars ?????
    stars = sorted(stars, key=lambda k: (float(k['Mag']), k["sort_date"]))
    # return sorted(stars, key=lambda k: k['Mag'])
    return stars


def read_stars_json(filename, gcvs_filename, user):
    stars = []
    site = ephem.Observer()
    today = datetime.today()
    site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
    site.lat = str(user.site_lat)  # "48.63" #loc.lat
    site.lon = str(user.site_lon)  # "22.33" #loc.lon
    site.horizon = '25'
    with open(filename) as json_file:
        data = json.load(json_file)
        for row in data:
            row["Name"] = ' '.join(row["Name"].split())

            if not row["Period"]:  # == None
                with open(gcvs_filename) as gf:
                    for line in gf:
                        if line[0] != "#":
                            l = line.split("|")
                            cat_Name = l[0].strip()
                            if cat_Name == row["Name"].strip():
                                ra = l[2]
                                dec = l[3]
                                mag = l[5]
                                row["Mag"] = mag
                                row["RA"] = ra[0:2] + "h" + ra[3:5] + "m" + ra[6:] + "s"
                                row["DEC"] = dec[:3] + "d" + dec[4:6] + "m" + dec[7:] + "s"
                                row["Period"] = float(l[7])
                                if row["Epoch"] is None:
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
                row["Rise"] = str(rise).replace("/", "-")
                row["Pass"] = str(pas).replace("/", "-")
                row["sort_date"] = datetime.strptime(row['Rise'], "%Y-%m-%d %H:%M:%S").timestamp()
            except ephem.AlwaysUpError:
                row["Rise"] = "alw up"
                row["Pass"] = "alw up"
                row["sort_date"] = (datetime.now() + timedelta(days=10)).timestamp()
            ##
            if row["Phase"] is not None:
                row["Phase"] = [tuple(x.split(":")) for x in row["Phase"].split(";")]
                row["Phase"] = [(x, y.strip('][').split(',')) for x, y in row["Phase"]]
                row["Phase"] = [(x, [float(z) for z in y]) for x,y in row["Phase"]]
                row["Phase"] = [(x,
                                 (t2phases([y[0]], row["Period"], row["Epoch"])[0], t2phases([y[1]], row["Period"], row["Epoch"])[0]),
                                 y[1] - y[0],
                                 )
                                for x, y in row["Phase"]]
                for i in range(0, len(row["Phase"])):
                    if row["Phase"][i][2] >= row["Period"]:
                        row["Phase"][i] = [row["Phase"][i][0], row["Phase"][i][1], "[" + "*"*50 + "]"]
                    else:
                        row["Phase"][i] = [row["Phase"][i][0], row["Phase"][i][1], phase2str(row["Phase"][i][1])]
            else:
                row["Phase"] = ""
            stars.append(row)
    # stars is list of dict [{.star_rec with keys..},{...}, {...}]

    # todo How to sort stars ?????
    stars = sorted(stars, key=lambda k: (float(k['Mag']), k["sort_date"]))
    stars = sorted(stars, key=lambda k: (k["Phase"] != ""), reverse=True)
    stars = sorted(stars, key=lambda k: (k["Done"]))  # Done are last ones
    # return sorted(stars, key=lambda k: k['Mag'])
    return stars


def read_stars_from_db(user, db_stars):
    stars = []
    site = ephem.Observer()
    today = datetime.today()
    site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
    site.lat = str(user.site_lat)  # "48.63" #loc.lat
    site.lon = str(user.site_lon)  # "22.33" #loc.lon
    site.horizon = '25'
    for star in db_stars:
        row = {'Name': star.star_name, 'RA': star.ra, 'DEC': star.dec}
        # calc hours above horizon
        obj = ephem.FixedBody()
        obj.name = star.star_name
        obj._ra = ephem.hours(star.ra.replace("h", ":").replace("m", ":")[:-1])
        obj._dec = ephem.degrees(star.dec.replace("d", ":").replace("m", ":")[:-1])
        obj.compute(site)
        # print(obj.name, obj._ra, obj._dec, obj.alt, obj.az)
        try:
            rise = site.previous_rising(obj)
            pas = site.next_setting(obj)
            row["Rise"] = str(rise).replace("/", "-")
            row["Pass"] = str(pas).replace("/", "-")
            row["sort_date"] = datetime.strptime(row['Rise'], "%Y-%m-%d %H:%M:%S").timestamp()
        except ephem.AlwaysUpError:
            row["Rise"] = "alw up"
            row["Pass"] = "alw up"
            row["sort_date"] = (datetime.now() + timedelta(days=10)).timestamp()
        ##
        row['Phase'] = star.phase
        row["Period"] = star.period
        row["Epoch"] = star.epoch
        row["Mag"] = star.mag
        row["Done"] = star.done
        row["id"] = star.id

        if row["Phase"] is not None:
            row["Phase"] = [(x,
                             (t2phases([y[0]], row["Period"], row["Epoch"])[0], t2phases([y[1]], row["Period"], row["Epoch"])[0]),
                             y[1] - y[0],
                             )
                            for x, y in row["Phase"].items()]

            for i in range(0, len(row["Phase"])):
                if row["Phase"][i][2] >= row["Period"]:
                    row["Phase"][i] = [row["Phase"][i][0], row["Phase"][i][1], "[" + "*"*50 + "]"]
                else:
                    row["Phase"][i] = [row["Phase"][i][0], row["Phase"][i][1], phase2str(row["Phase"][i][1])]
        else:
            row["Phase"] = ""
        stars.append(row)
    # stars is list of dict [{.star_rec with keys..},{...}, {...}]

    # todo How to sort stars ?????
    stars = sorted(stars, key=lambda k: (float(k['Mag']), k["sort_date"]))
    stars = sorted(stars, key=lambda k: (k["Phase"] != ""), reverse=True)
    stars = sorted(stars, key=lambda k: (k["Done"]))  # Done are last ones
    # return sorted(stars, key=lambda k: k['Mag'])
    return stars


def date_linspace(start, end, steps):
    delta = (end - start) / steps
    increments = range(0, steps) * np.array([delta]*steps)
    res = start + increments
    res[-1] = end
    return res


def plot4(star, user):
    # name, ra, dec = star["Name"], star["RA"], star["DEC"]
    name = star["Name"]

    site = ephem.Observer()
    today = datetime.today()
    site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
    site.lat = str(user.site_lat)  # "48.63" #loc.lat
    site.lon = str(user.site_lon)  # "22.33" #loc.lon

    obj = ephem.FixedBody()
    obj.name = name
    obj._ra = ephem.hours(star["RA"].replace("h", ":").replace("m", ":")[:-1])
    obj._dec = ephem.degrees(star["DEC"].replace("d", ":").replace("m", ":")[:-1])
    obj.compute(site)

    site.horizon = '-12'
    sun_set = site.previous_setting(ephem.Sun(), use_center=True).datetime()
    sun_rise = site.next_rising(ephem.Sun(), use_center=True).datetime()

    site.horizon = '25'
    try:
        obj_rise = site.previous_rising(obj).datetime()
        obj_set = site.next_setting(obj).datetime()
    except ephem.AlwaysUpError:
        obj_rise = "alw up"
        obj_set = "alw up"

    # make t_delta
    counts = 300
    # print(obj_rise, obj_set)
    # print(sun_set, sun_rise)
    if obj_rise != "alw up":
        if obj_rise >= sun_set:
            if obj_set <= sun_rise:
                t_delta = date_linspace(obj_rise, obj_set, counts)
            else:
                t_delta = date_linspace(obj_rise, sun_rise, counts)
        else:
            t_delta = date_linspace(sun_set, sun_rise, counts)
    else:
        t_delta = date_linspace(sun_set, sun_rise, counts)

    moon_alt = []
    obj_alt = []
    obj_az = []
    dt_jd = []

    for dt in t_delta:
        site.date = dt  # '1984/5/30 16:22:56'  # 12:22:56 EDT
        moon = ephem.Moon()
        moon.compute(site)
        obj.compute(site)
        moon_alt.append(math.degrees(float(moon.alt)))
        obj_az.append(math.degrees(float(obj.az)))
        obj_alt.append(math.degrees(float(obj.alt)))
        dt_jd.append(get_julian_datetime(dt))

    t_phase = t2phases(dt_jd, star["Period"], float(star["Epoch"]))
    t_phase = np.array(t_phase)
    obj_alt = np.array(obj_alt)
    obj_az = np.array(obj_az)
    moon_alt = np.array(moon_alt)
    t_delta = np.array(t_delta)
    ####PLOT
    fig = plt.figure()
    ax1 = fig.add_subplot(111)

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

    if not os.path.exists(os.path.join("app", "static", "tmp")):
        os.mkdir(os.path.join("app", "static", "tmp"))
    name2 = name + "_" + str(time.time()) + ".png"
    name3 = f'{os.path.join("app", "static", "tmp", name2)}'

    for gfile in os.listdir(os.path.join("app", "static", "tmp")):
        # if gfile.startswith(name + '_'):  # not to remove other images
        #     os.remove(os.path.join("static", "tmp", gfile))
        os.remove(os.path.join("app", "static", "tmp", gfile))

    fig.savefig(name3, bbox_inches='tight')
    # plt.clf()
    # return f'{os.path.join("tmp", name2)}'
    return os.path.join("tmp", name2)
    ############


def plot_star(star, user):
    site = ephem.Observer()
    today = datetime.today()
    site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
    site.lat = str(user.site_lat)  # "48.63" #loc.lat
    site.lon = str(user.site_lon)  # "22.33" #loc.lon

    obj = ephem.FixedBody()
    obj.name = star.star_name
    obj._ra = ephem.hours(star.ra.replace("h", ":").replace("m", ":")[:-1])
    obj._dec = ephem.degrees(star.dec.replace("d", ":").replace("m", ":")[:-1])
    obj.compute(site)

    site.horizon = '-12'
    sun_set = site.previous_setting(ephem.Sun(), use_center=True).datetime()
    sun_rise = site.next_rising(ephem.Sun(), use_center=True).datetime()

    site.horizon = '25'
    try:
        obj_rise = site.previous_rising(obj).datetime()
        obj_set = site.next_setting(obj).datetime()
    except ephem.AlwaysUpError:
        obj_rise = "alw up"
        obj_set = "alw up"

    # make t_delta
    counts = 300
    # print(obj_rise, obj_set)
    # print(sun_set, sun_rise)
    if obj_rise != "alw up":
        if obj_rise >= sun_set:
            if obj_set <= sun_rise:
                t_delta = date_linspace(obj_rise, obj_set, counts)
            else:
                t_delta = date_linspace(obj_rise, sun_rise, counts)
        else:
            t_delta = date_linspace(sun_set, sun_rise, counts)
    else:
        t_delta = date_linspace(sun_set, sun_rise, counts)

    moon_alt = []
    obj_alt = []
    obj_az = []
    dt_jd = []

    for dt in t_delta:
        site.date = dt  # '1984/5/30 16:22:56'  # 12:22:56 EDT
        moon = ephem.Moon()
        moon.compute(site)
        obj.compute(site)
        moon_alt.append(math.degrees(float(moon.alt)))
        obj_az.append(math.degrees(float(obj.az)))
        obj_alt.append(math.degrees(float(obj.alt)))
        dt_jd.append(get_julian_datetime(dt))

    t_phase = t2phases(dt_jd, star.period, float(star.epoch))
    t_phase = np.array(t_phase)
    obj_alt = np.array(obj_alt)
    obj_az = np.array(obj_az)
    moon_alt = np.array(moon_alt)
    t_delta = np.array(t_delta)
    ####PLOT
    fig = plt.figure()
    ax1 = fig.add_subplot(111)

    ax1.plot(t_delta, moon_alt, color="y", ls='--', label='Moon')
    mappable = ax1.scatter(t_delta, obj_alt, c=obj_az, label=star.star_name, lw=0, s=8, cmap='viridis')

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

    if not os.path.exists(os.path.join("app", "static", "tmp")):
        os.mkdir(os.path.join("app", "static", "tmp"))
    name2 = star.star_name + "_" + str(time.time()) + ".png"
    name3 = f'{os.path.join("app", "static", "tmp", name2)}'

    for gfile in os.listdir(os.path.join("app", "static", "tmp")):
        # if gfile.startswith(name + '_'):  # not to remove other images
        #     os.remove(os.path.join("static", "tmp", gfile))
        os.remove(os.path.join("app", "static", "tmp", gfile))

    fig.savefig(name3, bbox_inches='tight')
    # plt.clf()
    # return f'{os.path.join("tmp", name2)}'
    return os.path.join("tmp", name2)
    ############


def getListOfFiles(dirName):
    # create a list of file and sub directories
    # names in the given directory
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)

    return allFiles


def read_sat_files(dir):
    """
    dir
        path: path to db_sat_phot zip archive
        # ----- absolut path to folder with phc, phR files
    Returns:
        list of dict with records
    """
    sat_db = []
    ext = [".phc", ".phR"]

    with zipfile.ZipFile(os.path.join(dir, 'db_sat_phot.zip')) as myzip:
        for file in myzip.namelist():
            # read the file if its file and ext is phc, phR
            # print(file)
            if not os.path.isdir(file) and file.endswith(tuple(ext)):
                ###########################################################################
                if file.endswith(".phc"):
                    typ = "phc"
                    sat_r = {}
                    with myzip.open(file) as fs:
                        sat_st = fs.readline().decode("UTF-8").strip("\n").strip("\r")
                        sat_st_date = sat_st.split()[0]
                        sat_end = fs.readline().decode("UTF-8").strip("\n").strip("\r")
                        for line in fs:
                            line = line.decode("UTF-8")
                            if line[:9] == "COSPAR ID":
                                cospar = line.split("=")[1].strip().strip("\n").strip("\r")
                            if line[:8] == "NORAD ID":
                                norad = int(line.split("=")[1].strip())
                            if line[:4] == "NAME":
                                name = line.split("=")[1].strip().strip("\n").strip("\r")
                            if line[:2] == "dt":
                                dt = line.split("=")[1].strip().strip("\n").strip("\r")
                        fs.seek(0)
                        try:
                            impB, impV, fonB, fonV, mB, mV, az, el, rg = np.loadtxt(fs, unpack=True,
                                                                                    skiprows=7, usecols=(
                                1, 2, 3, 4, 5, 6, 7, 8, 9))
                            fs.seek(0)
                            lctime = np.loadtxt(fs, unpack=True, skiprows=7, usecols=(0,),
                                                dtype={'names': ('time',), 'formats': ('S15',)})

                            lctime = [
                                datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f")
                                for x in lctime]
                            t0 = lctime[0]
                            lctime = [x if t0 - x < timedelta(hours=2) else x + timedelta(days=1) for x in
                                      lctime]  # add DAY after 00:00:00

                            # print(lctime)

                            sat_find_ind = next((i for i, item in enumerate(sat_db) if item["norad"] == norad),
                                                None)

                            if sat_find_ind is not None:

                                sat_db[sat_find_ind]["lc_list"].append([sat_st, sat_end, dt, lctime,
                                                                        impB, impV,
                                                                        fonB, fonV,
                                                                        mB, mV,
                                                                        az, el, rg, typ])
                            else:
                                sat_r["norad"] = norad
                                sat_r["cospar"] = cospar
                                sat_r["name"] = name
                                sat_r["lc_list"] = [[sat_st, sat_end, dt, lctime, impB, impV,
                                                     fonB, fonV, mB, mV,
                                                     az, el, rg, typ]]
                                sat_db.append(sat_r)
                        except Exception as e:
                            print(e)
                            print("bed format PHC in file =", file)
                            pass

                elif file.endswith(".phR"):
                    typ = "phR"
                    sat_r = {}
                    with myzip.open(file) as fs:
                        fs.readline()
                        fs.readline()
                        fs.readline()
                        fs.readline()
                        sat_st = fs.readline().decode("UTF-8").strip("\n").strip("\r")[2:].strip()[:-1]
                        sat_st_date = sat_st.split()[0]

                        sat_end = fs.readline().decode("UTF-8").strip("\n").strip("\r")[2:].strip()[:-1]
                        # print("sat_st = ", sat_st)
                        # print("sat_end = ", sat_end)

                        for line in fs:
                            l = line.decode("UTF-8").split(" = ")
                            if l[0] == "# COSPAR":
                                cospar = l[1].strip("\n").strip("\r")
                            if l[0] == "# NORAD ":
                                norad = int(l[1])
                            if l[0] == "# NAME  ":
                                name = l[1].strip("\n").strip("\r")
                            if l[0] == "# dt":
                                dt = l[1].strip("\n").strip("\r")
                        fs.seek(0)
                        try:
                            m, merr, az, el, rg = np.loadtxt(fs, unpack=True, skiprows=11,
                                                             usecols=(8, 9, 10, 11, 12))
                            fs.seek(0)
                            lctime = np.loadtxt(fs, unpack=True, skiprows=11, usecols=(1,),
                                                dtype={'names': ('time',), 'formats': ('S14',)})
                            lctime = [
                                datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f")
                                for x in lctime]
                            t0 = lctime[0]
                            lctime = [x if t0 - x < timedelta(hours=2) else x + timedelta(days=1) for x in
                                      lctime]  # add DAY after 00:00:00

                            sat_find_ind = next((i for i, item in enumerate(sat_db) if item["norad"] == norad),
                                                None)

                            if sat_find_ind is not None:

                                sat_db[sat_find_ind]["lc_list"].append([sat_st, sat_end, dt, lctime,
                                                                        m, merr, az, el, rg, typ])
                            else:
                                sat_r["norad"] = norad
                                sat_r["cospar"] = cospar
                                sat_r["name"] = name
                                sat_r["lc_list"] = [[sat_st, sat_end, dt, lctime, m, merr, az, el, rg, typ]]
                                sat_db.append(sat_r)
                        except Exception as e:
                            # if str(e) == "list index out of range":   # no merr
                            # print(e.__class__.__name__)
                            # print(type(e.__class__.__name__))
                            # print(e.__class__ is IndexError)
                            if e.__class__ is IndexError:  # no merr
                                fs.seek(0)
                                m, az, el, rg = np.loadtxt(fs, unpack=True, skiprows=11,
                                                                 usecols=(7, 8, 9, 10))
                                fs.seek(0)
                                lctime = np.loadtxt(fs, unpack=True, skiprows=11, usecols=(1,),
                                                    dtype={'names': ('time',), 'formats': ('S14',)})
                                lctime = [
                                    datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f")
                                    for x in lctime]
                                t0 = lctime[0]
                                lctime = [x if t0 - x < timedelta(hours=2) else x + timedelta(days=1) for x in
                                          lctime]  # add DAY after 00:00:00

                                sat_find_ind = next((i for i, item in enumerate(sat_db) if item["norad"] == norad),
                                                    None)

                                if sat_find_ind is not None:

                                    sat_db[sat_find_ind]["lc_list"].append([sat_st, sat_end, dt, lctime,
                                                                            m, az, el, rg, typ])
                                else:
                                    sat_r["norad"] = norad
                                    sat_r["cospar"] = cospar
                                    sat_r["name"] = name
                                    sat_r["lc_list"] = [[sat_st, sat_end, dt, lctime, m, az, el, rg, typ]]
                                    sat_db.append(sat_r)
                            else:
                                # print(e.__class__.__name__)
                                print("Error = ", e, e.__class__.__name__)
                                print("Bed format PHR in file =", file)
                            pass

    ### SORT sat_db by sat["lc_list"][0] (sat_st)  ###
    if len(sat_db) > 0:
        sat_db = sorted(sat_db, key=lambda k: k["norad"])
        for z in range(0, len(sat_db)):
            sat_db[z]["lc_list"] = sorted(sat_db[z]["lc_list"], reverse=True, key=lambda k: k[0])  # [0] = sat_st
    ##################################################

    return sat_db
    ####################################################################

    # #############################old func without zip read ##############################################
    # if os.path.exists(dir):
    #     files = getListOfFiles(dir)
    #     files = [file for file in files if file.endswith(tuple(ext))]
    #     for file in files:
    #         # print(file)
    #         if file.endswith("phc"):
    #             typ = "phc"
    #             sat_r = {}
    #             with open(file) as fs:
    #                 sat_st = fs.readline().strip("\n")
    #                 sat_st_date = sat_st.split()[0]
    #                 sat_end = fs.readline().strip("\n")
    #                 for line in fs:
    #                     if line[:9] == "COSPAR ID":
    #                         cospar = line.split("=")[1].strip()
    #                     if line[:8] == "NORAD ID":
    #                         norad = int(line.split("=")[1].strip())
    #                     if line[:4] == "NAME":
    #                         name = line.split("=")[1].strip()
    #                     if line[:2] == "dt":
    #                         dt = line.split("=")[1].strip()
    #
    #             try:
    #                 impB, impV, fonB, fonV, mB, mV, az, el, rg = np.loadtxt(file, unpack=True,
    #                                                                         skiprows=7, usecols=(1, 2, 3, 4, 5, 6, 7, 8, 9))
    #                 lctime = np.loadtxt(file, unpack=True, skiprows=7, usecols=(0,),
    #                                   dtype={'names': ('time',), 'formats': ('S15',)})
    #                 lctime = [datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f") for x in lctime]
    #                 t0 = lctime[0]
    #                 lctime = [x if t0-x < timedelta(hours=2) else x + timedelta(days=1) for x in lctime]  # add DAY after 00:00:00
    #
    #                 # print(lctime)
    #
    #                 sat_find_ind = next((i for i, item in enumerate(sat_db) if item["norad"] == norad), None)
    #
    #                 if sat_find_ind is not None:
    #
    #                     sat_db[sat_find_ind]["lc_list"].append([sat_st, sat_end, dt, lctime,
    #                                                             impB, impV,
    #                                                             fonB, fonV,
    #                                                             mB, mV,
    #                                                             az, el, rg, typ])
    #                 else:
    #                     sat_r["norad"] = norad
    #                     sat_r["cospar"] = cospar
    #                     sat_r["name"] = name
    #                     sat_r["lc_list"] = [[sat_st, sat_end, dt, lctime, impB, impV,
    #                                          fonB, fonV, mB, mV,
    #                                          az, el, rg, typ]]
    #                     sat_db.append(sat_r)
    #             except Exception as e:
    #                 print(e)
    #                 print("bed format PHC in file =", file)
    #                 pass
    #
    #         elif file.endswith(".phR"):
    #             typ = "phR"
    #             sat_r = {}
    #             with open(file) as fs:
    #                 fs.readline()
    #                 fs.readline()
    #                 fs.readline()
    #                 fs.readline()
    #                 sat_st = fs.readline().strip("\n")[2:].strip()[:-1]
    #                 sat_st_date = sat_st.split()[0]
    #
    #                 sat_end = fs.readline().strip("\n")[2:].strip()[:-1]
    #                 # print("sat_st = ", sat_st)
    #                 # print("sat_end = ", sat_end)
    #
    #                 for line in fs:
    #                     l = line.split(" = ")
    #                     if l[0] == "# COSPAR":
    #                         cospar = l[1]
    #                     if l[0] == "# NORAD ":
    #                         norad = int(l[1])
    #                     if l[0] == "# NAME  ":
    #                         name = l[1]
    #                     if l[0] == "# dt":
    #                         dt = l[1].strip("\n")
    #                 # print("norad = ", norad)
    #
    #             try:
    #                 m, merr, az, el, rg = np.loadtxt(file, unpack=True, skiprows=11, usecols=(8, 9, 10, 11, 12))
    #                 lctime = np.loadtxt(file, unpack=True, skiprows=11, usecols=(1,),
    #                                   dtype={'names': ('time',), 'formats': ('S14',)})
    #                 lctime = [datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f") for x in lctime]
    #                 t0 = lctime[0]
    #                 lctime = [x if t0-x < timedelta(hours=2) else x + timedelta(days=1) for x in lctime]  # add DAY after 00:00:00
    #
    #                 # print(lctime)
    #
    #                 sat_find_ind = next((i for i, item in enumerate(sat_db) if item["norad"] == norad), None)
    #
    #                 if sat_find_ind is not None:
    #
    #                     sat_db[sat_find_ind]["lc_list"].append([sat_st, sat_end, dt, lctime,
    #                                                             m, merr, az, el, rg, typ])
    #                     # print("add phR rec2 ", norad)
    #                 else:
    #                     sat_r["norad"] = norad
    #                     sat_r["cospar"] = cospar
    #                     sat_r["name"] = name
    #                     sat_r["lc_list"] = [[sat_st, sat_end, dt, lctime, m, merr, az, el, rg, typ]]
    #                     sat_db.append(sat_r)
    #                     # print("add phR rec ", norad)
    #             except Exception as e:
    #                 print(e)
    #                 print("bed format PHR in file =", file)
    #                 pass
    #
    #
    #     ### SORT sat_db by sat["lc_list"][0] (sat_st)  ###
    #     if len(sat_db) > 0:
    #         sat_db = sorted(sat_db, key=lambda k: k["norad"])
    #         for z in range(0, len(sat_db)):
    #             sat_db[z]["lc_list"] = sorted(sat_db[z]["lc_list"], key=lambda k: k[0])  # [0] = sat_st
    #     ##################################################
    #
    #     return sat_db
    # else:
    #     return None
    # ####################################################################


def plot_ccd_lc(sat, lc_index):
    plt.gcf()
    plt.clf()
    filt = "R"
    grid = True
    lc = sat["lc_list"][lc_index]
    cospar, norad, name, dt = sat["cospar"], sat["norad"], sat["name"], lc[2]
    if len(lc) == 10:
        mR, merr, Az, El = lc[4], lc[5], lc[6], lc[7]
    else:
        mR, Az, El = lc[4], lc[5], lc[6]

    date_time = lc[3]

    ## fig im MAG
    plt.rcParams['figure.figsize'] = [12, 6]
    dm = max(mR) - min(mR)
    dm = dm * 0.1
    plt.axis([min(date_time), max(date_time), max(mR) + dm, min(mR) - dm])

    if len(lc) == 10:
        plt.errorbar(date_time, mR, yerr=merr, fmt='xr-', capsize=2, linewidth=0.5, fillstyle="none", markersize=3, ecolor="k")
    else:
        plt.plot(date_time, mR, "xr-", linewidth=0.5, fillstyle="none", markersize=3)
    # plt.errorbar(date_time, mR, yerr=merr, fmt='xr-', capsize=2, linewidth=0.5, fillstyle="none", markersize=3)
    # plt.plot(date_time, mR, "xr-", linewidth=0.5, fillstyle="none", markersize=3) without errors

    # d, t = str(date_time[0]).split(" ")
    # plt.title("Satellite Name:%s, NORAD:%s, COSPAR:%s \n Date=%s  UT=%s   dt=%s  Filter=%s" % (
        # name, norad, cospar, d, t, str(dt).strip("\n"), filt), pad=6, fontsize=12)

    plt.title("Satellite Name:%s, NORAD:%s, COSPAR:%s \n LC start=%s  dt=%s  Filter=%s" % (
        name, norad, cospar, lc[0], str(dt).strip("\n"), filt), pad=6, fontsize=12)

    plt.ylabel(r'$m_{st}$')
    plt.xlabel('UT')
    ax = plt.gca()

    # Azimuth axis----------------------------------
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    numElems = 6
    tt_idx = np.round(np.linspace(0, len(date_time) - 1, numElems)).astype(int)
    Tt2 = np.array(date_time)
    Az2 = np.array(Az)
    El2 = np.array(El)

    # Az2s = ["%3.2f" % Azt for Azt in Az2]
    Az2s = []
    Tt2s = []
    for kk in range(0, len(Az2)):
        azt = Az2[kk]
        elt = El2[kk]
        t = Tt2[kk]
        Az2s.append("%3.1f; %3.1f" % (azt, elt))
        Tt2s.append(t.strftime("%H:%M:%S"))
    Az2s = np.array(Az2s)
    ax2.set_xticks(Tt2[tt_idx])  # new_tick_locations
    ax2.set_xticklabels(Az2s[tt_idx], fontsize=8)
    ax2.set_xlabel(r"Az;h [deg]", fontsize=8)
    ax2.tick_params(axis='x', which='major', pad=0)

    Tt2s = np.array(Tt2s)
    ax.set_xticks(Tt2[tt_idx])  # new_tick_locations
    ax.set_xticklabels(Tt2s[tt_idx], fontsize=10)

    if grid:
        ax.xaxis.grid()
        ax.yaxis.grid()
    # ----------------------------------------------------

    if not os.path.exists(os.path.join("static", "tmp_sat")):
        os.mkdir(os.path.join("static", "tmp_sat"))
    name2 = name + "_" + str(time.time()) + ".png"
    name3 = f'{os.path.join("static", "tmp_sat", name2)}'

    for gfile in os.listdir(os.path.join("static", "tmp_sat")):
        # if gfile.startswith(name + '_'):  # not to remove other images
        #     os.remove(os.path.join("static", "tmp", gfile))
        os.remove(os.path.join("static", "tmp_sat", gfile))

    plt.savefig(name3, bbox_inches='tight')
    plt.gcf()
    return os.path.join("tmp_sat", name2)


def plot_sat_lc(sat, lc_index):
    NAME = sat["name"]
    NORAD = sat["norad"]
    COSPAR = sat["cospar"]

    lc = sat["lc_list"][lc_index]

    Tt = lc[3]
    # Tt = [datetime.strptime(t, '%H:%M:%S.%f') for t in Tt]
    Tmin = min(Tt)
    Tmax = max(Tt)
    mB = lc[8]
    mV = lc[9]
    maxB, minB = max(lc[8]), min(lc[8])
    maxV, minV = max(lc[9]), min(lc[9])
    Az = lc[10]
    El = lc[11]
    miny = max(maxB, maxV)
    maxy = min(minB, minV)
    maxy = maxy - 0.5

    plt.clf()
    plt.axis([Tmin, Tmax, miny, maxy])
    plt.ylabel('m_st')

    # locale.setlocale(locale.LC_NUMERIC, 'C')  # for graph

    plt.plot(Tt, mB, 'b.-', label="B")
    plt.plot(Tt, mV, 'g^--', mfc='none', ms=3, label="V")
    ax = plt.gca()

    # Azimuth axis----------------------------------
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    numElems = 5
    tt_idx = np.round(np.linspace(0, len(Tt) - 1, numElems)).astype(int)
    Tt2 = np.array(Tt)
    Az2 = np.array(Az)
    El2 = np.array(El)

    # Az2s = ["%3.2f" % Azt for Azt in Az2]
    Az2s = []
    Tt2s = []
    for kk in range(0, len(Az2)):
        azt = Az2[kk]
        elt = El2[kk]
        t = Tt2[kk]
        Az2s.append("%3.1f; %3.1f" % (azt, elt))
        Tt2s.append(t.strftime("%H:%M:%S"))
    Az2s = np.array(Az2s)
    ax2.set_xticks(Tt2[tt_idx])  # new_tick_locations
    ax2.set_xticklabels(Az2s[tt_idx], fontsize=8)
    ax2.set_xlabel(r"Az;h [deg]", fontsize=8)
    ax2.tick_params(axis='x', which='major', pad=0)
    # ----------------------------------------------------

    # ax.xaxis.set_major_formatter(timeFmt)
    Tt2s = np.array(Tt2s)
    ax.set_xticks(Tt2[tt_idx])  # new_tick_locations
    ax.set_xticklabels(Tt2s[tt_idx], fontsize=10)

    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    t_pos = 0.99
    ax2.set_title("Satellite Name:%s, NORAD:%s, COSPAR:%s \n LC Start=%s   dt=%s" %
                  (NAME, NORAD, COSPAR, lc[0], lc[2]), pad=28, fontsize=10)
    ax2.title.set_position([.5, t_pos])

    ax.xaxis.grid()
    ax.yaxis.grid()
    # plt.savefig(scr_pth + "//tmp_last_fig.png")

    if not os.path.exists(os.path.join("static", "tmp_sat")):
        os.mkdir(os.path.join("static", "tmp_sat"))
    name2 = NAME + "_" + str(time.time()) + ".png"
    name3 = f'{os.path.join("static", "tmp_sat", name2)}'

    for gfile in os.listdir(os.path.join("static", "tmp_sat")):
        # if gfile.startswith(name + '_'):  # not to remove other images
        #     os.remove(os.path.join("static", "tmp", gfile))
        os.remove(os.path.join("static", "tmp_sat", gfile))

    plt.savefig(name3, bbox_inches='tight')
    plt.gcf()
    return os.path.join("tmp_sat", name2)

