from flask import request
from flask_login import login_required, current_user
from flask_restx import Namespace, Resource, fields
from werkzeug.exceptions import Unauthorized

from app import bcrypt
from app.models import db
from app.models import User  # Import the SQLAlchemy User model

api = Namespace("users", description="User related operations")

# Swagger Model
user_model = api.model("User", {
    "id": fields.Integer(readonly=True),
    "username": fields.String(required=True, description="User's name", example="John"),
    # "password": fields.String(required=True, description="User's password", example="MySecurePass123"),

    "site_name": fields.String(required=True, description="User's site name", example="my_observatory_name"),
    "site_lat": fields.Float(required=True, description="User's site latitude", example=51.6),
    "site_lon": fields.Float(required=True, description="User's site longitude", example=22.1),
    "site_elev": fields.Float(required=True, description="User's site elevation", example=100.3),

    "is_admin": fields.Boolean(required=False, default=False, description="User's admin status"),
    "sat_access": fields.Boolean(required=False, default=False, description="User's sat access status"),
    "eb_access": fields.Boolean(required=False, default=False, description="User's Eclipsing Binary access status"),
    "sat_lc_upload": fields.Boolean(required=False, default=False, description="User's sat lc upload status"),
})

user_create_model = api.model("User_create", {
    "id": fields.Integer(readonly=True),
    "username": fields.String(required=True, description="User's name", example="Peter"),
    "password": fields.String(required=True, description="User's password", example="MySecurePass123"),

    "site_name": fields.String(required=True, description="User's site name", example="my_observatory_name"),
    "site_lat": fields.Float(required=True, description="User's site latitude", example=51.6),
    "site_lon": fields.Float(required=True, description="User's site longitude", example=22.1),
    "site_elev": fields.Float(required=True, description="User's site elevation", example=100.3),

    "is_admin": fields.Boolean(required=False, default=False, description="User's admin status"),
    "sat_access": fields.Boolean(required=False, default=False, description="User's sat access status"),
    "eb_access": fields.Boolean(required=False, default=False, description="User's Eclipsing Binary access status"),
    "sat_lc_upload": fields.Boolean(required=False, default=False, description="User's sat lc upload status"),
})

# Define Error Message Model
error_model = api.model("Error", {
    "message": fields.String(description="Error message"),
})

@api.route("/")
class UserList(Resource):
    # @api.marshal_list_with(user_model)  # Marshals the list of User objects into JSON only if successful
    @api.response(200, "Success", [user_model])  # Document success response
    @api.response(401, "Authentication required", error_model)  # Document 401 error response
    @api.response(403, "Admins only", error_model)  # Document 403 error response
    @api.doc(security="SessionAuth", description="Requires login & admin rights",
             responses={401: "Authentication required"})

    # # @api.marshal_list_with(user_model)
    # # @api.marshal_with(user_model)
    # @api.response(200, "Success", [user_model])  # Document success response
    # @api.response(401, "Authentication required", error_model)  # Document error response
    # # @api.response(200, "Success", user_model)
    # # @api.marshal_list_with(user_model)
    # @api.doc(security="SessionAuth",
    #          description="Requires login & admin rights",
    #          responses={401: "Authentication required"})
    def get(self):
        """Get all users"""
        if not current_user.is_authenticated:
            return {"message": "Authentication required. Please log in."}, 401
        return User.get_all(to_list=True), 200
        # return User.get_all(), 200

    @api.expect(user_create_model)
    @api.marshal_with(user_create_model, code=201)
    @login_required
    @api.doc(security="SessionAuth", description="Requires login & admin rights")
    def post(self):
        """Create a new user"""
        if not current_user.is_admin:  # Directly check user role
            return {"message": "Access denied. Admins only."}, 403

        data = request.json

        # Check if email already exists
        if User.query.filter_by(username=data["username"]).first():
            return {"message": "Name already registered"}, 400

        hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        hashed_password = hashed_password.decode("utf-8", "ignore")

        new_user = User(username=data["username"],
                        password=hashed_password,
                        site_name=data["site_name"],
                        site_lon=data["site_lon"],
                        site_lat=data["site_lat"],
                        site_elev=data["site_elev"],
                        )

        db.session.add(new_user)
        db.session.commit()
        return new_user, 201

@api.route("/<int:id>")
class UserResource(Resource):
    @api.marshal_with(user_model)
    @login_required
    @api.doc(security="SessionAuth", description="Requires login")
    def get(self, id):
        """Get user by ID"""
        user = User.query.get_or_404(id)
        return user

    @api.expect(user_model)
    @api.marshal_with(user_model)
    @login_required
    @api.doc(security="SessionAuth", description="Requires login & admin rights")
    def put(self, id):
        """Update user by ID"""
        if not current_user.is_admin:  # Directly check user role
            return {"message": "Access denied. Admins only."}, 403
        user = User.query.get_or_404(id)
        data = request.json
        user.name = data["name"]
        user.email = data["email"]
        db.session.commit()
        return user

    @login_required
    @api.doc(security="SessionAuth", description="Requires login & admin rights")
    def delete(self, id):
        """Delete user by ID"""
        if not current_user.is_admin:  # Directly check user role
            return {"message": "Access denied. Admins only."}, 403

        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted"}, 204
