import os
import shutil
import numpy as np
from datetime import datetime, timedelta
import time

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


def get_list_of_files(dirName):
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
            allFiles = allFiles + get_list_of_files(fullPath)
        else:
            allFiles.append(fullPath)
    return allFiles


def add_lc(db, sat_id, band,
           lc_st, lc_end, dt, lctime,
           flux, mag,
           az, el, rg, flux_err=None, mag_err=None, tle=None):
    # check if we already have such LC
    sat = Satellite.get_by_id(id=sat_id)
    # print("     Start processing...")
    # print(f"     Band is {band}")
    lcs, bands = Lightcurve.get_by_lc_start(norad=sat.norad, ut_start=lc_st, bands=True)

    if band in bands:
        return None
    else:
        # we have all data

        # we have "flux_err" and "mag_err"
        if flux_err is not None and mag_err is not None:
            lc = Lightcurve(sat_id=sat_id,
                            band=band, dt=dt,
                            ut_start=parser.parse(lc_st),
                            ut_end=parser.parse(lc_end),
                            date_time=lctime,
                            flux=flux, flux_err=flux_err,
                            mag=mag, mag_err=mag_err,
                            az=az, el=el, rg=rg)
            if tle is not None:
                lc.tle = tle
            db.session.add(lc)
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
                            az=az, el=el, rg=rg)
            if tle is not None:
                lc.tle = tle
            db.session.add(lc)
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
                            az=az, el=el, rg=rg)
            if tle is not None:
                lc.tle = tle
            db.session.add(lc)
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
                            az=az, el=el, rg=rg)
            if tle is not None:
                lc.tle = tle
            db.session.add(lc)
            db.session.commit()
            # print(f"commit with {band} and {lc_st}")


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
                                datetime.strptime(sat_st_date + " " + x[0], "%Y-%m-%d %H:%M:%S.%f")
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


def plot_lc(lc_id):
    color = {"B": "b",
             "V": "g",
             "R": "r",
             "C": "k"}
    lc = Lightcurve.get_by_id(id=lc_id)

    plt.gcf()
    plt.clf()
    grid = True

    # fig im MAG
    plt.rcParams['figure.figsize'] = [12, 6]
    dm = max(lc.mag) - min(lc.mag)
    dm = dm * 0.1
    plt.axis([min(lc.date_time), max(lc.date_time), max(lc.mag) + dm, min(lc.mag) - dm])

    if lc.mag_err is None:
        plt.plot(lc.date_time, lc.mag, f"x{color[lc.band]}-", linewidth=0.5, fillstyle="none", markersize=3)
    else:
        plt.errorbar(lc.date_time, lc.mag, yerr=lc.mag_err, fmt=f"x{color[lc.band]}-",
                     capsize=2, linewidth=0.5, fillstyle="none",
                     markersize=3, ecolor="k")

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
