import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

# Ensure uploads folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Hardcoded admin credentials
ADMIN_USERNAME = "jess69420"
ADMIN_PASSWORD = "jasser/1998J"

# Dummy client list for testing
clients = []

# Login route
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        session['username'] = username

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            session['role'] = 'agent'
            return redirect(url_for('agent_dashboard'))

    return render_template('login.html')


# Admin dashboard
@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', clients=clients)


# Agent dashboard
@app.route('/agent')
def agent_dashboard():
    if 'role' not in session or session['role'] != 'agent':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))
    return render_template('agent_dashboard.html', clients=clients)


# CSV upload (admin only)
@app.route('/upload', methods=['POST'])
def upload_clients():
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    file = request.files['file']
    if file.filename == '':
        flash("No file selected", "danger")
        return redirect(url_for('admin_dashboard'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filepath)

    # Read CSV and append to clients list
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            clients.append(row)

    flash("Clients uploaded successfully!", "success")
    return redirect(url_for('admin_dashboard'))


# Add client manually (admin only)
@app.route('/add_client', methods=['POST'])
def add_client():
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    name = request.form['name']
    email = request.form['email']
    clients.append({'name': name, 'email': email})
    flash("Client added successfully!", "success")
    return redirect(url_for('admin_dashboard'))


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
