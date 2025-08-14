from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Client

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db.init_app(app)

@app.before_first_request
def create_tables():
    db.create_all()
    # Ensure admin exists
    if not User.query.filter_by(username='jess69420').first():
        admin = User(username='jess69420', password='jasser/1998J', role='admin')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['role'] = user.role
            session['username'] = user.username
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('agent_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    agents = User.query.filter_by(role='agent').all()
    return render_template('admin_dashboard.html', agents=agents)

@app.route('/agent')
def agent_dashboard():
    if session.get('role') != 'agent':
        return redirect(url_for('login'))
    clients = Client.query.all()
    return render_template('agent_dashboard.html', clients=clients)

@app.route('/admin/create-agent', methods=['GET', 'POST'])
def create_agent():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Agent already exists', 'danger')
        else:
            new_agent = User(username=username, password=password, role='agent')
            db.session.add(new_agent)
            db.session.commit()
            flash('Agent created successfully', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('create_agent.html')
