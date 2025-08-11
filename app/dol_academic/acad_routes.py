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

@academic_bp.route('/theology')
def theology():
    return render_template('acad_theology.html')


@academic_bp.route('/sociology')
def sociology():
    return render_template('acad_sociology.html')


@academic_bp.route('/science')
def science():
    return render_template('acad_science.html')


@academic_bp.route('/library')
def library():
    return render_template('library.html', content="<h1>This is the Academic Library page.</h1>")


@academic_bp.route('/research')
def research():
    return render_template('research.html', content="<h1>This is the Published Papers page.</h1>")


@academic_bp.route('/tools')
def tools():
    return render_template('tools.html', content="<h1>This is the Academic Tools page.</h1>")
