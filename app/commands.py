# /project_folder/app/commands.py

import click
from flask.cli import with_appcontext
# Corrected import path based on your __init__.py
from .dol_db.models import db, Category, SubCategory, LiturgicalDay, CharityCategory, CharityCategoryDef,Charity,Role,RoleType,user_roles,charity_category_association
from .dol_db.dbops import seed_roles
from datetime import datetime
from .dol_liturgy.lit_utils import litcal_url, safe_fetch
from config import config


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
    
@click.command(name='seed-charity-categories')
@with_appcontext
def seed_charity_categories():
    # Check if categories already exist
    if CharityCategoryDef.query.first():
        click.echo("Charity categories already seeded.")
        return
        
    for category_enum in CharityCategory:
        try:
            existing_cat = CharityCategoryDef.query.filter_by(name=category_enum).first()
            if existing_cat:
                continue
        except Exception as e:
            click.secho(f"Error checking existing category {category_enum}: {e}", fg='red')
            continue
        new_cat = CharityCategoryDef(name=category_enum)
        db.session.add(new_cat)
    db.session.commit()
    click.echo("Successfully seeded charity categories.")



@click.command(name='seed-from-toml')
@with_appcontext
def seed_from_toml():
    """Seeds the database from a specified TOML file."""
    click.echo(f"Loading seed data toml...")
    
    try:
       
        data = config.GLOBAL_CONFIG
    except Exception as e:
        click.secho(f"Error reading TOML file: {e}", fg='red')
        return

    # --- Seed Roles ---
    if 'roles' in data:
        click.echo("--- Seeding Roles ---")
        
        # --- FIX: Delete children (associations) before parents (roles) ---
        db.session.execute(user_roles.delete())
        Role.query.delete()
        
        for role_data in data['roles']:
            role = Role(
                name=RoleType[role_data['name']],
                description=role_data.get('description', '')
            )
            db.session.add(role)
        db.session.commit()
        click.secho("Roles seeded successfully.", fg='green')

    # --- Seed Charity Categories ---
    if 'charity_categories' in data:
        click.echo("--- Seeding Charity Categories ---")

        # --- FIX: Delete children (associations) before parents (categories) ---
        # Note: This is a bit redundant if we delete all charities below,
        # but it's good practice to be explicit.
        db.session.execute(charity_category_association.delete())
        CharityCategoryDef.query.delete()
        
        for cat_data in data['charity_categories']:
            category = CharityCategoryDef(name=CharityCategory[cat_data['name']])
            db.session.add(category)
        db.session.commit()
        click.secho("Charity categories seeded successfully.", fg='green')

    # --- Seed Charities ---
    if 'charities' in data:
        click.echo("--- Seeding Charities ---")
        
        # Deleting all charities will also delete their associations
        # due to the backref/relationship setup, but clearing first is safest.
        db.session.execute(charity_category_association.delete())
        Charity.query.delete()
        
        category_map = {cat.name.name: cat for cat in CharityCategoryDef.query.all()}
        
        for charity_data in data['charities']:
            charity = Charity(
                name=charity_data['name'],
                contact=charity_data.get('contact'),
                email=charity_data.get('email'),
                website=charity_data.get('website'),
                location=charity_data.get('location'),
                description=charity_data.get('description', 'No description provided.'),
                logo_image=charity_data.get('logo_image', 'default_charity.webp'),
                is_vetted=charity_data.get('is_vetted', False)
            )
            
            for cat_name in charity_data.get('categories', []):
                if cat_name in category_map:
                    charity.categories.append(category_map[cat_name])
                else:
                    click.secho(f"Warning: Category '{cat_name}' not found for charity '{charity.name}'.", fg='yellow')

            db.session.add(charity)
        db.session.commit()
        click.secho("Charities seeded successfully.", fg='green')
    else:
        click.echo("No charities found in the seed data.")  
        
        
def init_app(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(seed_db_command)
    app.cli.add_command(fetch_calendar)
    app.cli.add_command(seed_charity_categories)
    app.cli.add_command(seed_from_toml)