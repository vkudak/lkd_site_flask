from tests.conftest import client
import matplotlib
matplotlib.use("Agg")

def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"welcome to laboratory of space research" in response.data.lower()

def test_404_page(client):
    response = client.get("/nonexistent_page")
    assert response.status_code == 404