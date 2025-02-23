from tests.conftest import client
import matplotlib
matplotlib.use("Agg")
from test_lc_upload import create_super_user
from app.models import Satellite, Lightcurve, db


def test_sat_phot(client, auth):
    create_super_user()
    auth.login("super_user", "user_pass")
    response = client.get("/sat_phot.html")
    assert response.status_code == 200


# TODO: test other routes, like in EB
# sat_details.html/83
# sat_lc_plot.html/2993
# sat_lc_period_plot.html/2993
# sat_plot_periods.html/83
