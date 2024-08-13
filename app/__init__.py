from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from .models import create_tables

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Load environment variables
    load_dotenv()
    
    # Initialize configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steamdata.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Ensure tables are created
    create_tables()

    # Register blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
