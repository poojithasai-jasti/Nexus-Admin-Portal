import uuid
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
CORS(app) # Enables the Nexus Bridge connection

app.config['SECRET_KEY'] = 'nexus_protocol_secure_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexus_admin.db'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# --- DATABASE MODELS ---
class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    opportunities = db.relationship('Opportunity', backref='creator', lazy=True)

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

# --- AUTHENTICATION ---
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    if Admin.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Account already exists"}), 400
    hashed_pw = generate_password_hash(data['password'])
    new_admin = Admin(fullname=data['full_name'], email=data['email'], password=hashed_pw)
    db.session.add(new_admin)
    db.session.commit()
    return jsonify({"message": "Success"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    admin = Admin.query.filter_by(email=data['email']).first()
    if not admin or not check_password_hash(admin.password, data['password']):
        return jsonify({"error": "Invalid email or password"}), 401
    login_user(admin, remember=data.get('remember_me', False))
    return jsonify({"message": "Logged in"}), 200

# --- OPPORTUNITY MANAGEMENT ---
@app.route('/api/opportunities', methods=['GET'])
@login_required
def get_opps():
    opps = Opportunity.query.filter_by(admin_id=current_user.id).all()
    return jsonify([{
        "id": o.id, "name": o.name, "category": o.category,
        "duration": o.duration, "start_date": o.start_date,
        "description": o.description
    } for o in opps])

@app.route('/api/opportunities/add', methods=['POST'])
@login_required
def add_opp():
    data = request.json
    new_opp = Opportunity(
        name=data['name'], duration=data['duration'], 
        start_date=data['start_date'], description=data['description'],
        skills=data['skills'], category=data['category'],
        admin_id=current_user.id
    )
    db.session.add(new_opp)
    db.session.commit()
    return jsonify({"message": "Opportunity added successfully"}), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8080)
