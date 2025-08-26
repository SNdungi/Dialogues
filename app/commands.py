# /project_folder/app/commands.py

import click
from flask.cli import with_appcontext
# Corrected import path based on your __init__.py
from .dol_db.models import db, Category, SubCategory, LiturgicalDay
from .dol_db.dbops import seed_roles
from datetime import datetime
from .dol_liturgy.lit_utils import litcal_url, safe_fetch

# --- THIS IS THE ONLY IMPORT YOU NEED ---
from config import config

@click.command(name='seed-db')
@with_appcontext
def seed_db_command():
    """Seeds the database using the pre-loaded data from the config module."""
    
    click.echo('--- Seeding Discourse Categories ---')
    db.session.query(SubCategory).delete()
    db.session.query(Category).delete()
    db.session.commit()
    click.echo('Cleared existing categories and subcategories.')

    try:
        # --- SIMPLE, DIRECT, NO FILE I/O ---
        # 1. Access the pre-loaded data directly from the config object.
        all_seed_data = config.GlOBAL_CONFIG
        
        # 2. Drill down into the dictionary, just as you requested.
        category_data_to_parse = all_seed_data.get('discourse_categories', {})

        if not category_data_to_parse:
            click.secho("Warning: 'discourse_categories' key not found in the loaded data. Skipping category seeding.", fg='yellow')
        else:
            # The rest of your logic is unchanged because it was already correct.
            for key, cat_data in category_data_to_parse.items():
                category_name = cat_data.get('name')
                if not category_name:
                    continue
                
                new_category = Category(name=category_name)
                db.session.add(new_category)
                db.session.flush()
                click.echo(f'Seeding category: {new_category.name}')

                for sub_name in cat_data.get('subcategories', []):
                    new_subcategory = SubCategory(name=sub_name, category_id=new_category.id)
                    db.session.add(new_subcategory)
                    click.echo(f'  -> Subcategory: {new_subcategory.name}')

            db.session.commit()
            click.echo('Category seeding complete.')
        
        click.echo('\n--- Seeding Roles ---')
        seed_roles()
        click.echo("Database roles seeded successfully.")

    except Exception as e:
        db.session.rollback()
        click.secho(f'An error occurred during seeding: {e}', fg='red')


@click.command(name='liturgy:fetch-calendar')
@with_appcontext
@click.argument("year", type=int)
@click.option("--nation", default=None, help="National calendar identifier (e.g., 'US').")
@click.option("--diocese", default=None, help="Diocesan calendar identifier.")
def fetch_calendar(year, nation, diocese):
    """
    Fetches the liturgical calendar for a given year and persists it to the database.
    Example: flask liturgy:fetch-calendar 2024 --nation US
    """
    api_url = litcal_url(nation=nation, diocese=diocese, year=year)
    region_key = diocese or nation or 'GR' # General Roman is the default
    click.echo(f"Fetching calendar for Year: {year}, Region: {region_key} from {api_url}")
    calendar_data, err = safe_fetch(api_url, ttl=0) # ttl=0 to bypass cache for the script
    if err or not calendar_data or "litcal" not in calendar_data:
        click.secho(f"Error fetching data: {err}", fg='red')
        return

    events = calendar_data.get("litcal", [])
    if not events:
        click.echo("No liturgical events found in the API response.")
        return

    click.echo(f"Found {len(events)} events. Processing and saving to database...")
    events_by_date = {}
    for event in events:
        event_date_str = f"{event['year']}-{event['month']}-{event['day']}"
        if event_date_str not in events_by_date:
            events_by_date[event_date_str] = []
        events_by_date[event_date_str].append(event)
    
    new_entries = 0
    for date_str, daily_events in events_by_date.items():
        primary_event = max(daily_events, key=lambda x: x['grade'])
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        entry = LiturgicalDay(
            date=target_date,
            region=region_key,
            year=primary_event['year'],
            name=primary_event['name'],
            grade=primary_event['grade'],
            grade_name=primary_event['grade_lcl'],
            liturgical_season=primary_event.get('liturgical_season_lcl'),
            full_data=daily_events # Store ALL events for that day
        )
        db.session.merge(entry)
        new_entries += 1

    db.session.commit()
    click.secho(f"Successfully processed and saved {new_entries} liturgical days for {year} [{region_key}].", fg='green')

        
def init_app(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(seed_db_command)
    
    app.cli.add_command(fetch_calendar)