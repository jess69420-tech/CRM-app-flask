import os
import csv
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from models import db, User, Client

# --- Flask app setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'

# Database in instance folder
os.makedirs('instance', exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folder
UPLOAD_FOLDER = os.path.join('instance', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)

# --- Login required decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Home route ---
@app.route('/')
def home():
    return redirect(url_for('login'))

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    clients = Client.query.all()
    return render_template('dashboard.html', clients=clients)

# --- Add single client ---
@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    client = Client(name=name, email=email, phone=phone)
    db.session.add(client)
    db.session.commit()
    flash('Client added successfully!', 'success')
    return redirect(url_for('dashboard'))

# --- Upload clients CSV ---
@app.route('/upload_clients', methods=['POST'])
@login_required
def upload_clients():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dashboard'))
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row.get('name') or row.get('Name')
                email = row.get('email') or row.get('Email')
                phone = row.get('phone') or row.get('Phone')
                if name and email:  # avoid empty rows
                    db.session.add(Client(name=name, email=email, phone=phone))
        db.session.commit()
        flash('Clients uploaded successfully!', 'success')
    except Exception as e:
        flash(f'Error reading CSV file: {e}', 'danger')

    return redirect(url_for('dashboard'))

# --- Init DB command ---
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database initialized.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
