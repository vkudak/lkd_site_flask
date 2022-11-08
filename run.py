from app import create_app
# from app import config
import logging

app = create_app()

log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)

if __name__ == "__main__":
    # from app.models import db
    # db.create_all()
    # app.run(host="0.0.0.0", port=5000, debug=True)
    app.run()
else:
    # https://trstringer.com/logging-flask-gunicorn-the-manageable-way/
    # https://stackoverflow.com/questions/26578733/why-is-flask-application-not-creating-any-logs-when-hosted-by-gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
