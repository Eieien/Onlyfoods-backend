
from flask import Flask, jsonify
from flask_cors import CORS
from routes import register_routes
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from extensions import bcrypt, jwt
from utils.errors import register_error_handlers
from dotenv import load_dotenv
import os
load_dotenv()

def create_app():
    app = Flask(__name__)
    register_routes(app)
    return app

if __name__ == '__main__':
    app = create_app()
    bcrypt.init_app(app)
    app.secret_key = os.environ.get("SECRET_KEY")
    app.config["JWT_SECRET_KEY"] = "super-secret-key"
    app.config["JWT_COOKIE_SECURE"] = True
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False # True if deployment
    jwt.init_app(app)
    register_error_handlers(app)
    app.run(debug=True)




