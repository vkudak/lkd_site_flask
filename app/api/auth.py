from flask import request, current_app
from flask_login import login_user, logout_user, login_required
from flask_restx import Namespace, Resource, fields

from app import bcrypt
from app.models import User


api = Namespace("auth", description="Authentication operations")

# Login request model
login_model = api.model("Login", {
    "username": fields.String(required=True, description="User name"),
    "password": fields.String(required=True, description="User password")
})

login_response_model = api.model("LoginResponse", {
    "message": fields.String(description="Login status"),
    "is_admin": fields.Boolean(description="Indicates if user is an admin", default=False, example=False)
})

@api.route("/login")
class Login(Resource):
    @api.expect(login_model)
    @api.response(200, "Success", login_response_model)
    def post(self):
        """Login user and verify password"""
        data = request.json
        user = User.query.filter_by(username=data["username"]).first()

        if user and bcrypt.check_password_hash(user.password,data["password"]):
            login_user(user)
            current_app.logger.info('API. User <%s> logged in', user.username)
            return {"message": "Login successful!", "is_admin": user.is_admin}, 200
        else:
            current_app.logger.info('API. User <%s> wrong password', user.username)
            return {"message": "Invalid email or password"}, 401


@api.route("/logout")
class Logout(Resource):
    @login_required  # Require user to be logged in
    @api.doc(security="SessionAuth")  # Mark as protected in Swagger UI
    def post(self):
        """Logout user and clear session"""
        logout_user()  # Flask-Login clears session
        return {"message": "Logged out successfully"}, 200