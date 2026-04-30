from .auth import auth_bp
from .users import users_bp
from .recipes import recipes_bp


def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(recipes_bp, url_prefix="/api/recipes")