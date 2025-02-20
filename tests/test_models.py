from app.models import User, db
import pytest

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

