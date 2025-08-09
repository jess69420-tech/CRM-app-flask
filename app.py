import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from functools import wraps
from models import db, User, Client

# --- Flask App Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/data.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

# Make sure uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# --- Authentication Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    clients = Client.query.all()
    return render_template('dashboard.html', clients=clients)

@app.route('/add_client', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone', '')
        new_client = Client(name=name, email=email, phone=phone)
        db.session.add(new_client)
        db.session.commit()
        flash('Client added successfully', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_client.html')

@app.route('/upload_clients', methods=['GET', 'POST'])
@login_required
def upload_clients():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.csv'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(filepath)

            added_count = 0
            with open(filepath, newline='', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    normalized_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                    if normalized_row.get('name') and normalized_row.get('email'):
                        client = Client(
                            name=normalized_row['name'],
                            email=normalized_row['email'],
                            phone=normalized_row.get('phone', '')
                        )
                        db.session.add(client)
                        added_count += 1

                db.session.commit()

            flash(f'{added_count} clients uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Please upload a valid CSV file', 'danger')
    return render_template('upload_clients.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
