import os
from datetime import datetime, timedelta
import uuid
from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SECRET_KEY'] = 'nexus_secure_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'nexus_admin.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)

# --- MODELS ---
class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    opportunities = db.relationship('Opportunity', backref='creator', lazy=True)

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.String(500))
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))

# --- AUTHENTICATION ROUTES ---
@app.route('/')
def home():
    return send_from_directory(basedir, 'index.html')

@app.route('/dashboard')
@login_required
def dashboard_view():
    return send_from_directory(basedir, 'dashboard.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    if len(data['password']) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if Admin.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 400
    
    new_admin = Admin(
        fullname=data['full_name'], 
        email=data['email'], 
        password=generate_password_hash(data['password'])
    )
    db.session.add(new_admin)
    db.session.commit()
    return jsonify({"message": "Profile Synchronized"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    admin = Admin.query.filter_by(email=data['email']).first()
    if admin and check_password_hash(admin.password, data['password']):
        login_user(admin, remember=data.get('remember', False))
        return jsonify({"redirect": "/dashboard"}), 200
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

# --- RESET PASSWORD LOGIC (US-1.3) ---
@app.route('/api/request-reset', methods=['POST'])
def request_reset():
    data = request.json
    admin = Admin.query.filter_by(email=data['email']).first()
    token = str(uuid.uuid4())
    if admin:
        admin.reset_token = token
        admin.token_expiry = datetime.utcnow() + timedelta(hours=1) # 1 Hour Expiry
        db.session.commit()
    return jsonify({"message": "Reset process initiated", "debug_link": f"/reset-password/{token}"}), 200

@app.route('/reset-password/<token>')
def validate_reset(token):
    admin = Admin.query.filter_by(reset_token=token).first()
    if not admin or (admin.token_expiry and datetime.utcnow() > admin.token_expiry):
        return "<h1>Error: Reset Link Expired or Invalid</h1><p>Please request a new link.</p>", 400
    return f"<h1>Reset Valid</h1><p>Reset authorized for {admin.email}. Proceed to change password.</p>"

# --- OPPORTUNITY CRUD ROUTES (US-2.1 to US-2.6) ---
@app.route('/api/opportunities', methods=['GET', 'POST'])
@login_required
def manage_opps():
    if request.method == 'POST':
        data = request.json
        new_opp = Opportunity(
            name=data['name'], category=data['category'], duration=data['duration'],
            start_date=data['start_date'], description=data['description'],
            skills=data.get('skills'), admin_id=current_user.id
        )
        db.session.add(new_opp)
        db.session.commit()
        return jsonify({"message": "Created"}), 201
    
    opps = Opportunity.query.filter_by(admin_id=current_user.id).all()
    return jsonify([{
        "id": o.id, "name": o.name, "category": o.category, "duration": o.duration,
        "start_date": o.start_date, "description": o.description, "skills": o.skills
    } for o in opps])

@app.route('/api/opportunities/<int:id>', methods=['DELETE', 'PUT'])
@login_required
def handle_opp(id):
    opp = Opportunity.query.get_or_404(id)
    if opp.admin_id != current_user.id: return jsonify({"error": "Unauthorized"}), 403
    
    if request.method == 'DELETE':
        db.session.delete(opp)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200
    
    if request.method == 'PUT':
        data = request.json
        opp.name = data.get('name', opp.name)
        opp.category = data.get('category', opp.category)
        opp.duration = data.get('duration', opp.duration)
        opp.description = data.get('description', opp.description)
        db.session.commit()
        return jsonify({"message": "Updated"}), 200

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True, port=8080)
