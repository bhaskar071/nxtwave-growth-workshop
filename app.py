import os
import csv
import io
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session,
    render_template_string, flash, make_response
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "local-demo-secret-change-before-deployment"
)

# Use DATABASE_PATH on hosting if a persistent database location is configured.
DB = os.environ.get("DATABASE_PATH", "growth_studio.db")
GOAL = 500
BUDGET = 2000

CHANNELS = [
    "WhatsApp Groups",
    "College Clubs",
    "Email Campaigns",
    "Student Ambassadors",
    "LinkedIn",
    "Instagram"
]

DAILY_TARGETS = [40, 60, 70, 80, 80, 80, 90]

BUDGET_PLAN = {
    "Student Ambassadors": 700,
    "College Clubs": 500,
    "Email Campaigns": 300,
    "WhatsApp Groups": 300,
    "Contingency": 200
}

EXPERIMENTS = [
    {
        "name": "Message positioning",
        "hypothesis": (
            "A practical project outcome will attract more registrations "
            "than a general AI-learning message."
        ),
        "test": "Compare two messages with similar audience groups.",
        "metric": "Registration conversion rate",
        "decision": "Use the message with the higher conversion rate after a fair comparison."
    },
    {
        "name": "Referral versus direct CTA",
        "hypothesis": "Student referrals will increase registrations from campus communities.",
        "test": "Compare referral-led posts with direct registration posts.",
        "metric": "Attributed registrations per post",
        "decision": "Scale the better-performing approach if results support it."
    },
    {
        "name": "Landing-page CTA",
        "hypothesis": "A prominent registration button will improve sign-ups.",
        "test": "Compare a prominent CTA with a standard text link.",
        "metric": "Landing-page registration rate",
        "decision": "Adopt the better-performing version after sufficient visits."
    }
]


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def connect_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    """Create required tables whenever the app starts."""
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                college TEXT NOT NULL,
                channel TEXT NOT NULL,
                referral_code TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS referral_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        con.execute("""
            INSERT OR IGNORE INTO referral_codes
            (code, owner, category, created_at)
            VALUES (?, ?, ?, ?)
        """, ("CAMPUS01", "Demo Student Ambassador",
              "Student Ambassador", now))

        con.execute("""
            INSERT OR IGNORE INTO referral_codes
            (code, owner, category, created_at)
            VALUES (?, ?, ?, ?)
        """, ("CLUB01", "Demo College Club", "College Club", now))


# Critical fix: initialize tables when Gunicorn imports this module.
init_db()


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


# --------------------------------------------------
# SHARED WEBSITE DESIGN
# --------------------------------------------------

BASE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} | Campus Growth Engine</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
 --purple:#7053f5; --blue:#3d73f5; --teal:#0ba5a7;
 --pink:#e94f9a; --orange:#f59e35; --ink:#172746;
 --muted:#697c9d; --line:#e0e7f5; --bg:#f4f6ff;
}
* {box-sizing:border-box}
body {
 margin:0;background:var(--bg);color:var(--ink);
 font-family:Inter,"Segoe UI",Arial,sans-serif
}
a {color:var(--purple);text-decoration:none}
button,.btn {
 border:0;border-radius:12px;padding:12px 17px;
 font-weight:700;cursor:pointer;display:inline-block;
 font-size:14px;text-decoration:none
}
.btn-primary {
 background:linear-gradient(110deg,var(--purple),var(--blue));
 color:white
}
.btn-secondary {background:white;border:1px solid var(--line);color:var(--ink)}
.btn-pink {
 background:linear-gradient(110deg,var(--pink),var(--purple));color:white
}
.layout {display:grid;grid-template-columns:260px minmax(0,1fr);min-height:100vh}
.sidebar {background:white;border-right:1px solid var(--line);padding:24px 17px}
.brand {font-size:19px;font-weight:800;display:flex;gap:11px;align-items:center}
.logo {
 background:linear-gradient(140deg,var(--purple),#08bfc5);
 color:white;border-radius:14px;padding:12px;font-weight:900
}
.small {font-size:12px;color:var(--muted)}
.navtitle {font-size:11px;letter-spacing:1.5px;color:#8995ae;margin:30px 10px 12px}
.nav a {
 display:block;padding:13px 12px;margin:4px 0;border-radius:12px;color:#50617f
}
.nav a:hover,.nav a.active {background:#edf0ff;color:var(--purple);font-weight:700}
.brief {
 margin-top:28px;padding:17px;border-radius:17px;
 background:linear-gradient(140deg,#f0eaff,#e6fbf8);
 line-height:1.7;font-size:13px
}
main {padding:30px;min-width:0}
.top {
 display:flex;justify-content:space-between;gap:18px;
 align-items:center;margin-bottom:24px
}
.eyebrow {font-size:11px;letter-spacing:2px;color:var(--purple);font-weight:800}
h1 {font-size:32px;margin:8px 0}
h2 {font-size:20px;margin:0 0 18px}
p {line-height:1.65}
.muted {color:var(--muted)}
.card {
 background:white;border:1px solid var(--line);border-radius:18px;
 padding:23px;margin-bottom:18px;box-shadow:0 4px 18px #22305b05;
 min-width:0
}
.grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.stats {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:18px}
.stat {
 background:white;border:1px solid var(--line);border-radius:17px;
 padding:20px;border-top:5px solid var(--purple)
}
.stat:nth-child(2){border-top-color:var(--blue)}
.stat:nth-child(3){border-top-color:var(--teal)}
.stat:nth-child(4){border-top-color:var(--orange)}
.stat strong {display:block;font-size:29px;margin:12px 0}
label {font-size:12px;font-weight:800;display:block;margin:16px 0 8px}
input,select,textarea {
 width:100%;padding:13px;border:1px solid #d7e0f2;
 border-radius:10px;font:inherit;background:white;color:var(--ink)
}
textarea {min-height:120px;resize:vertical}
form button {margin-top:18px}
table {width:100%;border-collapse:collapse;font-size:13px}
th,td {text-align:left;padding:13px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th {color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.table-wrap {overflow-x:auto}
.notice {padding:13px 16px;background:#edf6ff;border:1px solid #d2e5ff;border-radius:12px;margin-bottom:15px;color:#315a91}
.success {background:#eafaf2;border-color:#bcebd2;color:#137653}
.warning {background:#fff8e8;border-color:#ffe3a4;color:#925c00}
.hero {
 padding:34px;border:1px solid #ddd8ff;border-radius:22px;
 background:linear-gradient(115deg,#f0eaff,#fff 55%,#e2fbf8)
}
.hero h2 {font-size:34px;line-height:1.2;max-width:620px}
.pill {
 display:inline-block;padding:6px 10px;border-radius:20px;
 background:#fff7e5;color:#a46900;font-size:11px;font-weight:800
}
.progress {height:9px;background:#e9edf6;border-radius:20px;overflow:hidden}
.progress span {display:block;height:100%;background:linear-gradient(90deg,var(--purple),var(--teal))}
footer {text-align:center;color:#8190ad;font-size:12px;padding:18px}
ul.clean {padding-left:20px;line-height:1.9}
@media(max-width:1000px) {
 .layout {grid-template-columns:1fr}
 .sidebar {border-right:0;border-bottom:1px solid var(--line)}
 .nav {display:flex;flex-wrap:wrap}
 .navtitle {margin-top:18px}
 .brief {display:none}
 .stats {grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:650px) {
 main {padding:16px}
 .grid {grid-template-columns:1fr}
 .stats {grid-template-columns:1fr 1fr}
 .top {align-items:flex-start;flex-direction:column}
 h1 {font-size:27px}
 .hero {padding:22px}
 .hero h2 {font-size:27px}
}
</style>
</head>
<body>
<div class="layout">
<aside class="sidebar">
 <div class="brand">
  <span class="logo">AI</span>
  <span>Campus Growth<br><span class="small">GROWTH ENGINE</span></span>
 </div>
 <div class="navtitle">{{ 'ADMIN WORKSPACE' if is_admin else 'WORKSHOP' }}</div>
 <nav class="nav">
 {% if is_admin %}
  <a href="{{ url_for('dashboard') }}">▦ &nbsp; Dashboard</a>
  <a href="{{ url_for('referrals') }}">↗ &nbsp; Referral tracker</a>
  <a href="{{ url_for('campaign') }}">◷ &nbsp; Campaign plan</a>
  <a href="{{ url_for('experiments') }}">✦ &nbsp; Experiments</a>
  <a href="{{ url_for('message_studio') }}">✎ &nbsp; Message studio</a>
  <a href="{{ url_for('registrations') }}">▤ &nbsp; Registrations</a>
 {% else %}
  <a href="{{ url_for('home') }}">⌂ &nbsp; Workshop overview</a>
 {% endif %}
 </nav>
 <div class="brief">
  <b style="color:#5e45d9">CAMPAIGN BRIEF</b><br>
  Build Your First AI Project in 60 Minutes<br><br>
  Goal: 500 registrations<br>
  Duration: 7 days<br>
  Budget: ₹2,000
  <p style="color:#bd7900;font-weight:800;margin-bottom:0">Simulation · Demo data only</p>
 </div>
</aside>
<main>
 <div class="top">
  <div>
   <div class="eyebrow">NXTWAVE GROWTH CHALLENGE</div>
   <h1>{{ title }}</h1>
   <div class="muted">Campus AI Growth Engine · Student acquisition prototype</div>
  </div>
  <div style="display:flex;gap:10px;flex-wrap:wrap">
  {% if is_admin %}
   <a class="btn btn-secondary" href="{{ url_for('home') }}">View student site ↗</a>
   <a class="btn btn-pink" href="{{ url_for('logout') }}">Log out</a>
  {% else %}
   <span class="pill">● SIMULATION ONLY</span>
   <a class="btn btn-primary" href="{{ url_for('register') }}">Register for free →</a>
   <a class="btn btn-secondary" href="{{ url_for('admin_login') }}">Admin login</a>
  {% endif %}
  </div>
 </div>
 {% for category, message in get_flashed_messages(with_categories=true) %}
 <div class="notice {{ 'success' if category=='success' else 'warning' }}">{{ message }}</div>
 {% endfor %}
 {{ content|safe }}
 <footer>Campus AI Growth Engine · Working prototype · Campaign targets are simulated</footer>
</main>
</div>
</body>
</html>
"""


def page(title, content, is_admin=False, **context):
    body = render_template_string(content, **context)
    return render_template_string(
        BASE, title=title, content=body, is_admin=is_admin
    )


# --------------------------------------------------
# STUDENT WEBSITE
# --------------------------------------------------

@app.route("/")
def home():
    return page("Workshop overview", """
    <section class="hero">
      <div class="eyebrow">FREE ONLINE WORKSHOP · BEGINNER FRIENDLY</div>
      <h2>Build Your First AI Project<br>in 60 Minutes</h2>
      <p class="muted">
       Turn your curiosity about artificial intelligence into a practical project idea.
       Join a focused, beginner-friendly workshop designed for final-year engineering students.
      </p>
      <a class="btn btn-primary" href="{{ url_for('register') }}">Reserve your free spot →</a>
      <a class="btn btn-secondary" href="#learn">Explore workshop</a>
    </section>
    <div class="stats" style="margin-top:20px">
      <div class="stat"><span class="small">WORKSHOP DURATION</span><strong>60 min</strong><span class="small">Focused learning</span></div>
      <div class="stat"><span class="small">REGISTRATION FEE</span><strong>₹0</strong><span class="small">Free workshop</span></div>
      <div class="stat"><span class="small">LEARNING FOCUS</span><strong>AI Project</strong><span class="small">Practical introduction</span></div>
      <div class="stat"><span class="small">DELIVERY</span><strong>Online</strong><span class="small">Remote participation</span></div>
    </div>
    <section class="card" id="learn">
      <h2>What you will get</h2>
      <div class="grid">
        <div><h3>01 · Project thinking</h3><p class="muted">Turn a real problem into a beginner-friendly AI project idea.</p></div>
        <div><h3>02 · Guided learning</h3><p class="muted">Understand the basic workflow of an AI project.</p></div>
        <div><h3>03 · Clear next steps</h3><p class="muted">Leave with a practical starting point for further learning.</p></div>
        <div><h3>04 · Beginner friendly</h3><p class="muted">Designed for final-year engineering students exploring AI.</p></div>
      </div>
      <a class="btn btn-primary" href="{{ url_for('register') }}">Register for free →</a>
    </section>
    <div class="notice warning">
      Demo landing page: no real workshop date or joining link is being promised.
    </div>
    """)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        college = request.form.get("college", "").strip()
        channel = request.form.get("channel", "").strip()
        code = request.form.get("referral_code", "").strip().upper()

        if not name or not email or not college or channel not in CHANNELS:
            flash("Please complete all required fields.", "warning")
            return redirect(url_for("register"))

        if len(name) > 100 or len(email) > 160 or len(college) > 160:
            flash("Please check the length of your details.", "warning")
            return redirect(url_for("register"))

        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            flash("Enter a valid email address.", "warning")
            return redirect(url_for("register"))

        with connect_db() as con:
            if code:
                exists = con.execute(
                    "SELECT 1 FROM referral_codes WHERE code=?", (code,)
                ).fetchone()
                if not exists:
                    flash(
                        "Referral code not found. Leave it blank if you do not have one.",
                        "warning"
                    )
                    return redirect(url_for("register"))

            duplicate = con.execute(
                "SELECT 1 FROM registrations WHERE email=?", (email,)
            ).fetchone()

            if duplicate:
                flash("This email is already registered in the demo.", "warning")
                return redirect(url_for("register"))

            con.execute("""
                INSERT INTO registrations
                (name, email, college, channel, referral_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name, email, college, channel, code,
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

        return redirect(url_for("registration_success"))

    return page("Student registration", """
    <section class="card">
      <span class="eyebrow">YOUR NEXT LEARNING STEP</span>
      <h2 style="margin-top:10px">Register for the AI workshop</h2>
      <p class="muted">Complete this form to demonstrate the student registration journey.</p>
      <form method="post">
        <div class="grid">
          <div>
            <label for="name">FULL NAME *</label>
            <input id="name" name="name" maxlength="100" required placeholder="Enter your name">
          </div>
          <div>
            <label for="email">EMAIL ADDRESS *</label>
            <input id="email" name="email" type="email" maxlength="160" required placeholder="student@example.com">
          </div>
          <div>
            <label for="college">COLLEGE NAME *</label>
            <input id="college" name="college" maxlength="160" required placeholder="Your engineering college">
          </div>
          <div>
            <label for="channel">WHERE DID YOU SEE THIS WORKSHOP? *</label>
            <select id="channel" name="channel" required>
              {% for c in channels %}
              <option value="{{ c }}">{{ c }}</option>
              {% endfor %}
            </select>
          </div>
        </div>
        <label for="referral_code">AMBASSADOR OR CLUB REFERRAL CODE (OPTIONAL)</label>
        <input id="referral_code" name="referral_code" maxlength="40" placeholder="e.g. CAMPUS01">
        <div class="notice" style="margin-top:16px">
          Demo only: use fictional information. Referral codes are optional.
        </div>
        <button class="btn btn-primary" type="submit">Submit demo registration →</button>
        <a class="btn btn-secondary" href="{{ url_for('home') }}">Back to workshop</a>
      </form>
    </section>
    """, channels=CHANNELS)


@app.route("/registration-success")
def registration_success():
    return page("Registration received", """
    <section class="card" style="text-align:center;padding:45px 20px">
      <div style="font-size:48px;color:#0ba5a7">✓</div>
      <h2>Demo registration saved</h2>
      <p class="muted">Your test submission has been saved to the demo database.</p>
      <div class="notice warning">This is not a real workshop confirmation or joining link.</div>
      <a class="btn btn-primary" href="{{ url_for('home') }}">Back to workshop</a>
    </section>
    """)


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "Nxtwave@123")

        if (
            request.form.get("username") == username
            and request.form.get("password") == password
        ):
            session["admin"] = True
            return redirect(url_for("dashboard"))

        flash("Incorrect username or password.", "warning")

    return page("Admin login", """
    <section class="card" style="max-width:520px">
      <h2>Admin workspace</h2>
      <p class="muted">Sign in to review simulated campaign data.</p>
      <form method="post">
        <label>USERNAME</label>
        <input name="username" required autocomplete="username">
        <label>PASSWORD</label>
        <input type="password" name="password" required autocomplete="current-password">
        <button class="btn btn-primary" type="submit">Sign in →</button>
      </form>
      <div class="notice warning" style="margin-top:18px">
        Demo credentials: <b>admin</b> / <b>Nxtwave@123</b>.
        Set secure environment variables before public use.
      </div>
    </section>
    """)


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/admin")
@admin_required
def dashboard():
    with connect_db() as con:
        total = con.execute(
            "SELECT COUNT(*) AS n FROM registrations"
        ).fetchone()["n"]

        rows = con.execute(
            "SELECT channel, COUNT(*) AS n FROM registrations GROUP BY channel"
        ).fetchall()

        recent = con.execute("""
            SELECT name, college, channel, created_at
            FROM registrations ORDER BY id DESC LIMIT 5
        """).fetchall()

    counts = {channel: 0 for channel in CHANNELS}
    for row in rows:
        counts[row["channel"]] = row["n"]

    pct = min(100, round(total / GOAL * 100, 1))
    cumulative = [sum(DAILY_TARGETS[:i]) for i in range(1, 8)]

    return page("Campaign dashboard", """
    <div class="notice success">Welcome to the admin workspace.</div>
    <div class="notice">
      Simulation only. Saved registrations are demo submissions,
      not proof of campaign performance.
    </div>
    <div class="stats">
      <div class="stat"><span class="small">REGISTRATION TARGET</span><strong>500</strong><span class="small">Seven-day goal</span></div>
      <div class="stat"><span class="small">SAVED REGISTRATIONS</span><strong>{{ total }}</strong><span class="small">Demo records</span></div>
      <div class="stat"><span class="small">DEMO PROGRESS</span><strong>{{ pct }}%</strong><div class="progress"><span style="width:{{ pct }}%"></span></div></div>
      <div class="stat"><span class="small">PROPOSED BUDGET</span><strong>₹2,000</strong><span class="small">Hypothetical allocation</span></div>
    </div>
    <div class="grid">
      <section class="card"><h2>Registrations by channel</h2><canvas id="channelChart"></canvas></section>
      <section class="card"><h2>Proposed budget allocation</h2><canvas id="budgetChart"></canvas></section>
    </div>
    <section class="card">
      <h2>Seven-day registration targets</h2>
      <canvas id="targetChart"></canvas>
      <p class="small">Planned cumulative targets, not actual daily registrations.</p>
    </section>
    <div class="grid">
      <section class="card">
        <h2>Recent demo registrations</h2>
        {% if recent %}
        <div class="table-wrap"><table>
          <tr><th>Name</th><th>College</th><th>Channel</th></tr>
          {% for r in recent %}
          <tr><td>{{ r.name }}</td><td>{{ r.college }}</td><td>{{ r.channel }}</td></tr>
          {% endfor %}
        </table></div>
        {% else %}
        <p class="muted">No registrations yet. Test the student registration form.</p>
        {% endif %}
        <p><a href="{{ url_for('registrations') }}">View all records →</a></p>
      </section>
      <section class="card">
        <h2>Quick actions</h2>
        <p><a href="{{ url_for('registrations') }}">▤ Registration records →</a></p>
        <p><a href="{{ url_for('referrals') }}">↗ Referral tracker →</a></p>
        <p><a href="{{ url_for('campaign') }}">◷ Campaign plan →</a></p>
        <p><a href="{{ url_for('experiments') }}">✦ Proposed experiments →</a></p>
        <p><a href="{{ url_for('message_studio') }}">✎ Message studio →</a></p>
      </section>
    </div>
    <script>
    new Chart(document.getElementById('channelChart'), {
      type:'bar',
      data:{
        labels:{{ channels|tojson }},
        datasets:[{
          label:'Demo registrations',
          data:{{ values|tojson }},
          backgroundColor:['#7053f5','#3d73f5','#0ba5a7','#e94f9a','#f59e35','#8b9ab7']
        }]
      },
      options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{beginAtZero:true}}}
    });
    new Chart(document.getElementById('budgetChart'), {
      type:'doughnut',
      data:{
        labels:{{ budget_labels|tojson }},
        datasets:[{
          data:{{ budget_values|tojson }},
          backgroundColor:['#7053f5','#3d73f5','#0ba5a7','#e94f9a','#f59e35']
        }]
      },
      options:{responsive:true,plugins:{legend:{position:'bottom'}}}
    });
    new Chart(document.getElementById('targetChart'), {
      type:'line',
      data:{
        labels:['Day 1','Day 2','Day 3','Day 4','Day 5','Day 6','Day 7'],
        datasets:[{
          label:'Cumulative registration target',
          data:{{ cumulative|tojson }},
          borderColor:'#7053f5',
          backgroundColor:'#7053f522',
          fill:true,
          tension:.3
        }]
      },
      options:{responsive:true,scales:{y:{beginAtZero:true,max:500}}}
    });
    </script>
    """, True,
    total=total,
    pct=pct,
    recent=recent,
    channels=CHANNELS,
    values=[counts[c] for c in CHANNELS],
    budget_labels=list(BUDGET_PLAN.keys()),
    budget_values=list(BUDGET_PLAN.values()),
    cumulative=cumulative
    )


# --------------------------------------------------
# REGISTRATION RECORDS AND CSV EXPORT
# --------------------------------------------------

@app.route("/admin/registrations")
@admin_required
def registrations():
    with connect_db() as con:
        rows = con.execute(
            "SELECT * FROM registrations ORDER BY id DESC"
        ).fetchall()

    return page("Registration records", """
    <section class="card">
      <h2>Saved demo registrations</h2>
      <p class="muted">These are test submissions, not verified campaign outcomes.</p>
      <p><a class="btn btn-primary" href="{{ url_for('export_csv') }}">Export CSV ↓</a></p>
      {% if rows %}
      <div class="table-wrap"><table>
        <tr><th>ID</th><th>Name</th><th>Email</th><th>College</th><th>Channel</th><th>Referral</th><th>Created</th></tr>
        {% for r in rows %}
        <tr>
          <td>{{ r.id }}</td><td>{{ r.name }}</td><td>{{ r.email }}</td>
          <td>{{ r.college }}</td><td>{{ r.channel }}</td>
          <td>{{ r.referral_code or '—' }}</td><td>{{ r.created_at }}</td>
        </tr>
        {% endfor %}
      </table></div>
      {% else %}
      <p>No demo registrations yet.</p>
      {% endif %}
    </section>
    """, True, rows=rows)


@app.route("/admin/export.csv")
@admin_required
def export_csv():
    with connect_db() as con:
        rows = con.execute("""
            SELECT id, name, email, college, channel, referral_code, created_at
            FROM registrations ORDER BY id
        """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "name", "email", "college",
        "channel", "referral_code", "created_at"
    ])

    for row in rows:
        writer.writerow([row[key] for key in row.keys()])

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        "attachment; filename=demo_registrations.csv"
    )
    return response


# --------------------------------------------------
# REFERRAL TRACKER
# --------------------------------------------------

@app.route("/admin/referrals", methods=["GET", "POST"])
@admin_required
def referrals():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        owner = request.form.get("owner", "").strip()
        category = request.form.get("category", "").strip()

        if not code or not owner or category not in [
            "Student Ambassador", "College Club"
        ]:
            flash("Enter a code, owner, and valid category.", "warning")
        elif len(code) > 40 or len(owner) > 100:
            flash("Please shorten the code or owner name.", "warning")
        else:
            try:
                with connect_db() as con:
                    con.execute("""
                        INSERT INTO referral_codes
                        (code, owner, category, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        code, owner, category,
                        datetime.now().strftime("%Y-%m-%d %H:%M")
                    ))
                flash("Referral code created.", "success")
            except sqlite3.IntegrityError:
                flash("That referral code already exists.", "warning")

        return redirect(url_for("referrals"))

    with connect_db() as con:
        codes = con.execute("""
            SELECT rc.*,
              (SELECT COUNT(*) FROM registrations r
               WHERE UPPER(r.referral_code)=UPPER(rc.code)) AS attributed
            FROM referral_codes rc ORDER BY rc.id DESC
        """).fetchall()

    return page("Referral tracker", """
    <div class="grid">
      <section class="card">
        <h2>Create referral code</h2>
        <form method="post">
          <label>REFERRAL CODE</label>
          <input name="code" required maxlength="40" placeholder="e.g. CAMPUS02">
          <label>AMBASSADOR OR CLUB NAME</label>
          <input name="owner" required maxlength="100" placeholder="Demo ambassador">
          <label>CATEGORY</label>
          <select name="category">
            <option>Student Ambassador</option>
            <option>College Club</option>
          </select>
          <button class="btn btn-primary">Create code →</button>
        </form>
      </section>
      <section class="card">
        <h2>How attribution works</h2>
        <p class="muted">A registration is attributed when a student enters a valid referral code. The channel field separately records where they saw the workshop.</p>
        <div class="notice warning">Creating a code does not imply real outreach.</div>
      </section>
    </div>
    <section class="card">
      <h2>Referral codes</h2>
      <div class="table-wrap"><table>
        <tr><th>Code</th><th>Owner</th><th>Category</th><th>Attributed registrations</th><th>Created</th></tr>
        {% for c in codes %}
        <tr>
          <td><b>{{ c.code }}</b></td><td>{{ c.owner }}</td>
          <td>{{ c.category }}</td><td>{{ c.attributed }}</td>
          <td>{{ c.created_at }}</td>
        </tr>
        {% endfor %}
      </table></div>
    </section>
    """, True, codes=codes)


# --------------------------------------------------
# CAMPAIGN PLAN
# --------------------------------------------------

@app.route("/admin/campaign")
@admin_required
def campaign():
    daily_rows = []
    cumulative = 0

    for i, target in enumerate(DAILY_TARGETS, 1):
        cumulative += target
        daily_rows.append({
            "day": i,
            "daily": target,
            "cumulative": cumulative
        })

    return page("Campaign plan", """
    <div class="notice">
      Planning assumptions for a seven-day simulation. These are targets, not actual results.
    </div>
    <div class="stats">
      <div class="stat"><span class="small">TOTAL GOAL</span><strong>500</strong><span class="small">Registrations</span></div>
      <div class="stat"><span class="small">CAMPAIGN WINDOW</span><strong>7 days</strong><span class="small">Proposed schedule</span></div>
      <div class="stat"><span class="small">TOTAL BUDGET</span><strong>₹2,000</strong><span class="small">Hypothetical</span></div>
      <div class="stat"><span class="small">TARGET COST / REGISTRATION</span><strong>₹4</strong><span class="small">Budget divided by target</span></div>
    </div>
    <section class="card">
      <h2>Daily registration targets</h2>
      <div class="table-wrap"><table>
        <tr><th>Day</th><th>Daily target</th><th>Cumulative target</th></tr>
        {% for d in daily_rows %}
        <tr><td>Day {{ d.day }}</td><td>{{ d.daily }}</td><td>{{ d.cumulative }}</td></tr>
        {% endfor %}
      </table></div>
    </section>
    <section class="card">
      <h2>Proposed budget allocation</h2>
      <div class="table-wrap"><table>
        <tr><th>Activity</th><th>Budget</th><th>Share</th><th>Purpose</th></tr>
        {% for name, amount in budget.items() %}
        <tr>
          <td>{{ name }}</td><td>₹{{ amount }}</td>
          <td>{{ (amount / 2000 * 100)|round(1) }}%</td>
          <td>{{ purposes[name] }}</td>
        </tr>
        {% endfor %}
        <tr><th>Total</th><th>₹{{ budget.values()|sum }}</th><th>100%</th><th>Hypothetical plan</th></tr>
      </table></div>
    </section>
    <section class="card">
      <h2>Execution sequence</h2>
      <ul class="clean">
        <li><b>Days 1–2:</b> Publish the landing page, share in relevant student groups, and recruit campus ambassadors.</li>
        <li><b>Days 3–4:</b> Share club-specific posts and send permission-based email invitations.</li>
        <li><b>Days 5–6:</b> Re-share the best-performing message and use referral codes.</li>
        <li><b>Day 7:</b> Send a final reminder, validate registrations, and review channel performance.</li>
      </ul>
      <p class="muted">Use relevant, permission-based outreach. Avoid spam and scraping personal contact details.</p>
    </section>
    """, True,
    daily_rows=daily_rows,
    budget=BUDGET_PLAN,
    purposes={
        "Student Ambassadors": "Campus outreach and referral activation",
        "College Clubs": "Student-club collaboration and distribution",
        "Email Campaigns": "Permission-based invitations and reminders",
        "WhatsApp Groups": "Relevant student-community distribution",
        "Contingency": "Reserve for the best-performing channel"
    })


# --------------------------------------------------
# PROPOSED EXPERIMENTS
# --------------------------------------------------

@app.route("/admin/experiments")
@admin_required
def experiments():
    return page("Proposed experiments", """
    <div class="notice warning">
      These are proposed tests. No experiment has been run and no result is being claimed.
    </div>
    {% for e in experiments %}
    <section class="card">
      <span class="eyebrow">TEST {{ loop.index }}</span>
      <h2 style="margin-top:8px">{{ e.name }}</h2>
      <p><b>Hypothesis:</b> {{ e.hypothesis }}</p>
      <p><b>What to test:</b> {{ e.test }}</p>
      <p><b>Primary metric:</b> {{ e.metric }}</p>
      <p><b>Decision rule:</b> {{ e.decision }}</p>
    </section>
    {% endfor %}
    """, True, experiments=EXPERIMENTS)


# --------------------------------------------------
# MESSAGE STUDIO
# --------------------------------------------------

@app.route("/admin/message-studio", methods=["GET", "POST"])
@admin_required
def message_studio():
    output = ""
    audience = "WhatsApp student group"
    angle = "Practical outcome"

    if request.method == "POST":
        audience = request.form.get("audience", audience)
        angle = request.form.get("angle", angle)

        variants = {
            "Practical outcome":
                "Want to build your first AI project? Join our free, beginner-friendly 60-minute online workshop for final-year engineering students. Explore a practical project workflow and leave with a clear starting point. Register here: [insert demo link].",
            "Beginner friendly":
                "Curious about AI but unsure where to start? This free 60-minute online workshop introduces the basics of planning your first AI project. Designed for final-year engineering students. Register here: [insert demo link].",
            "Career relevance":
                "Explore how AI project skills can support your learning journey. Join a free 60-minute introductory online workshop for final-year engineering students. Learn the basics and identify your next learning step. Register here: [insert demo link]."
        }

        output = variants.get(angle, variants["Practical outcome"])

    return page("Message studio", """
    <div class="notice warning">
      Template-based copy assistant. This page does not call a live AI model. Review the copy before use.
    </div>
    <div class="grid">
      <section class="card">
        <h2>Build a campaign message</h2>
        <form method="post">
          <label>CHANNEL / AUDIENCE</label>
          <select name="audience">
            {% for a in ["WhatsApp student group","College club","Student ambassador","Email invitation","LinkedIn post"] %}
            <option {{ 'selected' if a == audience else '' }}>{{ a }}</option>
            {% endfor %}
          </select>
          <label>MESSAGE ANGLE</label>
          <select name="angle">
            {% for a in ["Practical outcome","Beginner friendly","Career relevance"] %}
            <option {{ 'selected' if a == angle else '' }}>{{ a }}</option>
            {% endfor %}
          </select>
          <button class="btn btn-primary" type="submit">Generate sample copy →</button>
        </form>
      </section>
      <section class="card">
        <h2>Suggested message</h2>
        {% if output %}
          <textarea id="copytext">{{ output }}</textarea>
          <button class="btn btn-primary" type="button"
            onclick="navigator.clipboard.writeText(document.getElementById('copytext').value).then(()=>alert('Copied'))">
            Copy message
          </button>
        {% else %}
          <p class="muted">Choose an audience and message angle, then generate sample copy.</p>
        {% endif %}
        <p class="small">Selected audience: {{ audience }}. Replace the placeholder with your demo URL before presenting.</p>
      </section>
    </div>
    """, True, output=output, audience=audience, angle=angle)


# --------------------------------------------------
# ERROR HANDLER
# --------------------------------------------------

@app.errorhandler(404)
def not_found(_error):
    return page("Page not found", """
    <section class="card">
      <h2>Page not found</h2>
      <p>The page may have moved.</p>
      <a class="btn btn-primary" href="{{ url_for('home') }}">Return to workshop</a>
    </section>
    """), 404


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

# This runs both locally and when Render/Gunicorn imports the application.
init_db()

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000"))
    )
