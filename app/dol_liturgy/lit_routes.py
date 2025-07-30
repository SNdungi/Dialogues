from flask import Blueprint, render_template

# Note the different name 'academic' for the blueprint
liturgy_bp = Blueprint('liturgy', __name__)

@liturgy_bp.route('/prayers')
def Prayer():
    return "<h1>preyers,devotions and chaplets  page.</h1>"

@liturgy_bp.route('/word')
def Word():
    # You would fetch data about library resources here
    return "<h1>This is the word page.</h1>"

@liturgy_bp.route('/commentary')
def Commentary():
    return "<h1>This are commentaries on the word page.</h1>"


 