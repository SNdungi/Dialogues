# /app/dol_academic/acad_routes.py

from flask import Blueprint, render_template

# MODIFICATION: Define the blueprint and specify its template/static folders.
# This tells Flask to look for templates in 'app/dol_academic/templates/'
# and static files in 'app/dol_academic/static/'.
academic_bp = Blueprint(
    'academic', 
    __name__,
    template_folder='templates/academy',
    static_folder='static'
)

# The route remains the same...
@academic_bp.route('/theology')
def academics():
    # MODIFICATION: The template path is now relative to the blueprint's 'templates' folder.
    # We must include the 'academy' sub-directory.
    return render_template('acad_theology.html')

@academic_bp.route('/library')
def library():
    return render_template('academy/acad_base.html', content="<h1>This is the Academic Library page.</h1>")

@academic_bp.route('/research')
def research():
    return render_template('academy/acad_base.html', content="<h1>This is the Published Papers page.</h1>")