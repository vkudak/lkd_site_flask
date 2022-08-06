import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_session import Session
from flask_migrate import Migrate

# from flask_wtf.csrf import CSRFProtect

bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
# csrf = CSRFProtect()


def setup_database(app, db):
    with app.app_context():
        @app.before_first_request
        def create_tables():
            db.create_all()


def create_app():
    app = Flask(__name__)
    # CONFIG_TYPE = os.getenv('CONFIG_TYPE', default='app.config.DevConfig')
    
    # https://realpython.com/flask-by-example-part-1-project-setup/#running-the-python-flask-example-locally
    
    app.config.from_object(
        os.getenv('CONFIG_TYPE', default='app.config.DevConfig')
    )

    uri = app.config["DATABASE_URI"]
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=uri  # app.config["DATABASE_URI"]
    )
    # app.config['UPLOAD_FOLDER'] = "upload/lcs"
    app.config['MAX_CONTENT_PATH'] = 5 * 1024 * 1024  # 5 Mb
    app.config['UPLOAD_EXTENSIONS'] = ['.phc', '.ph']

    # print(os.getenv('CONFIG_TYPE', default='app.config.DevConfig'))
    # print(app.config['DATABASE_URI'])

    bcrypt.init_app(app)
    from app.models import db
    db.init_app(app)
    migrate.init_app(app, db)
    setup_database(app, db)
    # https://flask-migrate.readthedocs.io/en/latest/

    login_manager.init_app(app)
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # csrf.init_app(app)

    from .views import auth_bp, home_bp, eb_bp, sat_bp
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(eb_bp)
    app.register_blueprint(sat_bp)

    login_manager.login_view = "auth.login"
    app.app_context().push()

    Session(app)
    return app
