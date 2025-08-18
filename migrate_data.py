# migrate_data.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- IMPORTANT ---
# Make sure your Flask app isn't running while you run this script.

# --- 1. SETUP ---
# Import your models from your application
# This assumes your script is in the project root and your app is in 'app'
from app.dol_db.models import (
    db, User, Role, Category, SubCategory, DiscourseBlog, Resource,
    DiscourseComment, Organisation, Liturgy, Reading
)

# Get the project's base directory
basedir = os.path.abspath(os.path.dirname(__file__))

# --- Connection to the OLD SQLite Database ---
SQLITE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'dialogues.db')
sqlite_engine = create_engine(SQLITE_URI)
SqliteSession = sessionmaker(bind=sqlite_engine)
sqlite_session = SqliteSession()
print("Successfully connected to SQLite database.")

# --- Connection to the NEW MySQL Database ---
# Make sure your .env file is correct and accessible here
from dotenv import load_dotenv
load_dotenv()
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
MYSQL_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
mysql_engine = create_engine(MYSQL_URI)
MysqlSession = sessionmaker(bind=mysql_engine)
mysql_session = MysqlSession()
print(f"Successfully connected to MySQL database '{DB_NAME}'.")

# --- 2. DATA MIGRATION ---
# The order is VERY important. Start with tables that don't depend on others,
# and move to tables with foreign keys.

# A dictionary to map old IDs to new objects, crucial for relationships
id_map = {
    'users': {},
    'roles': {},
    'categories': {},
    'subcategories': {},
    'discourses': {},
    'liturgies': {}
}

try:
    print("\nStarting data migration...")

    # -- Roles --
    print("Migrating Roles...")
    for old_role in sqlite_session.query(Role).all():
        new_role = Role(name=old_role.name, description=old_role.description)
        mysql_session.add(new_role)
    mysql_session.commit()
    print("Roles migrated.")

    # -- Users and their Roles --
    print("Migrating Users and User-Role relationships...")
    all_roles_in_new_db = {role.name: role for role in mysql_session.query(Role).all()}
    for old_user in sqlite_session.query(User).all():
        new_user = User(
            username=old_user.username, email=old_user.email, name=old_user.name,
            other_names=old_user.other_names, organization_name=old_user.organization_name,
            website=old_user.website, password_hash=old_user.password_hash,
            is_active=old_user.is_active, is_authorized=old_user.is_authorized,
            date_created=old_user.date_created
        )
        # Re-establish role relationships
        for old_role in old_user.roles:
            new_user.roles.append(all_roles_in_new_db[old_role.name])
        mysql_session.add(new_user)
    mysql_session.commit()
    print("Users migrated.")

    # -- Categories and SubCategories --
    print("Migrating Categories and SubCategories...")
    for old_cat in sqlite_session.query(Category).all():
        new_cat = Category(name=old_cat.name)
        id_map['categories'][old_cat.id] = new_cat # Store mapping
        for old_sub in old_cat.subcategories:
            new_sub = SubCategory(name=old_sub.name)
            new_cat.subcategories.append(new_sub)
        mysql_session.add(new_cat)
    mysql_session.commit()
    print("Categories and SubCategories migrated.")


    # -- DiscourseBlog and Resources --
    print("Migrating Discourses and their Resources...")
    # Create lookup maps for Users and SubCategories in the new DB
    user_map_new_db = {user.username: user for user in mysql_session.query(User).all()}
    subcategory_map_new_db = {f"{sub.category.name}-{sub.name}": sub for sub in mysql_session.query(SubCategory).all()}

    for old_disc in sqlite_session.query(DiscourseBlog).all():
        # Find the new author and subcategory using our maps
        new_author = user_map_new_db.get(old_disc.author.username)
        subcat_key = f"{old_disc.subcategory.category.name}-{old_disc.subcategory.name}"
        new_subcategory = subcategory_map_new_db.get(subcat_key)

        if not new_author or not new_subcategory:
            print(f"  [WARNING] Skipping discourse '{old_disc.title}' due to missing author or subcategory.")
            continue

        new_disc = DiscourseBlog(
            user_id=new_author.id, subcategory_id=new_subcategory.id, reference=old_disc.reference,
            title=old_disc.title, body=old_disc.body, date_posted=old_disc.date_posted,
            is_approved=old_disc.is_approved, featured_image=old_disc.featured_image
        )
        # Re-create associated resources
        for old_res in old_disc.resources:
            new_res = Resource(
                type=old_res.type, name=old_res.name, medium=old_res.medium, link=old_res.link
            )
            new_disc.resources.append(new_res)
        mysql_session.add(new_disc)
    mysql_session.commit()
    print("Discourses migrated.")

    # ... you would add similar loops for DiscourseComment, Liturgy, etc. ...

    print("\nMigration completed successfully!")

except Exception as e:
    print(f"\nAn error occurred: {e}")
    mysql_session.rollback()
finally:
    sqlite_session.close()
    mysql_session.close()
    print("Database sessions closed.")