import datetime
import os
import fnmatch
import random

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, FileField, MultipleFileField, SubmitField, RadioField, \
    SelectField, BooleanField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange, DataRequired

from app.models import Satellite, db, Lightcurve
from app.sat_utils import process_lc_files, get_list_of_files, del_files_in_folder, plot_lc, plot_lc_bokeh, \
    process_lc_file, lsp_plot_bokeh, lsp_calc, calc_period_for_all_lc, calc_sat_updated_for_all_sat
from app.star_util import plot_sat_lc, read_sat_files, plot_ccd_lc

sat_bp = Blueprint('sat', __name__)
# sat_db = None
basedir = os.path.abspath(os.path.dirname(__file__))


# @sat_bp.route('/upload_sat.html', methods=['GET', 'POST'])
# def upload_sat():
#     if request.method == "GET":
#         return render_template("upload_sat.html")
#
#     if request.method == "POST":
#         if not os.path.exists(os.path.join(basedir, "app", "static", "tmp-file")):
#             os.mkdir(os.path.join(basedir, "app", "static", "tmp-file"))
#         f = request.files['file']
#         f.save(secure_filename(f.filename))
#         return 'file uploaded successfully'


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
        # search_form = SearchForm()

        # if sat_id is not None:
        #     sat_search = Satellite.get_by_id(id=sat_id)
        # else:
        #     sat_search = None

        if lc_form.validate_on_submit() and lc_form.add.data:
            # print(lc_form.lc_file.data, end="  ")
            for file in lc_form.lc_file.data:
                # print(file.filename + "--------------")
                file_ext = os.path.splitext(file.filename)
                file_ext = file_ext[1]
                if len(file_ext) > 2:
                    file_ext = file_ext[:3]
                if file_ext in current_app.config['UPLOAD_EXTENSIONS']:
                    # print(file)
                    _, fext = os.path.splitext(file.filename)
                    process_lc_file(file_content=file.read(), file_ext=fext, db=db)
                    # # print("Saved.....")
                    # file.save(
                    #     os.path.join("app", current_app.config['UPLOAD_FOLDER'], file.filename)
                    # )
                else:
                    print("wrong file ext", file.filename)

            # lc_files_list = get_list_of_files(os.path.join("app", current_app.config['UPLOAD_FOLDER']))
            # print("process...")
            # process_lc_files(lc_flist=lc_files_list, db=db)
            # del_files_in_folder(folder=os.path.join("app", current_app.config['UPLOAD_FOLDER']))
            # print("Delete.")
            return redirect(url_for("sat.sat_phot"))

        # if search_form.validate_on_submit() and search_form.search.data:
        #     # print("search form submit....")
        #     try:
        #         option = search_form.rb.data
        #         if option == "NORAD":
        #             norad = int(search_form.searchtxt.data)
        #             sat_search = Satellite.get_by_norad(norad)
        #         elif option == "COSPAR":
        #             cospar = search_form.searchtxt.data
        #             sat_search = Satellite.get_by_cospar(cospar)
        #         elif option == "NAME":
        #             name = search_form.searchtxt.data
        #             # here we take first element of List as the most matched by name
        #             sat_search = Satellite.get_by_name(name)[0]
        #
        #         # print(sat_search)
        #         if sat_search:
        #             # print("found sat")
        #             return render_template("sat_phot.html",
        #                                    sats=Satellite.get_all(),
        #                                    sat_search=sat_search,
        #                                    lc_form=lc_form,
        #                                    search_form=search_form,
        #                                    user=current_user)
        #         else:
        #             raise Exception("Nothing found")
        #     except Exception as e:
        #         print("we are heere")
        #         print(e)
        #         if str(e) == "Nothing found":
        #             flash("Nothing found")
        #         else:
        #             flash("Invalid type of search")
        #         return redirect(url_for('sat.sat_phot'))

        if request.method == "GET":
            return render_template("sat_phot.html",
                                   sats=Satellite.get_all(),
                                   # sat_search=sat_search,
                                   lc_form=lc_form,
                                   # search_form=search_form,
                                   user=current_user)
    else:
        flash("User has no rights for Sat section. Contact admin please.")
        return redirect(url_for('home.index'))


@sat_bp.route('/sat_details.html/<sat_id>', methods=['GET', 'POST'])
@login_required
def sat_details(sat_id):
    if request.method == "POST":
        value = request.form.get('multi')
        print(value)
    sat_search = Satellite.get_by_id(id=sat_id)

    value = 'value' in locals() #or 'value' in globals()
    try:
        value
    except NameError:
        # var_exists = False
        multi_form = MultiLcForm()
    else:
        multi_form = MultiLcForm(multi=value)

    return render_template("sat_details.html", sat_search=sat_search, multi_form=multi_form)


@sat_bp.route('/sat_lc_plot.html/<int:lc_id>', methods=['GET', 'POST'])
@login_required
def sat_lc_plot(lc_id):
    # lc, filename = plot_lc(lc_id)
    # return render_template("sat_lc_details.html", lc=lc, lc_graph=filename)

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


@sat_bp.route("/ajaxfile_sat", methods=["POST", "GET"])
def ajax_file_sat():
    try:
        if request.method == 'POST':
            draw = request.form['draw']
            # row = int(request.form['start'])
            # rowperpage = int(request.form['length'])
            search_value = request.form["search[value]"]
            search_value = search_value.replace(" ", "%")

            query = Satellite.query

            # search filter
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
            query = query.offset(start).limit(length)

            sats = query.all()

            # if search_value:
            #     like_string = "%" + search_value.lower().replace(" ", "%") + "%"
            #     _, totalRecordwithFilter = Satellite.search_sat(search_string=like_string)
            # else:
            #     totalRecordwithFilter = totalRecords
            #
            # # Fetch records
            # if search_value == '':
            #     sats, _ = Satellite.count_sat(start=row, stop=row + rowperpage)
            # else:
            #     sats, _ = Satellite.search_sat(search_string=like_string, start=row, stop=row + rowperpage)

            data = []
            # for sat in sats:
            #     txt = url_for('sat.sat_details', sat_id=sat.id)
            #     link = "https://www.n2yo.com/satellite/?s=" + str(sat.norad)
            #     data.append({
            #         'norad': '<a href=' + txt + '>' + str(sat.norad) + '</a>',
            #         'cospar': sat.cospar,
            #         'name': sat.name,
            #         'LC': len(sat.get_lcs()),
            #         'n2yo': '<a href=' + link + '> link </a>',
            #     })

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
        print(e)


@sat_bp.route("/ajaxfile_lc/<int:sat_id>", methods=["POST", "GET"])
def ajax_file_lc(sat_id):
    try:
        if request.method == 'POST':
            draw = request.form['draw']
            search_value = request.form["search[value]"]
            search_value = search_value.replace(" ", "%")

            query = Lightcurve.query
            query = query.filter(Lightcurve.sat_id == sat_id)

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
            query = query.offset(start).limit(length)

            lcs = query.all()

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
        print(e)


@sat_bp.route("/ajax_checkbox_state", methods=["POST", "GET"])
def ajax_multi_lc_check():
    if request.method == "POST":
        state = request.values.get('state')
        # print(state)
        if state == 'true':
            current_app.config['multi_lc_state'] = True
        else:
            current_app.config['multi_lc_state'] = False
        # print(current_app.config['multi_lc_state'] )
    return "200"


class MultiLcForm(FlaskForm):
    multi = BooleanField()


class AddLcForm(FlaskForm):
    lc_file = MultipleFileField('File(s) Upload')
    add = SubmitField("Submit")


class SearchForm(FlaskForm):
    rb = RadioField('Search type', choices=[
        ('NORAD', 'NORAD'),
        ('COSPAR', 'COSPAR'),
        ('NAME', 'NAME')],
                    default="NORAD",
                    validators=None)
    searchtxt = StringField('SearchText', validators=[DataRequired(), Length(min=3, max=20)])
    search = SubmitField("Search")
