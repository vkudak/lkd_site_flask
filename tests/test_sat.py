from werkzeug.datastructures import FileStorage
from datetime import datetime
from tests.conftest import client
import matplotlib
matplotlib.use("Agg")
from test_lc_upload import create_super_user
from app.models import Satellite, Lightcurve


def test_sat_phot(client, auth):
    create_super_user()
    auth.login("super_user", "user_pass")
    response = client.get("/sat_phot.html")
    assert response.status_code == 200


def test_sat_all(client, auth):
    create_super_user()
    auth.login("super_user", "user_pass")  # Імітація входу

    # upload LC
    file1 = FileStorage(
        stream=open("tests/lc_to_upload/51511_250130_1719.phc", "rb"),
        filename="51511_250130_1719.phc",
        content_type="application/octet-stream"
    )

    # Виконуємо POST-запит до ендпоінту завантаження кривих блиску
    response = client.post(
        "/sat_phot.html",  # Замініть на правильний шлях у вашому застосунку
        data={
            "lc_file": [file1],  # Імітуємо список файлів
            "add": "1"  # Імітуємо натискання кнопки "Add"
        },
        content_type="multipart/form-data",
        follow_redirects=True
    )

    st_time = datetime.strptime('2025-01-30 17:19:41', '%Y-%m-%d %H:%M:%S')
    lc = Lightcurve.get_by_lc_start(51511, st_time)[0]
    sat = Satellite.get_by_norad(51511)
    assert lc is not None
    response = client.get(f"/sat_details.html/{sat.id}")
    assert response.status_code == 200
    assert b"Satellite NORAD=" in response.data

    # check LC plot details
    response = client.get(f"/sat_lc_plot.html/{lc.id}")
    assert response.status_code == 200
    assert b"LC start time =" in response.data

    # check LSP details
    response = client.get(f"/sat_lc_period_plot.html/{lc.id}")
    assert response.status_code == 200
    assert b"Observatory=" in response.data

    # check plot ALL periods
    response = client.get(f"/sat_plot_periods.html/{sat.id}")
    assert response.status_code == 200
    assert b"Number of LCs=" in response.data
