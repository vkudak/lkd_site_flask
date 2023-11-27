import io
import os
import shutil
import numpy as np
from datetime import datetime, timedelta
import time

from bokeh.layouts import gridplot
from bokeh.models import DatetimeTickFormatter, Text, HoverTool, Scatter, Title, ColumnDataSource, Whisker
from bokeh.plotting import figure
from bokeh.resources import CDN
from bokeh.embed import file_html
from bokeh.models.arrow_heads import TeeHead

from scipy.signal import find_peaks
from astropy.timeseries import LombScargle
from sklearn.preprocessing import minmax_scale
from pdmpy import pdm

from dateutil import parser
from matplotlib import pyplot as plt

from app.models import Satellite, Lightcurve


def del_files_in_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
            pass


def get_list_of_files(dir_name):
    # create a list of file and subdirectories
    # names in the given directory
    list_of_file = os.listdir(dir_name)
    all_files = list()
    # Iterate over all the entries
    for entry in list_of_file:
        # Create full path
        full_path = os.path.join(dir_name, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(full_path):
            all_files = all_files + get_list_of_files(full_path)
        else:
            all_files.append(full_path)
    return all_files


def add_lc(db, sat_id, band,
           lc_st, lc_end, dt, lctime,
           flux, mag,
           site,
           az, el, rg, flux_err=None, mag_err=None,
           tle=None):
    # check if we already have such LC
    sat = Satellite.get_by_id(id=sat_id)
    # print("     Start processing...")
    # print(f"     Band is {band}")
    lcs, bands = Lightcurve.get_by_lc_start(norad=sat.norad, ut_start=lc_st, bands=True)
    dt = float(dt)
    sat = Satellite.get_by_id(sat_id)

    if band in bands:
        # if we already have LC with same ut_start and Band return None
        return None
    else:

        # we have "flux_err" and "mag_err"
        if flux_err is not None and mag_err is not None:
            lc = Lightcurve(sat_id=sat_id,
                            band=band, dt=dt,
                            ut_start=parser.parse(lc_st),
                            ut_end=parser.parse(lc_end),
                            date_time=lctime,
                            flux=flux, flux_err=flux_err,
                            mag=mag, mag_err=mag_err,
                            az=az, el=el, rg=rg,
                            site=site)
            if tle is not None:
                lc.tle = tle

            lc.lsp_period = lsp_calc(lc=lc)
            db.session.add(lc)
            sat.updated = datetime.utcnow()  # lc.ut_start
            db.session.add(sat)
            db.session.commit()

        # we have "flux_err" only. No "mag_err"
        elif flux_err is not None and (mag_err is None):
            lc = Lightcurve(sat_id=sat_id,
                            band=band, dt=dt,
                            ut_start=parser.parse(lc_st),
                            ut_end=parser.parse(lc_end),
                            date_time=lctime,
                            flux=flux, flux_err=flux_err,
                            mag=mag, mag_err=None,
                            az=az, el=el, rg=rg,
                            site=site)
            if tle is not None:
                lc.tle = tle
            lc.lsp_period = lsp_calc(lc=lc)
            db.session.add(lc)
            sat.updated = datetime.utcnow()  # lc.ut_start
            db.session.add(sat)
            db.session.commit()

        # We have "mag_err" only No "flux_err"
        elif mag_err is not None and (flux_err is None):
            lc = Lightcurve(sat_id=sat_id,
                            band=band, dt=dt,
                            ut_start=parser.parse(lc_st),
                            ut_end=parser.parse(lc_end),
                            date_time=lctime,
                            flux=flux, flux_err=None,
                            mag=mag, mag_err=mag_err,
                            az=az, el=el, rg=rg,
                            site=site)
            if tle is not None:
                lc.tle = tle
            lc.lsp_period = lsp_calc(lc=lc)
            db.session.add(lc)
            sat.updated = datetime.utcnow()  # lc.ut_start
            db.session.add(sat)
            db.session.commit()

        # We have no "mag_err" neither "flux_err"
        elif (mag_err is None) and (flux_err is None):
            lc = Lightcurve(sat_id=sat_id,
                            band=band, dt=dt,
                            ut_start=parser.parse(lc_st),
                            ut_end=parser.parse(lc_end),
                            date_time=lctime,
                            flux=flux, flux_err=None,
                            mag=mag, mag_err=None,
                            az=az, el=el, rg=rg,
                            site=site)
            if tle is not None:
                lc.tle = tle
            lc.lsp_period = lsp_calc(lc=lc)
            db.session.add(lc)
            sat.updated = datetime.utcnow()  # lc.ut_start
            db.session.add(sat)
            db.session.commit()
            # print(f"commit with {band} and {lc_st}")


def process_lc_file(file, file_ext, db, app):
    file_content = file.read()
    file_name = file.filename
    # fext = file_ext
    if file_ext == ".phc":
        with io.StringIO(file_content.decode("UTF-8")) as fs:
            sat_st = fs.readline().strip("\n").strip("\r")
            sat_st_date = sat_st.split()[0]
            sat_end = fs.readline().strip("\n").strip("\r")
            for line in fs:
                # line = line.decode("UTF-8")
                if line[:9] == "COSPAR ID":
                    cospar = line.split("=")[1].strip().strip("\n").strip("\r")
                if line[:8] == "NORAD ID":
                    norad = int(line.split("=")[1].strip())
                if line[:4] == "NAME":
                    name = line.split("=")[1].strip().strip("\n").strip("\r")
                    if name[:2] == "0 ":
                        name = name[2:]  # delete leading zero in TLE name line
                if line[:2] == "dt":
                    dt = line.split("=")[1].strip().strip("\n").strip("\r")
            fs.seek(0)
            try:
                # leave LOADTXT here, because format has no '#' comments. Only hardcode skiprows will work
                impB, impV, fonB, fonV, mB, mV, az, el, rg = \
                    np.loadtxt(fs, unpack=True, skiprows=7,
                               usecols=(1, 2, 3, 4, 5, 6, 7, 8, 9)
                               )
                fs.seek(0)
                lctime = np.loadtxt(fs, unpack=True, skiprows=7, usecols=(0,),
                                    dtype={'names': ('time',), 'formats': ('S15',)})

                lctime = [
                    datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f")
                    for x in lctime]
                t0 = lctime[0]
                lctime = [x if t0 - x < timedelta(hours=2) else x + timedelta(days=1) for x in
                          lctime]  # add DAY after 00:00:00

                sat = Satellite.get_by_norad(norad=norad)

                if sat is None:
                    sat = Satellite(name=name, norad=norad, cospar=cospar)  # add satellite
                    db.session.add(sat)
                    db.session.commit()

                # print(f"Add LC. file = {file}")

                add_lc(db=db, sat_id=sat.id, band="B",
                       lc_st=sat_st, lc_end=sat_end,
                       dt=dt, lctime=lctime,
                       flux=impB, mag=mB,
                       az=az, el=el, rg=rg,
                       site="Uzhhorod")

                add_lc(db=db, sat_id=sat.id, band="V",
                       lc_st=sat_st, lc_end=sat_end,
                       dt=dt, lctime=lctime,
                       flux=impV, mag=mV,
                       az=az, el=el, rg=rg,
                       site="Uzhhorod")
                return True

            except Exception as e:
                app.logger.warning(f"error: {e}\nBed format PHC in file = {file_name}")
                # return {'error': e, "message": f"bed format PHC in file = {file_content}"}
                # print(e)
                # print("bed format PHC in file =", file)
                pass

    elif file_ext[:3] == ".ph":  # .phX where X is [B, V, R, C or others!]
        with io.StringIO(file_content.decode("UTF-8")) as fs:
            fs.readline()
            # fs.readline()
            # fs.readline()
            # fs.readline()
            tle = fs.readline()[2:] + fs.readline()[2:] + fs.readline()[2:]

            sat_st = fs.readline().strip("\n").strip("\r")[2:].strip()[:-1]
            sat_st_date = sat_st.split()[0]

            sat_end = fs.readline().strip("\n").strip("\r")[2:].strip()[:-1]

            # Default values
            site_name = "Derenivka"
            filt = file_ext[3:] # Get filter from file extension if not available in header

            # Check header
            for line in fs:
                l = line.split(" = ")
                if l[0] == "# COSPAR":
                    cospar = l[1].strip("\n").strip("\r")
                if l[0] == "# NORAD ":
                    norad = int(l[1])
                if l[0] == "# NAME  ":
                    name = l[1].strip("\n").strip("\r")
                    if name[:2] == "0 ":
                        name = name[2:]  # delete leading zero in TLE name line
                if l[0] == "# dt":
                    dt = l[1].strip("\n").strip("\r")
                if l[0] == "# SITE_NAME  ":
                    site_name = l[1].strip("\n").strip("\r")
                if l[0] == "# Filter":
                    filt = l[1].strip("\n").strip("\r")
            fs.seek(0)

            try:  # ##################################
                flux, flux_err, m, merr, az, el, rg = np.genfromtxt(fs, skip_header=True,
                                                                    usecols=(6, 7, 8, 9, 10, 11, 12,),
                                                                    unpack=True)
                fs.seek(0)
                lcd, lct = np.genfromtxt(fs, skip_header=True, unpack=True, usecols=(0, 1,),
                                       dtype=None, encoding="utf-8")
                lctime = list(zip(lcd, lct))
                lctime = [x[0] + " " + x[1] for x in lctime]
                lctime = [datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f") for x in lctime]

                # Bed option
                # lctime = [x + " " + t for x in lcd for t in lct]
                # lctime = [datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f") for x in lctime]

                sat = Satellite.get_by_norad(norad=norad)
                if not sat:  # sat == []
                    sat = Satellite(name=name, norad=norad, cospar=cospar)  # add satellite
                    db.session.add(sat)
                    db.session.commit()
                    sat = Satellite.get_by_norad(norad=norad)

                add_lc(db=db, sat_id=sat.id, band=filt,
                       lc_st=sat_st, lc_end=sat_end,
                       dt=dt, tle=tle, lctime=lctime,
                       flux=flux, flux_err=flux_err,
                       mag=m, mag_err=merr,
                       az=az, el=el, rg=rg,
                       site=site_name)
                return True

            except Exception as e:
                # if str(e) == "list index out of range":   # no merr
                # print(e.__class__.__name__)
                # print(type(e.__class__.__name__))
                # print(e.__class__ is IndexError)
                if e.__class__ is IndexError:  # no merr
                    # print("No m_err")
                    fs.seek(0)
                    flux, flux_err, m, az, el, rg = np.genfromtxt(fs, skip_header=True,
                                                                  usecols=(5, 6, 7, 8, 9, 10,),
                                                                  unpack=True)
                    # flux, flux_err, m, az, el, rg = np.loadtxt(fs, unpack=True, skiprows=11,
                    #                                            usecols=(5, 6, 7, 8, 9, 10))
                    fs.seek(0)
                    lcd, lct = np.genfromtxt(fs, skip_header=True, unpack=True, usecols=(0, 1,),
                                             dtype=None, encoding="utf-8")
                    # lctime = [x + " " + t for x in lcd for t in lct]
                    lctime = list(zip(lcd, lct))
                    lctime = [x[0] + " " + x[1] for x in lctime]
                    lctime = [datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f") for x in lctime]

                    sat = Satellite.get_by_norad(norad=norad)
                    if sat is None:
                        sat = Satellite(name=name, norad=norad, cospar=cospar)  # add satellite
                        db.session.add(sat)
                        db.session.commit()

                    add_lc(db=db, sat_id=sat.id, band=filt,
                           lc_st=sat_st, lc_end=sat_end,
                           dt=dt, tle=tle, lctime=lctime,
                           flux=flux, flux_err=flux_err,
                           mag=m, mag_err=None,
                           az=az, el=el, rg=rg,
                           site=site_name)
                else:
                    app.logger.error(f"Error: {e}")
                    app.logger.error(f"Bed format PHX in file = {file_name}")
                    # return {'error': e, "message": f"Bed format PHX in file= {file_content}"}
                    # print(e.__class__.__name__)
                    # print("Error = ", e, e.__class__.__name__)
                    # print("Bed format PHR in file")

                    # If error occurs there is a chance that we have satellite without LCs
                    # This will delete such records
                    app.logger.info("Fixing possible 'Satellite without LCs' issue...")
                    Satellite.clear_empty_records()
                    app.logger.info("Done.")
                pass


def process_lc_files(lc_flist, db):
    for file in lc_flist:
        # read the file if its file
        if not os.path.isdir(file):
            _, fext = os.path.splitext(file)
            if file.endswith(".phc"):
                with open(file, "r") as fs:
                    sat_st = fs.readline().strip("\n").strip("\r")
                    sat_st_date = sat_st.split()[0]
                    sat_end = fs.readline().strip("\n").strip("\r")
                    for line in fs:
                        # line = line.decode("UTF-8")
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
                        impB, impV, fonB, fonV, mB, mV, az, el, rg = \
                            np.loadtxt(fs, unpack=True, skiprows=7,
                                       usecols=(1, 2, 3, 4, 5, 6, 7, 8, 9)
                                       )
                        fs.seek(0)
                        lctime = np.loadtxt(fs, unpack=True, skiprows=7, usecols=(0,),
                                            dtype={'names': ('time',), 'formats': ('S15',)})

                        lctime = [
                            datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f")
                            for x in lctime]
                        t0 = lctime[0]
                        lctime = [x if t0 - x < timedelta(hours=2) else x + timedelta(days=1) for x in
                                  lctime]  # add DAY after 00:00:00

                        sat = Satellite.get_by_norad(norad=norad)

                        if sat is None:
                            sat = Satellite(name=name, norad=norad, cospar=cospar)  # add satellite
                            db.session.add(sat)
                            db.session.commit()

                        # print(f"Add LC. file = {file}")

                        add_lc(db=db, sat_id=sat.id, band="B",
                               lc_st=sat_st, lc_end=sat_end,
                               dt=dt, lctime=lctime,
                               flux=impB, mag=mB,
                               az=az, el=el, rg=rg)

                        add_lc(db=db, sat_id=sat.id, band="V",
                               lc_st=sat_st, lc_end=sat_end,
                               dt=dt, lctime=lctime,
                               flux=impV, mag=mV,
                               az=az, el=el, rg=rg)

                    except Exception as e:
                        print(e)
                        print("bed format PHC in file =", file)
                        pass

            elif fext[:3] == ".ph":  # .ph R B V C and others!
                with open(file) as fs:
                    fs.readline()
                    # fs.readline()
                    # fs.readline()
                    # fs.readline()
                    tle = fs.readline()[2:] + fs.readline()[2:] + fs.readline()[2:]

                    sat_st = fs.readline().strip("\n").strip("\r")[2:].strip()[:-1]
                    sat_st_date = sat_st.split()[0]

                    sat_end = fs.readline().strip("\n").strip("\r")[2:].strip()[:-1]

                    for line in fs:
                        l = line.split(" = ")
                        if l[0] == "# COSPAR":
                            cospar = l[1].strip("\n").strip("\r")
                        if l[0] == "# NORAD ":
                            norad = int(l[1])
                        if l[0] == "# NAME  ":
                            name = l[1].strip("\n").strip("\r")
                        if l[0] == "# dt":
                            dt = l[1].strip("\n").strip("\r")
                    fs.seek(0)
                    # read TLE
                    try:  # ##################################
                        flux, flux_err, m, merr, az, el, rg = np.loadtxt(fs, unpack=True, skiprows=11,
                                                                         usecols=(6, 7, 8, 9, 10, 11, 12))
                        fs.seek(0)
                        lctime = np.loadtxt(fs, unpack=True, skiprows=11, usecols=(1,),
                                            dtype={'names': ('time',), 'formats': ('S14',)})
                        lctime = [
                            datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f")
                            for x in lctime]
                        t0 = lctime[0]
                        lctime = [x if t0 - x < timedelta(hours=2) else x + timedelta(days=1) for x in
                                  lctime]  # add DAY after 00:00:00

                        sat = Satellite.get_by_norad(norad=norad)
                        if not sat:  # sat == []
                            sat = Satellite(name=name, norad=norad, cospar=cospar)  # add satellite
                            db.session.add(sat)
                            db.session.commit()
                            sat = Satellite.get_by_norad(norad=norad)

                        add_lc(db=db, sat_id=sat.id, band=fext[3:],
                               lc_st=sat_st, lc_end=sat_end,
                               dt=dt, tle=tle, lctime=lctime,
                               flux=flux, flux_err=flux_err,
                               mag=m, mag_err=merr,
                               az=az, el=el, rg=rg)

                    except Exception as e:
                        # if str(e) == "list index out of range":   # no merr
                        # print(e.__class__.__name__)
                        # print(type(e.__class__.__name__))
                        # print(e.__class__ is IndexError)
                        if e.__class__ is IndexError:  # no merr
                            # print("No m_err")
                            fs.seek(0)
                            flux, flux_err, m, az, el, rg = np.loadtxt(fs, unpack=True, skiprows=11,
                                                                       usecols=(5, 6, 7, 8, 9, 10))
                            fs.seek(0)
                            lctime = np.loadtxt(fs, unpack=True, skiprows=11, usecols=(1,),
                                                dtype={'names': ('time',), 'formats': ('S14',)})
                            lctime = [
                                datetime.strptime(sat_st_date + " " + x[0].decode('UTF-8'), "%Y-%m-%d %H:%M:%S.%f")
                                for x in lctime]
                            t0 = lctime[0]
                            lctime = [x if t0 - x < timedelta(hours=2) else x + timedelta(days=1) for x in
                                      lctime]  # add DAY after 00:00:00

                            sat = Satellite.get_by_norad(norad=norad)
                            if sat is None:
                                sat = Satellite(name=name, norad=norad, cospar=cospar)  # add satellite
                                db.session.add(sat)
                                db.session.commit()

                            add_lc(db=db, sat_id=sat.id, band=fext[3:],
                                   lc_st=sat_st, lc_end=sat_end,
                                   dt=dt, tle=tle, lctime=lctime,
                                   flux=flux, flux_err=flux_err,
                                   mag=m, mag_err=None,
                                   az=az, el=el, rg=rg)
                        else:
                            # print(e.__class__.__name__)
                            print("Error = ", e, e.__class__.__name__)
                            print("Bed format PHR in file =", file)
                        pass


def plot_lc_bokeh(lc_id):
    color = {"B": "blue",
             "V": "green",
             "R": "red",
             "C": "black"}
    lc = Lightcurve.get_by_id(id=lc_id)
    dt = str(lc.dt).strip('\n')

    # source = ColumnDataSource(data=dict(base=lc.date_time, mag=lc.mag))

    tools = 'pan,wheel_zoom,box_zoom,reset,save'
    title = f"Satellite Name:{lc.sat.name}, NORAD:{lc.sat.norad}, COSPAR:{lc.sat.cospar}" + ", " + \
            "\n" + \
            f"LC start={lc.ut_start}  dt={dt}  Filter={lc.band} Observatory={lc.site}"
    if lc.mag_err is None:
        dm = 0.1
    else:
        dm = max(lc.mag_err)

    plot = figure(title=title, plot_height=400, plot_width=800,
                  x_axis_type='datetime', min_border=10,
                  y_range=(max(lc.mag) + dm, min(lc.mag) - dm),
                  tools=tools
                  )

    plot.output_backend = "svg"
    plot.title.align = 'center'
    # plot.yaxis.axis_label = r"$$\textrm{m}_{st}~\textrm{[mag]}$$"
    # https://www.geeksforgeeks.org/how-to-print-superscript-and-subscript-in-python/
    plot.yaxis.axis_label = u'm\u209B\u209c [mag]'  # m_st
    plot.xaxis.axis_label = r"UT"

    source = ColumnDataSource(dict(x=lc.date_time, mag=lc.mag))

    if lc.mag_err is None:
        plot.line(lc.date_time, lc.mag, color=f"{color[lc.band]}", line_width=0.5)
        # plot.scatter(lc.date_time, lc.mag, color=f"{color[lc.band]}", marker="x")
        glyph = Scatter(x="x", y="mag", size=5, marker="x", line_color=f"{color[lc.band]}")
        plot.add_glyph(source, glyph)
    else:
        plot.line(lc.date_time, lc.mag, color=f"{color[lc.band]}", line_width=0.5)
        # plot.scatter(lc.date_time, lc.mag, color=f"{color[lc.band]}", marker="x")
        glyph = Scatter(x="x", y="mag", size=5, marker="x", line_color=f"{color[lc.band]}")
        plot.add_glyph(source, glyph)

        base, lower, upper = [], [], []
        for i in range(0, len(lc.mag)):
            base.append(lc.date_time[i])
            lower.append(lc.mag[i] - lc.mag_err[i])
            upper.append(lc.mag[i] + lc.mag_err[i])

        source_error = ColumnDataSource(data=dict(base=base, lower=lower, upper=upper))
        plot.add_layout(
            Whisker(source=source_error, base="base", upper="upper", lower="lower",
                    line_color=f"{color[lc.band]}",
                    upper_head=TeeHead(line_color=f"{color[lc.band]}", size=5),
                    lower_head=TeeHead(line_color=f"{color[lc.band]}", size=5)
                    )
        )

        ###############
        # x2 = ["%3.1f; %3.1f" % (alt, az) for alt, az in zip(lc.el, lc.az)]
        # x2 = np.array(x2)
        # plot.extra_x_ranges['sec_x_axis'] = Range1d(0, 100)
        # ax2 = LinearAxis(x_range_name="sec_x_axis", axis_label="secondary x-axis")
        # ax2.formatter = FuncTickFormatter(args={"y": x2, "x": np.linspace(0, 100, x2.size)}, code="""
        #      if (tick <= x[0])
        #        return y[0].toFixed(2)
        #      if (tick >= x[x.length - 1])
        #        return y[x.length-1].toFixed(2)
        #      let indexOfNumberToCompare, leftBorderIndex = 0, rightBorderIndex = x.length - 1
        #      //Reduce searching range till it find an interval point belongs to using binary search
        #      while (rightBorderIndex - leftBorderIndex !== 1) {
        #        indexOfNumberToCompare = leftBorderIndex + Math.floor((rightBorderIndex - leftBorderIndex)/2)
        #        tick >= x[indexOfNumberToCompare] ? leftBorderIndex = indexOfNumberToCompare : rightBorderIndex = indexOfNumberToCompare
        #      }
        #      return y[leftBorderIndex].toFixed(2)
        #    """)
        # plot.add_layout(ax2, 'above')
        ##################

    plot.xaxis.ticker.desired_num_ticks = 10
    plot.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                                 minutes=["%H:%M:%S"],
                                                 minsec=["%H:%M:%S"],
                                                 hours=["%H:%M:%S"])

    hover = HoverTool(
        tooltips=[
            ('time', '@x{%H:%M:%S.%3N}'),
            ('mag', '@mag'),
        ],
        formatters={
            '@x': 'datetime',
            'mag': 'numeral',
        },
        mode='mouse'
    )
    plot.add_tools(hover)
    #####

    p2 = figure(plot_height=150, plot_width=800, x_range=plot.x_range,
                y_axis_location="left", x_axis_type='datetime')
    p2.output_backend = "svg"
    p2.yaxis.axis_label = r"elevation [deg]"
    p2.line(lc.date_time, lc.el, color='black', line_width=0.5)
    p2.xaxis.ticker.desired_num_ticks = 10
    p2.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                               minutes=["%H:%M:%S"],
                                               minsec=["%H:%M:%S"],
                                               hours=["%H:%M:%S"])

    p3 = figure(plot_height=150, plot_width=800, x_range=plot.x_range,
                y_axis_location="left", x_axis_type='datetime')
    p3.output_backend = "svg"
    p3.yaxis.axis_label = r"Azimuth [deg]"
    p3.line(lc.date_time, lc.az, color='black', line_width=0.5)
    p3.xaxis.ticker.desired_num_ticks = 10
    p3.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                               minutes=["%H:%M:%S"],
                                               minsec=["%H:%M:%S"],
                                               hours=["%H:%M:%S"])
    layout = gridplot([[plot], [p2], [p3]], toolbar_options=dict(logo=None))

    html = file_html(layout, CDN, "LC plot")
    # html = file_html(plot, CDN, "my plot")
    return lc, html


def plot_lc_multi_bokeh(lc_id):
    color = {"B": "blue",
             "V": "green",
             "R": "red",
             "C": "black"}
    lc_selected = Lightcurve.get_by_id(id=lc_id)
    lcs = Lightcurve.get_synch_lc(lc_id, diff_in_sec=300) # list of synch LCs

    bands = ",".join([lc.band for lc in lcs])
    dts = ";".join([str(lc.dt) for lc in lcs])

    # dt = str(lc_selected.dt).strip('\n')
    tools = 'pan,wheel_zoom,box_zoom,reset,save'

    title1 = f"Satellite Name:{lc_selected.sat.name}, NORAD:{lc_selected.sat.norad}, COSPAR:{lc_selected.sat.cospar},"
    title1 = f'{title1:^100}'

    title2 = f"LC start={lc_selected.ut_start}  dt={dts}  Filter={bands} Observatory={lc_selected.site}"
    title2 = f'{title2:^100}'

    # title = f"Satellite Name:{lc_selected.sat.name}, NORAD:{lc_selected.sat.norad}, COSPAR:{lc_selected.sat.cospar}" + ", " + \
    #         "\n" + \
    #         f"LC start={lc_selected.ut_start}  dt={dts}  Filter={bands} Observatory={lc_selected.site}"

    list_ar = []
    for i in range(0, len(lcs)):
        list_ar.append(lcs[i].mag)

    all_mag = np.concatenate(list_ar, axis=0)

    max_mag = max(all_mag)
    min_mag = min(all_mag)

    if lc_selected.mag_err is None:
        dm = 0.1
    else:
        dm = max(lc_selected.mag_err)

    title = title1 + "\n" + title2
    p1 = figure(title=title, plot_height=400, plot_width=800,
                x_axis_type='datetime', min_border=10,
                y_range=(max_mag + dm, min_mag - dm),
                tools=tools
                )

    p1.output_backend = "svg"
    p1.title.align = 'center'

    p1.yaxis.axis_label = u'm\u209B\u209c [mag]'  # m_st
    p1.xaxis.axis_label = r"UT"

    for lc in lcs:
        source = ColumnDataSource(dict(x=lc.date_time, mag=lc.mag))

        if lc.mag_err is None:
            p1.line(lc.date_time, lc.mag, color=f"{color[lc.band]}", line_width=0.5)
            # plot.scatter(lc.date_time, lc.mag, color=f"{color[lc.band]}", marker="x")
            glyph = Scatter(x="x", y="mag", size=5, marker="x", line_color=f"{color[lc.band]}")
            p1.add_glyph(source, glyph)
        else:
            p1.line(lc.date_time, lc.mag, color=f"{color[lc.band]}", line_width=0.5)
            # plot.scatter(lc.date_time, lc.mag, color=f"{color[lc.band]}", marker="x")
            glyph = Scatter(x="x", y="mag", size=5, marker="x", line_color=f"{color[lc.band]}")
            p1.add_glyph(source, glyph)

            base, lower, upper = [], [], []
            for i in range(0, len(lc.mag)):
                base.append(lc.date_time[i])
                lower.append(lc.mag[i] - lc.mag_err[i])
                upper.append(lc.mag[i] + lc.mag_err[i])

            source_error = ColumnDataSource(data=dict(base=base, lower=lower, upper=upper))
            p1.add_layout(
                Whisker(source=source_error, base="base", upper="upper", lower="lower",
                        line_color=f"{color[lc.band]}",
                        upper_head=TeeHead(line_color=f"{color[lc.band]}", size=5),
                        lower_head=TeeHead(line_color=f"{color[lc.band]}", size=5)
                        )
            )

        p1.xaxis.ticker.desired_num_ticks = 10
        p1.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                                     minutes=["%H:%M:%S"],
                                                     minsec=["%H:%M:%S"],
                                                     hours=["%H:%M:%S"])

        hover = HoverTool(
            tooltips=[
                ('time', '@x{%H:%M:%S.%3N}'),
                ('mag', '@mag'),
            ],
            formatters={
                '@x': 'datetime',
                'mag': 'numeral',
            },
            mode='mouse'
        )
        p1.add_tools(hover)
        #####

    p2 = figure(plot_height=150, plot_width=800, x_range=p1.x_range,
                y_axis_location="left", x_axis_type='datetime')
    p2.output_backend = "svg"
    p2.yaxis.axis_label = r"elevation [deg]"
    for lc in lcs:
        p2.line(lc.date_time, lc.el, color='black', line_width=0.5)
    p2.xaxis.ticker.desired_num_ticks = 10
    p2.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                               minutes=["%H:%M:%S"],
                                               minsec=["%H:%M:%S"],
                                               hours=["%H:%M:%S"])

    p3 = figure(plot_height=150, plot_width=800, x_range=p1.x_range,
                y_axis_location="left", x_axis_type='datetime')
    p3.output_backend = "svg"
    p3.yaxis.axis_label = r"Azimuth [deg]"
    for lc in lcs:
        p3.line(lc.date_time, lc.az, color='black', line_width=0.5)
    p3.xaxis.ticker.desired_num_ticks = 10
    p3.xaxis.formatter = DatetimeTickFormatter(seconds=["%H:%M:%S"],
                                               minutes=["%H:%M:%S"],
                                               minsec=["%H:%M:%S"],
                                               hours=["%H:%M:%S"])
    layout = gridplot([[p1], [p2], [p3]], toolbar_options=dict(logo=None))

    html = file_html(layout, CDN, "LC plot")
    # html = file_html(plot, CDN, "my plot")
    return lc_selected, html


def lsp_calc(lc_id=None, lc=None):
    """
    Args:
        lc_id: id of LC (option #1 preferred)
        lc: Lightcurve object (option #2)

    Returns: None if Aperiodic or Period with the highest Power
    """
    if lc_id:
        lc = Lightcurve.get_by_id(id=lc_id)
    lctime = lc.date_time

    lctime = [x.timestamp() for x in lctime]

    if lc.dt < 1:
        max_freq = 0.83  # / (2 * lc.dt)
    else:
        max_freq = 1 / (2 * lc.dt)
    min_freq = 1 / ((lctime[-1] - lctime[0]) / 2)

    if lc.mag_err is not None:
        ls = LombScargle(lctime, lc.mag, lc.mag_err)
    else:
        ls = LombScargle(lctime, lc.mag)

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
        return None
    else:
        zipped_lists = zip(power[peaks], periods[peaks])
        sorted_pairs = sorted(zipped_lists, reverse=True)

        # Return period with higher power
        return sorted_pairs[0][1]


def lsp_plot_bokeh(lc_id, return_lc=False, return_period=False):
    """
    Args:
        lc_id: id of LC
        return_lc: return LC with parameters for further purposes
        return_period: calculated Period value, or "None"

    Returns: Bokeh html plot of LSP Periodogram
             Optionally return also LC and Period value
    """
    lc = Lightcurve.get_by_id(id=lc_id)
    lctime = lc.date_time
    lctime = [x.timestamp() for x in lctime]

    if lc.dt < 1:
        max_freq = 0.83 #/ (2 * lc.dt)
    else:
        max_freq = 1 / (2 * lc.dt)

    min_freq = 1 / ((lctime[-1] - lctime[0]) / 2)

    if lc.mag_err is not None:
        ls = LombScargle(lctime, lc.mag, lc.mag_err)
    else:
        ls = LombScargle(lctime, lc.mag)

    frequency, power = ls.autopower(
        # nyquist_factor=0.5,
        minimum_frequency=min_freq,
        maximum_frequency=max_freq,
        samples_per_peak=30,
        normalization='standard')

    periods = 1.0 / frequency

    probabilities = [0.0001]
    fap = ls.false_alarm_level(probabilities)
    peaks, _ = find_peaks(power, height=fap[0])
    # print(fap)
    # print(periods)

    hover = HoverTool(
        tooltips=[
            ('period', '@x'),
            ('power', '@y{0.0000}'),
        ],
        formatters={
            'period': 'numeral',
            'power': 'numeral',
        },
        mode='mouse'
    )

    # PLOT
    tools = 'pan,wheel_zoom,box_zoom,reset,save'
    plot = figure(title="Lomb-Scargle Periodogram", plot_height=400, plot_width=800,
                  min_border=10, tools=tools)
    plot.add_tools(hover)
    plot.output_backend = "svg"
    plot.title.align = 'center'
    plot.xaxis.axis_label = 'Period [Seconds]'
    plot.yaxis.axis_label = "Power"

    plot.line(periods, power, color="black", line_width=0.5, legend_label="Periodogram")
    plot.line([periods.min(), periods.max()], [fap[0], fap[0]],
              line_width=0.5, color="black", line_dash='dashdot', legend_label="0.01% FAP")
    plot.scatter(periods[peaks], power[peaks], marker="x", size=10)

    x = [x for x in periods[peaks]]
    y = [y for y in power[peaks]]
    text = list(map(lambda x: "%2.3f" % x, periods[peaks]))

    source = ColumnDataSource(dict(x=x, y=y, text=text))
    glyph = Text(x="x", y="y", text="text", angle=0.0, text_color="black")
    plot.add_glyph(source, glyph)

    lsp_html = file_html(plot, CDN, "my plot")

    if not peaks.any():
        period = None
    else:
        period = periods[np.argmax(power)]

    if return_lc:
        res = [lsp_html, lc]
    else:
        res = [lsp_html]

    if return_period:
        res.append(period)

    if return_period is False and return_lc is False:
        return lsp_html
    else:
        return res


def norm_lc(flux, mag=True, norm_range=(0, 1)):
    if mag is False:
        k = 1
    else:
        k = -1
    return minmax_scale(k * flux, feature_range=norm_range)


def get_phases(t, t0, p):
    """
    Create phases list
        Args:
            t: time in LC
            t0: initial time epoch
            p: period of LC
        Return:
            List of phases
    """
    t = np.array(t)
    ph = np.mod(t - t0, p)/float(p)
    return ph


def plot_phased_lc(lc, period):
    """
    Create phased plot of LC
    Args:
        lc: lc instance
        period: possible period in seconds (from LSP method)
    Return:
        Two plots - one with Period from LSP, second with Period defined with PDM method where P is +/- 3 *P_lsp
        If period is None - return None
    """
    if period is None:
        return None
    else:
        t = [x.timestamp() for x in lc.date_time]
        mag_norm = norm_lc(lc.mag)
        phase1 = get_phases(t, t[0], period)

        # new period search
        freq, theta = pdm(t, mag_norm,
                          f_min=1./period/3., f_max=1./period*3.0, delf=1e-5)  # 1e-6 ???
        period2 = 1 / freq[np.argmin(theta)]
        #####
        phase2 = get_phases(t, t[0], period2)

        # PLOT
        tools = 'pan,wheel_zoom,box_zoom,reset,save'
        # title = f"Phased LC with \nPeriod={period:.3f} sec and Epoch={lc.date_time[0]}",
        plot = figure(plot_height=400, plot_width=800, min_border=10, tools=tools)
        plot.add_layout(Title(text=f"Period={period:.3f} sec and Epoch={lc.date_time[0]}",
                               align='center'), 'above')
        plot.add_layout(Title(text="Phased LC with LSP Period",
                               text_font_size="12pt", align='center'), 'above')

        plot.output_backend = "svg"
        plot.title.align = 'center'
        plot.xaxis.axis_label = 'Phase'
        plot.yaxis.axis_label = "Normalized magnitude"
        plot.scatter(phase1, mag_norm, marker="o", size=3)
        p1 = file_html(plot, CDN, "phased_lc")

        # Second plot with Period +/- 3P
        plot2 = figure(plot_height=400, plot_width=800, min_border=10, tools=tools)

        plot2.add_layout(Title(text=f"Period={period2:.3f} sec and Epoch={lc.date_time[0]}",
                               align='center'), 'above')
        plot2.add_layout(Title(text=r"Phased LC with Period defined by PDM method (in borders +/- 3*P_lsp)",
                               text_font_size="12pt", align='center'), 'above')

        plot2.output_backend = "svg"
        plot2.title.align = 'center'
        plot2.xaxis.axis_label = 'Phase'
        plot2.yaxis.axis_label = "Normalized magnitude"
        plot2.scatter(phase2, mag_norm, marker="o", size=3)
        p2 = file_html(plot2, CDN, "phased_lc2")

        return [p1, p2]


def plot_lc(lc_id):
    color = {"B": "b",
             "V": "g",
             "R": "r",
             "C": "k"}
    lc = Lightcurve.get_by_id(id=lc_id)

    plt.gcf()
    plt.clf()
    grid = True

    fig, ax = plt.subplots()
    # ax.xaxis_date()

    # fig im MAG
    plt.rcParams['figure.figsize'] = [12, 6]
    dm = max(lc.mag) - min(lc.mag)
    dm = dm * 0.1
    plt.axis([min(lc.date_time), max(lc.date_time), max(lc.mag) + dm, min(lc.mag) - dm])
    # ax.set_xlim([min(lc.date_time), max(lc.date_time)])
    # ax.set_ylim([max(lc.mag) + dm, min(lc.mag) - dm])

    if lc.mag_err is None:
        plt.plot(lc.date_time, lc.mag, f"x{color[lc.band]}-", linewidth=0.5, fillstyle="none", markersize=3)
    else:
        plt.errorbar(lc.date_time, lc.mag, yerr=lc.mag_err, fmt=f"x{color[lc.band]}-",
                     capsize=2, linewidth=0.5, fillstyle="none",
                     markersize=3, ecolor="k")
    # plt
    plt.title("Satellite Name:%s, NORAD:%s, COSPAR:%s \n LC start=%s  dt=%s  Filter=%s" % (
        lc.sat.name, lc.sat.norad, lc.sat.cospar, lc.ut_start, str(lc.dt).strip("\n"), lc.band),
              pad=6, fontsize=12)

    plt.ylabel(r'$m_{st}$')
    plt.xlabel('UT')
    ax = plt.gca()

    # Azimuth axis----------------------------------
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    numElems = 6
    tt_idx = np.round(np.linspace(0, len(lc.date_time) - 1, numElems)).astype(int)
    Tt2 = np.array(lc.date_time)
    Az2 = np.array(lc.az)
    El2 = np.array(lc.el)

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

    if not os.path.exists(os.path.join("app", "static", "tmp_sat")):
        os.mkdir(os.path.join("app", "static", "tmp_sat"))
    name2 = lc.sat.name + "_" + str(time.time()) + ".png"
    name3 = f'{os.path.join("app", "static", "tmp_sat", name2)}'

    for gfile in os.listdir(os.path.join("app", "static", "tmp_sat")):
        # if gfile.startswith(name + '_'):  # not to remove other images
        #     os.remove(os.path.join("static", "tmp", gfile))
        os.remove(os.path.join("app", "static", "tmp_sat", gfile))

    plt.savefig(name3, bbox_inches='tight')
    plt.gcf()
    return lc, os.path.join("tmp_sat", name2)


def calc_period_for_all_lc():
    """
    Patch Period value if it is None or not calculated at all
    Returns: period for all LCs
    """
    lcs = Lightcurve.get_all()
    for lc in lcs:
        lc.calc_period()


def calc_sat_updated_for_all_sat():
    """
    Patch Updated value for all satellites
    Returns: last LC datetime
    """
    sats = Satellite.get_all()
    for sat in sats:
        sat.update_updated()