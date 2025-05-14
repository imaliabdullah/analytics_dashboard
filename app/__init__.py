from flask import Flask
from flask_sqlalchemy import SQLAlchemy
#from flask_migrate import Migrate
from flask_cors import CORS
from celery import Celery
from config import config

# Initialize extensions
db = SQLAlchemy()
#migrate = Migrate()
celery = Celery('analytics_dashboard',
                broker='redis://localhost:6379/0',
                backend='redis://localhost:6379/0',
                broker_connection_retry_on_startup=True)

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app
    db.init_app(app)
    #migrate.init_app(app, db)
    CORS(app)

    # Initialize Celery
    celery.conf.update(app.config)

    # Register blueprints
    from app.routes import bp
    app.register_blueprint(bp)

    return app 