import os
import csv
from io import TextIOWrapper
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -------------------
# Models
# -------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='agent')  # 'admin' or 'agent'
    clients = db.relationship('Client', backref='assigned_agent', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    wallet = db.Column(db.String(120))
    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    status = db.Column(db.String(50), default='NEW')
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_contact_date = db.Column(db.DateTime)
    comments = db.relationship('Comment', backref='client', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))

# -------------------
# Auth helpers
# -------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if user.role != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------
# Auto-create DB + Admin
# -------------------
@app.before_request
def create_tables():
    if not hasattr(app, 'tables_created'):
        db.create_all()
        app.tables_created = True
    if not User.query.filter_by(username='jess69420').first():
        admin = User(username='jess69420', role='admin')
        admin.set_password('jasser/1998J')
        db.session.add(admin)
        db.session.commit()

# -------------------
# Routes
# -------------------
@app.route('/')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    if user.role == 'admin':
        clients = Client.query.all()
    else:
        clients = Client.query.filter_by(assigned_agent_id=user.id).all()
    return render_template('dashboard.html', user=user, clients=clients)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/clients/add', methods=['GET', 'POST'])
@admin_required
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        wallet = request.form.get('wallet')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        assigned_agent_id = request.form.get('assigned_agent_id') or None

        client = Client(
            name=name,
            wallet=wallet,
            full_name=full_name,
            email=email,
            phone=phone,
            assigned_agent_id=assigned_agent_id
        )
        db.session.add(client)
        db.session.commit()
        flash('Client added', 'success')
        return redirect(url_for('dashboard'))

    agents = User.query.filter_by(role='agent').all()
    return render_template('add_client.html', agents=agents)

# -------------------
# BULK CSV UPLOAD
# -------------------
@app.route('/clients/upload', methods=['GET', 'POST'])
@admin_required
def upload_clients():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file uploaded', 'danger')
            return redirect(url_for('upload_clients'))

        try:
            csv_file = TextIOWrapper(file, encoding='utf-8')
            reader = csv.DictReader(csv_file)
            added_count = 0
            for row in reader:
                name = row.get('name', '').strip()
                wallet = row.get('wallet', '').strip()
                full_name = row.get('full_name', '').strip()
                email = row.get('email', '').strip()
                phone = row.get('phone', '').strip()
                assigned_agent_username = row.get('assigned_agent', '').strip()

                assigned_agent = None
                if assigned_agent_username:
                    assigned_agent = User.query.filter_by(username=assigned_agent_username).first()

                if name:
                    client = Client(
                        name=name,
                        wallet=wallet,
                        full_name=full_name,
                        email=email,
                        phone=phone,
                        assigned_agent_id=assigned_agent.id if assigned_agent else None
                    )
                    db.session.add(client)
                    added_count += 1

            db.session.commit()
            flash(f'{added_count} clients uploaded successfully', 'success')
        except Exception as e:
            flash(f'Error uploading clients: {str(e)}', 'danger')

        return redirect(url_for('dashboard'))

    return render_template('upload_clients.html')

# -------------------
# Call + Comment
# -------------------
@app.route('/clients/<int:client_id>/call', methods=['POST'])
@login_required
def call_client(client_id):
    client = Client.query.get_or_404(client_id)
    client.last_contact_date = datetime.utcnow()
    comment_text = request.form.get('comment')
    if comment_text:
        comment = Comment(content=comment_text, client_id=client.id)
        db.session.add(comment)
    db.session.commit()
    flash('Call logged', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
