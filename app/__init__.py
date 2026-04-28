from flask import Flask
from flask_login import LoginManager

from config.settings import SECRET_KEY, DATABASE_PATH

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DATABASE_PATH"] = DATABASE_PATH
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from app.models import init_db
    init_db(app)

    from app.routes.auth import auth_bp
    from app.routes.teacher import teacher_bp
    from app.routes.accountant import accountant_bp
    from app.routes.principal import principal_bp
    from app.routes.settings_bp import settings_bp
    from app.routes.documents import documents_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(accountant_bp, url_prefix="/accountant")
    app.register_blueprint(principal_bp, url_prefix="/principal")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(documents_bp, url_prefix="/documents")

    return app
