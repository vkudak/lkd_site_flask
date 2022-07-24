from app import create_app
# from app import config

app = create_app()

if __name__ == "__main__":
    # from app.models import db
    # db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
