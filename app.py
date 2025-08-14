from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import io
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SECRET_KEY'] = 'yoursecretkey'
db = SQLAlchemy(app)

# ----------------------------
# MODELS
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='agent')  # admin or agent


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))


# ----------------------------
# ROUTES
# ----------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Simple admin check
        if username == 'jess69420' and password == 'jasser/1998J':
            session['user'] = username
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        # Otherwise, check agent DB
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            session['role'] = user.role
            return redirect(url_for('agent_dashboard'))

        flash('Invalid credentials', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    clients = Client.query.all()
    agents = User.query.filter(User.role == 'agent').all()
    return render_template('admin_dashboard.html', clients=clients, agents=agents)


@app.route('/agent_dashboard')
def agent_dashboard():
    if 'role' not in session or session['role'] != 'agent':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    clients = Client.query.all()
    return render_template('agent_dashboard.html', clients=clients)


@app.route('/add_agent', methods=['GET', 'POST'])
def add_agent():
    if 'role' not in session or session['role'] != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('add_agent'))

        hashed_pw = generate_password_hash(password)
        new_agent = User(username=username, password=hashed_pw, role='agent')
        db.session.add(new_agent)
        db.session.commit()
        flash('Agent created successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('register.html')


@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if 'user' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']

        new_client = Client(name=name, email=email, phone=phone)
        db.session.add(new_client)
        db.session.commit()
        flash('Client added successfully.', 'success')
        return redirect(url_for(f"{session['role']}_dashboard"))

    return render_template('add_client.html')


@app.route('/edit_client/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    if 'user' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    client = Client.query.get_or_404(client_id)

    if request.method == 'POST':
        client.name = request.form['name']
        client.email = request.form['email']
        client.phone = request.form['phone']
        db.session.commit()
        flash('Client updated successfully.', 'success')
        return redirect(url_for(f"{session['role']}_dashboard"))

    return render_template('edit_client.html', client=client)


@app.route('/delete_client/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    if 'user' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    client = Client.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    flash('Client deleted successfully.', 'success')
    return redirect(url_for(f"{session['role']}_dashboard"))


@app.route('/import_clients', methods=['POST'])
def import_clients():
    try:
        if 'file' not in request.files:
            flash('No file part in request.', 'error')
            return redirect(url_for(f"{session['role']}_dashboard"))

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for(f"{session['role']}_dashboard"))

        if not file.filename.lower().endswith('.csv'):
            flash('Only CSV files are allowed.', 'error')
            return redirect(url_for(f"{session['role']}_dashboard"))

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8"))
        except UnicodeDecodeError:
            file.stream.seek(0)
            stream = io.StringIO(file.stream.read().decode("latin-1"))

        reader = csv.DictReader(stream)
        added_count = 0
        for row in reader:
            name = row.get('name')
            email = row.get('email')
            phone = row.get('phone')

            if not name or not email:
                continue

            client = Client(name=name, email=email, phone=phone)
            db.session.add(client)
            added_count += 1

        db.session.commit()
        flash(f'Successfully imported {added_count} clients.', 'success')
        return redirect(url_for(f"{session['role']}_dashboard"))

    except Exception as e:
        db.session.rollback()
        flash(f'Error importing clients: {str(e)}', 'error')
        return redirect(url_for(f"{session['role']}_dashboard"))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
