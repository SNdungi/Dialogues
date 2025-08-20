# /project_folder/app/__init__.py

import os
import json
import csv # <--- IMPORT THE CSV MODULE
from sqlalchemy.exc import OperationalError
from flask import Flask,render_template
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from sqlalchemy.orm import joinedload
from dotenv import load_dotenv # --- 1. IMPORT load_dotenv ---

# --- Load environment variables from .env file ---
load_dotenv()

# --- Import your models directly ---
from .dol_db.models import db, Category, User, DiscourseBlog

# --------------------------------------------------------------------------
# 1. INSTANTIATE EXTENSIONS
# --------------------------------------------------------------------------
migrate = Migrate()
from .dol_db.admin import setup_admin
login_manager = LoginManager()
login_manager.login_view = 'main.login_page'
login_manager.login_message_category = 'info'

def create_app():
    """The application factory function."""
    app = Flask(__name__, instance_relative_config=True)

    # --------------------------------------------------------------------------
    # 2. CONFIGURE THE APP (--- THIS SECTION IS REPLACED ---)
    # --------------------------------------------------------------------------
    
    # --- START OF CHANGES ---

    # Get database credentials from environment variables
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_HOST = os.environ.get('DB_HOST')
    DB_NAME = os.environ.get('DB_NAME')
    
    print(f"Using database: {DB_NAME} at {DB_HOST} with user {DB_USER}")

    # Construct the MySQL Database URI
    # The format is: 'mysql+pymysql://<user>:<password>@<host>/<database_name>'
    database_uri = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'

    # Load configuration from environment variables
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # --- END OF CHANGES ---

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # --------------------------------------------------------------------------
    # 3. INITIALIZE EXTENSIONS WITH THE APP
    # --------------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    jwt = JWTManager(app)
    setup_admin(app)
    login_manager.init_app(app)

    # ... (the rest of your file remains exactly the same) ...

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except OperationalError as e:
            app.logger.warning(f"Could not connect to DB to load user: {e}")
            return None # Tell Flask-Login no user could be loaded
    
    @app.context_processor
    def inject_global_data():
        # ... (no changes needed here) ...
        app.logger.info("--- [CONTEXT] Starting global data injection ---")
        
        # --- 1. Load static data for the right sidebar ---
        daily_data = load_json_data('daily.json')

        # --- 2. Build the dynamic sidebar data from the database ---
        sidebar_data = []
        try:
            # Fetch all categories and their subcategories in a single, efficient query.
            all_categories = Category.query.options(
                joinedload(Category.subcategories)
            ).order_by(Category.name).all()

            for cat in all_categories:
                if len(cat.subcategories) > 0:
                    sidebar_data.append({
                        'id': cat.id,
                        'name': cat.name,
                        'icon': "fa-landmark",  # Placeholder icon
                        'subcategories': [
                            {'id': sub.id, 'name': sub.name}
                            for sub in sorted(cat.subcategories, key=lambda x: x.name)
                        ]
                    })
            app.logger.info("[CONTEXT] Successfully built sidebar_data.")
        except Exception as e:
            app.logger.error(f"[CONTEXT] Could not build sidebar_data: {e}")

        # --- 3. NEW: Load all approved discourses for the JavaScript front-end ---
        content_data = []
        try:
            # Query all approved discourses, ordering by the newest first.
            # We only select the columns needed by the JavaScript to keep the payload small.
            all_discourses = db.session.query(
                DiscourseBlog.id, 
                DiscourseBlog.title,
                DiscourseBlog.subcategory_id
            ).filter(DiscourseBlog.is_approved == True).order_by(DiscourseBlog.date_posted.desc()).all()

            # Convert the SQLAlchemy objects to a list of simple dictionaries.
            # This is faster and cleaner for JSON serialization.
            content_data = [
                {
                    'id': disc.id,
                    'title': disc.title,
                    'subcategory_id': disc.subcategory_id
                } for disc in all_discourses
            ]
            app.logger.info(f"[CONTEXT] Successfully loaded {len(content_data)} discourses for content_data.")
        except Exception as e:
            app.logger.error(f"[CONTEXT] Could not load discourses for content_data: {e}")


        # --- 4. Return the complete context dictionary ---
        return dict(
            daily_data=daily_data,
            sidebar_data=sidebar_data,
            content_data=content_data  # This is the crucial addition
        )

    def load_json_data(filename):
        """Helper function to load data from the static/data folder."""
        # Use app.root_path which is more reliable than current_app in this context
        filepath = os.path.join(app.root_path, 'static', 'data', filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            app.logger.warning(f"Could not load or parse {filename}")
            return [] if filename.endswith('s.json') else {}
            
    # --------------------------------------------------------------------------
    # 5. REGISTER BLUEPRINTS & COMMANDS
    # --------------------------------------------------------------------------
    from . import routes
    from .dol_discourse.disc_routes import discourse_bp  
    from .dol_academic.acad_routes import academic_bp
    from .dol_liturgy.lit_routes import liturgy_bp
    app.register_blueprint(liturgy_bp)
    app.register_blueprint(routes.bp)
    app.register_blueprint(discourse_bp)
    app.register_blueprint(academic_bp, url_prefix='/academic')
    
    # --------------------------------------------------------------------------
    # 6. REGISTER CUSTOM ERROR HANDLERS
    # --------------------------------------------------------------------------


    @app.errorhandler(OperationalError)
    def handle_db_connection_error(e):
        """
        Catches database connection errors and shows an engaging "waiting" page
        with scrolling quotes.
        """
        app.logger.error(f"DATABASE CONNECTION ERROR: {e}")
        
        quotes = []
        # --- NEW: Read the CSV file ---
        csv_path = os.path.join(app.root_path, 'static', 'data', 'Jesus_speaks.csv')
        try:
            with open(csv_path, mode='r', encoding='utf-8') as infile:
                # Use DictReader to read rows as dictionaries
                reader = csv.DictReader(infile)
                for row in reader:
                    # Clean up keys and values
                    cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                    quotes.append(cleaned_row)
        except FileNotFoundError:
            app.logger.error(f"Jesus_speaks.csv not found at {csv_path}")
            # Provide a fallback quote if the file is missing
            quotes.append({
                'Quote': 'Come to me, all you who are weary and burdened, and I will give you rest.',
                'ref': 'Matthew 11:28',
                'Age': ''
            })

        # Pass the list of quotes to the template
        return render_template('errors/503.html', quotes=quotes), 503
    
    from . import commands
    commands.init_app(app)
    
    app.add_url_rule('/', endpoint='main.splash')

    return app