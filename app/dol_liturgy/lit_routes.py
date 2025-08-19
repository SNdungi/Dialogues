import requests
from flask import Blueprint, render_template
from datetime import date, datetime


liturgy_bp = Blueprint('liturgy_bp', __name__,
                         url_prefix='/liturgy',
                         template_folder='templates/liturgy',
                         static_folder='static')

# This helper function cleans the HTML that the API sometimes returns in the reading body
def format_reading_body(body_html):
    """Splits the body into a list of paragraphs, removing HTML tags."""
    if not body_html:
        return []
    # Simple replace for <p> tags and split by newline.
    # A more robust solution might use BeautifulSoup if the HTML is complex.
    cleaned_text = body_html.replace('<p>', '').replace('</p>', '\n').strip()
    return [p.strip() for p in cleaned_text.splitlines() if p.strip()]

@liturgy_bp.route('/liturgy')
def liturgy():
    """
    Fetches daily liturgical data from the Vachan API and renders the liturgy page.
    """
    today = date.today()
    api_date_format = today.strftime("%Y-%m-%d")
    display_date_format = today.strftime("%B %d, %Y")
    
    # The API endpoint for the current day
    api_url = f"https://vachan-api.herokuapp.com/api/v1/readings/{api_date_format}"
    
    liturgy_data = {}

    try:
        # Make the API request with a timeout
        response = requests.get(api_url, timeout=10)
        # This will raise an exception for bad status codes (like 404 or 500)
        response.raise_for_status()
        
        raw_data = response.json()
        
        # --- Structure the data for our template ---
        liturgy_data = {
            'date': raw_data.get('date'),
            'season': raw_data.get('season'),
            'season_week': raw_data.get('season_week'),
            'celebration': raw_data.get('celebration'),
            'color': raw_data.get('color', {}), # Safely access nested color dict
            'readings': [],
            'prayers': []
        }
        
        # Process readings
        for reading in raw_data.get('readings', []):
            liturgy_data['readings'].append({
                'title': reading.get('title'),
                'reference': reading.get('reference'),
                'response': reading.get('response', ''), # For psalms
                'body': format_reading_body(reading.get('text')) # Use our helper function
            })
            
        # Process prayers (Mass Propers)
        for prayer in raw_data.get('prayers', []):
             liturgy_data['prayers'].append({
                'title': prayer.get('title'),
                'body': prayer.get('text')
            })

    except requests.exceptions.RequestException as e:
        # Handle network errors, timeouts, bad responses, etc.
        print(f"Error fetching liturgical data: {e}")
        liturgy_data['error'] = "Could not connect to the liturgy service. Please try again later."
    except Exception as e:
        # Handle other potential errors (e.g., JSON parsing)
        print(f"An unexpected error occurred: {e}")
        liturgy_data['error'] = "An unexpected error occurred while processing the data."

    return render_template('liturgy.html', 
                           liturgy_data=liturgy_data, 
                           date_for_display=display_date_format)

# You can keep these other routes or remove them if they are not needed for this blueprint
@liturgy_bp.route('/prayers')
def Prayer():
    return "<h1>Prayers, devotions and chaplets page.</h1>"

@liturgy_bp.route('/word')
def Word():
    return "<h1>This is the word page.</h1>"

@liturgy_bp.route('/commentary')
def Commentary():
    return "<h1>These are commentaries on the word page.</h1>"


 