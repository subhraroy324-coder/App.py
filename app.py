# ============================================================
#  SHAYAN_EXPLORER · OSINT API CONTROL CENTER (v4)
#  Fixes: expiry, contact info, premium UI, loading states
# ============================================================

import os, sqlite3, secrets, requests
from datetime import datetime, timezone, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, session, redirect, Response

# ----------------------------- CONFIG -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))

def _resolve_db_path():
    env_path = os.environ.get("DB_PATH")
    if env_path: return env_path
    if os.path.isdir("/data"): return "/data/osint.db"
    if os.environ.get("VERCEL"): return "/tmp/osint.db"
    return os.path.join(APP_DIR, "osint.db")

DB_PATH = _resolve_db_path()
try:
    d = os.path.dirname(DB_PATH)
    if d: os.makedirs(d, exist_ok=True)
except Exception: pass

ADMIN_USER = os.environ.get("ADMIN_USER", "vernex")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "vernex@16vx")
SECRET_KEY = os.environ.get("SECRET_KEY", "shayan-explorer-super-secret-key")
UPSTREAM_BASE = os.environ.get("UPSTREAM_BASE", "https://ft-osint-api.duckdns.org/api").rstrip("/")
UPSTREAM_KEY  = os.environ.get("UPSTREAM_KEY", "explorer16")
BRAND = os.environ.get("BRAND", "SHAYAN_EXPLORER")

# 🔴 YOUR TELEGRAM — CHANGE THIS to your real username (without @)
TELEGRAM_CONTACT = os.environ.get("TELEGRAM_CONTACT", "asgardx5").strip().lstrip("@")
TELEGRAM_URL = f"https://t.me/{TELEGRAM_CONTACT}"

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", JSON_SORT_KEYS=False)

# ----------------------------- TOOLS ------------------------------
TOOLS = [
    {"id": "pk",          "label": "Phone Lookup (PK)",   "params": ["num"],             "path": "pk"},
    {"id": "number",      "label": "Number Lookup",       "params": ["num"],             "path": "number"},
    {"id": "name",        "label": "Name Lookup",         "params": ["name"],            "path": "name"},
    {"id": "aadhar",      "label": "Aadhaar Info",        "params": ["num"],             "path": "aadhar"},
    {"id": "adharfamily", "label": "Aadhaar Family",      "params": ["num"],             "path": "adharfamily"},
    {"id": "upi",         "label": "UPI Info",            "params": ["upi"],             "path": "upi"},
    {"id": "numtoupi",    "label": "Number → UPI",        "params": ["num"],             "path": "numtoupi"},
    {"id": "pan",         "label": "PAN Info",            "params": ["pan"],             "path": "pan"},
    {"id": "vehicle",     "label": "Vehicle Info",        "params": ["vehicle"],         "path": "vehicle"},
    {"id": "veh2num",     "label": "Vehicle → Number",    "params": ["vehicle"],         "path": "veh2num"},
    {"id": "challan",     "label": "Vehicle Challan",     "params": ["vehicle"],         "path": "challan"},
    {"id": "bomber",      "label": "SMS Bomber",          "params": ["number", "counter"], "path": "bomber"},
    {"id": "adv",         "label": "Advanced Lookup",     "params": ["num"],             "path": "adv"},
    {"id": "paytm",       "label": "Paytm Info",          "params": ["num"],             "path": "paytm"},
    {"id": "imei",        "label": "IMEI Info",           "params": ["imei"],            "path": "imei"},
    {"id": "calltracer",  "label": "Call Tracer",         "params": ["num"],             "path": "calltracer"},
    {"id": "ifsc",        "label": "IFSC Info",           "params": ["ifsc"],            "path": "ifsc"},
    {"id": "pincode",     "label": "Pincode Info",        "params": ["pin"],             "path": "pincode"},
    {"id": "ip",          "label": "IP Info",             "params": ["ip"],              "path": "ip"},
    {"id": "ff",          "label": "Free Fire Info",      "params": ["uid"],             "path": "ff"},
    {"id": "bgmi",        "label": "BGMI Info",           "params": ["uid"],             "path": "bgmi"},
    {"id": "snap",        "label": "Snapchat Info",       "params": ["username"],        "path": "snap"},
    {"id": "email",       "label": "Email → Info",        "params": ["email"],           "path": "email"},
    {"id": "git",         "label": "GitHub Lookup",       "params": ["username"],        "path": "git"},
    {"id": "insta",       "label": "Instagram Info",      "params": ["username"],        "path": "insta"},
    {"id": "tg",          "label": "Telegram Username",   "params": ["info"],            "path": "tg"},
    {"id": "tgidinfo",    "label": "Telegram ID → Num",   "params": ["id"],              "path": "tgidinfo"},
    {"id": "numleak",     "label": "Number Leak Check",   "params": ["num"],             "path": "numleak"},
]
TOOL_MAP = {t["id"]: t for t in TOOLS}

# ----------------------------- DB --------------------------------
def _conn():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    return c

def db_fetch(sql, args=()):
    c = _conn()
    try: return [dict(r) for r in c.execute(sql, args).fetchall()]
    finally: c.close()

def db_one(sql, args=()):
    rows = db_fetch(sql, args)
    return rows[0] if rows else None

def db_write(sql, args=()):
    c = _conn()
    try:
        cur = c.execute(sql, args); c.commit()
        return cur.lastrowid
    finally: c.close()

def init_db():
    c = _conn()
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS api_keys(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '', by_name TEXT DEFAULT '',
            tools TEXT DEFAULT 'all',
            created_at TEXT NOT NULL, expires_at TEXT,
            req_limit INTEGER DEFAULT 0, req_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active', price REAL DEFAULT 0,
            note TEXT DEFAULT '', last_used TEXT
        );
        CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT, name TEXT, tool TEXT, query TEXT,
            ip TEXT, status TEXT, ts TEXT
        );
        CREATE TABLE IF NOT EXISTS members(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            name TEXT DEFAULT '', created_at TEXT NOT NULL,
            status TEXT DEFAULT 'active', created_by TEXT DEFAULT 'telegram',
            last_login TEXT
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        CREATE INDEX IF NOT EXISTS idx_logs_key ON logs(key);
        CREATE INDEX IF NOT EXISTS idx_logs_ts  ON logs(ts);
        """)
        try: c.execute("ALTER TABLE api_keys ADD COLUMN by_name TEXT DEFAULT ''")
        except sqlite3.OperationalError: pass
        c.commit()
    finally: c.close()

# ----------------------------- TIME ------------------------------
def now_utc(): return datetime.now(timezone.utc)

def iso(dt):
    if dt is None: return None
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")

def parse_iso(s):
    if not s: return None
    try:
        s = str(s).replace("Z", "+00:00").strip()
        d = datetime.fromisoformat(s)
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        try:
            ms = float(s)
            return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        except Exception:
            return None

def ms_to_iso(ms):
    try:
        ms = float(ms)
        return iso(datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc))
    except Exception:
        return None

def humanize_expiry(exp):
    """Return friendly time-to-expiry string."""
    if not exp: return "never"
    delta = (exp - now_utc()).total_seconds()
    if delta <= 0:
        secs = int(-delta)
        if secs < 60: return f"expired {secs}s ago"
        if secs < 3600: return f"expired {secs//60}m ago"
        if secs < 86400: return f"expired {secs//3600}h ago"
        return f"expired {secs//86400}d ago"
    secs = int(delta)
    if secs < 60: return f"in {secs}s"
    if secs < 3600: return f"in {secs//60}m"
    if secs < 86400: return f"in {secs//3600}h"
    return f"in {secs//86400}d"

# ----------------------------- SETTINGS --------------------------
def get_setting(key, default=''):
    row = db_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default

def set_setting(key, value):
    db_write("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
             (key, value if value is not None else ''))

def get_bot_token():   return get_setting("tg_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
def get_bot_chat():    return get_setting("tg_chat_id") or os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "")
def get_bot_secret():  return get_setting("tg_webhook_secret") or os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
def get_public_url():  return get_setting("public_base_url") or os.environ.get("PUBLIC_BASE_URL", "")

# ----------------------------- AUTH ------------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("admin"):
            if request.path.startswith("/admin/api/"):
                return jsonify(ok=False, error="Unauthorized"), 401
            return redirect("/admin/login")
        return f(*a, **kw)
    return wrapper

def super_admin_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("admin"):
            return jsonify(ok=False, error="Unauthorized"), 401
        if session.get("role") != "admin":
            return jsonify(ok=False, error="Admin only"), 403
        return f(*a, **kw)
    return wrapper

# ----------------------------- KEY HELPERS -----------------------
def key_state(row):
    if not row: return row
    exp = parse_iso(row.get("expires_at"))
    now = now_utc()
    row["expired"] = bool(exp and now >= exp)
    row["expires_ms"] = int(exp.timestamp() * 1000) if exp else None
    row["expires_human"] = humanize_expiry(exp)
    row["seconds_left"] = int((exp - now).total_seconds()) if exp else None
    lim = int(row.get("req_limit") or 0)
    used = int(row.get("req_count") or 0)
    row["remaining"] = max(0, lim - used) if lim > 0 else None
    return row

def _err_response(kind, title, message, advice, status_code):
    """Build a beautiful emoji error response with contact info."""
    return jsonify(
        ok=False,
        error=kind,
        title=title,
        message=message,
        advice=advice,
        contact=f"@{TELEGRAM_CONTACT}",
        contact_url=TELEGRAM_URL,
        buy_url=TELEGRAM_URL,
        brand=BRAND,
    ), status_code

def check_key(key, tool_id):
    row = db_one("SELECT * FROM api_keys WHERE key = ?", (key,))
    if not row:
        return None, _err_response(
            "invalid",
            "❌ Invalid API Key",
            "The API key you provided does not exist in our database.",
            f"💎 Need a valid key? DM @{TELEGRAM_CONTACT} to buy instantly!",
            401
        )
    if row["status"] != "active":
        return None, _err_response(
            "suspended",
            "🚫 API Key Suspended",
            "This API key has been suspended by the administrator.",
            f"📩 Contact @{TELEGRAM_CONTACT} to resolve or renew.",
            403
        )
    exp = parse_iso(row["expires_at"])
    if exp and now_utc() >= exp:
        exp_str = exp.strftime("%d %b %Y · %H:%M UTC")
        return None, _err_response(
            "expired",
            "⛔ API Key Expired",
            f"Your key expired on {exp_str}.",
            f"💎 Buy a fresh key now! DM @{TELEGRAM_CONTACT}",
            403
        )
    allowed = (row["tools"] or "all").split(",")
    if "all" not in allowed and tool_id not in allowed:
        return None, _err_response(
            "forbidden",
            "🔒 Tool Not Allowed",
            f"Your key is not authorised for the '{tool_id}' endpoint.",
            f"💎 Upgrade your plan · DM @{TELEGRAM_CONTACT}",
            403
        )
    lim = int(row["req_limit"] or 0)
    if lim > 0 and int(row["req_count"] or 0) >= lim:
        return None, _err_response(
            "limit",
            "📊 Request Limit Reached",
            f"You've used {row['req_count']}/{lim} allowed requests.",
            f"💎 Buy more requests · DM @{TELEGRAM_CONTACT}",
            429
        )
    return row, None

def log_request(key, name, tool, query, status):
    db_write("INSERT INTO logs(key,name,tool,query,ip,status,ts) VALUES (?,?,?,?,?,?,?)",
             (key, name, tool, str(query)[:400],
              request.headers.get("X-Forwarded-For", request.remote_addr or ""),
              status, iso(now_utc())))

# ============================================================
#                  TELEGRAM BOT · MEMBERS
# ============================================================
TG_STATE = {}

def _tg_api(method, **params):
    token = get_bot_token()
    if not token: return None
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=params, timeout=15)
        return r.json()
    except Exception: return None

def _tg_send(chat_id, text):
    return _tg_api("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")

def _gen_password(n=12):
    alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return ''.join(secrets.choice(alphabet) for _ in range(n))

def _public_base():
    return (get_public_url() or request.host_url).rstrip("/")

def tg_handle_update(update):
    msg = update.get("message") or update.get("edited_message")
    if not msg: return
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text: return

    allowed_chat = get_bot_chat().strip()
    if allowed_chat and str(chat_id) != allowed_chat:
        _tg_send(chat_id, "⛔ <b>Unauthorized.</b>\nOnly the configured admin can use this bot.")
        return

    low = text.lower()
    if "@" in low: low = low.split("@")[0]

    if low in ("/start", "/help"):
        _tg_send(chat_id,
            "🤖 <b>SHAYAN_EXPLORER · Member Bot</b>\n\n"
            "<b>Commands:</b>\n"
            "/generatekey — create member login\n"
            "/listmembers — show latest members\n"
            "/cancel — cancel current flow\n\n"
            "<i>Creates login credentials for your website members.</i>")
        return

    if low == "/cancel":
        TG_STATE.pop(chat_id, None)
        _tg_send(chat_id, "❌ Cancelled.")
        return

    if low == "/listmembers":
        rows = db_fetch("SELECT username,name,status,created_at FROM members ORDER BY id DESC LIMIT 10")
        if not rows:
            _tg_send(chat_id, "No members yet. Send /generatekey")
            return
        lines = ["<b>Last 10 members:</b>\n"]
        for r in rows:
            lines.append(f"• <code>{r['username']}</code> · {r['name'] or '—'} · {r['status']}")
        _tg_send(chat_id, "\n".join(lines))
        return

    if low in ("/generatekey", "/generate"):
        TG_STATE[chat_id] = {"step": "password", "data": {}}
        _tg_send(chat_id, "🔐 <b>Step 1/2 · Admin Password</b>\n\nSend your <b>admin password</b>:")
        return

    state = TG_STATE.get(chat_id)
    if not state:
        _tg_send(chat_id, "Unknown command. Send /help")
        return

    if state["step"] == "password":
        if text != ADMIN_PASS:
            TG_STATE.pop(chat_id, None)
            _tg_send(chat_id, "❌ <b>Wrong password.</b>\nStart again with /generatekey")
            return
        state["step"] = "username"
        _tg_send(chat_id, "✅ <b>Password accepted.</b>\n\n📝 <b>Step 2/2 · Username</b>\n\nSend the <b>username</b> for the new member\n(letters, numbers, dot, dash, underscore only):")
        return

    if state["step"] == "username":
        username = text.strip()
        if len(username) < 4 or len(username) > 30 or not all(c.isalnum() or c in "-_." for c in username):
            _tg_send(chat_id, "❌ Invalid username. Use 4-30 chars: letters/numbers/-/_/.\nTry again:")
            return
        if db_one("SELECT id FROM members WHERE username = ?", (username,)):
            _tg_send(chat_id, f"❌ Username <code>{username}</code> already exists.\nSend a different one:")
            return
        password = _gen_password(12)
        db_write("INSERT INTO members(username,password_hash,name,created_at,status,created_by) VALUES(?,?,?,?,?,?)",
                 (username, generate_password_hash(password), username, iso(now_utc()), "active", "telegram"))
        TG_STATE.pop(chat_id, None)
        base = _public_base()
        _tg_send(chat_id,
            "✅ <b>Member Created!</b>\n\n"
            "👤 <b>Username:</b>\n"
            f"<code>{username}</code>\n\n"
            "🔑 <b>Password:</b>\n"
            f"<code>{password}</code>\n\n"
            "🌐 <b>Login URL:</b>\n"
            f"<code>{base}/admin/login</code>\n\n"
            "📅 " + now_utc().strftime("%d %b %Y · %H:%M UTC") + "\n\n"
            "<i>Tap any code block to copy.</i>")
        return

@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    secret = get_bot_secret()
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") != secret:
        return ("Unauthorized", 401)
    try: tg_handle_update(request.get_json(silent=True) or {})
    except Exception: pass
    return ("ok", 200)

# ----------------------------- PROXY API -------------------------
@app.route("/api/<tool_id>", methods=["GET"])
def proxy(tool_id):
    t = TOOL_MAP.get(tool_id)
    if not t: return jsonify(ok=False, error="Unknown endpoint"), 404
    user_key = (request.args.get("key") or "").strip()
    if not user_key:
        return _err_response("missing", "🔑 Missing API Key",
            "You must pass your key as a query parameter.",
            f"💎 Get a key from @{TELEGRAM_CONTACT}", 401)

    row, err = check_key(user_key, tool_id)
    if err:
        log_request(user_key, (row or {}).get("name", ""), tool_id,
                    request.query_string.decode()[:300], "DENIED")
        return err

    params = {}
    for p in t["params"]:
        v = (request.args.get(p) or "").strip()
        if not v: return jsonify(ok=False, error=f"Missing parameter '{p}'"), 400
        params[p] = v

    payload = dict(params); payload["key"] = UPSTREAM_KEY
    try:
        up = requests.get(f"{UPSTREAM_BASE}/{t['path']}", params=payload, timeout=45)
        content = up.content
        ctype = up.headers.get("Content-Type", "application/json")
    except requests.Timeout:
        log_request(user_key, row["name"], tool_id, str(params), "TIMEOUT")
        return jsonify(ok=False, error="Upstream timeout"), 504
    except Exception as e:
        log_request(user_key, row["name"], tool_id, str(params), "ERROR")
        return jsonify(ok=False, error=f"Upstream error: {e}"), 502

    if "application/json" in ctype:
        try:
            data = up.json()
            if isinstance(data, dict):
                data.pop("by", None)
                data["by"] = row.get("by_name") or "SHAYAN_EXPLORER"
                db_write("UPDATE api_keys SET req_count = req_count + 1, last_used = ? WHERE id = ?",
                         (iso(now_utc()), row["id"]))
                log_request(user_key, row["name"], tool_id, str(params), "OK")
                return jsonify(data), up.status_code
        except Exception: pass

    db_write("UPDATE api_keys SET req_count = req_count + 1, last_used = ? WHERE id = ?",
             (iso(now_utc()), row["id"]))
    log_request(user_key, row["name"], tool_id, str(params), "OK")
    return Response(content, status=up.status_code, content_type=ctype)

# ----------------------------- ROUTES ----------------------------
@app.route("/")
def root(): return redirect("/admin")

@app.route("/health")
def health():
    return jsonify(ok=True, brand=BRAND, time=iso(now_utc()), db=DB_PATH,
                   telegram=bool(get_bot_token()), contact=TELEGRAM_CONTACT)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        wants_json = (request.is_json or "application/json" in (request.headers.get("Accept") or ""))
        data = request.get_json(silent=True) or request.form
        u = (data.get("username") or "").strip()
        p = (data.get("password") or "").strip()
        ok_admin = (u == ADMIN_USER and p == ADMIN_PASS)
        ok_member = False; member_row = None
        if not ok_admin:
            member_row = db_one("SELECT * FROM members WHERE username = ? AND status = 'active'", (u,))
            if member_row and check_password_hash(member_row["password_hash"], p):
                ok_member = True
        if ok_admin or ok_member:
            session["admin"] = True; session["username"] = u
            if ok_admin:
                session["role"] = "admin"; session["name"] = u
            else:
                session["role"] = "member"; session["name"] = member_row.get("name") or u
                db_write("UPDATE members SET last_login = ? WHERE id = ?",
                         (iso(now_utc()), member_row["id"]))
            if wants_json: return jsonify(ok=True, role=session["role"])
            return redirect("/admin")
        if wants_json: return jsonify(ok=False, error="Invalid username or password"), 401
        return Response(LOGIN_HTML.replace("__ERR__", "Invalid username or password"),
                        401, content_type="text/html")
    return Response(LOGIN_HTML.replace("__ERR__", ""), content_type="text/html")

@app.route("/admin/logout")
def admin_logout():
    session.clear(); return redirect("/admin/login")

@app.route("/admin")
@admin_required
def admin_home(): return Response(DASH_HTML, content_type="text/html")

# ----------------------------- ADMIN API -------------------------
@app.route("/admin/api/me")
@admin_required
def api_me():
    return jsonify(ok=True, username=session.get("username"),
                   role=session.get("role"), name=session.get("name"))

@app.route("/admin/api/tools")
@admin_required
def api_tools(): return jsonify(ok=True, tools=TOOLS)

@app.route("/admin/api/stats")
@admin_required
def api_stats():
    keys = [key_state(k) for k in db_fetch("SELECT * FROM api_keys")]
    total_keys = len(keys)
    active_keys = sum(1 for k in keys if k["status"] == "active" and not k["expired"])
    suspended = sum(1 for k in keys if k["status"] != "active")
    expired = sum(1 for k in keys if k["expired"])
    total_requests = sum(int(k["req_count"] or 0) for k in keys)
    today = now_utc().date().isoformat()
    today_requests = db_one("SELECT COUNT(*) c FROM logs WHERE substr(ts,1,10)=?", (today,))["c"]

    rng = request.args.get("range", "30d")
    days = {"today": 1, "7d": 7, "30d": 30, "90d": 90, "1y": 365, "all": 36500}.get(rng, 30)
    start = now_utc() - timedelta(days=days)
    rev_range = 0.0
    for k in keys:
        cd = parse_iso(k["created_at"])
        if cd and cd >= start: rev_range += float(k["price"] or 0)
    rev_total = sum(float(k["price"] or 0) for k in keys)

    series = []
    base = now_utc().date()
    for i in range(13, -1, -1):
        d = base - timedelta(days=i)
        amt = 0.0; cnt = 0
        for k in keys:
            cd = parse_iso(k["created_at"])
            if cd and cd.date() == d:
                amt += float(k["price"] or 0); cnt += 1
        series.append({"date": d.isoformat(), "amount": round(amt, 2), "count": cnt})

    return jsonify(ok=True, total_keys=total_keys, active_keys=active_keys,
                   suspended_keys=suspended, expired_keys=expired,
                   total_requests=total_requests, today_requests=today_requests,
                   revenue_total=round(rev_total, 2), revenue_range=round(rev_range, 2),
                   range=rng, series=series)

@app.route("/admin/api/keys", methods=["GET"])
@admin_required
def api_keys_list():
    q = (request.args.get("q") or "").strip().lower()
    rows = [key_state(r) for r in db_fetch("SELECT * FROM api_keys ORDER BY id DESC")]
    if q:
        rows = [r for r in rows if q in (r["key"] or "").lower()
                or q in (r["name"] or "").lower() or q in (r["tools"] or "").lower()]
    return jsonify(ok=True, keys=rows, server_now=iso(now_utc()))

@app.route("/admin/api/keys", methods=["POST"])
@admin_required
def api_keys_create():
    d = request.get_json(silent=True) or {}
    key = (d.get("key") or "").strip()
    if not key: key = "FT-" + secrets.token_hex(10).upper()
    if len(key) < 6: return jsonify(ok=False, error="Key must be at least 6 chars"), 400
    if not all(ch.isalnum() or ch in "-_." for ch in key):
        return jsonify(ok=False, error="Only letters, numbers, - _ ."), 400
    if db_one("SELECT id FROM api_keys WHERE key = ?", (key,)):
        return jsonify(ok=False, error="This key exists"), 409

    name = (d.get("name") or "").strip()[:60] or "unnamed"
    by_name = (d.get("by_name") or "").strip()[:60]
    tools = d.get("tools") or ["all"]
    if isinstance(tools, str): tools = [x.strip() for x in tools.split(",") if x.strip()]
    tools = [t for t in tools if t in TOOL_MAP]
    tools_str = "all" if (not tools or "all" in tools) else ",".join(sorted(set(tools)))

    expires_ms = d.get("expires_ms")
    expires_at = ms_to_iso(expires_ms) if expires_ms else None
    try: req_limit = max(0, int(d.get("req_limit") or 0))
    except Exception: req_limit = 0
    try: price = max(0.0, float(d.get("price") or 0))
    except Exception: price = 0.0
    note = (d.get("note") or "").strip()[:300]

    kid = db_write("INSERT INTO api_keys(key,name,by_name,tools,created_at,expires_at,req_limit,req_count,status,price,note) VALUES (?,?,?,?,?,?,?,0,'active',?,?)",
                   (key, name, by_name, tools_str, iso(now_utc()), expires_at, req_limit, price, note))
    row = key_state(db_one("SELECT * FROM api_keys WHERE id = ?", (kid,)))
    return jsonify(ok=True, key=row)

@app.route("/admin/api/keys/<int:kid>", methods=["PATCH"])
@admin_required
def api_keys_edit(kid):
    row = db_one("SELECT * FROM api_keys WHERE id = ?", (kid,))
    if not row: return jsonify(ok=False, error="Not found"), 404
    d = request.get_json(silent=True) or {}
    updates = {}
    if "name" in d: updates["name"] = (d.get("name") or "").strip()[:60] or "unnamed"
    if "by_name" in d: updates["by_name"] = (d.get("by_name") or "").strip()[:60]
    if "tools" in d:
        tools = d.get("tools") or ["all"]
        if isinstance(tools, str): tools = [x.strip() for x in tools.split(",") if x.strip()]
        tools = [t for t in tools if t in TOOL_MAP]
        updates["tools"] = "all" if (not tools or "all" in tools) else ",".join(sorted(set(tools)))
    if "req_limit" in d:
        try: updates["req_limit"] = max(0, int(d.get("req_limit") or 0))
        except Exception: updates["req_limit"] = 0
    if "expires_ms" in d:
        updates["expires_at"] = ms_to_iso(d.get("expires_ms")) if d.get("expires_ms") else None
    if "price" in d:
        try: updates["price"] = max(0.0, float(d.get("price") or 0))
        except Exception: updates["price"] = 0.0
    if "note" in d: updates["note"] = (d.get("note") or "").strip()[:300]
    if "status" in d and d["status"] in ("active", "suspended"): updates["status"] = d["status"]
    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        db_write(f"UPDATE api_keys SET {sets} WHERE id=?", tuple(updates.values()) + (kid,))
    return jsonify(ok=True, key=key_state(db_one("SELECT * FROM api_keys WHERE id = ?", (kid,))))

@app.route("/admin/api/keys/<int:kid>/reset", methods=["POST"])
@admin_required
def api_keys_reset(kid):
    if not db_one("SELECT id FROM api_keys WHERE id=?", (kid,)):
        return jsonify(ok=False, error="Not found"), 404
    db_write("UPDATE api_keys SET req_count = 0 WHERE id = ?", (kid,))
    return jsonify(ok=True)

@app.route("/admin/api/keys/<int:kid>", methods=["DELETE"])
@admin_required
def api_keys_delete(kid):
    db_write("DELETE FROM api_keys WHERE id = ?", (kid,))
    return jsonify(ok=True)

@app.route("/admin/api/logs")
@admin_required
def api_logs():
    q = (request.args.get("q") or "").strip()
    key = (request.args.get("key") or "").strip()
    try: limit = min(1000, max(1, int(request.args.get("limit") or 200)))
    except Exception: limit = 200
    sql = "SELECT * FROM logs WHERE 1=1"; args = []
    if key: sql += " AND key = ?"; args.append(key)
    if q:
        sql += " AND (key LIKE ? OR name LIKE ? OR tool LIKE ? OR query LIKE ?)"
        like = f"%{q}%"; args += [like, like, like, like]
    sql += " ORDER BY id DESC LIMIT ?"; args.append(limit)
    return jsonify(ok=True, logs=db_fetch(sql, tuple(args)))

# Debug endpoint — verify expiry works
@app.route("/admin/api/debug/key/<key>", methods=["GET"])
@super_admin_required
def debug_key(key):
    row = db_one("SELECT * FROM api_keys WHERE key = ?", (key,))
    if not row: return jsonify(ok=False, error="not found"), 404
    exp = parse_iso(row["expires_at"])
    now = now_utc()
    return jsonify(
        ok=True, key=row["key"],
        raw_expires_at=row["expires_at"],
        parsed_expires_at=exp.isoformat() if exp else None,
        now_utc=now.isoformat(),
        is_expired=(exp and now >= exp),
        seconds_until_expiry=(exp - now).total_seconds() if exp else None,
        human=humanize_expiry(exp),
        status=row["status"]
    )

@app.route("/admin/api/members", methods=["GET"])
@super_admin_required
def api_members():
    q = (request.args.get("q") or "").strip().lower()
    rows = db_fetch("SELECT id,username,name,status,created_at,created_by,last_login FROM members ORDER BY id DESC")
    if q:
        rows = [r for r in rows if q in (r["username"] or "").lower() or q in (r["name"] or "").lower()]
    return jsonify(ok=True, members=rows)

@app.route("/admin/api/members/<int:mid>", methods=["DELETE"])
@super_admin_required
def api_member_delete(mid):
    db_write("DELETE FROM members WHERE id = ?", (mid,))
    return jsonify(ok=True)

# TELEGRAM SETTINGS
@app.route("/admin/api/telegram/config", methods=["GET"])
@super_admin_required
def api_tg_config():
    return jsonify(ok=True, token=get_bot_token(), chat_id=get_bot_chat(),
                   secret=get_bot_secret(), public_url=get_public_url())

@app.route("/admin/api/telegram/save-token", methods=["POST"])
@super_admin_required
def api_tg_save_token():
    d = request.get_json(silent=True) or {}
    token = (d.get("token") or "").strip()
    if not token: return jsonify(ok=False, error="Empty"), 400
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
        res = r.json()
        if not res.get("ok"):
            return jsonify(ok=False, error=res.get("description", "Invalid token")), 400
        bot_username = (res.get("result") or {}).get("username", "")
    except Exception as e:
        return jsonify(ok=False, error=f"Verify failed: {e}"), 500
    set_setting("tg_bot_token", token)
    return jsonify(ok=True, bot_username=bot_username)

@app.route("/admin/api/telegram/save-chat", methods=["POST"])
@super_admin_required
def api_tg_save_chat():
    d = request.get_json(silent=True) or {}
    chat_id = str(d.get("chat_id") or "").strip()
    if not chat_id: return jsonify(ok=False, error="Empty"), 400
    set_setting("tg_chat_id", chat_id)
    return jsonify(ok=True)

@app.route("/admin/api/telegram/save-public", methods=["POST"])
@super_admin_required
def api_tg_save_public():
    d = request.get_json(silent=True) or {}
    set_setting("public_base_url", (d.get("url") or "").strip().rstrip("/"))
    return jsonify(ok=True)

@app.route("/admin/api/telegram/install", methods=["POST"])
@super_admin_required
def api_tg_install():
    token = get_bot_token()
    if not token: return jsonify(ok=False, error="Save bot token first"), 400
    base = _public_base()
    if not base.startswith("http"):
        return jsonify(ok=False, error="Set PUBLIC_BASE_URL first"), 400
    webhook_url = base + "/telegram/webhook"
    secret = get_bot_secret()
    if not secret:
        secret = secrets.token_hex(16); set_setting("tg_webhook_secret", secret)
    payload = {"url": webhook_url, "allowed_updates": ["message"], "secret_token": secret}
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/setWebhook", json=payload, timeout=15)
        res = r.json()
    except Exception as e:
        return jsonify(ok=False, error=f"Failed: {e}"), 500
    if not res.get("ok"):
        return jsonify(ok=False, error=res.get("description", "Failed")), 400
    test_ok = False
    if get_bot_chat():
        test_ok = bool(_tg_send(get_bot_chat(),
            "✅ <b>Bot installed successfully!</b>\n\n"
            "Send /generatekey to create a member login."))
    return jsonify(ok=True, webhook=webhook_url, test_sent=test_ok)

@app.route("/admin/api/telegram/status", methods=["GET"])
@super_admin_required
def api_tg_status():
    token = get_bot_token()
    if not token: return jsonify(ok=True, configured=False)
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=15)
        return jsonify(ok=True, configured=True, info=r.json())
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.route("/admin/api/telegram/test", methods=["POST"])
@super_admin_required
def api_tg_test():
    chat_id = get_bot_chat()
    if not chat_id: return jsonify(ok=False, error="Save Chat ID first"), 400
    res = _tg_send(chat_id, "🧪 <b>Test</b>\nBot connected. Send /generatekey to create a member.")
    if res and res.get("ok"): return jsonify(ok=True)
    return jsonify(ok=False, error=(res or {}).get("description", "Failed")), 400

# ============================================================
#                         LOGIN PAGE
# ============================================================
LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SHAYAN_EXPLORER · Secure Login</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--cyan:#00e5ff;--violet:#8b5cf6;--txt:#e6f0ff;--mut:#7b93b5;--red:#ff4d6d;--green:#22e08a;--bg:#03060d}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{display:flex;align-items:center;justify-content:center;padding:20px;
  font-family:'Inter',system-ui,-apple-system,sans-serif;color:var(--txt);
  background:radial-gradient(1000px 700px at 15% 0%,rgba(0,229,255,.16),transparent 60%),
    radial-gradient(900px 600px at 90% 100%,rgba(139,92,246,.2),transparent 60%),var(--bg);
  overflow:hidden}
#bg{position:fixed;inset:0;z-index:0;pointer-events:none}
#snow{position:fixed;inset:0;z-index:1;pointer-events:none}
.wrap{position:relative;z-index:2;width:100%;max-width:440px;perspective:1400px}
.card{background:linear-gradient(160deg,rgba(14,26,45,.94),rgba(5,10,20,.97));
  border:1px solid rgba(0,229,255,.22);border-radius:24px;padding:38px 30px;
  box-shadow:0 40px 100px -40px rgba(0,229,255,.65),0 0 0 1px rgba(255,255,255,.04) inset;
  transform:rotateX(4deg);animation:float 8s ease-in-out infinite;position:relative;overflow:hidden}
.card::before{content:"";position:absolute;inset:0;padding:1px;border-radius:24px;
  background:linear-gradient(135deg,rgba(0,229,255,.5),transparent 40%,transparent 60%,rgba(139,92,246,.5));
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
@keyframes float{0%,100%{transform:rotateX(4deg) translateY(0)}50%{transform:rotateX(4deg) translateY(-10px)}}
.logo{width:72px;height:72px;margin:0 auto 18px;border-radius:20px;display:grid;place-items:center;
  font-weight:900;font-size:24px;letter-spacing:1px;color:#02121a;
  background:linear-gradient(135deg,#00e5ff,#8b5cf6);
  box-shadow:0 0 46px rgba(0,229,255,.75),0 8px 30px rgba(139,92,246,.4);
  animation:pulse 3s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 46px rgba(0,229,255,.75),0 8px 30px rgba(139,92,246,.4)}
  50%{box-shadow:0 0 70px rgba(0,229,255,1),0 12px 40px rgba(139,92,246,.6)}}
h1{font-size:22px;text-align:center;letter-spacing:3px;font-weight:900;
  background:linear-gradient(135deg,#fff,#7fe9ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{text-align:center;color:var(--mut);font-size:10.5px;letter-spacing:3px;margin:8px 0 30px;font-weight:600}
label{display:block;font-size:10px;letter-spacing:2px;color:var(--mut);margin:16px 0 7px;
  text-transform:uppercase;font-weight:700}
.field{position:relative}
.field::before{content:"";position:absolute;left:14px;top:50%;transform:translateY(-50%);
  font-size:14px;opacity:.7;pointer-events:none}
.field.u::before{content:"👤"}
.field.p::before{content:"🔒"}
input{width:100%;padding:14px 14px 14px 40px;border-radius:13px;
  background:rgba(2,8,16,.85);border:1px solid rgba(0,229,255,.2);
  color:var(--txt);font-size:14px;outline:none;transition:.25s;font-family:inherit}
input:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(0,229,255,.15),0 0 24px -8px rgba(0,229,255,.7);background:rgba(2,8,16,.95)}
button{width:100%;margin-top:26px;padding:15px;border:0;border-radius:13px;cursor:pointer;
  font-weight:800;letter-spacing:2px;font-size:12.5px;color:#02121a;font-family:inherit;
  background:linear-gradient(135deg,#00e5ff,#3b82f6);
  box-shadow:0 18px 40px -18px rgba(0,229,255,.9);transition:.22s;
  position:relative;overflow:hidden}
button::before{content:"";position:absolute;inset:0;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);
  transform:translateX(-100%);transition:transform .6s}
button:hover{transform:translateY(-2px);box-shadow:0 26px 48px -20px rgba(0,229,255,1)}
button:hover::before{transform:translateX(100%)}
.err{background:rgba(255,77,109,.12);border:1px solid rgba(255,77,109,.4);color:#ffb3c1;
  padding:12px 14px;border-radius:11px;font-size:12.5px;margin-bottom:8px;text-align:center;font-weight:500}
.foot{margin-top:24px;text-align:center;font-size:10px;letter-spacing:2px;color:var(--mut);font-weight:600}
.foot b{color:var(--cyan);font-weight:800}

/* hacker overlay */
#hacker{display:none;position:fixed;inset:0;background:rgba(0,4,2,.98);z-index:9999;
  font-family:'JetBrains Mono',monospace;color:#0f0;padding:40px;font-size:14px;
  text-shadow:0 0 8px #0f0;overflow:hidden}
#hacker.show{display:block;animation:flash .4s ease}
@keyframes flash{0%{opacity:0}100%{opacity:1}}
#hacker .scanline{position:absolute;inset:0;pointer-events:none;
  background:repeating-linear-gradient(180deg,transparent 0,transparent 3px,rgba(0,255,0,.06) 3px,rgba(0,255,0,.06) 4px);
  animation:scan 8s linear infinite}
@keyframes scan{0%{transform:translateY(0)}100%{transform:translateY(4px)}}
#hacker-text{line-height:1.9;position:relative;z-index:1}
#hacker-text div{margin-bottom:6px;animation:typeIn .25s ease}
@keyframes typeIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
#hacker-text .ok{color:#0f0;font-weight:700}
#hacker-text .warn{color:#ff0}
#hacker-text .err-line{color:#f55}
.blink{animation:blink 1s step-end infinite}
@keyframes blink{50%{opacity:0}}
.progress{height:4px;background:rgba(0,255,0,.15);border-radius:2px;margin-top:20px;overflow:hidden}
.progress-bar{height:100%;width:0;background:linear-gradient(90deg,#0f0,#0a0);
  box-shadow:0 0 18px #0f0;transition:width .15s linear}
</style>
</head>
<body>
<canvas id="bg"></canvas>
<canvas id="snow"></canvas>

<div id="hacker">
  <div class="scanline"></div>
  <div id="hacker-text"></div>
  <div class="progress"><div class="progress-bar" id="pbar"></div></div>
</div>

<div class="wrap">
  <div class="card">
    <div class="logo">SE</div>
    <h1>SHAYAN_EXPLORER</h1>
    <div class="sub">OSINT API · CONTROL CENTER</div>
    <div class="err" id="errBox" style="display:none">__ERR__</div>
    <form autocomplete="off" id="loginForm" onsubmit="startHacking(event)">
      <label>Username</label>
      <div class="field u"><input name="username" id="uName" placeholder="Enter username" required autofocus></div>
      <label>Password</label>
      <div class="field p"><input name="password" id="pWord" type="password" placeholder="Enter password" required></div>
      <button type="submit">AUTHENTICATE</button>
    </form>
    <div class="foot">API DEVELOPER · <b>SHAYAN_EXPLORER</b></div>
  </div>
</div>

<script>
/* ---------- Particle background ---------- */
(function(){
  const c = document.getElementById('bg'), ctx = c.getContext('2d');
  let W, H, parts = [];
  function resize(){ W = c.width = innerWidth; H = c.height = innerHeight; }
  resize(); addEventListener('resize', resize);
  for(let i=0;i<40;i++) parts.push({
    x: Math.random()*W, y: Math.random()*H,
    vx: (Math.random()-.5)*.3, vy: (Math.random()-.5)*.3,
    r: Math.random()*1.4+.4
  });
  function tick(){
    ctx.clearRect(0,0,W,H);
    for(const p of parts){
      ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle = 'rgba(0,229,255,.35)'; ctx.fill();
      p.x += p.vx; p.y += p.vy;
      if(p.x<0||p.x>W) p.vx *= -1;
      if(p.y<0||p.y>H) p.vy *= -1;
    }
    for(let i=0;i<parts.length;i++){
      for(let j=i+1;j<parts.length;j++){
        const dx = parts[i].x-parts[j].x, dy = parts[i].y-parts[j].y;
        const d = Math.sqrt(dx*dx+dy*dy);
        if(d < 140){
          ctx.beginPath(); ctx.moveTo(parts[i].x,parts[i].y); ctx.lineTo(parts[j].x,parts[j].y);
          ctx.strokeStyle = `rgba(0,229,255,${.12*(1-d/140)})`; ctx.lineWidth = .5; ctx.stroke();
        }
      }
    }
    requestAnimationFrame(tick);
  }
  tick();
})();

/* ---------- Snowfall ---------- */
(function(){
  const c = document.getElementById('snow'), ctx = c.getContext('2d');
  let W, H;
  function resize(){ W = c.width = innerWidth; H = c.height = innerHeight; }
  resize(); addEventListener('resize', resize);
  const flakes = Array.from({length:60}, () => ({
    x: Math.random()*W, y: Math.random()*H, r: Math.random()*2.2+.3,
    dx: Math.random()*.4-.2, dy: Math.random()*.35+.15, o: Math.random()*.55+.2
  }));
  function tick(){
    ctx.clearRect(0,0,W,H);
    for(const f of flakes){
      ctx.beginPath(); ctx.arc(f.x,f.y,f.r,0,Math.PI*2);
      ctx.fillStyle = `rgba(220,240,255,${f.o})`; ctx.fill();
      f.x += f.dx; f.y += f.dy;
      if(f.y > H+5){ f.y = -5; f.x = Math.random()*W; }
      if(f.x < -5) f.x = W;
      if(f.x > W+5) f.x = 0;
    }
    requestAnimationFrame(tick);
  }
  tick();
})();

/* ---------- Login flow ---------- */
function startHacking(e){
  e.preventDefault();
  const username = document.getElementById('uName').value.trim();
  const password = document.getElementById('pWord').value;
  if(!username || !password) return;

  const errBox = document.getElementById('errBox');
  errBox.style.display = 'none';

  // Fire request in parallel
  const loginPromise = fetch('/admin/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    body: JSON.stringify({username, password})
  }).then(r => r.json()).catch(() => ({ok:false, error:'Network error'}));

  // Show hacker overlay
  const hacker = document.getElementById('hacker');
  const textDiv = document.getElementById('hacker-text');
  const pbar = document.getElementById('pbar');
  textDiv.innerHTML = '';
  pbar.style.width = '0%';
  hacker.classList.add('show');

  const lines = [
    {t: "> [BOOT] Initializing SHAYAN_EXPLORER OSINT Engine...", c: ''},
    {t: "> [SYS]  Loading modules......................... OK", c: 'ok'},
    {t: "> [AUTH] Connecting to secure authentication...", c: ''},
    {t: "> [NET]  Establishing encrypted channel........... OK", c: 'ok'},
    {t: "> [SEC]  Validating credentials against database...", c: ''},
    {t: "> [TOK]  Generating session token.................. OK", c: 'ok'},
    {t: "> [DB]   Connecting to encrypted storage........... OK", c: 'ok'},
    {t: "> [SYS]  Bypassing firewall protocols............. OK", c: 'ok'},
    {t: "> [SYS]  ACCESS GRANTED. Loading dashboard...", c: 'ok'}
  ];
  let i = 0;
  const interval = setInterval(() => {
    if(i < lines.length){
      const d = document.createElement('div');
      d.textContent = lines[i].t;
      if(lines[i].c) d.className = lines[i].c;
      if(i === lines.length - 1) d.innerHTML += ' <span class="blink">▊</span>';
      textDiv.appendChild(d);
      pbar.style.width = Math.round(((i+1)/lines.length)*100) + '%';
      i++;
    } else {
      clearInterval(interval);
      loginPromise.then(result => {
        if(result && result.ok){
          sessionStorage.setItem('auth','1');
          setTimeout(() => { location.href = '/admin'; }, 400);
        } else {
          hacker.classList.remove('show');
          errBox.textContent = (result && result.error) || 'Login failed';
          errBox.style.display = 'block';
        }
      });
    }
  }, 280);
}
</script>
</body>
</html>"""
LOGIN_HTML = LOGIN_HTML.replace("__ERRBLOCK__", "")

# ============================================================
#                       DASHBOARD PAGE
# ============================================================
DASH_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>SHAYAN_EXPLORER · OSINT API CONTROL</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#03060d;--line:rgba(0,229,255,.16);--cyan:#00e5ff;--blue:#3b82f6;
  --violet:#8b5cf6;--green:#22e08a;--red:#ff4d6d;--amber:#ffb020;
  --txt:#e6f0ff;--mut:#7b93b5;--r:16px;--ease:cubic-bezier(.2,.9,.3,1)}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;color:var(--txt);
  background:var(--bg);overflow-x:hidden;-webkit-font-smoothing:antialiased}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(1100px 650px at 10% -10%,rgba(0,229,255,.13),transparent 60%),
    radial-gradient(900px 600px at 100% 0%,rgba(139,92,246,.14),transparent 55%),
    radial-gradient(900px 700px at 50% 120%,rgba(59,130,246,.12),transparent 60%)}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(0,229,255,.045) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(0,229,255,.045) 1px,transparent 1px);
  background-size:58px 58px;animation:grid 24s linear infinite;
  -webkit-mask-image:radial-gradient(circle at 50% 30%,#000 15%,transparent 80%);
          mask-image:radial-gradient(circle at 50% 30%,#000 15%,transparent 80%)}
@keyframes grid{to{background-position:58px 58px,58px 58px}}
#snow{position:fixed;inset:0;pointer-events:none;z-index:1}

.app{position:relative;z-index:2;display:flex;min-height:100vh}

/* Sidebar */
.sidebar{width:250px;flex:0 0 250px;padding:20px 14px;display:flex;flex-direction:column;gap:6px;
  background:linear-gradient(180deg,rgba(8,16,30,.95),rgba(4,9,18,.92));
  border-right:1px solid var(--line);position:sticky;top:0;height:100vh;overflow-y:auto;
  transition:transform .3s var(--ease);z-index:60}
.side-head{display:flex;gap:12px;align-items:center;padding:6px 6px 18px;
  border-bottom:1px solid var(--line);margin-bottom:10px}
.logo{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;font-weight:900;
  font-size:15px;color:#02121a;background:linear-gradient(135deg,#00e5ff,#8b5cf6);
  box-shadow:0 0 26px rgba(0,229,255,.6);flex:0 0 44px}
.side-title{font-size:12.5px;font-weight:800;letter-spacing:1.6px}
.side-sub{font-size:9px;letter-spacing:2px;color:var(--mut);margin-top:3px;font-weight:600}
.nav-item{display:flex;align-items:center;gap:11px;width:100%;padding:12px 13px;border-radius:12px;
  background:transparent;border:1px solid transparent;color:var(--mut);font-size:13px;
  font-weight:600;cursor:pointer;text-align:left;transition:.2s var(--ease);
  letter-spacing:.3px;font-family:inherit}
.nav-item span{width:20px;text-align:center;font-size:14px;opacity:.9}
.nav-item:hover{background:rgba(0,229,255,.07);color:var(--txt);border-color:rgba(0,229,255,.14)}
.nav-item.active{background:linear-gradient(90deg,rgba(0,229,255,.18),rgba(0,229,255,.02));
  color:#fff;border-color:rgba(0,229,255,.35);box-shadow:0 0 24px -10px rgba(0,229,255,.9)}
.side-foot{margin-top:auto;padding-top:14px;border-top:1px solid var(--line);
  display:flex;flex-direction:column;gap:10px}
.dev{font-size:9.5px;letter-spacing:1.6px;color:var(--mut);text-align:center;font-weight:600}
.dev b{color:var(--cyan);font-size:11px;letter-spacing:1.4px}

.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{display:flex;align-items:center;gap:14px;padding:14px 20px;position:sticky;
  top:0;z-index:50;background:rgba(4,9,18,.82);backdrop-filter:blur(14px);
  border-bottom:1px solid var(--line)}
.icon-btn{width:40px;height:40px;border-radius:11px;border:1px solid var(--line);
  background:rgba(0,229,255,.07);color:var(--cyan);font-size:17px;cursor:pointer;
  display:none;place-items:center;transition:.18s}
.icon-btn:hover{background:rgba(0,229,255,.18)}
.top-brand{font-size:13px;font-weight:800;letter-spacing:2px}
.top-brand small{display:block;font-size:9px;letter-spacing:2.4px;color:var(--mut);
  font-weight:600;margin-top:2px}
.top-spacer{flex:1}
.chip{font-size:10px;letter-spacing:1.4px;padding:7px 12px;border-radius:999px;
  border:1px solid rgba(34,224,138,.4);color:var(--green);
  background:rgba(34,224,138,.09);font-weight:700;position:relative}
.chip::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;
  background:var(--green);margin-right:6px;box-shadow:0 0 10px var(--green);
  animation:pulseDot 1.5s infinite}
@keyframes pulseDot{0%,100%{opacity:1}50%{opacity:.3}}

.content{padding:22px;flex:1}
.view{display:none;animation:fadeIn .4s var(--ease)}
.view.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}

/* Cards */
.grid{display:grid;gap:16px}
.g4{grid-template-columns:repeat(4,1fr)}
.g3{grid-template-columns:repeat(3,1fr)}
.card{background:linear-gradient(160deg,rgba(13,24,42,.9),rgba(6,12,24,.88));
  border:1px solid var(--line);border-radius:var(--r);padding:20px;position:relative;
  box-shadow:0 20px 44px -28px rgba(0,229,255,.55),inset 0 1px 0 rgba(255,255,255,.05);
  transition:transform .3s var(--ease),box-shadow .3s var(--ease);overflow:hidden}
.card::before{content:"";position:absolute;top:-50%;right:-30%;width:200px;height:200px;
  background:radial-gradient(circle,rgba(0,229,255,.15),transparent 70%);pointer-events:none;opacity:0;transition:.4s}
.card:hover{transform:translateY(-4px) rotateX(1deg);
  box-shadow:0 30px 60px -26px rgba(0,229,255,.75)}
.card:hover::before{opacity:1}
.card h3{margin:0 0 8px;font-size:10.5px;letter-spacing:2px;color:var(--mut);
  font-weight:700;text-transform:uppercase}
.card .big{font-size:32px;font-weight:900;letter-spacing:-1px;
  background:linear-gradient(135deg,#fff,#7fe9ff);-webkit-background-clip:text;
  background-clip:text;color:transparent;line-height:1.1}
.card .sub{font-size:11px;color:var(--mut);margin-top:8px;font-weight:500}

/* Panel */
.panel{background:linear-gradient(160deg,rgba(11,20,36,.92),rgba(5,10,20,.9));
  border:1px solid var(--line);border-radius:var(--r);padding:20px;margin-top:20px;
  box-shadow:0 20px 50px -34px rgba(0,229,255,.6)}
.panel-head{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.panel-head h2{margin:0;font-size:12px;letter-spacing:2.2px;font-weight:800;color:#eaf6ff}
.panel-head .spacer{flex:1}

/* Buttons */
.btn{padding:10px 18px;border-radius:11px;border:1px solid rgba(0,229,255,.35);
  background:linear-gradient(135deg,rgba(0,229,255,.2),rgba(59,130,246,.16));
  color:#eaffff;font-size:12px;font-weight:700;letter-spacing:1.1px;cursor:pointer;
  transition:.2s var(--ease);font-family:inherit;position:relative;overflow:hidden}
.btn:hover{transform:translateY(-2px);box-shadow:0 14px 30px -14px rgba(0,229,255,.9)}
.btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.btn.ghost{background:transparent;border-color:var(--line);color:var(--mut)}
.btn.ghost:hover{color:#fff;border-color:rgba(0,229,255,.5);background:rgba(0,229,255,.06)}
.btn.red{border-color:rgba(255,77,109,.45);background:rgba(255,77,109,.12);color:#ffb3c1}
.btn.green{border-color:rgba(34,224,138,.45);background:rgba(34,224,138,.12);color:#9ff5cd}
.btn.amber{border-color:rgba(255,176,32,.45);background:rgba(255,176,32,.12);color:#ffd894}
.btn.sm{padding:7px 11px;font-size:10.5px;letter-spacing:.8px;border-radius:9px}
.btn.loading{color:transparent;pointer-events:none;position:relative}
.btn.loading::after{content:"";position:absolute;inset:0;margin:auto;width:16px;height:16px;
  border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;
  animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* Inputs */
input,select,textarea{width:100%;padding:11px 13px;border-radius:11px;
  background:rgba(2,8,16,.9);border:1px solid rgba(0,229,255,.18);color:var(--txt);
  font-size:13px;outline:none;font-family:inherit;transition:.18s}
input:focus,select:focus,textarea:focus{border-color:var(--cyan);
  box-shadow:0 0 0 3px rgba(0,229,255,.13)}
.search{max-width:280px}
label.fl{display:block;font-size:10px;letter-spacing:1.6px;color:var(--mut);
  margin:14px 0 6px;text-transform:uppercase;font-weight:700}

/* Table */
.tbl-wrap{overflow-x:auto;border-radius:12px;border:1px solid rgba(0,229,255,.1)}
table{width:100%;border-collapse:collapse;font-size:12.3px;min-width:760px}
th{text-align:left;padding:12px;font-size:9.6px;letter-spacing:1.7px;color:var(--mut);
  text-transform:uppercase;background:rgba(0,229,255,.05);border-bottom:1px solid var(--line);
  white-space:nowrap;font-weight:800}
td{padding:12px;border-bottom:1px solid rgba(0,229,255,.07);vertical-align:middle}
tr:hover td{background:rgba(0,229,255,.04)}
.mono{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11.4px;color:#9de8ff;
  word-break:break-all;font-weight:500}

/* Badges */
.badge{display:inline-block;padding:4px 10px;border-radius:999px;font-size:9.5px;
  letter-spacing:1.1px;font-weight:800;text-transform:uppercase}
.b-active{background:rgba(34,224,138,.14);color:var(--green);border:1px solid rgba(34,224,138,.35)}
.b-susp{background:rgba(255,176,32,.13);color:var(--amber);border:1px solid rgba(255,176,32,.35)}
.b-exp{background:rgba(255,77,109,.13);color:var(--red);border:1px solid rgba(255,77,109,.35)}
.b-warn{background:rgba(255,176,32,.13);color:var(--amber);border:1px solid rgba(255,176,32,.35);
  animation:pulseBadge 2s infinite}
@keyframes pulseBadge{0%,100%{box-shadow:0 0 0 0 rgba(255,176,32,.5)}50%{box-shadow:0 0 0 4px rgba(255,176,32,0)}}
.acts{display:flex;gap:6px;flex-wrap:wrap}

/* Skeleton loader */
.skel{background:linear-gradient(90deg,rgba(0,229,255,.05) 25%,rgba(0,229,255,.13) 50%,rgba(0,229,255,.05) 75%);
  background-size:200% 100%;animation:shimmer 1.4s infinite;border-radius:6px;height:14px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}

/* Modal */
.modal{position:fixed;inset:0;z-index:200;display:none;align-items:center;
  justify-content:center;padding:18px;background:rgba(2,6,14,.85);backdrop-filter:blur(7px)}
.modal.show{display:flex}
.modal-box{width:100%;max-width:660px;max-height:90vh;overflow-y:auto;border-radius:20px;
  padding:26px;background:linear-gradient(160deg,rgba(13,24,42,.98),rgba(5,10,20,.99));
  border:1px solid rgba(0,229,255,.3);box-shadow:0 50px 110px -40px rgba(0,229,255,.85);
  animation:pop .3s var(--ease)}
@keyframes pop{from{opacity:0;transform:scale(.94) translateY(14px)}to{opacity:1;transform:none}}
.modal-box h2{margin:0 0 4px;font-size:15px;letter-spacing:2px}
.modal-box p.hint{margin:0 0 8px;font-size:11px;color:var(--mut)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.toolgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:8px;
  max-height:210px;overflow-y:auto;padding:10px;border-radius:12px;
  background:rgba(2,8,16,.6);border:1px solid rgba(0,229,255,.12)}
.tool-item{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:9px;
  cursor:pointer;font-size:11.4px;border:1px solid transparent;transition:.15s;color:var(--mut)}
.tool-item:hover{background:rgba(0,229,255,.07);color:var(--txt)}
.tool-item input{width:15px;height:15px;accent-color:#00e5ff;cursor:pointer;flex:0 0 15px}
.quick{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}

/* Chart */
.chart{display:flex;align-items:flex-end;gap:7px;height:170px;padding:14px;
  border-radius:14px;background:rgba(2,8,16,.6);border:1px solid rgba(0,229,255,.1)}
.bar{flex:1;border-radius:6px 6px 3px 3px;min-height:4px;position:relative;
  background:linear-gradient(180deg,#00e5ff,#3b82f6);
  box-shadow:0 0 18px -6px rgba(0,229,255,.9);transition:height .6s var(--ease)}
.bar:hover{background:linear-gradient(180deg,#8b5cf6,#00e5ff)}
.bar span{position:absolute;bottom:-19px;left:0;right:0;text-align:center;
  font-size:8.4px;color:var(--mut);font-weight:700}

/* Toasts */
#toasts{position:fixed;top:16px;right:16px;z-index:999;display:flex;
  flex-direction:column;gap:9px;max-width:340px}
.toast{padding:13px 18px;border-radius:13px;font-size:12.5px;font-weight:600;
  background:rgba(9,18,32,.97);border:1px solid rgba(0,229,255,.35);color:#dff7ff;
  box-shadow:0 20px 44px -20px rgba(0,229,255,.9);animation:slideIn .3s var(--ease);
  display:flex;align-items:center;gap:10px}
.toast::before{content:"ℹ";font-size:16px}
.toast.err{border-color:rgba(255,77,109,.55);color:#ffc2cc}
.toast.err::before{content:"✕"}
.toast.ok{border-color:rgba(34,224,138,.55);color:#a8f7d2}
.toast.ok::before{content:"✓"}
@keyframes slideIn{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:none}}

.empty{padding:30px;text-align:center;color:var(--mut);font-size:12px}
.overlay{position:fixed;inset:0;background:rgba(2,6,14,.7);backdrop-filter:blur(3px);
  z-index:55;display:none}
.overlay.show{display:block}

.doc-item{padding:14px;border-radius:12px;background:rgba(2,8,16,.6);
  border:1px solid rgba(0,229,255,.1);margin-bottom:10px;transition:.2s var(--ease)}
.doc-item:hover{border-color:rgba(0,229,255,.3);transform:translateX(3px)}
.doc-item .u{font-family:'JetBrains Mono',monospace;font-size:11.6px;color:#8ce8ff;word-break:break-all}
.doc-item .d{font-size:10.4px;color:var(--mut);margin-top:4px;letter-spacing:.6px;font-weight:500}

/* 3-dot menu */
.menu3-wrap{position:relative}
.icon-btn-3dot{width:40px;height:40px;border-radius:11px;border:1px solid var(--line);
  background:rgba(0,229,255,.07);color:var(--cyan);font-size:20px;cursor:pointer;
  display:grid;place-items:center;transition:.22s var(--ease);font-weight:900;line-height:1}
.icon-btn-3dot:hover{background:rgba(0,229,255,.18);transform:rotate(90deg)}
.menu3{position:absolute;top:calc(100% + 10px);right:0;min-width:230px;
  background:linear-gradient(160deg,rgba(13,24,42,.98),rgba(5,10,20,.99));
  border:1px solid rgba(0,229,255,.3);border-radius:14px;padding:8px;
  box-shadow:0 25px 55px -20px rgba(0,229,255,.9);display:none;z-index:120}
.menu3.show{display:block;animation:menuPop .22s var(--ease)}
@keyframes menuPop{from{opacity:0;transform:scale(.95) translateY(-6px)}to{opacity:1;transform:none}}
.menu3 .mi{display:flex;align-items:center;gap:10px;width:100%;padding:10px 12px;
  border:0;background:transparent;color:var(--txt);text-align:left;font-size:12.5px;
  font-weight:600;cursor:pointer;border-radius:9px;font-family:inherit;
  text-decoration:none;letter-spacing:.3px;transition:.15s}
.menu3 .mi:hover{background:rgba(0,229,255,.12);color:#fff}
.menu3 .mi .ic{width:22px;text-align:center;font-size:14px}
.menu3 .sep{height:1px;background:rgba(0,229,255,.13);margin:6px 4px}
.menu3 .mi.danger{color:#ffb3c1}
.menu3 .mi.danger:hover{background:rgba(255,77,109,.15);color:#ff8ea0}

.copy-inline{padding:5px 9px;border-radius:7px;border:1px solid rgba(0,229,255,.35);
  background:rgba(0,229,255,.09);color:#8ce8ff;font-size:10px;font-weight:800;
  letter-spacing:.8px;cursor:pointer;font-family:inherit;transition:.15s;white-space:nowrap}
.copy-inline:hover{background:rgba(0,229,255,.22);color:#fff}
.copy-inline.copied{background:rgba(34,224,138,.22);border-color:rgba(34,224,138,.5);color:#a8f7d2}

/* Wizard */
.wiz-step{padding:14px 16px;border-radius:12px;background:rgba(2,8,16,.6);
  border:1px solid rgba(0,229,255,.12);margin-bottom:12px;transition:.22s}
.wiz-step.done{border-color:rgba(34,224,138,.4);background:rgba(34,224,138,.06)}
.wiz-step .sh{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.wiz-step .sh .n{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;
  background:rgba(0,229,255,.15);color:var(--cyan);font-weight:900;font-size:12px}
.wiz-step.done .sh .n{background:rgba(34,224,138,.2);color:var(--green)}
.wiz-step .sh .t{font-size:12px;font-weight:800;letter-spacing:1.4px}
.wiz-step .status{font-size:11px;color:var(--mut);margin-top:8px;line-height:1.6}

@media(max-width:1100px){.g4{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:860px){
  .sidebar{position:fixed;left:0;top:0;height:100vh;transform:translateX(-105%);
    box-shadow:0 0 70px rgba(0,229,255,.22)}
  .sidebar.open{transform:translateX(0)}
  .icon-btn{display:grid}
  .content{padding:14px}
  .g4,.g3{grid-template-columns:1fr}
  .row2{grid-template-columns:1fr}
  .panel{padding:14px}
  .top-brand{font-size:11px;letter-spacing:1.4px}
  .card .big{font-size:24px}
  .search{max-width:100%;width:100%}
  .chip{display:none}
}
</style>
</head>
<body>
<canvas id="snow"></canvas>
<div id="toasts"></div>

<div class="app">
  <aside class="sidebar" id="sidebar">
    <div class="side-head">
      <div class="logo">SE</div>
      <div>
        <div class="side-title">SHAYAN_EXPLORER</div>
        <div class="side-sub">OSINT API CONTROL</div>
      </div>
    </div>
    <button class="nav-item active" data-view="overview"><span>◈</span> Overview</button>
    <button class="nav-item" data-view="keys"><span>🔑</span> API Keys</button>
    <button class="nav-item" data-view="logs"><span>▤</span> Request Logs</button>
    <button class="nav-item" data-view="revenue"><span>₹</span> Revenue</button>
    <button class="nav-item" data-view="docs"><span>❰❱</span> API Docs</button>
    <button class="nav-item admin-only" data-view="members" style="display:none"><span>👥</span> Members</button>
    <div class="side-foot">
      <div class="dev">API DEVELOPER<br><b>SHAYAN_EXPLORER</b></div>
      <a class="btn ghost" href="/admin/logout" onclick="sessionStorage.removeItem('auth')" style="text-align:center;text-decoration:none">LOGOUT</a>
    </div>
  </aside>
  <div class="overlay" id="overlay"></div>
  <div class="main">
    <header class="topbar">
      <button class="icon-btn" id="menuBtn" aria-label="menu">☰</button>
      <div class="top-brand">CONTROL CENTER<small>SHAYAN_EXPLORER · OSINT API</small></div>
      <div class="top-spacer"></div>
      <div class="chip">SYSTEM ONLINE</div>
      <div class="menu3-wrap">
        <button class="icon-btn-3dot" id="menu3Btn" aria-label="more">⋮</button>
        <div class="menu3" id="menu3">
          <button class="mi" onclick="refreshCurrent()"><span class="ic">🔄</span> Refresh</button>
          <button class="mi" onclick="copyAdminUrl()"><span class="ic">🔗</span> Copy Admin URL</button>
          <button class="mi" onclick="showView('docs');closeMenu3()"><span class="ic">❰❱</span> API Docs</button>
          <button class="mi admin-only" onclick="openTgModal();closeMenu3()" style="display:none"><span class="ic">🤖</span> Connect Telegram Bot</button>
          <div class="sep"></div>
          <a class="mi danger" href="/admin/logout" onclick="sessionStorage.removeItem('auth')"><span class="ic">🚪</span> Logout</a>
        </div>
      </div>
    </header>
    <div class="content">
      <!-- OVERVIEW -->
      <section class="view active" id="view-overview">
        <div class="grid g4">
          <div class="card"><h3>Total Keys</h3><div class="big" id="s-keys">—</div><div class="sub" id="s-keys-sub">&nbsp;</div></div>
          <div class="card"><h3>Active Keys</h3><div class="big" id="s-active">—</div><div class="sub" id="s-active-sub">&nbsp;</div></div>
          <div class="card"><h3>Total Requests</h3><div class="big" id="s-req">—</div><div class="sub" id="s-req-sub">&nbsp;</div></div>
          <div class="card"><h3>Total Revenue</h3><div class="big" id="s-rev">—</div><div class="sub" id="s-rev-sub">&nbsp;</div></div>
        </div>
        <div class="panel">
          <div class="panel-head">
            <h2>REVENUE · LAST 14 DAYS</h2>
            <div class="spacer"></div>
            <button class="btn ghost sm" onclick="loadOverview()">REFRESH</button>
          </div>
          <div class="chart" id="revChart"></div>
        </div>
        <div class="panel">
          <div class="panel-head"><h2>QUICK ACTIONS</h2></div>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <button class="btn" onclick="openKeyModal()">+ GENERATE KEY</button>
            <button class="btn ghost" onclick="showView('keys')">MANAGE KEYS</button>
            <button class="btn ghost" onclick="showView('logs')">VIEW LOGS</button>
            <button class="btn ghost" onclick="showView('docs')">API DOCS</button>
            <button class="btn ghost admin-only" style="display:none" onclick="openTgModal()">🤖 CONNECT TELEGRAM</button>
          </div>
        </div>
      </section>
      <!-- KEYS -->
      <section class="view" id="view-keys">
        <div class="panel" style="margin-top:0">
          <div class="panel-head">
            <h2>API KEY HISTORY</h2>
            <div class="spacer"></div>
            <input class="search" id="keySearch" placeholder="Search key / name / tool..." oninput="loadKeys()">
            <button class="btn" onclick="openKeyModal()">+ GENERATE KEY</button>
          </div>
          <div class="tbl-wrap">
            <table>
              <thead><tr>
                <th>Key</th><th>Name</th><th>Tools</th><th>Expiry</th>
                <th>Used / Limit</th><th>Price</th><th>By</th><th>Status</th><th>Actions</th>
              </tr></thead>
              <tbody id="keysBody"><tr><td colspan="9" class="empty">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
      </section>
      <!-- LOGS -->
      <section class="view" id="view-logs">
        <div class="panel" style="margin-top:0">
          <div class="panel-head">
            <h2>REQUEST LOGS</h2>
            <div class="spacer"></div>
            <input class="search" id="logSearch" placeholder="Search..." oninput="loadLogs()">
            <button class="btn ghost" onclick="loadLogs()">REFRESH</button>
          </div>
          <div class="tbl-wrap">
            <table>
              <thead><tr><th>Time</th><th>Key</th><th>Name</th><th>Tool</th><th>Query</th><th>IP</th><th>Status</th></tr></thead>
              <tbody id="logsBody"><tr><td colspan="7" class="empty">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
      </section>
      <!-- REVENUE -->
      <section class="view" id="view-revenue">
        <div class="panel" style="margin-top:0">
          <div class="panel-head">
            <h2>REVENUE ANALYTICS</h2>
            <div class="spacer"></div>
            <select id="revRange" style="max-width:170px" onchange="loadRevenue()">
              <option value="today">Today</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d" selected>Last 30 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="1y">Last 1 Year</option>
              <option value="all">All Time</option>
            </select>
          </div>
          <div class="grid g3">
            <div class="card"><h3>Revenue (Range)</h3><div class="big" id="r-range">₹0</div><div class="sub">selected period</div></div>
            <div class="card"><h3>Revenue (All Time)</h3><div class="big" id="r-total">₹0</div><div class="sub">lifetime earnings</div></div>
            <div class="card"><h3>Keys Sold</h3><div class="big" id="r-count">0</div><div class="sub">total keys</div></div>
          </div>
          <div class="chart" id="revChart2" style="margin-top:16px"></div>
        </div>
      </section>
      <!-- DOCS -->
      <section class="view" id="view-docs">
        <div class="panel" style="margin-top:0">
          <div class="panel-head">
            <h2>API ENDPOINTS</h2>
            <div class="spacer"></div>
            <button class="btn ghost sm" onclick="copyBaseUrl()">COPY BASE URL</button>
          </div>
          <p style="font-size:11.5px;color:var(--mut);margin:0 0 14px">
            Base URL: <span class="mono" id="baseUrl"></span> · Pass your key as <b>key</b> query parameter.
          </p>
          <div id="docsList"></div>
        </div>
      </section>
      <!-- MEMBERS -->
      <section class="view" id="view-members">
        <div class="panel" style="margin-top:0">
          <div class="panel-head">
            <h2>MEMBERS · Via Telegram Bot</h2>
            <div class="spacer"></div>
            <input class="search" id="memberSearch" placeholder="Search..." oninput="loadMembers()">
            <button class="btn ghost" onclick="openTgModal()">🤖 TELEGRAM BOT</button>
          </div>
          <div class="tbl-wrap">
            <table>
              <thead><tr>
                <th>Username</th><th>Name</th><th>Status</th>
                <th>Created</th><th>Last Login</th><th>Created By</th><th>Actions</th>
              </tr></thead>
              <tbody id="membersBody"><tr><td colspan="7" class="empty">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  </div>
</div>

<!-- KEY MODAL -->
<div class="modal" id="keyModal">
  <div class="modal-box">
    <h2 id="modalTitle">GENERATE API KEY</h2>
    <p class="hint">Custom key or auto-generated · choose tools · set expiry & limit</p>
    <label class="fl">API Key (custom or random)</label>
    <div style="display:flex;gap:8px">
      <input id="kKey" placeholder="Leave empty for auto key">
      <button class="btn ghost" style="flex:0 0 auto" onclick="randomKey()">🎲 RANDOM</button>
    </div>
    <label class="fl">Key Name</label>
    <input id="kName" placeholder="e.g. customer name / label">
    <label class="fl">Developer Name / "By" (Optional)</label>
    <input id="kByName" placeholder="SHAYAN_EXPLORER (default)">
    <div class="row2">
      <div><label class="fl">Request Limit (0 = unlimited)</label><input id="kLimit" type="number" min="0" value="0"></div>
      <div><label class="fl">Price (₹)</label><input id="kPrice" type="number" min="0" step="1" value="0"></div>
    </div>
    <label class="fl">Expiry Date &amp; Time (LOCAL time)</label>
    <input id="kExpiry" type="datetime-local">
    <div class="quick">
      <button class="btn ghost sm" onclick="setExpiry(3600000)">+1 HOUR</button>
      <button class="btn ghost sm" onclick="setExpiry(21600000)">+6 HOURS</button>
      <button class="btn ghost sm" onclick="setExpiry(86400000)">+1 DAY</button>
      <button class="btn ghost sm" onclick="setExpiry(604800000)">+7 DAYS</button>
      <button class="btn ghost sm" onclick="setExpiry(2592000000)">+30 DAYS</button>
    </div>
    <label class="fl" style="display:flex;align-items:center;gap:10px">
      <span>Allowed Tools</span>
      <button class="btn ghost sm" type="button" onclick="toggleAllTools()" id="selAllBtn">SELECT ALL</button>
    </label>
    <div class="toolgrid" id="toolGrid"></div>
    <label class="fl">Note</label>
    <input id="kNote" placeholder="optional note">
    <div style="display:flex;gap:10px;margin-top:22px">
      <button class="btn" style="flex:1" id="saveKeyBtn" onclick="saveKey()">GENERATE KEY</button>
      <button class="btn ghost" style="flex:0 0 auto" onclick="closeModal('keyModal')">CANCEL</button>
    </div>
  </div>
</div>

<!-- TELEGRAM MODAL -->
<div class="modal" id="tgModal">
  <div class="modal-box">
    <h2>🤖 CONNECT TELEGRAM BOT</h2>
    <p class="hint">4 steps · bot creates member logins via /generatekey</p>

    <div class="wiz-step" id="wiz1">
      <div class="sh"><div class="n">1</div><div class="t">BOT TOKEN</div></div>
      <input id="tgTokenInput" placeholder="123456:ABC-DEF...">
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn" style="flex:1" onclick="saveTgToken()">SAVE & VERIFY</button>
      </div>
      <div class="status" id="tgTokenStatus">Get token from @BotFather</div>
    </div>

    <div class="wiz-step" id="wiz2">
      <div class="sh"><div class="n">2</div><div class="t">YOUR CHAT ID</div></div>
      <input id="tgChatInput" placeholder="123456789">
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn" style="flex:1" onclick="saveTgChat()">SAVE CHAT ID</button>
      </div>
      <div class="status" id="tgChatStatus">Get chat ID from @userinfobot</div>
    </div>

    <div class="wiz-step" id="wiz3">
      <div class="sh"><div class="n">3</div><div class="t">PUBLIC URL</div></div>
      <input id="tgPublicInput" placeholder="https://your-app.up.railway.app">
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn" style="flex:1" onclick="saveTgPublic()">SAVE URL</button>
        <button class="btn ghost" onclick="autofillPublic()">USE THIS URL</button>
      </div>
      <div class="status" id="tgPublicStatus">Your Railway public domain</div>
    </div>

    <div class="wiz-step" id="wiz4">
      <div class="sh"><div class="n">4</div><div class="t">INSTALL & START BOT</div></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn green" style="flex:1;min-width:180px" onclick="installBot()">INSTALL / START BOT</button>
        <button class="btn ghost" onclick="testBot()">SEND TEST</button>
      </div>
      <div class="status" id="tgInstallStatus">After install, open Telegram & send /generatekey</div>
    </div>

    <div style="margin-top:16px;padding:12px;border-radius:12px;background:rgba(0,229,255,.06);border:1px solid rgba(0,229,255,.15);font-size:11px;color:var(--mut);line-height:1.8">
      <b style="color:var(--cyan)">🤖 Bot Commands:</b><br>
      <code>/generatekey</code> — create a member login<br>
      <code>/listmembers</code> — show latest members<br>
      <code>/help</code> — commands
    </div>

    <div style="display:flex;justify-content:flex-end;margin-top:16px">
      <button class="btn ghost" onclick="closeModal('tgModal')">CLOSE</button>
    </div>
  </div>
</div>

<script>
/* ---------- STRICT AUTH ---------- */
if (!sessionStorage.getItem('auth')) {
  location.replace('/admin/login');
}

/* ---------- HELPERS ---------- */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const esc = s => String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let TOOLS = []; let EDIT_ID = null; let ME = {role:'member'}; let REFRESH_TIMER = null;

/* ---------- BULLETPROOF LOCAL TIME CONVERSION ---------- */
// Converts "YYYY-MM-DDTHH:MM" (from datetime-local) to explicit LOCAL timezone ms.
// This is THE FIX for the expiry bug — no ambiguity across browsers/timezones.
function localDateTimeToMs(s){
  if(!s) return NaN;
  const [datePart, timePart] = s.split('T');
  if(!datePart || !timePart) return NaN;
  const [y, mo, d] = datePart.split('-').map(Number);
  const bits = timePart.split(':').map(Number);
  const h = bits[0] || 0, mi = bits[1] || 0, sec = bits[2] || 0;
  // new Date(y, mo-1, d, h, mi, sec) uses the BROWSER'S LOCAL TIMEZONE unambiguously.
  return new Date(y, mo - 1, d, h, mi, sec, 0).getTime();
}

function toast(msg, type='ok'){
  const d = document.createElement('div');
  d.className = 'toast ' + type; d.textContent = msg;
  $('#toasts').appendChild(d);
  setTimeout(()=>{ d.style.opacity='0'; d.style.transform='translateX(30px)'; d.style.transition='.3s'; }, 2600);
  setTimeout(()=> d.remove(), 3000);
}
async function jget(url){
  const r = await fetch(url, {credentials:'same-origin'});
  if(r.status === 401){ sessionStorage.removeItem('auth'); location.replace('/admin/login'); return null; }
  try { return await r.json(); } catch(e){ return {ok:false, error:'Bad response'}; }
}
async function jsend(url, method, body, btnEl){
  if(btnEl){ btnEl.classList.add('loading'); btnEl.disabled = true; }
  try {
    const r = await fetch(url, {
      method, credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body || {})
    });
    if(r.status === 401){ sessionStorage.removeItem('auth'); location.replace('/admin/login'); return null; }
    try { return await r.json(); } catch(e){ return {ok:false, error:'Bad response'}; }
  } finally {
    if(btnEl){ btnEl.classList.remove('loading'); btnEl.disabled = false; }
  }
}
async function copyText(text){
  try { await navigator.clipboard.writeText(text); toast('Copied ✅','ok'); return true; }
  catch(e){
    const ta = document.createElement('textarea');
    ta.value = text; ta.style.position='fixed'; ta.style.opacity='0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); toast('Copied ✅','ok'); }
    catch(_){ toast('Copy failed','err'); }
    document.body.removeChild(ta);
  }
}
function copyAdminUrl(){ copyText(location.origin + '/admin'); }
function copyBaseUrl(){ copyText(location.origin + '/api'); }

/* ---------- ANIMATED COUNTER ---------- */
function animateCount(el, target, prefix='', suffix=''){
  if(!el) return;
  const start = 0;
  const dur = 800; const t0 = performance.now();
  function step(t){
    const p = Math.min(1, (t - t0) / dur);
    const eased = 1 - Math.pow(1 - p, 3);
    const v = start + (target - start) * eased;
    el.textContent = prefix + (Number.isInteger(target) ? Math.round(v) : v.toFixed(2)) + suffix;
    if(p < 1) requestAnimationFrame(step);
    else el.textContent = prefix + target + suffix;
  }
  requestAnimationFrame(step);
}

/* ---------- SNOWFALL ---------- */
(function(){
  const c = document.getElementById('snow'); if(!c) return;
  const ctx = c.getContext('2d');
  let W, H;
  function resize(){ W = c.width = innerWidth; H = c.height = innerHeight; }
  resize(); addEventListener('resize', resize);
  const flakes = Array.from({length:60}, () => ({
    x: Math.random()*W, y: Math.random()*H, r: Math.random()*2.2+.3,
    dx: Math.random()*.4-.2, dy: Math.random()*.35+.15, o: Math.random()*.55+.2
  }));
  function tick(){
    ctx.clearRect(0,0,W,H);
    for(const f of flakes){
      ctx.beginPath(); ctx.arc(f.x,f.y,f.r,0,Math.PI*2);
      ctx.fillStyle = `rgba(220,240,255,${f.o})`; ctx.fill();
      f.x += f.dx; f.y += f.dy;
      if(f.y > H+5){ f.y = -5; f.x = Math.random()*W; }
      if(f.x < -5) f.x = W;
      if(f.x > W+5) f.x = 0;
    }
    requestAnimationFrame(tick);
  }
  tick();
})();

/* ---------- 3-DOT ---------- */
const menu3 = $('#menu3'), menu3Btn = $('#menu3Btn');
function closeMenu3(){ menu3.classList.remove('show'); }
menu3Btn.addEventListener('click', e => { e.stopPropagation(); menu3.classList.toggle('show'); });
document.addEventListener('click', e => {
  if(!menu3.contains(e.target) && e.target !== menu3Btn) closeMenu3();
});
function refreshCurrent(){
  const active = document.querySelector('.view.active');
  const id = active ? active.id.replace('view-','') : 'overview';
  if(id === 'overview') loadOverview();
  else if(id === 'keys') loadKeys();
  else if(id === 'logs') loadLogs();
  else if(id === 'revenue') loadRevenue();
  else if(id === 'docs') renderDocs();
  else if(id === 'members') loadMembers();
  toast('Refreshed','ok'); closeMenu3();
}

/* ---------- SIDEBAR ---------- */
const sidebar = $('#sidebar'), overlay = $('#overlay');
function openMenu(){ sidebar.classList.add('open'); overlay.classList.add('show'); }
function closeMenu(){ sidebar.classList.remove('open'); overlay.classList.remove('show'); }
$('#menuBtn').addEventListener('click', ()=>{
  if(sidebar.classList.contains('open')) closeMenu(); else openMenu();
});
overlay.addEventListener('click', closeMenu);
$$('.nav-item').forEach(b => b.addEventListener('click', ()=> showView(b.dataset.view)));

function showView(name){
  $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-'+name));
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.view === name));
  closeMenu();
  if(name === 'overview') loadOverview();
  if(name === 'keys') loadKeys();
  if(name === 'logs') loadLogs();
  if(name === 'revenue') loadRevenue();
  if(name === 'docs') renderDocs();
  if(name === 'members') loadMembers();
}

/* ---------- AUTO REFRESH every 15s (so expired status updates live) ---------- */
function startAutoRefresh(){
  if(REFRESH_TIMER) clearInterval(REFRESH_TIMER);
  REFRESH_TIMER = setInterval(() => {
    const active = document.querySelector('.view.active');
    if(!active) return;
    const id = active.id.replace('view-','');
    if(id === 'keys') loadKeys();
    else if(id === 'members') loadMembers();
    else if(id === 'overview') loadOverview();
  }, 15000);
}

/* ---------- OVERVIEW ---------- */
async function loadOverview(){
  const d = await jget('/admin/api/stats?range=30d');
  if(!d || !d.ok) return;
  animateCount($('#s-keys'), d.total_keys);
  $('#s-keys-sub').textContent = d.suspended_keys + ' suspended · ' + d.expired_keys + ' expired';
  animateCount($('#s-active'), d.active_keys);
  $('#s-active-sub').textContent = 'currently usable';
  animateCount($('#s-req'), d.total_requests);
  $('#s-req-sub').textContent = d.today_requests + ' today';
  animateCount($('#s-rev'), d.revenue_total, '₹');
  $('#s-rev-sub').textContent = '₹' + d.revenue_range + ' in last 30 days';
  drawChart('#revChart', d.series);
}
function drawChart(sel, series){
  const el = $(sel); if(!el) return;
  if(!series || !series.length){ el.innerHTML = '<div class="empty">No data</div>'; return; }
  const max = Math.max(1, ...series.map(s => s.amount));
  el.innerHTML = series.map(s => {
    const h = Math.max(4, Math.round((s.amount / max) * 120));
    return '<div class="bar" style="height:'+h+'px" title="'+esc(s.date)+' · ₹'+s.amount+' · '+s.count+' keys"><span>'+esc(s.date.slice(5))+'</span></div>';
  }).join('');
}

/* ---------- KEYS ---------- */
async function loadKeys(){
  const tb = $('#keysBody');
  // Skeleton while loading
  if(!tb.dataset.loaded){
    tb.innerHTML = '<tr><td colspan="9" style="padding:20px"><div class="skel" style="margin-bottom:8px"></div><div class="skel" style="margin-bottom:8px;width:80%"></div><div class="skel" style="width:60%"></div></td></tr>';
  }
  const q = $('#keySearch').value.trim();
  const d = await jget('/admin/api/keys?q=' + encodeURIComponent(q));
  if(!d || !d.ok) return;
  tb.dataset.loaded = '1';

  if(!d.keys.length){ tb.innerHTML = '<tr><td colspan="9" class="empty">No keys yet. Click "+ GENERATE KEY".</td></tr>'; return; }

  tb.innerHTML = d.keys.map(k => {
    let badge = '<span class="badge b-active">ACTIVE</span>';
    if(k.expired) badge = '<span class="badge b-exp">EXPIRED</span>';
    else if(k.status !== 'active') badge = '<span class="badge b-susp">SUSPENDED</span>';
    else if(k.seconds_left != null && k.seconds_left < 3600)
      badge = '<span class="badge b-warn">EXPIRING</span>';

    const exp = k.expires_at
      ? (new Date(k.expires_at).toLocaleString() + ' <span style="opacity:.6;font-size:10px">(' + esc(k.expires_human) + ')</span>')
      : 'Never';
    const lim = (k.req_limit > 0) ? (k.req_count + ' / ' + k.req_limit) : (k.req_count + ' / ∞');
    const tools = k.tools === 'all' ? '<b style="color:#22e08a">ALL TOOLS</b>' : esc(k.tools.split(',').join(', '));
    const byName = k.by_name ? esc(k.by_name) : '<span style="color:#7b93b5">Default</span>';

    return '<tr>' +
      '<td><span class="mono">'+esc(k.key)+'</span></td>' +
      '<td>'+esc(k.name)+'</td>' +
      '<td style="font-size:10.6px;max-width:190px">'+tools+'</td>' +
      '<td style="font-size:10.6px">'+exp+'</td>' +
      '<td style="font-size:11px">'+esc(lim)+'</td>' +
      '<td>₹'+ (k.price||0) +'</td>' +
      '<td>'+byName+'</td>' +
      '<td>'+badge+'</td>' +
      '<td><div class="acts">' +
        '<button class="btn ghost sm" data-act="copy" data-key="'+esc(k.key)+'">COPY</button>' +
        '<button class="btn ghost sm" data-act="edit" data-id="'+k.id+'">EDIT</button>' +
        '<button class="btn amber sm" data-act="reset" data-id="'+k.id+'">RESET</button>' +
        '<button class="btn green sm" data-act="toggle" data-id="'+k.id+'" data-status="'+k.status+'">'+(k.status==='active'?'SUSPEND':'UNSUSPEND')+'</button>' +
        '<button class="btn red sm" data-act="del" data-id="'+k.id+'">DELETE</button>' +
      '</div></td></tr>';
  }).join('');
}
$('#keysBody').addEventListener('click', async (e) => {
  const btn = e.target.closest('button[data-act]'); if(!btn) return;
  const act = btn.dataset.act;
  if(act === 'copy'){ copyText(btn.dataset.key); return; }
  if(act === 'edit'){
    const d = await jget('/admin/api/keys');
    const k = d.keys.find(x => String(x.id) === btn.dataset.id);
    if(k) openKeyModal(k);
    return;
  }
  if(act === 'reset'){
    if(!confirm('Reset request counter?')) return;
    const r = await jsend('/admin/api/keys/'+btn.dataset.id+'/reset', 'POST', {}, btn);
    toast(r && r.ok ? 'Counter reset' : 'Failed', r && r.ok ? 'ok' : 'err');
    loadKeys(); return;
  }
  if(act === 'toggle'){
    const newStatus = btn.dataset.status === 'active' ? 'suspended' : 'active';
    const r = await jsend('/admin/api/keys/'+btn.dataset.id, 'PATCH', {status:newStatus}, btn);
    toast(r && r.ok ? 'Status updated' : 'Failed', r && r.ok ? 'ok' : 'err');
    loadKeys(); return;
  }
  if(act === 'del'){
    if(!confirm('Delete this key permanently?')) return;
    const r = await jsend('/admin/api/keys/'+btn.dataset.id, 'DELETE', {}, btn);
    toast(r && r.ok ? 'Key deleted' : 'Failed', r && r.ok ? 'ok' : 'err');
    loadKeys(); return;
  }
});

/* ---------- KEY MODAL ---------- */
async function openKeyModal(k){
  EDIT_ID = k ? k.id : null;
  $('#modalTitle').textContent = k ? 'EDIT API KEY' : 'GENERATE API KEY';
  $('#saveKeyBtn').textContent = k ? 'SAVE CHANGES' : 'GENERATE KEY';
  $('#kKey').value = k ? k.key : '';
  $('#kKey').disabled = !!k;
  $('#kName').value = k ? (k.name || '') : '';
  $('#kByName').value = k ? (k.by_name || '') : '';
  $('#kLimit').value = k ? (k.req_limit || 0) : 0;
  $('#kPrice').value = k ? (k.price || 0) : 0;
  $('#kNote').value = k ? (k.note || '') : '';
  if(k && k.expires_ms) setExpiryAt(k.expires_ms); else setExpiry(86400000);
  await renderToolGrid(k ? (k.tools || 'all').split(',') : ['all']);
  $('#keyModal').classList.add('show');
  document.body.style.overflow = 'hidden';
}
function closeModal(id){ $('#'+id).classList.remove('show'); document.body.style.overflow = ''; }
function setExpiryAt(ms){
  const d = new Date(ms);
  const p = n => String(n).padStart(2,'0');
  $('#kExpiry').value = d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+'T'+p(d.getHours())+':'+p(d.getMinutes());
}
function setExpiry(offsetMs){ setExpiryAt(Date.now() + offsetMs); }
function randomKey(){
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; let out = 'FT-';
  for(let i=0;i<16;i++) out += chars[Math.floor(Math.random()*chars.length)];
  $('#kKey').value = out;
}
async function renderToolGrid(selected){
  if(!TOOLS.length){
    const d = await jget('/admin/api/tools');
    TOOLS = (d && d.tools) ? d.tools : [];
  }
  const sel = selected.map(s=>s.trim()).filter(Boolean);
  const all = sel.includes('all');
  $('#toolGrid').innerHTML = TOOLS.map(t =>
    '<label class="tool-item"><input type="checkbox" class="toolChk" value="'+esc(t.id)+'"'+
    ((all || sel.includes(t.id)) ? ' checked' : '')+'> '+esc(t.label)+'</label>'
  ).join('');
  updateSelAllBtn();
}
function toggleAllTools(){
  const boxes = $$('.toolChk');
  const allChecked = boxes.every(b => b.checked);
  boxes.forEach(b => b.checked = !allChecked);
  updateSelAllBtn();
}
function updateSelAllBtn(){
  const boxes = $$('.toolChk');
  const allChecked = boxes.length && boxes.every(b => b.checked);
  $('#selAllBtn').textContent = allChecked ? 'UNSELECT ALL' : 'SELECT ALL';
}
document.addEventListener('change', e => {
  if(e.target.classList && e.target.classList.contains('toolChk')) updateSelAllBtn();
});
async function saveKey(){
  const tools = $$('.toolChk').filter(b => b.checked).map(b => b.value);
  if(!tools.length){ toast('Select at least one tool', 'err'); return; }
  const expVal = $('#kExpiry').value;
  if(!expVal){ toast('Expiry required', 'err'); return; }

  // ⭐ THE FIX: explicit local timezone conversion (no ambiguity)
  const expires_ms = localDateTimeToMs(expVal);
  if(!expires_ms || isNaN(expires_ms)){
    toast('Invalid expiry time', 'err'); return;
  }
  if(expires_ms <= Date.now()){
    toast('Expiry must be in the future', 'err'); return;
  }

  const payload = {
    name: $('#kName').value.trim(),
    by_name: $('#kByName').value.trim(),
    tools: tools,
    expires_ms: expires_ms,
    req_limit: parseInt($('#kLimit').value || '0', 10) || 0,
    price: parseFloat($('#kPrice').value || '0') || 0,
    note: $('#kNote').value.trim()
  };
  const btn = $('#saveKeyBtn');
  let r;
  if(EDIT_ID) r = await jsend('/admin/api/keys/' + EDIT_ID, 'PATCH', payload, btn);
  else { payload.key = $('#kKey').value.trim(); r = await jsend('/admin/api/keys', 'POST', payload, btn); }
  if(r && r.ok){
    const min = Math.round((expires_ms - Date.now())/60000);
    toast((EDIT_ID ? 'Updated' : 'Generated') + ' · expires in ' + (min < 60 ? min+'m' : Math.round(min/60)+'h'), 'ok');
    closeModal('keyModal'); EDIT_ID = null;
    showView('keys'); loadKeys(); loadOverview();
  } else toast((r && r.error) || 'Failed', 'err');
}

/* ---------- LOGS ---------- */
async function loadLogs(){
  const q = $('#logSearch').value.trim();
  const d = await jget('/admin/api/logs?limit=300&q=' + encodeURIComponent(q));
  if(!d || !d.ok) return;
  const tb = $('#logsBody');
  if(!d.logs.length){ tb.innerHTML = '<tr><td colspan="7" class="empty">No logs yet.</td></tr>'; return; }
  tb.innerHTML = d.logs.map(l =>
    '<tr>' +
      '<td style="font-size:10.6px;white-space:nowrap">'+esc((l.ts||'').replace('T',' ').replace('+00:00',''))+'</td>' +
      '<td><span class="mono">'+esc(l.key)+'</span></td>' +
      '<td>'+esc(l.name)+'</td>' +
      '<td>'+esc(l.tool)+'</td>' +
      '<td style="font-size:10.6px;max-width:230px;word-break:break-all">'+esc(l.query)+'</td>' +
      '<td style="font-size:10.4px">'+esc(l.ip)+'</td>' +
      '<td><span class="badge '+(l.status==='OK'?'b-active':'b-exp')+'">'+esc(l.status)+'</span></td></tr>'
  ).join('');
}

/* ---------- REVENUE ---------- */
async function loadRevenue(){
  const rng = $('#revRange').value;
  const d = await jget('/admin/api/stats?range=' + rng);
  if(!d || !d.ok) return;
  animateCount($('#r-range'), d.revenue_range, '₹');
  animateCount($('#r-total'), d.revenue_total, '₹');
  animateCount($('#r-count'), d.total_keys);
  drawChart('#revChart2', d.series);
}

/* ---------- DOCS ---------- */
async function renderDocs(){
  if(!TOOLS.length){
    const d = await jget('/admin/api/tools');
    TOOLS = (d && d.tools) ? d.tools : [];
  }
  const base = location.origin + '/api';
  $('#baseUrl').textContent = base;
  $('#docsList').innerHTML = TOOLS.map(t => {
    const qs = ['key=YOUR_KEY'].concat(t.params.map(p => p + '=VALUE')).join('&');
    const fullUrl = base + '/' + t.id + '?' + qs;
    return '<div class="doc-item">' +
      '<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">' +
        '<div class="u" style="flex:1;min-width:200px">GET ' + esc(fullUrl) + '</div>' +
        '<button class="copy-inline" data-copy="' + esc(fullUrl) + '">📋 COPY</button>' +
      '</div>' +
      '<div class="d">' + esc(t.label) + ' · params: ' + esc(t.params.join(', ')) + '</div></div>';
  }).join('');
  document.querySelectorAll('.copy-inline').forEach(btn => {
    btn.onclick = async () => {
      await copyText(btn.dataset.copy);
      const orig = btn.textContent;
      btn.textContent = '✅ COPIED';
      btn.classList.add('copied');
      setTimeout(()=>{ btn.textContent = orig; btn.classList.remove('copied'); }, 1500);
    };
  });
}

/* ---------- MEMBERS ---------- */
async function loadMembers(){
  const q = ($('#memberSearch')?.value || '').trim();
  const d = await jget('/admin/api/members?q=' + encodeURIComponent(q));
  if(!d || !d.ok) return;
  const tb = $('#membersBody'); if(!tb) return;
  if(!d.members.length){
    tb.innerHTML = '<tr><td colspan="7" class="empty">No members yet. Use Telegram bot /generatekey.</td></tr>';
    return;
  }
  tb.innerHTML = d.members.map(m =>
    '<tr>' +
      '<td><span class="mono">'+esc(m.username)+'</span></td>' +
      '<td>'+esc(m.name || '—')+'</td>' +
      '<td><span class="badge '+(m.status==='active'?'b-active':'b-susp')+'">'+esc((m.status||'').toUpperCase())+'</span></td>' +
      '<td style="font-size:10.6px">'+esc((m.created_at||'').replace('T',' ').replace('+00:00',''))+'</td>' +
      '<td style="font-size:10.6px">'+esc(m.last_login ? m.last_login.replace('T',' ').replace('+00:00','') : 'never')+'</td>' +
      '<td style="font-size:10.6px">'+esc(m.created_by)+'</td>' +
      '<td><button class="btn red sm" data-act="del-member" data-id="'+m.id+'">DELETE</button></td></tr>'
  ).join('');
  tb.querySelectorAll('button[data-act="del-member"]').forEach(btn => {
    btn.onclick = async () => {
      if(!confirm('Delete this member?')) return;
      const r = await jsend('/admin/api/members/'+btn.dataset.id, 'DELETE', {}, btn);
      toast(r && r.ok ? 'Deleted' : 'Failed', r && r.ok ? 'ok' : 'err');
      loadMembers();
    };
  });
}

/* ---------- TELEGRAM WIZARD ---------- */
function openTgModal(){
  $('#tgModal').classList.add('show');
  document.body.style.overflow = 'hidden';
  loadTgConfig();
}
async function loadTgConfig(){
  const d = await jget('/admin/api/telegram/config');
  if(!d || !d.ok) return;
  if(d.token){ $('#tgTokenInput').value = d.token; $('#wiz1').classList.add('done'); $('#tgTokenStatus').innerHTML = '✅ Token saved'; }
  if(d.chat_id){ $('#tgChatInput').value = d.chat_id; $('#wiz2').classList.add('done'); $('#tgChatStatus').innerHTML = '✅ Chat ID saved'; }
  if(d.public_url){ $('#tgPublicInput').value = d.public_url; $('#wiz3').classList.add('done'); $('#tgPublicStatus').innerHTML = '✅ URL saved'; }
  refreshTgStatus();
}
async function refreshTgStatus(){
  const d = await jget('/admin/api/telegram/status');
  if(d && d.ok && d.configured){
    const info = (d.info && d.info.result) || {};
    if(info.url){
      $('#wiz4').classList.add('done');
      $('#tgInstallStatus').innerHTML = '✅ Bot installed · webhook: <span class="mono">'+esc(info.url)+'</span><br>Send <code>/generatekey</code>';
    }
  }
}
async function saveTgToken(){
  const token = $('#tgTokenInput').value.trim();
  if(!token){ toast('Paste token','err'); return; }
  const r = await jsend('/admin/api/telegram/save-token', 'POST', {token});
  if(r && r.ok){
    $('#wiz1').classList.add('done');
    $('#tgTokenStatus').innerHTML = '✅ Verified · @'+esc(r.bot_username);
    toast('Token saved','ok');
  } else {
    $('#tgTokenStatus').innerHTML = '❌ '+esc((r && r.error) || 'Failed');
    toast('Token failed','err');
  }
}
async function saveTgChat(){
  const chat_id = $('#tgChatInput').value.trim();
  if(!chat_id){ toast('Paste chat ID','err'); return; }
  const r = await jsend('/admin/api/telegram/save-chat', 'POST', {chat_id});
  if(r && r.ok){ $('#wiz2').classList.add('done'); $('#tgChatStatus').innerHTML = '✅ Chat ID saved'; toast('Saved','ok'); }
  else toast((r && r.error) || 'Failed','err');
}
async function saveTgPublic(){
  const url = $('#tgPublicInput').value.trim();
  if(!url){ toast('Paste URL','err'); return; }
  const r = await jsend('/admin/api/telegram/save-public', 'POST', {url});
  if(r && r.ok){ $('#wiz3').classList.add('done'); $('#tgPublicStatus').innerHTML = '✅ URL saved'; toast('Saved','ok'); }
  else toast((r && r.error) || 'Failed','err');
}
function autofillPublic(){ $('#tgPublicInput').value = location.origin; }
async function installBot(){
  $('#tgInstallStatus').textContent = '⏳ Installing...';
  const r = await jsend('/admin/api/telegram/install', 'POST', {});
  if(r && r.ok){
    $('#wiz4').classList.add('done');
    $('#tgInstallStatus').innerHTML = '✅ <b>Installed & started!</b>' + (r.test_sent ? '<br>✅ Test sent.' : '') + '<br>Send <code>/generatekey</code>';
    toast('Bot installed','ok');
  } else {
    $('#tgInstallStatus').innerHTML = '❌ ' + esc((r && r.error) || 'Failed');
    toast('Failed','err');
  }
}
async function testBot(){
  const r = await jsend('/admin/api/telegram/test', 'POST', {});
  if(r && r.ok) toast('Test sent ✅','ok');
  else toast((r && r.error) || 'Failed','err');
}

/* ---------- INIT ---------- */
(async function init(){
  const me = await jget('/admin/api/me');
  if(me && me.ok){
    ME = me;
    if(me.role === 'admin') document.querySelectorAll('.admin-only').forEach(el => el.style.display = '');
  }
  const d = await jget('/admin/api/tools');
  TOOLS = (d && d.tools) ? d.tools : [];
  loadOverview();
  loadKeys();
  startAutoRefresh();
})();
</script>
</body>
</html>"""

# ----------------------------- BOOT ------------------------------
init_db()

if __name__ == "__main__":
    print("=" * 62)
    print("  SHAYAN_EXPLORER · OSINT API CONTROL CENTER v4")
    print(f"  DB      : {DB_PATH}")
    print("  URL     : http://127.0.0.1:5000")
    print(f"  Admin   : {ADMIN_USER} / {ADMIN_PASS}")
    print(f"  Contact : @{TELEGRAM_CONTACT}")
    print(f"  Telegram: {'configured' if get_bot_token() else 'NOT configured (set via UI)'}")
    print("=" * 62)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
