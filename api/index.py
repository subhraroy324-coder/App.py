from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
import requests
import sqlite3
import datetime
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Admin Credentials
ADMIN_USER = "vernex"
ADMIN_PASS = "vernex@16vx"

# Upstream APIs Mapping
UPSTREAM_APIS = {
    "adv": "https://ft-osint-api.duckdns.org/api/adv?key={key}&num={num}",
    "paytm": "https://ft-osint-api.duckdns.org/api/paytm?key={key}&num={num}",
    "imei": "https://ft-osint-api.duckdns.org/api/imei?key={key}&imei={imei}",
    "calltracer": "https://ft-osint-api.duckdns.org/api/calltracer?key={key}&num={num}",
    "upi": "https://ft-osint-api.duckdns.org/api/upi?key={key}&upi={upi}",
    "ifsc": "https://ft-osint-api.duckdns.org/api/ifsc?key={key}&ifsc={ifsc}",
    "number": "https://ft-osint-api.duckdns.org/api/number?key={key}&num={num}",
    "pincode": "https://ft-osint-api.duckdns.org/api/pincode?key={key}&pin={pin}",
    "ip": "https://ft-osint-api.duckdns.org/api/ip?key={key}&ip={ip}",
    "challan": "https://ft-osint-api.duckdns.org/api/challan?key={key}&vehicle={vehicle}",
    "ff": "https://ft-osint-api.duckdns.org/api/ff?key={key}&uid={uid}",
    "bgmi": "https://ft-osint-api.duckdns.org/api/bgmi?key={key}&uid={uid}",
    "snap": "https://ft-osint-api.duckdns.org/api/snap?key={key}&username={username}",
    "email": "https://ft-osint-api.duckdns.org/api/email?key={key}&email={email}",
    "vehicle": "https://ft-osint-api.duckdns.org/api/vehicle?key={key}&vehicle={vehicle}",
    "git": "https://ft-osint-api.duckdns.org/api/git?key={key}&username={username}",
    "insta": "https://ft-osint-api.duckdns.org/api/insta?key={key}&username={username}",
    "tg": "https://ft-osint-api.duckdns.org/api/tg?key={key}&info={info}",
    "tgidinfo": "https://ft-osint-api.duckdns.org/api/tgidinfo?key={key}&id={id}",
    "numleak": "https://ft-osint-api.duckdns.org/api/numleak?key={key}&num={num}"
}

DB_NAME = "database.db"

# ==========================================
# HTML TEMPLATES (MIXED DIRECTLY IN PYTHON)
# ==========================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login | SHAYAN_EXPLORER OSINT Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>body { background: #0b0f19; color: #fff; }</style>
</head>
<body class="flex items-center justify-center h-screen">
    <div class="bg-gray-900 border border-gray-800 p-8 rounded-2xl shadow-2xl w-96">
        <h2 class="text-2xl font-bold mb-6 text-center text-indigo-400">SHAYAN_EXPLORER Admin</h2>
        {% if error %}<p class="bg-red-500 bg-opacity-20 text-red-400 p-2 rounded mb-4 text-xs text-center">{{ error }}</p>{% endif %}
        <form method="POST">
            <div class="mb-4">
                <label class="block text-xs uppercase text-gray-400 mb-1">Username</label>
                <input type="text" name="username" value="vernex" required class="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-indigo-500">
            </div>
            <div class="mb-6">
                <label class="block text-xs uppercase text-gray-400 mb-1">Password</label>
                <input type="password" name="password" value="vernex@16vx" required class="w-full bg-gray-800 border border-gray-700 rounded p-2 text-sm text-white focus:outline-none focus:border-indigo-500">
            </div>
            <button type="submit" class="w-full bg-indigo-600 hover:bg-indigo-700 p-2 rounded font-bold text-sm transition">Secure Login</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SHAYAN_EXPLORER | OSINT API Gateway Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background: #0b0f19; color: #f3f4f6; font-family: 'Inter', sans-serif; }
        .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); }
        .card-3d { transition: transform 0.3s ease, box-shadow 0.3s ease; transform-style: preserve-3d; }
        .card-3d:hover { transform: translateY(-5px) rotateX(2deg) rotateY(2deg); box-shadow: 0 20px 30px rgba(0, 0, 0, 0.5); }
    </style>
</head>
<body class="min-h-screen p-6">
    <div class="max-w-7xl mx-auto">
        <!-- Header -->
        <div class="glass p-6 rounded-2xl mb-8 flex flex-col md:flex-row justify-between items-center shadow-2xl">
            <div>
                <h1 class="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
                    <i class="fa-solid fa-shield-halved"></i> SHAYAN_EXPLORER API Matrix
                </h1>
                <p class="text-gray-400 text-sm mt-1">Enterprise 3D OSINT Infrastructure & Key Management Hub</p>
            </div>
            <div class="mt-4 md:mt-0 flex items-center space-x-4">
                <span class="px-4 py-2 bg-green-500 bg-opacity-20 text-green-400 border border-green-500 rounded-full text-xs font-semibold animate-pulse">
                    <i class="fa-solid fa-circle text-[8px]"></i> System Live
                </span>
                <a href="/logout" class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-medium transition shadow-lg">
                    <i class="fa-solid fa-right-from-bracket"></i> Logout
                </a>
            </div>
        </div>

        <!-- Create Key Section -->
        <div class="glass p-6 rounded-2xl mb-8 card-3d shadow-xl">
            <h2 class="text-xl font-bold mb-4 text-indigo-300"><i class="fa-solid fa-key"></i> Generate / Configure New API Key</h2>
            <form action="/api/create_key" method="POST" class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                    <label class="block text-xs uppercase tracking-wider text-gray-400 mb-1">Key Name / Client</label>
                    <input type="text" name="key_name" required placeholder="e.g. Client Alpha" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500">
                </div>
                <div>
                    <label class="block text-xs uppercase tracking-wider text-gray-400 mb-1">API Key Token</label>
                    <input type="text" name="api_key" value="explorer-{{ range(1000, 9999) | random }}" required class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500">
                </div>
                <div>
                    <label class="block text-xs uppercase tracking-wider text-gray-400 mb-1">Expiry Type</label>
                    <select name="expiry_type" id="expiry_type" onchange="toggleDateInput(this.value)" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500">
                        <option value="lifetime">Lifetime</option>
                        <option value="custom">Custom Date & Time</option>
                    </select>
                </div>
                <div id="date_box" style="display:none;">
                    <label class="block text-xs uppercase tracking-wider text-gray-400 mb-1">Expiry Date</label>
                    <input type="datetime-local" name="expiry_date" class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                </div>
                <div>
                    <label class="block text-xs uppercase tracking-wider text-gray-400 mb-1">Request Limit (-1 = Unlimited)</label>
                    <input type="number" name="limit" value="5000" required class="w-full bg-gray-900 border border-gray-700 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500">
                </div>
                <div class="md:col-span-4">
                    <label class="block text-xs uppercase tracking-wider text-gray-400 mb-2">Select Accessible Tools (Leave ALL selected or check specific)</label>
                    <div class="flex items-center space-x-2 mb-2">
                        <input type="checkbox" id="check_all" checked onclick="toggleAllTools(this)">
                        <label for="check_all" class="text-sm font-semibold text-indigo-400">Select All Tools</label>
                    </div>
                    <div class="grid grid-cols-2 md:grid-cols-5 gap-2 max-h-36 overflow-y-auto p-2 bg-gray-900 rounded-lg border border-gray-800">
                        {% for tool in tools %}
                        <label class="flex items-center space-x-2 text-xs text-gray-300">
                            <input type="checkbox" name="tools" value="{{ tool }}" checked class="tool-checkbox">
                            <span>{{ tool }}</span>
                        </label>
                        {% endfor %}
                    </div>
                </div>
                <div class="md:col-span-4">
                    <button type="submit" class="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 font-bold rounded-xl shadow-lg transition">
                        <i class="fa-solid fa-plus-circle"></i> Create & Provision Key
                    </button>
                </div>
            </form>
        </div>

        <!-- Keys Management Table -->
        <div class="glass p-6 rounded-2xl mb-8 shadow-xl overflow-x-auto">
            <h2 class="text-xl font-bold mb-4 text-indigo-300"><i class="fa-solid fa-list-check"></i> Active API Keys & Endpoints</h2>
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="border-b border-gray-800 text-gray-400 text-xs uppercase">
                        <th class="p-3">Name</th>
                        <th class="p-3">API Key</th>
                        <th class="p-3">Expiry</th>
                        <th class="p-3">Usage</th>
                        <th class="p-3">Status</th>
                        <th class="p-3">Endpoint Copy</th>
                        <th class="p-3">Actions</th>
                    </tr>
                </thead>
                <tbody class="text-sm divide-y divide-gray-800">
                    {% for key in keys %}
                    <tr class="hover:bg-gray-800 hover:bg-opacity-45 transition">
                        <td class="p-3 font-semibold text-white">{{ key[1] }}</td>
                        <td class="p-3 font-mono text-indigo-400">{{ key[2] }}</td>
                        <td class="p-3 text-gray-300">{{ key[3] }}</td>
                        <td class="p-3 text-gray-300">{{ key[5] }} / {% if key[4] == -1 %}∞{% else %}{{ key[4] }}{% endif %}</td>
                        <td class="p-3">
                            <span class="px-2 py-1 rounded text-xs {% if key[7] == 'Active' %}bg-green-500 bg-opacity-20 text-green-400{% else %}bg-red-500 bg-opacity-20 text-red-400{% endif %}">
                                {{ key[7] }}
                            </span>
                        </td>
                        <td class="p-3">
                            <button onclick="copyEndpoint('{{ key[2] }}')" class="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 rounded text-xs font-semibold text-white shadow">
                                <i class="fa-solid fa-copy"></i> Copy Base Endpoint
                            </button>
                        </td>
                        <td class="p-3 flex space-x-2">
                            <form action="/api/toggle_status/{{ key[0] }}" method="POST">
                                <button type="submit" class="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 rounded text-xs text-white">
                                    <i class="fa-solid fa-power-off"></i>
                                </button>
                            </form>
                            <form action="/api/delete_key/{{ key[0] }}" method="POST">
                                <button type="submit" class="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-xs text-white">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Request Logs Section -->
        <div class="glass p-6 rounded-2xl shadow-xl overflow-x-auto">
            <h2 class="text-xl font-bold mb-4 text-indigo-300"><i class="fa-solid fa-clock-rotate-left"></i> Live Request History & Logs</h2>
            <table class="w-full text-left border-collapse font-mono text-xs">
                <thead>
                    <tr class="border-b border-gray-800 text-gray-400 uppercase">
                        <th class="p-3">Timestamp</th>
                        <th class="p-3">API Key</th>
                        <th class="p-3">Tool Endpoint</th>
                        <th class="p-3">Query Parameters</th>
                        <th class="p-3">Status</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-800 text-gray-300">
                    {% for log in logs %}
                    <tr>
                        <td class="p-3">{{ log[3] }}</td>
                        <td class="p-3 text-indigo-400">{{ log[0] }}</td>
                        <td class="p-3 text-green-400">/api/{{ log[1] }}</td>
                        <td class="p-3 truncate max-w-xs">{{ log[2] }}</td>
                        <td class="p-3">
                            <span class="px-2 py-0.5 rounded {% if log[4] == 200 %}bg-green-500 bg-opacity-20 text-green-400{% else %}bg-red-500 bg-opacity-20 text-red-400{% endif %}">
                                {{ log[4] }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function toggleDateInput(val) {
            document.getElementById('date_box').style.display = (val === 'custom') ? 'block' : 'none';
        }
        function toggleAllTools(source) {
            let checkboxes = document.querySelectorAll('.tool-checkbox');
            checkboxes.forEach(cb => cb.checked = source.checked);
        }
        function copyEndpoint(apiKey) {
            const domain = window.location.origin;
            const sampleUrl = `${domain}/api/number?key=${apiKey}&num=9876543210`;
            navigator.clipboard.writeText(sampleUrl);
            alert("Endpoint Copied to Clipboard! Replace query parameters as required:\\n\\n" + sampleUrl);
        }
    </script>
</body>
</html>
"""

# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS keys (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key_name TEXT,
                        api_key TEXT UNIQUE,
                        expiry_date TEXT,
                        request_limit INTEGER,
                        requests_used INTEGER,
                        allowed_tools TEXT,
                        status TEXT
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        api_key TEXT,
                        endpoint TEXT,
                        query_params TEXT,
                        timestamp TEXT,
                        status_code INTEGER
                      )''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def validate_key(api_key, tool_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date, request_limit, requests_used, allowed_tools, status FROM keys WHERE api_key = ?", (api_key,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "Invalid API Key. Developed by SHAYAN_EXPLORER."
    
    expiry_date, limit, used, tools, status = row
    if status != "Active":
        conn.close()
        return False, "API Key is suspended or inactive."
    
    if limit != -1 and used >= limit:
        conn.close()
        return False, "API Key request limit exceeded."
        
    if expiry_date != "Lifetime":
        try:
            exp_dt = datetime.datetime.strptime(expiry_date.replace("T", " "), "%Y-%m-%d %H:%M")
            if datetime.datetime.now() > exp_dt:
                conn.close()
                return False, "API Key has expired."
        except Exception:
            pass
            
    allowed_list = tools.split(",")
    if "ALL" not in allowed_list and tool_name not in allowed_list:
        conn.close()
        return False, f"Unauthorized access to tool: {tool_name}"

    cursor.execute("UPDATE keys SET requests_used = requests_used + 1 WHERE api_key = ?", (api_key,))
    conn.commit()
    conn.close()
    return True, "OK"

def log_request(api_key, endpoint, params, status_code):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (api_key, endpoint, query_params, timestamp, status_code) VALUES (?, ?, ?, ?, ?)",
                   (api_key, endpoint, str(params), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status_code))
    conn.commit()
    conn.close()

# ==========================================
# ROUTING & ENDPOINTS
# ==========================================

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, key_name, api_key, expiry_date, request_limit, requests_used, allowed_tools, status FROM keys")
    keys = cursor.fetchall()
    
    cursor.execute("SELECT api_key, endpoint, query_params, timestamp, status_code FROM logs ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()
    conn.close()
    
    return render_template_string(DASHBOARD_HTML, keys=keys, logs=logs, tools=list(UPSTREAM_APIS.keys()))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = 'Invalid Credentials. Use provided account.'
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/api/create_key', methods=['POST'])
def create_key():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.form
    key_name = data.get('key_name')
    custom_key = data.get('api_key')
    expiry_type = data.get('expiry_type')
    expiry_date = data.get('expiry_date') if expiry_type == 'custom' else 'Lifetime'
    limit = int(data.get('limit', 1000))
    tools = ",".join(data.getlist('tools')) if 'tools' in data else 'ALL'
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO keys (key_name, api_key, expiry_date, request_limit, requests_used, allowed_tools, status) VALUES (?, ?, ?, ?, 0, ?, 'Active')",
                       (key_name, custom_key, expiry_date, limit, tools))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 400
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/delete_key/<int:key_id>', methods=['POST'])
def delete_key(key_id):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 403
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM keys WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/toggle_status/<int:key_id>', methods=['POST'])
def toggle_status(key_id):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 403
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM keys WHERE id = ?", (key_id,))
    status = cursor.fetchone()[0]
    new_status = "Suspended" if status == "Active" else "Active"
    cursor.execute("UPDATE keys SET status = ? WHERE id = ?", (new_status, key_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/api/<tool_name>', methods=['GET'])
def api_gateway(tool_name):
    if tool_name not in UPSTREAM_APIS:
        return jsonify({"error": "Invalid API Endpoint", "developer": "SHAYAN_EXPLORER"}), 404
        
    api_key = request.args.get('key')
    if not api_key:
        return jsonify({"error": "API Key required. Pass ?key=YOUR_KEY", "developer": "SHAYAN_EXPLORER"}), 401
        
    valid, msg = validate_key(api_key, tool_name)
    if not valid:
        log_request(api_key, tool_name, dict(request.args), 403)
        return jsonify({"error": msg, "developer": "SHAYAN_EXPLORER"}), 403
        
    target_url_template = UPSTREAM_APIS[tool_name]
    req_params = request.args.to_dict()
    
    try:
        formatted_url = target_url_template.format(**req_params)
    except Exception:
        formatted_url = target_url_template
        for k, v in req_params.items():
            formatted_url = formatted_url.replace(f"{{{k}}}", v)
            
    try:
        resp = requests.get(formatted_url, timeout=15)
        log_request(api_key, tool_name, req_params, resp.status_code)
        try:
            return jsonify(resp.json())
        except Exception:
            return resp.text, resp.status_code
    except Exception as e:
        log_request(api_key, tool_name, req_params, 500)
        return jsonify({"error": "Upstream timeout or connection error", "details": str(e), "developer": "SHAYAN_EXPLORER"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
