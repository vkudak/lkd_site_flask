from app.models import User, Lightcurve, db
import io
import os
from datetime import datetime
from werkzeug.datastructures import FileStorage
import logging
from app import bcrypt


def create_super_user():
    hashed_password = bcrypt.generate_password_hash("user_pass")
    hashed_password = hashed_password.decode("utf-8", "ignore")
    new_user = User(username="super_user", password=hashed_password,
                    site_name="site", site_lat=48, site_lon=22, site_elev=180
                    )
    new_user.sat_access = True
    new_user.is_admin = True
    new_user.eb_access = True

    db.session.add(new_user)
    db.session.commit()
    return new_user


def test_phc_lc_upload(client, caplog, auth):
    """Перевіряє завантаження файлів PHC кривих блиску через форму AddLcForm."""
    create_super_user()
    auth.login("super_user", "user_pass")  # Імітація входу

    with caplog.at_level(logging.INFO):  # Перехоплення логів INFO+
        # Імітуємо файл для завантаження
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

    assert "successfully processed" in caplog.text
    # assert "Processing file:" in caplog.text

    # # Перевіряємо, що сервер відповів редіректом або статусом успіху
    assert response.status_code in [200, 302]

    # Якщо є редірект, перевіряємо, що він правильний
    if response.status_code == 302:
        assert "/sat_phot.html" in response.headers["Location"]  # Замініть на правильну URL

    # Перевіряємо, чи файли були успішно додані (якщо вони зберігаються в БД)
    st_time = datetime.strptime('2025-01-30 17:19:41', '%Y-%m-%d %H:%M:%S')
    lc1 = Lightcurve.query.filter_by(ut_start=st_time).first()
    assert lc1 is not None


def test_phx_lc_upload(client, caplog, auth):
    """Перевіряє завантаження НОВИХ файлів PHX кривих блиску через форму AddLcForm."""
    create_super_user()
    auth.login("super_user", "user_pass")  # Імітація входу

    with caplog.at_level(logging.INFO):  # Перехоплення логів INFO+
        # Імітуємо файл для завантаження
        file1 = FileStorage(
            stream=open("tests/lc_to_upload/result_44517_20250130_UT173650.phV", "rb"),
            filename="result_44517_20250130_UT173650.phV",
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

    assert "successfully processed" in caplog.text
    # assert "Processing file:" in caplog.text

    # # Перевіряємо, що сервер відповів редіректом або статусом успіху
    assert response.status_code in [200, 302]

    # Якщо є редірект, перевіряємо, що він правильний
    if response.status_code == 302:
        assert "/sat_phot.html" in response.headers["Location"]  # Замініть на правильну URL

    # Перевіряємо, чи файли були успішно додані (якщо вони зберігаються в БД)
    # lcs = Lightcurve.get_all()
    # for lc in lcs:
    #     print(lc.ut_start, lc.ut_end)

    st_time = datetime.strptime('2025-01-30 17:36:50.807771', '%Y-%m-%d %H:%M:%S.%f')
    lc1 = Lightcurve.query.filter_by(ut_start=st_time).first()
    assert lc1 is not None