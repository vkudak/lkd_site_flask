from flask import current_app, redirect, request, url_for
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from wtforms.validators import ValidationError

from app.models import db, User


class SecureMixin:
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login", next=request.url))


class SecureIndex(SecureMixin, AdminIndexView):
    pass


class UserAdmin(SecureMixin, ModelView):
    column_list = ("username", "site_name", "eb_access", "sat_access", "sat_lc_upload", "is_admin")
    column_editable_list = ("eb_access", "sat_access", "sat_lc_upload", "is_admin")
    column_searchable_list = ("username", "site_name")
    form_columns = ("eb_access", "sat_access", "sat_lc_upload", "is_admin")
    can_create = False
    can_delete = False

    def on_model_change(self, form, model, is_created):
        # Prevent an admin from locking themselves out
        if model.id == current_user.id and not model.is_admin:
            raise ValidationError("You cannot remove your own admin rights.")

        for flag in self.column_editable_list:
            hist = db.inspect(model).attrs[flag].history
            if hist.has_changes() and hist.deleted:
                current_app.logger.info(
                    "Admin <%s> changed %s for user <%s>: %s -> %s",
                    current_user.username, flag, model.username, hist.deleted[0], hist.added[0],
                )


def init_admin(app):
    # Built per app: a module-level Admin would re-register blueprints across create_app() calls
    admin = Admin(
        name="LKD Admin",
        index_view=SecureIndex(url="/magic", endpoint="magic"),
    )
    admin.init_app(app)
    admin.add_view(UserAdmin(User, db.session, name="Users", url="users", endpoint="admin_users"))
