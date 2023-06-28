from flask import Blueprint, render_template, redirect, request, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SubmitField
from wtforms.validators import InputRequired, Length

from sqlalchemy import case

from app import cache
from app.star_util import plot_star
from app.models import Star, db

eb_bp = Blueprint('eb', __name__)
global eb_users


@eb_bp.route('/eb_phot.html')
def eb_phot():
    return render_template('eb_phot.html')


@eb_bp.route('/eb_list.html', methods=["GET", "POST"])
@login_required
def eb_list():
    # star = Star(star_name="V0527 Dra",
    #             ra="18h38m56.22s",
    #             dec="+60d23m53.5s",
    #             mag=10.440,
    #             period=0.744805,
    #             epoch=53747.7723,
    #             n_lc_TESS=0,
    #             publications=2,
    #             phase={
    #                 "2020-05-19": [2458988.3167629, 2458988.5581998],
    #                 "2021-05-10": [2459345.3424883, 2459345.5765755]
    #             },
    #             done=False
    #             )
    # db.session.add(star)
    # db.session.commit()
    #
    # star.add_phase(date="2021-05-12", new_phase=[2459345.6424883, 2459345.8765755])
    #
    # print(star.phase)

    if current_user.eb_access:
        # stars = Star.return_all()
        # print(stars)
        # print(stars[0].pas(user=current_user))
        eb_form = AddEBForm()

        if eb_form.validate_on_submit():
            if eb_form.epoch.data > 240000:
                eb_form.epoch.data = eb_form.epoch.data - 240000
            star = Star(star_name=eb_form.name.data,
                        ra=eb_form.ra.data,
                        dec=eb_form.dec.data,
                        mag=eb_form.mag.data,
                        period=eb_form.period.data,
                        epoch=eb_form.epoch.data,
                        n_lc_TESS=0,
                        publications=0,
                        done=False
                        )
            db.session.add(star)
            db.session.commit()

        # stars = Star.return_all()
        # return render_template('eb_list.html', stars=stars, user=current_user, eb_form=eb_form)
        if request.method == "GET":
            return render_template('eb_list.html', user=current_user, eb_form=eb_form)
    else:
        flash("User has no rights for EB section. Contact admin please.")
        return redirect(render_template('eb_phot.html'))


@eb_bp.route('/details.html/<star_id>', methods=['GET', 'POST'])
@login_required
@cache.cached(timeout=100)
def details(star_id):
    star = Star.get_by_id(star_id)
    graph_name = plot_star(star, user=current_user)

    form = AddObsForm()
    if form.validate_on_submit():
        star.add_obs(start_date=form.JD_start.data, end_date=form.JD_end.data)
        # graph_name = plot_star(star, user=current_user)
        return render_template('details.html', star=star, graph=graph_name, user=current_user, form=form)

    return render_template('details.html', star=star, graph=graph_name, user=current_user, form=form)


# @eb_bp.route('/add_obs.html/<star_id>', methods=['GET', 'POST'])
# def add_obs(star_id):
#     star = Star.get_by_id(id=star_id)
#     form = AddObsForm()
#     if form.validate_on_submit():
#         star.add_obs(start_date=form.JD_start.data, end_date=form.JD_end.data)
#         graph_name = plot_star(star, user=current_user)
#         return render_template('details.html', star=star, graph=graph_name, user=current_user)
#     # else if GET
#     return render_template('add_obs.html', star=star, form=form)


@eb_bp.route('/del_eb.html/<star_id>', methods=['GET'])
@login_required
def del_eb(star_id):
    Star.delete_by_id(star_id)
    return redirect(url_for('eb.eb_list'))


@cache.memoize(timeout=300)
def get_stars_query(s_value):
    query = Star.query
    search_value = s_value

    # search filter
    if search_value:
        query = query.filter(db.or_(
            Star.star_name.ilike(f'%{search_value}%'),
            # db.cast(Star.rise(current_user), db.String).ilike(f'%{search_value}%'),
            db.cast(Star.period, db.String).ilike(f'%{search_value}%'),
            db.cast(Star.mag, db.String).ilike(f'%{search_value}%')
        ))
    total_filtered = query.count()

    # Total number of records without filtering
    # _, totalRecords = Star.count_sat()

    # sorting
    order = []
    i = 0  # order index
    while True:
        col_index = request.form.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.form.get(f'columns[{col_index}][data]')

        # sort by rise_time
        if col_name == "rise":  # if sort by rise_time
            stars_my = query.all()
            descending = request.form.get(f'order[{i}][dir]') == 'desc'
            if descending:
                stars_my = sorted(
                    stars_my, key=lambda k: k.rise(current_user, get_timestamp=True),
                    reverse=True
                )
            else:  # ascending
                stars_my = sorted(
                    stars_my, key=lambda k: k.rise(current_user, get_timestamp=True),
                    reverse=False
                )
            ids_list = [star.id for star in stars_my]

            # get order
            rise_ordering = case(
                {_id: index for index, _id in enumerate(ids_list)},
                value=Star.id
            )
            # append order
            order.append(rise_ordering)
        ###############################

        # sort by pas_time
        if col_name == "pass":  # if sort by pas_time
            stars_my = query.all()
            descending = request.form.get(f'order[{i}][dir]') == 'desc'
            if descending:
                stars_my = sorted(
                    stars_my, key=lambda k: k.pas(current_user, get_timestamp=True),
                    reverse=False
                )
            else:  # ascending
                stars_my = sorted(
                    stars_my, key=lambda k: k.pas(current_user, get_timestamp=True),
                    reverse=True
                )
            ids_list = [star.id for star in stars_my]

            # get order
            pas_ordering = case(
                {_id: index for index, _id in enumerate(ids_list)},
                value=Star.id
            )
            order.append(pas_ordering)
        #######################

        if col_name not in ['star_name', 'period', 'mag', 'rise', 'pass']:
            col_name = 'star_name'
        descending = request.form.get(f'order[{i}][dir]') == 'desc'

        # Form order
        if col_name not in ["rise", "pass"]:
            col = getattr(Star, col_name)
            if descending:
                col = col.desc()
            order.append(col)
        i += 1

    # set orders
    if order:
        query = query.order_by(*order)

    # pagination
    start = request.form.get('start', type=int)
    length = request.form.get('length', type=int)
    if length == -1:
        length = Star.query.count()
    query = query.offset(start).limit(length)

    stars = query.all()
    # print([s.id for s in stars])

    data = [{
        'eb_name':
        # star.star_name,
            (
                    '<a href=' + f"https://simbad.cds.unistra.fr/simbad/sim-basic?Ident={star.star_name.replace(' ', '+')}"
                                 "&submit=SIMBAD+search"
                                 f"> {star.star_name} </a>"),
        'period': f"{star.period:1.8f}",
        'epoch': f"{star.epoch:5.4f}",
        'mag': f"{star.mag:2.2f}",
        'rise': f"{star.rise(current_user):>25}",  # .strftime('%Y-%m-%d %H:%M'),
        'pass': f"{star.pas(current_user):>25}",  # .strftime('%Y-%m-%d %H:%M'),
        'details': '<a href=' + f"{url_for('eb.details', star_id=star.id)}" + "> Details </a>",
        'remove': ('<a href=' + f"{url_for('eb.del_eb', star_id=star.id)} onclick='return confirmAction()'>"
                                " Remove </a>"),
        'done': str(star.done),
        'work': str(True if (star.observations and not star.done) else False),
    } for star in stars]

    return stars, total_filtered, data


@eb_bp.route("/ajax_eb", methods=["POST"])
def ajax_file_eb():
    try:
        if request.method == 'POST':
            draw = request.form['draw']
            search_value = request.form["search[value]"]
            search_value = search_value.replace(" ", "%")

            stars, total_filtered, data = get_stars_query(search_value)

            response = {
                'draw': draw,
                # 'iTotalRecords': totalRecords,
                'iTotalRecords': Star.query.count(),
                'iTotalDisplayRecords': total_filtered,
                'aaData': data,
            }
            return jsonify(response)
    except Exception as e:
        # print(e)
        current_app.logger.error(f"""Error in ajax_file_eb function.
        \nDetailed error: {e}
        \nError class: {e.__class__.__name__}
        """)


class AddObsForm(FlaskForm):
    JD_start = FloatField(validators=[InputRequired()],
                          render_kw={"placeholder": 2459345.3424883})
    JD_end = FloatField(validators=[InputRequired()],
                        render_kw={"placeholder": 2459346.3424883})
    id = IntegerField(validators=[InputRequired()],
                      render_kw={"placeholder": "id"})
    submit = SubmitField("Submit")


class AddEBForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=4, max=30)],
                       render_kw={"placeholder": "EB_name"})
    period = FloatField(validators=[InputRequired()],
                        render_kw={"placeholder": 0.888})
    epoch = FloatField(validators=[InputRequired()],
                       render_kw={"placeholder": 2459346.3424883})
    ra = StringField(validators=[InputRequired(), Length(min=4, max=30)],
                     render_kw={"placeholder": "00h00m00.00s"})
    dec = StringField(validators=[InputRequired(), Length(min=4, max=30)],
                      render_kw={"placeholder": "+00d00m00.00s"})
    mag = FloatField(validators=[InputRequired()],
                     render_kw={"placeholder": 10.02})
    submit = SubmitField("Submit")
