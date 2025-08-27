import sqlite3
import os
from flask import Blueprint, jsonify, current_app, g, render_template
from datetime import datetime
from config import config

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

def get_bible_db(version_abbr):
    """Gets a connection to a specific Bible version's SQLite database."""
    db_conn_key = f'bible_db_{version_abbr}'
    if db_conn_key not in g:
        db_path = os.path.join(
            current_app.config['BIBLE_DATABASES_PATH'], 
            f'{version_abbr.upper()}.db'
        )
        if not os.path.exists(db_path):
            return None
        
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True) # Connect in read-only mode
        conn.row_factory = sqlite3.Row
        g.setdefault(db_conn_key, conn)
    
    return g.get(db_conn_key)

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

# === REVISED ENDPOINT: Get a chapter, now with full translation name ===
@bible_bp.route('/api/<string:version>/<string:book>/<int:chapter>')
def get_chapter(version, book, chapter):
    """
    API endpoint to fetch an entire chapter of a book.
    """
    conn = get_bible_db(version)
    if conn is None:
        return jsonify({"error": f"Translation '{version}' not found."}), 404

    cursor = conn.cursor()
    
    books_table = f"{version}_books"
    verses_table = f"{version}_verses"

    query = f"""
        SELECT verse, text FROM {verses_table}
        WHERE book_id = (SELECT id FROM {books_table} WHERE name = ?)
        AND chapter = ?
        ORDER BY verse ASC;
    """
    
    # Capitalize book name for matching, e.g., 'john' -> 'John'
    cursor.execute(query, (book.capitalize(), chapter))
    verses = cursor.fetchall()

    if not verses:
        return jsonify({"error": "Chapter or book not found."}), 404

    results = [dict(row) for row in verses]
    
    return jsonify({
        "translation_abbreviation": version.upper(),
        "translation_name": TRANSLATION_NAMES.get(version.upper(), version.upper()),
        "reference": f"{book.capitalize()} {chapter}",
        "verses": results
    })