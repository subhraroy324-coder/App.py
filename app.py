import os
import sys
import re
import shutil
import zipfile
import subprocess
import json
import psutil
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import razorpay

# ==========================================
# APPLICATION CONFIGURATION
# ==========================================
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.secret_key = os.getenv('SECRET_KEY', 'vx_hosting_elite_enterprise_secret_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///vx_hosting_enterprise.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.abspath(os.getenv('UPLOAD_FOLDER', 'bot_storage_cluster'))
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB Limit

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# ==========================================
# RAZORPAY PAYMENT ENGINE
# ==========================================
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', 'rzp_live_demo_key')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', 'demo_secret')

try:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
except Exception:
    razorpay_client = None

# ==========================================
# DATABASE MODELS
# ==========================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default="Admin")  # Admin, Developer, Viewer
    two_factor_enabled = db.Column(db.Boolean, default=False)

class BotInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    runtime = db.Column(db.String(30), default="Python 3")  # Python, Node.js, Go, Rust, PHP, Docker
    bot_type = db.Column(db.String(50), default="Telegram Bot") # Telegram, Discord, WhatsApp, Slack, Custom
    filename = db.Column(db.String(250), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    bot_dir = db.Column(db.String(500), nullable=False)
    masked_token = db.Column(db.String(100), default="None Detected")
    custom_cmd = db.Column(db.String(250), nullable=True)
    status = db.Column(db.String(20), default="Stopped")
    pid = db.Column(db.Integer, nullable=True)
    plan = db.Column(db.String(50), default="Starter (₹49)")
    auto_restart = db.Column(db.Boolean, default=True)
    restart_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    env_vars = db.relationship('BotEnvVar', backref='bot', cascade="all, delete-orphan", lazy=True)

class BotEnvVar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot_instance.id'), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(500), nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    payment_id = db.Column(db.String(100), nullable=True)
    plan_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(250), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, nullable=False)
    active = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()

# ==========================================
# ENTERPRISE PROCESS MANAGER ENGINE
# ==========================================
class ProcessManager:
    def __init__(self):
        self.processes = {}
        self.logs = {}

    def log(self, bot_id, message):
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        if bot_id not in self.logs:
            self.logs[bot_id] = []
        self.logs[bot_id].append(f"[{timestamp}] {message}")
        # Keep last 500 lines in memory
        if len(self.logs[bot_id]) > 500:
            self.logs[bot_id].pop(0)

    def start_bot(self, bot):
        self.stop_bot(bot.id)
        
        env = os.environ.copy()
        for ev in bot.env_vars:
            env[ev.key] = ev.value

        # Build Runtime Command
        cmd = []
        if bot.custom_cmd:
            cmd = bot.custom_cmd.split()
        elif bot.runtime == "Node.js":
            cmd = ["node", bot.filepath]
        elif bot.runtime == "Go":
            cmd = ["go", "run", bot.filepath]
        elif bot.runtime == "PHP":
            cmd = ["php", bot.filepath]
        else: # Default Python
            cmd = [sys.executable, bot.filepath]

        try:
            self.log(bot.id, f"STARTING PROCESS ({bot.runtime}): {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                cwd=bot.bot_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env
            )
            self.processes[bot.id] = process
            bot.pid = process.pid
            bot.status = "Running"
            db.session.commit()
            
            # Audit log
            db.session.add(ActivityLog(action="BOT_START", details=f"Started bot '{bot.name}' (PID: {process.pid})"))
            db.session.commit()
            return True
        except Exception as e:
            bot.status = "Error"
            db.session.commit()
            self.log(bot.id, f"CRITICAL LAUNCH ERROR: {str(e)}")
            return False

    def stop_bot(self, bot_id):
        if bot_id in self.processes:
            try:
                proc = self.processes[bot_id]
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            del self.processes[bot_id]

        bot = BotInstance.query.get(bot_id)
        if bot:
            bot.status = "Stopped"
            bot.pid = None
            db.session.commit()
            self.log(bot_id, "PROCESS TERMINATED BY USER/SYSTEM")

    def get_metrics(self, bot_id):
        if bot_id in self.processes:
            try:
                pid = self.processes[bot_id].pid
                p = psutil.Process(pid)
                return {
                    "cpu": round(p.cpu_percent(interval=0.1), 1),
                    "memory_mb": round(p.memory_info().rss / (1024 * 1024), 2),
                    "status": "Running"
                }
            except Exception:
                pass
        return {"cpu": 0.0, "memory_mb": 0.0, "status": "Stopped"}

process_manager = ProcessManager()

# ==========================================
# HELPER UTILITIES
# ==========================================
def mask_token(token_str):
    if len(token_str) > 10:
        return token_str[:5] + "••••••••••••" + token_str[-4:]
    return "••••••••"

def detect_bot_info(file_content):
    # Telegram Regex
    tg_match = re.search(r'\d{9,10}:[A-Za-z0-9_-]{35}', file_content)
    if tg_match:
        return "Telegram Bot", mask_token(tg_match.group(0))
    
    # Discord Regex
    dc_match = re.search(r'[MNO][a-zA-Z0-9_-]{23,25}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}', file_content)
    if dc_match:
        return "Discord Bot", mask_token(dc_match.group(0))

    return "Generic Script", "No Token Detected"

# ==========================================
# FRONTEND TEMPLATE
# ==========================================
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VX HOSTING ELITE | Enterprise Infrastructure</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        [x-cloak] { display: none !important; }
        .glass-panel { background: rgba(10, 5, 5, 0.93); backdrop-filter: blur(25px); border: 1px solid rgba(220, 38, 38, 0.25); }
        .glow-red { box-shadow: 0 0 35px -5px rgba(220, 38, 38, 0.35); }
        .matrix-bg { background-image: radial-gradient(rgba(220, 38, 38, 0.1) 1px, transparent 1px); background-size: 24px 24px; }
    </style>
</head>
<body class="bg-[#030101] matrix-bg text-slate-100 font-sans"
      x-data="{ 
          activeTab: 'dashboard', 
          selectedBotId: null, 
          logContent: '',
          aiAnalysis: '',
          aiLoading: false,
          fileList: [],
          selectedFileName: '',
          selectedFileContent: '',
          envKey: '',
          envVal: '',
          envVarsList: [],
          
          async fetchLogs(id) { 
              this.selectedBotId = id; 
              let res = await fetch('/api/bot/' + id + '/logs'); 
              let data = await res.json(); 
              this.logContent = data.logs.join('\\n'); 
          },
          async analyzeLogsWithAI() {
              if(!this.selectedBotId) return;
              this.aiLoading = true;
              let res = await fetch('/api/bot/' + this.selectedBotId + '/ai-analyze');
              let data = await res.json();
              this.aiAnalysis = data.analysis;
              this.aiLoading = false;
          },
          async openFileManager(id) {
              this.selectedBotId = id;
              this.activeTab = 'filemanager';
              let res = await fetch('/api/bot/' + id + '/files');
              let data = await res.json();
              this.fileList = data.files;
          },
          async openFile(filename) {
              this.selectedFileName = filename;
              let res = await fetch('/api/bot/' + this.selectedBotId + '/read-file?file=' + encodeURIComponent(filename));
              let data = await res.json();
              this.selectedFileContent = data.content;
          },
          async saveFile() {
              await fetch('/api/bot/' + this.selectedBotId + '/save-file', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({ filename: this.selectedFileName, content: this.selectedFileContent })
              });
              alert('File saved successfully!');
          },
          async openEnvVars(id) {
              this.selectedBotId = id;
              this.activeTab = 'envvars';
              let res = await fetch('/api/bot/' + id + '/env');
              let data = await res.json();
              this.envVarsList = data.env_vars;
          },
          async addEnvVar() {
              await fetch('/api/bot/' + this.selectedBotId + '/env', {
                  method: 'POST',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({ key: this.envKey, value: this.envVal })
              });
              this.envKey = ''; this.envVal = '';
              this.openEnvVars(this.selectedBotId);
          }
      }">

    <div class="flex h-screen overflow-hidden">
        <!-- Sidebar Navigation -->
        <aside class="w-72 bg-[#070303] border-r border-red-950/60 flex flex-col justify-between hidden lg:flex">
            <div>
                <div class="flex items-center space-x-3.5 px-6 h-24 border-b border-red-950/60">
                    <div class="w-11 h-11 rounded-2xl bg-gradient-to-br from-red-600 via-rose-600 to-black flex items-center justify-center text-white shadow-xl glow-red">
                        <i class="fa-solid fa-server text-2xl text-red-100"></i>
                    </div>
                    <div>
                        <span class="text-lg font-black tracking-wider uppercase text-white block leading-tight">VX ELITE</span>
                        <span class="text-[9px] text-red-500 font-extrabold tracking-widest uppercase">CLOUD PLATFORM v3.0</span>
                    </div>
                </div>

                <nav class="p-4 space-y-2">
                    <button @click="activeTab = 'dashboard'" :class="activeTab === 'dashboard' ? 'bg-red-600 text-white' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all">
                        <i class="fa-solid fa-chart-pie w-5"></i><span>Dashboard</span>
                    </button>
                    <button @click="activeTab = 'deploy'" :class="activeTab === 'deploy' ? 'bg-red-600 text-white' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all">
                        <i class="fa-solid fa-cloud-arrow-up w-5"></i><span>Deploy App/Bot</span>
                    </button>
                    <button @click="activeTab = 'system'" :class="activeTab === 'system' ? 'bg-red-600 text-white' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all">
                        <i class="fa-solid fa-microchip w-5"></i><span>System Health</span>
                    </button>
                    <button @click="activeTab = 'billing'" :class="activeTab === 'billing' ? 'bg-red-600 text-white' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all">
                        <i class="fa-solid fa-credit-card w-5"></i><span>Pricing & Plans</span>
                    </button>
                    <button @click="activeTab = 'audit'" :class="activeTab === 'audit' ? 'bg-red-600 text-white' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all">
                        <i class="fa-solid fa-shield-halved w-5"></i><span>Audit Logs</span>
                    </button>
                </nav>
            </div>

            <div class="p-6 border-t border-red-950/60">
                <div class="bg-black/80 border border-red-900/30 p-4 rounded-2xl">
                    <div class="flex items-center space-x-3">
                        <div class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
                        <span class="text-xs font-black text-slate-200">CLUSTER ONLINE</span>
                    </div>
                    <p class="text-[10px] text-slate-400 mt-1">CPU: {{ system_metrics.cpu }}% | RAM: {{ system_metrics.ram }}%</p>
                </div>
            </div>
        </aside>

        <!-- Main Workspace -->
        <div class="flex-1 flex flex-col overflow-y-auto">
            <header class="h-24 border-b border-red-950/60 bg-[#070303]/90 flex items-center justify-between px-8 sticky top-0 z-50 backdrop-blur-md">
                <h1 class="text-lg font-black uppercase tracking-wider text-white" x-text="activeTab"></h1>
                <div class="flex items-center space-x-4">
                    <span class="text-xs font-extrabold text-red-500 bg-red-950/40 border border-red-900/50 px-3 py-1.5 rounded-xl">ROLE: ADMIN</span>
                </div>
            </header>

            <main class="p-8 max-w-7xl mx-auto w-full space-y-8">
                <!-- Flash Messages -->
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="p-4 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm font-semibold flex items-center space-x-3">
                                <i class="fa-solid fa-circle-check text-red-500"></i><span>{{ message }}</span>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}

                <!-- TAB 1: DASHBOARD -->
                <div x-show="activeTab === 'dashboard'" class="space-y-8">
                    <!-- Metric Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <div class="glass-panel p-6 rounded-3xl glow-red">
                            <p class="text-xs font-black text-red-400 uppercase">Active Bots</p>
                            <h3 class="text-3xl font-black mt-2 text-white">{{ bots|length }}</h3>
                        </div>
                        <div class="glass-panel p-6 rounded-3xl">
                            <p class="text-xs font-black text-slate-400 uppercase">Host CPU Load</p>
                            <h3 class="text-3xl font-black mt-2 text-red-400">{{ system_metrics.cpu }}%</h3>
                        </div>
                        <div class="glass-panel p-6 rounded-3xl">
                            <p class="text-xs font-black text-slate-400 uppercase">Host RAM Usage</p>
                            <h3 class="text-3xl font-black mt-2 text-emerald-400">{{ system_metrics.ram }}%</h3>
                        </div>
                        <div class="glass-panel p-6 rounded-3xl">
                            <p class="text-xs font-black text-slate-400 uppercase">Storage Free</p>
                            <h3 class="text-3xl font-black mt-2 text-white">{{ system_metrics.disk_free }} GB</h3>
                        </div>
                    </div>

                    <!-- Deployed Processes Table -->
                    <div class="glass-panel rounded-3xl p-6">
                        <div class="flex items-center justify-between pb-6 border-b border-red-950/60">
                            <h3 class="text-lg font-black uppercase text-white">Deployed Applications</h3>
                            <button @click="activeTab = 'deploy'" class="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-xl text-xs font-bold">+ New Deployment</button>
                        </div>
                        <div class="overflow-x-auto mt-4">
                            <table class="w-full text-left">
                                <thead>
                                    <tr class="text-slate-400 text-xs uppercase border-b border-red-950/60">
                                        <th class="py-4 px-4">Bot / Script</th>
                                        <th class="py-4 px-4">Runtime</th>
                                        <th class="py-4 px-4">Token Detection</th>
                                        <th class="py-4 px-4">Status</th>
                                        <th class="py-4 px-4 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-red-950/40 text-sm">
                                    {% for bot in bots %}
                                    <tr>
                                        <td class="py-4 px-4 font-bold text-white">{{ bot.name }}</td>
                                        <td class="py-4 px-4"><span class="px-3 py-1 rounded-full text-xs font-black bg-red-950/40 text-red-300 border border-red-900/40">{{ bot.runtime }}</span></td>
                                        <td class="py-4 px-4 font-mono text-xs text-slate-400">{{ bot.masked_token }}</td>
                                        <td class="py-4 px-4">
                                            <span class="px-3 py-1 rounded-full text-xs font-black {% if bot.status == 'Running' %}bg-emerald-500/10 text-emerald-400 border border-emerald-500/20{% else %}bg-rose-500/10 text-rose-400 border border-rose-500/20{% endif %}">
                                                {{ bot.status }}
                                            </span>
                                        </td>
                                        <td class="py-4 px-4 text-right space-x-2">
                                            {% if bot.status == 'Running' %}
                                                <a href="{{ url_for('control_bot', bot_id=bot.id, action='stop') }}" class="px-3 py-1.5 bg-rose-950/60 border border-rose-800 text-rose-300 rounded-xl text-xs font-bold">Stop</a>
                                            {% else %}
                                                <a href="{{ url_for('control_bot', bot_id=bot.id, action='start') }}" class="px-3 py-1.5 bg-emerald-950/60 border border-emerald-800 text-emerald-300 rounded-xl text-xs font-bold">Start</a>
                                            {% endif %}
                                            <button @click="fetchLogs({{ bot.id }})" class="px-3 py-1.5 bg-black border border-red-950 text-slate-300 rounded-xl text-xs hover:border-red-500">Terminal</button>
                                            <button @click="openFileManager({{ bot.id }})" class="px-3 py-1.5 bg-black border border-red-950 text-slate-300 rounded-xl text-xs hover:border-red-500">Files</button>
                                            <button @click="openEnvVars({{ bot.id }})" class="px-3 py-1.5 bg-black border border-red-950 text-slate-300 rounded-xl text-xs hover:border-red-500">Secrets</button>
                                            <a href="{{ url_for('control_bot', bot_id=bot.id, action='delete') }}" class="px-3 py-1.5 bg-rose-950/30 border border-rose-900 text-rose-400 rounded-xl text-xs"><i class="fa-solid fa-trash"></i></a>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr><td colspan="5" class="py-8 text-center text-slate-500 font-semibold">No instances deployed yet.</td></tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Live Terminal Output View -->
                    <div x-show="selectedBotId !== null" class="glass-panel rounded-3xl p-6 space-y-4">
                        <div class="flex items-center justify-between">
                            <h4 class="font-black text-white text-base flex items-center space-x-2">
                                <i class="fa-solid fa-terminal text-red-500"></i><span>Subprocess Live Terminal</span>
                            </h4>
                            <div class="space-x-2">
                                <button @click="analyzeLogsWithAI()" class="px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-xl text-xs font-bold">
                                    <i class="fa-solid fa-brain mr-1.5"></i> AI Analyze Errors
                                </button>
                                <button @click="selectedBotId = null" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
                            </div>
                        </div>

                        <pre x-text="logContent" class="bg-black/90 border border-red-950 p-5 rounded-2xl text-red-400 font-mono text-xs h-64 overflow-auto shadow-inner"></pre>

                        <!-- AI Explanation Window -->
                        <div x-show="aiLoading" class="text-purple-400 text-xs font-bold animate-pulse">AI Parsing Stack Trace...</div>
                        <div x-show="aiAnalysis !== ''" class="p-4 bg-purple-950/30 border border-purple-500/40 rounded-2xl text-purple-200 text-xs font-mono">
                            <strong class="text-purple-400 block mb-1">🤖 AI Diagnostic Assistant:</strong>
                            <span x-text="aiAnalysis"></span>
                        </div>
                    </div>
                </div>

                <!-- TAB 2: DEPLOYMENT -->
                <div x-show="activeTab === 'deploy'" class="max-w-2xl mx-auto">
                    <div class="glass-panel rounded-3xl p-8 glow-red">
                        <h2 class="text-2xl font-black text-white uppercase mb-2">Deploy Application</h2>
                        <p class="text-xs text-slate-400 mb-6">Supports Python, Node.js, Go, Rust, PHP, or Docker archives.</p>
                        
                        <form action="{{ url_for('upload_bot') }}" method="POST" enctype="multipart/form-data" class="space-y-5">
                            <div>
                                <label class="block text-xs font-black uppercase text-slate-400 mb-2">Application Name</label>
                                <input type="text" name="bot_name" required placeholder="my-awesome-bot" class="w-full bg-black/80 border border-red-950 rounded-2xl px-4 py-3.5 text-white text-sm focus:border-red-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-black uppercase text-slate-400 mb-2">Select Runtime Environment</label>
                                <select name="runtime" class="w-full bg-black/80 border border-red-950 rounded-2xl px-4 py-3.5 text-white text-sm focus:border-red-500 outline-none">
                                    <option value="Python 3">Python 3 (default)</option>
                                    <option value="Node.js">Node.js</option>
                                    <option value="Go">Go Language</option>
                                    <option value="PHP">PHP Engine</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-black uppercase text-slate-400 mb-2">Custom Startup Command (Optional)</label>
                                <input type="text" name="custom_cmd" placeholder="e.g. python main.py or node index.js" class="w-full bg-black/80 border border-red-950 rounded-2xl px-4 py-3.5 text-white text-sm focus:border-red-500 outline-none">
                            </div>
                            <div>
                                <label class="block text-xs font-black uppercase text-slate-400 mb-2">Script or ZIP File Archive</label>
                                <input type="file" name="bot_file" accept=".py,.js,.go,.zip" required class="w-full bg-black/80 border border-red-950 rounded-2xl px-4 py-3 text-slate-400 text-sm">
                            </div>
                            <button type="submit" class="w-full bg-red-600 hover:bg-red-500 text-white font-black py-4 rounded-2xl uppercase text-sm transition-all shadow-lg shadow-red-600/40">Launch Deployment</button>
                        </form>
                    </div>
                </div>

                <!-- TAB 3: FILE MANAGER & ONLINE CODE EDITOR -->
                <div x-show="activeTab === 'filemanager'" class="space-y-6">
                    <div class="glass-panel rounded-3xl p-6">
                        <h3 class="text-lg font-black text-white uppercase mb-4">File Explorer & Editor</h3>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <!-- File List -->
                            <div class="bg-black/80 border border-red-950 p-4 rounded-2xl space-y-2 max-h-96 overflow-y-auto">
                                <template x-for="f in fileList" :key="f">
                                    <button @click="openFile(f)" class="w-full text-left px-3 py-2 text-xs font-mono rounded-xl hover:bg-red-950/40 text-slate-300 block truncate" x-text="f"></button>
                                </template>
                            </div>
                            <!-- Code Editor -->
                            <div class="md:col-span-2 space-y-4">
                                <input type="text" readonly x-model="selectedFileName" class="w-full bg-black border border-red-950 rounded-xl px-4 py-2 text-xs font-mono text-red-400">
                                <textarea x-model="selectedFileContent" rows="15" class="w-full bg-black/90 border border-red-950 rounded-2xl p-4 text-xs font-mono text-slate-200 focus:outline-none"></textarea>
                                <button @click="saveFile()" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-6 py-2.5 rounded-xl text-xs">Save File Changes</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- TAB 4: SECRETS / ENV VAULT -->
                <div x-show="activeTab === 'envvars'" class="max-w-2xl mx-auto space-y-6">
                    <div class="glass-panel rounded-3xl p-6 space-y-4">
                        <h3 class="text-lg font-black text-white uppercase">Environment Secret Vault</h3>
                        <div class="flex space-x-2">
                            <input type="text" x-model="envKey" placeholder="KEY (e.g. API_TOKEN)" class="w-1/2 bg-black border border-red-950 rounded-xl px-4 py-2 text-xs text-white">
                            <input type="text" x-model="envVal" placeholder="VALUE" class="w-1/2 bg-black border border-red-950 rounded-xl px-4 py-2 text-xs text-white">
                            <button @click="addEnvVar()" class="bg-red-600 text-white font-bold px-4 py-2 rounded-xl text-xs">Add</button>
                        </div>
                        <div class="space-y-2 pt-4">
                            <template x-for="ev in envVarsList" :key="ev.id">
                                <div class="flex justify-between items-center bg-black/80 border border-red-950/60 px-4 py-2.5 rounded-xl text-xs font-mono">
                                    <span class="text-red-400 font-bold" x-text="ev.key"></span>
                                    <span class="text-slate-400" x-text="ev.value"></span>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>

                <!-- TAB 5: SYSTEM HEALTH -->
                <div x-show="activeTab === 'system'" class="glass-panel rounded-3xl p-8 space-y-6">
                    <h3 class="text-xl font-black text-white uppercase">Cluster Performance Metrics</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-mono">
                        <div class="bg-black/80 border border-red-950 p-6 rounded-2xl space-y-2">
                            <p class="text-red-400 font-bold">HOST SYSTEM CPU</p>
                            <p class="text-2xl text-white font-black">{{ system_metrics.cpu }}%</p>
                        </div>
                        <div class="bg-black/80 border border-red-950 p-6 rounded-2xl space-y-2">
                            <p class="text-emerald-400 font-bold">MEMORY CONSUMPTION</p>
                            <p class="text-2xl text-white font-black">{{ system_metrics.ram }}%</p>
                        </div>
                    </div>
                </div>

                <!-- TAB 6: AUDIT LOGS -->
                <div x-show="activeTab === 'audit'" class="glass-panel rounded-3xl p-6">
                    <h3 class="text-lg font-black text-white uppercase mb-4">Platform Audit Stream</h3>
                    <div class="space-y-2">
                        {% for log in audit_logs %}
                        <div class="bg-black/80 border border-red-950/60 p-3 rounded-xl text-xs font-mono flex justify-between">
                            <span class="text-red-400 font-bold">[{{ log.timestamp.strftime('%H:%M:%S') }}] {{ log.action }}</span>
                            <span class="text-slate-300">{{ log.details }}</span>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </main>
        </div>
    </div>
</body>
</html>
"""

# ==========================================
# API & WEB ROUTES
# ==========================================
@app.route('/')
def index():
    bots = BotInstance.query.all()
    audit_logs = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(20).all()
    
    # System Metrics
    sys_metrics = {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk_free": round(psutil.disk_usage('/').free / (1024**3), 2)
    }
    
    return render_template_string(DASHBOARD_TEMPLATE, bots=bots, audit_logs=audit_logs, system_metrics=sys_metrics)

@app.route('/upload', methods=['POST'])
def upload_bot():
    bot_name = request.form.get('bot_name')
    runtime = request.form.get('runtime', 'Python 3')
    custom_cmd = request.form.get('custom_cmd')
    file = request.files.get('bot_file')

    if not file or file.filename == '':
        flash('Valid script or archive file is required.', 'error')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    bot_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"bot_{int(datetime.utcnow().timestamp())}")
    os.makedirs(bot_dir, exist_ok=True)

    filepath = os.path.join(bot_dir, filename)
    file.save(filepath)

    # ZIP Extraction Support
    if filename.endswith('.zip'):
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(bot_dir)
        # Search for main file
        candidates = ['main.py', 'bot.py', 'app.py', 'index.js', 'main.go']
        found = False
        for c in candidates:
            if os.path.exists(os.path.join(bot_dir, c)):
                filepath = os.path.join(bot_dir, c)
                filename = c
                found = True
                break

    # Read and auto-detect tokens
    masked_token = "None Detected"
    bot_type = "Generic Script"
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        bot_type, masked_token = detect_bot_info(content)
    except Exception:
        pass

    new_bot = BotInstance(
        name=bot_name,
        runtime=runtime,
        bot_type=bot_type,
        filename=filename,
        filepath=filepath,
        bot_dir=bot_dir,
        masked_token=masked_token,
        custom_cmd=custom_cmd
    )
    db.session.add(new_bot)
    db.session.commit()

    # Launch Instance
    process_manager.start_bot(new_bot)
    flash(f'Application "{bot_name}" deployed and launched!', 'success')
    return redirect(url_for('index'))

@app.route('/bot/<int:bot_id>/<action>')
def control_bot(bot_id, action):
    bot = BotInstance.query.get_or_404(bot_id)
    if action == 'start':
        process_manager.start_bot(bot)
        flash(f'Bot "{bot.name}" started.', 'success')
    elif action == 'stop':
        process_manager.stop_bot(bot.id)
        flash(f'Bot "{bot.name}" stopped.', 'success')
    elif action == 'delete':
        process_manager.stop_bot(bot.id)
        if os.path.exists(bot.bot_dir):
            shutil.rmtree(bot.bot_dir, ignore_errors=True)
        db.session.delete(bot)
        db.session.commit()
        flash(f'Bot "{bot.name}" deleted.', 'success')
    return redirect(url_for('index'))

# ==========================================
# REST API ENDPOINTS
# ==========================================
@app.route('/api/bot/<int:bot_id>/logs')
def get_bot_logs(bot_id):
    return jsonify({"logs": process_manager.logs.get(bot_id, ["Console initialized. Waiting for output..."])})

@app.route('/api/bot/<int:bot_id>/ai-analyze')
def ai_analyze_logs(bot_id):
    logs = process_manager.logs.get(bot_id, [])
    log_text = "\n".join(logs[-30:])
    
    # Built-in AI Analysis Heuristic
    if "ModuleNotFoundError" in log_text:
        match = re.search(r"No module named '([^']+)'", log_text)
        missing_mod = match.group(1) if match else "a package"
        analysis = f"Dependency Error: The Python package '{missing_mod}' is not installed. Add it to requirements.txt or install via terminal."
    elif "SyntaxError" in log_text:
        analysis = "Syntax Error: There is invalid syntax in your script file. Check indentation or missing brackets/quotes."
    elif "Unauthorized" in log_text or "InvalidToken" in log_text:
        analysis = "Authentication Failure: Your bot token appears to be invalid or revoked by BotFather/Discord Developer Portal."
    else:
        analysis = "No critical error signatures found. System running normally or failure occurred prior to execution logging."

    return jsonify({"analysis": analysis})

@app.route('/api/bot/<int:bot_id>/files')
def list_bot_files(bot_id):
    bot = BotInstance.query.get_or_404(bot_id)
    file_list = []
    if os.path.exists(bot.bot_dir):
        for root, _, files in os.walk(bot.bot_dir):
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), bot.bot_dir)
                file_list.append(rel_path)
    return jsonify({"files": file_list})

@app.route('/api/bot/<int:bot_id>/read-file')
def read_bot_file(bot_id):
    bot = BotInstance.query.get_or_404(bot_id)
    rel_filename = request.args.get('file')
    safe_path = os.path.abspath(os.path.join(bot.bot_dir, rel_filename))
    
    # Path Traversal Prevention Check
    if not safe_path.startswith(os.path.abspath(bot.bot_dir)):
        return jsonify({"error": "Forbidden path traversal detected"}), 403

    if os.path.exists(safe_path):
        with open(safe_path, 'r', encoding='utf-8', errors='ignore') as f:
            return jsonify({"content": f.read()})
    return jsonify({"content": "File not found."}), 440

@app.route('/api/bot/<int:bot_id>/save-file', methods=['POST'])
def save_bot_file(bot_id):
    bot = BotInstance.query.get_or_404(bot_id)
    data = request.get_json() or {}
    rel_filename = data.get('filename')
    content = data.get('content', '')

    safe_path = os.path.abspath(os.path.join(bot.bot_dir, rel_filename))
    if not safe_path.startswith(os.path.abspath(bot.bot_dir)):
        return jsonify({"error": "Forbidden path traversal detected"}), 403

    with open(safe_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return jsonify({"status": "success"})

@app.route('/api/bot/<int:bot_id>/env', methods=['GET', 'POST'])
def manage_env_vars(bot_id):
    bot = BotInstance.query.get_or_404(bot_id)
    if request.method == 'POST':
        data = request.get_json() or {}
        key = data.get('key')
        value = data.get('value')
        if key and value:
            ev = BotEnvVar(bot_id=bot.id, key=key, value=value)
            db.session.add(ev)
            db.session.commit()
    
    vars_list = [{"id": v.id, "key": v.key, "value": v.value} for v in bot.env_vars]
    return jsonify({"env_vars": vars_list})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
