# /project_folder/app/dol_discourse/disc_routes.py

import os
from flask import Blueprint, render_template, current_app, request, jsonify, url_for
from datetime import datetime
from app.dol_db.models import db, DiscourseBlog, User, Category, SubCategory
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user

# 1. Define the Blueprint correctly (removed url_defaults)
discourse_bp = Blueprint('discourse', __name__,
                         url_prefix='/discourse',
                         template_folder='templates/discourse',
                         static_folder='static')


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
    """Handles saving a new discourse, now linking to a subcategory_id."""
    data = request.get_json()
    if not data or not all(k in data for k in ['title', 'body', 'subcategory_id']):
        return jsonify({"status": "error", "message": "Missing title, body, or subcategory"}), 400

    current_user = User.query.first()  # Replace with get_jwt_identity() in production
    if not current_user:
        return jsonify({"status": "error", "message": "No users found"}), 500
    
    try:
        new_discourse = DiscourseBlog(
            user_id=current_user.id,
            title=data['title'],
            body=data['body'],
            subcategory_id=int(data['subcategory_id']),
            reference=f"DISC-{int(datetime.now().timestamp())}",
            is_approved=True 
        )
        
        db.session.add(new_discourse)
        db.session.commit()

        return jsonify({
            "status": "success", 
            "message": "Discourse saved successfully!",
            # 2. Corrected the url_for endpoint to point to the 'discourse' blueprint
            "redirect_url": url_for('discourse.dialogues') 
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving discourse: {e}")
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500


# --- PUBLIC-FACING DIALOGUES ROUTE ---

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
    

# --- NEW ROUTE FOR VIEWING A SINGLE DISCOURSE ---
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