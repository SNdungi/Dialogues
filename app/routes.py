import json
import os
from flask import Blueprint, render_template, current_app, request, jsonify
from datetime import datetime
from PIL import Image
from .dol_db.dbops import create_user, get_user_by_email
from .dol_db.models import DiscourseBlog # Assuming you will use it
from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import check_password_hash

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

# === NEW ROUTE 2: ADD DISCOURSE ===
@bp.route('/add-discourse', methods=['POST'])
def add_discourse():
    try:
        data = request.get_json()
        title = data.get('title')
        body_text = data.get('body')

        if not title or not body_text:
            return jsonify({'status': 'error', 'message': 'Title and Body are required'}), 400

        # Construct the new discourse object
        new_discourse = {
            "id": f"disc-{int(datetime.now().timestamp())}",
            "reference": f"DISC-{datetime.now().strftime('%Y-%m-%d-%H%M')}",
            "date_posted": datetime.now().strftime('%B %d, %Y'),
            "title": title,
            "body": f"<p>{body_text.replace(chr(10), '</p><p>')}</p>", # Convert newlines to paragraphs
            "resources": [] # For now, can be extended later
        }
        
        content_path = os.path.join(current_app.root_path, 'static', 'data', 'content.json')
        
        # Read-modify-write the content.json file
        with open(content_path, 'r+', encoding='utf-8') as f:
            content_data = json.load(f)
            content_data.insert(0, new_discourse) # Add to the beginning
            f.seek(0) # Rewind to the start of the file
            json.dump(content_data, f, indent=2)
            f.truncate()

        return jsonify({'status': 'success', 'message': 'Discourse added successfully. Please refresh.'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    



# =================================================================
# REFACTOR DIALOGUES ROUTE TO USE THE DATABASE
# =================================================================
@bp.route('/dialogues')
def dialogues():
    """Renders the main application with a discourse from the database."""
    latest_discourse = DiscourseBlog.query.filter_by(is_approved=True).order_by(DiscourseBlog.date_posted.desc()).first()
    all_discourses = DiscourseBlog.query.filter_by(is_approved=True).order_by(DiscourseBlog.date_posted.desc()).all()
    
    all_discourses = load_json_data('content.json')
    default_discourse = all_discourses[0] if all_discourses and isinstance(all_discourses, list) else {}

    return render_template(
        'dialogues.html',
        initial_content=latest_discourse, # Pass the object directly
        content_data=all_discourses, # Pass the list of objects
        default_content=default_discourse
    )

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

@bp.route('/login', methods=['POST'])
def login():
    """Handles user login."""
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"status": "error", "message": "Missing email or password"}), 400

    user = get_user_by_email(data['email'])

    if user and user.check_password(data['password']):
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        return jsonify({
            "status": "success",
            "access_token": access_token,
            "refresh_token": refresh_token
        })

    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

# ... (your other routes like /add-discourse and /upload-image would also be refactored
# to use dbops and require a valid JWT with @jwt_required())
