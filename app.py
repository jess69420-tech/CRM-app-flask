import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from functools import wraps
from models import db, Client

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

db.init_app(app)

# Create uploads folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "jess69420" and password == "jasser/1998J":
            session['logged_in'] = True
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            session['logged_in'] = True
            session['role'] = 'agent'
            return redirect(url_for('agent_dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('agent_dashboard'))
    clients = Client.query.all()
    return render_template('admin_dashboard.html', clients=clients)

@app.route('/agent/dashboard')
@login_required
def agent_dashboard():
    if session.get('role') != 'agent':
        return redirect(url_for('admin_dashboard'))
    clients = Client.query.all()
    return render_template('agent_dashboard.html', clients=clients)

@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    if session.get('role') != 'admin':
        flash("Only admin can add clients")
        return redirect(url_for('agent_dashboard'))
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    new_client = Client(name=name, email=email, phone=phone)
    db.session.add(new_client)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/upload_clients', methods=['POST'])
@login_required
def upload_clients():
    if session.get('role') != 'admin':
        flash("Only admin can upload clients")
        return redirect(url_for('agent_dashboard'))
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('admin_dashboard'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('admin_dashboard'))
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)
        import csv
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                client = Client(name=row['name'], email=row['email'], phone=row['phone'])
                db.session.add(client)
        db.session.commit()
        flash('Clients uploaded successfully')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
