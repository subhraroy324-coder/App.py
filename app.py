# ============================================================
#  SHAYAN_EXPLORER · OSINT API CONTROL CENTER
#  Developer: SHAYAN_EXPLORER
# ============================================================

import os
import sqlite3
import secrets
import stat
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, redirect, Response
import requests

# ----------------------------- CONFIG -----------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))

def _resolve_db_path():
    """Choose the DB path so data survives Render restarts."""
    if os.environ.get("DB_PATH"):
        return os.environ["DB_PATH"]
    if os.environ.get("RENDER"):
        return "/var/data/osint.db"
    if os.environ.get("VERCEL"):
        return "/tmp/osint.db"
    return os.path.join(APP_DIR, "osint.db")

DB_PATH = _resolve_db_path()

ADMIN_USER = os.environ.get("ADMIN_USER", "vernex")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "vernex@16vx")
SECRET_KEY = os.environ.get("SECRET_KEY", "shayan-explorer-super-secret-key")

UPSTREAM_BASE = os.environ.get("UPSTREAM_BASE", "https://ft-osint-api.duckdns.org/api").rstrip("/")
UPSTREAM_KEY = os.environ.get("UPSTREAM_KEY", "explorer16")
BRAND = os.environ.get("BRAND", "SHAYAN_EXPLORER")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    JSON_SORT_KEYS=False,
)

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

# ----------------------------- DB HELPERS --------------------------------
def _ensure_db_dir():
    """Forces the creation of the directory and sets permissions for Render."""
    parent = os.path.dirname(DB_PATH)
    if parent and not os.path.isdir(parent):
        try:
            os.makedirs(parent, exist_ok=True)
            os.chmod(parent, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) 
        except Exception as e:
            print(f"Warning: Could not create DB directory: {e}")

def _conn():
    _ensure_db_dir()
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        c.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    return c

def db_fetch(sql, args=()):
    c = _conn()
    try:
        cur = c.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]
    finally:
        c.close()

def db_one(sql, args=()):
    rows = db_fetch(sql, args)
    return rows[0] if rows else None

def db_write(sql, args=()):
    c = _conn()
    try:
        cur = c.execute(sql, args)
        c.commit()
        return cur.lastrowid
    finally:
        c.close()

def init_db():
    _ensure_db_dir()
    c = _conn()
    try:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.executescript("""
        CREATE TABLE IF NOT EXISTS api_keys(
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT UNIQUE NOT NULL,
            name        TEXT DEFAULT '',
            by_name     TEXT DEFAULT '',
            tools       TEXT DEFAULT 'all',
            created_at  TEXT NOT NULL,
            expires_at  TEXT,
            req_limit   INTEGER DEFAULT 0,
            req_count   INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'active',
            price       REAL DEFAULT 0,
            note        TEXT DEFAULT '',
            last_used   TEXT
        );
        CREATE TABLE IF NOT EXISTS logs(
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            key     TEXT,
            name    TEXT,
            tool    TEXT,
            query   TEXT,
            ip      TEXT,
            status  TEXT,
            ts      TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_logs_key ON logs(key);
        CREATE INDEX IF NOT EXISTS idx_logs_ts  ON logs(ts);
        """)
        try:
            c.execute("ALTER TABLE api_keys ADD COLUMN by_name TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        c.commit()
    finally:
        c.close()

# ----------------------------- TIME ------------------------------
def now_utc():
    return datetime.now(timezone.utc)

def iso(dt):
    if dt is None: return None
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")

def parse_iso(s):
    if not s: return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except Exception:
        return None

def ms_to_iso(ms):
    try: return iso(datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc))
    except Exception: return None

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

# ----------------------------- KEY HELPERS -----------------------
def key_state(row):
    if not row: return row
    exp = parse_iso(row.get("expires_at"))
    row["expired"] = bool(exp and now_utc() > exp)
    row["expires_ms"] = int(exp.timestamp() * 1000) if exp else None
    lim = int(row.get("req_limit") or 0)
    used = int(row.get("req_count") or 0)
    row["remaining"] = max(0, lim - used) if lim > 0 else None
    return row

def check_key(key, tool_id):
    row = db_one("SELECT * FROM api_keys WHERE key = ?", (key,))
    if not row: return None, (jsonify(ok=False, error="Invalid API key"), 401)
    if row["status"] != "active": return None, (jsonify(ok=False, error="API key suspended"), 403)
    exp = parse_iso(row["expires_at"])
    if exp and now_utc() > exp: return None, (jsonify(ok=False, error="API key expired"), 403)
    
    allowed = (row["tools"] or "all").split(",")
    if "all" not in allowed and tool_id not in allowed:
        return None, (jsonify(ok=False, error=f"Key not allowed for tool '{tool_id}'"), 403)

    lim = int(row["req_limit"] or 0)
    if lim > 0 and int(row["req_count"] or 0) >= lim:
        return None, (jsonify(ok=False, error="Request limit reached"), 429)

    return row, None

def log_request(key, name, tool, query, status):
    db_write(
        "INSERT INTO logs(key,name,tool,query,ip,status,ts) VALUES (?,?,?,?,?,?,?)",
        (key, name, tool, str(query)[:400], request.headers.get("X-Forwarded-For", request.remote_addr or ""), status, iso(now_utc()))
    )

# ----------------------------- PROXY API -------------------------
@app.route("/api/<tool_id>", methods=["GET"])
def proxy(tool_id):
    t = TOOL_MAP.get(tool_id)
    if not t: return jsonify(ok=False, error="Unknown endpoint"), 404

    user_key = (request.args.get("key") or "").strip()
    if not user_key: return jsonify(ok=False, error="Missing key parameter"), 401

    row, err = check_key(user_key, tool_id)
    if err:
        log_request(user_key, (row or {}).get("name", ""), tool_id, request.query_string.decode()[:300], "DENIED")
        return err

    params = {}
    for p in t["params"]:
        v = (request.args.get(p) or "").strip()
        if not v: return jsonify(ok=False, error=f"Missing parameter '{p}'"), 400
        params[p] = v

    payload = dict(params)
    payload["key"] = UPSTREAM_KEY

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
                db_write("UPDATE api_keys SET req_count = req_count + 1, last_used = ? WHERE id = ?", (iso(now_utc()), row["id"]))
                log_request(user_key, row["name"], tool_id, str(params), "OK")
                return jsonify(data), up.status_code
        except Exception:
            pass 

    db_write("UPDATE api_keys SET req_count = req_count + 1, last_used = ? WHERE id = ?", (iso(now_utc()), row["id"]))
    log_request(user_key, row["name"], tool_id, str(params), "OK")
    return Response(content, status=up.status_code, content_type=ctype)

# ----------------------------- ROUTES ----------------------------
@app.route("/")
def root():
    return redirect("/admin")

@app.route("/health")
def health():
    db_ok = True
    try:
        db_one("SELECT 1 AS x")
    except Exception:
        db_ok = False
    return jsonify(
        ok=True, brand=BRAND, time=iso(now_utc()),
        db_path=DB_PATH, db_ok=db_ok,
        persistent=bool(os.environ.get("RENDER") or os.environ.get("DB_PATH"))
    )

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        u = (data.get("username") or "").strip()
        p = (data.get("password") or "").strip()
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin"] = True
            session["admin_user"] = u
            return redirect("/admin")
        return Response(LOGIN_HTML.replace("__ERR__", "Invalid username or password"), 401, content_type="text/html")
    return Response(LOGIN_HTML.replace("__ERR__", ""), content_type="text/html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")

@app.route("/admin")
@admin_required
def admin_home():
    return Response(DASH_HTML, content_type="text/html")

# ----------------------------- ADMIN API -------------------------
@app.route("/admin/api/tools")
@admin_required
def api_tools():
    return jsonify(ok=True, tools=TOOLS)

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
        amt = 0.0
        cnt = 0
        for k in keys:
            cd = parse_iso(k["created_at"])
            if cd and cd.date() == d:
                amt += float(k["price"] or 0)
                cnt += 1
        series.append({"date": d.isoformat(), "amount": round(amt, 2), "count": cnt})

    return jsonify(ok=True, total_keys=total_keys, active_keys=active_keys, suspended_keys=suspended, expired_keys=expired,
                   total_requests=total_requests, today_requests=today_requests, revenue_total=round(rev_total, 2), 
                   revenue_range=round(rev_range, 2), range=rng, series=series)

@app.route("/admin/api/keys", methods=["GET"])
@admin_required
def api_keys_list():
    q = (request.args.get("q") or "").strip().lower()
    rows = [key_state(r) for r in db_fetch("SELECT * FROM api_keys ORDER BY id DESC")]
    if q:
        rows = [r for r in rows if q in (r["key"] or "").lower() or q in (r["name"] or "").lower() or q in (r["tools"] or "").lower()]
    return jsonify(ok=True, keys=rows)

@app.route("/admin/api/keys", methods=["POST"])
@admin_required
def api_keys_create():
    d = request.get_json(silent=True) or {}
    key = (d.get("key") or "").strip()
    if not key: key = "FT-" + secrets.token_hex(10).upper()
    if len(key) < 6: return jsonify(ok=False, error="Custom key must be at least 6 characters"), 400
    if not all(ch.isalnum() or ch in "-_." for ch in key): return jsonify(ok=False, error="Key may only contain letters, numbers, - _ ."), 400

    if db_one("SELECT id FROM api_keys WHERE key = ?", (key,)): return jsonify(ok=False, error="This key already exists"), 409
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
    if not row: return jsonify(ok=False, error="Key not found"), 404

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
    if "expires_ms" in d: updates["expires_at"] = ms_to_iso(d.get("expires_ms")) if d.get("expires_ms") else None
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
    if not db_one("SELECT id FROM api_keys WHERE id=?", (kid,)): return jsonify(ok=False, error="Key not found"), 404
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

    sql = "SELECT * FROM logs WHERE 1=1"
    args = []
    if key: sql += " AND key = ?"; args.append(key)
    if q:
        sql += " AND (key LIKE ? OR name LIKE ? OR tool LIKE ? OR query LIKE ?)"
        like = f"%{q}%"; args += [like, like, like, like]
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    return jsonify(ok=True, logs=db_fetch(sql, tuple(args)))

# ============================================================
#                          LOGIN PAGE
# ============================================================
LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SHAYAN_EXPLORER · Secure Login</title>
<style>
:root{--cyan:#00e5ff;--violet:#8b5cf6;--txt:#dceaff;--mut:#7b93b5;--red:#ff4d6d;--green:#22e08a}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;display:flex;align-items:center;justify-content:center;padding:20px;
  font-family:"Segoe UI",Inter,system-ui,-apple-system,sans-serif;color:var(--txt);
  background:radial-gradient(900px 600px at 15% 0%,rgba(0,229,255,.16),transparent 60%),
    radial-gradient(800px 600px at 90% 100%,rgba(139,92,246,.18),transparent 60%), #03060d;}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(0,229,255,.07) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(0,229,255,.07) 1px,transparent 1px);
  background-size:54px 54px;
  -webkit-mask-image:radial-gradient(circle at 50% 40%,#000 10%,transparent 75%);
          mask-image:radial-gradient(circle at 50% 40%,#000 10%,transparent 75%);
  animation:grid 20s linear infinite}
@keyframes grid{to{background-position:54px 54px,54px 54px}}
.wrap{position:relative;z-index:2;width:100%;max-width:420px;perspective:1200px}
.card{background:linear-gradient(160deg,rgba(14,26,45,.94),rgba(5,10,20,.96));
  border:1px solid rgba(0,229,255,.22);border-radius:22px;padding:34px 28px;
  box-shadow:0 40px 90px -40px rgba(0,229,255,.6),0 0 0 1px rgba(255,255,255,.03) inset;
  transform:rotateX(4deg);animation:float 6s ease-in-out infinite}
@keyframes float{0%,100%{transform:rotateX(4deg) translateY(0)}50%{transform:rotateX(4deg) translateY(-8px)}}
.logo{width:64px;height:64px;margin:0 auto 16px;border-radius:18px;display:grid;place-items:center;
  font-weight:900;font-size:22px;letter-spacing:1px;color:#02121a;
  background:linear-gradient(135deg,#00e5ff,#8b5cf6);
  box-shadow:0 0 34px rgba(0,229,255,.65)}
h1{font-size:20px;margin:0;text-align:center;letter-spacing:3px;font-weight:800}
.sub{text-align:center;color:var(--mut);font-size:11px;letter-spacing:2.6px;margin:6px 0 26px}
label{display:block;font-size:11px;letter-spacing:1.6px;color:var(--mut);margin:14px 0 6px;text-transform:uppercase}
input{width:100%;padding:13px 14px;border-radius:12px;background:rgba(2,8,16,.85);
  border:1px solid rgba(0,229,255,.2);color:var(--txt);font-size:14px;outline:none;transition:.2s}
input:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(0,229,255,.15)}
button{width:100%;margin-top:24px;padding:14px;border:0;border-radius:12px;cursor:pointer;
  font-weight:800;letter-spacing:1.6px;font-size:13px;color:#02121a;
  background:linear-gradient(135deg,#00e5ff,#3b82f6);box-shadow:0 16px 34px -16px rgba(0,229,255,.9);transition:.2s}
button:hover{transform:translateY(-2px);box-shadow:0 22px 44px -18px rgba(0,229,255,1)}
.err{background:rgba(255,77,109,.12);border:1px solid rgba(255,77,109,.4);color:#ffb3c1;
  padding:10px 12px;border-radius:10px;font-size:12.5px;margin-bottom:8px;text-align:center}
.foot{margin-top:22px;text-align:center;font-size:10.5px;letter-spacing:1.6px;color:var(--mut)}
.foot b{color:var(--cyan)}
#hacker-overlay{display:none;position:fixed;inset:0;background:#000;color:#0f0;
  font-family:'Courier New',monospace;z-index:9999;padding:40px;font-size:16px;
  text-shadow:0 0 5px #0f0;overflow:hidden}
#hacker-text{line-height:1.6}
#hacker-text div{margin-bottom:5px}
.blink{animation:blink 1s step-end infinite}
@keyframes blink{50%{opacity:0}}
.scanline{position:absolute;top:0;left:0;width:100%;height:100%;
  background:linear-gradient(to bottom,rgba(255,255,255,0),rgba(255,255,255,0) 50%,rgba(0,255,0,0.1) 50%,rgba(0,255,0,0.1));
  background-size:100% 4px;pointer-events:none;opacity:0.3}
</style>
</head>
<body>
<div id="hacker-overlay"><div class="scanline"></div><div id="hacker-text"></div></div>
<div class="wrap">
  <div class="card">
    <div class="logo">SE</div>
    <h1>SHAYAN_EXPLORER</h1>
    <div class="sub">OSINT API · CONTROL CENTER</div>
    __ERRBLOCK__
    <form method="post" autocomplete="off" id="loginForm" onsubmit="startHacking(event)">
      <label>Username</label>
      <input name="username" id="uName" placeholder="Enter username" required autofocus>
      <label>Password</label>
      <input name="password" id="pWord" type="password" placeholder="Enter password" required>
      <button type="submit">AUTHENTICATE</button>
    </form>
    <div class="foot">API DEVELOPER · <b>SHAYAN_EXPLORER</b></div>
  </div>
</div>
<script>
function startHacking(e) {
  e.preventDefault();
  const overlay = document.getElementById('hacker-overlay');
  const textDiv = document.getElementById('hacker-text');
  overlay.style.display = 'block';
  const lines = [
    "> [SYSTEM] Initializing SHAYAN_EXPLORER OSINT Engine...",
    "> [AUTH] Checking credentials...",
    "> [NET] Bypassing firewall protocols...",
    "> [SEC] Injecting payload...",
    "> [DB] Connecting to secure database...",
    "> [SYSTEM] Access Granted. Loading Dashboard..."
  ];
  let i = 0;
  const interval = setInterval(() => {
    if (i < lines.length) {
      const p = document.createElement('div');
      p.textContent = lines[i];
      if (i === lines.length - 1) p.innerHTML += ' <span class="blink">_</span>';
      textDiv.appendChild(p); i++;
    } else {
      clearInterval(interval);
      setTimeout(() => { document.getElementById('loginForm').submit(); }, 500);
    }
  }, 400);
}
</script>
</body>
</html>"""
LOGIN_HTML = LOGIN_HTML.replace("__ERRBLOCK__", '<div class="err">__ERR__</div>')

# ============================================================
#                        DASHBOARD PAGE
# ============================================================
DASH_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>SHAYAN_EXPLORER · OSINT API CONTROL</title>
<style>
:root{
  --bg:#03060d;--panel:rgba(10,18,32,.82);--panel2:rgba(13,24,42,.7);
  --line:rgba(0,229,255,.16);--cyan:#00e5ff;--blue:#3b82f6;--violet:#8b5cf6;
  --green:#22e08a;--red:#ff4d6d;--amber:#ffb020;--txt:#dceaff;--mut:#7b93b5;--r:16px;
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;font-family:"Segoe UI",Inter,system-ui,-apple-system,sans-serif;
  color:var(--txt);background:var(--bg);overflow-x:hidden}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(1100px 650px at 10% -10%,rgba(0,229,255,.13),transparent 60%),
    radial-gradient(900px 600px at 100% 0%,rgba(139,92,246,.14),transparent 55%),
    radial-gradient(900px 700px at 50% 120%,rgba(59,130,246,.12),transparent 60%);}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(0,229,255,.045) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(0,229,255,.045) 1px,transparent 1px);
  background-size:58px 58px;animation:grid 24s linear infinite;
  -webkit-mask-image:radial-gradient(circle at 50% 30%,#000 15%,transparent 80%);
          mask-image:radial-gradient(circle at 50% 30%,#000 15%,transparent 80%)}
@keyframes grid{to{background-position:58px 58px,58px 58px}}
.app{position:relative;z-index:2;display:flex;min-height:100vh}
.sidebar{width:250px;flex:0 0 250px;padding:20px 14px;display:flex;flex-direction:column;gap:8px;
  background:linear-gradient(180deg,rgba(8,16,30,.95),rgba(4,9,18,.92));
  border-right:1px solid var(--line);position:sticky;top:0;height:100vh;overflow-y:auto;
  transition:transform .28s ease;z-index:60}
.side-head{display:flex;gap:12px;align-items:center;padding:6px 6px 18px;border-bottom:1px solid var(--line);margin-bottom:10px}
.logo{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;font-weight:900;font-size:15px;
  color:#02121a;background:linear-gradient(135deg,#00e5ff,#8b5cf6);box-shadow:0 0 26px rgba(0,229,255,.6);flex:0 0 44px}
.side-title{font-size:12.5px;font-weight:800;letter-spacing:1.6px}
.side-sub{font-size:9px;letter-spacing:2px;color:var(--mut);margin-top:3px}
.nav-item{display:flex;align-items:center;gap:11px;width:100%;padding:12px 13px;border-radius:12px;
  background:transparent;border:1px solid transparent;color:var(--mut);font-size:13px;font-weight:600;
  cursor:pointer;text-align:left;transition:.18s;letter-spacing:.3px;font-family:inherit}
.nav-item span{width:20px;text-align:center;font-size:14px;opacity:.9}
.nav-item:hover{background:rgba(0,229,255,.07);color:var(--txt);border-color:rgba(0,229,255,.14)}
.nav-item.active{background:linear-gradient(90deg,rgba(0,229,255,.18),rgba(0,229,255,.02));
  color:#fff;border-color:rgba(0,229,255,.35);box-shadow:0 0 24px -10px rgba(0,229,255,.9)}
.side-foot{margin-top:auto;padding-top:14px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:10px}
.dev{font-size:9.5px;letter-spacing:1.6px;color:var(--mut);text-align:center}
.dev b{color:var(--cyan);font-size:11px;letter-spacing:1.4px}
.main{flex:1;min-width:0;display:flex;flex-direction:column}
.topbar{display:flex;align-items:center;gap:14px;padding:14px 20px;position:sticky;top:0;z-index:50;
  background:rgba(4,9,18,.82);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.icon-btn{width:40px;height:40px;border-radius:11px;border:1px solid var(--line);background:rgba(0,229,255,.07);
  color:var(--cyan);font-size:17px;cursor:pointer;display:none;place-items:center;transition:.18s}
.icon-btn:hover{background:rgba(0,229,255,.18)}
.top-brand{font-size:13px;font-weight:800;letter-spacing:2px}
.top-brand small{display:block;font-size:9px;letter-spacing:2.4px;color:var(--mut);font-weight:600;margin-top:2px}
.top-spacer{flex:1}
.chip{font-size:10px;letter-spacing:1.4px;padding:7px 12px;border-radius:999px;
  border:1px solid rgba(34,224,138,.4);color:var(--green);background:rgba(34,224,138,.09)}
.content{padding:22px;flex:1}
.view{display:none;animation:fade .35s ease}
.view.active{display:block}
@keyframes fade{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.grid{display:grid;gap:16px}
.g4{grid-template-columns:repeat(4,1fr)}
.g3{grid-template-columns:repeat(3,1fr)}
.g2{grid-template-columns:repeat(2,1fr)}
.card{background:linear-gradient(160deg,rgba(13,24,42,.9),rgba(6,12,24,.88));
  border:1px solid var(--line);border-radius:var(--r);padding:18px;position:relative;
  box-shadow:0 20px 44px -28px rgba(0,229,255,.55),inset 0 1px 0 rgba(255,255,255,.05);
  transition:transform .3s,box-shadow .3s;transform-style:preserve-3d}
.card:hover{transform:translateY(-4px) rotateX(1.5deg);box-shadow:0 30px 60px -26px rgba(0,229,255,.75)}
.card h3{margin:0 0 4px;font-size:11px;letter-spacing:2px;color:var(--mut);font-weight:700;text-transform:uppercase}
.card .big{font-size:29px;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,#fff,#7fe9ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.card .sub{font-size:11px;color:var(--mut);margin-top:6px}
.card.glow::after{content:"";position:absolute;inset:auto 12px 0 12px;height:2px;border-radius:2px;
  background:linear-gradient(90deg,transparent,var(--cyan),transparent);opacity:.7}
.panel{background:linear-gradient(160deg,rgba(11,20,36,.92),rgba(5,10,20,.9));
  border:1px solid var(--line);border-radius:var(--r);padding:18px;margin-top:18px;
  box-shadow:0 20px 50px -34px rgba(0,229,255,.6)}
.panel-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.panel-head h2{margin:0;font-size:13px;letter-spacing:2.2px;font-weight:800;color:#eaf6ff}
.panel-head .spacer{flex:1}
.btn{padding:10px 16px;border-radius:11px;border:1px solid rgba(0,229,255,.35);
  background:linear-gradient(135deg,rgba(0,229,255,.2),rgba(59,130,246,.16));
  color:#eaffff;font-size:12px;font-weight:700;letter-spacing:1.1px;cursor:pointer;transition:.18s;font-family:inherit}
.btn:hover{transform:translateY(-2px);box-shadow:0 14px 30px -14px rgba(0,229,255,.9)}
.btn.ghost{background:transparent;border-color:var(--line);color:var(--mut)}
.btn.ghost:hover{color:#fff;border-color:rgba(0,229,255,.5)}
.btn.red{border-color:rgba(255,77,109,.45);background:rgba(255,77,109,.12);color:#ffb3c1}
.btn.green{border-color:rgba(34,224,138,.45);background:rgba(34,224,138,.12);color:#9ff5cd}
.btn.amber{border-color:rgba(255,176,32,.45);background:rgba(255,176,32,.12);color:#ffd894}
.btn.sm{padding:7px 11px;font-size:10.5px;letter-spacing:.8px;border-radius:9px}
input,select,textarea{width:100%;padding:11px 13px;border-radius:11px;background:rgba(2,8,16,.9);
  border:1px solid rgba(0,229,255,.18);color:var(--txt);font-size:13px;outline:none;font-family:inherit;transition:.18s}
input:focus,select:focus,textarea:focus{border-color:var(--cyan);box-shadow:0 0 0 3px rgba(0,229,255,.13)}
.search{max-width:280px}
label.fl{display:block;font-size:10px;letter-spacing:1.6px;color:var(--mut);margin:14px 0 6px;text-transform:uppercase;font-weight:700}
.tbl-wrap{overflow-x:auto;border-radius:12px;border:1px solid rgba(0,229,255,.1)}
table{width:100%;border-collapse:collapse;font-size:12.3px;min-width:760px}
th{text-align:left;padding:11px 12px;font-size:9.6px;letter-spacing:1.7px;color:var(--mut);
  text-transform:uppercase;background:rgba(0,229,255,.05);border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:11px 12px;border-bottom:1px solid rgba(0,229,255,.07);vertical-align:middle}
tr:hover td{background:rgba(0,229,255,.04)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.4px;color:#9de8ff;word-break:break-all}
.badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:9.6px;letter-spacing:1.1px;font-weight:800}
.b-active{background:rgba(34,224,138,.14);color:var(--green);border:1px solid rgba(34,224,138,.35)}
.b-susp{background:rgba(255,176,32,.13);color:var(--amber);border:1px solid rgba(255,176,32,.35)}
.b-exp{background:rgba(255,77,109,.13);color:var(--red);border:1px solid rgba(255,77,109,.35)}
.acts{display:flex;gap:6px;flex-wrap:wrap}
.modal{position:fixed;inset:0;z-index:200;display:none;align-items:center;justify-content:center;padding:18px;
  background:rgba(2,6,14,.82);backdrop-filter:blur(7px)}
.modal.show{display:flex}
.modal-box{width:100%;max-width:640px;max-height:90vh;overflow-y:auto;border-radius:20px;padding:24px;
  background:linear-gradient(160deg,rgba(13,24,42,.98),rgba(5,10,20,.99));
  border:1px solid rgba(0,229,255,.3);box-shadow:0 50px 110px -40px rgba(0,229,255,.85);
  animation:pop .28s cubic-bezier(.2,1.2,.4,1)}
@keyframes pop{from{opacity:0;transform:scale(.94) translateY(14px)}to{opacity:1;transform:none}}
.modal-box h2{margin:0 0 4px;font-size:15px;letter-spacing:2px}
.modal-box p.hint{margin:0 0 8px;font-size:11px;color:var(--mut)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.toolgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:8px;max-height:210px;
  overflow-y:auto;padding:10px;border-radius:12px;background:rgba(2,8,16,.6);border:1px solid rgba(0,229,255,.12)}
.tool-item{display:flex;align-items:center;gap:8px;padding:7px 9px;border-radius:9px;cursor:pointer;
  font-size:11.4px;border:1px solid transparent;transition:.15s;color:var(--mut)}
.tool-item:hover{background:rgba(0,229,255,.07);color:var(--txt)}
.tool-item input{width:15px;height:15px;accent-color:#00e5ff;cursor:pointer;flex:0 0 15px}
.quick{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.chart{display:flex;align-items:flex-end;gap:7px;height:170px;padding:14px;border-radius:14px;
  background:rgba(2,8,16,.6);border:1px solid rgba(0,229,255,.1)}
.bar{flex:1;border-radius:6px 6px 3px 3px;min-height:4px;position:relative;
  background:linear-gradient(180deg,#00e5ff,#3b82f6);box-shadow:0 0 18px -6px rgba(0,229,255,.9);transition:height .5s}
.bar:hover{background:linear-gradient(180deg,#8b5cf6,#00e5ff)}
.bar span{position:absolute;bottom:-19px;left:0;right:0;text-align:center;font-size:8.4px;color:var(--mut)}
#toasts{position:fixed;top:16px;right:16px;z-index:999;display:flex;flex-direction:column;gap:9px;max-width:330px}
.toast{padding:12px 16px;border-radius:12px;font-size:12.4px;font-weight:600;
  background:rgba(9,18,32,.97);border:1px solid rgba(0,229,255,.35);color:#dff7ff;
  box-shadow:0 20px 44px -20px rgba(0,229,255,.9);animation:slide .3s ease}
.toast.err{border-color:rgba(255,77,109,.55);color:#ffc2cc}
.toast.ok{border-color:rgba(34,224,138,.55);color:#a8f7d2}
@keyframes slide{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:none}}
.empty{padding:26px;text-align:center;color:var(--mut);font-size:12px}
.overlay{position:fixed;inset:0;background:rgba(2,6,14,.7);backdrop-filter:blur(3px);
  z-index:55;display:none}
.overlay.show{display:block}
.doc-item{padding:13px 14px;border-radius:12px;background:rgba(2,8,16,.6);
  border:1px solid rgba(0,229,255,.1);margin-bottom:9px}
.doc-item .u{font-family:ui-monospace,Menlo,monospace;font-size:11.6px;color:#8ce8ff;word-break:break-all}
.doc-item .d{font-size:10.4px;color:var(--mut);margin-top:4px;letter-spacing:.6px}
@media(max-width:1100px){.g4{grid-template-columns:repeat(2,1fr)}.g3{grid-template-columns:repeat(2,1fr)}}
@media(max-width:860px){
  .sidebar{position:fixed;left:0;top:0;height:100vh;transform:translateX(-105%);
    box-shadow:0 0 70px rgba(0,229,255,.22)}
  .sidebar.open{transform:translateX(0)}
  .icon-btn{display:grid}
  .content{padding:14px}
  .g4,.g3,.g2{grid-template-columns:1fr}
  .row2{grid-template-columns:1fr}
  .panel{padding:14px}
  .top-brand{font-size:11px;letter-spacing:1.4px}
  .card .big{font-size:24px}
  .search{max-width:100%;width:100%}
}
</style>
</head>
<body>
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
    <div class="side-foot">
      <div class="dev">API DEVELOPER<br><b>SHAYAN_EXPLORER</b></div>
      <a class="btn ghost" href="/admin/logout" style="text-align:center;text-decoration:none">LOGOUT</a>
    </div>
  </aside>
  <div class="overlay" id="overlay"></div>
  <div class="main">
    <header class="topbar">
      <button class="icon-btn" id="menuBtn" aria-label="menu">☰</button>
      <div class="top-brand">CONTROL CENTER<small>SHAYAN_EXPLORER · OSINT API</small></div>
      <div class="top-spacer"></div>
      <div class="chip">● SYSTEM ONLINE</div>
    </header>
    <div class="content">
      <section class="view active" id="view-overview">
        <div class="grid g4">
          <div class="card glow"><h3>Total Keys</h3><div class="big" id="s-keys">0</div><div class="sub" id="s-keys-sub">—</div></div>
          <div class="card glow"><h3>Active Keys</h3><div class="big" id="s-active">0</div><div class="sub" id="s-active-sub">—</div></div>
          <div class="card glow"><h3>Total Requests</h3><div class="big" id="s-req">0</div><div class="sub" id="s-req-sub">—</div></div>
          <div class="card glow"><h3>Total Revenue</h3><div class="big" id="s-rev">₹0</div><div class="sub" id="s-rev-sub">—</div></div>
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
          </div>
        </div>
      </section>
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
                <th>Used / Limit</th><th>Price</th><th>Dev</th><th>Status</th><th>Actions</th>
              </tr></thead>
              <tbody id="keysBody"><tr><td colspan="9" class="empty">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
      </section>
      <section class="view" id="view-logs">
        <div class="panel" style="margin-top:0">
          <div class="panel-head">
            <h2>REQUEST LOGS</h2>
            <div class="spacer"></div>
            <input class="search" id="logSearch" placeholder="Search key / tool / query..." oninput="loadLogs()">
            <button class="btn ghost" onclick="loadLogs()">REFRESH</button>
          </div>
          <div class="tbl-wrap">
            <table>
              <thead><tr><th>Time (UTC)</th><th>Key</th><th>Name</th><th>Tool</th><th>Query</th><th>IP</th><th>Status</th></tr></thead>
              <tbody id="logsBody"><tr><td colspan="7" class="empty">Loading…</td></tr></tbody>
            </table>
          </div>
        </div>
      </section>
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
            <div class="card"><h3>Keys Sold</h3><div class="big" id="r-count">0</div><div class="sub">total keys generated</div></div>
          </div>
          <div class="chart" id="revChart2" style="margin-top:16px"></div>
        </div>
      </section>
      <section class="view" id="view-docs">
        <div class="panel" style="margin-top:0">
          <div class="panel-head"><h2>API ENDPOINTS</h2></div>
          <p style="font-size:11.5px;color:var(--mut);margin:0 0 14px">
            Base URL: <span class="mono" id="baseUrl"></span> · Pass your key as <b>key</b> query parameter.
          </p>
          <div id="docsList"></div>
        </div>
      </section>
    </div>
  </div>
</div>
<div class="modal" id="keyModal">
  <div class="modal-box">
    <h2 id="modalTitle">GENERATE API KEY</h2>
    <p class="hint" id="modalHint">Custom key or auto-generated · choose tools · set expiry & limit</p>
    <label class="fl">API Key (custom or random)</label>
    <div style="display:flex;gap:8px">
      <input id="kKey" placeholder="Leave empty for auto key">
      <button class="btn ghost" style="flex:0 0 auto" onclick="randomKey()">🎲 RANDOM</button>
    </div>
    <label class="fl">Key Name (for history)</label>
    <input id="kName" placeholder="e.g. customer name / label">
    <label class="fl">Developer Name / "By" (Optional)</label>
    <input id="kByName" placeholder="e.g. SHAYAN_EXPLORER (Leave blank for default)">
    <div class="row2">
      <div><label class="fl">Request Limit (0 = unlimited)</label><input id="kLimit" type="number" min="0" value="0"></div>
      <div><label class="fl">Price (₹) — revenue</label><input id="kPrice" type="number" min="0" step="1" value="0"></div>
    </div>
    <label class="fl">Expiry Date &amp; Time (required)</label>
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
<script>
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const esc = s => String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let TOOLS = [], EDIT_ID = null;
function toast(msg, type='ok'){
  const d = document.createElement('div'); d.className = 'toast ' + type; d.textContent = msg;
  $('#toasts').appendChild(d);
  setTimeout(()=>{ d.style.opacity='0'; d.style.transform='translateX(30px)'; d.style.transition='.3s'; }, 2600);
  setTimeout(()=> d.remove(), 3000);
}
async function jget(url){
  const r = await fetch(url, {credentials:'same-origin'});
  if(r.status === 401){ location.href = '/admin/login'; return null; }
  try { return await r.json(); } catch(e){ return {ok:false, error:'Bad response'}; }
}
async function jsend(url, method, body){
  const r = await fetch(url, {method, credentials:'same-origin',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})});
  if(r.status === 401){ location.href = '/admin/login'; return null; }
  try { return await r.json(); } catch(e){ return {ok:false, error:'Bad response'}; }
}
const sidebar = $('#sidebar'), overlay = $('#overlay');
function openMenu(){ sidebar.classList.add('open'); overlay.classList.add('show'); }
function closeMenu(){ sidebar.classList.remove('open'); overlay.classList.remove('show'); }
$('#menuBtn').addEventListener('click', ()=>{ if(sidebar.classList.contains('open')) closeMenu(); else openMenu(); });
overlay.addEventListener('click', closeMenu);
$$('.nav-item').forEach(b => b.addEventListener('click', ()=> showView(b.dataset.view)));
function showView(name){
  $$('.view').forEach(v => v.classList.toggle('active', v.id === 'view-'+name));
  $$('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.view === name));
  closeMenu();
  if(name === 'overview') loadOverview();
  if(name === 'keys')     loadKeys();
  if(name === 'logs')     loadLogs();
  if(name === 'revenue')  loadRevenue();
  if(name === 'docs')     renderDocs();
}
async function loadOverview(){
  const d = await jget('/admin/api/stats?range=30d');
  if(!d || !d.ok) return;
  $('#s-keys').textContent   = d.total_keys;
  $('#s-keys-sub').textContent = d.suspended_keys + ' suspended · ' + d.expired_keys + ' expired';
  $('#s-active').textContent = d.active_keys;
  $('#s-active-sub').textContent = 'currently usable';
  $('#s-req').textContent    = d.total_requests;
  $('#s-req-sub').textContent = d.today_requests + ' today';
  $('#s-rev').textContent    = '₹' + d.revenue_total;
  $('#s-rev-sub').textContent = '₹' + d.revenue_range + ' in last 30 days';
  drawChart('#revChart', d.series);
}
function drawChart(sel, series){
  const el = $(sel); if(!el) return;
  if(!series || !series.length){ el.innerHTML = '<div class="empty">No data</div>'; return; }
  const max = Math.max(1, ...series.map(s => s.amount));
  el.innerHTML = series.map(s => {
    const h = Math.max(4, Math.round((s.amount / max) * 120));
    const label = s.date.slice(5);
    return '<div class="bar" style="height:'+h+'px" title="'+esc(s.date)+' · ₹'+s.amount+' · '+s.count+' keys"><span>'+esc(label)+'</span></div>';
  }).join('');
}
async function loadKeys(){
  const q = $('#keySearch').value.trim();
  const d = await jget('/admin/api/keys?q=' + encodeURIComponent(q));
  if(!d || !d.ok) return;
  const tb = $('#keysBody');
  if(!d.keys.length){ tb.innerHTML = '<tr><td colspan="9" class="empty">No keys yet. Click "+ GENERATE KEY".</td></tr>'; return; }
  tb.innerHTML = d.keys.map(k => {
    let badge = '<span class="badge b-active">ACTIVE</span>';
    if(k.expired) badge = '<span class="badge b-exp">EXPIRED</span>';
    else if(k.status !== 'active') badge = '<span class="badge b-susp">SUSPENDED</span>';
    const exp = k.expires_at ? new Date(k.expires_at).toLocaleString() : 'Never';
    const lim = (k.req_limit > 0) ? (k.req_count + ' / ' + k.req_limit) : (k.req_count + ' / ∞');
    const tools = k.tools === 'all' ? '<b style="color:#22e08a">ALL TOOLS</b>' : esc(k.tools.split(',').join(', '));
    const byName = k.by_name ? esc(k.by_name) : '<span style="color:#7b93b5">Default</span>';
    return '<tr>' +
      '<td><span class="mono">'+esc(k.key)+'</span></td>' +
      '<td>'+esc(k.name)+'</td>' +
      '<td style="font-size:10.6px;max-width:190px">'+tools+'</td>' +
      '<td style="font-size:10.6px">'+esc(exp)+'</td>' +
      '<td style="font-size:11px">'+esc(lim)+'</td>' +
      '<td>₹'+ (k.price||0) +'</td>' +
      '<td>'+byName+'</td>' +
      '<td>'+badge+'</td>' +
      '<td><div class="acts">' +
        '<button class="btn ghost sm" data-act="copy" data-key="'+esc(k.key)+'">COPY</button>' +
        '<button class="btn ghost sm" data-act="edit" data-id="'+k.id+'">EDIT</button>' +
        '<button class="btn amber sm" data-act="reset" data-id="'+k.id+'">RESTART</button>' +
        '<button class="btn green sm" data-act="toggle" data-id="'+k.id+'" data-status="'+k.status+'">'+(k.status==='active'?'SUSPEND':'UNSUSPEND')+'</button>' +
        '<button class="btn red sm" data-act="del" data-id="'+k.id+'">DELETE</button>' +
      '</div></td></tr>';
  }).join('');
}
$('#keysBody').addEventListener('click', async (e) => {
  const btn = e.target.closest('button[data-act]'); if(!btn) return;
  const act = btn.dataset.act;
  if(act === 'copy'){ try { await navigator.clipboard.writeText(btn.dataset.key); toast('Key copied','ok'); } catch(err){ toast('Copy failed','err'); } return; }
  if(act === 'edit'){ const d = await jget('/admin/api/keys'); const k = d.keys.find(x => String(x.id) === btn.dataset.id); if(k) openKeyModal(k); return; }
  if(act === 'reset'){ if(!confirm('Reset request counter for this key?')) return; const r = await jsend('/admin/api/keys/'+btn.dataset.id+'/reset','POST',{}); toast(r && r.ok ? 'Counter reset' : 'Failed', r && r.ok ? 'ok' : 'err'); loadKeys(); return; }
  if(act === 'toggle'){ const newStatus = btn.dataset.status === 'active' ? 'suspended' : 'active'; const r = await jsend('/admin/api/keys/'+btn.dataset.id,'PATCH',{status:newStatus}); toast(r && r.ok ? 'Status updated' : 'Failed', r && r.ok ? 'ok' : 'err'); loadKeys(); return; }
  if(act === 'del'){ if(!confirm('Delete this key permanently?')) return; const r = await jsend('/admin/api/keys/'+btn.dataset.id,'DELETE',{}); toast(r && r.ok ? 'Key deleted' : 'Failed', r && r.ok ? 'ok' : 'err'); loadKeys(); return; }
});
async function openKeyModal(k){
  EDIT_ID = k ? k.id : null;
  $('#modalTitle').textContent = k ? 'EDIT API KEY' : 'GENERATE API KEY';
  $('#saveKeyBtn').textContent = k ? 'SAVE CHANGES' : 'GENERATE KEY';
  $('#kKey').value    = k ? k.key : ''; $('#kKey').disabled = !!k;
  $('#kName').value   = k ? (k.name || '') : '';
  $('#kByName').value = k ? (k.by_name || '') : '';
  $('#kLimit').value  = k ? (k.req_limit || 0) : 0;
  $('#kPrice').value  = k ? (k.price || 0) : 0;
  $('#kNote').value   = k ? (k.note || '') : '';
  if(k && k.expires_ms) setExpiryAt(k.expires_ms); else setExpiry(86400000);
  await renderToolGrid(k ? (k.tools || 'all').split(',') : ['all']);
  $('#keyModal').classList.add('show'); document.body.style.overflow = 'hidden';
}
function closeModal(id){ $('#'+id).classList.remove('show'); document.body.style.overflow = ''; }
function setExpiryAt(ms){
  const d = new Date(ms), p = n => String(n).padStart(2,'0');
  $('#kExpiry').value = d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+'T'+p(d.getHours())+':'+p(d.getMinutes());
}
function setExpiry(offsetMs){ setExpiryAt(Date.now() + offsetMs); }
function randomKey(){
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; let out = 'FT-';
  for(let i=0;i<16;i++) out += chars[Math.floor(Math.random()*chars.length)];
  $('#kKey').value = out;
}
async function renderToolGrid(selected){
  if(!TOOLS.length){ const d = await jget('/admin/api/tools'); TOOLS = (d && d.tools) ? d.tools : []; }
  const sel = selected.map(s=>s.trim()).filter(Boolean); const all = sel.includes('all');
  $('#toolGrid').innerHTML = TOOLS.map(t =>
    '<label class="tool-item"><input type="checkbox" class="toolChk" value="'+esc(t.id)+'"'+
    ((all || sel.includes(t.id)) ? ' checked' : '')+'> '+esc(t.label)+'</label>'
  ).join('');
  updateSelAllBtn();
}
function toggleAllTools(){
  const boxes = $$('.toolChk'); const allChecked = boxes.every(b => b.checked);
  boxes.forEach(b => b.checked = !allChecked); updateSelAllBtn();
}
function updateSelAllBtn(){
  const boxes = $$('.toolChk'); const allChecked = boxes.length && boxes.every(b => b.checked);
  $('#selAllBtn').textContent = allChecked ? 'UNSELECT ALL' : 'SELECT ALL';
}
document.addEventListener('change', e => { if(e.target.classList && e.target.classList.contains('toolChk')) updateSelAllBtn(); });
async function saveKey(){
  const tools = $$('.toolChk').filter(b => b.checked).map(b => b.value);
  if(!tools.length){ toast('Select at least one tool','err'); return; }
  const expVal = $('#kExpiry').value; if(!expVal){ toast('Expiry date & time is required','err'); return; }
  const payload = { name: $('#kName').value.trim(), by_name: $('#kByName').value.trim(), tools: tools,
    expires_ms: new Date(expVal).getTime(), req_limit: parseInt($('#kLimit').value||'0',10)||0,
    price: parseFloat($('#kPrice').value||'0')||0, note: $('#kNote').value.trim() };
  let r;
  if(EDIT_ID){ r = await jsend('/admin/api/keys/' + EDIT_ID,'PATCH',payload); }
  else { payload.key = $('#kKey').value.trim(); r = await jsend('/admin/api/keys','POST',payload); }
  if(r && r.ok){ toast(EDIT_ID ? 'Key updated' : 'Key generated successfully','ok'); closeModal('keyModal'); EDIT_ID = null; showView('keys'); loadKeys(); loadOverview(); }
  else { toast((r && r.error) || 'Failed','err'); }
}
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
      '<td><span class="badge '+(l.status==='OK'?'b-active':'b-exp')+'">'+esc(l.status)+'</span></td>' +
    '</tr>').join('');
}
async function loadRevenue(){
  const rng = $('#revRange').value;
  const d = await jget('/admin/api/stats?range=' + rng);
  if(!d || !d.ok) return;
  $('#r-range').textContent = '₹' + d.revenue_range;
  $('#r-total').textContent = '₹' + d.revenue_total;
  $('#r-count').textContent = d.total_keys;
  drawChart('#revChart2', d.series);
}
async function renderDocs(){
  if(!TOOLS.length){ const d = await jget('/admin/api/tools'); TOOLS = (d && d.tools) ? d.tools : []; }
  $('#baseUrl').textContent = location.origin + '/api';
  $('#docsList').innerHTML = TOOLS.map(t => {
    const qs = ['key=YOUR_KEY'].concat(t.params.map(p => p + '=VALUE')).join('&');
    return '<div class="doc-item">' +
      '<div class="u">GET ' + esc(location.origin) + '/api/' + esc(t.id) + '?' + esc(qs) + '</div>' +
      '<div class="d">' + esc(t.label) + ' · params: ' + esc(t.params.join(', ')) + '</div></div>';
  }).join('');
}
(async function init(){
  const d = await jget('/admin/api/tools'); TOOLS = (d && d.tools) ? d.tools : [];
  loadOverview(); loadKeys();
})();
</script>
</body>
</html>"""

# ----------------------------- BOOT ------------------------------
init_db()

if __name__ == "__main__":
    print("=" * 62)
    print("  SHAYAN_EXPLORER · OSINT API CONTROL CENTER")
    print("  Developer: SHAYAN_EXPLORER")
    print("  URL   : http://127.0.0.1:5000")
    print(f"  DB    : {DB_PATH}  (persistent={os.environ.get('RENDER') == 'true' or bool(os.environ.get('DB_PATH'))})")
    print(f"  Admin : {ADMIN_USER} / {ADMIN_PASS}")
    print("=" * 62)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
