# /project_folder/app/dbops.py

from .models import db, User, Role, DiscourseBlog, DiscourseComment, Resource, RoleType
from sqlalchemy.orm import joinedload
from datetime import datetime

# --- User & Role Operations ---

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()


def create_user(name, other_names, email, username, password, organization_name=None, website=None):
    """Creates a new user and adds them to the database."""
    if User.query.filter_by(email=email).first():
        raise ValueError("An account with this email already exists.")
    if User.query.filter_by(username=username).first():
        raise ValueError("This username is already taken.")
    
    new_user = User(
        name=name,
        other_names=other_names,
        email=email,
        username=username,
        organization_name=organization_name,
        website=website,
        is_active=True,      # New users are active by default
        is_authorized=False  # But not authorized to post until approved by an admin
    )
    new_user.set_password(password)
    
    # Assign 'Reader' role by default
    reader_role = Role.query.filter_by(name=RoleType.READER).first()
    if reader_role:
        new_user.roles.append(reader_role)
    
    db.session.add(new_user)
    db.session.commit()
    return new_user

def get_approved_discourses(page=1, per_page=10):
    """
    Gets paginated, approved discourses.
    Uses joinedload to prevent N+1 queries for author and resources.
    """
    return DiscourseBlog.query\
        .options(joinedload(DiscourseBlog.author), joinedload(DiscourseBlog.resources))\
        .filter_by(is_approved=True)\
        .order_by(DiscourseBlog.date_posted.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

def get_discourse_with_comments(discourse_id):
    """
    Gets a single discourse and eagerly loads its author, resources, and comments with their authors.
    """
    return DiscourseBlog.query\
        .options(
            joinedload(DiscourseBlog.author),
            joinedload(DiscourseBlog.resources),
            joinedload(DiscourseBlog.comments).joinedload(DiscourseComment.commenter)
        )\
        .filter_by(id=discourse_id, is_approved=True)\
        .first_or_404()


def add_discourse(user_id, title, body_html, resources_data=[]):
    """
    Adds a new discourse, which starts as unapproved.
    `resources_data` should be a list of dicts: [{'type': ResourceType, 'name': '...', 'link': '...'}]
    """
    new_discourse = DiscourseBlog(
        user_id=user_id,
        title=title,
        body=body_html,
        reference=f"DISC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    
    for res_data in resources_data:
        resource = Resource(**res_data)
        new_discourse.resources.append(resource)
        
    db.session.add(new_discourse)
    db.session.commit()
    return new_discourse

def add_comment_to_discourse(user_id, discourse_id, comment_body, ip_address=None):
    """
    Adds a new comment, which starts as unaudited.
    """
    # Ensure the discourse exists and is approved before allowing comments
    discourse = DiscourseBlog.query.filter_by(id=discourse_id, is_approved=True).first()
    if not discourse:
        raise ValueError("Discourse not found or not open for comments.")

    new_comment = DiscourseComment(
        user_id=user_id,
        discourse_id=discourse_id,
        body=comment_body,
        ip_address=ip_address
    )
    db.session.add(new_comment)
    db.session.commit()
    return new_comment

# --- Helper for initial setup ---

def seed_roles():
    """A function to populate the Roles table with initial data."""
    if Role.query.count() > 0:
        print("Roles already seeded.")
        return
        
    roles_to_add = [
        Role(name=RoleType.ADMIN, description='Full access to the system.'),
        Role(name=RoleType.EDITOR, description='Can create, edit, and delete content.'),
        Role(name=RoleType.WRITER, description='Can create content for approval.'),
        Role(name=RoleType.READER, description='Can only read approved content.')
    ]
    db.session.bulk_save_objects(roles_to_add)
    db.session.commit()
    print("Roles seeded successfully.")