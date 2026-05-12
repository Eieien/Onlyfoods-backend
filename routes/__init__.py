from .auth import auth_bp
from .profiles import profiles_bp
from .recipes import recipes_bp
from .favorites import favorites_bp 
from .reccomendation import recommendations_bp


def register_routes(app):
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(profiles_bp, url_prefix="/profiles")
    app.register_blueprint(recipes_bp, url_prefix="/recipes")
    app.register_blueprint(favorites_bp, url_prefix="/favorites")
    app.register_blueprint(recommendations_bp, url_prefix="/recommendations")