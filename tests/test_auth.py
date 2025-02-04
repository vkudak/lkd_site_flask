from app.models import User, db


def test_register(client):
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'password123',
        'site_name': 'test123',
        'site_lat': 44,
        'site_lon': 22,
        'site_elev': 55
    }, content_type='application/x-www-form-urlencoded', follow_redirects=False)  # тут без follow_redirects

    # print(response.data.decode())  # Подивимося HTML-відповідь
    # Перевіряємо, чи відбувся редирект на сторінку входу
    assert response.status_code == 302  # код 302 означає редирект
    assert '/login' in response.headers['Location']

    # Перевіримо, що користувача додано до бази
    user = User.query.filter_by(username='newuser').first()
    assert user is not None


def test_login(client, app):
    # Create User to log in
    from app import bcrypt
    hashed_password = bcrypt.generate_password_hash("log_pass")
    hashed_password = hashed_password.decode("utf-8", "ignore")
    new_user = User(username="LogUser", password=hashed_password,
                    site_name="site", site_lat=48, site_lon=22, site_elev=180
                    )
    db.session.add(new_user)
    db.session.commit()

    response = client.post("/login", data={
        "username": "LogUser",
        "password": "log_pass",
    }, content_type='application/x-www-form-urlencoded', follow_redirects=False)
    # print(response.data.decode())
    assert response.status_code == 302
    assert '/' in response.headers['Location']


def test_bad_user_login(client):
    response = client.post("/login", data={
        "username": "wronguser",
        "password": "password123"
    }, content_type='application/x-www-form-urlencoded', follow_redirects=True)
    assert b"Invalid username" in response.data