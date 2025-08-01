import json
import os
from flask import Blueprint, render_template, current_app, request, jsonify,url_for,redirect, flash
from datetime import datetime
from PIL import Image
from .dol_db.dbops import create_user, get_user_by_email
from .dol_db.models import DiscourseBlog, SubCategory, db
from sqlalchemy.orm import joinedload # Assuming you will use it
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_login import login_user, logout_user, login_required, current_user

bp = Blueprint('main', __name__)


def load_json_data(filename):
    """Helper function to load data from the static/data folder."""
    filepath = os.path.join(current_app.root_path, 'static', 'data', filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [] if 'json' in filename and 's' in filename else {}
    
@bp.app_context_processor
def inject_now():
    """Makes the 'now' function available to all templates for the current year."""
    return {'now': datetime.utcnow}

@bp.context_processor
def inject_shared_data():
    """Injects data needed by the base layout into all templates."""
    topics_data = load_json_data('topics.json')
    daily_data = load_json_data('daily.json')
    return dict(topics_data=topics_data, daily_data=daily_data)


@bp.route('/')
def splash():
    """Renders the new elegant, art-forward landing page."""
    return render_template('splash.html')


# === NEW ROUTE 1: UPLOAD IMAGE ===
@bp.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    
    file = request.files['image_file']
    filename = request.form.get('filename')

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    
    if not filename:
        return jsonify({'status': 'error', 'message': 'Filename is required'}), 400

    # Sanitize filename (basic)
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_')).rstrip()
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename provided'}), 400

    try:
        # Define the save path for the new WebP image
        webp_filename = f"{safe_filename}.webp"
        save_path = os.path.join(current_app.root_path, 'static', 'images', webp_filename)

        # Open the uploaded image and save it as WebP
        with Image.open(file.stream) as img:
            img.save(save_path, 'webp', quality=85) # quality can be adjusted
        
        return jsonify({'status': 'success', 'message': f'Image uploaded and saved as {webp_filename}'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# =================================================================
# AUTHENTICATION ROUTES
# =================================================================


@bp.route('/register', methods=['POST'])
def register():
    """Handles user registration with extended fields."""
    data = request.get_json()
    required_fields = ['name', 'other_names', 'email', 'username', 'password', 'password_confirmation']
    if not data or not all(k in data for k in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    # --- New Validation ---
    if data['password'] != data['password_confirmation']:
        return jsonify({"status": "error", "message": "Passwords do not match."}), 400

    try:
        # Pass all fields to the updated dbops function
        new_user = create_user(
            name=data['name'],
            other_names=data['other_names'],
            email=data['email'],
            username=data['username'],
            password=data['password'],
            organization_name=data.get('organization_name'), # Optional
            website=data.get('website')                     # Optional
        )
        
        access_token = create_access_token(identity=new_user.id)
        refresh_token = create_refresh_token(identity=new_user.id)
        
        return jsonify({
            "status": "success",
            "message": "Registration successful! You can now log in.",
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 201

    except ValueError as e: # Catches "Email/Username already exists"
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        # In production, you might want to log this error instead of exposing it
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500

@bp.route('/login', methods=['GET', 'POST'])
def login_page():
    """Renders the login page and handles form submission."""
    if current_user.is_authenticated:
        return redirect(url_for('discourse.dialogues'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = get_user_by_email(email)

        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('main.login_page'))
        
        # Use Flask-Login's login_user function
        login_user(user, remember=remember)
        return redirect(url_for('discourse.dialogues'))

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.splash'))

@bp.route('/register', methods=['GET'])
def registration_page():
    """Renders the new registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('discourse.dialogues'))
    return render_template('registration.html')

@bp.context_processor
def inject_sidebar_data():
    """
    Injects a structured list of categories and their subcategories
    THAT HAVE AT LEAST ONE APPROVED DISCOURSE. This makes the sidebar
    dynamic and relevant.
    """
    # Query to get all subcategories that are linked to an approved discourse
    active_subcategories = db.session.query(SubCategory)\
        .join(DiscourseBlog)\
        .filter(DiscourseBlog.is_approved == True)\
        .options(joinedload(SubCategory.category))\
        .distinct()\
        .all()

    # Structure the data for the template
    sidebar_topics = {}
    for sub in active_subcategories:
        cat_name = sub.category.name
        if cat_name not in sidebar_topics:
            sidebar_topics[cat_name] = []
        sidebar_topics[cat_name].append({
            'name': sub.name,
            'id': sub.id # You might use this for linking later
        })
        
    return dict(sidebar_topics=sidebar_topics)
