from flask import Blueprint, render_template

# Note the different name 'academic' for the blueprint
academic_bp = Blueprint('academic', __name__)

@academic_bp.route('/library')
def library():
    # You would fetch data about library resources here
    return "<h1>This is the Academic Library page.</h1>"

@academic_bp.route('/research')
def research():
    return "<h1>This is the Published Papers page.</h1>"