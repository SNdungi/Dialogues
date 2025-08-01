# /project_folder/app/models.py

import enum
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# --- Enums for controlled vocabulary ---

class RoleType(enum.Enum):
    ADMIN = 'Admin'
    EDITOR = 'Editor'
    WRITER = 'Writer'
    READER = 'Reader'

class OrgType(enum.Enum):
    CHURCH = 'Church'
    GROUP = 'Group'
    CHARITY = 'Charity'
    ORDER = 'Order'
    HOSPITAL = 'Hospital'
    SCHOOL = 'School'
    OTHER = 'Other'

class ResourceType(enum.Enum):
    REPOSITORY = 'Repository'
    JOURNAL = 'Journal'
    ACADEMIC_PAPER = 'Academic Paper'
    BLOG = 'Blog'
    COMMENTARY = 'Commentary'
    TUTORIAL = 'Tutorial'
    LECTURE = 'Lecture'
    VIDEO = 'Video'

class LiturgyType(enum.Enum):
    WORD = 'Word'
    PRAYER = 'Prayer'

# --- Association Table for Many-to-Many User-Role relationship ---

user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

# --- Main Models ---

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Enum(RoleType), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return f'<Role {self.name.value}>'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)        # Will be "First Name"
    other_names = db.Column(db.String(100), nullable=False) # Will be "Last Name"
    organization_name = db.Column(db.String(150))           # New optional field
    website = db.Column(db.String(200))                     # New optional field
    
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_authorized = db.Column(db.Boolean, default=False, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                            backref=db.backref('users', lazy=True))
    
    discourses = db.relationship('DiscourseBlog', back_populates='author', lazy='dynamic')
    comments = db.relationship('DiscourseComment', back_populates='commenter', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(role.name.value == role_name for role in self.roles)

    @staticmethod
    def find_by_email(email):
        return User.query.filter_by(email=email).first()

    def __repr__(self):
        return f'<User {self.name} {self.email}>'

class DiscourseBlog(db.Model):
    __tablename__ = 'discourse_blogs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reference = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)

    author = db.relationship('User', back_populates='discourses')
    resources = db.relationship('Resource', back_populates='discourse', lazy='joined', cascade="all, delete-orphan")
    comments = db.relationship('DiscourseComment', back_populates='discourse', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<DiscourseBlog {self.title}>'

class DiscourseComment(db.Model):
    __tablename__ = 'discourse_comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    discourse_id = db.Column(db.Integer, db.ForeignKey('discourse_blogs.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date_commented = db.Column(db.DateTime, default=datetime.utcnow)
    is_audited = db.Column(db.Boolean, default=False, nullable=False)
    ip_address = db.Column(db.String(45)) # For audit trail

    commenter = db.relationship('User', back_populates='comments')
    discourse = db.relationship('DiscourseBlog', back_populates='comments')

    def __repr__(self):
        return f'<Comment {self.id} on Discourse {self.discourse_id}>'

class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    discourse_id = db.Column(db.Integer, db.ForeignKey('discourse_blogs.id'), nullable=False)
    type = db.Column(db.Enum(ResourceType), nullable=False)
    name = db.Column(db.String(200), nullable=False) # e.g., "Psalm 19:1" or "On the Incarnation"
    medium = db.Column(db.String(100)) # e.g., "Book", "Journal Article"
    link = db.Column(db.String(512)) # URL or reference text

    discourse = db.relationship('DiscourseBlog', back_populates='resources')

    def __repr__(self):
        return f'<Resource {self.name}>'

class Organisation(db.Model):
    __tablename__ = 'organisations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    type = db.Column(db.Enum(OrgType), nullable=False)
    contact = db.Column(db.String(150))
    email = db.Column(db.String(120), unique=True)
    country = db.Column(db.String(100))
    location = db.Column(db.String(200))
    description = db.Column(db.Text)

    def __repr__(self):
        return f'<Organisation {self.name}>'

class Liturgy(db.Model):
    __tablename__ = 'liturgies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.Enum(LiturgyType), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    source = db.Column(db.String(200))
    author = db.Column(db.String(200))
    theme = db.Column(db.String(500))
    
    # For PRAYER type, the body can be stored here
    body = db.Column(db.Text) 
    
    # For WORD type, we use a one-to-many relationship to readings
    readings = db.relationship('Reading', back_populates='liturgy', lazy='joined', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Liturgy {self.name} on {self.date}>'

class Reading(db.Model):
    __tablename__ = 'readings'
    id = db.Column(db.Integer, primary_key=True)
    liturgy_id = db.Column(db.Integer, db.ForeignKey('liturgies.id'), nullable=False)
    reading_number = db.Column(db.Integer, nullable=False) # 1 for 1st reading, 2 for 2nd etc.
    reference = db.Column(db.String(100)) # e.g., "Genesis 1:1-5"
    body = db.Column(db.Text, nullable=False)

    liturgy = db.relationship('Liturgy', back_populates='readings')

    def __repr__(self):
        return f'<Reading {self.reading_number} for Liturgy {self.liturgy_id}>'