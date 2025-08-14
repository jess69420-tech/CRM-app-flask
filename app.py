import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from functools import wraps
from models import db, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db.init_app(app)

# -----------------------
# LOGIN DECORATOR
# -----------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------
# LOGIN PAGE
# -----------------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Hardcoded admin credentials
        if username == 'jess69420' and password == 'jasser/1998J':
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            # All other logins are agents
            session['role'] = 'agent'
            return redirect(url_for('agent_dashboard'))

    return render_template('login.html')

# -----------------------
# ADMIN DASHBOARD
# -----------------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('agent_dashboard'))
    clients = Client.query.all()
    return render_template('admin_dashboard.html', clients=clients)

# -----------------------
# AGENT DASHBOARD
# -----------------------
@app.route('/agent')
@login_required
def agent_dashboard():
    clients = Client.query.all()
    return render_template('agent_dashboard.html', clients=clients)

# -----------------------
# ADD CLIENT (Admin only)
# -----------------------
@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    if session.get('role') != 'admin':
        flash("Only admins can add clients.", "danger")
        return redirect(url_for('agent_dashboard'))

    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')

    if name and email:
        client = Client(name=name, email=email, phone=phone)
        db.session.add(client)
        db.session.commit()
        flash("Client added successfully.", "success")
    else:
        flash("Name and Email are required.", "danger")

    return redirect(url_for('admin_dashboard'))

# -----------------------
# IMPORT CLIENTS (CSV)
# -----------------------
@app.route('/import_clients', methods=['POST'])
@login_required
def import_clients():
    if session.get('role') != 'admin':
        flash("Only admins can import clients.", "danger")
        return redirect(url_for('agent_dashboard'))

    file = request.files['file']
    if not file:
        flash("No file selected.", "danger")
        return redirect(url_for('admin_dashboard'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            client = Client(name=row.get('name'), email=row.get('email'), phone=row.get('phone'))
            db.session.add(client)
        db.session.commit()

    flash("Clients imported successfully.", "success")
    return redirect(url_for('admin_dashboard'))

# -----------------------
# LOGOUT
# -----------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -----------------------
# INITIALIZE DB
# -----------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
