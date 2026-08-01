import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shayan_explorer_secure_key_123")

DB_NAME = "database.db"
MASTER_KEY = "explorer16"

# Integrated OSINT Tool Endpoints
API_ENDPOINTS = {
    "adv": "https://ft-osint-api.duckdns.org/api/adv?key={key}&num={num}",
    "paytm": "https://ft-osint-api.duckdns.org/api/paytm?key={key}&num={num}",
    "imei": "https://ft-osint-api.duckdns.org/api/imei?key={key}&imei={imei}",
    "calltracer": "https://ft-osint-api.duckdns.org/api/calltracer?key={key}&num={num}",
    "upi": "https://ft-osint-api.duckdns.org/api/upi?key={key}&upi={upi}",
    "ifsc": "https://ft-osint-api.duckdns.org/api/ifsc?key={key}&ifsc={ifsc}",
    "pincode": "https://ft-osint-api.duckdns.org/api/pincode?key={key}&pin={pin}",
    "ip": "https://ft-osint-api.duckdns.org/api/ip?key={key}&ip={ip}",
    "challan": (
        "https://ft-osint-api.duckdns.org/api/challan?key={key}&vehicle={vehicle}"
    ),
    "ff": "https://ft-osint-api.duckdns.org/api/ff?key={key}&uid={uid}",
    "bgmi": "https://ft-osint-api.duckdns.org/api/bgmi?key={key}&uid={uid}",
    "snap": "https://ft-osint-api.duckdns.org/api/snap?key={key}&username={username}",
    "number": "https://ft-osint-api.duckdns.org/api/number?key={key}&num={num}",
    "email": "https://ft-osint-api.duckdns.org/api/email?key={key}&email={email}",
    "vehicle": (
        "https://ft-osint-api.duckdns.org/api/vehicle?key={key}&vehicle={vehicle}"
    ),
    "git": "https://ft-osint-api.duckdns.org/api/git?key={key}&username={username}",
    "insta": (
        "https://ft-osint-api.duckdns.org/api/insta?key={key}&username={username}"
    ),
    "tg": "https://ft-osint-api.duckdns.org/api/tg?key={key}&info={info}",
    "tgidinfo": "https://ft-osint-api.duckdns.org/api/tgidinfo?key={key}&id={id}",
    "numleak": "https://ft-osint-api.duckdns.org/api/numleak?key={key}&num={num}",
}


def init_db():
  with sqlite3.connect(DB_NAME) as conn:
    cursor = conn.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT UNIQUE NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                expiry_date TEXT NOT NULL,
                daily_limit INTEGER NOT NULL,
                requests_used INTEGER DEFAULT 0,
                allowed_tools TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT,
                tool_name TEXT,
                query_params TEXT,
                status_code INTEGER,
                timestamp TEXT
            )
        """)
    conn.commit()


init_db()


def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if not session.get("logged_in"):
      return redirect(url_for("login"))
    return f(*args, **kwargs)

  return decorated_function


@app.route("/login", methods=["GET", "POST"])
def login():
  error = None
  if request.method == "POST":
    username = request.form.get("username")
    password = request.form.get("password")
    if username == "vernex" and password == "vernex@16vx":
      session["logged_in"] = True
      return redirect(url_for("dashboard"))
    else:
      error = "Invalid credentials. Use vernex / vernex@16vx"
  return render_template("login.html", error=error)


@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
  with sqlite3.connect(DB_NAME) as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    keys = cursor.execute("SELECT * FROM api_keys").fetchall()
    logs = cursor.execute(
        "SELECT * FROM request_logs ORDER BY id DESC LIMIT 50"
    ).fetchall()
  return render_template(
      "index.html", keys=keys, logs=logs, tools=list(API_ENDPOINTS.keys())
  )


@app.route("/create_key", methods=["POST"])
@login_required
def create_key():
  key_name = request.form.get("key_name")
  custom_key = request.form.get("custom_key")
  expiry_date = request.form.get("expiry_date")
  daily_limit = int(request.form.get("daily_limit", 100))
  selected_tools = request.form.getlist("tools")
  tools_str = ",".join(selected_tools)
  created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  try:
    with sqlite3.connect(DB_NAME) as conn:
      cursor = conn.cursor()
      cursor.execute(
          """INSERT INTO api_keys (key_name, api_key, expiry_date, daily_limit, allowed_tools, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)""",
          (
              key_name,
              custom_key,
              expiry_date,
              daily_limit,
              tools_str,
              created_at,
          ),
      )
      conn.commit()
  except Exception as e:
    print(f"Error creating key: {e}")

  return redirect(url_for("dashboard"))


@app.route("/delete_key/<int:key_id>", methods=["POST"])
@login_required
def delete_key(key_id):
  with sqlite3.connect(DB_NAME) as conn:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
    conn.commit()
  return redirect(url_for("dashboard"))


@app.route("/api/<tool_name>", methods=["GET"])
def proxy_api(tool_name):
  if tool_name not in API_ENDPOINTS:
    return (
        jsonify({
            "error": "Invalid Tool Endpoint",
            "developer": "SHAYAN_EXPLORER",
        }),
        404,
    )

  client_key = request.args.get("key")
  if not client_key:
    return (
        jsonify({
            "error": "API Key missing. Pass ?key=YOUR_KEY",
            "developer": "SHAYAN_EXPLORER",
        }),
        401,
    )

  with sqlite3.connect(DB_NAME) as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    key_record = cursor.execute(
        "SELECT * FROM api_keys WHERE api_key = ?", (client_key,)
    ).fetchone()

  if not key_record:
    return (
        jsonify({
            "error": "Invalid API Key",
            "developer": "SHAYAN_EXPLORER",
        }),
        403,
    )

  # Check Expiry
  expiry_date = datetime.strptime(key_record["expiry_date"], "%Y-%m-%d")
  if datetime.now() > expiry_date:
    return (
        jsonify({
            "error": "API Key has expired",
            "developer": "SHAYAN_EXPLORER",
        }),
        403,
    )

  # Check Rate Limits
  if key_record["requests_used"] >= key_record["daily_limit"]:
    return (
        jsonify({
            "error": "Daily request limit exhausted",
            "developer": "SHAYAN_EXPLORER",
        }),
        429,
    )

  # Check Tool Permissions
  allowed_tools = key_record["allowed_tools"].split(",")
  if tool_name not in allowed_tools and "all" not in allowed_tools:
    return (
        jsonify({
            "error": "Unauthorized access to this specific tool endpoint",
            "developer": "SHAYAN_EXPLORER",
        }),
        403,
    )

  # Proxy Upstream Request with Master Key
  target_url_template = API_ENDPOINTS[tool_name]
  query_params_dict = request.args.to_dict()
  query_params_dict["key"] = MASTER_KEY
  url_to_fetch = target_url_template.split("?")[0]

  try:
    response = requests.get(
        url_to_fetch, params=query_params_dict, timeout=15
    )
    upstream_data = response.json()
  except Exception:
    upstream_data = {
        "status": False,
        "error": "Upstream API timeout or server error",
    }
    response.status_code = 500

  # Log Request & Update Count
  param_summary = str(request.args.to_dict())
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  with sqlite3.connect(DB_NAME) as conn:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE api_keys SET requests_used = requests_used + 1 WHERE id = ?",
        (key_record["id"],),
    )
    cursor.execute(
        """INSERT INTO request_logs (key_name, tool_name, query_params, status_code, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
        (
            key_record["key_name"],
            tool_name,
            param_summary,
            response.status_code,
            timestamp,
        ),
    )
    conn.commit()

  if isinstance(upstream_data, dict):
    upstream_data["developer"] = "SHAYAN_EXPLORER"

  return jsonify(upstream_data), response.status_code


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
