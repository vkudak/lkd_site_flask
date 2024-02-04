import csv
import os
import ephem
import numpy as np
from datetime import datetime, timedelta
import math
import json

from bokeh.layouts import gridplot
from bokeh.models import DatetimeTickFormatter, HoverTool, LinearAxis, Range1d
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.embed import file_html


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
            row["Phase"] = [
                (x,
                 (t2phases([y[0]], row["Period"], row["Epoch"])[0],
                  t2phases([y[1]], row["Period"], row["Epoch"])[0]),
                 y[1] - y[0],
                 ) for x, y in row["Phase"].items()
            ]

            for i in range(0, len(row["Phase"])):
                if row["Phase"][i][2] >= row["Period"]:
                    row["Phase"][i] = [row["Phase"][i][0], row["Phase"][i][1], "[" + "*"*50 + "]"]
                else:
                    row["Phase"][i] = [row["Phase"][i][0], row["Phase"][i][1], phase2str(row["Phase"][i][1])]
        else:
            row["Phase"] = ""
        stars.append(row)
    # stars is list of dict [{.star_rec with keys..},{...}, {...}]

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


# def plot_star(star, user):
#     site = ephem.Observer()
#     today = datetime.today()
#     site.date = datetime(today.year, today.month, today.day, 23, 59, 0)  # datetime.now()
#     site.lat = str(user.site_lat)  # "48.63" #loc.lat
#     site.lon = str(user.site_lon)  # "22.33" #loc.lon
#
#     obj = ephem.FixedBody()
#     obj.name = star.star_name
#     obj._ra = ephem.hours(star.ra.replace("h", ":").replace("m", ":")[:-1])
#     obj._dec = ephem.degrees(star.dec.replace("d", ":").replace("m", ":")[:-1])
#     obj.compute(site)
#
#     site.horizon = '-12'
#     sun_set = site.previous_setting(ephem.Sun(), use_center=True).datetime()
#     sun_rise = site.next_rising(ephem.Sun(), use_center=True).datetime()
#
#     site.horizon = '25'
#     try:
#         obj_rise = site.previous_rising(obj).datetime()
#         obj_set = site.next_setting(obj).datetime()
#     except ephem.AlwaysUpError:
#         obj_rise = "alw up"
#         obj_set = "alw up"
#
#     # make t_delta
#     counts = 300
#     # print(obj_rise, obj_set)
#     # print(sun_set, sun_rise)
#     if obj_rise != "alw up":
#         if obj_rise >= sun_set:
#             if obj_set <= sun_rise:
#                 t_delta = date_linspace(obj_rise, obj_set, counts)
#             else:
#                 t_delta = date_linspace(obj_rise, sun_rise, counts)
#         else:
#             t_delta = date_linspace(sun_set, sun_rise, counts)
#     else:
#         t_delta = date_linspace(sun_set, sun_rise, counts)
#
#     moon_alt = []
#     obj_alt = []
#     obj_az = []
#     dt_jd = []
#
#     for dt in t_delta:
#         site.date = dt  # '1984/5/30 16:22:56'  # 12:22:56 EDT
#         moon = ephem.Moon()
#         moon.compute(site)
#         obj.compute(site)
#         moon_alt.append(math.degrees(float(moon.alt)))
#         obj_az.append(math.degrees(float(obj.az)))
#         obj_alt.append(math.degrees(float(obj.alt)))
#         dt_jd.append(get_julian_datetime(dt))
#
#     t_phase = t2phases(dt_jd, star.period, float(star.epoch))
#     t_phase = np.array(t_phase)
#     obj_alt = np.array(obj_alt)
#     obj_az = np.array(obj_az)
#     moon_alt = np.array(moon_alt)
#     t_delta = np.array(t_delta)
#     ####PLOT
#     fig = plt.figure()
#     ax1 = fig.add_subplot(111)
#
#     ax1.plot(t_delta, moon_alt, color="y", ls='--', label='Moon')
#     mappable = ax1.scatter(t_delta, obj_alt, c=obj_az, label=star.star_name, lw=0, s=8, cmap='viridis')
#
#     myfmt = mdates.DateFormatter('%H:%M')  # %Y-%m-%d
#     ax1.xaxis.set_major_formatter(myfmt)
#     plt.gcf().autofmt_xdate()
#
#     # Azimuth axis----------------------------------
#     ax2 = ax1.twiny()
#     ax2.set_xlim(ax1.get_xlim())
#     numElems = 10  # 10 elements evenly spaced on ax2 on the top
#     tt_idx = np.round(np.linspace(0, len(t_delta) - 1, numElems)).astype(int)
#     t_delta = np.array(t_delta)
#     phs = ["%1.2f" % x for x in t_phase]
#     phs = np.array(phs)
#
#     ax2.set_xticks(t_delta[tt_idx])
#     ax2.set_xticklabels(phs[tt_idx])
#     ax2.set_xlabel(r"Phase")
#     ax2.tick_params(axis='x', which='major', pad=0)
#     # -------------------------------------------------
#
#     ax2.plot(t_phase, np.ones(len(t_phase)))
#
#     plt.colorbar(mappable, ax=ax1).set_label('Azimuth [deg]')
#     # plt.legend(loc='upper left')
#
#     ax1.set_ylim(25, max(obj_alt) + 3)
#     ax1.legend()
#     ax1.set_xlabel('Time (UTC) \n' \
#                    + t_delta[0].strftime("%Y-%m-%d") + " -- " + t_delta[-1].strftime("%Y-%m-%d"))
#     ax1.set_ylabel('Altitude [deg]')
#
#     # plt.subplots_adjust(top=0.88)  # to leave the title and not cut it !
#
#     if not os.path.exists(os.path.join("app", "static", "tmp")):
#         os.mkdir(os.path.join("app", "static", "tmp"))
#     name2 = star.star_name + "_" + str(time.time()) + ".png"
#     name3 = f'{os.path.join("app", "static", "tmp", name2)}'
#
#     for gfile in os.listdir(os.path.join("app", "static", "tmp")):
#         # if gfile.startswith(name + '_'):  # not to remove other images
#         #     os.remove(os.path.join("static", "tmp", gfile))
#         os.remove(os.path.join("app", "static", "tmp", gfile))
#
#     fig.savefig(name3, bbox_inches='tight')
#     # plt.clf()
#     # return f'{os.path.join("tmp", name2)}'
#     return os.path.join("tmp", name2)
#     ############


def plot_star_bokeh(star, user):
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

    tools = 'pan,wheel_zoom,box_zoom,reset,save'
    title = f"EB system: {star.star_name}"

    plot = figure(title=title, plot_height=400, plot_width=800,
                  x_axis_type='datetime', min_border=10,
                  y_range=(min(obj_alt)-10, max(obj_alt)+10),
                  tools=tools
                  )

    plot.output_backend = "svg"
    plot.title.align = 'center'

    plot.yaxis.axis_label = r'Elevation [deg]'  # m_st
    # plot.xaxis.axis_label = r"Time [UT]"

    plot.line(t_delta, obj_alt, color='black', line_width=2.)
    plot.line(t_delta, moon_alt, color='yellow', line_width=2.)

    plot.xaxis.ticker.desired_num_ticks = 10
    plot.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                                 minutes=["%H:%M:%S"],
                                                 minsec=["%H:%M:%S"],
                                                 hours=["%H:%M:%S"])

    t_ph_str = [f"{x:.2f}" for x in t_phase]
    t_ph_str = t_ph_str[0::20]  # each 20th point to display

    # exta x axis
    plot.extra_x_ranges['sec_x_axis'] = Range1d(0, len(t_ph_str))
    ax2 = LinearAxis(x_range_name="sec_x_axis", axis_label="phase")
    plot.add_layout(ax2, 'above')

    # set ticker to avoid wrong formatted labels while zooming
    plot.above[0].ticker = list(range(0, len(t_ph_str)))
    # overwrite labels
    plot.above[0].major_label_overrides = {key: item for key, item in zip(range(0, len(t_ph_str)), t_ph_str)}
    # plot.above[0].ticker.desired_num_ticks = 10

    hover = HoverTool(
        tooltips=[
            ('time', '@x{%H:%M:%S.%3N}'),
            ('el/az', '@y'),
            # ('ph', '@sec_x_axis'),
        ],
        formatters={
            '@x': 'datetime',
            '@y': 'numeral',
            # '@sec_x_axis': 'printf'
        },
        mode='mouse'
    )
    plot.add_tools(hover)
    #####

    p2 = figure(plot_height=150, plot_width=800, x_range=plot.x_range,
                y_axis_location="left", x_axis_type='datetime', tools=tools)
    p2.output_backend = "svg"
    p2.yaxis.axis_label = r"Azimuth [deg]"
    p2.xaxis.axis_label = r"Time [UT]"
    p2.line(t_delta, obj_az, color='black', line_width=2.)
    p2.xaxis.ticker.desired_num_ticks = 10
    p2.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                               minutes=["%H:%M:%S"],
                                               minsec=["%H:%M:%S"],
                                               hours=["%H:%M:%S"])
    p2.add_tools(hover)

    layout = gridplot([[plot], [p2]], toolbar_options=dict(logo=None))
    html = file_html(layout, CDN, "EB system AltAz plot")
    return html


def getListOfFiles(dirName):
    # create a list of file and subdirectories
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

