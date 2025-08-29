from app.dol_db.models import db, DiscourseBlog, User, Category, SubCategory
from sqlalchemy import or_, case

def search_discourses(search_query, limit=7):
    """
    Performs a weighted search across DiscourseBlogs and related models.

    Args:
        search_query (str): The user's search term.
        limit (int): The maximum number of results to return.

    Returns:
        list: A list of DiscourseBlog objects matching the query,
              ordered by relevance.
    """
    if not search_query or len(search_query) < 2:
        return []

    search_term = f"%{search_query}%"

    # Define the weighting using a SQL CASE statement.
    # Lower numbers have higher priority.
    relevance = case(
        (DiscourseBlog.title.ilike(search_term), 1),
        (User.name.ilike(search_term), 2),
        (User.other_names.ilike(search_term), 2),
        (DiscourseBlog.body.ilike(search_term), 3),
        (SubCategory.name.ilike(search_term), 4),
        (Category.name.ilike(search_term), 4),
        else_=5
    ).label("relevance")

    # Build the query
    query = (
        db.session.query(DiscourseBlog)
        .join(User, DiscourseBlog.user_id == User.id)
        .join(SubCategory, DiscourseBlog.subcategory_id == SubCategory.id)
        .join(Category, SubCategory.category_id == Category.id)
        .add_columns(relevance) # Add our relevance score as a column
        .filter(
            DiscourseBlog.is_approved == True, # Only search approved posts
            or_(
                DiscourseBlog.title.ilike(search_term),
                DiscourseBlog.body.ilike(search_term),
                User.name.ilike(search_term),
                User.other_names.ilike(search_term),
                SubCategory.name.ilike(search_term),
                Category.name.ilike(search_term)
            )
        )
        .order_by(relevance, DiscourseBlog.date_posted.desc()) # Order by relevance, then by date
        .limit(limit)
    )

    # The result of the query will be tuples of (DiscourseBlog, relevance_score).
    # We only need the DiscourseBlog object.
    results = [result[0] for result in query.all()]
    
    return results

def search_by_author(author_id):
    """
    A specific function to find all discourses by a single author.

    Args:
        author_id (int): The ID of the user.

    Returns:
        list: A list of DiscourseBlog objects by that author.
    """
    if not author_id:
        return []
    
    # This is a simple, direct query.
    results = (
        DiscourseBlog.query
        .filter_by(user_id=author_id, is_approved=True)
        .order_by(DiscourseBlog.date_posted.desc())
        .all()
    )
    
    return results