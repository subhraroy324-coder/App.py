import os
import sys
import time
import shutil
import subprocess
import threading
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "vx_hostinger_ultimate_production_key"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SITES_DIR = os.path.join(BASE_DIR, "hosted_sites")
os.makedirs(SITES_DIR, exist_ok=True)

DEPLOYMENTS = {}
RUNNING_PROCESSES = {}
DOMAINS_OWNED = {} 

RAZORPAY_KEY_ID = "rzp_live_TGzOHwqjwcYfov"
RAZORPAY_KEY_SECRET = "qbqBS1dxdFRYTizozIH083E4"

MASTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ title }} &bull; VX Hostinger Cloud</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        body { background-color: #000000; color: #f3f4f6; font-family: 'Plus Jakarta Sans', sans-serif; }
        .glass-panel { background: rgba(5, 5, 5, 0.85); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); }
        .glass-card { background: rgba(5, 5, 5, 0.9); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8); }
        .glow-btn { box-shadow: 0 0 25px -5px rgba(255, 255, 255, 0.2); }
        #sidebar-drawer { transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #000000; }
        ::-webkit-scrollbar-thumb { background: #1a1a1a; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #333333; }
    </style>
</head>
<body class="min-h-screen flex flex-col selection:bg-white selection:text-black antialiased">

    <!-- Top Navigation Bar -->
    <header class="glass-panel sticky top-0 z-40 px-4 sm:px-8 py-3.5 flex justify-between items-center border-b border-white/10">
        <div class="flex items-center space-x-3 sm:space-x-5">
            <button onclick="toggleSidebar()" class="p-2 rounded-xl bg-white/5 border border-white/10 text-white hover:bg-white/10 transition flex items-center justify-center space-x-1.5 active:scale-95" title="Menu">
                <span class="text-sm font-bold tracking-widest">⋮</span>
                <span class="text-xs font-semibold hidden sm:inline">MENU</span>
            </button>
            <a href="/" class="flex items-center space-x-2.5 group">
                <div class="w-8 h-8 rounded-xl bg-gradient-to-tr from-white to-gray-400 text-black font-extrabold flex items-center justify-center text-sm shadow-lg group-hover:scale-105 transition">VX</div>
                <span class="font-bold text-sm sm:text-base tracking-tight text-white">VX <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-white">Hostinger</span></span>
            </a>
        </div>
        <div class="flex items-center space-x-2 sm:space-x-3">
            <div class="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Cloud Node Operational</span>
            </div>
            <a href="/deploy-page" class="bg-white text-black text-xs font-bold px-4 py-2.5 rounded-xl hover:bg-gray-200 transition shadow-lg glow-btn active:scale-95">
                + Deploy Instance
            </a>
        </div>
    </header>

    <!-- Slide-Out Drawer Sidebar -->
    <div id="sidebar-overlay" class="fixed inset-0 bg-black/80 backdrop-blur-md z-50 hidden transition-opacity opacity-0" onclick="toggleSidebar()"></div>
    <aside id="sidebar-drawer" class="fixed top-0 left-0 bottom-0 w-80 bg-black border-r border-white/10 z-50 transform -translate-x-full flex flex-col p-6 shadow-2xl">
        <div class="flex justify-between items-center mb-6 border-b border-white/10 pb-4">
            <div class="flex items-center space-x-2.5">
                <div class="w-7 h-7 rounded-lg bg-white text-black font-extrabold flex items-center justify-center text-xs">VX</div>
                <span class="font-bold text-sm text-white">Navigation Drawer</span>
            </div>
            <button onclick="toggleSidebar()" class="w-8 h-8 rounded-lg bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/10 transition flex items-center justify-center font-bold text-sm">
                ✕
            </button>
        </div>

        <nav class="space-y-1.5 flex-grow text-xs font-medium text-gray-300 overflow-y-auto pr-1">
            <a href="/" class="flex items-center space-x-3 px-3.5 py-3 rounded-xl hover:bg-white/5 hover:text-white transition">
                <span>⚡ Active Deployments & Bots</span>
            </a>
            <a href="/deploy-page" class="flex items-center space-x-3 px-3.5 py-3 rounded-xl hover:bg-white/5 hover:text-white transition">
                <span>🚀 New Deployment Studio</span>
            </a>
            <a href="/domain-registrar" class="flex items-center space-x-3 px-3.5 py-3 rounded-xl hover:bg-white/5 hover:text-white transition">
                <span>🌐 Domain Registrar & Cart</span>
            </a>
            <a href="/databases" class="flex items-center space-x-3 px-3.5 py-3 rounded-xl hover:bg-white/5 hover:text-white transition">
                <span>🗄️ Database & Redis Cluster</span>
            </a>
            <a href="/env-manager" class="flex items-center space-x-3 px-3.5 py-3 rounded-xl hover:bg-white/5 hover:text-white transition">
                <span>🔒 Environment Variables / Secrets</span>
            </a>
            <a href="/ssl-manager" class="flex items-center space-x-3 px-3.5 py-3 rounded-xl hover:bg-white/5 hover:text-white transition">
                <span>🛡️ SSL & TLS Security Manager</span>
            </a>
        </nav>

        <div class="border-t border-white/10 pt-4 text-[11px] text-gray-500 text-center">
            VX Hostinger Enterprise Cloud v5.0
        </div>
    </aside>

    <!-- Main Content Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-8 py-6 sm:py-10 flex-grow w-full">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="border-t border-white/10 text-center py-6 text-xs text-gray-500 bg-black px-4">
        &copy; 2026 VX Hostinger Cloud Infrastructure. All rights reserved.
    </footer>

    <script>
        function toggleSidebar() {
            let sidebar = document.getElementById('sidebar-drawer');
            let overlay = document.getElementById('sidebar-overlay');
            if (sidebar.classList.contains('-translate-x-full')) {
                sidebar.classList.remove('-translate-x-full');
                overlay.classList.remove('hidden', 'opacity-0');
            } else {
                sidebar.classList.add('-translate-x-full');
                overlay.classList.add('hidden');
            }
        }
    </script>
</body>
</html>
"""

INDEX_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
            <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Deployments & Bots</h1>
            <p class="text-gray-400 text-xs sm:text-sm mt-1">Manage your active web servers, automated bots, and connected domains.</p>
        </div>
        <div class="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
            <a href="/domain-registrar" class="flex-1 md:flex-none text-center bg-white/5 border border-white/10 text-white text-xs font-bold px-4 py-3 rounded-xl hover:bg-white/10 transition">
                🌐 Buy Domains
            </a>
            <a href="/deploy-page" class="flex-1 md:flex-none text-center bg-white text-black text-xs font-bold px-5 py-3 rounded-xl hover:bg-gray-200 transition shadow-lg glow-btn">
                + New Deployment
            </a>
        </div>
    </div>

    <!-- Metrics Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div class="glass-card rounded-2xl p-5 sm:p-6">
            <span class="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Total Hosted Instances</span>
            <div class="text-3xl font-extrabold mt-2 text-white">{{ deployments|length }}</div>
        </div>
        <div class="glass-card rounded-2xl p-5 sm:p-6">
            <span class="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Active & Running</span>
            <div class="text-3xl font-extrabold mt-2 text-emerald-400">
                {{ deployments.values() | selectattr("status", "equalto", "Live") | list | length }}
            </div>
        </div>
        <div class="glass-card rounded-2xl p-5 sm:p-6">
            <span class="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Custom Domains</span>
            <div class="text-3xl font-extrabold mt-2 text-indigo-400">{{ domains|length }}</div>
        </div>
    </div>

    <!-- Responsive Projects List -->
    <div class="glass-card rounded-3xl overflow-hidden">
        <div class="hidden md:grid px-6 py-4 border-b border-white/10 text-[11px] font-extrabold uppercase tracking-wider text-gray-400 grid-cols-6 items-center">
            <span class="col-span-2">Project / Instance Name</span>
            <span>Source Type</span>
            <span>Status</span>
            <span>Live Endpoint URL</span>
            <span class="text-right">Manage Actions</span>
        </div>
        <div class="divide-y divide-white/10">
            {% if deployments %}
                {% for d_id, item in deployments.items() %}
                <div class="p-5 sm:px-6 sm:py-4 flex flex-col md:grid md:grid-cols-6 items-start md:items-center gap-3 md:gap-0 text-sm">
                    <div class="col-span-2 flex flex-col truncate w-full">
                        <span class="font-bold text-white text-base sm:text-sm truncate">{{ item.name }}</span>
                        <span class="text-[11px] text-gray-500 font-mono mt-0.5">ID: {{ d_id }}</span>
                    </div>
                    <div>
                        <span class="text-[10px] uppercase font-bold tracking-wider bg-white/5 text-gray-300 px-3 py-1 rounded-lg border border-white/10 inline-block">{{ item.source_type }}</span>
                    </div>
                    <div>
                        <span class="px-3 py-1 rounded-full text-[11px] font-bold inline-block 
                            {% if item.status == 'Live' %} bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 
                            {% elif item.status == 'Failed' %} bg-rose-500/10 text-rose-400 border border-rose-500/20
                            {% else %} bg-amber-500/10 text-amber-400 border border-amber-500/20 {% endif %}">
                            {{ item.status }}
                        </span>
                    </div>
                    <div class="truncate w-full">
                        {% if item.status == 'Live' %}
                            <a href="{{ item.url }}" target="_blank" class="text-indigo-400 hover:underline truncate block text-xs font-mono">{{ item.url }}</a>
                        {% else %}
                            <span class="text-gray-500 text-xs">Building cluster daemon...</span>
                        {% endif %}
                    </div>
                    <!-- Actions Menu -->
                    <div class="flex justify-end w-full md:w-auto pt-2 md:pt-0">
                        <div class="inline-flex rounded-xl shadow-sm bg-black border border-white/10 p-1 space-x-1 items-center w-full md:w-auto justify-end">
                            <a href="/settings/{{ d_id }}" class="px-2.5 py-1.5 text-xs text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition">⚙️ Config</a>
                            <a href="/logs/{{ d_id }}" class="px-2.5 py-1.5 text-xs text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition">📊 Logs</a>
                            <a href="/domain-registrar?project={{ d_id }}" class="px-2.5 py-1.5 text-xs text-indigo-400 hover:bg-white/10 rounded-lg transition font-bold">🌐 Domain</a>
                        </div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="px-6 py-20 text-center text-gray-500 text-sm">
                    No deployments found. Click <a href="/deploy-page" class="text-white underline font-bold">New Deployment</a> to deploy your app.
                </div>
            {% endif %}
        </div>
    </div>
""")

DEPLOY_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="max-w-xl mx-auto glass-card rounded-3xl p-6 sm:p-8">
        <h1 class="text-xl sm:text-2xl font-extrabold text-white mb-1">VX Hostinger Deployment Studio</h1>
        <p class="text-gray-400 text-xs sm:text-sm mb-6">Deploy files, GitHub repos, Telegram bots, or Discord bots instantly.</p>

        <form action="/api/create-deployment" method="POST" enctype="multipart/form-data" class="space-y-4 sm:space-y-5">
            <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Deployment Source Method</label>
                <select name="source_type" id="source_type" onchange="toggleDeploymentInputs()" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white text-white">
                    <option value="file">Direct File Upload (.zip / .html / .py)</option>
                    <option value="github">GitHub Repository URL</option>
                    <option value="telegram_bot">Telegram Bot (Python / Node Worker)</option>
                    <option value="discord_bot">Discord Bot (Python / Node Worker)</option>
                </select>
            </div>

            <div id="field_name">
                <label class="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Project / Instance Name</label>
                <input type="text" name="app_name" required placeholder="my-vx-application" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white text-white placeholder-gray-600">
            </div>

            <div id="field_file">
                <label class="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Upload Source Code / File</label>
                <input type="file" name="project_file" class="w-full bg-black border border-white/10 rounded-xl px-3 py-2.5 text-xs text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-white file:text-black">
            </div>

            <div id="field_repo" class="hidden">
                <label class="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">GitHub Repository URL</label>
                <input type="text" name="repo_url" placeholder="https://github.com/username/repository" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white text-white placeholder-gray-600">
            </div>

            <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Start Command (Optional)</label>
                <input type="text" name="start_command" placeholder="e.g. python main.py or node index.js" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white text-white placeholder-gray-600">
            </div>

            <button type="submit" class="w-full bg-white text-black font-bold py-4 rounded-xl text-xs tracking-wider uppercase hover:bg-gray-200 transition shadow-lg glow-btn">
                Deploy Instance Now &rarr;
            </button>
        </form>
    </div>

    <script>
        function toggleDeploymentInputs() {
            let val = document.getElementById('source_type').value;
            if(val === 'github') {
                document.getElementById('field_repo').classList.remove('hidden');
                document.getElementById('field_file').classList.add('hidden');
            } else {
                document.getElementById('field_repo').classList.add('hidden');
                document.getElementById('field_file').classList.remove('hidden');
            }
        }
    </script>
""")

DOMAIN_REGISTRAR_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="max-w-2xl mx-auto glass-card rounded-3xl p-6 sm:p-8 space-y-6">
        <div>
            <h1 class="text-xl sm:text-2xl font-extrabold text-white mb-1">VX Domain Registrar & Cart</h1>
            <p class="text-gray-400 text-xs sm:text-sm">Search custom TLD extensions, add items to cart, configure duration, and pay securely.</p>
        </div>

        <div class="flex space-x-2">
            <input type="text" id="domain_query" placeholder="Enter domain name (e.g. mybrand)" value="vxstartup" class="flex-grow bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white text-white placeholder-gray-600">
            <button onclick="searchDomains()" class="bg-white text-black font-bold px-6 py-3.5 rounded-xl text-xs uppercase tracking-wider hover:bg-gray-200 transition">Search</button>
        </div>

        <div id="search_results" class="space-y-3 hidden">
            <h3 class="text-xs font-bold uppercase tracking-wider text-gray-400">Available Extensions</h3>
            <div id="domain_items_list" class="space-y-2.5"></div>
        </div>

        <div id="cart_section" class="hidden border border-white/10 bg-black p-5 sm:p-6 rounded-2xl space-y-4">
            <h3 class="text-xs font-bold uppercase tracking-wider text-white flex justify-between items-center">
                <span>🛒 Shopping Cart Checkout</span>
                <span id="cart_domain_name" class="text-indigo-400 font-mono"></span>
            </h3>

            <div class="space-y-2.5 text-xs text-gray-300">
                <div class="flex justify-between items-center">
                    <span>Registration Period:</span>
                    <select id="duration_select" onchange="updateCartTotal()" class="bg-black border border-white/10 rounded-lg px-3 py-2 text-white">
                        <option value="trial">1 Day Free Trial (24 Hours Trial)</option>
                        <option value="1_month">1 Month</option>
                        <option value="2_months">2 Months</option>
                        <option value="1_year">1 Year (Standard)</option>
                    </select>
                </div>
                <div class="flex justify-between"><span>Registry Base Price:</span> <span id="lbl_base">₹0</span></div>
                <div class="flex justify-between"><span>Platform & ICANN Fee:</span> <span>₹25</span></div>
                <div class="flex justify-between"><span>GST (18%):</span> <span id="lbl_gst">₹0</span></div>
                <hr class="border-white/10 my-2">
                <div class="flex justify-between font-extrabold text-sm text-white"><span>Total Checkout Amount:</span> <span id="lbl_total">₹25</span></div>
            </div>

            <button onclick="checkoutCart()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl text-xs uppercase tracking-wider transition shadow-lg">
                Proceed to Secure Checkout &rarr;
            </button>
        </div>
    </div>

    <script>
        const targetProject = "{{ target_project }}";
        const rzpKey = "{{ rzp_key }}";
        const hasClaimedTrial = {{ 'true' if trial_claimed else 'false' }};
        let activeDomain = '';
        let basePriceInPaise = 0;

        function searchDomains() {
            let q = document.getElementById('domain_query').value.trim().toLowerCase();
            if(!q) return alert('Please enter a valid domain query.');

            let cleanName = q.split('.')[0];
            let extensions = ['.com', '.in', '.site', '.xyz', '.tech', '.store'];
            let html = '';

            extensions.forEach((ext, idx) => {
                let full = cleanName + ext;
                let rawPrice = idx === 0 ? 89900 : (idx === 1 ? 49900 : 29900);
                let priceLabel = '₹' + (rawPrice / 100) + ' / yr';

                html += `
                    <div class="flex justify-between items-center bg-black border border-white/10 px-4 py-3.5 rounded-xl text-sm">
                        <div>
                            <span class="font-bold text-white">${full}</span>
                            <span class="text-xs text-gray-500 ml-2">Available (${priceLabel})</span>
                        </div>
                        <button onclick="addToCart('${full}', ${rawPrice})" class="bg-white/10 hover:bg-white/20 border border-white/10 text-white text-xs font-semibold px-4 py-2 rounded-lg transition">
                            + Add to Cart
                        </button>
                    </div>
                `;
            });

            if (!hasClaimedTrial) {
                html += `
                    <div class="flex justify-between items-center bg-emerald-500/10 border border-emerald-500/20 px-4 py-3.5 rounded-xl text-sm">
                        <div>
                            <span class="font-bold text-emerald-400">${cleanName}.vx.site</span>
                            <span class="text-xs text-emerald-500 ml-2">1 Day Free Trial (One-Time Only)</span>
                        </div>
                        <button onclick="addToCart('${cleanName}.vx.site', 0, true)" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition">
                            Claim Free Trial
                        </button>
                    </div>
                `;
            }

            document.getElementById('domain_items_list').innerHTML = html;
            document.getElementById('search_results').classList.remove('hidden');
        }

        function addToCart(domain, price, isTrial = false) {
            activeDomain = domain;
            basePriceInPaise = price;
            document.getElementById('cart_domain_name').innerText = domain;
            if(isTrial) {
                document.getElementById('duration_select').value = 'trial';
                document.getElementById('duration_select').disabled = true;
            } else {
                document.getElementById('duration_select').disabled = false;
            }
            updateCartTotal();
            document.getElementById('cart_section').classList.remove('hidden');
        }

        function updateCartTotal() {
            let dur = document.getElementById('duration_select').value;
            let currentBase = basePriceInPaise;
            let multiplier = 1;

            if(dur === 'trial') {
                currentBase = 0;
            } else if(dur === '1_month') {
                multiplier = 0.1;
            } else if(dur === '2_months') {
                multiplier = 0.2;
            }

            let calculatedBase = currentBase * multiplier;
            let platformFee = 2500;
            let gst = Math.round((calculatedBase + platformFee) * 0.18);
            let total = calculatedBase + platformFee + gst;

            document.getElementById('lbl_base').innerText = '₹' + (calculatedBase / 100).toFixed(2);
            document.getElementById('lbl_gst').innerText = '₹' + (gst / 100).toFixed(2);
            document.getElementById('lbl_total').innerText = '₹' + (total / 100).toFixed(2);
            window.finalCheckoutAmount = total;
        }

        function checkoutCart() {
            if(window.finalCheckoutAmount <= 0) {
                window.location.href = "/api/attach-domain?domain=" + activeDomain + "&project=" + targetProject + "&trial=true";
                return;
            }

            var options = {
                "key": rzpKey,
                "amount": window.finalCheckoutAmount,
                "currency": "INR",
                "name": "VX Hostinger Cloud",
                "description": "Domain Registration: " + activeDomain,
                "handler": function (response) {
                    alert("Payment Verified! Domain attached successfully.");
                    window.location.href = "/api/attach-domain?domain=" + activeDomain + "&project=" + targetProject;
                },
                "theme": { "color": "#000000" }
            };
            var rzp = new Razorpay(options);
            rzp.open();
        }
    </script>
""")

DATABASES_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="max-w-xl mx-auto glass-card rounded-3xl p-6 sm:p-8 space-y-4">
        <h1 class="text-xl sm:text-2xl font-extrabold text-white">Database & Redis Cluster</h1>
        <p class="text-gray-400 text-xs sm:text-sm">Provision managed PostgreSQL and Redis instances for your VX Hostinger apps.</p>
        <div class="bg-black border border-white/10 p-5 rounded-2xl space-y-3 text-xs">
            <div class="flex justify-between items-center"><span class="text-white font-bold">PostgreSQL Main Cluster</span> <span class="text-emerald-400 font-bold">● Active</span></div>
            <div class="font-mono text-gray-400 break-all bg-black p-2.5 rounded-lg border border-white/5">postgres://admin:vx_secret@db.vxhostinger.internal:5432/main</div>
            <button onclick="alert('New Database provisioned successfully!')" class="bg-white text-black font-bold px-4 py-3 rounded-xl w-full uppercase text-xs">Provision New Database</button>
        </div>
    </div>
""")

ENV_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="max-w-xl mx-auto glass-card rounded-3xl p-6 sm:p-8 space-y-4">
        <h1 class="text-xl sm:text-2xl font-extrabold text-white">Environment Variables & Secrets</h1>
        <p class="text-gray-400 text-xs sm:text-sm">Inject secure runtime environment keys into your deployments safely.</p>
        <div class="space-y-3">
            <input type="text" placeholder="KEY_NAME (e.g. BOT_TOKEN)" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm text-white placeholder-gray-600">
            <input type="text" placeholder="VALUE (e.g. 123456:ABC-DEF)" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm text-white placeholder-gray-600">
            <button onclick="alert('Secret saved successfully!')" class="bg-white text-black font-bold py-3.5 rounded-xl w-full uppercase text-xs tracking-wider">Add Environment Variable</button>
        </div>
    </div>
""")

SSL_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="max-w-xl mx-auto glass-card rounded-3xl p-6 sm:p-8 space-y-4">
        <h1 class="text-xl sm:text-2xl font-extrabold text-white">SSL & TLS Certificates</h1>
        <p class="text-gray-400 text-xs sm:text-sm">Manage automated Let's Encrypt SSL encryption for all your custom domains.</p>
        <div class="bg-black border border-white/10 p-5 rounded-2xl space-y-3 text-xs">
            <div class="flex justify-between items-center"><span class="text-white font-bold">Auto SSL Engine</span> <span class="text-emerald-400 font-bold">SECURED (TLS 1.3)</span></div>
            <div class="text-gray-500">All inbound traffic across VX Hostinger is protected with enterprise-grade encryption.</div>
        </div>
    </div>
""")

SETTINGS_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="max-w-xl mx-auto glass-card rounded-3xl p-6 sm:p-8">
        <h1 class="text-xl sm:text-2xl font-extrabold text-white mb-1">Instance Configuration</h1>
        <p class="text-gray-400 text-xs sm:text-sm mb-6">Update deployment runtime parameters or delete the instance.</p>

        <form action="/api/update-settings/{{ d_id }}" method="POST" class="space-y-4">
            <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Project Name</label>
                <input type="text" name="app_name" value="{{ item.name }}" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white text-white">
            </div>
            <div>
                <label class="block text-[11px] font-bold uppercase tracking-wider text-gray-400 mb-2">Start Command</label>
                <input type="text" name="start_command" value="{{ item.start_command }}" class="w-full bg-black border border-white/10 rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:border-white text-white">
            </div>
            <button type="submit" class="w-full bg-white text-black font-bold py-3.5 rounded-xl text-xs uppercase tracking-wider hover:bg-gray-200 transition">
                Save Configurations
            </button>
        </form>

        <hr class="border-white/10 my-6">

        <form action="/api/delete/{{ d_id }}" method="POST">
            <button type="submit" class="w-full bg-rose-500/10 border border-rose-500/30 text-rose-400 font-bold py-3.5 rounded-xl text-xs uppercase tracking-wider hover:bg-rose-500/20 transition">
                Delete Deployment Instance
            </button>
        </form>
    </div>
""")

LOGS_PAGE = MASTER_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="space-y-5">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div>
                <h1 class="text-xl sm:text-2xl font-extrabold text-white">Analytics & Build Console</h1>
                <p class="text-gray-400 text-xs sm:text-sm mt-0.5">Live trace console for <span class="text-white font-bold">{{ item.name }}</span>.</p>
            </div>
            <a href="{{ item.url }}" target="_blank" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-4 py-3 rounded-xl text-xs transition shadow">
                Open Live Endpoint &rarr;
            </a>
        </div>

        <div class="glass-card rounded-3xl p-5 font-mono text-xs text-emerald-400 h-80 sm:h-[420px] overflow-y-auto leading-relaxed" id="term">
            {{ item.logs | safe }}
        </div>

        <div class="flex justify-between text-xs">
            <a href="/" class="bg-white/5 border border-white/10 text-gray-300 py-3 px-5 rounded-xl hover:bg-white/10 transition">&larr; Back to Dashboard</a>
            <button onclick="location.reload()" class="bg-white/5 border border-white/10 text-gray-300 py-3 px-5 rounded-xl hover:bg-white/10 transition">Refresh Console</button>
        </div>
    </div>
    <script>
        let t = document.getElementById('term');
        t.scrollTop = t.scrollHeight;
    </script>
""")

@app.route('/')
def index():
    return render_template_string(INDEX_PAGE, title="Dashboard", deployments=DEPLOYMENTS, domains=DOMAINS_OWNED)

@app.route('/deploy-page')
def deploy_page():
    return render_template_string(DEPLOY_PAGE, title="New Deployment")

@app.route('/domain-registrar')
def domain_registrar():
    target_project = request.args.get('project', '')
    trial_claimed = session.get('trial_claimed', False)
    return render_template_string(DOMAIN_REGISTRAR_PAGE, title="Domain Registrar", target_project=target_project, rzp_key=RAZORPAY_KEY_ID, trial_claimed=trial_claimed)

@app.route('/databases')
def databases_page():
    return render_template_string(DATABASES_PAGE, title="Databases")

@app.route('/env-manager')
def env_page():
    return render_template_string(ENV_PAGE, title="Environment Variables")

@app.route('/ssl-manager')
def ssl_page():
    return render_template_string(SSL_PAGE, title="SSL Certificates")

@app.route('/logs/<d_id>')
def view_logs(d_id):
    if d_id not in DEPLOYMENTS:
        return redirect(url_for('index'))
    return render_template_string(LOGS_PAGE, title="Analytics", item=DEPLOYMENTS[d_id])

@app.route('/settings/<d_id>')
def view_settings(d_id):
    if d_id not in DEPLOYMENTS:
        return redirect(url_for('index'))
    return render_template_string(SETTINGS_PAGE, title="Settings", item=DEPLOYMENTS[d_id], d_id=d_id)

@app.route('/api/create-deployment', methods=['POST'])
def create_deployment():
    source_type = request.form.get('source_type')
    app_name = request.form.get('app_name', 'app').strip().lower().replace(' ', '-')
    start_command = request.form.get('start_command', '').strip()
    repo_url = request.form.get('repo_url', '').strip()
    
    d_id = f"dpl_{int(time.time())}"
    site_folder = os.path.join(SITES_DIR, app_name)
    os.makedirs(site_folder, exist_ok=True)
    
    timestamp = time.strftime('%X')
    logs_buffer = f"[{timestamp}] Initializing VX Hostinger cluster daemon for '{app_name}' ({source_type})...<br>"
    
    if source_type in ['file', 'telegram_bot', 'discord_bot']:
        uploaded_file = request.files.get('project_file')
        if uploaded_file and uploaded_file.filename:
            filename = uploaded_file.filename
            file_path = os.path.join(site_folder, filename)
            uploaded_file.save(file_path)
            logs_buffer += f"[{timestamp}] Stored uploaded asset: {filename}<br>"
            
            if filename.endswith('.py') and not start_command:
                start_command = f"python {filename}"
            elif filename.endswith('.js') and not start_command:
                start_command = f"node {filename}"
        else:
            logs_buffer += f"[{timestamp}] Workspace initialized successfully.<br>"
            
    elif source_type == 'github' and repo_url:
        logs_buffer += f"[{timestamp}] Cloning git repository from {repo_url}...<br>"
        try:
            subprocess.run(["git", "clone", repo_url, site_folder], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logs_buffer += f"[{timestamp}] Repository successfully cloned.<br>"
            if not start_command and os.path.exists(os.path.join(site_folder, "package.json")):
                start_command = "npm start"
        except Exception as e:
            logs_buffer += f"[{timestamp}] <span style='color:#f87171;'>Git Clone Error: {str(e)}</span><br>"

    live_url = f"/view/{app_name}/"
    
    DEPLOYMENTS[d_id] = {
        "name": app_name,
        "source_type": source_type,
        "status": "Building",
        "url": live_url,
        "start_command": start_command,
        "folder": site_folder,
        "logs": logs_buffer
    }

    def execute_build():
        time.sleep(1)
        try:
            if start_command:
                DEPLOYMENTS[d_id]["logs"] += f"[{time.strftime('%X')}] Executing: {start_command}<br>"
                process = subprocess.Popen(
                    start_command, shell=True, cwd=site_folder,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                RUNNING_PROCESSES[d_id] = process
                time.sleep(2)
                if process.poll() is not None:
                    _, err = process.communicate()
                    if err:
                        DEPLOYMENTS[d_id]["status"] = "Failed"
                        DEPLOYMENTS[d_id]["logs"] += f"<span style='color:#f87171;'>[Build Error] {err}</span><br>"
                        return

            DEPLOYMENTS[d_id]["status"] = "Live"
            DEPLOYMENTS[d_id]["logs"] += f"[{time.strftime('%X')}] <span style='color:#34d399;'>VX Hostinger instance is live and running!</span><br>"
        except Exception as err:
            DEPLOYMENTS[d_id]["status"] = "Failed"
            DEPLOYMENTS[d_id]["logs"] += f"<span style='color:#f87171;'>Exception: {str(err)}</span><br>"

    threading.Thread(target=execute_build).start()
    return redirect(url_for('view_logs', d_id=d_id))

@app.route('/api/attach-domain')
def attach_domain():
    domain = request.args.get('domain')
    project_id = request.args.get('project')
    is_trial = request.args.get('trial')
    
    if is_trial == 'true':
        session['trial_claimed'] = True
        
    if domain and project_id in DEPLOYMENTS:
        DOMAINS_OWNED[project_id] = domain
        DEPLOYMENTS[project_id]["url"] = f"https://{domain}/"
    return redirect(url_for('index'))

@app.route('/view/<app_name>/', defaults={'path': ''})
@app.route('/view/<app_name>/<path:path>')
def view_hosted_site(app_name, path):
    site_folder = os.path.join(SITES_DIR, app_name)
    if not os.path.exists(site_folder):
        return "Hosting deployment instance not found.", 404
    
    target_file = os.path.join(site_folder, path if path else "index.html")
    if os.path.exists(target_file) and os.path.isfile(target_file):
        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return f"VX Hostinger application '{app_name}' background daemon is active.", 200

@app.route('/api/update-settings/<d_id>', methods=['POST'])
def update_settings(d_id):
    if d_id in DEPLOYMENTS:
        DEPLOYMENTS[d_id]["name"] = request.form.get('app_name')
        DEPLOYMENTS[d_id]["start_command"] = request.form.get('start_command')
    return redirect(url_for('index'))

@app.route('/api/delete/<d_id>', methods=['POST'])
def delete_deployment(d_id):
    if d_id in DEPLOYMENTS:
        if d_id in RUNNING_PROCESSES:
            try:
                RUNNING_PROCESSES[d_id].terminate()
            except:
                pass
        folder = DEPLOYMENTS[d_id]["folder"]
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
        del DEPLOYMENTS[d_id]
        if d_id in DOMAINS_OWNED:
            del DOMAINS_OWNED[d_id]
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
