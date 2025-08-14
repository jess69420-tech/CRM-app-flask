import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from models import db, Client  # Keep Client model for CRM features
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

db.init_app(app)

# Make sure uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# --- LOGIN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hardcoded admin login
        if username == "jess69420" and password == "jasser/1998J":
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            session['role'] = 'agent'
            return redirect(url_for('agent_dashboard'))

    return render_template('login.html')


# --- DASHBOARDS ---
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('agent_dashboard'))
    clients = Client.query.all()
    return render_template('admin_dashboard.html', clients=clients)


@app.route('/agent')
def
