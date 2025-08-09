import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from functools import wraps
from models import db, User, Client

app = Flask(__name__)

# Ensure instance folder exists (writable in Render)
os.makedirs(app.instance_path, exist_ok=True)

app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'data.db')
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# -------------------------
# Authentication decorator
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------
# Routes
# -------------------------
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    clients = Client.query.all()
    return render_template('dashboard.html', clients=clients)

@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    client = Client(name=name, email=email, phone=phone)
    db.session.add(client)
    db.session.commit()
    flash('Client added successfully')
    return redirect(url_for('dashboard'))

@app.route('/upload_clients', methods=['POST'])
@login_required
def upload_clients():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('dashboard'))

    if file and file.filename.endswith('.csv'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)

        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('name') and row.get('email'):
                    client = Client(
                        name=row['name'].strip(),
                        email=row['email'].strip(),
                        phone=row.get('phone', '').strip()
                    )
                    db.session.add(client)

        db.session.commit()
        flash('Clients uploaded successfully')
    else:
        flash('Invalid file format. Please upload a CSV file.')

    return redirect(url_for('dashboard'))

# -------------------------
# CLI to init DB
# -------------------------
@app.cli.command('init-db')
def init_db():
    db.create_all()
    print('Database initialized.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
