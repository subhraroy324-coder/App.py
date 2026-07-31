import os
import sys
import re
import subprocess
import zipfile
import urllib.parse
import urllib.request
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
# Fix for Render's HTTPS proxy so Google OAuth redirect URIs match https://
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.secret_key = os.getenv('SECRET_KEY', 'vx_hosting_enterprise_secure_auth_key_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vx_hosting_enterprise.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'bot_storage_cluster'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# ==========================================
# GOOGLE OAUTH CREDENTIALS (REPLACE OR USE RENDER ENVIRONMENT VARIABLES)
# ==========================================
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET', 'YOUR_GOOGLE_CLIENT_SECRET')

ACTIVE_PROCESSES = {}
BOT_LOGS = {}

class BotInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(250), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    token = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Running")
    pid = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Authentication required. Please log in with Google to access VX Hosting.', 'error')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def start_bot_process(bot):
    if bot.id in ACTIVE_PROCESSES:
        try:
            ACTIVE_PROCESSES[bot.id].terminate()
        except:
            pass
    try:
        BOT_LOGS[bot.id] = [f"[{datetime.utcnow().strftime('%H:%M:%S')}] INITIALIZING SUBPROCESS: {bot.name}"]
        process = subprocess.Popen(
            [sys.executable, bot.filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        ACTIVE_PROCESSES[bot.id] = process
        bot.pid = process.pid
        bot.status = "Running"
        db.session.commit()
    except Exception as e:
        bot.status = "Error"
        db.session.commit()
        BOT_LOGS[bot.id] = BOT_LOGS.get(bot.id, []) + [f"ERROR: {str(e)}"]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VX Hosting | Enterprise Bot Cloud</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        [x-cloak] { display: none !important; }
        .glass-panel { background: rgba(12, 6, 6, 0.92); backdrop-filter: blur(20px); border: 1px solid rgba(220, 38, 38, 0.2); }
        .glow-red { box-shadow: 0 0 35px -5px rgba(220, 38, 38, 0.25); }
        .matrix-bg { background-image: radial-gradient(rgba(220, 38, 38, 0.08) 1px, transparent 1px); background-size: 24px 24px; }
    </style>
</head>
<body class="bg-[#050202] matrix-bg text-slate-100 font-sans"
      x-data="{ sidebarOpen: true, activeTab: 'dashboard', selectedBotLog: null, logContent: 'Loading logs...', async fetchLogs(id) { this.selectedBotLog = id; let res = await fetch('/bot/' + id + '/logs'); let data = await res.json(); this.logContent = data.logs.join('\\n'); } }">
    <div class="flex h-screen overflow-hidden">
        <!-- Sidebar -->
        <aside :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'" class="fixed inset-y-0 left-0 z-50 w-72 bg-[#0c0606] border-r border-red-950/50 transition-transform flex flex-col justify-between lg:translate-x-0 lg:static">
            <div>
                <div class="flex items-center justify-between px-6 h-20 border-b border-red-950/50">
                    <div class="flex items-center space-x-3.5">
                        <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-red-700 via-rose-600 to-black flex items-center justify-center text-white shadow-xl p-2">
                            <svg viewBox="0 0 24 24" fill="none" class="w-full h-full text-white"><path d="M2 19H22V21H2V19ZM3.5 17L5 7L9.5 12L12 5L14.5 12L19 7L20.5 17H3.5Z" fill="currentColor"/></svg>
                        </div>
                        <div>
                            <span class="text-base font-black uppercase text-white">VX Hosting</span>
                            <span class="block text-[10px] text-red-400 font-extrabold">POWERED BY VX</span>
                        </div>
                    </div>
                </div>
                <nav class="p-4 space-y-2">
                    <button @click="activeTab = 'dashboard'" :class="activeTab === 'dashboard' ? 'bg-red-600 text-white' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm"><i class="fa-solid fa-chart-pie w-5"></i><span>Dashboard</span></button>
                    <button @click="activeTab = 'deploy'" :class="activeTab === 'deploy' ? 'bg-red-600 text-white' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm"><i class="fa-solid fa-cloud-arrow-up w-5"></i><span>Upload & Host</span></button>
                </nav>
            </div>
            <div class="p-4 border-t border-red-950/50"><div class="bg-black/60 p-3 rounded-xl text-xs text-slate-300 font-bold">[VX HOSTING] Online</div></div>
        </aside>
        <!-- Main Content -->
        <div class="flex-1 flex flex-col overflow-y-auto">
            <header class="h-20 border-b border-red-950/50 bg-[#0c0606]/80 flex items-center justify-between px-6 lg:px-10">
                <h1 class="text-xl font-black uppercase text-white" x-text="activeTab"></h1>
                <div class="flex items-center space-x-3 bg-red-950/30 border border-red-900/30 px-4 py-2 rounded-2xl">
                    <img src="{{ session['user'].get('picture', '') }}" class="w-8 h-8 rounded-full border border-red-500">
                    <span class="text-xs font-bold text-white">{{ session['user'].get('name', 'User') }}</span>
                    <a href="{{ url_for('logout') }}" class="ml-2 text-slate-400 hover:text-red-400"><i class="fa-solid fa-right-from-bracket"></i></a>
                </div>
            </header>
            <main class="p-6 lg:p-10 max-w-7xl mx-auto w-full space-y-8">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="p-4 rounded-2xl border bg-red-500/10 border-red-500/20 text-red-300 text-sm font-semibold">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                <!-- Dashboard Tab -->
                <div x-show="activeTab === 'dashboard'" class="space-y-6">
                    <div class="glass-panel p-6 rounded-3xl glow-red">
                        <p class="text-xs font-black text-red-400 uppercase">Your Hosted Bots</p>
                        <h3 class="text-3xl font-black mt-2 text-white">{{ bots|length }}</h3>
                    </div>
                    <div class="glass-panel rounded-3xl overflow-hidden p-6">
                        <table class="w-full text-left">
                            <thead>
                                <tr class="text-slate-400 text-xs uppercase border-b border-red-950">
                                    <th class="py-3 px-4">Name</th>
                                    <th class="py-3 px-4">Status</th>
                                    <th class="py-3 px-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-red-950/30 text-sm">
                                {% for bot in bots %}
                                <tr>
                                    <td class="py-4 px-4 font-bold text-white">{{ bot.name }}</td>
                                    <td class="py-4 px-4"><span class="px-2.5 py-1 rounded-full text-xs font-black bg-emerald-500/10 text-emerald-400">{{ bot.status }}</span></td>
                                    <td class="py-4 px-4 text-right space-x-2">
                                        <button @click="fetchLogs({{ bot.id }})" class="px-3 py-1.5 bg-black border border-red-950 rounded-xl text-xs text-slate-300">Logs</button>
                                        <a href="{{ url_for('control_bot', bot_id=bot.id, action='delete') }}" class="px-3 py-1.5 bg-black border border-red-950 rounded-xl text-xs text-rose-400">Delete</a>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                    <div x-show="selectedBotLog !== null" x-cloak class="glass-panel rounded-3xl p-6 space-y-4">
                        <h4 class="font-black text-white text-base">Bot Terminal Output</h4>
                        <pre x-text="logContent" class="bg-black p-4 rounded-2xl text-red-400 font-mono text-xs h-48 overflow-auto"></pre>
                    </div>
                </div>
                <!-- Deploy Tab -->
                <div x-show="activeTab === 'deploy'" class="max-w-xl mx-auto">
                    <div class="glass-panel rounded-3xl p-8">
                        <h2 class="text-2xl font-black text-white mb-4">Deploy Bot 24/7</h2>
                        <form action="{{ url_for('upload_bot') }}" method="POST" enctype="multipart/form-data" class="space-y-4">
                            <input type="text" name="bot_name" required placeholder="Bot Name" class="w-full bg-black border border-red-950 rounded-xl px-4 py-3 text-white text-sm">
                            <input type="file" name="bot_file" accept=".py,.zip" required class="w-full bg-black border border-red-950 rounded-xl px-4 py-3 text-slate-400 text-sm">
                            <button type="submit" class="w-full bg-red-600 hover:bg-red-500 text-white font-black py-3 rounded-xl">Deploy Now</button>
                        </form>
                    </div>
                </div>
            </main>
        </div>
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login | VX Hosting</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>.glass-panel { background: rgba(12, 6, 6, 0.95); backdrop-filter: blur(25px); border: 1px solid rgba(220, 38, 38, 0.25); }</style>
</head>
<body class="bg-[#050202] text-slate-100 h-screen flex items-center justify-center p-4">
    <div class="glass-panel rounded-3xl p-8 max-w-md w-full text-center space-y-6 shadow-2xl">
        <div class="w-16 h-16 rounded-2xl bg-red-600 flex items-center justify-center text-white mx-auto p-3">
            <svg viewBox="0 0 24 24" fill="none" class="w-full h-full text-white"><path d="M2 19H22V21H2V19ZM3.5 17L5 7L9.5 12L12 5L14.5 12L19 7L20.5 17H3.5Z" fill="currentColor"/></svg>
        </div>
        <h1 class="text-2xl font-black uppercase text-white">VX Hosting</h1>
        <p class="text-slate-400 text-sm">Authenticate via Google to access dashboard and cloud hosting.</p>
        <a href="{{ url_for('login') }}" class="w-full bg-red-600 hover:bg-red-500 text-white font-bold py-3.5 rounded-xl block uppercase tracking-wider text-sm"><i class="fa-brands fa-google mr-2"></i> Sign in with Google</a>
    </div>
</body>
</html>
"""

@app.route('/login-page')
def login_page():
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    params = {
        'client_id': app.config['GOOGLE_CLIENT_ID'],
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params))

@app.route('/authorize')
def authorize():
    code = request.args.get('code')
    if not code:
        flash('Google authentication failed: No authorization code received.', 'error')
        return redirect(url_for('login_page'))
    
    redirect_uri = url_for('authorize', _external=True)
    payload = {
        'code': code,
        'client_id': app.config['GOOGLE_CLIENT_ID'],
        'client_secret': app.config['GOOGLE_CLIENT_SECRET'],
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    try:
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, method='POST')
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            access_token = res_data.get('access_token')
            
        userinfo_url = f'https://www.googleapis.com/oauth2/v3/userinfo?access_token={access_token}'
        with urllib.request.urlopen(userinfo_url) as response:
            user_info = json.loads(response.read().decode('utf-8'))
            
        session['user'] = user_info
        flash('Successfully authenticated!', 'success')
    except Exception as e:
        flash(f'Authentication error: {str(e)}.', 'error')
        return redirect(url_for('login_page'))
        
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

@app.route('/')
@login_required
def index():
    user_email = session['user'].get('email')
    bots = BotInstance.query.filter_by(user_email=user_email).all()
    return render_template_string(HTML_TEMPLATE, bots=bots)

@app.route('/upload', methods=['POST'])
@login_required
def upload_bot():
    bot_name = request.form.get('bot_name')
    file = request.files.get('bot_file')
    user_email = session['user'].get('email')

    if not file or file.filename == '':
        flash('Please select a valid file.', 'error')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    token_match = re.search(r'\d{9,10}:[A-Za-z0-9_-]{35}', content)
    bot_token = token_match.group(0) if token_match else "mock_token_12345"

    new_bot = BotInstance(user_email=user_email, name=bot_name, filename=filename, filepath=filepath, token=bot_token)
    db.session.add(new_bot)
    db.session.commit()
    start_bot_process(new_bot)
    flash(f'Bot "{bot_name}" deployed successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/bot/<int:bot_id>/logs')
@login_required
def get_bot_logs(bot_id):
    bot = BotInstance.query.get_or_404(bot_id)
    if bot.user_email != session['user'].get('email'):
        return jsonify({"logs": ["Unauthorized."]}), 403
    return jsonify({"logs": BOT_LOGS.get(bot_id, ["No logs yet."])})

@app.route('/bot/<int:bot_id>/<action>')
@login_required
def control_bot(bot_id, action):
    bot = BotInstance.query.get_or_404(bot_id)
    if bot.user_email != session['user'].get('email'):
        return redirect(url_for('index'))
    if action == 'delete':
        if bot.id in ACTIVE_PROCESSES:
            try: ACTIVE_PROCESSES[bot.id].terminate()
            except: pass
        db.session.delete(bot)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
