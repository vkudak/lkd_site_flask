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

# TODO: test other routes
# sat_details.html/83
# sat_lc_plot.html/2993
# sat_lc_period_plot.html/2993
# sat_plot_periods.html/83
#
# /eb_phot.html
# /eb_list.html
# /details.html/2
