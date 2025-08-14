from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "database.db")
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ======================
# MODELS
# ======================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # this is the missing column
    role = db.Column(db.String(20), nullable=False)

# ======================
# DATABASE RESET CHECK
# ======================
def check_and_reset_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(user)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()

        if "password" not in columns:
            print("⚠ Missing 'password' column in 'user' table. Resetting database...")
            os.remove(DB_PATH)
            return True
    except sqlite3.Error as e:
        print(f"Database error: {e}. Resetting database...")
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        return True
    return False

if check_and_reset_db():
    print("✅ Database was reset and will be recreated now.")

db.create_all()

# ======================
# ROUTES
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["username"] = user.username
            session["role"] = user.role
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return "Welcome, Agent!"
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "role" in session and session["role"] == "admin":
        agents = User.query.filter(User.role == "agent").all()
        return render_template("admin_dashboard.html", agents=agents)
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ======================
# RUN APP
# ======================
if __name__ == "__main__":
    app.run(debug=True)
