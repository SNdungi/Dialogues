# /project_folder/app/dol_charity/charity_routes.py

import json
from os import path
from flask import Blueprint, render_template, current_app, request
from flask_login import login_required
from app.dol_db.models import Charity, CharityCategoryDef, CharityCategory
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import or_

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
    """Renders the main charity donation page with server-side pagination and filtering."""
    
    # --- 1. Get current page, search, and filter parameters from the URL ---
    page = request.args.get(get_page_parameter(), type=int, default=1)
    search_query = request.args.get('search', type=str, default='').strip()
    active_filter = request.args.get('filter', type=str, default='all').strip()

    # --- 2. Build the base query ---
    # Start with all vetted charities
    query = Charity.query.filter_by(is_vetted=True)

    # --- 3. Apply search filter if present ---
    if search_query:
        # Search in charity name and description
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Charity.name.ilike(search_term),
                Charity.description.ilike(search_term)
            )
        )

    # --- 4. Apply category filter if present ---
    if active_filter and active_filter != 'all':
        # Find the category enum member that matches the filter string
        try:
            category_enum = CharityCategory[active_filter.upper()]
            query = query.join(Charity.categories).filter(CharityCategoryDef.name == category_enum)
        except KeyError:
            # Handle invalid filter gracefully, maybe flash a message or ignore
            pass

    # --- 5. Get the total count BEFORE pagination ---
    total = query.count()

    # --- 6. Apply pagination to the query ---
    per_page = 9 # Number of cards per page
    offset = (page - 1) * per_page
    charities_for_page = query.order_by(Charity.name).limit(per_page).offset(offset).all()

    # --- 7. Set up the Pagination object ---
    pagination = Pagination(page=page, total=total, per_page=per_page,
                            css_framework='bootstrap5', record_name='charities')

    # --- 8. Get all unique, active categories for the filter pills ---
    active_categories = (
        CharityCategoryDef.query
        .join(CharityCategoryDef.charities)
        .filter(Charity.is_vetted == True)
        .distinct()
        .order_by(CharityCategoryDef.name)
        .all()
    )
    
    # --- 9. Load static currency data ---
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