# app.py

from flask import Flask
from extensions import db, login_manager
from flask_migrate import Migrate
from utils import initialize_models  # Import initialize_models from utils


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key_here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.jinja_env.add_extension('jinja2.ext.do') 
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)

    # Set the login view
    login_manager.login_view = 'auth.login'  # Add this line

    # Initialize NLP models once and store in app config
    models = initialize_models()
    app.config['MODELS'] = models

    # Import and register blueprints
    from routes.auth import auth
    from routes.main import main
    from routes.resume import resume
    from routes.job import job
    from routes.admin import admin

    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(resume)
    app.register_blueprint(job)
    app.register_blueprint(admin)

    # User loader callback for Flask-Login
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app

app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
