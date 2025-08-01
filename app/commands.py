import click
from flask.cli import with_appcontext
from app.dol_db.models import db, Category, SubCategory
from app.dol_db.dbops import seed_roles

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

def init_app(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(seed_db_command)