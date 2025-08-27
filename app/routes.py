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

@bp.route('/setup')
@login_required # IMPORTANT: Always protect admin pages
def setup_page():
    """Renders the new database management and setup page."""
    # Add a check here to ensure only Admin users can access it
    # if not current_user.has_role('Admin'):
    #     flash('You do not have permission to access this page.', 'danger')
    #     return redirect(url_for('discourse.dialogues'))
        
    return render_template('setup.html')

# === MODIFIED ROUTE: UPLOAD IMAGE ===
@bp.route('/upload-image', methods=['POST', 'GET'])
@login_required # Good practice to protect this endpoint
def upload_image():
    if 'image_file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    
    file = request.files['image_file']
    filename = request.form.get('filename')
    # NEW: Get the target subfolder
    subfolder = request.form.get('subfolder', '') # e.g., 'profile_pics'

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    
    if not filename:
        return jsonify({'status': 'error', 'message': 'Filename is required'}), 400

    safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_')).rstrip()
    if not safe_filename:
        return jsonify({'status': 'error', 'message': 'Invalid filename provided'}), 400

    try:
        # --- MODIFIED SAVE PATH ---
        # Create the target directory if it doesn't exist
        upload_folder = os.path.join(current_app.root_path, 'static', 'images', subfolder)
        os.makedirs(upload_folder, exist_ok=True)
        
        webp_filename = f"{safe_filename}.webp"
        save_path = os.path.join(upload_folder, webp_filename)

        with Image.open(file.stream) as img:
            # Resize for profile pictures to a consistent size
            if subfolder == 'profile_pics':
                img.thumbnail((300, 300)) # Create a thumbnail, maintains aspect ratio

            img.save(save_path, 'webp', quality=85)
        
        # Return the final filename to the client
        return jsonify({
            'status': 'success',
            'message': f'Image saved as {webp_filename}',
            'filename': webp_filename
        })

    except Exception as e:
        current_app.logger.error(f"Image upload failed: {e}")
        return jsonify({'status': 'error', 'message': 'Image processing failed.'}), 500


# =================================================================
# PROFILE ROUTES
# =================================================================

@bp.route('/profile')
@login_required
def profile_page():
    """Renders the user's profile page for viewing and editing."""
    # The `current_user` proxy from Flask-Login gives us the user object.
    # We pass it to the template, which will populate the form fields.
    return render_template('profile.html')


@bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Handles the submission of the profile update form."""
    
    # Update the user's attributes directly from the form data.
    # The `request.form.get()` method is used to access form data.
    current_user.name = request.form.get('name')
    current_user.other_names = request.form.get('other_names')
    current_user.contact = request.form.get('contact')
    current_user.organization_name = request.form.get('organization_name')
    current_user.website = request.form.get('website')
    current_user.education = request.form.get('education')
    current_user.career = request.form.get('career')
    
    new_picture_filename = request.form.get('profile_picture')
    if new_picture_filename:
        current_user.profile_picture = new_picture_filename

    # Basic validation to ensure required fields aren't blanked out.
    if not current_user.name or not current_user.other_names:
        flash('First Name and Last Name are required fields.', 'danger')
        return redirect(url_for('main.profile_page'))

    try:
        # Commit the changes to the database
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating profile for user {current_user.id}: {e}")
        flash('An error occurred while updating your profile. Please try again.', 'danger')

    return redirect(url_for('main.profile_page'))


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
            website=data.get('website'),
            education=data.get('education'),
            contact=data.get('contact'),
            career=data.get('career')# Optional
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


