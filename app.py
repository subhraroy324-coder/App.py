import os
import sys
import re
import subprocess
import json
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import razorpay

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.secret_key = os.getenv('SECRET_KEY', 'vx_hosting_elite_secure_key_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vx_hosting_enterprise.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'bot_storage_cluster'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# ==========================================
# YOUR LIVE RAZORPAY CREDENTIALS
# ==========================================
RAZORPAY_KEY_ID = 'rzp_live_TGzOHwqjwcYfov'
RAZORPAY_KEY_SECRET = 'qbqBS1dxdFRYTizozIH083E4'

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

ACTIVE_PROCESSES = {}
BOT_LOGS = {}

class BotInstance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(250), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    token = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default="Running")
    pid = db.Column(db.Integer, nullable=True)
    plan = db.Column(db.String(50), default="Starter (₹49)")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), nullable=False)
    payment_id = db.Column(db.String(100), nullable=True)
    plan_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def start_bot_process(bot):
    if bot.id in ACTIVE_PROCESSES:
        try:
            ACTIVE_PROCESSES[bot.id].terminate()
        except:
            pass
    try:
        BOT_LOGS[bot.id] = [f"[{datetime.utcnow().strftime('%H:%M:%S')}] INITIALIZING KERNEL SUBPROCESS: {bot.name}"]
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
        BOT_LOGS[bot.id] = BOT_LOGS.get(bot.id, []) + [f"CRITICAL ERROR: {str(e)}"]

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VX HOSTING ELITE | Enterprise Bot Infrastructure</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        [x-cloak] { display: none !important; }
        .glass-panel { background: rgba(10, 5, 5, 0.94); backdrop-filter: blur(25px); border: 1px solid rgba(220, 38, 38, 0.25); }
        .glow-red { box-shadow: 0 0 40px -8px rgba(220, 38, 38, 0.3); }
        .matrix-bg { background-image: radial-gradient(rgba(220, 38, 38, 0.08) 1px, transparent 1px); background-size: 28px 28px; }
    </style>
</head>
<body class="bg-[#030101] matrix-bg text-slate-100 font-sans"
      x-data="{ 
          activeTab: 'dashboard', 
          selectedBotLog: null, 
          logContent: 'Initializing secure terminal stream...', 
          async fetchLogs(id) { 
              this.selectedBotLog = id; 
              let res = await fetch('/bot/' + id + '/logs'); 
              let data = await res.json(); 
              this.logContent = data.logs.join('\\n'); 
          },
          payWithRazorpay(planName, amountInINR) {
              fetch('/create-order', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ plan: planName, amount: amountInINR })
              })
              .then(res => res.json())
              .then(order => {
                  var options = {
                      \"key\": order.key_id,
                      \"amount\": order.amount,
                      \"currency\": \"INR\",
                      \"name\": \"VX Hosting Elite\",
                      \"description\": \"Subscription for \" + planName,
                      \"order_id\": order.order_id,
                      \"handler\": function (response){
                          fetch('/payment-success', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                  payment_id: response.razorpay_payment_id,
                                  order_id: response.razorpay_order_id,
                                  signature: response.razorpay_signature,
                                  plan: planName
                              })
                          }).then(res => {
                              window.location.reload();
                          });
                      },
                      \"theme\": { \"color\": \"#dc2626\" }
                  };
                  var rzp1 = new Razorpay(options);
                  rzp1.open();
              });
          }
      }">
    <div class="flex h-screen overflow-hidden">
        <!-- Sidebar -->
        <aside class="w-72 bg-[#070303] border-r border-red-950/60 flex flex-col justify-between hidden lg:flex">
            <div>
                <div class="flex items-center space-x-3.5 px-6 h-24 border-b border-red-950/60">
                    <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-red-700 via-rose-600 to-black flex items-center justify-center text-white shadow-2xl p-2.5 glow-red">
                        <i class="fa-solid fa-server text-xl"></i>
                    </div>
                    <div>
                        <span class="text-base font-black tracking-wider uppercase text-white">VX HOSTING</span>
                        <span class="block text-[10px] text-red-500 font-extrabold tracking-widest">ELITE INFRASTRUCTURE</span>
                    </div>
                </div>
                <nav class="p-4 space-y-2">
                    <button @click="activeTab = 'dashboard'" :class="activeTab === 'dashboard' ? 'bg-red-600 text-white shadow-lg shadow-red-600/30' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all"><i class="fa-solid fa-chart-pie w-5"></i><span>Dashboard</span></button>
                    <button @click="activeTab = 'deploy'" :class="activeTab === 'deploy' ? 'bg-red-600 text-white shadow-lg shadow-red-600/30' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all"><i class="fa-solid fa-cloud-arrow-up w-5"></i><span>Deploy Bot</span></button>
                    <button @click="activeTab = 'billing'" :class="activeTab === 'billing' ? 'bg-red-600 text-white shadow-lg shadow-red-600/30' : 'text-slate-400 hover:bg-red-950/30'" class="w-full flex items-center space-x-3.5 px-4 py-3.5 rounded-2xl font-bold text-sm transition-all"><i class="fa-solid fa-credit-card w-5"></i><span>Pricing & Billing</span></button>
                </nav>
            </div>
            <div class="p-6 border-t border-red-950/60">
                <div class="bg-black/80 border border-red-900/30 p-4 rounded-2xl">
                    <div class="flex items-center space-x-3">
                        <div class="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
                        <span class="text-xs font-black text-slate-200">CLUSTER ONLINE</span>
                    </div>
                    <p class="text-[10px] text-slate-400 mt-1">Status: 99.99% Uptime SLA</p>
                </div>
            </div>
        </aside>

        <!-- Main Workspace -->
        <div class="flex-1 flex flex-col overflow-y-auto">
            <header class="h-24 border-b border-red-950/60 bg-[#070303]/90 flex items-center justify-between px-8 backdrop-blur-md">
                <div class="flex items-center space-x-4">
                    <h1 class="text-xl font-black uppercase text-white tracking-wide" x-text="activeTab"></h1>
                </div>
                <div class="flex items-center space-x-4">
                    <button @click="activeTab = 'billing'" class="bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white px-5 py-2.5 rounded-xl font-black text-xs uppercase tracking-wider glow-red transition-all">
                        <i class="fa-solid fa-crown mr-2"></i> Upgrade Tier
                    </button>
                </div>
            </header>

            <main class="p-8 lg:p-12 max-w-7xl mx-auto w-full space-y-8">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="p-4 rounded-2xl border bg-red-500/10 border-red-500/30 text-red-300 text-sm font-semibold flex items-center space-x-3">
                                <i class="fa-solid fa-triangle-exclamation text-red-500"></i>
                                <span>{{ message }}</span>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}

                <!-- DASHBOARD TAB -->
                <div x-show="activeTab === 'dashboard'" class="space-y-8">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="glass-panel p-6 rounded-3xl glow-red">
                            <p class="text-xs font-black text-red-400 uppercase tracking-widest">Active Instances</p>
                            <h3 class="text-4xl font-black mt-2 text-white">{{ bots|length }}</h3>
                            <span class="text-[10px] text-slate-400 mt-1 block">Running 24/7 on Dedicated Core</span>
                        </div>
                        <div class="glass-panel p-6 rounded-3xl">
                            <p class="text-xs font-black text-slate-400 uppercase tracking-widest">Active Subscription</p>
                            <h3 class="text-2xl font-black mt-2 text-emerald-400">Enterprise Elite</h3>
                            <span class="text-[10px] text-slate-400 mt-1 block">Razorpay Live Secured</span>
                        </div>
                        <div class="glass-panel p-6 rounded-3xl">
                            <p class="text-xs font-black text-slate-400 uppercase tracking-widest">Cluster Storage</p>
                            <h3 class="text-2xl font-black mt-2 text-white">NVMe SSD</h3>
                            <span class="text-[10px] text-slate-400 mt-1 block">High-Speed File Mounts</span>
                        </div>
                    </div>

                    <div class="glass-panel rounded-3xl overflow-hidden p-6">
                        <div class="flex items-center justify-between pb-6 border-b border-red-950/60">
                            <h3 class="text-lg font-black uppercase text-white">Your Deployed Bot Instances</h3>
                            <button @click="activeTab = 'deploy'" class="bg-red-600/20 hover:bg-red-600/40 border border-red-500/40 text-red-400 px-4 py-2 rounded-xl text-xs font-bold transition-all">+ Deploy New Bot</button>
                        </div>
                        <div class="overflow-x-auto mt-4">
                            <table class="w-full text-left">
                                <thead>
                                    <tr class="text-slate-400 text-xs uppercase border-b border-red-950/60">
                                        <th class="py-4 px-4">Bot Name</th>
                                        <th class="py-4 px-4">Plan Tier</th>
                                        <th class="py-4 px-4">Status</th>
                                        <th class="py-4 px-4 text-right">Terminal & Management</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-red-950/40 text-sm">
                                    {% for bot in bots %}
                                    <tr>
                                        <td class="py-4 px-4 font-bold text-white flex items-center space-x-3">
                                            <div class="w-8 h-8 rounded-xl bg-red-950/50 border border-red-900/50 flex items-center justify-center text-red-400">
                                                <i class="fa-solid fa-robot text-xs"></i>
                                            </div>
                                            <span>{{ bot.name }}</span>
                                        </td>
                                        <td class="py-4 px-4"><span class="px-3 py-1 rounded-full text-xs font-black bg-red-950/40 border border-red-900/40 text-red-300">{{ bot.plan }}</span></td>
                                        <td class="py-4 px-4"><span class="px-3 py-1 rounded-full text-xs font-black bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{{ bot.status }}</span></td>
                                        <td class="py-4 px-4 text-right space-x-3">
                                            <button @click="fetchLogs({{ bot.id }})" class="px-3.5 py-2 bg-black border border-red-950 rounded-xl text-xs text-slate-300 hover:border-red-500 transition-all"><i class="fa-solid fa-terminal mr-1.5"></i> Logs</button>
                                            <a href="{{ url_for('control_bot', bot_id=bot.id, action='delete') }}" class="px-3.5 py-2 bg-black border border-red-950 rounded-xl text-xs text-rose-400 hover:border-rose-500 transition-all"><i class="fa-solid fa-trash mr-1.5"></i> Delete</a>
                                        </td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="4" class="py-8 text-center text-slate-500 font-semibold">No bot instances deployed yet. Click "Deploy Bot" to start hosting.</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Terminal Logs Box -->
                    <div x-show="selectedBotLog !== null" x-cloak class="glass-panel rounded-3xl p-6 space-y-4">
                        <div class="flex items-center justify-between">
                            <h4 class="font-black text-white text-base flex items-center space-x-2">
                                <i class="fa-solid fa-terminal text-red-500"></i>
                                <span>Live Kernel Subprocess Output</span>
                            </h4>
                            <button @click="selectedBotLog = null" class="text-slate-400 hover:text-white"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                        <pre x-text="logContent" class="bg-black/90 border border-red-950 p-5 rounded-2xl text-red-400 font-mono text-xs h-64 overflow-auto shadow-inner"></pre>
                    </div>
                </div>

                <!-- DEPLOY TAB -->
                <div x-show="activeTab === 'deploy'" class="max-w-xl mx-auto">
                    <div class="glass-panel rounded-3xl p-8 glow-red">
                        <div class="text-center space-y-2 mb-6">
                            <div class="w-14 h-14 rounded-2xl bg-red-600/20 border border-red-500/40 flex items-center justify-center text-red-400 mx-auto">
                                <i class="fa-solid fa-cloud-arrow-up text-2xl"></i>
                            </div>
                            <h2 class="text-2xl font-black text-white uppercase">Deploy Telegram Bot</h2>
                            <p class="text-xs text-slate-400">Upload your Python bot script (.py or .zip). Runs 24/7 on the cloud cluster.</p>
                        </div>
                        <form action="{{ url_for('upload_bot') }}" method="POST" enctype="multipart/form-data" class="space-y-5">
                            <div>
                                <label class="block text-xs font-black uppercase text-slate-400 mb-2">Bot Identification Name</label>
                                <input type="text" name="bot_name" required placeholder="e.g., CryptoVipBot" class="w-full bg-black/80 border border-red-950 rounded-2xl px-4 py-3.5 text-white text-sm focus:border-red-500 focus:outline-none transition-all">
                            </div>
                            <div>
                                <label class="block text-xs font-black uppercase text-slate-400 mb-2">Select Hosting Plan Tier</label>
                                <select name="bot_plan" class="w-full bg-black/80 border border-red-950 rounded-2xl px-4 py-3.5 text-white text-sm focus:border-red-500 focus:outline-none transition-all">
                                    <option value="Starter (₹49)">Starter Plan - ₹49 / Month</option>
                                    <option value="Pro Enterprise (₹199)">Pro Enterprise - ₹199 / Month</option>
                                    <option value="Ultimate Cluster (₹499)">Ultimate Cluster - ₹499 / Month</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-black uppercase text-slate-400 mb-2">Bot Script (.py or .zip)</label>
                                <input type="file" name="bot_file" accept=".py,.zip" required class="w-full bg-black/80 border border-red-950 rounded-2xl px-4 py-3 text-slate-400 text-sm file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-black file:bg-red-600 file:text-white hover:file:bg-red-500 transition-all">
                            </div>
                            <button type="submit" class="w-full bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-black py-4 rounded-2xl uppercase tracking-wider text-sm glow-red transition-all">Deploy Instance Now</button>
                        </form>
                    </div>
                </div>

                <!-- BILLING & PRICING TAB -->
                <div x-show="activeTab === 'billing'" class="space-y-8">
                    <div class="text-center max-w-2xl mx-auto space-y-3">
                        <span class="text-xs font-black uppercase text-red-500 tracking-widest">Razorpay Instant Checkout</span>
                        <h2 class="text-3xl font-black text-white uppercase">Choose Your Power Tier</h2>
                        <p class="text-sm text-slate-400">Upgrade your hosting cluster with premium dedicated resources, high-frequency CPU cycles, and priority uptime support.</p>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 pt-4">
                        <!-- Starter Plan -->
                        <div class="glass-panel rounded-3xl p-8 flex flex-col justify-between space-y-6">
                            <div class="space-y-4">
                                <span class="px-3 py-1 rounded-full text-[10px] font-black bg-red-950/60 text-red-400 border border-red-900/50 uppercase">Starter</span>
                                <h3 class="text-3xl font-black text-white">₹49 <span class="text-xs font-normal text-slate-400">/ month</span></h3>
                                <p class="text-xs text-slate-400">Perfect for running standard Telegram bots with lightweight background loops.</p>
                                <ul class="space-y-3 text-xs text-slate-300">
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> 1 Active Bot Instance</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> 24/7 Cloud Uptime</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Standard Terminal Logs</li>
                                </ul>
                            </div>
                            <button @click="payWithRazorpay('Starter Plan', 4900)" class="w-full bg-black border border-red-900/60 hover:bg-red-600 text-white font-black py-3.5 rounded-2xl text-xs uppercase tracking-wider transition-all">Select Starter</button>
                        </div>

                        <!-- Pro Enterprise -->
                        <div class="glass-panel rounded-3xl p-8 flex flex-col justify-between space-y-6 glow-red border-red-500/50 relative overflow-hidden">
                            <div class="absolute top-0 right-0 bg-red-600 text-white text-[9px] font-black px-4 py-1 rounded-bl-xl uppercase tracking-widest">Most Popular</div>
                            <div class="space-y-4">
                                <span class="px-3 py-1 rounded-full text-[10px] font-black bg-red-950/60 text-red-400 border border-red-900/50 uppercase">Pro Enterprise</span>
                                <h3 class="text-3xl font-black text-white">₹199 <span class="text-xs font-normal text-slate-400">/ month</span></h3>
                                <p class="text-xs text-slate-400">Designed for high-traffic bots, automated trading engines, and group managers.</p>
                                <ul class="space-y-3 text-xs text-slate-300">
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Up to 5 Active Instances</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Priority CPU Allocation</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Live Real-Time Logs</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Auto-Restart on Crash</li>
                                </ul>
                            </div>
                            <button @click="payWithRazorpay('Pro Enterprise', 19900)" class="w-full bg-red-600 hover:bg-red-500 text-white font-black py-3.5 rounded-2xl text-xs uppercase tracking-wider transition-all shadow-lg shadow-red-600/40">Select Pro</button>
                        </div>

                        <!-- Ultimate Cluster -->
                        <div class="glass-panel rounded-3xl p-8 flex flex-col justify-between space-y-6">
                            <div class="space-y-4">
                                <span class="px-3 py-1 rounded-full text-[10px] font-black bg-red-950/60 text-red-400 border border-red-900/50 uppercase">Ultimate Cluster</span>
                                <h3 class="text-3xl font-black text-white">₹499 <span class="text-xs font-normal text-slate-400">/ month</span></h3>
                                <p class="text-xs text-slate-400">Full dedicated resource pooling for developers managing multiple enterprise bot networks.</p>
                                <ul class="space-y-3 text-xs text-slate-300">
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Unlimited Bot Instances</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Dedicated RAM & Core</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> VIP Telegram Support</li>
                                    <li><i class="fa-solid fa-check text-red-500 mr-2"></i> Instant Failover Node</li>
                                </ul>
                            </div>
                            <button @click="payWithRazorpay('Ultimate Cluster', 49900)" class="w-full bg-black border border-red-900/60 hover:bg-red-600 text-white font-black py-3.5 rounded-2xl text-xs uppercase tracking-wider transition-all">Select Ultimate</button>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    bots = BotInstance.query.all()
    return render_template_string(DASHBOARD_TEMPLATE, bots=bots)

@app.route('/create-order', methods=['POST'])
def create_order():
    data = request.get_json()
    plan_name = data.get('plan', 'Starter Plan')
    amount = data.get('amount', 4900)

    order_data = {
        'amount': amount,
        'currency': 'INR',
        'payment_capture': 1
    }
    try:
        order = razorpay_client.order.create(data=order_data)
        new_tx = Transaction(order_id=order['id'], plan_name=plan_name, amount=amount, status="Created")
        db.session.add(new_tx)
        db.session.commit()

        return jsonify({
            'order_id': order['id'],
            'amount': amount,
            'key_id': RAZORPAY_KEY_ID
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/payment-success', methods=['POST'])
def payment_success():
    data = request.get_json()
    payment_id = data.get('payment_id')
    order_id = data.get('order_id')
    plan_name = data.get('plan')

    tx = Transaction.query.filter_by(order_id=order_id).first()
    if tx:
        tx.payment_id = payment_id
        tx.status = "Success"
        db.session.commit()
        flash(f'Successfully upgraded to {plan_name} via Razorpay Live!', 'success')
    return jsonify({'status': 'success'})

@app.route('/upload', methods=['POST'])
def upload_bot():
    bot_name = request.form.get('bot_name')
    bot_plan = request.form.get('bot_plan', 'Starter (₹49)')
    file = request.files.get('bot_file')

    if not file or file.filename == '':
        flash('Please select a valid Python or ZIP file.', 'error')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    token_match = re.search(r'\d{9,10}:[A-Za-z0-9_-]{35}', content)
    bot_token = token_match.group(0) if token_match else "mock_token_12345"

    new_bot = BotInstance(name=bot_name, filename=filename, filepath=filepath, token=bot_token, plan=bot_plan)
    db.session.add(new_bot)
    db.session.commit()
    start_bot_process(new_bot)
    flash(f'Bot "{bot_name}" successfully deployed and running 24/7!', 'success')
    return redirect(url_for('index'))

@app.route('/bot/<int:bot_id>/logs')
def get_bot_logs(bot_id):
    return jsonify({"logs": BOT_LOGS.get(bot_id, ["No logs available yet."])})

@app.route('/bot/<int:bot_id>/<action>')
def control_bot(bot_id, action):
    bot = BotInstance.query.get_or_404(bot_id)
    if action == 'delete':
        if bot.id in ACTIVE_PROCESSES:
            try:
                ACTIVE_PROCESSES[bot.id].terminate()
            except:
                pass
        db.session.delete(bot)
        db.session.commit()
        flash('Bot instance deleted successfully.', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
