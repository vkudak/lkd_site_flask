from app.models import User, db

def test_login(client):
    # Create User to log in
    new_user = User(username="LogUser", password="log_pass",
                    site_name="site", site_lat=48, site_lon=22, site_elev=180
                    )
    db.session.add(new_user)
    db.session.commit()

    # Test user
    response = client.post("/login", data={
        "username": "testuser",
        "password": "password123"
    }, follow_redirects=True)
    assert b"Welcome back, testuser" in response.data


def test_failed_login(client):
    response = client.post("/login", data={
        "username": "wronguser",
        "password": "wrongpassword"
    })
    assert b"Invalid credentials" in response.data