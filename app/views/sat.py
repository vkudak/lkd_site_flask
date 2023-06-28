import os

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify, Response
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, MultipleFileField, SubmitField, RadioField, IntegerField
from wtforms.validators import Length, DataRequired
import datetime

from app import cache
from app.models import Satellite, db, Lightcurve
from app.sat_utils import plot_lc_bokeh, process_lc_file, lsp_plot_bokeh, plot_lc_multi_bokeh

# FOR PATCH case
from app.sat_utils import lsp_calc, calc_period_for_all_lc, calc_sat_updated_for_all_sat

sat_bp = Blueprint('sat', __name__)
basedir = os.path.abspath(os.path.dirname(__file__))


def generate_report(date_from, date_to):
    lcs = Lightcurve.report_lcs(date_from, date_to)
    res = [{'sat_name': lc.sat.name,
            'sat_norad': lc.sat.norad,
            'sat_cospar': lc.sat.cospar,
            'lc_st': lc.ut_start.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'lc_band': lc.band,
            'lc_site': lc.site}
           for lc in lcs]
    res = sorted(res, key=lambda k: (k['sat_norad'], k['lc_st']))

    # Turn to text
    text = ''
    norad = 0
    for r in res:
        if norad == r['sat_norad']:  # if satellite is repeating
            text += " " * 43
            text += f"{r['lc_st']}  {r['lc_band']:3}  {r['lc_site']:10}\n"
        else:
            # text += f"{r['sat_name']:25}  {r['sat_norad']:6}  {r['sat_cospar']:8}"
            t = f'"{r["sat_name"]}",({r["sat_cospar"]}/{r["sat_norad"]})'
            text += f"{t:43}"
            text += f"{r['lc_st']}  {r['lc_band']:3}  {r['lc_site']:10}\n"
        norad = r['sat_norad']

    return text


@sat_bp.route('/sat_phot.html', methods=['GET', 'POST'])
@login_required
def sat_phot():
    # PATCH LC without calculated Period
    # Uncomment to recalc ALL LCs period  (about 7-10 min procedure !)
    # calc_period_for_all_lc()

    # PATCH add updated time to each satellite record
    # calc_sat_updated_for_all_sat()

    if current_user.sat_access:
        lc_form = AddLcForm()

        today = datetime.date.today()
        report_form = ReportForm()

        if request.method == "GET":
            report_form.d_from.data = today.strftime("%Y-%m-%d")
            report_form.d_to.data = today.strftime("%Y-%m-%d")
            return render_template("sat_phot.html",
                                   sats=Satellite.get_all(),
                                   lc_form=lc_form,
                                   report_form=report_form,
                                   user=current_user)
        else:  # POST
            if lc_form.validate_on_submit() and lc_form.add.data:
                # print(lc_form.lc_file.data, end="  ")
                for file in lc_form.lc_file.data:
                    file_ext = os.path.splitext(file.filename)
                    file_ext = file_ext[1]
                    if len(file_ext) > 2:
                        file_ext = file_ext[:3]
                    current_app.logger.info(f'Checking file {file.filename} has allowed extension ...')
                    if file_ext in current_app.config['UPLOAD_EXTENSIONS']:
                        current_app.logger.info(f'Processing file {file.filename}...')
                        _, fext = os.path.splitext(file.filename)
                        process_res = process_lc_file(file=file, file_ext=fext, db=db, app=current_app)
                        if process_res:
                            current_app.logger.info(f'File {file.filename} successfully processed')
                        else:
                            current_app.logger.warning(f"""File {file.filename} processed with error
                            \nSkipping this file....""")
                    else:
                        current_app.logger.warning(f'''wrong file ext in {file.filename}.
                                                   \nSkipping this file....''')
                return redirect(url_for("sat.sat_phot"))

            if report_form.validate_on_submit():
                d_from_s = report_form.d_from.data
                d_to_s = report_form.d_to.data

                try:
                    d_from = datetime.datetime.strptime(d_from_s, '%Y-%m-%d')
                    d_to = datetime.datetime.strptime(d_to_s, '%Y-%m-%d')

                    results = generate_report(d_from, d_to)
                    generator = (cell for row in results
                                 for cell in row)

                    # https://shorturl.at/ayW01
                    return Response(generator,
                                    mimetype="text/plain",
                                    headers={"Content-Disposition": f"attachment;filename=phot_report_{d_from_s}.txt"})
                except Exception as e:
                    current_app.logger.error(f'Error in report. Details: {e}, ErrorClass: {e.__class__.__name__}')
                    flash(f"Probably wrong date format. Example: YYYY-MM-DD. <br>{d_from_s}---{d_to_s}")
                    return redirect(url_for("sat.sat_phot"))

    else:
        flash("User has no rights for Satellite section. Contact admin please.")
        return redirect(url_for('home.index'))


@sat_bp.route('/sat_details.html/<sat_id>', methods=['GET', 'POST'])
@login_required
def sat_details(sat_id):
    sat_search = Satellite.get_by_id(id=sat_id)

    return render_template("sat_details.html", sat_search=sat_search,
                           chckb=current_app.config['multi_lc_state'])


@sat_bp.route('/sat_lc_plot.html/<int:lc_id>', methods=['GET', 'POST'])
@login_required
def sat_lc_plot(lc_id):
    # lc, filename = plot_lc(lc_id)
    # return render_template("sat_lc_details.html", lc=lc, lc_graph=filename)

    if current_app.config['multi_lc_state']:
        lc, lc_fig = plot_lc_multi_bokeh(lc_id)
    else:
        lc, lc_fig = plot_lc_bokeh(lc_id)

    # lsp_fig = lsp_plot_bokeh(lc_id)
    # value = request.form.get('checkbox')
    # print(value)
    return render_template("sat_lc_details.html", lc=lc, lc_graph=lc_fig)


@sat_bp.route('/sat_lc_period_plot.html/<int:lc_id>', methods=['GET', 'POST'])
@login_required
def sat_lc_period_plot(lc_id):
    lsp_fig, lc = lsp_plot_bokeh(lc_id, return_lc=True)
    return render_template("sat_lc_lsp_details.html", lc=lc, lsp_graph=lsp_fig)


@cache.memoize(timeout=300)
# @cache.cached(timeout=15, key_prefix="sat_query", query_string=True)
def get_sat_query(s_value):
    query = Satellite.query
    search_value = s_value

    if search_value:
        query = query.filter(db.or_(
            Satellite.name.ilike(f'%{search_value}%'),
            db.cast(Satellite.norad, db.String).ilike(f'%{search_value}%'),
            db.cast(Satellite.cospar, db.String).ilike(f'%{search_value}%')
        ))
    total_filtered = query.count()

    # Total number of records without filtering
    # _, totalRecords = Satellite.count_sat()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.form.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.form.get(f'columns[{col_index}][data]')
        if col_name not in ['cospar', 'name', 'updated']:
            col_name = 'norad'
        descending = request.form.get(f'order[{i}][dir]') == 'desc'
        col = getattr(Satellite, col_name)
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        query = query.order_by(*order)

    # pagination
    start = request.form.get('start', type=int)
    length = request.form.get('length', type=int)
    if length == -1:
        length = Satellite.query.count()
    query = query.offset(start).limit(length)

    sats = query.all()
    # print("performing func...")
    return sats, total_filtered


@sat_bp.route("/ajaxfile_sat", methods=["POST", "GET"])
def ajax_file_sat():
    try:
        if request.method == 'POST':
            draw = request.form['draw']
            # row = int(request.form['start'])
            # rowperpage = int(request.form['length'])
            search_value = request.form["search[value]"]
            search_value = search_value.replace(" ", "%")

            sats, total_filtered = get_sat_query(s_value=search_value)

            data = [{
                'norad': '<a href=' + url_for('sat.sat_details', sat_id=sat.id) + '>' + str(sat.norad) + '</a>',
                'cospar': sat.cospar,
                'name': sat.name,
                'LC': sat.count_lcs(),
                'updated': sat.updated.strftime('%Y-%m-%d %H:%M'),
                'n2yo': '<a href=' + "https://www.n2yo.com/satellite/?s=" + str(sat.norad) + '> link </a>',
            } for sat in sats]

            response = {
                'draw': draw,
                # 'iTotalRecords': totalRecords,
                'iTotalRecords': Satellite.query.count(),
                'iTotalDisplayRecords': total_filtered,
                'aaData': data,
            }
            return jsonify(response)
    except Exception as e:
        # print(e)
        current_app.logger.error(f"""Error in ajax_file_sat function.
        \nDetailed error: {e}
        \nError class: {e.__class__.__name__}
        """)


@cache.memoize(timeout=300)
def get_lcs_query(sat_id, s_value):
    query = Lightcurve.query
    query = query.filter(Lightcurve.sat_id == sat_id)
    search_value = s_value

    # search filter
    if search_value:
        query = query.filter(db.or_(
            db.cast(Lightcurve.ut_start, db.String).ilike(f'%{search_value}%'),
            Lightcurve.band.ilike(f'%{search_value}%')
        ))
    total_filtered = query.count()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.form.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.form.get(f'columns[{col_index}][data]')
        if col_name not in ['ut_start', 'filter']:
            col_name = 'ut_start'
        if col_name == "filter":
            col_name = "band"
        descending = request.form.get(f'order[{i}][dir]') == 'desc'
        col = getattr(Lightcurve, col_name)
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        query = query.order_by(*order)

    # pagination
    start = request.form.get('start', type=int)
    length = request.form.get('length', type=int)
    if length == -1:
        length = Lightcurve.query.count()
    query = query.offset(start).limit(length)

    lcs = query.all()
    return lcs, total_filtered


@sat_bp.route("/ajaxfile_lc/<int:sat_id>", methods=["POST", "GET"])
def ajax_file_lc(sat_id):
    try:
        if request.method == 'POST':
            draw = request.form['draw']
            search_value = request.form["search[value]"]
            search_value = search_value.replace(" ", "%")

            lcs, total_filtered = get_lcs_query(sat_id, search_value)

            data = []
            for lc in lcs:
                txt = url_for('sat.sat_lc_plot', lc_id=lc.id)
                txt_lsp = url_for('sat.sat_lc_period_plot', lc_id=lc.id)

                if lc.lsp_period is None:
                    period = "Aperiodic"
                else:
                    period = lc.lsp_period

                data.append({
                    'ut_start': lc.ut_start.strftime("%Y-%m-%d %H:%M:%S"),
                    'site': lc.site,
                    'filter': lc.band,
                    'dt': "%5.3f" % lc.dt,
                    'curve': '<a href=' + txt + '>' + "LC" + '</a>',
                    'period': period,
                    'lsp': '<a href=' + txt_lsp + '>' + "LSP" + '</a>'
                })
            response = {
                'draw': draw,
                # 'iTotalRecords': totalRecords,
                # 'iTotalRecords': Lightcurve.query.count(),
                'iTotalRecords': Lightcurve.query.filter(Lightcurve.sat_id == sat_id).count(),
                'iTotalDisplayRecords': total_filtered,
                'aaData': data,
            }
            return jsonify(response)
    except Exception as e:
        # print(e)
        current_app.logger.error(f"""Error in ajax_file_lc function.
        \nDetailed error: {e}
        \nError class: {e.__class__.__name__}
        """)


@sat_bp.route("/ajax_checkbox_state", methods=["POST", "GET"])
def ajax_multi_lc_check():
    if request.method == "POST":
        state = request.values.get('state')
        # print(state)
        if state == 'true':
            current_app.config['multi_lc_state'] = True
            current_app.logger.info("User <%s> set Multi_lc_checkbox in True", current_user.username)
        else:
            current_app.config['multi_lc_state'] = False
            current_app.logger.info("User <%s> set Multi_lc_checkbox in False", current_user.username)
        # print(current_app.config['multi_lc_state'] )
    return "200"


class AddLcForm(FlaskForm):
    lc_file = MultipleFileField('File(s) Upload')
    add = SubmitField("Submit")


class ReportForm(FlaskForm):
    # month = IntegerField(u'Month', [DataRequired()])
    # year = IntegerField(u'Year', [DataRequired()])
    d_from = StringField(u'From:', [DataRequired(), Length(min=10, max=10)])
    d_to = StringField(u'To:', [DataRequired(), Length(min=10, max=10)])
    generate = SubmitField("Generate")
