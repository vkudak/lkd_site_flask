from flask_restx import Api
from flask import Blueprint, jsonify
from werkzeug.exceptions import Unauthorized

# Create a Blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")


authorizations = {
    "SessionAuth": {
        "type": "apiKey",
        "in": "cookie",
        "name": "session"
    }
}

# Initialize Flask-RESTx API
api = Api(api_bp, doc="/docs",
          title="API for RSO LC DataBase", version="1.0.1",
          description="A simple Flask-RESTx API with session-based authentication",
          authorizations=authorizations)  # Swagger UI at /api/docs

# # Custom error handler for 401 Unauthorized
# @api.errorhandler(Unauthorized)
# def unauthorized_error(error):
#     return jsonify({"message": "Authentication required. Please log in."}), 401

# Import API namespaces
from .users import api as users_ns
from .auth import api as auth_ns

# Register namespaces
api.add_namespace(users_ns, path="/users")
api.add_namespace(auth_ns, path="/auth")
