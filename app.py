import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

# Configuration
MASTER_KEY = os.getenv('MASTER_KEY', 'explorer16')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///instance/osint.db')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database helper
def get_db():
    db_path = DATABASE_URL.replace('sqlite:///', '')
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_name TEXT NOT NULL,
                key_value TEXT UNIQUE NOT NULL,
                expiry_date DATETIME,
                request_limit INTEGER,
                request_count INTEGER DEFAULT 0,
                allowed_apis TEXT,  -- JSON array of tool names
                status TEXT DEFAULT 'active', -- active, suspended, expired
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id INTEGER,
                tool TEXT NOT NULL,
                parameters TEXT,  -- JSON
                response_status INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (key_id) REFERENCES api_keys (id)
            )
        ''')
        # Create default user if not exists
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('vernex',)).fetchone()
        if not user:
            hashed = generate_password_hash('vernex@16vx')
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', ('vernex', hashed))
        conn.commit()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if user:
            return User(user['id'], user['username'])
    return None

# Helper functions
def generate_key():
    return secrets.token_hex(16)

def get_allowed_apis(key_id):
    with get_db() as conn:
        row = conn.execute('SELECT allowed_apis FROM api_keys WHERE id = ?', (key_id,)).fetchone()
        if row and row['allowed_apis']:
            return json.loads(row['allowed_apis'])
        return []

def is_tool_allowed(key_id, tool):
    allowed = get_allowed_apis(key_id)
    if not allowed:  # If empty, allow all
        return True
    return tool in allowed

def log_request(key_id, tool, parameters, status):
    with get_db() as conn:
        conn.execute(
            'INSERT INTO logs (key_id, tool, parameters, response_status) VALUES (?, ?, ?, ?)',
            (key_id, tool, json.dumps(parameters), status)
        )
        conn.commit()

def increment_request_count(key_id):
    with get_db() as conn:
        conn.execute('UPDATE api_keys SET request_count = request_count + 1 WHERE id = ?', (key_id,))
        conn.commit()

def check_key_validity(key_value, tool):
    with get_db() as conn:
        key = conn.execute(
            'SELECT id, expiry_date, request_limit, request_count, status FROM api_keys WHERE key_value = ?',
            (key_value,)
        ).fetchone()
        if not key:
            return None, 'Invalid API key'
        if key['status'] != 'active':
            return None, 'Key is not active'
        if key['expiry_date']:
            expiry = datetime.fromisoformat(key['expiry_date'])
            if datetime.now() > expiry:
                return None, 'Key has expired'
        if key['request_limit'] is not None and key['request_count'] >= key['request_limit']:
            return None, 'Request limit exceeded'
        if not is_tool_allowed(key['id'], tool):
            return None, f'Tool "{tool}" not allowed for this key'
        return key['id'], None

# Mapping from tool to backend URL and required parameters
TOOL_CONFIG = {
    'adv': {'url': 'https://ft-osint-api.duckdns.org/api/adv', 'params': ['num']},
    'paytm': {'url': 'https://ft-osint-api.duckdns.org/api/paytm', 'params': ['num']},
    'imei': {'url': 'https://ft-osint-api.duckdns.org/api/imei', 'params': ['imei']},
    'calltracer': {'url': 'https://ft-osint-api.duckdns.org/api/calltracer', 'params': ['num']},
    'upi': {'url': 'https://ft-osint-api.duckdns.org/api/upi', 'params': ['upi']},
    'ifsc': {'url': 'https://ft-osint-api.duckdns.org/api/ifsc', 'params': ['ifsc']},
    'number': {'url': 'https://ft-osint-api.duckdns.org/api/number', 'params': ['num']},
    'pincode': {'url': 'https://ft-osint-api.duckdns.org/api/pincode', 'params': ['pin']},
    'ip': {'url': 'https://ft-osint-api.duckdns.org/api/ip', 'params': ['ip']},
    'challan': {'url': 'https://ft-osint-api.duckdns.org/api/challan', 'params': ['vehicle']},
    'ff': {'url': 'https://ft-osint-api.duckdns.org/api/ff', 'params': ['uid']},
    'bgmi': {'url': 'https://ft-osint-api.duckdns.org/api/bgmi', 'params': ['uid']},
    'snap': {'url': 'https://ft-osint-api.duckdns.org/api/snap', 'params': ['username']},
    'email': {'url': 'https://ft-osint-api.duckdns.org/api/email', 'params': ['email']},
    'vehicle': {'url': 'https://ft-osint-api.duckdns.org/api/vehicle', 'params': ['vehicle']},
    'git': {'url': 'https://ft-osint-api.duckdns.org/api/git', 'params': ['username']},
    'insta': {'url': 'https://ft-osint-api.duckdns.org/api/insta', 'params': ['username']},
    'tg': {'url': 'https://ft-osint-api.duckdns.org/api/tg', 'params': ['info']},
    'tgidinfo': {'url': 'https://ft-osint-api.duckdns.org/api/tgidinfo', 'params': ['id']},
    'numleak': {'url': 'https://ft-osint-api.duckdns.org/api/numleak', 'params': ['num']},
}

ALL_TOOLS = sorted(TOOL_CONFIG.keys())

# ------------------- Routes -------------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        with get_db() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and check_password_hash(user['password_hash'], password):
                user_obj = User(user['id'], user['username'])
                login_user(user_obj)
                return redirect(url_for('dashboard'))
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    with get_db() as conn:
        total_keys = conn.execute('SELECT COUNT(*) FROM api_keys').fetchone()[0]
        active_keys = conn.execute('SELECT COUNT(*) FROM api_keys WHERE status = "active"').fetchone()[0]
        total_requests = conn.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
        # Recent logs
        recent_logs = conn.execute(
            'SELECT logs.*, api_keys.key_name FROM logs LEFT JOIN api_keys ON logs.key_id = api_keys.id ORDER BY timestamp DESC LIMIT 10'
        ).fetchall()
    return render_template('dashboard.html',
                           total_keys=total_keys,
                           active_keys=active_keys,
                           total_requests=total_requests,
                           recent_logs=recent_logs)

@app.route('/generate', methods=['GET', 'POST'])
@login_required
def generate_key():
    if request.method == 'POST':
        key_name = request.form.get('key_name', '').strip()
        expiry_date = request.form.get('expiry_date')
        expiry_time = request.form.get('expiry_time')
        request_limit = request.form.get('request_limit')
        allowed_apis = request.form.getlist('allowed_apis')

        if not key_name:
            flash('Key name is required', 'danger')
            return render_template('generate.html', tools=ALL_TOOLS, selected=[])

        # Build expiry datetime
        expiry_datetime = None
        if expiry_date and expiry_time:
            try:
                expiry_datetime = datetime.strptime(f"{expiry_date} {expiry_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                flash('Invalid expiry date/time format', 'danger')
                return render_template('generate.html', tools=ALL_TOOLS, selected=allowed_apis)

        # If no expiry, set to None (lifetime)
        # Limit: if empty, set to None (unlimited)
        try:
            limit = int(request_limit) if request_limit else None
        except ValueError:
            flash('Request limit must be a number', 'danger')
            return render_template('generate.html', tools=ALL_TOOLS, selected=allowed_apis)

        key_value = generate_key()
        allowed_json = json.dumps(allowed_apis) if allowed_apis else None

        with get_db() as conn:
            conn.execute(
                '''INSERT INTO api_keys 
                   (key_name, key_value, expiry_date, request_limit, allowed_apis, status)
                   VALUES (?, ?, ?, ?, ?, 'active')''',
                (key_name, key_value, expiry_datetime.isoformat() if expiry_datetime else None,
                 limit, allowed_json)
            )
            conn.commit()
        flash(f'Key "{key_name}" generated successfully! Key: {key_value}', 'success')
        return redirect(url_for('keys'))

    return render_template('generate.html', tools=ALL_TOOLS, selected=[])

@app.route('/keys')
@login_required
def keys():
    with get_db() as conn:
        all_keys = conn.execute('SELECT * FROM api_keys ORDER BY created_at DESC').fetchall()
    return render_template('keys.html', keys=all_keys)

@app.route('/edit/<int:key_id>', methods=['GET', 'POST'])
@login_required
def edit_key(key_id):
    with get_db() as conn:
        key = conn.execute('SELECT * FROM api_keys WHERE id = ?', (key_id,)).fetchone()
        if not key:
            flash('Key not found', 'danger')
            return redirect(url_for('keys'))
        allowed = json.loads(key['allowed_apis']) if key['allowed_apis'] else []

    if request.method == 'POST':
        key_name = request.form.get('key_name', '').strip()
        expiry_date = request.form.get('expiry_date')
        expiry_time = request.form.get('expiry_time')
        request_limit = request.form.get('request_limit')
        allowed_apis = request.form.getlist('allowed_apis')
        status = request.form.get('status', 'active')

        if not key_name:
            flash('Key name is required', 'danger')
            return render_template('edit_key.html', key=key, tools=ALL_TOOLS, selected=allowed)

        expiry_datetime = None
        if expiry_date and expiry_time:
            try:
                expiry_datetime = datetime.strptime(f"{expiry_date} {expiry_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                flash('Invalid expiry date/time format', 'danger')
                return render_template('edit_key.html', key=key, tools=ALL_TOOLS, selected=allowed)

        try:
            limit = int(request_limit) if request_limit else None
        except ValueError:
            flash('Request limit must be a number', 'danger')
            return render_template('edit_key.html', key=key, tools=ALL_TOOLS, selected=allowed)

        allowed_json = json.dumps(allowed_apis) if allowed_apis else None

        with get_db() as conn:
            conn.execute(
                '''UPDATE api_keys SET
                    key_name = ?,
                    expiry_date = ?,
                    request_limit = ?,
                    allowed_apis = ?,
                    status = ?
                   WHERE id = ?''',
                (key_name, expiry_datetime.isoformat() if expiry_datetime else None,
                 limit, allowed_json, status, key_id)
            )
            conn.commit()
        flash('Key updated successfully', 'success')
        return redirect(url_for('keys'))

    return render_template('edit_key.html', key=key, tools=ALL_TOOLS, selected=allowed)

@app.route('/delete/<int:key_id>', methods=['POST'])
@login_required
def delete_key(key_id):
    with get_db() as conn:
        conn.execute('DELETE FROM api_keys WHERE id = ?', (key_id,))
        conn.commit()
    flash('Key deleted', 'success')
    return redirect(url_for('keys'))

@app.route('/suspend/<int:key_id>', methods=['POST'])
@login_required
def suspend_key(key_id):
    with get_db() as conn:
        key = conn.execute('SELECT status FROM api_keys WHERE id = ?', (key_id,)).fetchone()
        if key:
            new_status = 'suspended' if key['status'] == 'active' else 'active'
            conn.execute('UPDATE api_keys SET status = ? WHERE id = ?', (new_status, key_id))
            conn.commit()
            flash(f'Key status changed to {new_status}', 'success')
    return redirect(url_for('keys'))

@app.route('/logs')
@login_required
def logs():
    key_filter = request.args.get('key_id')
    tool_filter = request.args.get('tool')
    with get_db() as conn:
        query = 'SELECT logs.*, api_keys.key_name FROM logs LEFT JOIN api_keys ON logs.key_id = api_keys.id WHERE 1=1'
        params = []
        if key_filter:
            query += ' AND logs.key_id = ?'
            params.append(key_filter)
        if tool_filter:
            query += ' AND logs.tool = ?'
            params.append(tool_filter)
        query += ' ORDER BY logs.timestamp DESC LIMIT 100'
        logs_data = conn.execute(query, params).fetchall()
        # Get all keys for filter dropdown
        keys_list = conn.execute('SELECT id, key_name FROM api_keys ORDER BY key_name').fetchall()
    return render_template('logs.html', logs=logs_data, keys=keys_list, selected_key=key_filter, selected_tool=tool_filter, tools=ALL_TOOLS)

@app.route('/endpoint')
@login_required
def endpoint():
    tool = request.args.get('tool', 'number')
    if tool not in TOOL_CONFIG:
        tool = 'number'
    # Generate example URL
    base_url = request.host_url.rstrip('/') + '/api/v1/'
    example_params = {p: 'VALUE' for p in TOOL_CONFIG[tool]['params']}
    example_url = f"{base_url}{tool}?key=YOUR_API_KEY&{urlencode(example_params)}"
    return render_template('endpoint.html', tools=ALL_TOOLS, selected_tool=tool, example_url=example_url)

# ------------------- API Proxy Endpoint -------------------

@app.route('/api/v1/<tool>', methods=['GET'])
def proxy_api(tool):
    if tool not in TOOL_CONFIG:
        return jsonify({'error': f'Tool "{tool}" not supported'}), 404

    # Get the user's API key from query
    user_key = request.args.get('key')
    if not user_key:
        return jsonify({'error': 'Missing API key (key parameter)'}), 401

    # Validate key and permissions
    key_id, error = check_key_validity(user_key, tool)
    if error:
        # Log failed attempt? We'll log only if key found but error.
        if key_id:
            log_request(key_id, tool, dict(request.args), 401)
        return jsonify({'error': error}), 401

    # Build backend URL
    backend_config = TOOL_CONFIG[tool]
    backend_url = backend_config['url']
    # Required parameters
    required = backend_config['params']
    missing = [p for p in required if p not in request.args]
    if missing:
        return jsonify({'error': f'Missing required parameters: {", ".join(missing)}'}), 400

    # Prepare parameters for backend: include master key and all provided params
    params = {'key': MASTER_KEY}
    for p in required:
        params[p] = request.args.get(p)
    # Forward any extra parameters? We'll only pass required to avoid issues.
    # But we can pass all to be safe; we'll use request.args but override key.
    # Better: copy all args, then set key to master
    all_params = dict(request.args)
    all_params['key'] = MASTER_KEY
    # Remove the user key from parameters (already used)
    all_params.pop('key', None)  # remove the user key if present

    try:
        # Make request to backend
        resp = requests.get(backend_url, params=all_params, timeout=30)
        status_code = resp.status_code
        response_data = resp.text
        # Log the request
        log_request(key_id, tool, dict(request.args), status_code)
        increment_request_count(key_id)
        # Return the backend response as is (could be JSON or text)
        return resp.content, status_code, resp.headers.items()
    except requests.exceptions.RequestException as e:
        log_request(key_id, tool, dict(request.args), 500)
        return jsonify({'error': f'Backend request failed: {str(e)}'}), 500

# ------------------- Init -------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=False, host='0.0.0.0', port=5000)
