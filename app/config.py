from datetime import timedelta
from os import environ, path
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))


class Config:
    """Base config."""
    # SESSION_COOKIE_NAME = environ.get('SESSION_COOKIE_NAME')
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'

    # https://stackoverflow.com/questions/58866560/flask-sqlalchemy-pool-pre-ping-only-working-sometimes
    SQLALCHEMY_POOL_RECYCLE = 20  # 35  # value less than backend’s timeout
    SQLALCHEMY_POOL_TIMEOUT = 7  # value less than backend’s timeout
    SQLALCHEMY_PRE_PING = True
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_size': 10,
                                 'pool_recycle': SQLALCHEMY_POOL_RECYCLE,
                                 'pool_timeout': SQLALCHEMY_POOL_TIMEOUT,
                                 'pool_pre_ping': SQLALCHEMY_PRE_PING}

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_TYPE = "filesystem"
    # SESSION_PERMANENT = False
    # PERMANENT_SESSION_LIFETIME = timedelta(hours=5)
    # The maximum number of items the session stores
    # before it starts deleting some, default 500
    # SESSION_FILE_THRESHOLD = 200

    # UPLOAD_FOLDER = path.join(basedir, "app", "static", "tmp-file")


class ProdConfig(Config):
    FLASK_ENV = 'production'
    SECRET_KEY = environ.get('SECRET_KEY')
    FLASK_APP = 'run.py'
    DEBUG = False
    TESTING = False
    # DATABASE_URI = environ.get('DATABASE_URL')
    DATABASE_URI = environ.get('SUPABASE_DB_URL')


class DevConfig(Config):
    FLASK_ENV = 'development'
    # SECRET_KEY = 'secret_777'
    SECRET_KEY = environ.get('SECRET_KEY')
    DEBUG = True
    TESTING = True
    DATABASE_URI = "sqlite:///dev.db"
