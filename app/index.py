#!/usr/bin/env python3
"""
Single-file Flask API gateway + admin UI for FT-OSINT proxying with per-key:
- name, generated key, expiry, daily limit, allowed tools, revoke
- usage logging and counters (SQLite)
- admin login seeded: username=vernex password=vernex@16vx

Place this at api/index.py (or api/index.py when deploying).
"""
import os
import sqlite3
import secrets
import requests
from datetime import datetime, timezone
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    abort,
    render_template_string,
)

# ---------- Configuration ----------
DB_PATH = os.environ.get("DATA_DB", "data.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_ME_IN_PROD")
ADMIN_USERNAME = os.environ.get("ADMIN_USER", "vernex")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASS", "vernex@16vx")

# Upstream endpoints map (tool key -> upstream URL)
UPSTREAM_MAP = {
    "adv": "https://ft-osint-api.duckdns.org/api/adv",
    "paytm": "https://ft-osint-api.duckdns.org/api/paytm",
    "imei": "https://ft-osint-api.duckdns.org/api/imei",
    "calltracer": "https://ft-osint-api.duckdns.org/api/calltracer",
    "upi": "https://ft-osint-api.duckdns.org/api/upi",
    "ifsc": "https://ft-osint-api.duckdns.org/api/ifsc",
    "pincode": "https://ft-osint-api.duckdns.org/api/pincode",
    "ip": "https://ft-osint-api.duckdns.org/api/ip",
    "challan": "https://ft-osint-api.duckdns.org/api/challan",
    "ff": "https://ft-osint-api.duckdns.org/api/ff",
    "bgmi": "https://ft-osint-api.duckdns.org/api/bgmi",
    "snap": "https://ft-osint-api.duckdns.org/api/snap",
    "number": "https://ft-osint-api.duckdns.org/api/number",
    "email": "https://ft-osint-api.duckdns.org/api/email",
    "vehicle": "https://ft-osint-api.duckdns.org/api/vehicle",
    "git": "https://ft-osint-api.duckdns.org/api/git",
    "insta": "https://ft-osint-api.duckdns.org/api/insta",
    "tg": "https://ft-osint-api.duckdns.org/api/tg",
    "tgidinfo": "https://ft-osint-api.duckdns.org/api/tgidinfo",
    "numleak": "https://ft-osint-api.duckdns.org/api/numleak",
}

# Substitutions to remove original branding/links
REPLACE_MAP = {
    "@ftgamer2": "SHAYAN_EXPLORER",
    "@bornex": "SHAYAN_EXPLORER",
    "Ultra": "",
    "https://t.me/ftgamer2": "https://yourdomain.example",
}

# ---------- Helpers ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY,
            name TEXT,
            api_key TEXT UNIQUE,
            allowed_tools TEXT,
            daily_limit INTEGER DEFAULT 0,
            created_at TEXT,
            expires_at TEXT,
            revoked INTEGER DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY,
            api_key TEXT,
            tool TEXT,
            ts TEXT,
            ip TEXT,
            path TEXT,
            response_code INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS counters (
            id INTEGER PRIMARY KEY,
            api_key TEXT,
            day TEXT,
            count INTEGER
        )
        """
    )
    # seed admin user if missing
    cur.execute("SELECT * FROM users WHERE username = ?", (ADMIN_USERNAME,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
            (ADMIN_USERNAME, ADMIN_PASSWORD, datetime.now(timezone.utc).isoformat()),
        )
    conn.commit()
    conn.close()

def generate_key(nbytes=32):
    return secrets.token_urlsafe(nbytes)[:nbytes]

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def iso_to_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        # try appending midnight
        try:
            return datetime.fromisoformat(s + "T00:00:00")
        except Exception:
            return None

# DB helpers for keys & usage
def create_key_db(name, api_key, allowed_tools, daily_limit, expires_at):
    conn = get_conn()
    cur = conn.cursor()
    allowed = ",".join(allowed_tools or [])
    cur.execute(
        "INSERT INTO api_keys (name, api_key, allowed_tools, daily_limit, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, api_key, allowed, daily_limit or 0, now_iso(), expires_at),
    )
    conn.commit()
    conn.close()

def get_key_record(api_key):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM api_keys WHERE api_key = ?", (api_key,))
    row = cur.fetchone()
    conn.close()
    return row

def list_keys_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM api_keys ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def set_revoke_db(api_key, revoke=True):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE api_keys SET revoked = ? WHERE api_key = ?", (1 if revoke else 0, api_key))
    conn.commit()
    conn.close()

def increment_counter(api_key, ip, tool, path, response_code):
    conn = get_conn()
    cur = conn.cursor()
    ts = now_iso()
    cur.execute(
        "INSERT INTO usage (api_key, tool, ts, ip, path, response_code) VALUES (?, ?, ?, ?, ?, ?)",
        (api_key, tool, ts, ip, path, response_code),
    )
    day = datetime.now(timezone.utc).date().isoformat()
    cur.execute("SELECT count FROM counters WHERE api_key = ? AND day = ?", (api_key, day))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE counters SET count = count + 1 WHERE api_key = ? AND day = ?", (api_key, day))
    else:
        cur.execute("INSERT INTO counters (api_key, day, count) VALUES (?, ?, 1)", (api_key, day))
    conn.commit()
    conn.close()

def get_today_count(api_key):
    conn = get_conn()
    cur = conn.cursor()
    day = datetime.now(timezone.utc).date().isoformat()
    cur.execute("SELECT count FROM counters WHERE api_key = ? AND day = ?", (api_key, day))
    row = cur.fetchone()
    conn.close()
    return row["count"] if row else 0

def query_usage(limit=200):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usage ORDER BY ts DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def verify_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return row["password"] == password

# ---------- Application ----------
init_db()
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------- Auth helpers ----------
def require_auth():
    return session.get("user") == ADMIN_USERNAME

# ---------- Key policy check ----------
def check_key_policy(api_key: str, tool: str):
    rec = get_key_record(api_key)
    if not rec:
        return False, "Invalid API key"
    if rec["revoked"]:
        return False, "Key revoked"
    if rec["expires_at"]:
        try:
            exp = iso_to_dt(rec["expires_at"])
        except Exception:
            exp = None
        if exp and exp.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return False, "Key expired"
    if rec["daily_limit"] is not None and rec["daily_limit"] >= 0:
        if rec["daily_limit"] > 0:
            today = get_today_count(api_key)
            if today >= rec["daily_limit"]:
                return False, "Daily limit exceeded"
    # allowed tools
    allowed = rec["allowed_tools"] or ""
    allowed = allowed.strip()
    if allowed:
        allowed_set = set(x.strip() for x in allowed.split(",") if x.strip())
        if allowed_set and tool not in allowed_set:
            return False, f"Tool '{tool}' not allowed for this key"
    return True, rec

# ---------- Admin UI (minimal HTML) ----------
INDEX_HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>SHAYAN_EXPLORER API Gateway</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <style>
      body{font-family:Inter,Arial;background:#071021;color:#fff;padding:18px}
      a{color:#7c5cff}
      .card{background:rgba(255,255,255,0.02);padding:12px;border-radius:8px;margin-bottom:12px;border:1px solid rgba(255,255,255,0.03)}
      input,select{padding:8px;border-radius:6px;border:1px solid rgba(255,255,255,0.06);background:transparent;color:#fff}
      label{display:block;margin-top:8px}
    </style>
  </head>
  <body>
    <h1>SHAYAN_EXPLORER — API Gateway</h1>
    <p>Proxy endpoints for FT-OSINT suite. Use <code>/api/&lt;tool&gt;?key=YOUR_KEY&amp;...params...</code></p>
    <div class="card">
      <h3>Admin</h3>
      <p><a href="/admin">Open Admin Panel</a></p>
    </div>
    <div class="card">
      <h3>Docs</h3>
      <p>Tools: {{tools}}</p>
      <p>Example: <code>/api/number?key=YOUR_KEY&num=9876543210</code></p>
    </div>
    <footer style="margin-top:20px;color:#9aa8bf">API developer: SHAYAN_EXPLORER</footer>
  </body>
</html>
"""

ADMIN_HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>Admin Panel — SHAYAN_EXPLORER</title>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <style>
      body{font-family:Inter,Arial;background:#04101a;color:#fff;padding:18px}
      .card{background:rgba(255,255,255,0.02);padding:12px;border-radius:8px;margin-bottom:12px;border:1px solid rgba(255,255,255,0.03)}
      input,select,textarea{padding:8px;border-radius:6px;border:1px solid rgba(255,255,255,0.06);background:transparent;color:#fff;width:100%}
      label{display:block;margin-top:8px}
      table{width:100%;border-collapse:collapse;margin-top:12px}
      th,td{padding:8px;border-bottom:1px solid rgba(255,255,255,0.03);color:#9aa8bf;font-size:13px}
      .btn{background:#7c5cff;padding:8px 10px;border-radius:8px;color:#fff;border:none;cursor:pointer}
      a{color:#7c5cff}
    </style>
  </head>
  <body>
    <h1>Admin — SHAYAN_EXPLORER</h1>
    <p><a href="/">Back to Home</a> — <a href="/logout">Logout</a></p>

    <div class="card">
      <h3>Create API Key</h3>
      <form method="post" action="/admin/keys/create">
        <label>Name <input name="name" required></label>
        <label>Daily limit (0 = unlimited) <input name="daily_limit" type="number" value="0"></label>
        <label>Expiry (YYYY-MM-DD or YYYY-MM-DDTHH:MM) <input name="expires_at" placeholder="2026-12-31"></label>
        <label>Allowed tools (comma separated, blank = all) <input name="allowed_tools" placeholder="number,email,ip"></label>
        <div style="margin-top:8px"><button class="btn" type="submit">Create Key</button></div>
      </form>
    </div>

    <div class="card">
      <h3>API Keys</h3>
      {% for k in keys %}
        <div style="margin-bottom:8px">
          <strong>{{k['name']}}</strong> — <code>{{k['api_key']}}</code><br/>
          Allowed: {{k['allowed_tools'] or "all"}} | Daily: {{k['daily_limit']}} | Expires: {{k['expires_at']}} | Revoked: {{k['revoked']}}
          <form method="post" action="/admin/keys/revoke" style="display:inline-block;margin-left:8px">
            <input type="hidden" name="api_key" value="{{k['api_key']}}">
            {% if k['revoked'] %}
              <button class="btn" name="revoke" value="0">Unrevoke</button>
            {% else %}
              <button class="btn" name="revoke" value="1">Revoke</button>
            {% endif %}
          </form>
        </div>
      {% endfor %}
    </div>

    <div class="card">
      <h3>Recent Usage (last 200)</h3>
      <table>
        <thead><tr><th>Time</th><th>Key</th><th>Tool</th><th>IP</th><th>Path</th><th>Code</th></tr></thead>
        <tbody>
        {% for u in usage %}
          <tr>
            <td>{{u['ts']}}</td>
            <td><code>{{u['api_key']}}</code></td>
            <td>{{u['tool']}}</td>
            <td>{{u['ip']}}</td>
            <td>{{u['path']}}</td>
            <td>{{u['response_code']}}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""

LOGIN_HTML = """
<!doctype html>
<html>
  <head><meta charset="utf-8"/><title>Login</title></head>
  <body style="font-family:Inter,Arial;background:#071021;color:#fff;padding:18px">
    <h2>Admin Login</h2>
    {% if error %}<div style="color:#f88">{{error}}</div>{% endif %}
    <form method="post" action="/login">
      <label>Username <input name="username" value="{{default_user}}"></label>
      <label>Password <input type="password" name="password" value="{{default_pass}}"></label>
      <div style="margin-top:8px"><button type="submit">Login</button></div>
    </form>
  </body>
</html>
"""

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template_string(INDEX_HTML, tools=", ".join(sorted(UPSTREAM_MAP.keys())))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if verify_user(u, p):
            session["user"] = u
            return redirect(url_for("admin"))
        return render_template_string(LOGIN_HTML, error="Invalid credentials", default_user=u or "", default_pass="")
    return render_template_string(LOGIN_HTML, error=None, default_user=ADMIN_USERNAME, default_pass=ADMIN_PASSWORD)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

@app.route("/admin")
def admin():
    if not require_auth():
        return redirect(url_for("login"))
    keys = [dict(r) for r in list_keys_db()]
    usage = [dict(r) for r in query_usage(limit=200)]
    return render_template_string(ADMIN_HTML, keys=keys, usage=usage)

@app.route("/admin/keys/create", methods=["POST"])
def admin_create_key():
    if not require_auth():
        abort(403)
    name = request.form.get("name") or "unnamed"
    daily_limit = int(request.form.get("daily_limit") or 0)
    expires_at_raw = request.form.get("expires_at") or None
    expires_iso = None
    if expires_at_raw:
        dt = iso_to_dt(expires_at_raw)
        expires_iso = dt.isoformat() if dt else None
    allowed = request.form.get("allowed_tools") or ""
    allowed_list = [x.strip() for x in allowed.split(",") if x.strip()]
    key = generate_key(36)
    create_key_db(name=name, api_key=key, allowed_tools=allowed_list, daily_limit=daily_limit, expires_at=expires_iso)
    return redirect(url_for("admin"))

@app.route("/admin/keys/revoke", methods=["POST"])
def admin_revoke():
    if not require_auth():
        abort(403)
    key = request.form.get("api_key")
    revoke = request.form.get("revoke", "1") == "1"
    set_revoke_db(key, revoke)
    return redirect(url_for("admin"))

@app.route("/admin/keys/generate.json", methods=["POST"])
def admin_generate_json():
    if not require_auth():
        abort(403)
    j = request.get_json() or {}
    name = j.get("name", "temp")
    daily_limit = int(j.get("daily_limit", 0))
    allowed_tools = j.get("allowed_tools", [])
    expires_at = j.get("expires_at", None)
    if expires_at:
        dt = iso_to_dt(expires_at)
        expires_at = dt.isoformat() if dt else None
    key = generate_key(36)
    create_key_db(name=name, api_key=key, allowed_tools=allowed_tools, daily_limit=daily_limit, expires_at=expires_at)
    return jsonify({"ok": True, "api_key": key})

@app.route("/admin/keys.json")
def admin_keys_json():
    if not require_auth():
        abort(403)
    rows = [dict(r) for r in list_keys_db()]
    return jsonify(rows)

@app.route("/api/<tool>", methods=["GET", "POST"])
def proxy_tool(tool):
    # Accept key via ?key= or X-API-KEY header
    api_key = request.args.get("key") or request.headers.get("X-API-KEY")
    if not api_key:
        return jsonify({"ok": False, "error": "Missing key"}), 401
    valid, info = check_key_policy(api_key, tool)
    if not valid:
        return jsonify({"ok": False, "error": info}), 403

    if tool not in UPSTREAM_MAP:
        return jsonify({"ok": False, "error": "Unknown tool"}), 404
    upstream = UPSTREAM_MAP[tool]

    # forward params except our key
    forward_params = {}
    for k, v in request.args.items():
        if k == "key":
            continue
        forward_params[k] = v

    # for POST, forward JSON or form as appropriate (small proxy)
    try:
        if request.method == "POST":
            if request.is_json:
                resp = requests.post(upstream, json=request.get_json(), params=forward_params, timeout=15)
            else:
                resp = requests.post(upstream, data=request.form, params=forward_params, timeout=15)
        else:
            resp = requests.get(upstream, params=forward_params, timeout=15)
    except Exception as e:
        increment_counter(api_key, request.remote_addr, tool, request.path, 502)
        return jsonify({"ok": False, "error": "Upstream fetch failed", "detail": str(e)}), 502

    # sanitize body
    body_text = resp.text
    for a, b in REPLACE_MAP.items():
        if a and a in body_text:
            body_text = body_text.replace(a, b)

    increment_counter(api_key, request.remote_addr, tool, request.full_path, resp.status_code)

    content_type = resp.headers.get("Content-Type", "") or ""
    if "application/json" in content_type:
        # Return JSON string as JSON response
        try:
            return app.response_class(body_text, status=resp.status_code, mimetype="application/json")
        except Exception:
            return jsonify({"ok": False, "error": "Failed to parse upstream JSON"}), 502
    else:
        return app.response_class(body_text, status=resp.status_code, mimetype=content_type or "text/plain")

@app.route("/health")
def health():
    return jsonify({"ok": True})

# ---------- Run ----------
if __name__ == "__main__":
    # Local debug server
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), debug=True)
