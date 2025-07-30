import os
from flask import Flask

def create_app():
    # Create and configure the app
    # The instance_relative_config=True tells the app that configuration files
    # are relative to the instance folder.
    # The __name__ tells Flask where to look for templates and static files.
    # By putting it here, it knows to look inside the 'app' package.
    app = Flask(__name__, instance_relative_config=True)

    # A default configuration can be set here if needed
    app.config.from_mapping(
        SECRET_KEY='dev', # Change this for production!
    )

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --- Register Blueprints Here ---
    # We will import and register our routes Blueprint
    from . import routes
    app.register_blueprint(routes.bp)

    # In the future, you would register other blueprints like this:
    # from . import academic
    # app.register_blueprint(academic.bp, url_prefix='/academic')
    
    return app