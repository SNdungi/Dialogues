# /project_folder/app/lit_utils.py
# /project_folder/app/lit_utils.py
import requests, time
from urllib.parse import urlencode
import asyncio
import datetime
from plugins.catholic_mass_readings import USCCB,models


"""
Blueprint helpers for Catholic devotions + liturgical calendar.
- Extended safe_fetch(url, params, headers, method, json, ttl, cache_key)
- Centralized endpoints & defaults
- Caching for daily devotions and calendar data
"""

# -------------------------
# Centralized endpoints
# -------------------------
API = {
    # LitCal (official project)
    "LITCAL_BASE": "https://litcal.johnromanodorazio.com/api/dev/calendar",

    # TCCP API endpoints
    "TCCP_PRAYERS": "https://the-collection-of-catholic-prayers-api.vercel.app/v1/basic_prayers",
    "TCCP_STATIONS": "https://the-collection-of-catholic-prayers-api.vercel.app/v1/stations_of_cross",
    "TCCP_SAINTS": "https://the-collection-of-catholic-prayers-api.vercel.app/v1/saints",

    # YoriFaith API endpoints
    "YORI_ROSARY": "https://yorifaith.cf/rosary/v1/today",
    "YORI_READINGS": "https://yorifaith.cf/daily-readings-podcasts/v1/today",
    "YORI_SAINT": "https://yorifaith.cf/saint-of-the-day/v1/saints",
}


DEFAULTS = {
    "locale": "en-US",     # use US English; underscores are normalized to hyphens by the ecosystem
    "accept": "application/json",
    "calendar_ttl": 60 * 60 * 12,  # 12h cache for calendars
    "devotions_ttl": 60 * 15,      # 15m cache for daily devotions
    "timeout": 10,
}

# -------------------------
# Simple in-memory TTL cache
# -------------------------
_CACHE = {}  # key -> {"exp": <epoch>, "data": <payload>}

def _cache_get(key):
    now = time.time()
    item = _CACHE.get(key)
    if item and item["exp"] > now:
        return item["data"]
    if item:
        _CACHE.pop(key, None)
    return None

def _cache_set(key, data, ttl):
    _CACHE[key] = {"exp": time.time() + max(1, int(ttl)), "data": data}

# -------------------------
# Extended safe_fetch
# -------------------------
def safe_fetch(
    url: str,
    *,
    method: str = "GET",
    params: dict | None = None,
    headers: dict | None = None,
    json: dict | None = None,
    timeout: int | float | None = None,
    ttl: int | None = None,
    cache_key: str | None = None,
):
    """
    Robust fetch with:
      - optional params/headers/json
      - JSON/text auto-parsing
      - per-request TTL cache
      - graceful error shaping
    Returns: (data, error_dict_or_None)
    """
    timeout = timeout or DEFAULTS["timeout"]
    params = params or {}
    headers = {"Accept": DEFAULTS["accept"], **(headers or {})}

    # Build a stable cache key if not provided
    if cache_key is None:
        # Avoid leaking sensitive headers; this is a public API so headers are fine
        key_parts = [
            method.upper(),
            url,
            urlencode(sorted(params.items()), doseq=True),
            urlencode(sorted(headers.items())),
        ]
        cache_key = "|".join(key_parts)

    # Cache hit
    if ttl:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached, None

    try:
        resp = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            headers=headers,
            json=json,
            timeout=timeout,
        )
    except requests.RequestException as e:
        return None, {"kind": "network_error", "detail": str(e)}

    ct = resp.headers.get("Content-Type", "")
    if not resp.ok:
        return None, {
            "kind": "http_error",
            "status": resp.status_code,
            "content_type": ct,
            "detail": (resp.text or "")[:400],
        }

    # parse
    data = None
    try:
        if "application/json" in ct:
            data = resp.json()
        else:
            data = resp.text  # XML / ICS / plain text, etc.
    except Exception as e:
        # Last resort: return text
        data = resp.text
        # but flag parse issue (non-fatal)
        parse_err = {"kind": "parse_warning", "detail": str(e)}
    else:
        parse_err = None

    # Cache store
    if ttl:
        _cache_set(cache_key, data, ttl)

    # Return with optional parse warning attached (non-fatal)
    return data, parse_err

# -------------------------
# URL helpers for LitCal
# -------------------------
def litcal_url(*, nation: str | None = None, diocese: str | None = None, year: int | None = None) -> str:
    """
    Compose the LitCal path:
      - General Roman: /calendar[/YEAR]
      - National:      /calendar/nation/{NATION}[/YEAR]
      - Diocesan:      /calendar/diocese/{DIOCESE}[/YEAR]
    """
    base = API["LITCAL_BASE"].rstrip("/")
    if nation:
        path = f"{base}/nation/{nation}"
    elif diocese:
        path = f"{base}/diocese/{diocese}"
    else:
        path = base
    if year:
        path = f"{path}/{year}"
    return path



# The core async function now accepts a date object
async def fetch_readings_async(target_date: datetime.date):
    """Asynchronously fetches mass readings for a specific date."""
    try:
        # The library uses an async context manager
        async with USCCB() as usccb:
            # --- FIX: Explicitly specify the MassType as DAILY ---
            mass = await usccb.get_mass(target_date, type_=models.MassType.DEFAULT) 
            # Note: The argument name is 'type_'
            return mass
    except Exception as e:
        # If anything goes wrong (website changed, network error), log it and return None
        print(f"Error fetching mass readings for {target_date}: {e}")
        return None


# The synchronous wrapper now accepts and passes on the date object
def get_daily_readings(target_date: datetime.date):
    """
    A synchronous wrapper to run the async fetcher for a specific date.
    This is the function you'll import into your routes.
    """
    if not isinstance(target_date, datetime.date):
        print("Error: get_readings_for_date requires a datetime.date object.")
        return None
        
    # asyncio.run() starts the async event loop, runs the task, and closes the loop.
    return asyncio.run(fetch_readings_async(target_date))




