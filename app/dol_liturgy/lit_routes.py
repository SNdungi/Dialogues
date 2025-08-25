from flask import Blueprint, render_template, current_app, jsonify, request
from datetime import date, datetime

# Import helpers from lit_utils
from app.dol_liturgy.lit_utils import (
    get_daily_readings,
    safe_fetch,
    litcal_url,
    DEFAULTS,
    API,
)

liturgy_bp = Blueprint(
    'liturgy_bp',
    __name__,
    url_prefix='/liturgy',
    template_folder='templates/liturgy',
    static_folder='static'
)


@liturgy_bp.route('/liturgy')
def liturgy():
    today = date.today()
    year = today.year

    locale = request.args.get("locale", DEFAULTS["locale"])
    nation = request.args.get("nation", "US")
    diocese = request.args.get("diocese")

    api_url = litcal_url(nation=nation if not diocese else None,
                         diocese=diocese,
                         year=year)

    current_app.logger.info(f"Fetching liturgy calendar: {api_url} with locale {locale}")

    calendar_data, err = safe_fetch(
        api_url,
        params={"locale": locale},
        ttl=DEFAULTS["calendar_ttl"],
        cache_key=f"LITCAL::{nation or diocese or 'GR'}::{year}::{locale}",
        timeout=20,
    )

    if calendar_data is None:
        current_app.logger.error(f"Calendar fetch failed: {err}")
        calendar_data = {"error": "Could not connect to the liturgy service.", "detail": err}

    return render_template(
        'liturgy.html',
        calendar_data=calendar_data,
        national_calendar_config=nation
    )

@liturgy_bp.route("/daily-devotions")
def daily_devotions():
    today_str = date.today().isoformat()
    current_app.logger.info("Fetching daily_devotions...")

    # Fetch from APIs
    prayers_raw, err1 = safe_fetch(API["TCCP_PRAYERS"], ttl=DEFAULTS["devotions_ttl"], cache_key=f"TCCP::{today_str}")
    rosary_raw, err2 = safe_fetch(API["YORI_ROSARY"], ttl=DEFAULTS["devotions_ttl"], cache_key=f"YORI::ROSARY::{today_str}")
    saint_raw, err3 = safe_fetch(API["YORI_SAINT"], ttl=DEFAULTS["devotions_ttl"], cache_key=f"YORI::SAINT::{today_str}")

    # --- Normalize prayers (map tilte → title, pick text) ---
    prayers = []
    if isinstance(prayers_raw, list):
        for p in prayers_raw:
            prayers.append({
                "title": p.get("title") or p.get("tilte") or "Untitled Prayer",
                "text": p.get("prayerText") or p.get("prayerHTML") or ""
            })

    # --- Normalize rosary ---
    rosary = {}
    if isinstance(rosary_raw, dict) and "title" in rosary_raw:
        rosary = {
            "title": rosary_raw.get("title"),
            "mysteries": rosary_raw.get("mysteries", [])
        }

    # --- Normalize saint ---
    saint = {}
    if isinstance(saint_raw, dict) and ("title" in saint_raw or "name" in saint_raw):
        saint = {
            "title": saint_raw.get("title") or saint_raw.get("name"),
            "description": saint_raw.get("description") or saint_raw.get("bio") or ""
        }

    combined = {
        "date": today_str,
        "prayers": prayers,
        "rosary": rosary,
        "saint_of_the_day": saint,
        "errors": {"tccp": err1, "rosary": err2, "saint": err3}
    }

    return jsonify(combined)


@liturgy_bp.route('/api/get-readings/<date_str>')
def get_readings_for_date(date_str):
    """
    Fetches daily readings for a given date using the catholic-mass-readings library helper.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid date format provided.'}), 400

    current_app.logger.info(f"Fetching readings for {target_date} using lit_utils helper.")
    
    mass_data = get_daily_readings(target_date)
    if not mass_data or not mass_data.sections:
        return jsonify({
            'status': 'error',
            'message': f'Readings are not available for {date_str}.'
        }), 404

    readings_list = []
    for section in mass_data.sections:
        for reading in section.readings:
            readings_list.append({
                'title': reading.header,
                'body': reading.text
            })

    if not readings_list:
        return jsonify({
            'status': 'error',
            'message': f"Successfully fetched mass data for {date_str}, but it contained no parseable readings."
        }), 404

    return jsonify({'status': 'success', 'readings': readings_list})


