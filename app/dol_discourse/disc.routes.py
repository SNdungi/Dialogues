from flask import Blueprint, render_template

# Note the different name 'academic' for the blueprint
dialogue_bp = Blueprint('reserch', __name__)

@dialogue_bp.route('/discourse')
def discourse():
    return "<h1>This is the Published Papers page.</h1>"

@dialogue_bp.route('/dialogues')
def dialogues():
    # You would fetch data about library resources here
    return "<h1>This is the discussion page.</h1>"

@dialogue_bp.route('/blogs')
def Blogs():
    return "<h1>This is the Blogger page.</h1>"

@dialogue_bp.route('/comments')
def comments():
    return "<h1>This is the Resoponces and comments page.</h1>"
 
