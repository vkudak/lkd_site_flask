from werkzeug.datastructures import FileStorage

from test_lc_upload import create_super_user


def test_report(client, caplog, auth):
    create_super_user()
    auth.login("super_user", "user_pass")  # Імітація входу

    # upload LC
    file1 = FileStorage(
        stream=open("tests/lc_to_upload/51511_250130_1719_report.phc", "rb"),
        filename="51511_250130_1719_report.phc",
        content_type="application/octet-stream"
    )
    response = client.post(
        "/sat_phot.html",  # Замініть на правильний шлях у вашому застосунку
        data={
            "lc_file": [file1],  # Імітуємо список файлів
            "add": "1"  # Імітуємо натискання кнопки "Add"
        },
        content_type="multipart/form-data",
        follow_redirects=True
    )
    # LC uploaded


    # Get report
    response = client.post(
        "/sat_phot.html",
        # url_for("sat.sat_phot"),
        data={"d_from": "2025-01-30",
              "d_to": "2025-02-01",
              "submit": "Generate"
              },
        content_type="application/x-www-form-urlencoded",
        follow_redirects=False
    )

    # Перевіряємо, що відповідь містить файл
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")

    assert "attachment;filename=phot_report_2025-01-30.txt" in response.headers["Content-Disposition"]
    # is not empty
    assert len(response.data) > 0