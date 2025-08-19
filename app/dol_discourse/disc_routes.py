# /project_folder/app/dol_discourse/disc_routes.py

import os
from flask import Blueprint, render_template, current_app, request, jsonify, url_for, abort
from datetime import datetime
from app.dol_db.models import db, DiscourseBlog, User, Category, SubCategory, Resource, ResourceMedium,ResourceType, DiscourseComment
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
    """Renders the editor for creating a new discourse."""
    all_categories = Category.query.order_by(Category.name).all()
    # Pass discourse=None to make template logic explicit
    return render_template('discourse.html', categories=all_categories, discourse=None)


# ============== NEW: ROUTE TO EDIT AN EXISTING DISCOURSE ===============
@discourse_bp.route('/edit/<int:discourse_id>', methods=['GET'])
@login_required
def edit_discourse(discourse_id):
    """Renders the editor pre-populated with an existing discourse."""
    discourse = DiscourseBlog.query.options(
        joinedload(DiscourseBlog.resources),
        joinedload(DiscourseBlog.subcategory)
    ).get_or_44(discourse_id)

    # --- Authorization Check ---
    is_author = discourse.user_id == current_user.id
    is_privileged = current_user.has_role('Admin') or current_user.has_role('Editor')
    if not is_author and not is_privileged:
        abort(403) # Forbidden

    # Prepare data for JavaScript on the front-end
    discourse_data_for_js = {
        "id": discourse.id,
        "body": discourse.body,
        "subcategory_id": discourse.subcategory_id,
        "resources": [
            {
                "name": r.name,
                "type": r.type.name,    # Pass the Enum member NAME
                "medium": r.medium.name, # Pass the Enum member NAME
                "link": r.link,
            } for r in discourse.resources
        ]
    }

    all_categories = Category.query.order_by(Category.name).all()
    return render_template(
        'discourse.html', 
        categories=all_categories, 
        discourse=discourse, # Pass the full object for template logic
        discourse_data_for_js=json.dumps(discourse_data_for_js) # Pass JSON for JS
    )


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
        
        # Redirect to the new discourse's view page
        return jsonify({
            "status": "success", 
            "message": "Discourse saved successfully!",
            "redirect_url": url_for('discourse.dialogues')
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during discourse save process: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500


# ============== NEW: ROUTE TO UPDATE AN EXISTING DISCOURSE ===============
@discourse_bp.route('/update/<int:discourse_id>', methods=['POST'])
@login_required
def update_discourse(discourse_id):
    """Handles updating an existing discourse."""
    discourse_to_update = DiscourseBlog.query.get_or_404(discourse_id)

    # --- Authorization Check ---
    is_author = discourse_to_update.user_id == current_user.id
    is_privileged = current_user.has_role('Admin') or current_user.has_role('Editor')
    if not is_author and not is_privileged:
        return jsonify({"status": "error", "message": "You are not authorized to edit this discourse."}), 403

    try:
        # 1. Update text fields from form data
        discourse_to_update.title = request.form['title']
        discourse_to_update.body = request.form['body']
        discourse_to_update.subcategory_id = int(request.form['subcategory_id'])
        resources_json_string = request.form.get('resources', '[]')

        # 2. Handle optional image update
        if 'featured_image' in request.files:
            file = request.files['featured_image']
            if file and file.filename != '':
                # (Optional) Delete old image file
                if discourse_to_update.featured_image:
                    old_image_path = os.path.join(current_app.root_path, 'static', 'uploads', 'discourse_images', discourse_to_update.featured_image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image
                timestamp = int(datetime.now().timestamp())
                base_filename = secure_filename(os.path.splitext(file.filename)[0])
                new_image_filename = f"{base_filename}_{timestamp}.webp"
                save_path_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'discourse_images')
                os.makedirs(save_path_dir, exist_ok=True)
                save_path = os.path.join(save_path_dir, new_image_filename)
                
                with Image.open(file.stream) as img:
                    img.save(save_path, 'webp', quality=85)
                
                # Update the filename in the database
                discourse_to_update.featured_image = new_image_filename

        # 3. Synchronize resources (simple and robust: delete all, then re-add)
        discourse_to_update.resources.clear() # Requires cascade="all, delete-orphan" on relationship
        db.session.flush() # Persist the deletion before adding new ones

        resources_data = json.loads(resources_json_string)
        if resources_data:
            for res_data in resources_data:
                resource = Resource(
                    name=res_data['name'],
                    type=ResourceType[res_data['type']],
                    medium=ResourceMedium[res_data['medium']],
                    link=res_data['link']
                )
                discourse_to_update.resources.append(resource)

        db.session.commit()
        current_app.logger.info(f"Discourse ID {discourse_id} updated successfully.")

        # Redirect to the discourse's view page
        return jsonify({
            "status": "success",
            "message": "Discourse updated successfully!",
            "redirect_url": url_for('discourse.dialogues')
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during discourse update process for ID {discourse_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An internal server error occurred."}), 500

    
# ============= ROUTE FOR VIEWING DIALOGUES (UPDATED) ===================
@discourse_bp.route('/')
@discourse_bp.route('/dialogues')
def dialogues():
    """
    Renders the main dialogues page.
    - If 'discourse_id' is in the URL, it loads that specific discourse.
    - Otherwise, it loads the latest approved discourse.
    """
    requested_discourse_id = request.args.get('discourse_id', type=int)
    
    content_to_load = None

    # Eagerly load all related data needed for the initial render
    query_options = [
        joinedload(DiscourseBlog.subcategory).joinedload(SubCategory.category),
        joinedload(DiscourseBlog.author),
        joinedload(DiscourseBlog.resources),
        joinedload(DiscourseBlog.comments).joinedload(DiscourseComment.commenter) # Eager load comments and their authors
    ]

    if requested_discourse_id:
        current_app.logger.info(f"Loading specific discourse with ID: {requested_discourse_id}")
        content_to_load = DiscourseBlog.query.options(*query_options).get(requested_discourse_id)
    else:
        current_app.logger.info("Loading latest discourse.")
        content_to_load = DiscourseBlog.query.filter_by(is_approved=True)\
                                          .order_by(DiscourseBlog.date_posted.desc())\
                                          .options(*query_options)\
                                          .first()
    
    return render_template(
        'dialogues.html',
        initial_content=content_to_load
    )

# ============= API ENDPOINT TO GET DISCOURSE DETAILS (UPDATED) ================
@discourse_bp.route('/api/get/<int:discourse_id>')
def get_discourse_details(discourse_id):
    """API endpoint to fetch the full details of a single discourse, including comments."""
    try:
        discourse = DiscourseBlog.query.options(
            joinedload(DiscourseBlog.resources),
            joinedload(DiscourseBlog.comments).joinedload(DiscourseComment.commenter) # Eagerly load comments and authors
        ).get(discourse_id)

        if not discourse:
            return jsonify({"status": "error", "message": "Discourse not found"}), 404

        # Sort comments by date posted
        sorted_comments = sorted(discourse.comments, key=lambda c: c.date_commented)

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
                        "type": resource.type.value,
                        "name": resource.name,
                        "link": resource.link
                    } for resource in discourse.resources
                ],
                "comments": [ # NEW: Add comments to the payload
                    {
                        "body": comment.body,
                        "author_name": f"{comment.commenter.name} {comment.commenter.other_names}",
                        "date_commented": comment.date_commented.strftime('%B %d, %Y at %I:%M %p')
                    } for comment in sorted_comments
                ]
            }
        }
        return jsonify(data_to_return)
    except Exception as e:
        current_app.logger.error(f"API Error fetching discourse {discourse_id}: {e}")
        return jsonify({"status": "error", "message": "An internal server error occurred"}), 500

# === API ROUTE TO ADD A COMMENT TO A DISCOURSE ===
@discourse_bp.route('/api/add-comment', methods=['POST'])
@login_required
def add_comment():
    """API endpoint to add a new comment to an existing discourse."""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid request. No data provided.'}), 400

    discourse_id = data.get('discourse_id')
    comment_body = data.get('comment_body')

    if not discourse_id or not comment_body or not isinstance(comment_body, str) or not comment_body.strip():
        return jsonify({'status': 'error', 'message': 'Missing discourse ID or comment body.'}), 400

    try:
        # Verify the discourse exists
        discourse = DiscourseBlog.query.get(discourse_id)
        if not discourse:
            return jsonify({'status': 'error', 'message': 'Discourse not found.'}), 404

        # Create the new comment
        new_comment = DiscourseComment(
            user_id=current_user.id,
            discourse_id=discourse.id,
            body=comment_body.strip(),
            ip_address=request.remote_addr
        )

        db.session.add(new_comment)
        db.session.commit()

        current_app.logger.info(f"User {current_user.id} added comment to Discourse {discourse_id}")

        return jsonify({
            "status": "success",
            "message": "Your contribution has been submitted successfully!",
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding comment for discourse {discourse_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'An internal server error occurred.'}), 500


# === API ROUTE TO ADD A RESOURCE TO A DISCOURSE ===
@discourse_bp.route('/api/add-resource', methods=['POST'])
@login_required
def add_resource():
    """API endpoint to add a new resource to an existing discourse."""
    data = request.get_json()
    
    required_fields = ['discourse_id', 'name', 'type', 'medium', 'link']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400

    try:
        discourse = DiscourseBlog.query.get(data['discourse_id'])
        if not discourse:
            return jsonify({'status': 'error', 'message': 'Discourse not found.'}), 404

        new_resource = Resource(
            discourse_id=discourse.id,
            name=data['name'],
            type=ResourceType[data['type']],
            medium=ResourceMedium[data['medium']],
            link=data['link']
        )
        
        db.session.add(new_resource)
        db.session.commit()

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
        return jsonify({'status': 'error', 'message': f'Invalid value for type or medium: {e}'}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding resource: {e}")
        return jsonify({'status': 'error', 'message': 'An internal server error occurred.'}), 500
    

@discourse_bp.route('/api/navigation/<int:discourse_id>')
def get_navigation_links(discourse_id):
    """
    Given a discourse ID, finds the IDs of the chronologically previous and next
    approved discourses.
    """
    try:
        current_discourse = DiscourseBlog.query.get(discourse_id)
        if not current_discourse:
            return jsonify({"status": "error", "message": "Discourse not found"}), 404

        if not current_discourse.date_posted:
            current_app.logger.warning(f"Discourse ID {discourse_id} has no date_posted. Cannot determine navigation.")
            return jsonify({"status": "success", "previous_id": None, "next_id": None})

        previous_post = DiscourseBlog.query.filter(
            DiscourseBlog.date_posted < current_discourse.date_posted,
            DiscourseBlog.is_approved == True
        ).order_by(
            DiscourseBlog.date_posted.desc(), 
            DiscourseBlog.id.desc()
        ).first()

        next_post = DiscourseBlog.query.filter(
            DiscourseBlog.date_posted > current_discourse.date_posted,
            DiscourseBlog.is_approved == True
        ).order_by(
            DiscourseBlog.date_posted.asc(),
            DiscourseBlog.id.asc()
        ).first()

        return jsonify({
            "status": "success",
            "previous_id": previous_post.id if previous_post else None,
            "next_id": next_post.id if next_post else None
        })

    except Exception as e:
        current_app.logger.error(f"API Error fetching navigation for discourse {discourse_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An internal server error occurred"}), 500