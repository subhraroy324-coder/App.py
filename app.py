import os
from datetime import datetime
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shayan_explorer_super_secret_key")

# In-memory database simulation (Use PostgreSQL/SQLite for permanent production storage)
# Default admin credentials requested: vernex / vernex@16vx
ADMIN_USER = "vernex"
ADMIN_PASS = "vernex@16vx"

# Storage
API_KEYS = {
    "explorer16": {
        "name": "Master Key",
        "expiry": "2099-12-31T23:59",
        "limit": 10000,
        "used": 0,
        "tools": ["all"],
        "status": "Active",
    }
}

REQUEST_LOGS = []

# Base upstream endpoints to proxy/forward requests
UPSTREAM_BASE = "https://ft-osint-api.duckdns.org/api"


@app.route("/")
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template(
        "index.html", keys=API_KEYS, logs=REQUEST_LOGS, developer="SHAYAN_EXPLORER"
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if (
            request.form.get("username") == ADMIN_USER
            and request.form.get("password") == ADMIN_PASS
        ):
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Invalid username or password!"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


# --- API Management Routes ---
@app.route("/admin/create_key", methods=["POST"])
def create_key():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.form
    key_name = data.get("key_name", "Custom Key")
    custom_key = data.get("custom_key_val", "").strip()
    expiry = data.get("expiry", "2026-12-31T23:59")
    limit = int(data.get("limit", 100))
    tools = data.getlist("tools")  # List of selected tools or ['all']

    if not custom_key:
        return jsonify({"error": "Key value cannot be empty"}), 400

    API_KEYS[custom_key] = {
        "name": key_name,
        "expiry": expiry,
        "limit": limit,
        "used": 0,
        "tools": tools if tools else ["all"],
        "status": "Active",
    }
    return redirect(url_for("index"))


@app.route("/admin/edit_key/<key_id>", methods=["POST"])
def edit_key(key_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    if key_id in API_KEYS:
        data = request.form
        API_KEYS[key_id]["name"] = data.get("name", API_KEYS[key_id]["name"])
        API_KEYS[key_id]["limit"] = int(
            data.get("limit", API_KEYS[key_id]["limit"])
        )
        API_KEYS[key_id]["expiry"] = data.get(
            "expiry", API_KEYS[key_id]["expiry"]
        )
        API_KEYS[key_id]["tools"] = data.getlist("tools") or ["all"]
    return redirect(url_for("index"))


@app.route("/admin/toggle_status/<key_id>")
def toggle_status(key_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if key_id in API_KEYS:
        current = API_KEYS[key_id]["status"]
        API_KEYS[key_id]["status"] = (
            "Suspended" if current == "Active" else "Active"
        )
    return redirect(url_for("index"))


@app.route("/admin/delete_key/<key_id>")
def delete_key(key_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if key_id in API_KEYS:
        del API_KEYS[key_id]
    return redirect(url_for("index"))


# --- Public Proxy OSINT API Endpoints (Branded to SHAYAN_EXPLORER) ---
def validate_and_process(tool_name):
    key = request.args.get("key")
    if not key or key not in API_KEYS:
        return jsonify({"error": "Invalid or missing API key", "developer": "SHAYAN_EXPLORER"}), 403

    key_data = API_KEYS[key]

    # Check status
    if key_data["status"] != "Active":
        return jsonify({"error": "API Key is suspended", "developer": "SHAYAN_EXPLORER"}), 403

    # Check Expiry
    try:
        expiry_dt = datetime.strptime(key_data["expiry"], "%Y-%m-%dT%H:%M")
        if datetime.now() > expiry_dt:
            return jsonify({"error": "API Key has expired", "developer": "SHAYAN_EXPLORER"}), 403
    except Exception:
        pass

    # Check Limit
    if key_data["used"] >= key_data["limit"]:
        return jsonify({"error": "API Key rate limit/quota exhausted", "developer": "SHAYAN_EXPLORER"}), 429

    # Check Tool Permission
    if "all" not in key_data["tools"] and tool_name not in key_data["tools"]:
        return jsonify({"error": f"Unauthorized access to tool: {tool_name}", "developer": "SHAYAN_EXPLORER"}), 403

    # Increment Usage
    key_data["used"] += 1

    # Log Request
    query_params = dict(request.args)
    REQUEST_LOGS.insert(
        0,
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "key": key,
            "tool": tool_name,
            "query": str(query_params),
            "ip": request.remote_addr,
        },
    )
    if len(REQUEST_LOGS) > 100:
        REQUEST_LOGS.pop()

    # Forward to upstream API
    query_params["key"] = "explorer16"  # Master upstream key fallback
    try:
        resp = requests.get(f"{UPSTREAM_BASE}/{tool_name}", params=query_params, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": "Upstream service timeout or error", "details": str(e), "developer": "SHAYAN_EXPLORER"}), 502


# Map all requested endpoints
@app.route("/api/adv")
def api_adv():
    return validate_and_process("adv")


@app.route("/api/paytm")
def api_paytm():
    return validate_and_process("paytm")


@app.route("/api/imei")
def api_imei():
    return validate_and_process("imei")


@app.route("/api/calltracer")
def api_calltracer():
    return validate_and_process("calltracer")


@app.route("/api/upi")
def api_upi():
    return validate_and_process("upi")


@app.route("/api/ifsc")
def api_ifsc():
    return validate_and_process("ifsc")


@app.route("/api/number")
def api_number():
    return validate_and_process("number")


@app.route("/api/pincode")
def api_pincode():
    return validate_and_process("pincode")


@app.route("/api/ip")
def api_ip():
    return validate_and_process("ip")


@app.route("/api/challan")
def api_challan():
    return validate_and_process("challan")


@app.route("/api/ff")
def api_ff():
    return validate_and_process("ff")


@app.route("/api/bgmi")
def api_bgmi():
    return validate_and_process("bgmi")


@app.route("/api/snap")
def api_snap():
    return validate_and_process("snap")


@app.route("/api/email")
def api_email():
    return validate_and_process("email")


@app.route("/api/vehicle")
def api_vehicle():
    return validate_and_process("vehicle")


@app.route("/api/git")
def api_git():
    return validate_and_process("git")


@app.route("/api/insta")
def api_insta():
    return validate_and_process("insta")


@app.route("/api/tg")
def api_tg():
    return validate_and_process("tg")


@app.route("/api/tgidinfo")
def api_tgidinfo():
    return validate_and_process("tgidinfo")


@app.route("/api/numleak")
def api_numleak():
    return validate_and_process("numleak")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
