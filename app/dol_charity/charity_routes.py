# /project_folder/app/dol_charity/charity_routes.py

import json
import os
from os import path
from flask import Blueprint, render_template, current_app, request,flash, redirect, url_for, jsonify
from flask_login import login_required
from app.dol_db.models import Charity, CharityCategoryDef, CharityCategory,db
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import or_
import uuid # For generating unique filenames
from werkzeug.utils import secure_filename
from PIL import Image # For image dimension validation

from app.dol_charity.charity_utils import search_charities

charity_bp = Blueprint(
    'charity_bp',
    __name__,
    url_prefix='/charity',
    template_folder='templates',
    static_folder='static'
)

def load_app_json(filename):
    """Helper to load a JSON file from the main application's static/data directory."""
    filepath = path.join(current_app.static_folder, 'data', filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        current_app.logger.error(f"FATAL: Could not load or parse required config file: {filepath}")
        return {}

@charity_bp.route('/home')
@login_required
def charity_home():
    """Renders the main charity donation page using the search abstraction."""
    
    # Get parameters from the URL
    page = request.args.get(get_page_parameter(), type=int, default=1)
    search_query = request.args.get('search', type=str, default='').strip()
    active_filter = request.args.get('filter', type=str, default='all').strip()

    # Use the abstracted search function to get results and pagination
    charities_for_page, pagination = search_charities(search_query, active_filter, page)

    # Get all unique, active categories for the filter pills
    active_categories = (
        CharityCategoryDef.query
        .join(CharityCategoryDef.charities)
        .filter(Charity.is_vetted == True)
        .distinct()
        .order_by(CharityCategoryDef.name)
        .all()
    )
    
    currency_data = load_app_json('currencies.json')

    return render_template(
        'charity.html', 
        charities=charities_for_page,
        categories=active_categories,
        currency_data=currency_data,
        pagination=pagination,
        search_query=search_query,
        active_filter=active_filter
    )

@charity_bp.route('/api/search')
@login_required
def api_search_charities():
    """API endpoint for live charity search, returns HTML partials."""
    
    page = request.args.get(get_page_parameter(), type=int, default=1)
    search_query = request.args.get('search', type=str, default='').strip()
    active_filter = request.args.get('filter', type=str, default='all').strip()
    
    charities_for_page, pagination = search_charities(search_query, active_filter, page)
    
    # Render just the list of charity cards and the pagination controls as HTML snippets
    charity_list_html = render_template(
        '_charity_list.html', 
        charities=charities_for_page
    )
    pagination_html = render_template(
        '_pagination.html',
        pagination=pagination
    )
    
    return jsonify({
        'charity_list_html': charity_list_html,
        'pagination_html': pagination_html
    })

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_IMAGE_SIZE_MB = 2
MAX_IMAGE_DIMENSION = 1000 # Max width/height in pixels

def allowed_file(filename):
    """Checks if a filename has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@charity_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register_charity():
    """Renders and handles the charity registration form."""
    
    all_categories = CharityCategoryDef.query.order_by(CharityCategoryDef.name).all()

    if request.method == 'POST':
        # --- 1. Get Form Data ---
        # ... (This part is unchanged) ...
        name = request.form.get('name')
        description = request.form.get('description')
        category_ids = request.form.getlist('categories') 

        # --- 2. Basic Validation ---
        # ... (This part is unchanged) ...
        if not name or not description or not category_ids:
            flash('Name, Description, and at least one Category are required.', 'danger')
            return render_template('charity_registration.html', categories=all_categories)
        if Charity.query.filter(Charity.name.ilike(name)).first():
            flash('A charity with this name already exists.', 'danger')
            return render_template('charity_registration.html', categories=all_categories)

        # --- 3. Handle File Upload ---
        logo_filename_to_save = None # Use this variable to store the final filename for the DB
        if 'logo_image' in request.files:
            logo_file = request.files['logo_image']

            if logo_file and logo_file.filename != '':
                if not allowed_file(logo_file.filename):
                    flash('Invalid image file type. Please use png, jpg, jpeg, or webp.', 'danger')
                    return render_template('charity_registration.html', categories=all_categories)

                # --- START OF MODIFIED UPLOAD & CONVERSION LOGIC ---
                try:
                    # Perform all validation on the file stream before saving
                    logo_file.seek(0, os.SEEK_END)
                    file_length = logo_file.tell()
                    if file_length > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                        flash(f'Image file is too large (max {MAX_IMAGE_SIZE_MB}MB).', 'danger')
                        return render_template('charity_registration.html', categories=all_categories)
                    logo_file.seek(0)

                    # Generate a unique base name (without extension)
                    unique_basename = f"charity_{uuid.uuid4().hex}"
                    
                    # The final filename WILL be .webp
                    logo_filename_to_save = f"{unique_basename}.webp"

                    # Define the full save path
                    upload_folder = os.path.join(current_app.static_folder, 'images', 'charity_logos')
                    os.makedirs(upload_folder, exist_ok=True)
                    save_path = os.path.join(upload_folder, logo_filename_to_save)

                    # Open the uploaded file stream with Pillow
                    with Image.open(logo_file) as img:
                        # Check dimensions BEFORE saving
                        if img.width > MAX_IMAGE_DIMENSION or img.height > MAX_IMAGE_DIMENSION:
                            flash(f'Image dimensions are too large (max {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}px).', 'danger')
                            return render_template('charity_registration.html', categories=all_categories)
                        
                        # Save the image, converting it to WebP format in the process
                        img.save(save_path, 'webp', quality=85) # quality can be adjusted

                except Exception as e:
                    current_app.logger.error(f"Image processing/saving failed: {e}")
                    flash('Could not process the uploaded image. It might be corrupted or in an unsupported format.', 'danger')
                    return render_template('charity_registration.html', categories=all_categories)
                # --- END OF MODIFIED LOGIC ---

        # --- 4. Create and Save to Database ---
        try:
            new_charity = Charity(
                name=request.form.get('name'),
                contact=request.form.get('contact'),
                email=request.form.get('email'),
                website=request.form.get('website'),
                location=request.form.get('location'),
                description=request.form.get('description'),
                is_vetted=False
            )
            
            # Use the .webp filename if it was successfully created
            if logo_filename_to_save:
                new_charity.logo_image = logo_filename_to_save
            
            selected_categories = CharityCategoryDef.query.filter(CharityCategoryDef.id.in_(category_ids)).all()
            for cat in selected_categories:
                new_charity.categories.append(cat)
            
            db.session.add(new_charity)
            db.session.commit()
            
            flash('Thank you for your submission! Your charity will be reviewed shortly.', 'success')
            return redirect(url_for('charity_bp.charity_home'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating charity: {e}")
            flash('An unexpected error occurred while saving your submission. Please try again.', 'danger')
        
    return render_template('charity_registration.html', categories=all_categories)