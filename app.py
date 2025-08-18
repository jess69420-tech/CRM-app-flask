from flask import Flask, render_template, request, redirect, url_for, session, g
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from io import TextIOWrapper
from datetime import datetime
import csv

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///crm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="agent")

    comments = db.relationship("Comment", backref="author", lazy=True)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    wallet = db.Column(db.String(200))
    full_name = db.Column(db.String(300))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(100))
    last_contact_date = db.Column(db.DateTime)
    status = db.Column(db.String(50), default="NEW")
    assigned_agent_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    comments = db.relationship("Comment", backref="client", lazy=True)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)


# --- DB INIT ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created (admin/admin123)")


# --- CONTEXT LOADING ---
@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = User.query.get(user_id) if user_id else None


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
        if user and user.verify_password(password):
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("admin_dashboard" if user.role == "admin" else "agent_dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin_dashboard")
def admin_dashboard():
    if g.user and g.user.role == "admin":
        agents = User.query.filter(User.role == "agent").all()
        clients = Client.query.all()
        return render_template("admin_dashboard.html", agents=agents, clients=clients)
    return redirect(url_for("login"))


@app.route("/agent_dashboard")
def agent_dashboard():
    if g.user and g.user.role == "agent":
        return render_template("agent_dashboard.html")
    return redirect(url_for("login"))


@app.route("/add_client", methods=["POST"])
def add_client():
    if g.user and g.user.role == "admin":
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
    if g.user and g.user.role == "admin":
        file = request.files["file"]
        if file and file.filename.endswith(".csv"):
            csv_file = TextIOWrapper(file, encoding="utf-8")
            reader = csv.DictReader(csv_file)

            required_fields = {"Name", "Email", "Phone"}
            if not required_fields.issubset(reader.fieldnames or []):
                return "CSV must have at least 'Name', 'Email' and 'Phone' columns", 400

            for row in reader:
                name = row.get("Name")
                email = row.get("Email")
                phone = row.get("Phone", "")

                if email and not Client.query.filter_by(email=email).first():
                    new_client = Client(name=name, email=email, phone=phone)
                    db.session.add(new_client)
            db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/create_agent", methods=["POST"])
def create_agent():
    if g.user and g.user.role == "admin":
        username = request.form["username"]
        if not User.query.filter_by(username=username).first():
            new_agent = User(
                username=username,
                password_hash=generate_password_hash("agent123"),
                role="agent",
            )
            db.session.add(new_agent)
            db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/client/<int:client_id>")
def client_profile(client_id):
    if not g.user:
        return redirect(url_for("login"))

    client = Client.query.get_or_404(client_id)
    comments = Comment.query.filter_by(client_id=client.id).order_by(Comment.timestamp.desc()).all()
    return render_template("client.html", client=client, comments=comments)


@app.route("/client/<int:client_id>/comment", methods=["POST"])
def add_comment(client_id):
    if not g.user:
        return redirect(url_for("login"))

    comment_text = request.form.get("comment_text", "").strip()
    status = request.form.get("status", "").strip().upper()
    client = Client.query.get_or_404(client_id)

    if comment_text:
        comment = Comment(
            client_id=client.id,
            author_id=g.user.id,
            text=comment_text,
            timestamp=datetime.now()
        )
        db.session.add(comment)

    if status:
        client.status = status
        client.last_contact_date = datetime.now()

    db.session.commit()
    return redirect(url_for("client_profile", client_id=client.id))


if __name__ == "__main__":
    app.run(debug=True)
