# /project_folder/app/admin.py

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from .models import db, User, Role, DiscourseBlog, DiscourseComment, Resource, Organisation, Liturgy, Reading



class UserAdminView(ModelView):
    column_list = ('name', 'email', 'is_active', 'is_authorized', 'roles')
    form_excluded_columns = ('password_hash',) # Don't show password hash in forms
    form_columns = ('name', 'other_names', 'email', 'is_active', 'is_authorized', 'roles')

class DiscourseBlogAdminView(ModelView):
    column_list = ('title', 'author', 'date_posted', 'is_approved')
    form_columns = ('title', 'author', 'body', 'is_approved', 'resources')
    # Allows editing resources directly within the discourse form
    inline_models = (Resource,) 

class DiscourseCommentAdminView(ModelView):
    column_list = ('discourse', 'commenter', 'date_commented', 'is_audited')
    form_columns = ('discourse', 'commenter', 'body', 'is_audited', 'ip_address')

class LiturgyAdminView(ModelView):
    column_list = ('name', 'type', 'date', 'theme')
    # Allows adding/editing readings directly within the liturgy form
    inline_models = (Reading,)

def setup_admin(app):
    # Pass a custom index_view to secure the admin panel
    # admin = Admin(app, name='Dialogues Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())
    
    # For this example, we use the default unprotected view
    admin = Admin(app, name='Dialogues Admin', template_mode='bootstrap4')
    
    # Add views
    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(ModelView(Role, db.session))
    admin.add_view(DiscourseBlogAdminView(DiscourseBlog, db.session))
    admin.add_view(DiscourseCommentAdminView(DiscourseComment, db.session))
    admin.add_view(ModelView(Organisation, db.session))
    admin.add_view(LiturgyAdminView(Liturgy, db.session))