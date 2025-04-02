import os
from flask import Flask, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_session import Session
from flask_migrate import Migrate
from flask_caching import Cache
from dotenv import load_dotenv

from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS

load_dotenv('.env')
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
cors = CORS()
cache = Cache()


def setup_database(app, db):
    with app.app_context():
        @app.before_first_request
        def create_tables():
            db.create_all()


def create_app():
    app = Flask(__name__)
    # CONFIG_TYPE = os.getenv('CONFIG_TYPE', default='app.config.DevConfig')
    
    # https://realpython.com/flask-by-example-part-1-project-setup/#running-the-python-flask-example-locally

    with app.app_context():
        app.config.from_object(
            os.getenv('CONFIG_TYPE', default='app.config.DevConfig')
        )
        # print("sec_key =", app.config['SECRET_KEY'])
        # print("conf_type =", os.getenv('CONFIG_TYPE'))

        uri = app.config["DATABASE_URI"]
        if uri and uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)

        app.config.update(
            SQLALCHEMY_DATABASE_URI=uri  # app.config["DATABASE_URI"]
        )
        # app.config['UPLOAD_FOLDER'] = "upload/lcs"
        app.config['MAX_CONTENT_PATH'] = 5 * 1024 * 1024  # 5 Mb
        app.config['UPLOAD_EXTENSIONS'] = ['.phc', '.ph']
        app.config['multi_lc_state'] = False

        # print(os.getenv('CONFIG_TYPE', default='app.config.DevConfig'))
        # print(app.config['DATABASE_URI'])
        # print(app.config['SECRET_KEY'])

        bcrypt.init_app(app)
        from app.models import db
        db.init_app(app)
        migrate.init_app(app, db)
        setup_database(app, db)
        # https://flask-migrate.readthedocs.io/en/latest/

        login_manager.init_app(app)
        login_manager.session_protection = "strong"
        from app.models import User

        @login_manager.user_loader
        def load_user(user_id):
            # return User.query.get(int(user_id))
            user = User.query.get(int(user_id))
            # user = User.query.filter_by(id=int(user_id)).first()
            if user:
                # print(user.username)
                app.logger.info("Load User with username <%s>", user.username)
            return user

        # Customize unauthorized response for APIs
        @login_manager.unauthorized_handler
        def unauthorized():
            return jsonify({"message": "Authentication required. Please log in."}), 401

        # csrf.init_app(app)

        from .views import auth_bp, home_bp, eb_bp, sat_bp, sat_view_bp
        app.register_blueprint(home_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(eb_bp)
        app.register_blueprint(sat_bp)
        app.register_blueprint(sat_view_bp)

        from app.api import api_bp
        app.register_blueprint(api_bp)
        csrf.exempt(api_bp)    # <---- This line disables CSRF for API


        login_manager.login_view = "auth.login"
        # app.app_context().push()

        Session(app)
        csrf.init_app(app)
        cors.init_app(app)
        # cors.init_app(app, resources={r"/*": {"origins": "http://localhost:5000"}})  # Adjust to your domain

        # # Get the current environment (you can also set this using environment variables)
        # environment = app.config['FLASK_ENV']
        #
        # if environment == 'production':
        #     # In production, allow multiple origins for paths under `/api/*`
        #     cors.init_app(app,
        #                   resources={r"/api/*": {
        #                       "origins": ["https://test.com", "http://test.com", "https://www.test.com"]}
        #                   }
        #                   )
        # else:
        #     # In development, allow any localhost port for paths under `/api/*`
        #     cors.init_app(app, resources={r"/api/*": {"origins": "http://localhost:*"}})

        cache.init_app(app,
                       config={
                           #'CACHE_TYPE': 'SimpleCache',
                           'CACHE_TYPE': 'FileSystemCache',
                           'CACHE_DIR': 'cache',
                           "CACHE_THRESHOLD": 300
                               }
                       )

    # https://trstringer.com/logging-flask-gunicorn-the-manageable-way/
    import logging
    from flask.logging import default_handler

    # # Deactivate the default flask logger so that log messages don't get duplicated
    # app.logger.removeHandler(default_handler)
    #
    # gunicorn_logger = logging.getLogger('gunicorn.error')
    # app.logger.handlers = gunicorn_logger.handlers
    # app.logger.setLevel(gunicorn_logger.level)


    # Possible CSRF token error with gunicorn(w>1), solution:
    # https://medium.com/@sagar.pndt305/how-to-fix-the-csrf-token-issue-when-using-gunicorn-with-flask-66f04fc1a9b9
    # or
    # https://stackoverflow.com/questions/54027777/flask-wtf-csrf-session-token-missing-secret-key-not-found/64148808#64148808

    return app
