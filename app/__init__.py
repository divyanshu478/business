from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import os



# create database object globally
db = SQLAlchemy()

def create_app() :
    app = Flask(__name__)
    app.config['SECRET_KEY'] = "9950"
    # app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///company.db"
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL_EXTERNAL")
    app.config['SQLALCHEMY_TRACK_NOTIFICATIONS'] = False

    #connecting the database
    db.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.tasks import task_bp

    # app.register_blueprint(auth_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(auth_bp)

    return app