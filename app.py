from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data.db')  # store database directly in project folder

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devsecret123')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='agent')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    wallet = db.Column(db.String(200))
    full_name = db.Column(db.String(300))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(100))
    last_contact_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='NEW')
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    assigned_agent = db.relationship('User', backref='clients', foreign_keys=[assigned_agent_id])

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    client = db.relationship('Client', backref='comments', foreign_keys=[client_id])
    author = db.relationship('User', foreign_keys=[author_id])

def init_db_and_admin():
    db.create_all()
    admin_username = 'jess69420'
    admin_password = 'jasser/1998J'
    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(username=admin_username, role='admin')
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print('Admin user created')

@app.before_request
def load_logged_in_user():
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])

def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if g.user is None or g.user.role != 'admin':
            flash('Admin access required', 'warning')
            return redirect(url_for('dashboard'))
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    if g.user:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            flash('Logged in', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if g.user.role == 'admin':
        clients = Client.query.order_by(Client.name).all()
    else:
        clients = Client.query.filter_by(assigned_agent_id=g.user.id).order_by(Client.name).all()
    return render_template('dashboard.html', clients=clients)

@app.route('/client/<int:client_id>')
@login_required
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)
    if g.user.role != 'admin' and client.assigned_agent_id != g.user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    comments = Comment.query.filter_by(client_id=client.id).order_by(Comment.timestamp.desc()).all()
    agents = User.query.filter(User.role=='agent').all() if g.user.role=='admin' else []
    return render_template('client.html', client=client, comments=comments, agents=agents)

@app.route('/call/<int:client_id>', methods=['POST','GET'])
@login_required
def call_client(client_id):
    client = Client.query.get_or_404(client_id)
    if g.user.role != 'admin' and client.assigned_agent_id != g.user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    client.last_contact_date = datetime.utcnow()
    db.session.commit()
    flash('Call logged (last_contact_date updated)', 'success')
    return redirect(url_for('client_detail', client_id=client.id))

@app.route('/client/<int:client_id>/comment', methods=['POST'])
@login_required
def add_comment(client_id):
    client = Client.query.get_or_404(client_id)
    if g.user.role != 'admin' and client.assigned_agent_id != g.user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    text = request.form.get('comment_text','').strip()
    status = request.form.get('status')
    if text:
        comment = Comment(client_id=client.id, author_id=g.user.id, text=text, timestamp=datetime.utcnow())
        db.session.add(comment)
    if status and status in ['NEW','NO ANSWER','NOT INTERESTED','CALL AGAIN','DEPOSIT']:
        client.status = status
    db.session.commit()
    flash('Comment added', 'success')
    return redirect(url_for('client_detail', client_id=client.id))

@app.route('/clients/add', methods=['GET','POST'])
@admin_required
def add_client():
    if request.method == 'POST':
        name = request.form.get('name') or 'Unnamed'
        wallet = request.form.get('wallet') or ''
        full_name = request.form.get('full_name') or ''
        email = request.form.get('email') or ''
        phone = request.form.get('phone') or ''
        assigned_agent_id = request.form.get('assigned_agent') or None
        if assigned_agent_id == 'None' or assigned_agent_id == '':
            assigned_agent_id = None
        client = Client(name=name, wallet=wallet, full_name=full_name, email=email, phone=phone, assigned_agent_id=assigned_agent_id)
        db.session.add(client)
        db.session.commit()
        flash('Client added', 'success')
        return redirect(url_for('dashboard'))
    agents = User.query.filter_by(role='agent').all()
    return render_template('add_client.html', agents=agents)

@app.route('/clients/<int:client_id>/edit', methods=['GET','POST'])
@admin_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
        client.name = request.form.get('name') or client.name
        client.wallet = request.form.get('wallet') or client.wallet
        client.full_name = request.form.get('full_name') or client.full_name
        client.email = request.form.get('email') or client.email
        client.phone = request.form.get('phone') or client.phone
        assigned_agent_id = request.form.get('assigned_agent') or None
        if assigned_agent_id == 'None' or assigned_agent_id == '':
            assigned_agent_id = None
        client.assigned_agent_id = assigned_agent_id
        client.status = request.form.get('status') or client.status
        db.session.commit()
        flash('Client updated', 'success')
        return redirect(url_for('client_detail', client_id=client.id))
    agents = User.query.filter_by(role='agent').all()
    return render_template('edit_client.html', client=client, agents=agents)

if __name__ == '__main__':
    with app.app_context():
        init_db_and_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)
