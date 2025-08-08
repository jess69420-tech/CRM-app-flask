# Flask CRM - Full Project (multi-file)

This canvas contains a complete, ready-to-run Flask CRM project split into files and folders. Copy these files into a Git repo and push to GitHub. Then connect the repo to Render (or run locally).

---

## Project structure

```
flask-crm/
├─ app.py
├─ requirements.txt
├─ Procfile
├─ render.yaml
├─ .env.example
├─ README.md
├─ templates/
│  ├─ layout.html
│  ├─ index.html
│  ├─ edit.html
│  ├─ login.html
│  └─ register.html
├─ static/
│  └─ style.css
└─ instance/
   └─ (data.db will be created at runtime)
```

---

## app.py

```python
from flask import Flask, request, redirect, url_for, render_template, send_file, flash, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import csv
import io
import os
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DB_PATH = os.path.join(INSTANCE_DIR, 'data.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['DATABASE'] = DB_PATH

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------- DB helpers ----------
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    # users table for simple auth
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    # contacts table
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            wallet TEXT,
            fullname TEXT,
            email TEXT,
            phone TEXT,
            tags TEXT,
            notes TEXT,
            owner_id INTEGER,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------- User class for Flask-Login ----------
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username FROM users WHERE id=?', (user_id,))
    r = c.fetchone()
    conn.close()
    if r:
        return User(r['id'], r['username'])
    return None

# ---------- Utilities ----------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# simple sanitizer for phone
def clean_phone(phone):
    if not phone:
        return ''
    return ''.join(ch for ch in phone if ch.isdigit() or ch == '+')

# ---------- Routes ----------
@app.route('/')
@login_required
def index():
    q = request.args.get('q','').strip()
    conn = get_db()
    c = conn.cursor()
    if q:
        like = f"%{q}%"
        c.execute('''SELECT * FROM contacts WHERE owner_id=? AND (name LIKE ? OR wallet LIKE ? OR fullname LIKE ? OR email LIKE ? OR phone LIKE ? OR tags LIKE ?) ORDER BY id''',
                  (current_user.id, like, like, like, like, like, like))
    else:
        c.execute('SELECT * FROM contacts WHERE owner_id=? ORDER BY id', (current_user.id,))
    rows = c.fetchall()
    conn.close()
    return render_template('index.html', rows=rows)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        with open(path, newline='', encoding='utf-8', errors='replace') as csvfile:
            reader = csv.reader(csvfile)
            conn = get_db()
            c = conn.cursor()
            for i,row in enumerate(reader):
                if not row or all(not cell.strip() for cell in row):
                    continue
                # Skip header heuristics
                if i == 0:
                    head = [cell.strip().lower() for cell in row]
                    if any('name' in h for h in head) and any('wallet' in h for h in head):
                        continue
                while len(row) < 5:
                    row.append('')
                name = row[0].strip() or 'N/A'
                wallet = row[1].strip() or 'N/A'
                fullname = row[2].strip() or 'N/A'
                email = row[3].strip() or 'N/A'
                phone = row[4].strip() or 'N/A'
                tags = row[5].strip() if len(row) > 5 else ''
                notes = row[6].strip() if len(row) > 6 else ''
                c.execute('INSERT INTO contacts (name,wallet,fullname,email,phone,tags,notes,owner_id) VALUES (?,?,?,?,?,?,?,?)',
                          (name,wallet,fullname,email,phone,tags,notes,current_user.id))
            conn.commit()
            conn.close()
        flash('CSV uploaded (N/A used for empty fields)')
        return redirect(url_for('index'))
    else:
        flash('Invalid file type (use .csv)')
        return redirect(url_for('index'))

@app.route('/export')
@login_required
def export_csv():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT name,wallet,fullname,email,phone,tags,notes FROM contacts WHERE owner_id=? ORDER BY id', (current_user.id,))
    rows = c.fetchall()
    conn.close()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Name','Wallet Address','Full Name','Email','Phone Number','Tags','Notes'])
    for r in rows:
        writer.writerow([r['name'], r['wallet'], r['fullname'], r['email'], r['phone'], r['tags'], r['notes']])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='contacts_export.csv', mimetype='text/csv')

@app.route('/edit/<int:cid>', methods=['GET','POST'])
@login_required
def edit(cid):
    conn = get_db()
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form.get('name','N/A').strip() or 'N/A'
        wallet = request.form.get('wallet','N/A').strip() or 'N/A'
        fullname = request.form.get('fullname','N/A').strip() or 'N/A'
        email = request.form.get('email','N/A').strip() or 'N/A'
        phone = request.form.get('phone','N/A').strip() or 'N/A'
        tags = request.form.get('tags','').strip()
        notes = request.form.get('notes','').strip()
        c.execute('UPDATE contacts SET name=?,wallet=?,fullname=?,email=?,phone=?,tags=?,notes=? WHERE id=? AND owner_id=?',
                  (name,wallet,fullname,email,phone,tags,notes,cid,current_user.id))
        conn.commit()
        conn.close()
        flash('Contact updated')
        return redirect(url_for('index'))
    c.execute('SELECT * FROM contacts WHERE id=? AND owner_id=?', (cid,current_user.id))
    r = c.fetchone()
    conn.close()
    if not r:
        flash('Contact not found')
        return redirect(url_for('index'))
    return render_template('edit.html', r=r)

@app.route('/delete/<int:cid>')
@login_required
def delete(cid):
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM contacts WHERE id=? AND owner_id=?', (cid,current_user.id))
    conn.commit()
    conn.close()
    flash('Contact deleted')
    return redirect(url_for('index'))

@app.route('/clear')
@login_required
def clear_all():
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM contacts WHERE owner_id=?', (current_user.id,))
    conn.commit()
    conn.close()
    flash('All contacts deleted')
    return redirect(url_for('index'))

# ---------- Authentication (register/login) ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        if not username or not password:
            flash('Username and password required')
            return redirect(url_for('register'))
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username,password) VALUES (?,?)', (username,pw_hash))
            conn.commit()
            conn.close()
            flash('Registration successful, please log in')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already taken')
            conn.close()
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id,username,password FROM users WHERE username=?', (username,))
        r = c.fetchone()
        conn.close()
        if r and bcrypt.check_password_hash(r['password'], password):
            user = User(r['id'], r['username'])
            login_user(user)
            flash('Logged in')
            return redirect(url_for('index'))
        flash('Invalid credentials')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out')
    return redirect(url_for('login'))

@app.route('/ping')
def ping():
    return 'pong'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
```

---

## templates/layout.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CRM</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  </head>
  <body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
      <div class="container-fluid">
        <a class="navbar-brand" href="{{ url_for('index') }}">Simple CRM</a>
        <div class="collapse navbar-collapse">
          <ul class="navbar-nav ms-auto">
            {% if current_user.is_authenticated %}
            <li class="nav-item"><a class="nav-link" href="#">{{ current_user.username }}</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
            {% else %}
            <li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Login</a></li>
            <li class="nav-item"><a class="nav-link" href="{{ url_for('register') }}">Register</a></li>
            {% endif %}
          </ul>
        </div>
      </div>
    </nav>
    <div class="container py-4">
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="alert alert-info">{{ messages[0] }}</div>
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </div>
  </body>
</html>
```

---

## templates/index.html

```html
{% extends 'layout.html' %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h1>Contacts</h1>
  <div>
    <a class="btn btn-secondary" href="{{ url_for('export_csv') }}">Export</a>
    <a class="btn btn-outline-danger" href="{{ url_for('clear_all') }}" onclick="return confirm('Delete all your contacts?')">Delete All</a>
  </div>
</div>

<div class="card mb-3">
  <div class="card-body">
    <form action="{{ url_for('upload') }}" method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <input class="form-control" type="file" name="file" accept=".csv" required>
      </div>
      <button class="btn btn-primary" type="submit">Upload CSV</button>
    </form>
  </div>
</div>

<form class="mb-3" method="get">
  <div class="input-group">
    <input type="search" name="q" class="form-control" placeholder="Search..." value="{{ request.args.get('q','') }}">
    <button class="btn btn-outline-primary" type="submit">Search</button>
  </div>
</form>

<div class="table-responsive">
  <table class="table table-sm table-striped">
    <thead>
      <tr>
        <th>#</th>
        <th>Name</th>
        <th>Wallet</th>
        <th>Full Name</th>
        <th>Email</th>
        <th>Phone</th>
        <th>Tags</th>
        <th>Notes</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for r in rows %}
      <tr>
        <td>{{ loop.index }}</td>
        <td>{{ r['name'] }}</td>
        <td style="max-width:200px;overflow:auto;">{{ r['wallet'] }}</td>
        <td>{{ r['fullname'] }}</td>
        <td>{{ r['email'] }}</td>
        <td>{{ r['phone'] }}</td>
        <td>{{ r['tags'] }}</td>
        <td>{{ r['notes'] }}</td>
        <td>
          <a class="btn btn-sm btn-outline-primary" href="{{ url_for('edit', cid=r['id']) }}">Edit</a>
          <a class="btn btn-sm btn-outline-danger" href="{{ url_for('delete', cid=r['id']) }}" onclick="return confirm('Delete this contact?')">Delete</a>
          {% if r['phone'] and r['phone']!='N/A' %}
          <a class="btn btn-sm btn-success" href="sip:{{ r['phone'] }}@microsiptwilio.sip.twilio.com">Call</a>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% endblock %}
```

---

## templates/edit.html

```html
{% extends 'layout.html' %}
{% block content %}
<h1>Edit Contact</h1>
<form method="post">
  <div class="mb-3">
    <label class="form-label">Name</label>
    <input class="form-control" name="name" value="{{ r['name'] }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Wallet</label>
    <input class="form-control" name="wallet" value="{{ r['wallet'] }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Full Name</label>
    <input class="form-control" name="fullname" value="{{ r['fullname'] }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Email</label>
    <input class="form-control" name="email" value="{{ r['email'] }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Phone</label>
    <input class="form-control" name="phone" value="{{ r['phone'] }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Tags (comma separated)</label>
    <input class="form-control" name="tags" value="{{ r['tags'] }}">
  </div>
  <div class="mb-3">
    <label class="form-label">Notes</label>
    <textarea class="form-control" name="notes">{{ r['notes'] }}</textarea>
  </div>
  <button class="btn btn-primary" type="submit">Save</button>
  <a class="btn btn-secondary" href="{{ url_for('index') }}">Back</a>
</form>
{% endblock %}
```

---

## templates/login.html & register.html

```html
<!-- login.html -->
{% extends 'layout.html' %}
{% block content %}
<h1>Login</h1>
<form method="post">
  <div class="mb-3">
    <label class="form-label">Username</label>
    <input class="form-control" name="username">
  </div>
  <div class="mb-3">
    <label class="form-label">Password</label>
    <input class="form-control" name="password" type="password">
  </div>
  <button class="btn btn-primary" type="submit">Login</button>
  <a class="btn btn-link" href="{{ url_for('register') }}">Register</a>
</form>
{% endblock %}

<!-- register.html -->
{% extends 'layout.html' %}
{% block content %}
<h1>Register</h1>
<form method="post">
  <div class="mb-3">
    <label class="form-label">Username</label>
    <input class="form-control" name="username">
  </div>
  <div class="mb-3">
    <label class="form-label">Password</label>
    <input class="form-control" name="password" type="password">
  </div>
  <button class="btn btn-primary" type="submit">Register</button>
  <a class="btn btn-link" href="{{ url_for('login') }}">Login</a>
</form>
{% endblock %}
```

---

## static/style.css

```css
body { padding-bottom: 40px; }
.table td, .table th { vertical-align: middle; }
```

---

## requirements.txt

```
Flask>=2.2
Flask-Login>=0.6
Flask-Bcrypt>=1.0
gunicorn
```

---

## Procfile

```
web: gunicorn app:app
```

---

## render.yaml (optional)

```yaml
services:
  - type: web
    name: simple-crm
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: SECRET_KEY
        value: "changeme"
```

---

## .env.example

```
SECRET_KEY=your-secret-key
```

---

## README.md (quick start)

```
# Simple Flask CRM

1. Copy files into a repo.
2. Create virtualenv and install requirements: `pip install -r requirements.txt`
3. Run: `flask run` or `gunicorn app:app`
4. Register an account and upload your CSV using the UI.

Deploy to Render: Push repo to GitHub and create a Web Service pointing to this repo.
```

---

### Done
I updated this canvas with the full multi-file project. Copy the files into your GitHub repo and I can help with any follow-up: e.g. migration scripts, adding tests, or committing them to your repo via instructions. If you want I can also generate a ZIP file of the project here.
