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

# Check if DB needs to be created
with app.app_context():
    try:
        # Try reading password column
        db.session.execute(db.select(User.password)).first()
    except Exception as e:
        print("⚠ Missing 'password' column. Recreating database...")
        db.drop_all()
        db.create_all()
        # Create default admin
        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Database recreated with default admin (admin/admin123)")

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
        return render_template("admin_dashboard.html", agents=agents)
    return redirect(url_for("login"))

@app.route("/agent_dashboard")
def agent_dashboard():
    if "role" in session and session["role"] == "agent":
        return render_template("agent_dashboard.html")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
