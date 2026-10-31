from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Lightcurve, User, db

def test_create_user(app):
    new_user = User(username="Test User", password="test_pass",
                    site_name="site", site_lat=48, site_lon=22, site_elev=180
                    )
    db.session.add(new_user)
    db.session.commit()

    user = User.query.filter_by(username="Test User").first()
    assert user is not None
    assert user.username == "Test User"


def test_delete_user(app):
    user = User(username="User_del", password="test_pass",
                site_name="site", site_lat=48, site_lon=22, site_elev=180
                )
    db.session.add(user)
    db.session.commit()

    db.session.delete(user)
    db.session.commit()

    assert User.query.filter_by(username="User_del").first() is None


def test_lightcurve_status_defaults(app):
    lightcurve = Lightcurve(
        ut_start=datetime(2025, 1, 1),
        ut_end=datetime(2025, 1, 1, 0, 1),
        dt=1.0,
        band="V",
        date_time=[],
        flux=[],
        mag=[],
    )
    db.session.add(lightcurve)
    db.session.flush()

    assert lightcurve.stable_status is None
    assert lightcurve.status_prob == 0.0


@pytest.mark.parametrize("status_prob", [-0.1, 100.1])
def test_lightcurve_status_prob_must_be_percentage(app, status_prob):
    lightcurve = Lightcurve(
        ut_start=datetime(2025, 1, 1),
        ut_end=datetime(2025, 1, 1, 0, 1),
        dt=1.0,
        band="V",
        date_time=[],
        flux=[],
        mag=[],
        status_prob=status_prob,
    )
    db.session.add(lightcurve)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


# def test_user_validation(app):
#     user = User(username="", password="invalid-password", site_name="site", site_lat=48, site_lon=22, site_elev=180)
#     from _pytest.outcomes import Failed
#     try:
#         with pytest.raises(ValueError):
#             db.session.add(user)
#             db.session.commit()
#     except Failed as exc:
#         # suppress
#         pass
#         # or
#         # do something else with the exception
#         print(exc)
#         # or
#         # raise SomeOtherException

