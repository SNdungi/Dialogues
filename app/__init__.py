# /project_folder/app/__init__.py

import os
import click
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# --------------------------------------------------------------------------
# 1. INSTANTIATE EXTENSIONS (WITHOUT AN APP)
# --------------------------------------------------------------------------
# The extensions are created here, but not initialized. They are "empty"
# until they are connected to a specific app instance in the factory below.

# Correct: Import the 'db' object that is defined in your models file.
from .dol_db.models import db
# Instantiate the Migrate object here.
migrate = Migrate()

# We will need these for the factory function.
from .dol_db.admin import setup_admin
from .dol_db.dbops import seed_roles

def create_app():
    """The application factory function."""
    app = Flask(__name__, instance_relative_config=True)

    # --------------------------------------------------------------------------
    # 2. CONFIGURE THE APP
    # --------------------------------------------------------------------------
    # Load configuration from a mapping.
    app.config.from_mapping(
        SECRET_KEY='change-this-in-production!',
        # Set the database path. The 'instance' folder is a good place for it.
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'dialogues.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # Ensure the instance folder exists where the database file will be stored.
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --------------------------------------------------------------------------
    # 3. INITIALIZE EXTENSIONS WITH THE APP
    # --------------------------------------------------------------------------
    # This is the crucial step. This connects the 'db' and 'migrate' objects
    # to your configured Flask app.
    db.init_app(app)
    migrate.init_app(app, db) # Now 'db' knows about the app.
    
    jwt = JWTManager(app)
    setup_admin(app)

    # --------------------------------------------------------------------------
    # 4. REGISTER BLUEPRINTS & COMMANDS
    # --------------------------------------------------------------------------
    # Register the main routes.
    from . import routes
    app.register_blueprint(routes.bp)
    
    # Optional: Add a default URL rule if your blueprint doesn't define '/'.
    # This ensures navigating to the root of your site works.
    app.add_url_rule('/', endpoint='main.splash')


    # Add the custom CLI command for seeding the database.
    @app.cli.command("db_seed")
    def db_seed_command():
        """Seeds the database with initial data (e.g., roles)."""
        with app.app_context():
            seed_roles()
            click.echo("Database roles seeded successfully.")

    return app