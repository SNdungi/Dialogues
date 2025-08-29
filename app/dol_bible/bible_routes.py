
import os
from flask import Blueprint, jsonify, current_app, g, render_template,request
from datetime import datetime
from config import config
from .bible_utils import get_bible_db, parse_query, fetch_from_db

bible_bp = Blueprint('bible', __name__,
                    url_prefix='/bible',
                    template_folder='templates/bible',
                    static_folder='static'
                     )

# NEW: Context processor to make 'now' available for the footer copyright year
@bible_bp.app_context_processor
def inject_now():
    return {'now': datetime.utcnow}

# === NEW: HOME ROUTE ===
@bible_bp.route('/')
def bible_home():
    """
    Renders the main Bible reader interface and provides a default
    passage for the JavaScript to load on initialization.
    """
    # We pass the default passage as a variable to the template.
    return render_template('bible.html', default_passage="John 3:16")

# A simple mapping for full translation names
TRANSLATION_NAMES = config.GLOBAL_CONFIG.get('bible_translations', {})



@bible_bp.teardown_app_request
def teardown_bible_dbs(exception):
    """Closes any open Bible DB connections at the end of the request."""
    for key in list(g.__dict__.keys()):
        if key.startswith('bible_db_'):
            db = g.pop(key, None)
            if db is not None:
                db.close()


# --- API ROUTES ---

# === NEW ENDPOINT: Get available translations ===
@bible_bp.route('/api/translations')
def get_translations():
    """
    Scans the bible data directory and returns a list of available translations.
    """
    db_path = current_app.config['BIBLE_DATABASES_PATH']
    try:
        files = os.listdir(db_path)
        translations = []
        for f in files:
            if f.endswith('.db'):
                abbr = f.replace('.db', '')
                translations.append({
                    "abbreviation": abbr,
                    "name": TRANSLATION_NAMES.get(abbr, abbr) # Fallback to abbr if name not mapped
                })
        return jsonify(translations)
    except FileNotFoundError:
        return jsonify({"error": "Bible data directory not found."}), 500

# === NEW ENDPOINT: Get metadata for a specific translation ===
@bible_bp.route('/api/<string:version>/metadata')
def get_metadata(version):
    """
    Returns the book list, chapter counts, and book order for a version.
    """
    conn = get_bible_db(version)
    if conn is None:
        return jsonify({"error": f"Translation '{version}' not found."}), 404

    cursor = conn.cursor()
    
    # --- START OF FIX ---
    # Dynamically and safely create the table names.
    # We can trust `version` because we've already validated it by finding the file.
    books_table = f"{version}_books"
    verses_table = f"{version}_verses"

    query = f"""
        SELECT b.name, MAX(v.chapter) as chapter_count
        FROM {verses_table} v
        JOIN {books_table} b ON v.book_id = b.id
        GROUP BY b.name
        ORDER BY b.id;
    """
    # --- END OF FIX ---
    
    cursor.execute(query) # The query string now has the correct table names
    rows = cursor.fetchall()
    
    metadata = {
        'books': {row['name']: row['chapter_count'] for row in rows},
        'bookOrder': [row['name'] for row in rows]
    }
    
    return jsonify(metadata)

@bible_bp.route('/api/intelligent_search')
def intelligent_search():
    """
    The new primary search endpoint that uses the parsing engine.
    """
    query = request.args.get('q', '').strip()
    version = request.args.get('t', 'kjv').lower()

    if not query:
        return jsonify({"error": "A search query is required."}), 400

    # 1. Parse the user's query into a structured object
    search_obj = parse_query(query)

    # 2. Fetch the results from the database using the parsed object
    results, error = fetch_from_db(version, search_obj)
    
    if error:
        return jsonify({"error": error}), 500
    if not results:
        return jsonify({"error": "No results found for your query."}), 404

    # 3. Format the results and metadata for the frontend
    response_data = {
        "translation_abbreviation": version.upper(),
        "translation_name": TRANSLATION_NAMES.get(version.upper(), version.upper()),
        "search_type": search_obj['type'],
        "verses": [dict(row) for row in results]
    }
    
    # Add a canonical reference for display
    if search_obj['type'] != 'text':
        ref = search_obj['book']
        if search_obj.get('chapter'):
            ref += f" {search_obj['chapter']}"
        if search_obj.get('verse_start'):
            ref += f":{search_obj['verse_start']}"
            if search_obj.get('verse_end'):
                ref += f"-{search_obj['verse_end']}"
        response_data['reference'] = ref
    else:
        response_data['reference'] = f'Text search for "{query}"'

    return jsonify(response_data)