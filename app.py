import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.utils import secure_filename
from models import db, User, Client
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

db.init_app(app)

# -------------------------
# LOGIN CHECK DECORATOR
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_id') is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------
# SET g.user BEFORE EACH REQUEST
# -------------------------
@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id:
        g.user = User.query.get(user_id)
    else:
        g.user = None

# -------------------------
# LOGIN ROUTE (BASIC)
# -------------------------
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

# -------------------------
# LOGOUT
# -------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------------
# DASHBOARD
# -------------------------
@app.route('/')
@login_required
def dashboard():
    clients = Client.query.all()
    return render_template('dashboard.html', clients=clients)

# -------------------------
# ADD SINGLE CLIENT
# -------------------------
@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    if name and email:
        client = Client(name=name, email=email, phone=phone)
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully!', 'success')
    else:
        flash('Name and Email are required.', 'danger')
    return redirect(url_for('dashboard'))

# -------------------------
# BULK UPLOAD CLIENTS FROM CSV
# -------------------------
@app.route('/upload_clients', methods=['POST'])
@login_required
def upload_clients():
    if 'file' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    file.save(filepath)

    try:
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('name') and row.get('email'):
                    client = Client(
                        name=row['name'],
                        email=row['email'],
                        phone=row.get('phone', '')
                    )
                    db.session.add(client)
            db.session.commit()
        flash('Clients uploaded successfully!', 'success')
    except Exception as e:
        flash(f'Error processing file: {e}', 'danger')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
