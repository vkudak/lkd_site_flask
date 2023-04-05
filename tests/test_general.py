import pytest
from ..run import app

@pytest.fixture
def client():
    # app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    yield client


def test_homepage(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome to the Linux Kernel Development website!" in response.data


def test_about_page(client):
    response = client.get('/about')
    assert response.status_code == 200
    assert b"About" in response.data


def test_invalid_page(client):
    response = client.get('/invalid')
    assert response.status_code == 404
