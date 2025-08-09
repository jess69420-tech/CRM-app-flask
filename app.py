import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from functools import wraps
from models import db, User, Client

# Create app and point to instance folder (writable on Render)
app = Flask(__name__, instance_relative_config=True)

# Ensure the instance folder exists
os.makedirs(app.instance_path, exist_ok=True)

# Config
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'data.db')}"
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')

# Ensure uploads folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# ---------- AUTH DECORATOR ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------- ROUTES ----------
@app.route("/")
@login_required
def index():
    clients = Client.query.all()
    return render_template("dashboard.html", clients=clients)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Make sure 'password' exists in your User model!
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user_id"] = user.id
            flash("Logged in successfully!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ---------- ADD CLIENT ----------
@app.route("/add_client", methods=["POST"])
@login_required
def add_client():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    if name and email:
        new_client = Client(name=name, email=email, phone=phone)
        db.session.add(new_client)
        db.session.commit()
        flash("Client added successfully!", "success")
    else:
        flash("Name and email are required.", "danger")
    return redirect(url_for("index"))

# ---------- BULK UPLOAD ----------
@app.route("/upload_clients", methods=["POST"])
@login_required
def upload_clients():
    file = request.files.get("file")
    if not file:
        flash("No file uploaded.", "danger")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    with open(filepath, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            name = row.get("name")
            email = row.get("email")
            phone = row.get("phone")
            if name and email:
                client = Client(name=name, email=email, phone=phone)
                db.session.add(client)
        db.session.commit()

    flash("Clients imported successfully!", "success")
    return redirect(url_for("index"))

# ---------- INIT DB ----------
@app.cli.command("init-db")
def init_db():
    """Initialize the database."""
    db.create_all()
    print("Database initialized.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
