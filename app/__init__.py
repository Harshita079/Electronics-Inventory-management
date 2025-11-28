from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from . import models 
from config import get_config
from .extensions import db, migrate, login_manager
from .blueprints.public.routes import public_bp
from .blueprints.admin import admin_bp
from .blueprints.staff import staff_bp


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(get_config())

    register_extensions(app)
    register_blueprints(app)
    apply_middlewares(app)

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)


def apply_middlewares(app: Flask) -> None:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

