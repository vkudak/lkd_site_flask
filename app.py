from flask import Flask, Response, render_template, redirect, url_for, request, session, abort
from star_util import read_stars, plot3
from datetime import datetime
# from astropy.time import Time
import ast
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange
from flask_bcrypt import Bcrypt


today = datetime.today()
year = today.year

app = Flask(__name__)

# config
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config.update(
    DEBUG=True,
    SQLALCHEMY_DATABASE_URI="sqlite:///users.db",
    SQLALCHEMY_TRACK_MODIFICATIONS = True,
    SECRET_KEY='secret_777'
)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

global eb_users

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

    site_name = db.Column(db.String(80), nullable=False)
    site_lat = db.Column(db.Float, nullable=False)
    site_lon = db.Column(db.Float, nullable=False)
    site_elev = db.Column(db.Float, nullable=False)

    # https: // www.youtube.com / watch?v = 71
    # EU8gnZqZQ & ab_channel = ArpanNeupane


class RegisterForm(FlaskForm):
    username = StringField(default=u'login', validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Password"})
    site_name = StringField(default=u'Observatory Name', validators=[InputRequired(), Length(min=3, max=20)],
                           render_kw={"placeholder": "SiteName"})
    site_lat = FloatField(default=u'Latitude [in deg (45.5)]', validators=[InputRequired(), NumberRange(min=-180, max=180)],
                           render_kw={"placeholder": "SiteLat"})
    site_lon = FloatField(default=u'Latitude [in deg (22.5)]', validators=[InputRequired(), NumberRange(min=-180, max=180)],
                           render_kw={"placeholder": "SiteLon"})
    site_elev = FloatField(default=u'Elevation [in m (180)]', validators=[InputRequired(), NumberRange(min=0, max=10800)],
                           render_kw={"placeholder": "SiteElev"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_username = User.query.filter_by(username=username.data).first()
        if existing_username:
            raise ValidationError("Such user already exists")


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],
                           render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


@app.route('/')
@app.route('/index.html')
def index():
    global eb_users
    eb_users = []
    with open("eb_users.lst") as f:
        for line in f:
            eb_users.append(line.strip())
    return render_template('index.html', year=year)


@app.route('/about.html')
def about():
    return render_template('about.html', year=year)


@app.route('/details.html/<star>', methods=['GET', 'POST'])
def details(star):
    # we got star dict as a string. So need to convert...
    star_d = ast.literal_eval(star)

    # lon = 22.45
    # lat = 48.6
    # elev = 270.3
    # lat, lon, elev = current_user.lat, current_user.lon, current_user.elev
    graph_name = plot3(star_d, user=current_user)
    return render_template('details.html', year=year, star=star_d, graph=graph_name)


@app.route('/contact.html')
def contact():
    return render_template('contact.html', year=year)


@app.route('/eb_list.html')
@login_required
def eb_list():
    if current_user.username in eb_users:
        cat = 'eb_cat.csv'
        gcvs_filename = 'gcvs_select.dat'
        stars = read_stars(cat, gcvs_filename, current_user)
        return render_template('eb_list.html', year=year, stars=stars)
    else:
        redirect(render_template('index.html', year=year))


# somewhere to login
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                # print(f"LOGGED IN.......{user.username}")
                return render_template("index.html", year=year)
    return render_template("login.html", form=form)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return render_template("index.html", year=year)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data,
                        password=hashed_password,
                        site_name=form.site_name.data,
                        site_lat=form.site_lat.data,
                        site_lon=form.site_lon.data,
                        site_elev=form.site_elev.data)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html", form=form)

if __name__ == "__main__":
    # https: // github.com / arpanneupane19 / Flask - File - Uploads
    app.run(debug=True)
