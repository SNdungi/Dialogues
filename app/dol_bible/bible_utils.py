import os
import re
from sqlalchemy import or_
from flask_paginate import Pagination
from app.dol_db.models import db  # Assuming a models.py in this blueprint or accessible from app.dol_db.models
import sqlite3
from flask import current_app, g


   
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
   
   
BOOK_ALIASES = {
    'genesis': 'Genesis', 'gen': 'Genesis', 'gn': 'Genesis',
    'exodus': 'Exodus', 'exo': 'Exodus', 'ex': 'Exodus',
    'leviticus': 'Leviticus', 'lev': 'Leviticus', 'lv': 'Leviticus',
    'numbers': 'Numbers', 'num': 'Numbers', 'nm': 'Numbers',
    'deuteronomy': 'Deuteronomy', 'deut': 'Deuteronomy', 'dt': 'Deuteronomy',
    'joshua': 'Joshua', 'josh': 'Joshua',
    'judges': 'Judges', 'jdg': 'Judges',
    'ruth': 'Ruth', 'rth': 'Ruth',
    '1 samuel': '1 Samuel', '1 sam': '1 Samuel', '1 sm': '1 Samuel',
    '2 samuel': '2 Samuel', '2 sam': '2 Samuel', '2 sm': '2 Samuel',
    '1 kings': '1 Kings', '1 kgs': '1 Kings',
    '2 kings': '2 Kings', '2 kgs': '2 Kings',
    '1 chronicles': '1 Chronicles', '1 chr': '1 Chronicles',
    '2 chronicles': '2 Chronicles', '2 chr': '2 Chronicles',
    'ezra': 'Ezra', 'ezr': 'Ezra',
    'nehemiah': 'Nehemiah', 'neh': 'Nehemiah',
    'esther': 'Esther', 'est': 'Esther',
    'job': 'Job',
    'psalms': 'Psalms', 'psalm': 'Psalms', 'psa': 'Psalms', 'ps': 'Psalms',
    'proverbs': 'Proverbs', 'prov': 'Proverbs', 'prv': 'Proverbs',
    'ecclesiastes': 'Ecclesiastes', 'eccl': 'Ecclesiastes', 'ecc': 'Ecclesiastes',
    'song of solomon': 'Song of Solomon', 'song': 'Song of Solomon', 'sos': 'Song of Solomon',
    'isaiah': 'Isaiah', 'isa': 'Isaiah',
    'jeremiah': 'Jeremiah', 'jer': 'Jeremiah',
    'lamentations': 'Lamentations', 'lam': 'Lamentations',
    'ezekiel': 'Ezekiel', 'ezek': 'Ezekiel',
    'daniel': 'Daniel', 'dan': 'Daniel',
    'hosea': 'Hosea', 'hos': 'Hosea',
    'joel': 'Joel',
    'amos': 'Amos',
    'obadiah': 'Obadiah', 'obd': 'Obadiah',
    'jonah': 'Jonah', 'jon': 'Jonah',
    'micah': 'Micah', 'mic': 'Micah',
    'nahum': 'Nahum', 'nah': 'Nahum',
    'habakkuk': 'Habakkuk', 'hab': 'Habakkuk',
    'zephaniah': 'Zephaniah', 'zeph': 'Zephaniah',
    'haggai': 'Haggai', 'hag': 'Haggai',
    'zechariah': 'Zechariah', 'zech': 'Zechariah',
    'malachi': 'Malachi', 'mal': 'Malachi',
    'matthew': 'Matthew', 'matt': 'Matthew', 'mt': 'Matthew',
    'mark': 'Mark', 'mrk': 'Mark', 'mk': 'Mark',
    'luke': 'Luke', 'luk': 'Luke', 'lk': 'Luke',
    'john': 'John', 'jhn': 'John',
    'acts of the apostles': 'Acts', 'acts': 'Acts', 'act': 'Acts',
    'romans': 'Romans', 'rom': 'Romans',
    '1 corinthians': '1 Corinthians', '1 cor': '1 Corinthians',
    '2 corinthians': '2 Corinthians', '2 cor': '2 Corinthians',
    'galatians': 'Galatians', 'gal': 'Galatians',
    'ephesians': 'Ephesians', 'eph': 'Ephesians',
    'philippians': 'Philippians', 'phil': 'Philippians', 'php': 'Philippians',
    'colossians': 'Colossians', 'col': 'Colossians',
    '1 thessalonians': '1 Thessalonians', '1 thess': '1 Thessalonians',
    '2 thessalonians': '2 Thessalonians', '2 thess': '2 Thessalonians',
    '1 timothy': '1 Timothy', '1 tim': '1 Timothy',
    '2 timothy': '2 Timothy', '2 tim': '2 Timothy',
    'titus': 'Titus', 'tit': 'Titus',
    'philemon': 'Philemon', 'phlm': 'Philemon',
    'hebrews': 'Hebrews', 'heb': 'Hebrews',
    'james': 'James', 'jas': 'James',
    '1 peter': '1 Peter', '1 pet': '1 Peter',
    '2 peter': '2 Peter', '2 pet': '2 Peter',
    '1 john': '1 John', '1 jn': '1 John',
    '2 john': '2 John', '2 jn': '2 John',
    '3 john': '3 John', '3 jn': '3 John',
    'jude': 'Jude','jud': 'Jude',
    'revelation of christ': 'Revelation of John', 'revelation of the christ': 'RRevelation of John','the revelation': 'Revelation of John', 'revelation of jesus christ':'Revelation of John',
    'revelation of john': 'Revelation of John', 'revelation': 'Revelation of John', 'rev': 'Revelation of John'
}

# A set for fast lookups of single-chapter books
SINGLE_CHAPTER_BOOKS = {"Obadiah", "Philemon", "2 John", "3 John", "Jude"}

def parse_query(query_string):
    """The core parsing logic. Tries to extract Book, Chapter, and Verses."""
    query = query_string.lower().strip()
    
    sorted_aliases = sorted(BOOK_ALIASES.keys(), key=len, reverse=True)

    for alias in sorted_aliases:
        if query.startswith(alias):
            book_name = BOOK_ALIASES[alias]
            ref_part = query[len(alias):].strip()

            # --- START OF NEW, MORE PRECISE LOGIC ---

            # Priority 1: Full reference with range (e.g., "1:15-18", "1 15 - 18")
            # Requires a clear separator like '-' or ',' for the range.
            match = re.match(r'^\s*(\d+)\s*[:\s.]\s*(\d+)\s*(?:-|,)\s*(\d+)$', ref_part)
            if match:
                g = match.groups()
                return {'type': 'reference', 'book': book_name, 'chapter': int(g[0]), 'verse_start': int(g[1]), 'verse_end': int(g[2])}

            # Priority 2: Single verse with a colon (e.g., "1:15")
            # The colon is a strong signal for a verse.
            match = re.match(r'^\s*(\d+)\s*[:]\s*(\d+)$', ref_part)
            if match:
                g = match.groups()
                return {'type': 'reference', 'book': book_name, 'chapter': int(g[0]), 'verse_start': int(g[1]), 'verse_end': None}

            # Priority 3: Chapter ONLY (e.g., "11", "150")
            # Must match the entire rest of the string to avoid partial matches like "1" from "11".
            match = re.match(r'^\s*(\d+)$', ref_part)
            if match:
                g = match.groups()
                chapter_num = int(g[0])
                return {'type': 'reference', 'book': book_name, 'chapter': chapter_num, 'verse_start': None, 'verse_end': None}
            
            # Priority 4: Single-chapter book verse (e.g., "Jude 15") or ambiguous space-separated C:V ("John 1 15")
            # This is treated as a fallback.
            match = re.match(r'^\s*(\d+)\s+(\d+)$', ref_part)
            if match:
                 g = match.groups()
                 # If it's a single chapter book, interpret as Chapter 1, Verse X
                 if book_name in SINGLE_CHAPTER_BOOKS:
                     return {'type': 'reference', 'book': book_name, 'chapter': int(g[0]), 'verse_start': int(g[1]), 'verse_end': None}
                 # Otherwise, assume Chapter:Verse
                 return {'type': 'reference', 'book': book_name, 'chapter': int(g[0]), 'verse_start': int(g[1]), 'verse_end': None}


            # If only a book name was matched (e.g., "Genesis")
            if not ref_part:
                return {'type': 'book', 'book': book_name}
            
            # --- END OF NEW LOGIC ---

    # Fallback to text search if no structured reference is found
    return {'type': 'text', 'query': query_string.strip()}

def fetch_from_db(version, search_obj):
    """Executes a search against the SQLite DB based on the parsed object."""
    conn = get_bible_db(version)
    if conn is None:
        return None, f"Translation '{version}' not found."

    cursor = conn.cursor()
    books_table = f"{version}_books"
    verses_table = f"{version}_verses"
    
    params = []
    
    if search_obj['type'] == 'text':
        sql = f"SELECT b.name, v.chapter, v.verse, v.text FROM {verses_table} v JOIN {books_table} b ON v.book_id = b.id WHERE v.text LIKE ? ORDER BY b.id, v.chapter, v.verse LIMIT 100"
        params.append(f"%{search_obj['query']}%")
    else: # Reference-based searches
        sql = f"SELECT b.name, v.chapter, v.verse, v.text FROM {verses_table} v JOIN {books_table} b ON v.book_id = b.id WHERE b.name = ?"
        params.append(search_obj['book'])

        if search_obj.get('chapter'):
            sql += " AND v.chapter = ?"
            params.append(search_obj['chapter'])
        
        if search_obj.get('verse_start'):
            if search_obj.get('verse_end'):
                sql += " AND v.verse BETWEEN ? AND ?"
                params.append(search_obj['verse_start'])
                params.append(search_obj['verse_end'])
            else:
                sql += " AND v.verse = ?"
                params.append(search_obj['verse_start'])

        sql += " ORDER BY v.verse ASC"

    try:
        cursor.execute(sql, tuple(params))
        return cursor.fetchall(), None
    except Exception as e:
        return None, f"Database query failed: {e}"