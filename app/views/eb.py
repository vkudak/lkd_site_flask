from flask import Blueprint, render_template, redirect, request, url_for
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, IntegerField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange
import ast

from app.star_util import read_stars_json, plot4, plot_star, read_stars_from_db
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
        stars = Star.return_all()
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

        stars = Star.return_all()
        return render_template('eb_list.html', stars=stars, user=current_user, eb_form=eb_form)
    else:
        # TODO print some message here if login unsuccessful
        return redirect(render_template('eb_phot.html'))


@eb_bp.route('/details.html/<star_id>', methods=['GET', 'POST'])
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
def del_eb(star_id):
    Star.delete_by_id(star_id)
    return redirect(url_for('eb.eb_list'))


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
