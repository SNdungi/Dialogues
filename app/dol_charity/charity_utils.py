import json
from os import path
from flask import current_app
from app.dol_db.models import Charity, CharityCategory, CharityCategoryDef
from sqlalchemy import or_
from flask_paginate import Pagination

def search_charities(search_query, active_filter, page, per_page=9):
    """
    A comprehensive search and filter abstraction for charities.

    Args:
        search_query (str): The text to search for in name, description, and location.
        active_filter (str): The category to filter by (e.g., 'children', 'all').
        page (int): The current page number for pagination.
        per_page (int): The number of results per page.

    Returns:
        tuple: A tuple containing (list_of_charities_for_page, pagination_object).
    """
    # 1. Build the base query for all vetted charities
    query = Charity.query.filter_by(is_vetted=True)

    # 2. Apply text search filter if a query is provided
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Charity.name.ilike(search_term),
                Charity.description.ilike(search_term),
                Charity.location.ilike(search_term) # Also search by location
            )
        )

    # 3. Apply category filter if a specific category is chosen
    if active_filter and active_filter != 'all':
        try:
            # Convert the lowercase filter string to an Enum member
            category_enum = CharityCategory[active_filter.upper()]
            # Join with the categories relationship and filter by the enum
            query = query.join(Charity.categories).filter(CharityCategoryDef.name == category_enum)
        except KeyError:
            # If the filter is invalid, ignore it.
            pass

    # 4. Get the total count of matching charities BEFORE pagination
    total = query.count()

    # 5. Apply ordering and pagination to the query
    offset = (page - 1) * per_page
    charities_for_page = query.order_by(Charity.name).limit(per_page).offset(offset).all()

    # 6. Set up the Pagination object for the view
    pagination = Pagination(page=page, total=total, per_page=per_page,
                            css_framework='bootstrap5', record_name='charities')

    return charities_for_page, pagination

def load_app_json(filename):
    """Helper to load a JSON file from the main application's static/data directory."""
    filepath = path.join(current_app.static_folder, 'data', filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        current_app.logger.error(f"FATAL: Could not load or parse required config file: {filepath}")
        return {}