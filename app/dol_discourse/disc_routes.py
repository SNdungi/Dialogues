# /project_folder/app/dol_discourse/disc_routes.py

import os
from flask import Blueprint, render_template, current_app, request, jsonify, url_for
from datetime import datetime
from app.dol_db.models import db, DiscourseBlog, User, Category, SubCategory, Resource, ResourceMedium,ResourceType
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
import json


# 1. Define the Blueprint correctly (removed url_defaults)
discourse_bp = Blueprint('discourse', __name__,
                         url_prefix='/discourse',
                         template_folder='templates/discourse',
                         static_folder='static')

# === NEW: BLUEPRINT-SPECIFIC CONTEXT PROCESSOR ===
@discourse_bp.app_context_processor
def inject_enums_for_discourse_templates():
    """
    Makes the ResourceType and ResourceMedium enums available
    specifically to templates rendered by this blueprint.
    """
    # These functions will now be available in discourse.html
    def get_resource_types():
        return list(ResourceType)

    def get_resource_mediums():
        return list(ResourceMedium)
    
    return dict(
        get_resource_types=get_resource_types,
        get_resource_mediums=get_resource_mediums
    )
# --- EDITOR AND API ROUTES ---
@discourse_bp.route('/new', methods=['GET'])
@login_required
def new_discourse_editor():
    """Renders the editor, passing all top-level categories."""
    all_categories = Category.query.order_by(Category.name).all()
    return render_template('discourse.html', categories=all_categories)

@discourse_bp.route('/api/subcategories/<int:category_id>')
def get_subcategories(category_id):
    """API endpoint to fetch subcategories for a given category."""
    subcategories = SubCategory.query.filter_by(category_id=category_id).order_by(SubCategory.name).all()
    return jsonify([{'id': sub.id, 'name': sub.name} for sub in subcategories])





@discourse_bp.route('/save', methods=['POST'])
@login_required
def save_discourse():
    """
    Handles saving a new discourse from a multipart/form-data request,
    including a potential featured image upload.
    """
    current_app.logger.info("Received request to /discourse/save")
    
    # 1. Access data from request.form for text fields
    try:
        title = request.form['title']
        body = request.form['body']
        subcategory_id = int(request.form['subcategory_id'])
        resources_json_string = request.form.get('resources', '[]') # Default to an empty JSON array string
    except (KeyError, ValueError) as e:
        current_app.logger.error(f"Missing or invalid form data: {e}")
        return jsonify({"status": "error", "message": "Missing or invalid required form data."}), 400

    # ... (Authorization check remains the same) ...
    if not current_user.has_role('Admin') and not current_user.has_role('Editor') and not current_user.has_role('Writer'):
        return jsonify({"status": "error", "message": "You are not authorized to create a discourse."}), 403

    try:
        image_filename = None
        # 2. Handle the optional image upload from request.files
        if 'featured_image' in request.files:
            file = request.files['featured_image']
            if file and file.filename != '':
                timestamp = int(datetime.now().timestamp())
                base_filename = secure_filename(os.path.splitext(file.filename)[0])
                image_filename = f"{base_filename}_{timestamp}.webp"
                
                # It's good practice to have a dedicated uploads folder
                save_path_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'discourse_images')
                os.makedirs(save_path_dir, exist_ok=True)
                save_path = os.path.join(save_path_dir, image_filename)

                with Image.open(file.stream) as img:
                    img.save(save_path, 'webp', quality=85)
                current_app.logger.info(f"Successfully saved image as {image_filename}")

        # 3. Create the DiscourseBlog object
        new_discourse = DiscourseBlog(
            user_id=current_user.id,
            title=title,
            body=body,
            subcategory_id=subcategory_id,
            featured_image=image_filename,
            reference=f"DISC-{int(datetime.now().timestamp())}",
            is_approved=True
        )

        # 4. Process resources from the JSON string
        resources_data = json.loads(resources_json_string)
        if resources_data:
            for res_data in resources_data:
                resource = Resource(
                    name=res_data['name'],
                    type=ResourceType[res_data['type']],
                    medium=ResourceMedium[res_data['medium']],
                    link=res_data['link']
                )
                new_discourse.resources.append(resource)
        
        db.session.add(new_discourse)
        db.session.commit()
        
        current_app.logger.info(f"Discourse '{title}' saved successfully with ID {new_discourse.id}")
        
        return jsonify({
            "status": "success", 
            "message": "Discourse saved successfully!",
            "redirect_url": url_for('discourse.dialogues') 
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during discourse save process: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500


# ============== PUBLIC-FACING DIALOGUES ROUTE =====================
@discourse_bp.route('/')  # This will be the '/discourse/' URL
@discourse_bp.route('/dialogues') # This will be the '/discourse/dialogues' URL
def dialogues():
    """
    Renders the main page with the latest discourse.
    Accessible at /discourse/ or /discourse/dialogues
    """
    latest_discourse = DiscourseBlog.query.filter_by(is_approved=True)\
                                          .order_by(DiscourseBlog.date_posted.desc())\
                                          .options(joinedload(DiscourseBlog.subcategory).joinedload(SubCategory.category))\
                                          .first()
    
    # Assuming your template is now at app/templates/discourse/dialogues.html
    return render_template(
        'dialogues.html',
        initial_content=latest_discourse
    )
    

# ============= NEW ROUTE FOR VIEWING A SINGLE DISCOURSE ===================
@discourse_bp.route('/<int:discourse_id>')
def view_discourse(discourse_id):
    """Renders a page for a single, specific discourse."""
    # Query for the specific discourse by its primary key.
    # We use joinedload to efficiently fetch related author and category data in one go.
    discourse = DiscourseBlog.query\
        .options(
            joinedload(DiscourseBlog.subcategory).joinedload(SubCategory.category),
            joinedload(DiscourseBlog.author),
            joinedload(DiscourseBlog.resources) # Also load resources
        )\
        .get_or_404(discourse_id) # .get_or_404 is perfect for this, it will show a "Not Found" page if the ID is invalid.

    # Render the new template, passing the fetched discourse object.
    return render_template('discourse.html', discourse=discourse)


# -============== NEW API ENDPOINT TO GET A SINGLE DISCOURSE'S DETAILS ================
@discourse_bp.route('/api/get/<int:discourse_id>')
def get_discourse_details(discourse_id):
    """API endpoint to fetch the full details of a single discourse."""
    try:
        discourse = DiscourseBlog.query.options(
            joinedload(DiscourseBlog.resources) # Eager load the resources
        ).get(discourse_id)

        if not discourse:
            return jsonify({"status": "error", "message": "Discourse not found"}), 404

        # Prepare the data in a JSON-friendly format
        data_to_return = {
            "status": "success",
            "discourse": {
                "id": discourse.id,
                "title": discourse.title,
                "body": discourse.body,
                "featured_image_url": url_for('static', filename=f'uploads/discourse_images/{discourse.featured_image}') if discourse.featured_image else None,
                "date_posted": discourse.date_posted.strftime('%B %d, %Y'),
                "reference": discourse.reference,
                "resources": [
                    {
                        "type": resource.type.value, # Get the string value from the Enum
                        "name": resource.name,
                        "link": resource.link
                    } for resource in discourse.resources
                ]
            }
        }
        return jsonify(data_to_return)
    except Exception as e:
        current_app.logger.error(f"API Error fetching discourse {discourse_id}: {e}")
        return jsonify({"status": "error", "message": "An internal server error occurred"}), 500
    
# === NEW API ROUTE TO ADD A RESOURCE TO A DISCOURSE ===
@discourse_bp.route('/api/add-resource', methods=['POST'])
@login_required # Only logged-in users can add resources
def add_resource():
    """API endpoint to add a new resource to an existing discourse."""
    data = request.get_json()
    
    # --- 1. Validate incoming data ---
    required_fields = ['discourse_id', 'name', 'type', 'medium', 'link']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400

    try:
        # --- 2. Check if the discourse exists ---
        discourse = DiscourseBlog.query.get(data['discourse_id'])
        if not discourse:
            return jsonify({'status': 'error', 'message': 'Discourse not found.'}), 404

        # --- 3. Create the new Resource object ---
        new_resource = Resource(
            discourse_id=discourse.id,
            name=data['name'],
            type=ResourceType[data['type']],         # Convert string back to Enum
            medium=ResourceMedium[data['medium']], # Convert string back to Enum
            link=data['link']
        )
        
        db.session.add(new_resource)
        db.session.commit()

        # --- 4. Return the newly created resource for dynamic UI update ---
        return jsonify({
            "status": "success",
            "message": "Resource added successfully!",
            "resource": {
                "type": new_resource.type.value,
                "name": new_resource.name,
                "link": new_resource.link
            }
        }), 201

    except KeyError as e:
        # This catches invalid enum values (e.g., 'BOK' instead of 'BOOK')
        return jsonify({'status': 'error', 'message': f'Invalid value for type or medium: {e}'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding resource: {e}")
        return jsonify({'status': 'error', 'message': 'An internal server error occurred.'}), 500