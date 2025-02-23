from tests.conftest import client
import matplotlib
matplotlib.use("Agg")
from test_lc_upload import create_super_user
from app.models import Star, db


def test_eb_phot(client):
    response = client.get("/eb_phot.html")
    assert response.status_code == 200
    assert b"photometry of selected eclipsing binary systems" in response.data.lower()

def test_eb_list_access_denied(client,auth):
    """Перевіряє, що користувач без прав отримує редірект."""
    create_super_user(eb_access=False)
    auth.login("super_user", "user_pass")  # Імітація входу

    response = client.get("/eb_list.html")
    assert response.status_code == 302  # Перевіряємо, що користувача редіректить
    assert b"User has no rights for EB section" in response.data  # Flash повідомлення

def test_eb_list_login_required(client):
    response = client.get("/eb_list.html", follow_redirects=False)
    assert response.status_code == 302  # Перевіряємо, що користувача редіректить
    assert "/login?next=%2Feb_list.html" in response.headers["Location"]

def test_add_eb(client, auth):
    create_super_user()
    auth.login("super_user", "user_pass")

    response = client.post("/eb_list.html", data={
        "name": "Test Star",
        "ra": 123.45,
        "dec": -45.67,
        "mag": 10.5,
        "period": 2.345,
        "epoch": 250000,  # Перевіримо віднімання 240000
        # "submit": True  # Симуляція натискання кнопки
    }, follow_redirects=True)

    assert response.status_code == 200
    star = Star.query.filter_by(star_name="Test Star").first()
    assert star is not None
    assert star.epoch == 10000  # Переконуємося, що 240000 відняли


def test_eb_details(client, auth):
    create_super_user()
    auth.login("super_user", "user_pass")

    # make a star
    star = Star(star_name="test2",
                ra=123.45, dec=84.32, mag=10.5,
                period=2.34, epoch=2450000,
                n_lc_TESS=0,
                publications=0,
                done=False
                )
    db.session.add(star)
    db.session.commit()

    star = Star.query.filter_by(star_name="test2").first()

    response = client.get(f"/details.html/{str(star.id)}")
    assert response.status_code == 200
    assert b"Details of EB" in response.data

def test_details_form_submission(client, auth):
    """Перевіряє, що користувач може додавати спостереження через форму."""
    create_super_user()
    auth.login("super_user", "user_pass")  # Логуємо користувача

    # Додаємо тестову зорю
    star = Star(star_name="Test Star", ra=123.45, dec=84.32, mag=10.5, period=2.34, epoch=2450000,
                n_lc_TESS=0,
                publications=0,
                done=False
                )
    db.session.add(star)
    db.session.commit()

    # Надсилаємо POST-запит із заповненою формою
    response = client.post(
        f"/details.html/{star.id}",
        data={"JD_start": "2459999.5", "JD_end": "2460000.5"},
        content_type="application/x-www-form-urlencoded",
        follow_redirects=True
    )
    assert response.status_code == 200  # Переконуємося, що сторінка відображається після відправки форми