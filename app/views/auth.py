from flask import Blueprint, render_template, redirect, url_for, flash, current_app, session, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user


from app import bcrypt
from app.models import User, db


auth_bp = Blueprint('auth', __name__)


def validate_username(username):
    existing_username = User.query.filter_by(username=username.data).first()
    if existing_username:
        raise ValidationError("Such user already exists")


class RegisterForm(FlaskForm):
    username = StringField(default=u'login', validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={"placeholder": "Password"})
    site_name = StringField(default=u'Observatory Name', validators=[InputRequired(), Length(min=3, max=20)],
                            render_kw={"placeholder": "SiteName"})
    site_lat = FloatField(default=u'Latitude [in deg (45.5)]',
                          validators=[InputRequired(), NumberRange(min=-180, max=180)],
                          render_kw={"placeholder": "SiteLat"})
    site_lon = FloatField(default=u'Latitude [in deg (22.5)]',
                          validators=[InputRequired(), NumberRange(min=-180, max=180)],
                          render_kw={"placeholder": "SiteLon"})
    site_elev = FloatField(default=u'Elevation [in m (180)]', validators=[InputRequired(), NumberRange(min=0, max=10800)],
                           render_kw={"placeholder": "SiteElev"})
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                             render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


# somewhere to login
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    # current_app.logger.info("Secret is %s", session)
    # current_app.logger.info("csrf_token is %s", session['csrf_token'])
    # Check data
    # if request.method == "POST":
    #     current_app.logger.info("form valid = %s ", form.validate_on_submit())
    #     current_app.logger.info("FORM_data = %s", request.form)

    if form.validate_on_submit():
        current_app.logger.info('Logging form is valid')
        # print("form valid")
        current_app.logger.info('Username entered: %s', form.username.data)
        # print(form.username.data)
        # print(User.query.filter_by(username=form.username.data))
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            current_app.logger.info('User found in DB. Checking password...')
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                current_app.logger.info('User <%s> logged in', user.username)
                # return render_template("index.html")
                redirect_url = request.args.get('next') or url_for('home.index')
                return redirect(redirect_url)
            else:
                current_app.logger.info('User <%s> wrong password', user.username)
                flash("invalid password")
        else:
            current_app.logger.info('User <%s> NOT found in DB', user.username)

    if request.method == "POST":
        current_app.logger.warning('FORM not valid')
        current_app.logger.warning("FORM_data = %s", request.form)
    return render_template("login.html", form=form)


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    user = User.query.get(int(current_user.id))
    if logout_user():
        current_app.logger.info('User with username <%s> is logged out', user.username)
    # return render_template("index.html")
    return redirect(url_for('home.index'))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        hashed_password = hashed_password.decode("utf-8", "ignore")
        new_user = User(username=form.username.data,
                        password=hashed_password,
                        site_name=form.site_name.data,
                        site_lat=form.site_lat.data,
                        site_lon=form.site_lon.data,
                        site_elev=form.site_elev.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)