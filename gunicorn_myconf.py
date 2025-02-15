# gunicorn.conf.py
'''
used only if added as parameter
gunicorn -c config.py
'''
import os
from dotenv import load_dotenv
# import multiprocessing

for env_file in ('.env', '.flaskenv'):
    env = os.path.join(os.getcwd(), env_file)
    if os.path.exists(env):
        load_dotenv(env)


# --log-level=debug
# --reload
# --workers=1
# --threads=2

# preload_app = True
bind = "127.0.0.1:8000"
workers = 2 #multiprocessing.cpu_count() * 2 + 1
threads = 2
log_level = 'info'
# log_level = 'debug'
reload = True
timeout = 180
# umask = "0o007"
