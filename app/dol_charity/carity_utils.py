import json
from os import path
from flask import current_app

def load_app_json(filename):
    """Helper to load a JSON file from the main application's static/data directory."""
    filepath = path.join(current_app.static_folder, 'data', filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        current_app.logger.error(f"FATAL: Could not load or parse required config file: {filepath}")
        return {}