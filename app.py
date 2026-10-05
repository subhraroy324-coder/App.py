# =====================================================================
#  VERNEX OSINT API CONTROL CENTER
#  Developer: SHAYAN_EXPLORER
#  Stack: Flask + SQLite + Telegram Bot
#  Run:  pip install flask requests
#        python app.py
#  Open: http://127.0.0.1:5000
#  Admin Login: vernex / vernex@16vx
# =====================================================================

import os, json, sqlite3, secrets, threading, time, hashlib, random, string
from datetime import datetime, timedelta, timezone
from functools import wraps
import requests
from flask import Flask, request, jsonify, session

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
DB_PATH        = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vernex.db")
UPSTREAM_BASE  = "https://ft-osint-api.duckdns.org/api"
ADMIN_USER     = "vernex"
ADMIN_PASS     = "vernex@16vx"
SECRET_KEY     = secrets.token_hex(32)

app = Flask(__name__)
app.secret_key = SECRET_KEY

DB_LOCK = threading.Lock()

# ---------------------------------------------------------------------
# TOOL DEFINITIONS
# ---------------------------------------------------------------------
TOOLS = {
    "number":     {"label":"Number Info",       "icon":"📞", "param":"num"},
    "pk":         {"label":"Phone → Owner",     "icon":"🔍", "param":"num"},
    "name":       {"label":"Name → Info",       "icon":"🧑", "param":"name"},
    "aadhar":     {"label":"Aadhaar Info",      "icon":"🆔", "param":"num"},
    "adharfamily":{"label":"Aadhaar Family",    "icon":"👨‍👩‍👧", "param":"num"},
    "upi":        {"label":"UPI Info",          "icon":"💳", "param":"upi"},
    "numtoupi":   {"label":"Number → UPI",      "icon":"🔗", "param":"num"},
    "pan":        {"label":"PAN Info",          "icon":"📄", "param":"pan"},
    "vehicle":    {"label":"Vehicle Info",      "icon":"🚗", "param":"vehicle"},
    "veh2num":    {"label":"Vehicle → Number",  "icon":"🔁", "param":"vehicle"},
    "challan":    {"label":"Challan Check",     "icon":"🚨", "param":"vehicle"},
    "bomber":     {"label":"SMS Bomber",        "icon":"💣", "param":"number"},
    "adv":        {"label":"Advanced Lookup",   "icon":"⚡", "param":"num"},
    "paytm":      {"label":"Paytm Info",        "icon":"💰", "param":"num"},
    "imei":       {"label":"IMEI Info",         "icon":"📱", "param":"imei"},
    "calltracer": {"label":"Call Tracer",       "icon":"📡", "param":"num"},
    "ifsc":       {"label":"IFSC Info",         "icon":"🏦", "param":"ifsc"},
    "pincode":    {"label":"Pincode Info",      "icon":"📍", "param":"pin"},
    "ip":         {"label":"IP Lookup",         "icon":"🌐", "param":"ip"},
    "ff":         {"label":"Free Fire Info",    "icon":"🎮", "param":"uid"},
    "bgmi":       {"label":"BGMI Info",         "icon":"🔫", "param":"uid"},
    "snap":       {"label":"Snapchat Info",     "icon":"👻", "param":"username"},
    "email":      {"label":"Email → Info",      "icon":"📧", "param":"email"},
    "git":        {"label":"GitHub Lookup",     "icon":"🐙", "param":"username"},
    "insta":      {"label":"Instagram Info",    "icon":"📸", "param":"username"},
    "tg":         {"label":"Telegram Info",     "icon":"✈️", "param":"info"},
    "tgidinfo":   {"label":"Telegram ID → Num", "icon":"🆔", "param":"id"},
    "numleak":    {"label":"Number Leak",       "icon":"💧", "param":"num"},
}

# ---------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with DB_LOCK:
        c = db()
        cur = c.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_value TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            tools TEXT NOT NULL,
            expires_at TEXT,
            request_limit INTEGER DEFAULT 0,
            request_used INTEGER DEFAULT 0,
            suspended INTEGER DEFAULT 0,
            price REAL DEFAULT 0,
            device_limit INTEGER DEFAULT 1,
            devices TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_value TEXT,
            key_name TEXT,
            tool TEXT,
            input TEXT,
            ip TEXT,
            device TEXT,
            status TEXT,
            ts TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            k TEXT PRIMARY KEY,
            v TEXT
        );
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            device_limit INTEGER DEFAULT 1,
            devices TEXT DEFAULT '[]',
            api_key TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT
        );
        """)
        c.commit()
        for k, v in [("upstream_key",""), ("bot_token",""), ("bot_enabled","0"), ("bot_admin_chat","")]:
            cur.execute("INSERT OR IGNORE INTO settings (k,v) VALUES (?,?)", (k, v))
        c.commit()
        c.close()

def get_setting(k, default=""):
    with DB_LOCK:
        c = db(); r = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone(); c.close()
        return r["v"] if r else default

def set_setting(k, v):
    with DB_LOCK:
        c = db()
        c.execute("INSERT INTO settings (k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=?", (k, v, v))
        c.commit(); c.close()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def parse_dt(s):
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception:
        return None

def is_expired(s):
    dt = parse_dt(s)
    if not dt: return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > dt

# ---------------------------------------------------------------------
# AUTH DECORATOR
# ---------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("admin"):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return f(*a, **kw)
    return wrapper

# ---------------------------------------------------------------------
# ADMIN AUTH
# ---------------------------------------------------------------------
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    u = (data.get("username") or "").strip()
    p = (data.get("password") or "").strip()
    if u == ADMIN_USER and p == ADMIN_PASS:
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"ok": True})

@app.route("/api/admin/check", methods=["GET"])
def admin_check():
    return jsonify({"ok": True, "admin": bool(session.get("admin"))})

# ---------------------------------------------------------------------
# KEY GENERATION HELPERS
# ---------------------------------------------------------------------
def gen_key(prefix="VX"):
    alphabet = string.ascii_uppercase + string.digits
    body = "".join(random.choice(alphabet) for _ in range(20))
    return f"{prefix}-{body[:5]}-{body[5:10]}-{body[10:15]}-{body[15:20]}"

# ---------------------------------------------------------------------
# ADMIN: API KEYS
# ---------------------------------------------------------------------
@app.route("/api/admin/keys", methods=["GET"])
@admin_required
def list_keys():
    with DB_LOCK:
        c = db()
        rows = c.execute("SELECT * FROM api_keys ORDER BY id DESC").fetchall()
        c.close()
    out = []
    for r in rows:
        d = dict(r)
        d["tools"] = json.loads(d["tools"]) if d["tools"] not in ("all","") else "all"
        d["devices"] = json.loads(d["devices"] or "[]")
        d["expired"] = is_expired(d["expires_at"])
        out.append(d)
    return jsonify({"ok": True, "keys": out})

@app.route("/api/admin/keys", methods=["POST"])
@admin_required
def create_key():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Key name is required"}), 400
    key_value = (data.get("key_value") or "").strip()
    if not key_value:
        key_value = gen_key()
    tools = data.get("tools", "all")
    if isinstance(tools, list):
        tools = json.dumps([t for t in tools if t in TOOLS])
    else:
        tools = "all"
    expires_at = data.get("expires_at") or None
    request_limit = int(data.get("request_limit") or 0)
    price = float(data.get("price") or 0)
    device_limit = int(data.get("device_limit") or 1)
    try:
        with DB_LOCK:
            c = db()
            c.execute("""INSERT INTO api_keys
                (key_value,name,tools,expires_at,request_limit,request_used,suspended,price,device_limit,devices,created_at)
                VALUES (?,?,?,?,?,0,0,?,?,?,?)""",
                (key_value, name, tools, expires_at, request_limit, price, device_limit, "[]", now_iso()))
            c.commit()
            c.close()
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "error": "Key already exists"}), 400
    return jsonify({"ok": True, "key": key_value})

@app.route("/api/admin/keys/<int:kid>", methods=["PUT"])
@admin_required
def edit_key(kid):
    data = request.get_json(silent=True) or {}
    fields, vals = [], []
    for f in ("name","expires_at"):
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if "tools" in data:
        t = data["tools"]
        if isinstance(t, list):
            t = json.dumps([x for x in t if x in TOOLS])
        else:
            t = "all"
        fields.append("tools=?"); vals.append(t)
    if "request_limit" in data:
        fields.append("request_limit=?"); vals.append(int(data["request_limit"] or 0))
    if "price" in data:
        fields.append("price=?"); vals.append(float(data["price"] or 0))
    if "device_limit" in data:
        fields.append("device_limit=?"); vals.append(int(data["device_limit"] or 1))
    if "suspended" in data:
        fields.append("suspended=?"); vals.append(1 if data["suspended"] else 0)
    if not fields:
        return jsonify({"ok": False, "error": "Nothing to update"}), 400
    vals.append(kid)
    with DB_LOCK:
        c = db()
        c.execute(f"UPDATE api_keys SET {','.join(fields)} WHERE id=?", vals)
        c.commit(); c.close()
    return jsonify({"ok": True})

@app.route("/api/admin/keys/<int:kid>", methods=["DELETE"])
@admin_required
def delete_key(kid):
    with DB_LOCK:
        c = db()
        c.execute("DELETE FROM api_keys WHERE id=?", (kid,))
        c.commit(); c.close()
    return jsonify({"ok": True})

@app.route("/api/admin/keys/<int:kid>/restart", methods=["POST"])
@admin_required
def restart_key(kid):
    with DB_LOCK:
        c = db()
        c.execute("UPDATE api_keys SET request_used=0 WHERE id=?", (kid,))
        c.commit(); c.close()
    return jsonify({"ok": True})

@app.route("/api/admin/keys/<int:kid>/suspend", methods=["POST"])
@admin_required
def suspend_key(kid):
    with DB_LOCK:
        c = db()
        r = c.execute("SELECT suspended FROM api_keys WHERE id=?", (kid,)).fetchone()
        if not r:
            c.close(); return jsonify({"ok": False, "error": "Not found"}), 404
        new = 0 if r["suspended"] else 1
        c.execute("UPDATE api_keys SET suspended=? WHERE id=?", (new, kid))
        c.commit(); c.close()
    return jsonify({"ok": True, "suspended": new})

# ---------------------------------------------------------------------
# ADMIN: LOGS
# ---------------------------------------------------------------------
@app.route("/api/admin/logs", methods=["GET"])
@admin_required
def list_logs():
    limit = min(int(request.args.get("limit", 200)), 1000)
    key_filter = request.args.get("key", "").strip()
    with DB_LOCK:
        c = db()
        if key_filter:
            rows = c.execute("SELECT * FROM logs WHERE key_value LIKE ? ORDER BY id DESC LIMIT ?",
                             (f"%{key_filter}%", limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        c.close()
    return jsonify({"ok": True, "logs": [dict(r) for r in rows]})

# ---------------------------------------------------------------------
# ADMIN: STATS
# ---------------------------------------------------------------------
@app.route("/api/admin/stats", methods=["GET"])
@admin_required
def stats():
    now = datetime.now(timezone.utc)
    def since(days): return (now - timedelta(days=days)).isoformat()
    with DB_LOCK:
        c = db()
        total_keys = c.execute("SELECT COUNT(*) n FROM api_keys").fetchone()["n"]
        active_keys = c.execute("SELECT COUNT(*) n FROM api_keys WHERE suspended=0").fetchone()["n"]
        total_requests = c.execute("SELECT COALESCE(SUM(request_used),0) n FROM api_keys").fetchone()["n"]
        total_revenue = c.execute("SELECT COALESCE(SUM(price),0) n FROM api_keys").fetchone()["n"]
        today_rev = c.execute("SELECT COALESCE(SUM(price),0) n FROM api_keys WHERE created_at >= ?",
                              (now.replace(hour=0,minute=0,second=0,microsecond=0).isoformat(),)).fetchone()["n"]
        rev_7   = c.execute("SELECT COALESCE(SUM(price),0) n FROM api_keys WHERE created_at >= ?", (since(7),)).fetchone()["n"]
        rev_30  = c.execute("SELECT COALESCE(SUM(price),0) n FROM api_keys WHERE created_at >= ?", (since(30),)).fetchone()["n"]
        rev_365 = c.execute("SELECT COALESCE(SUM(price),0) n FROM api_keys WHERE created_at >= ?", (since(365),)).fetchone()["n"]
        chart = []
        for i in range(13, -1, -1):
            day = (now - timedelta(days=i)).replace(hour=0,minute=0,second=0,microsecond=0)
            nxt = day + timedelta(days=1)
            r = c.execute("SELECT COALESCE(SUM(price),0) n FROM api_keys WHERE created_at >= ? AND created_at < ?",
                          (day.isoformat(), nxt.isoformat())).fetchone()["n"]
            chart.append({"day": day.strftime("%d %b"), "value": round(r,2)})
        top = c.execute("SELECT tool, COUNT(*) n FROM logs GROUP BY tool ORDER BY n DESC LIMIT 8").fetchall()
        c.close()
    return jsonify({
        "ok": True, "total_keys": total_keys, "active_keys": active_keys,
        "total_requests": total_requests, "total_revenue": round(total_revenue,2),
        "today_revenue": round(today_rev,2), "revenue_7": round(rev_7,2),
        "revenue_30": round(rev_30,2), "revenue_365": round(rev_365,2),
        "chart": chart, "top_tools": [{"tool": r["tool"], "count": r["n"]} for r in top],
        "tools": TOOLS,
    })

# ---------------------------------------------------------------------
# ADMIN: SETTINGS
# ---------------------------------------------------------------------
@app.route("/api/admin/settings", methods=["GET"])
@admin_required
def get_settings():
    return jsonify({"ok": True, "settings": {
        "upstream_key": get_setting("upstream_key"),
        "bot_token":    get_setting("bot_token"),
        "bot_enabled":  get_setting("bot_enabled"),
        "bot_admin_chat": get_setting("bot_admin_chat"),
    }})

@app.route("/api/admin/settings", methods=["POST"])
@admin_required
def save_settings():
    data = request.get_json(silent=True) or {}
    for k in ("upstream_key","bot_token","bot_enabled","bot_admin_chat"):
        if k in data:
            set_setting(k, str(data[k]))
    return jsonify({"ok": True})

# ---------------------------------------------------------------------
# ADMIN: USERS
# ---------------------------------------------------------------------
@app.route("/api/admin/users", methods=["GET"])
@admin_required
def list_users():
    with DB_LOCK:
        c = db()
        rows = c.execute("SELECT id,username,device_limit,api_key,active,created_at FROM users ORDER BY id DESC").fetchall()
        c.close()
    return jsonify({"ok": True, "users": [dict(r) for r in rows]})

@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
@admin_required
def delete_user(uid):
    with DB_LOCK:
        c = db()
        c.execute("DELETE FROM users WHERE id=?", (uid,))
        c.commit(); c.close()
    return jsonify({"ok": True})

# ---------------------------------------------------------------------
# PUBLIC PROXY
# ---------------------------------------------------------------------
@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Device-Id, X-API-Key"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

def log_request(key_value, key_name, tool, inp, status):
    with DB_LOCK:
        c = db()
        c.execute("INSERT INTO logs (key_value,key_name,tool,input,ip,device,status,ts) VALUES (?,?,?,?,?,?,?,?)",
                  (key_value, key_name, tool, inp,
                   request.headers.get("X-Forwarded-For", request.remote_addr),
                   request.headers.get("X-Device-Id",""),
                   status, now_iso()))
        c.commit(); c.close()

@app.route("/api/<tool>", methods=["GET","POST","OPTIONS"])
def proxy(tool):
    if request.method == "OPTIONS":
        return ("", 204)
    if tool == "admin":
        return jsonify({"ok": False, "error": "not found"}), 404
    if tool not in TOOLS:
        return jsonify({"ok": False, "error": f"Unknown tool '{tool}'"}), 404

    key_value = (request.args.get("key") or request.headers.get("X-API-Key") or "").strip()
    if not key_value:
        return jsonify({"ok": False, "error": "Missing API key"}), 401

    with DB_LOCK:
        c = db()
        row = c.execute("SELECT * FROM api_keys WHERE key_value=?", (key_value,)).fetchone()
        c.close()

    if not row:
        log_request(key_value, "", tool, request.args.get(TOOLS[tool]["param"],""), "invalid_key")
        return jsonify({"ok": False, "error": "Invalid API key"}), 401

    row = dict(row)

    if row["suspended"]:
        log_request(key_value, row["name"], tool, request.args.get(TOOLS[tool]["param"],""), "suspended")
        return jsonify({"ok": False, "error": "Key suspended"}), 403

    if is_expired(row["expires_at"]):
        log_request(key_value, row["name"], tool, request.args.get(TOOLS[tool]["param"],""), "expired")
        return jsonify({"ok": False, "error": "Key expired"}), 403

    if row["tools"] != "all":
        try: allowed = json.loads(row["tools"])
        except Exception: allowed = []
        if tool not in allowed:
            log_request(key_value, row["name"], tool, request.args.get(TOOLS[tool]["param"],""), "tool_denied")
            return jsonify({"ok": False, "error": f"Tool '{tool}' not allowed for this key"}), 403

    if row["request_limit"] and row["request_used"] >= row["request_limit"]:
        log_request(key_value, row["name"], tool, request.args.get(TOOLS[tool]["param"],""), "limit_reached")
        return jsonify({"ok": False, "error": "Request limit reached"}), 429

    device_id = (request.headers.get("X-Device-Id") or "").strip()
    if not device_id:
        device_id = hashlib.sha256((request.headers.get("User-Agent","") + request.remote_addr).encode()).hexdigest()[:32]
    devices = json.loads(row["devices"] or "[]")
    if device_id not in devices:
        if len(devices) >= int(row["device_limit"] or 1):
            log_request(key_value, row["name"], tool, request.args.get(TOOLS[tool]["param"],""), "device_limit")
            return jsonify({"ok": False, "error": "Device limit reached. Contact admin."}), 403
        devices.append(device_id)
        with DB_LOCK:
            c = db()
            c.execute("UPDATE api_keys SET devices=? WHERE id=?", (json.dumps(devices), row["id"]))
            c.commit(); c.close()

    upstream_key = get_setting("upstream_key")
    if not upstream_key:
        return jsonify({"ok": False, "error": "Upstream key not configured by admin"}), 500

    params = {k: v for k, v in request.args.items() if k != "key"}
    params["key"] = upstream_key
    url = f"{UPSTREAM_BASE}/{tool}"
    try:
        if request.method == "POST":
            r = requests.post(url, params=params, json=request.get_json(silent=True) or {}, timeout=30)
        else:
            r = requests.get(url, params=params, timeout=30)
        try: body = r.json()
        except Exception: body = {"raw": r.text}
    except requests.exceptions.Timeout:
        log_request(key_value, row["name"], tool, params.get(TOOLS[tool]["param"],""), "timeout")
        return jsonify({"ok": False, "error": "Upstream timeout"}), 504
    except Exception as e:
        log_request(key_value, row["name"], tool, params.get(TOOLS[tool]["param"],""), f"error:{e}")
        return jsonify({"ok": False, "error": f"Upstream error: {e}"}), 502

    # =========================================================
    # CLEAN UP OLD DEVELOPER TAGS AND ADD YOURS
    # =========================================================
    if isinstance(body, dict):
        # Remove any old developer attribution keys
        for old_key in ["by", "developer", "credit", "credits", "owner", "author"]:
            if old_key in body:
                del body[old_key]
        # Add your own developer tag
        body["by"] = "DEVELOPER BY @dark_MARLBORO"
    # =========================================================

    with DB_LOCK:
        c = db()
        c.execute("UPDATE api_keys SET request_used = request_used + 1 WHERE id=?", (row["id"],))
        c.commit(); c.close()

    inp = params.get(TOOLS[tool]["param"], "")
    log_request(key_value, row["name"], tool, str(inp)[:200], "ok")
    return jsonify(body)

# ---------------------------------------------------------------------
# CUSTOMER PORTAL LOGIN
# ---------------------------------------------------------------------
@app.route("/api/user/login", methods=["POST"])
def user_login():
    data = request.get_json(silent=True) or {}
    u = (data.get("username") or "").strip()
    p = (data.get("password") or "").strip()
    device_id = (data.get("device_id") or "").strip()
    with DB_LOCK:
        c = db()
        row = c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone()
        if not row:
            c.close(); return jsonify({"ok": False, "error": "Invalid credentials"}), 401
        row = dict(row)
        if not row["active"]:
            c.close(); return jsonify({"ok": False, "error": "Account disabled"}), 403
        devices = json.loads(row["devices"] or "[]")
        if device_id and device_id not in devices:
            if len(devices) >= int(row["device_limit"] or 1):
                c.close(); return jsonify({"ok": False, "error": "Device limit reached"}), 403
            devices.append(device_id)
            c.execute("UPDATE users SET devices=? WHERE id=?", (json.dumps(devices), row["id"]))
            c.commit()
        c.close()
    return jsonify({"ok": True, "api_key": row["api_key"], "username": row["username"]})

# =====================================================================
#  TELEGRAM BOT
# =====================================================================
BOT_STATE = {"offset": 0, "running": False}

def tg_api(token, method, payload=None):
    try:
        url = f"https://api.telegram.org/bot{token}/{method}"
        r = requests.post(url, json=payload or {}, timeout=35)
        return r.json()
    except Exception:
        return {}

def bot_send(token, chat_id, text):
    tg_api(token, "sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def bot_create_login(token, chat_id, username, password, devices):
    """Create (or update) a website login + auto API key."""
    try:
        devices = int(devices)
    except Exception:
        devices = 1
    if devices < 1: devices = 1

    kv = gen_key()
    exp = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    with DB_LOCK:
        c = db()
        existing = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()

        if existing:
            c.execute("""UPDATE users SET password=?, device_limit=?, devices='[]', api_key=?, active=1
                         WHERE username=?""", (password, devices, kv, username))
            action = "updated"
        else:
            c.execute("""INSERT INTO users (username,password,device_limit,devices,api_key,active,created_at)
                         VALUES (?,?,?,?,?,1,?)""",
                      (username, password, devices, "[]", kv, now_iso()))
            action = "created"

        # create api key row
        try:
            c.execute("""INSERT INTO api_keys
                (key_value,name,tools,expires_at,request_limit,request_used,suspended,price,device_limit,devices,created_at)
                VALUES (?,?,?,?,?,0,0,?,?,?,?)""",
                (kv, username, "all", exp, 1000, 0, devices, "[]", now_iso()))
        except sqlite3.IntegrityError:
            pass
        c.commit(); c.close()

    bot_send(token, chat_id,
        f"✅ <b>Website Login {action.title()}</b>\n\n"
        f"👤 Username: <code>{username}</code>\n"
        f"🔑 Password: <code>{password}</code>\n"
        f"📱 Devices: {devices}\n"
        f"🗝️ API Key: <code>{kv}</code>\n"
        f"⏳ Expires: 30 days\n"
        f"📊 Limit: 1000 requests\n\n"
        f"🔐 Login at: <code>/api/user/login</code>")

def bot_loop():
    while True:
        try:
            if get_setting("bot_enabled") != "1":
                time.sleep(5); continue
            token = get_setting("bot_token").strip()
            if not token:
                time.sleep(5); continue

            res = tg_api(token, "getUpdates", {"offset": BOT_STATE["offset"] + 1, "timeout": 25})
            if not res.get("ok"):
                time.sleep(5); continue

            for upd in res.get("result", []):
                BOT_STATE["offset"] = max(BOT_STATE["offset"], upd["update_id"])
                msg = upd.get("message") or {}
                chat_id = msg.get("chat", {}).get("id")
                text = (msg.get("text") or "").strip()
                if not chat_id or not text:
                    continue

                admin_chat = get_setting("bot_admin_chat").strip()
                if not admin_chat:
                    set_setting("bot_admin_chat", str(chat_id))
                    admin_chat = str(chat_id)

                if str(chat_id) != admin_chat:
                    bot_send(token, chat_id, "⛔ Unauthorized. This bot is private.")
                    continue

                # ---------------------------------------------------
                # /start — help
                # ---------------------------------------------------
                if text.startswith("/start"):
                    bot_send(token, chat_id,
                        "🛰️ <b>VERNEX BOT</b>\n\n"
                        "<b>Commands:</b>\n"
                        "/loginkey &lt;username&gt; &lt;password&gt; &lt;devices&gt;\n"
                        "   → create website login + API key\n"
                        "/generate &lt;username&gt; &lt;password&gt; &lt;devices&gt;\n"
                        "   → same as /loginkey\n"
                        "/newkey &lt;name&gt; &lt;days&gt; &lt;limit&gt; &lt;price&gt;\n"
                        "   → create API key only\n"
                        "/keys — list recent keys\n"
                        "/stats — quick statistics\n\n"
                        "<i>Example:</i>\n"
                        "<code>/loginkey rahul rahul900P0 1</code>")

                # ---------------------------------------------------
                # /loginkey  +  /generate  (alias)
                # ---------------------------------------------------
                elif text.startswith("/loginkey") or text.startswith("/generate"):
                    parts = text.split()
                    if len(parts) < 4:
                        bot_send(token, chat_id,
                            "⚠️ <b>Usage:</b>\n"
                            "<code>/loginkey &lt;username&gt; &lt;password&gt; &lt;devices&gt;</code>\n\n"
                            "<i>Example:</i>\n"
                            "<code>/loginkey rahul rahul900P0 1</code>")
                        continue
                    username, password, devs = parts[1], parts[2], parts[3]
                    try:
                        bot_create_login(token, chat_id, username, password, devs)
                    except Exception as e:
                        bot_send(token, chat_id, f"❌ Failed: <code>{e}</code>")

                # ---------------------------------------------------
                # /newkey
                # ---------------------------------------------------
                elif text.startswith("/newkey"):
                    parts = text.split()
                    if len(parts) < 5:
                        bot_send(token, chat_id, "Usage: /newkey &lt;name&gt; &lt;days&gt; &lt;limit&gt; &lt;price&gt;")
                        continue
                    name = parts[1]
                    try: days = int(parts[2])
                    except: days = 30
                    try: limit = int(parts[3])
                    except: limit = 1000
                    try: price = float(parts[4])
                    except: price = 0
                    kv = gen_key()
                    exp = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
                    with DB_LOCK:
                        c = db()
                        c.execute("""INSERT INTO api_keys
                            (key_value,name,tools,expires_at,request_limit,request_used,suspended,price,device_limit,devices,created_at)
                            VALUES (?,?,?,?,?,0,0,?,?,?,?)""",
                            (kv, name, "all", exp, limit, price, 1, "[]", now_iso()))
                        c.commit(); c.close()
                    bot_send(token, chat_id,
                        f"✅ <b>API Key Created</b>\n\n"
                        f"🏷️ Name: {name}\n"
                        f"🗝️ Key: <code>{kv}</code>\n"
                        f"⏳ {days} days\n"
                        f"📊 {limit} requests\n"
                        f"💰 ₹{price}")

                # ---------------------------------------------------
                # /keys
                # ---------------------------------------------------
                elif text.startswith("/keys"):
                    with DB_LOCK:
                        c = db()
                        rows = c.execute("SELECT name,key_value,request_used,request_limit,suspended FROM api_keys ORDER BY id DESC LIMIT 10").fetchall()
                        c.close()
                    if not rows:
                        bot_send(token, chat_id, "No keys yet.")
                    else:
                        lines = ["🗝️ <b>Recent Keys</b>\n"]
                        for r in rows:
                            st = "⛔" if r["suspended"] else "✅"
                            lines.append(f"{st} <b>{r['name']}</b>\n<code>{r['key_value']}</code>\n{r['request_used']}/{r['request_limit']}\n")
                        bot_send(token, chat_id, "\n".join(lines))

                # ---------------------------------------------------
                # /stats
                # ---------------------------------------------------
                elif text.startswith("/stats"):
                    with DB_LOCK:
                        c = db()
                        tk = c.execute("SELECT COUNT(*) n FROM api_keys").fetchone()["n"]
                        tr = c.execute("SELECT COALESCE(SUM(request_used),0) n FROM api_keys").fetchone()["n"]
                        rev = c.execute("SELECT COALESCE(SUM(price),0) n FROM api_keys").fetchone()["n"]
                        c.close()
                    bot_send(token, chat_id,
                        f"📊 <b>STATS</b>\n\n🗝️ Keys: {tk}\n📡 Requests: {tr}\n💰 Revenue: ₹{round(rev,2)}")

        except Exception:
            time.sleep(5)

# =====================================================================
#  FRONTEND (SPA)  — unchanged
# =====================================================================
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>VERNEX • OSINT API CONTROL</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#05070d;--card:rgba(16,22,38,.72);--border:rgba(80,120,255,.18);
--accent:#3b82f6;--txt:#e6edf7;--mut:#8b9bb4;--ok:#10b981;--warn:#f59e0b;--bad:#ef4444}
html,body{height:100%}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--txt);overflow-x:hidden;-webkit-font-smoothing:antialiased}
body::before{content:'';position:fixed;inset:0;z-index:-2;background:
radial-gradient(1000px 600px at 10% -10%,rgba(59,130,246,.18),transparent 60%),
radial-gradient(900px 600px at 110% 10%,rgba(139,92,246,.16),transparent 60%),
radial-gradient(800px 500px at 50% 120%,rgba(6,182,212,.12),transparent 60%),
linear-gradient(180deg,#05070d,#070a12 40%,#05070d)}
body::after{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.35;
background-image:linear-gradient(rgba(80,120,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(80,120,255,.05) 1px,transparent 1px);
background-size:44px 44px;mask-image:radial-gradient(ellipse at center,#000 30%,transparent 80%)}
::-webkit-scrollbar{width:9px;height:9px}::-webkit-scrollbar-thumb{background:linear-gradient(#3b82f6,#8b5cf6);border-radius:10px}
#login{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;perspective:1400px}
.login-card{width:100%;max-width:440px;background:var(--card);border:1px solid var(--border);border-radius:24px;padding:44px 34px;backdrop-filter:blur(24px);box-shadow:0 40px 100px rgba(0,0,0,.7),0 0 30px rgba(59,130,246,.35);animation:floatIn .9s cubic-bezier(.2,.8,.2,1);position:relative;overflow:hidden}
.login-card::before{content:'';position:absolute;inset:-2px;border-radius:26px;padding:2px;background:linear-gradient(135deg,#3b82f6,#8b5cf6,#06b6d4,#3b82f6);background-size:300% 300%;-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;animation:borderMove 6s linear infinite;z-index:-1}
@keyframes borderMove{0%{background-position:0% 50%}100%{background-position:300% 50%}}
@keyframes floatIn{from{opacity:0;transform:translateY(40px) rotateX(12deg)}to{opacity:1;transform:none}}
.logo-3d{width:82px;height:82px;margin:0 auto 18px;border-radius:22px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;font-size:38px;box-shadow:0 20px 50px rgba(59,130,246,.55),inset 0 -6px 20px rgba(0,0,0,.4);animation:spin3d 8s ease-in-out infinite}
@keyframes spin3d{0%,100%{transform:rotateY(0) rotateX(0)}50%{transform:rotateY(180deg) rotateX(8deg)}}
.login-card h1{text-align:center;font-size:24px;font-weight:900;letter-spacing:2px;background:linear-gradient(90deg,#60a5fa,#a78bfa,#22d3ee);-webkit-background-clip:text;background-clip:text;color:transparent}
.login-card p.sub{text-align:center;color:var(--mut);font-size:12px;margin-top:6px;letter-spacing:2px;text-transform:uppercase}
.field{margin-top:18px}.field label{display:block;font-size:11px;font-weight:700;color:var(--mut);letter-spacing:1.5px;margin-bottom:7px;text-transform:uppercase}
.field input{width:100%;padding:14px 16px;border-radius:12px;border:1px solid var(--border);background:rgba(5,10,20,.7);color:var(--txt);font-size:14px;outline:none;transition:.25s}
.field input:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(59,130,246,.18),0 0 24px rgba(59,130,246,.25)}
.btn{cursor:pointer;border:none;border-radius:12px;padding:14px 20px;font-weight:800;font-size:14px;letter-spacing:.5px;transition:.25s;display:inline-flex;align-items:center;justify-content:center;gap:8px;font-family:'Inter',sans-serif}
.btn-primary{background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;width:100%;margin-top:24px;box-shadow:0 14px 34px rgba(59,130,246,.45)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 20px 44px rgba(139,92,246,.6)}
.btn-ghost{background:rgba(255,255,255,.05);color:var(--txt);border:1px solid var(--border)}
.btn-ghost:hover{background:rgba(255,255,255,.1)}
.btn-danger{background:linear-gradient(135deg,#ef4444,#b91c1c);color:#fff}
.btn-warn{background:linear-gradient(135deg,#f59e0b,#d97706);color:#111}
.btn-ok{background:linear-gradient(135deg,#10b981,#059669);color:#fff}
.btn-sm{padding:8px 12px;font-size:12px;border-radius:9px}
.err{color:#fca5a5;font-size:12px;margin-top:14px;text-align:center;min-height:16px}
#app{display:none;min-height:100vh}#app.on{display:block}
.topbar{position:sticky;top:0;z-index:60;display:flex;align-items:center;gap:14px;padding:14px 20px;background:rgba(6,9,17,.82);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
.burger{width:42px;height:42px;border-radius:12px;background:rgba(255,255,255,.05);border:1px solid var(--border);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;cursor:pointer;transition:.25s;flex-shrink:0}
.burger:hover{background:rgba(59,130,246,.18);border-color:var(--accent)}
.burger span{display:block;width:18px;height:2px;background:var(--txt);border-radius:2px;transition:.3s}
.burger.x span:nth-child(1){transform:translateY(6px) rotate(45deg)}
.burger.x span:nth-child(2){opacity:0}
.burger.x span:nth-child(3){transform:translateY(-6px) rotate(-45deg)}
.topbar .brand{font-weight:900;letter-spacing:2px;font-size:15px;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}
.topbar .spacer{flex:1}
.pill{padding:6px 12px;border-radius:999px;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.35);color:#6ee7b7;font-size:11px;font-weight:700;letter-spacing:1px}
.sidebar{position:fixed;top:0;left:0;height:100vh;width:270px;z-index:80;background:rgba(8,12,22,.96);backdrop-filter:blur(24px);border-right:1px solid var(--border);padding:20px 14px;overflow-y:auto;transform:translateX(-100%);transition:transform .35s cubic-bezier(.2,.8,.2,1);box-shadow:20px 0 60px rgba(0,0,0,.6)}
.sidebar.open{transform:translateX(0)}
.sb-brand{display:flex;align-items:center;gap:12px;padding:6px 8px 20px;border-bottom:1px solid var(--border);margin-bottom:16px}
.sb-logo{width:44px;height:44px;border-radius:13px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:0 10px 26px rgba(59,130,246,.5)}
.sb-brand h3{font-size:14px;font-weight:900;letter-spacing:2px;background:linear-gradient(90deg,#60a5fa,#a78bfa);-webkit-background-clip:text;background-clip:text;color:transparent}
.sb-brand small{display:block;color:var(--mut);font-size:10px;letter-spacing:1px;margin-top:2px}
.nav-item{display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:12px;cursor:pointer;color:var(--mut);font-size:13.5px;font-weight:600;transition:.22s;margin-bottom:3px;border:1px solid transparent}
.nav-item:hover{background:rgba(59,130,246,.1);color:var(--txt);transform:translateX(3px)}
.nav-item.active{background:linear-gradient(90deg,rgba(59,130,246,.24),rgba(139,92,246,.14));color:#fff;border-color:rgba(59,130,246,.4);box-shadow:0 8px 24px rgba(59,130,246,.22)}
.nav-item .ic{font-size:17px;width:22px;text-align:center}
.sb-foot{position:absolute;bottom:14px;left:14px;right:14px;color:var(--mut);font-size:10px;text-align:center;padding-top:14px;border-top:1px solid var(--border);letter-spacing:1px}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:70;opacity:0;pointer-events:none;transition:.3s}
.overlay.on{opacity:1;pointer-events:auto}
.main{padding:22px 20px 80px;max-width:1500px;margin:0 auto}
.page{display:none;animation:fadeUp .4s ease}.page.on{display:block}
@keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.page-head{margin-bottom:22px}.page-head h2{font-size:26px;font-weight:900;letter-spacing:-.5px}
.page-head p{color:var(--mut);font-size:13px;margin-top:5px}
.grid{display:grid;gap:16px}.g4{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}.g2{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:20px;backdrop-filter:blur(20px);box-shadow:0 20px 50px rgba(0,0,0,.45);position:relative;overflow:hidden;transition:.3s}
.card:hover{border-color:rgba(59,130,246,.45);transform:translateY(-3px);box-shadow:0 28px 60px rgba(0,0,0,.55),0 0 40px rgba(59,130,246,.12)}
.card::after{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#3b82f6,#8b5cf6,transparent);opacity:.7}
.stat-label{color:var(--mut);font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}
.stat-value{font-size:30px;font-weight:900;margin-top:8px;letter-spacing:-1px}
.stat-sub{color:var(--mut);font-size:11px;margin-top:6px}
.c-blue{color:#60a5fa}.c-purple{color:#a78bfa}.c-cyan{color:#22d3ee}.c-green{color:#34d399}.c-amber{color:#fbbf24}
.tbl-wrap{overflow-x:auto;border-radius:16px;border:1px solid var(--border);background:rgba(8,12,22,.5)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:760px}
th{text-align:left;padding:14px;background:rgba(59,130,246,.08);color:#9db4d6;font-size:10.5px;letter-spacing:1.4px;text-transform:uppercase;font-weight:800;border-bottom:1px solid var(--border);white-space:nowrap}
td{padding:13px 14px;border-bottom:1px solid rgba(80,120,255,.08);vertical-align:middle}
tr:last-child td{border-bottom:none}tr:hover td{background:rgba(59,130,246,.05)}
.mono{font-family:'JetBrains Mono',monospace;font-size:11.5px}
.key-chip{background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.35);color:#93c5fd;padding:5px 9px;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:10.5px;cursor:pointer;transition:.2s;display:inline-block;word-break:break-all}
.key-chip:hover{background:rgba(59,130,246,.25)}
.badge{padding:4px 10px;border-radius:999px;font-size:10px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;display:inline-block}
.b-ok{background:rgba(16,185,129,.15);color:#6ee7b7;border:1px solid rgba(16,185,129,.4)}
.b-bad{background:rgba(239,68,68,.15);color:#fca5a5;border:1px solid rgba(239,68,68,.4)}
.b-warn{background:rgba(245,158,11,.15);color:#fcd34d;border:1px solid rgba(245,158,11,.4)}
.b-info{background:rgba(59,130,246,.15);color:#93c5fd;border:1px solid rgba(59,130,246,.4)}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.inp,select,textarea{width:100%;padding:12px 14px;border-radius:11px;border:1px solid var(--border);background:rgba(5,10,20,.75);color:var(--txt);font-size:13.5px;outline:none;transition:.22s;font-family:'Inter',sans-serif}
.inp:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(59,130,246,.15)}
label.lbl{display:block;font-size:11px;font-weight:800;color:var(--mut);letter-spacing:1.4px;text-transform:uppercase;margin-bottom:7px}
.tools-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin-top:6px}
.tool-tile{display:flex;align-items:center;gap:10px;padding:11px 13px;border-radius:12px;border:1px solid var(--border);background:rgba(5,10,20,.6);cursor:pointer;transition:.2s;user-select:none}
.tool-tile:hover{border-color:var(--accent);background:rgba(59,130,246,.08)}
.tool-tile.on{border-color:var(--accent);background:linear-gradient(135deg,rgba(59,130,246,.22),rgba(139,92,246,.12));box-shadow:0 0 20px rgba(59,130,246,.25)}
.tool-tile .ic{font-size:17px}.tool-tile .nm{font-size:12px;font-weight:700}
.tool-tile .ck{margin-left:auto;width:18px;height:18px;border-radius:6px;border:1.5px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:11px;color:transparent;transition:.2s}
.tool-tile.on .ck{background:var(--accent);border-color:var(--accent);color:#fff}
.modal{position:fixed;inset:0;z-index:200;display:none;align-items:center;justify-content:center;padding:18px;background:rgba(0,0,0,.75);backdrop-filter:blur(6px)}
.modal.on{display:flex}
.modal-box{width:100%;max-width:560px;max-height:90vh;overflow-y:auto;background:rgba(12,17,30,.98);border:1px solid var(--border);border-radius:22px;padding:26px;backdrop-filter:blur(24px);box-shadow:0 40px 100px rgba(0,0,0,.8),0 0 60px rgba(59,130,246,.2);animation:pop .3s cubic-bezier(.2,.9,.3,1.2)}
@keyframes pop{from{opacity:0;transform:scale(.94) translateY(20px)}to{opacity:1;transform:none}}
.modal-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}
.modal-head h3{font-size:18px;font-weight:900;letter-spacing:-.3px}
.x-btn{width:34px;height:34px;border-radius:10px;background:rgba(255,255,255,.06);border:1px solid var(--border);color:var(--txt);cursor:pointer;font-size:16px;transition:.2s}
.x-btn:hover{background:rgba(239,68,68,.2);border-color:#ef4444}
#toasts{position:fixed;top:20px;right:20px;z-index:999;display:flex;flex-direction:column;gap:10px}
.toast{padding:13px 18px;border-radius:12px;background:rgba(12,17,30,.97);border:1px solid var(--border);color:var(--txt);font-size:13px;font-weight:600;box-shadow:0 20px 50px rgba(0,0,0,.6);animation:slideIn .3s ease;min-width:240px;max-width:340px}
.toast.ok{border-color:rgba(16,185,129,.5);box-shadow:0 0 30px rgba(16,185,129,.25)}
.toast.err{border-color:rgba(239,68,68,.5);box-shadow:0 0 30px rgba(239,68,68,.25)}
@keyframes slideIn{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:none}}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.mt{margin-top:16px}.mt2{margin-top:24px}
.muted{color:var(--mut);font-size:12px}
.code-box{background:rgba(0,0,0,.5);border:1px solid var(--border);border-radius:12px;padding:14px;font-family:'JetBrains Mono',monospace;font-size:11.5px;color:#93c5fd;word-break:break-all;line-height:1.7}
.chart-wrap{position:relative;height:280px;margin-top:10px}
.empty{text-align:center;padding:50px 20px;color:var(--mut)}.empty .ic{font-size:44px;opacity:.4;margin-bottom:12px}
@media(max-width:640px){.main{padding:16px 13px 90px}.page-head h2{font-size:21px}.stat-value{font-size:24px}.login-card{padding:34px 22px}.topbar{padding:12px 13px}.topbar .brand{font-size:13px;letter-spacing:1px}}
</style>
</head>
<body>

<div id="login">
  <div class="login-card">
    <div class="logo-3d">🛰️</div>
    <h1>VERNEX CONTROL</h1>
    <p class="sub">OSINT API MANAGEMENT</p>
    <div class="field"><label>Username</label><input id="luser" type="text" placeholder="vernex"></div>
    <div class="field"><label>Password</label><input id="lpass" type="password" placeholder="••••••••"></div>
    <button class="btn btn-primary" onclick="doLogin()">⚡ ACCESS CONTROL CENTER</button>
    <div class="err" id="lerr"></div>
    <div style="text-align:center;margin-top:18px;color:var(--mut);font-size:10px;letter-spacing:1.5px">DEVELOPER • SHAYAN_EXPLORER</div>
  </div>
</div>

<div id="app">
  <div class="sidebar" id="sidebar">
    <div class="sb-brand"><div class="sb-logo">🛰️</div><div><h3>VERNEX</h3><small>CONTROL CENTER</small></div></div>
    <div class="nav-item active" data-page="dashboard"><span class="ic">📊</span> Dashboard</div>
    <div class="nav-item" data-page="keys"><span class="ic">🗝️</span> API Keys</div>
    <div class="nav-item" data-page="generate"><span class="ic">➕</span> Generate Key</div>
    <div class="nav-item" data-page="logs"><span class="ic">📜</span> Request Logs</div>
    <div class="nav-item" data-page="tools"><span class="ic">🧰</span> Tools &amp; Endpoints</div>
    <div class="nav-item" data-page="users"><span class="ic">👥</span> Customers</div>
    <div class="nav-item" data-page="bot"><span class="ic">🤖</span> Telegram Bot</div>
    <div class="nav-item" data-page="settings"><span class="ic">⚙️</span> Settings</div>
    <div class="nav-item" onclick="doLogout()" style="color:#fca5a5"><span class="ic">🚪</span> Logout</div>
    <div class="sb-foot">v2.1 • SHAYAN_EXPLORER</div>
  </div>
  <div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
  <div class="topbar">
    <div class="burger" id="burger" onclick="toggleSidebar()"><span></span><span></span><span></span></div>
    <div class="brand">VERNEX • OSINT API</div>
    <div class="spacer"></div><div class="pill">● ONLINE</div>
  </div>
  <div class="main">
    <div class="page on" id="page-dashboard">
      <div class="page-head"><h2>Dashboard</h2><p>Real-time overview of your API infrastructure</p></div>
      <div class="grid g4">
        <div class="card"><div class="stat-label">Total Revenue</div><div class="stat-value c-green" id="s-rev">₹0</div><div class="stat-sub" id="s-rev-sub">All time</div></div>
        <div class="card"><div class="stat-label">Today Revenue</div><div class="stat-value c-amber" id="s-today">₹0</div><div class="stat-sub">Since 00:00 UTC</div></div>
        <div class="card"><div class="stat-label">Total Keys</div><div class="stat-value c-blue" id="s-keys">0</div><div class="stat-sub" id="s-active">0 active</div></div>
        <div class="card"><div class="stat-label">Total Requests</div><div class="stat-value c-purple" id="s-req">0</div><div class="stat-sub">Across all keys</div></div>
      </div>
      <div class="grid g4 mt">
        <div class="card"><div class="stat-label">Last 7 Days</div><div class="stat-value c-cyan" id="s-7">₹0</div></div>
        <div class="card"><div class="stat-label">Last 30 Days</div><div class="stat-value c-cyan" id="s-30">₹0</div></div>
        <div class="card"><div class="stat-label">Last 365 Days</div><div class="stat-value c-cyan" id="s-365">₹0</div></div>
        <div class="card"><div class="stat-label">Active Keys</div><div class="stat-value c-green" id="s-ak">0</div></div>
      </div>
      <div class="card mt2"><div class="stat-label">Revenue • Last 14 Days</div><div class="chart-wrap"><canvas id="revChart"></canvas></div></div>
      <div class="card mt2"><div class="stat-label">Top Tools Used</div><div id="top-tools" class="mt"></div></div>
    </div>
    <div class="page" id="page-keys">
      <div class="page-head"><h2>API Keys</h2><p>Manage, edit, suspend and track all your API keys</p></div>
      <div class="card"><div class="tbl-wrap"><table>
        <thead><tr><th>Name</th><th>Key</th><th>Tools</th><th>Usage</th><th>Devices</th><th>Expiry</th><th>Price</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody id="keys-body"></tbody>
      </table></div></div>
    </div>
    <div class="page" id="page-generate">
      <div class="page-head"><h2>Generate API Key</h2><p>Create a new key with custom permissions, expiry, limits and price</p></div>
      <div class="card">
        <div class="form-grid">
          <div><label class="lbl">Key Name *</label><input class="inp" id="g-name" placeholder="e.g. Rahul Premium"></div>
          <div><label class="lbl">Custom Key (optional)</label><div class="row"><input class="inp" id="g-key" placeholder="Leave empty for random"><button class="btn btn-ghost btn-sm" onclick="randomKey()">🎲</button></div></div>
          <div><label class="lbl">Price (₹)</label><input class="inp" id="g-price" type="number" value="0" min="0" step="0.01"></div>
          <div><label class="lbl">Request Limit (0 = unlimited)</label><input class="inp" id="g-limit" type="number" value="1000" min="0"></div>
          <div><label class="lbl">Device Limit</label><input class="inp" id="g-devices" type="number" value="1" min="1"></div>
          <div><label class="lbl">Expiry Mode</label>
            <select id="g-expmode" class="inp" onchange="expMode()">
              <option value="never">Never Expires</option>
              <option value="preset" selected>Preset Duration</option>
              <option value="custom">Custom Date/Time</option>
            </select>
          </div>
          <div id="g-preset-wrap"><label class="lbl">Duration</label>
            <select id="g-preset" class="inp">
              <option value="1h">1 Hour</option><option value="6h">6 Hours</option><option value="12h">12 Hours</option>
              <option value="1d" selected>1 Day</option><option value="7d">7 Days</option><option value="30d">30 Days</option>
              <option value="90d">90 Days</option><option value="365d">365 Days</option>
            </select>
          </div>
          <div id="g-custom-wrap" style="display:none"><label class="lbl">Expiry Date &amp; Time</label><input class="inp" id="g-datetime" type="datetime-local"></div>
        </div>
        <div class="mt2">
          <div class="row" style="justify-content:space-between">
            <label class="lbl" style="margin:0">Allowed Tools</label>
            <button class="btn btn-ghost btn-sm" onclick="toggleAllTools()" id="selAllBtn">✅ Select All</button>
          </div>
          <div class="tools-grid" id="tools-grid"></div>
        </div>
        <div class="mt2 row">
          <button class="btn btn-primary" style="width:auto;margin:0;padding:14px 34px" onclick="createKey()">🚀 GENERATE KEY</button>
          <button class="btn btn-ghost" onclick="resetForm()">↺ Reset</button>
        </div>
      </div>
    </div>
    <div class="page" id="page-logs">
      <div class="page-head"><h2>Request Logs</h2><p>Every API request made with your keys</p></div>
      <div class="card">
        <div class="row" style="margin-bottom:14px">
          <input class="inp" id="log-filter" placeholder="Filter by key value..." style="max-width:320px">
          <button class="btn btn-ghost btn-sm" onclick="loadLogs()">🔍 Search</button>
          <button class="btn btn-ghost btn-sm" onclick="document.getElementById('log-filter').value='';loadLogs()">Clear</button>
        </div>
        <div class="tbl-wrap"><table>
          <thead><tr><th>Time</th><th>Key Name</th><th>Key</th><th>Tool</th><th>Input</th><th>IP</th><th>Status</th></tr></thead>
          <tbody id="logs-body"></tbody>
        </table></div>
      </div>
    </div>
    <div class="page" id="page-tools">
      <div class="page-head"><h2>Tools &amp; Endpoints</h2><p>All available endpoints — call them with your API key</p></div>
      <div class="card"><div class="muted">Base URL: <span class="mono" id="base-url"></span> &nbsp;•&nbsp; Add <span class="mono">?key=YOUR_KEY&amp;&lt;param&gt;=VALUE</span></div></div>
      <div class="grid g3 mt" id="tools-list"></div>
    </div>
    <div class="page" id="page-users">
      <div class="page-head"><h2>Customers</h2><p>Customer logins created via Telegram bot or manually</p></div>
      <div class="card"><div class="tbl-wrap"><table>
        <thead><tr><th>Username</th><th>Device Limit</th><th>API Key</th><th>Active</th><th>Created</th><th></th></tr></thead>
        <tbody id="users-body"></tbody>
      </table></div></div>
    </div>
    <div class="page" id="page-bot">
      <div class="page-head"><h2>Telegram Bot</h2><p>Control your API from Telegram — generate customer logins instantly</p></div>
      <div class="grid g2">
        <div class="card">
          <div class="stat-label">Bot Configuration</div>
          <div class="mt"><label class="lbl">Bot Token (from @BotFather)</label><input class="inp" id="bot-token" placeholder="123456:ABC-DEF..."></div>
          <div class="mt"><label class="lbl">Bot Enabled</label>
            <select class="inp" id="bot-enabled"><option value="0">Disabled</option><option value="1">Enabled</option></select>
          </div>
          <div class="mt"><label class="lbl">Admin Chat ID (auto-set on first /start)</label><input class="inp" id="bot-admin-chat" placeholder="Auto"></div>
          <button class="btn btn-primary mt" onclick="saveBot()">💾 SAVE BOT SETTINGS</button>
        </div>
        <div class="card">
          <div class="stat-label">Bot Commands</div>
          <div class="code-box mt">
/loginkey &lt;username&gt; &lt;password&gt; &lt;devices&gt;
   → creates website login + API key
/generate &lt;username&gt; &lt;password&gt; &lt;devices&gt;
   → same as /loginkey
/newkey &lt;name&gt; &lt;days&gt; &lt;limit&gt; &lt;price&gt;
   → creates API key only
/keys — list recent keys
/stats — quick statistics
          </div>
          <div class="muted mt">⚡ First person to send <b>/start</b> becomes bot admin.</div>
        </div>
      </div>
    </div>
    <div class="page" id="page-settings">
      <div class="page-head"><h2>Settings</h2><p>Configure upstream API key and system options</p></div>
      <div class="card">
        <div class="stat-label">Upstream API Key</div>
        <div class="muted" style="margin:8px 0 12px">This is the master key used to call ft-osint-api.duckdns.org</div>
        <input class="inp" id="set-upstream" placeholder="ftgamer2">
        <button class="btn btn-primary mt" onclick="saveSettings()">💾 SAVE SETTINGS</button>
      </div>
      <div class="card mt2"><div class="stat-label">System Info</div><div class="mt mono muted" id="sys-info"></div></div>
    </div>
  </div>
</div>

<div class="modal" id="editModal">
  <div class="modal-box">
    <div class="modal-head"><h3>✏️ Edit Key</h3><button class="x-btn" onclick="closeEdit()">✕</button></div>
    <input type="hidden" id="e-id">
    <div class="form-grid">
      <div><label class="lbl">Name</label><input class="inp" id="e-name"></div>
      <div><label class="lbl">Price (₹)</label><input class="inp" id="e-price" type="number" step="0.01"></div>
      <div><label class="lbl">Request Limit</label><input class="inp" id="e-limit" type="number"></div>
      <div><label class="lbl">Device Limit</label><input class="inp" id="e-devices" type="number" min="1"></div>
      <div><label class="lbl">Expiry (datetime)</label><input class="inp" id="e-exp" type="datetime-local"></div>
    </div>
    <div class="mt">
      <div class="row" style="justify-content:space-between">
        <label class="lbl" style="margin:0">Allowed Tools</label>
        <button class="btn btn-ghost btn-sm" onclick="toggleAllEditTools()" id="eSelAll">✅ Select All</button>
      </div>
      <div class="tools-grid" id="edit-tools-grid"></div>
    </div>
    <div class="mt row">
      <button class="btn btn-primary" style="width:auto;margin:0;padding:12px 28px" onclick="saveEdit()">💾 SAVE CHANGES</button>
      <button class="btn btn-ghost" onclick="closeEdit()">Cancel</button>
    </div>
  </div>
</div>

<div id="toasts"></div>

<script>
let ALL_TOOLS = {};
let SELECTED = new Set();
let EDIT_SELECTED = new Set();
let revChartObj = null;
let CURRENT_KEYS = [];

function $(id){ return document.getElementById(id); }
function toast(msg, type){
  const t = document.createElement('div');
  t.className = 'toast ' + (type || '');
  t.textContent = msg;
  $('toasts').appendChild(t);
  setTimeout(()=>{ t.style.opacity='0'; t.style.transform='translateX(40px)'; setTimeout(()=>t.remove(),300); }, 3200);
}
function fmtMoney(n){ return '₹' + Number(n||0).toLocaleString('en-IN',{maximumFractionDigits:2}); }
function fmtDate(s){ if(!s) return '—'; try{ return new Date(s).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'}); }catch(e){ return s; } }
function copyText(t){ navigator.clipboard.writeText(t).then(()=>toast('Copied!','ok')); }
async function api(url, opts){
  const r = await fetch(url, Object.assign({headers:{'Content-Type':'application/json'}}, opts||{}));
  let j = {};
  try{ j = await r.json(); }catch(e){}
  if(!r.ok && !j.error){ j.error = 'HTTP ' + r.status; }
  return j;
}
function esc(s){ return String(s||'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

async function doLogin(){
  const u = $('luser').value.trim();
  const p = $('lpass').value;
  $('lerr').textContent = '';
  const r = await api('/api/admin/login', {method:'POST', body:JSON.stringify({username:u,password:p})});
  if(r.ok){ showApp(); } else { $('lerr').textContent = r.error || 'Login failed'; }
}
async function doLogout(){ await api('/api/admin/logout', {method:'POST'}); location.reload(); }
$('lpass').addEventListener('keydown', e=>{ if(e.key==='Enter') doLogin(); });

async function showApp(){
  $('login').style.display = 'none';
  $('app').classList.add('on');
  await loadTools();
  await loadDashboard();
  await loadKeys();
  await loadLogs();
  await loadUsers();
  await loadSettings();
  $('base-url').textContent = location.origin + '/api/{tool}?key=YOUR_KEY';
}
(async function(){ const r = await api('/api/admin/check'); if(r.admin){ showApp(); } })();

function toggleSidebar(){
  $('sidebar').classList.toggle('open');
  $('overlay').classList.toggle('on');
  $('burger').classList.toggle('x');
}
document.querySelectorAll('.nav-item[data-page]').forEach(el=>{
  el.addEventListener('click', ()=>{
    document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'));
    el.classList.add('active');
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));
    $('page-' + el.dataset.page).classList.add('on');
    if(window.innerWidth < 900) toggleSidebar();
    if(el.dataset.page === 'dashboard') loadDashboard();
    if(el.dataset.page === 'keys') loadKeys();
    if(el.dataset.page === 'logs') loadLogs();
    if(el.dataset.page === 'users') loadUsers();
  });
});

async function loadTools(){
  const r = await api('/api/admin/stats');
  if(r.ok && r.tools){ ALL_TOOLS = r.tools; renderToolsGrid(); renderToolsList(); }
}
function renderToolsGrid(){
  const grid = $('tools-grid'); grid.innerHTML = '';
  Object.entries(ALL_TOOLS).forEach(([id,t])=>{
    const d = document.createElement('div');
    d.className = 'tool-tile'; d.dataset.id = id;
    d.innerHTML = `<span class="ic">${t.icon}</span><span class="nm">${t.label}</span><span class="ck">✓</span>`;
    d.onclick = ()=>{ if(SELECTED.has(id)){ SELECTED.delete(id); d.classList.remove('on'); } else { SELECTED.add(id); d.classList.add('on'); } };
    grid.appendChild(d);
  });
}
function renderToolsList(){
  const wrap = $('tools-list'); wrap.innerHTML = '';
  Object.entries(ALL_TOOLS).forEach(([id,t])=>{
    const url = location.origin + '/api/' + id + '?key=YOUR_KEY&' + t.param + '=VALUE';
    const d = document.createElement('div');
    d.className = 'card';
    d.innerHTML = `<div style="display:flex;align-items:center;gap:10px"><span style="font-size:24px">${t.icon}</span>
      <div><div style="font-weight:800">${t.label}</div><div class="muted mono" style="font-size:10.5px">/api/${id}</div></div></div>
      <div class="code-box" style="margin-top:12px;font-size:10.5px">${url}</div>
      <button class="btn btn-ghost btn-sm mt" onclick="copyText('${url}')">📋 Copy URL</button>`;
    wrap.appendChild(d);
  });
}
function toggleAllTools(){
  const allOn = SELECTED.size === Object.keys(ALL_TOOLS).length;
  SELECTED.clear();
  document.querySelectorAll('#tools-grid .tool-tile').forEach(el=>{
    if(allOn){ el.classList.remove('on'); } else { el.classList.add('on'); SELECTED.add(el.dataset.id); }
  });
  $('selAllBtn').textContent = allOn ? '✅ Select All' : '❌ Deselect All';
}
function toggleAllEditTools(){
  const allOn = EDIT_SELECTED.size === Object.keys(ALL_TOOLS).length;
  EDIT_SELECTED.clear();
  document.querySelectorAll('#edit-tools-grid .tool-tile').forEach(el=>{
    if(allOn){ el.classList.remove('on'); } else { el.classList.add('on'); EDIT_SELECTED.add(el.dataset.id); }
  });
  $('eSelAll').textContent = allOn ? '✅ Select All' : '❌ Deselect All';
}

async function loadDashboard(){
  const r = await api('/api/admin/stats');
  if(!r.ok) return;
  $('s-rev').textContent = fmtMoney(r.total_revenue);
  $('s-today').textContent = fmtMoney(r.today_revenue);
  $('s-keys').textContent = r.total_keys;
  $('s-active').textContent = r.active_keys + ' active';
  $('s-req').textContent = Number(r.total_requests).toLocaleString();
  $('s-7').textContent = fmtMoney(r.revenue_7);
  $('s-30').textContent = fmtMoney(r.revenue_30);
  $('s-365').textContent = fmtMoney(r.revenue_365);
  $('s-ak').textContent = r.active_keys;
  const tt = $('top-tools');
  if(!r.top_tools || !r.top_tools.length){ tt.innerHTML = '<div class="muted">No requests yet.</div>'; }
  else {
    const max = Math.max(...r.top_tools.map(x=>x.count));
    tt.innerHTML = r.top_tools.map(x=>{
      const t = ALL_TOOLS[x.tool] || {label:x.tool, icon:'🔧'};
      const pct = Math.round((x.count/max)*100);
      return `<div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px">
        <span>${t.icon} ${t.label}</span><span class="muted">${x.count}</span></div>
        <div style="height:8px;border-radius:8px;background:rgba(255,255,255,.06);overflow:hidden">
        <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,#3b82f6,#8b5cf6);border-radius:8px;transition:.5s"></div></div></div>`;
    }).join('');
  }
  const ctx = $('revChart').getContext('2d');
  if(revChartObj) revChartObj.destroy();
  const grad = ctx.createLinearGradient(0,0,0,280);
  grad.addColorStop(0,'rgba(59,130,246,.55)'); grad.addColorStop(1,'rgba(59,130,246,0)');
  revChartObj = new Chart(ctx, {
    type:'line',
    data:{ labels:r.chart.map(x=>x.day), datasets:[{ label:'Revenue (₹)', data:r.chart.map(x=>x.value),
      borderColor:'#60a5fa', backgroundColor:grad, borderWidth:2.5, fill:true, tension:.4,
      pointBackgroundColor:'#8b5cf6', pointBorderColor:'#fff', pointRadius:4, pointHoverRadius:7 }]},
    options:{ responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
      scales:{ x:{grid:{color:'rgba(80,120,255,.08)'},ticks:{color:'#8b9bb4',font:{size:10}}},
              y:{grid:{color:'rgba(80,120,255,.08)'},ticks:{color:'#8b9bb4',font:{size:10}},beginAtZero:true}}}
  });
}

async function loadKeys(){
  const r = await api('/api/admin/keys');
  if(!r.ok) return;
  CURRENT_KEYS = r.keys;
  const body = $('keys-body');
  if(!r.keys.length){ body.innerHTML = '<tr><td colspan="9"><div class="empty"><div class="ic">🗝️</div>No API keys yet. Generate one!</div></td></tr>'; return; }
  body.innerHTML = r.keys.map(k=>{
    const tools = k.tools === 'all' ? '<span class="badge b-info">ALL TOOLS</span>' : `<span class="muted" style="font-size:11px">${k.tools.length} tools</span>`;
    const usage = k.request_limit ? `${k.request_used}/${k.request_limit}` : `${k.request_used}/∞`;
    const exp = k.expires_at ? (k.expired ? `<span class="badge b-bad">EXPIRED</span>` : fmtDate(k.expires_at)) : '<span class="badge b-ok">NEVER</span>';
    const st = k.suspended ? '<span class="badge b-warn">SUSPENDED</span>' : '<span class="badge b-ok">ACTIVE</span>';
    return `<tr>
      <td><b>${esc(k.name)}</b></td>
      <td><span class="key-chip" onclick="copyText('${k.key_value}')">${k.key_value}</span></td>
      <td>${tools}</td><td class="mono">${usage}</td>
      <td class="mono">${(k.devices||[]).length}/${k.device_limit}</td>
      <td style="font-size:11px">${exp}</td>
      <td class="mono c-green">${fmtMoney(k.price)}</td>
      <td>${st}</td>
      <td><div class="row" style="gap:5px">
        <button class="btn btn-ghost btn-sm" onclick="openEdit(${k.id})">✏️</button>
        <button class="btn btn-ghost btn-sm" onclick="restartKey(${k.id})" title="Reset request count">🔄</button>
        <button class="btn ${k.suspended?'btn-ok':'btn-warn'} btn-sm" onclick="suspendKey(${k.id})">${k.suspended?'▶':'⏸'}</button>
        <button class="btn btn-danger btn-sm" onclick="deleteKey(${k.id})">🗑</button>
      </div></td></tr>`;
  }).join('');
}
async function restartKey(id){ if(!confirm('Reset request count to 0?')) return;
  const r = await api('/api/admin/keys/'+id+'/restart', {method:'POST'});
  if(r.ok){ toast('Request counter reset','ok'); loadKeys(); } else toast(r.error||'Failed','err'); }
async function suspendKey(id){
  const r = await api('/api/admin/keys/'+id+'/suspend', {method:'POST'});
  if(r.ok){ toast(r.suspended?'Key suspended':'Key activated','ok'); loadKeys(); } else toast(r.error||'Failed','err'); }
async function deleteKey(id){ if(!confirm('Permanently delete this key?')) return;
  const r = await api('/api/admin/keys/'+id, {method:'DELETE'});
  if(r.ok){ toast('Key deleted','ok'); loadKeys(); loadDashboard(); } else toast(r.error||'Failed','err'); }

function randomKey(){
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let s = 'VX-';
  for(let i=0;i<4;i++){ let part=''; for(let j=0;j<5;j++) part += chars[Math.floor(Math.random()*chars.length)];
    s += part + (i<3?'-':''); }
  $('g-key').value = s;
}
function expMode(){
  const m = $('g-expmode').value;
  $('g-preset-wrap').style.display = m==='preset' ? '' : 'none';
  $('g-custom-wrap').style.display = m==='custom' ? '' : 'none';
}
function computeExpiry(){
  const m = $('g-expmode').value;
  if(m === 'never') return null;
  if(m === 'custom'){ const v = $('g-datetime').value; if(!v) return null; return new Date(v).toISOString(); }
  const dur = $('g-preset').value;
  const map = {'1h':1/24,'6h':6/24,'12h':12/24,'1d':1,'7d':7,'30d':30,'90d':90,'365d':365};
  return new Date(Date.now() + (map[dur]||1)*86400000).toISOString();
}
function resetForm(){
  $('g-name').value = ''; $('g-key').value = ''; $('g-price').value = 0;
  $('g-limit').value = 1000; $('g-devices').value = 1;
  $('g-expmode').value = 'preset'; expMode();
  SELECTED.clear();
  document.querySelectorAll('#tools-grid .tool-tile').forEach(el=>el.classList.remove('on'));
  $('selAllBtn').textContent = '✅ Select All';
}
async function createKey(){
  const name = $('g-name').value.trim();
  if(!name){ toast('Key name is required','err'); return; }
  const tools = SELECTED.size === Object.keys(ALL_TOOLS).length ? 'all' : Array.from(SELECTED);
  if(tools !== 'all' && tools.length === 0){ toast('Select at least one tool','err'); return; }
  const payload = { name, key_value: $('g-key').value.trim(),
    price: parseFloat($('g-price').value) || 0,
    request_limit: parseInt($('g-limit').value) || 0,
    device_limit: parseInt($('g-devices').value) || 1,
    expires_at: computeExpiry(), tools };
  const r = await api('/api/admin/keys', {method:'POST', body: JSON.stringify(payload)});
  if(r.ok){
    toast('Key generated: ' + r.key, 'ok');
    resetForm();
    document.querySelectorAll('.nav-item').forEach(x=>x.classList.remove('active'));
    document.querySelector('.nav-item[data-page="keys"]').classList.add('active');
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));
    $('page-keys').classList.add('on');
    loadKeys(); loadDashboard();
  } else toast(r.error || 'Failed to create key','err');
}

function openEdit(id){
  const k = CURRENT_KEYS.find(x=>x.id === id); if(!k) return;
  $('e-id').value = k.id; $('e-name').value = k.name;
  $('e-price').value = k.price; $('e-limit').value = k.request_limit;
  $('e-devices').value = k.device_limit;
  if(k.expires_at){ const d = new Date(k.expires_at); const pad = n => String(n).padStart(2,'0');
    $('e-exp').value = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`; }
  else { $('e-exp').value = ''; }
  EDIT_SELECTED = new Set(k.tools === 'all' ? Object.keys(ALL_TOOLS) : k.tools);
  const grid = $('edit-tools-grid'); grid.innerHTML = '';
  Object.entries(ALL_TOOLS).forEach(([tid,t])=>{
    const d = document.createElement('div');
    d.className = 'tool-tile' + (EDIT_SELECTED.has(tid) ? ' on' : ''); d.dataset.id = tid;
    d.innerHTML = `<span class="ic">${t.icon}</span><span class="nm">${t.label}</span><span class="ck">✓</span>`;
    d.onclick = ()=>{ if(EDIT_SELECTED.has(tid)){ EDIT_SELECTED.delete(tid); d.classList.remove('on'); }
      else { EDIT_SELECTED.add(tid); d.classList.add('on'); } };
    grid.appendChild(d);
  });
  $('eSelAll').textContent = EDIT_SELECTED.size === Object.keys(ALL_TOOLS).length ? '❌ Deselect All' : '✅ Select All';
  $('editModal').classList.add('on');
}
function closeEdit(){ $('editModal').classList.remove('on'); }
async function saveEdit(){
  const id = $('e-id').value;
  const tools = EDIT_SELECTED.size === Object.keys(ALL_TOOLS).length ? 'all' : Array.from(EDIT_SELECTED);
  const exp = $('e-exp').value ? new Date($('e-exp').value).toISOString() : null;
  const payload = { name: $('e-name').value.trim(), price: parseFloat($('e-price').value) || 0,
    request_limit: parseInt($('e-limit').value) || 0, device_limit: parseInt($('e-devices').value) || 1,
    expires_at: exp, tools };
  const r = await api('/api/admin/keys/'+id, {method:'PUT', body: JSON.stringify(payload)});
  if(r.ok){ toast('Key updated','ok'); closeEdit(); loadKeys(); } else toast(r.error||'Failed','err');
}

async function loadLogs(){
  const f = $('log-filter').value.trim();
  const r = await api('/api/admin/logs?limit=300' + (f ? '&key=' + encodeURIComponent(f) : ''));
  if(!r.ok) return;
  const body = $('logs-body');
  if(!r.logs.length){ body.innerHTML = '<tr><td colspan="7"><div class="empty"><div class="ic">📜</div>No logs yet</div></td></tr>'; return; }
  body.innerHTML = r.logs.map(l=>{
    const map = {ok:'b-ok', invalid_key:'b-bad', expired:'b-bad', suspended:'b-warn', limit_reached:'b-warn',
      device_limit:'b-warn', tool_denied:'b-warn'};
    const st = `<span class="badge ${map[l.status]||'b-info'}">${esc((l.status||'').toUpperCase())}</span>`;
    return `<tr>
      <td style="font-size:11px" class="mono">${fmtDate(l.ts)}</td>
      <td>${esc(l.key_name)}</td>
      <td><span class="mono" style="font-size:10.5px;color:#93c5fd">${(l.key_value||'').slice(0,18)}…</span></td>
      <td><b>${esc(l.tool)}</b></td>
      <td class="mono" style="font-size:11px">${esc((l.input||'').slice(0,32))}</td>
      <td class="mono" style="font-size:10.5px">${esc(l.ip||'')}</td>
      <td>${st}</td></tr>`;
  }).join('');
}

async function loadUsers(){
  const r = await api('/api/admin/users');
  if(!r.ok) return;
  const body = $('users-body');
  if(!r.users.length){ body.innerHTML = '<tr><td colspan="6"><div class="empty"><div class="ic">👥</div>No customers yet</div></td></tr>'; return; }
  body.innerHTML = r.users.map(u=>`<tr>
    <td><b>${esc(u.username)}</b></td>
    <td class="mono">${u.device_limit}</td>
    <td><span class="key-chip" onclick="copyText('${u.api_key||''}')">${(u.api_key||'—').slice(0,22)}…</span></td>
    <td>${u.active ? '<span class="badge b-ok">ACTIVE</span>' : '<span class="badge b-bad">OFF</span>'}</td>
    <td style="font-size:11px">${fmtDate(u.created_at)}</td>
    <td><button class="btn btn-danger btn-sm" onclick="delUser(${u.id})">🗑</button></td></tr>`).join('');
}
async function delUser(id){ if(!confirm('Delete this customer?')) return;
  const r = await api('/api/admin/users/'+id, {method:'DELETE'});
  if(r.ok){ toast('Customer deleted','ok'); loadUsers(); } else toast(r.error||'Failed','err'); }

async function loadSettings(){
  const r = await api('/api/admin/settings');
  if(!r.ok) return;
  $('set-upstream').value = r.settings.upstream_key || '';
  $('bot-token').value = r.settings.bot_token || '';
  $('bot-enabled').value = r.settings.bot_enabled || '0';
  $('bot-admin-chat').value = r.settings.bot_admin_chat || '';
}
async function saveSettings(){
  const r = await api('/api/admin/settings', {method:'POST', body: JSON.stringify({upstream_key: $('set-upstream').value.trim()})});
  if(r.ok) toast('Settings saved','ok'); else toast(r.error||'Failed','err');
}
async function saveBot(){
  const r = await api('/api/admin/settings', {method:'POST', body: JSON.stringify({
    bot_token: $('bot-token').value.trim(),
    bot_enabled: $('bot-enabled').value,
    bot_admin_chat: $('bot-admin-chat').value.trim()})});
  if(r.ok) toast('Bot settings saved','ok'); else toast(r.error||'Failed','err');
}

expMode();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------
# HTML ROUTE
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return HTML

# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=bot_loop, daemon=True)
    t.start()
    print("=" * 60)
    print("  VERNEX OSINT API CONTROL CENTER")
    print("  Developer: SHAYAN_EXPLORER")
    print("=" * 60)
    print(f"  Admin URL : http://127.0.0.1:5000")
    print(f"  Username  : {ADMIN_USER}")
    print(f"  Password  : {ADMIN_PASS}")
    print(f"  Proxy     : http://127.0.0.1:5000/api/<tool>?key=YOUR_KEY")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
