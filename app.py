from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'agent'

# Client model
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20))

# Initialize DB and create default admin
with app.app_context():
    try:
        db.session.execute(db.select(User.password)).first()
    except Exception:
        print("⚠ Recreating database...")
        db.drop_all()
        db.create_all()
        # Default admin
        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Database ready. Default admin: admin / admin123")

# Routes
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("agent_dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin_dashboard")
def admin_dashboard():
    if "role" in session and session["role"] == "admin":
        agents = User.query.filter(User.role == 'agent').all()
        clients = Client.query.all()
        return render_template("admin_dashboard.html", agents=agents, clients=clients)
    return redirect(url_for("login"))

@app.route("/agent_dashboard")
def agent_dashboard():
    if "role" in session and session["role"] == "agent":
        return render_template("agent_dashboard.html")
    return redirect(url_for("login"))

# Add client
@app.route("/add_client", methods=["POST"])
def add_client():
    if "role" in session and session["role"] == "admin":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form.get("phone")
        new_client = Client(name=name, email=email, phone=phone)
        db.session.add(new_client)
        db.session.commit()
    return redirect(url_for("admin_dashboard"))

# Create agent
@app.route("/create_agent", methods=["POST"])
def create_agent():
    if "role" in session and session["role"] == "admin":
        username = request.form["username"]
        password = generate_password_hash("password123")  # default password
        new_agent = User(username=username, password=password, role="agent")
        db.session.add(new_agent)
        db.session.commit()
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
