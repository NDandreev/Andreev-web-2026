from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object('app.config.Config')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Создаём папки
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Импорт моделей (для Alembic)
    from app import models

    # Регистрация blueprint'ов
    from app.auth import auth_bp
    from app.books import books_bp
    from app.reviews import reviews_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(books_bp, url_prefix='/')
    app.register_blueprint(reviews_bp, url_prefix='/reviews')

    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return {'current_user': current_user}

    return app