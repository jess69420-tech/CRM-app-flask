from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from io import TextIOWrapper
import csv

# --- Flask setup ---
app = Flask(__name__)
app.secret_key = "your_secret_key"  # change this to a secure random key

# --- Database setup ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///crm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "admin" or "agent"


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(20))


# --- DB INIT ---
with app.app_context():
    db.create_all()
    # ensure default admin exists
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created (admin/admin123)")


# --- ROUTES ---
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
        agents = User.query.filter(User.role == "agent").all()
        clients = Client.query.all()
        return render_template("admin_dashboard.html", agents=agents, clients=clients)
    return redirect(url_for("login"))


@app.route("/agent_dashboard")
def agent_dashboard():
    if "role" in session and session["role"] == "agent":
        return render_template("agent_dashboard.html")
    return redirect(url_for("login"))


@app.route("/add_client", methods=["POST"])
def add_client():
    if "role" in session and session["role"] == "admin":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form.get("phone", "")

        if not Client.query.filter_by(email=email).first():
            new_client = Client(name=name, email=email, phone=phone)
            db.session.add(new_client)
            db.session.commit()

    return redirect(url_for("admin_dashboard"))


@app.route("/import_clients", methods=["POST"])
def import_clients():
    if "role" in session and session["role"] == "admin":
        file = request.files["file"]
        if file and file.filename.endswith(".csv"):
            csv_file = TextIOWrapper(file, encoding="utf-8")
            reader = csv.DictReader(csv_file)
            for row in reader:
                if not Client.query.filter_by(email=row["email"]).first():
                    new_client = Client(
                        name=row["name"], email=row["email"], phone=row.get("phone", "")
                    )
                    db.session.add(new_client)
            db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/create_agent", methods=["POST"])
def create_agent():
    if "role" in session and session["role"] == "admin":
        username = request.form["username"]
        if not User.query.filter_by(username=username).first():
            new_agent = User(
                username=username,
                password=generate_password_hash("agent123"),  # default pw
                role="agent",
            )
            db.session.add(new_agent)
            db.session.commit()
    return redirect(url_for("admin_dashboard"))


# --- RUN APP ---
if __name__ == "__main__":
    app.run(debug=True)
