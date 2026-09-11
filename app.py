# app.py - Sukuna Bomber for Vercel
import os
import json
import requests
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

app = Flask(__name__)

# Configuration
SETTINGS_FILE = 'settings.json'
API_BASE_URL = "https://ft-osint-api.duckdns.org/api/bomber"

# Default settings
DEFAULT_SETTINGS = {
    "api_key": "explorer16",
    "default_count": 20,
    "owner_name": "Your Name Here",
    "profile_image": "https://via.placeholder.com/300x300/000000/00ff00?text=Upload+Image",
    "main_bg": "", 
    "sidebar_bg": "",
    "audio_url": "",  
    "phone": "+1234567890",
    "telegram": "username",
    "whatsapp": "1234567890"
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in data:
                        data[key] = value
                return data
        except:
            return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
    except:
        # Vercel read-only fallback
        pass

# ----------------------------------------------------------------------
# HTML TEMPLATES (Embedded)
# ----------------------------------------------------------------------

# --- MAIN USER INTERFACE ---
MAIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sukuna Bomber @{{ owner_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Share Tech Mono', monospace; }
        body {
            background-color: #000;
            color: #00ff00;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow-x: hidden;
            padding: 10px;
        }
        
        /* Dynamic Background Handling */
        #bg-video {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            object-fit: cover;
            z-index: -2;
            display: {{ 'block' if main_bg and main_bg.endswith(('.mp4', '.webm', '.ogg')) else 'none' }};
        }
        #bg-image {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background-image: url('{{ main_bg }}');
            background-size: cover;
            background-position: center;
            z-index: -2;
            display: {{ 'block' if main_bg and not main_bg.endswith(('.mp4', '.webm', '.ogg')) else 'none' }};
            opacity: 0.3;
        }
        
        /* Matrix Rain Overlay */
        #matrix-canvas {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: -1;
            opacity: 0.15;
        }

        /* --- AUDIO POPUP OVERLAY --- */
        .audio-popup {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.95);
            backdrop-filter: blur(15px);
            z-index: 99999;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: opacity 0.6s ease;
            cursor: pointer;
        }
        .audio-popup.hidden {
            opacity: 0;
            pointer-events: none;
        }
        .audio-popup-content {
            text-align: center;
            animation: pulse 2s infinite ease-in-out;
        }
        .audio-logo {
            width: 180px;
            height: 180px;
            border-radius: 50%;
            border: 4px solid #00ff00;
            box-shadow: 0 0 40px #00ff00, inset 0 0 20px #00ff00;
            object-fit: cover;
            margin-bottom: 25px;
            transition: transform 0.3s;
        }
        .audio-popup-content:hover .audio-logo {
            transform: scale(1.1);
        }
        .audio-popup-content h2 {
            color: #00ff00;
            text-shadow: 0 0 15px #00ff00;
            font-size: 1.8rem;
            margin-bottom: 10px;
            letter-spacing: 2px;
        }
        .audio-popup-content p {
            color: #fff;
            font-size: 0.9rem;
            opacity: 0.7;
            letter-spacing: 1px;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        /* --- END AUDIO POPUP --- */

        /* Header */
        .header {
            width: 100%;
            max-width: 500px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 15px 20px;
            border-bottom: 1px solid #00ff00;
            margin-bottom: 20px;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(5px);
            position: sticky;
            top: 0;
            z-index: 10;
            border-radius: 0 0 10px 10px;
        }
        .header .left-side {
            display: flex;
            align-items: center;
        }
        .header .menu-icon {
            font-size: 24px;
            margin-right: 15px;
            cursor: pointer;
            transition: color 0.3s;
        }
        .header .menu-icon:hover { color: #fff; }
        .header h1 {
            font-size: 1.1rem;
            color: #00ff00;
            text-shadow: 0 0 10px #00ff00;
            letter-spacing: 1px;
        }
        .header .owner-badge {
            font-size: 0.7rem;
            color: #fff;
            background: #00ff00;
            color: #000;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: bold;
        }

        /* Main Container */
        .container {
            width: 100%;
            max-width: 500px;
            display: flex;
            flex-direction: column;
            align-items: center;
            z-index: 1;
        }
        
        /* User Image Area */
        .image-area {
            margin-bottom: 15px;
            text-align: center;
            position: relative;
        }
        .image-area img {
            width: 250px;
            height: 250px;
            object-fit: cover;
            border: 2px solid #00ff00;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
            background: #111;
        }
        .image-area .subtitle {
            font-size: 1.5rem;
            font-weight: bold;
            color: #00ff00;
            text-shadow: 0 0 15px #00ff00, 0 0 30px #00ff00;
            margin-top: -20px;
            position: relative;
            z-index: 2;
            background: rgba(0,0,0,0.5);
            display: inline-block;
            padding: 5px 15px;
            border-radius: 5px;
        }

        /* Input & Output Boxes */
        .form-box {
            width: 100%;
            background: rgba(0, 0, 0, 0.8);
            border: 1px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
            backdrop-filter: blur(5px);
            margin-bottom: 20px;
        }
        .input-group {
            display: flex;
            align-items: center;
            background: #111;
            border: 1px solid #00ff00;
            border-radius: 8px;
            padding: 10px 15px;
            margin-bottom: 15px;
            box-shadow: inset 0 0 10px rgba(0, 255, 0, 0.1);
        }
        .input-group .icon {
            font-size: 1.2rem;
            margin-right: 10px;
            color: #00ff00;
        }
        .input-group input {
            background: transparent;
            border: none;
            color: #fff;
            font-size: 1rem;
            width: 100%;
            outline: none;
            font-family: 'Share Tech Mono', monospace;
        }
        .input-group input::placeholder {
            color: #00ff00;
            opacity: 0.7;
        }
        
        /* Status Box */
        .status-box {
            background: #111;
            border: 1px solid #00ff00;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            min-height: 60px;
            font-size: 0.9rem;
            color: #00ff00;
            box-shadow: inset 0 0 10px rgba(0, 255, 0, 0.1);
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .status-box p { margin: 2px 0; }

        /* Buttons */
        .btn-group {
            display: flex;
            gap: 10px;
            width: 100%;
        }
        .btn {
            flex: 1;
            padding: 15px;
            background: #000;
            border: 2px solid #00ff00;
            color: #00ff00;
            font-size: 1.2rem;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-shadow: 0 0 5px #00ff00;
            font-family: 'Share Tech Mono', monospace;
        }
        .btn:hover {
            background: #00ff00;
            color: #000;
            box-shadow: 0 0 20px #00ff00;
            text-shadow: none;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            background: #000;
            color: #00ff00;
        }
        .btn-stop {
            border-color: #ff0000;
            color: #ff0000;
            text-shadow: 0 0 5px #ff0000;
        }
        .btn-stop:hover {
            background: #ff0000;
            color: #000;
            box-shadow: 0 0 20px #ff0000;
            text-shadow: none;
        }

        /* Footer */
        .footer {
            width: 100%;
            max-width: 500px;
            text-align: center;
            margin-top: 10px;
            padding-bottom: 20px;
        }
        .footer .modded {
            font-size: 1rem;
            color: #00ff00;
            text-shadow: 0 0 5px #00ff00;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            top: 0;
            left: -320px; 
            width: 300px;
            height: 100%;
            background: #000;
            border-right: 2px solid #00ff00;
            z-index: 1000;
            transition: left 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: flex;
            flex-direction: column;
            padding: 20px;
            overflow-y: auto;
        }
        .sidebar.active { left: 0; }
        
        /* Sidebar Background */
        .sidebar-bg {
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: -1;
            opacity: 0.2;
            object-fit: cover;
        }

        .sidebar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 10px;
            border-bottom: 1px solid #00ff00;
        }
        .sidebar-header h2 { color: #00ff00; font-size: 1.2rem; }
        .close-btn {
            background: none;
            border: none;
            color: #00ff00;
            font-size: 2rem;
            cursor: pointer;
            line-height: 1;
        }
        .close-btn:hover { color: #fff; }

        .contact-section { margin-top: 20px; }
        .contact-section h3 { color: #00ff00; margin-bottom: 15px; font-size: 1rem; border-bottom: 1px dashed #00ff00; padding-bottom: 5px;}
        
        .contact-item {
            display: flex;
            align-items: center;
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
            text-decoration: none;
            color: #00ff00;
            transition: all 0.3s;
        }
        .contact-item:hover {
            background: #00ff00;
            color: #000;
            box-shadow: 0 0 15px #00ff00;
        }
        .contact-item .icon { font-size: 1.5rem; margin-right: 15px; }
        .contact-item .info { display: flex; flex-direction: column; }
        .contact-item .info .label { font-size: 0.7rem; text-transform: uppercase; }
        .contact-item .info .value { font-size: 0.9rem; font-weight: bold; }

        /* Overlay for sidebar */
        .overlay {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 999;
            display: none;
            opacity: 0;
            transition: opacity 0.4s;
        }
        .overlay.active { display: block; opacity: 1; }

        @media (max-width: 480px) {
            .header h1 { font-size: 0.9rem; }
            .image-area img { width: 200px; height: 200px; }
            .image-area .subtitle { font-size: 1.2rem; }
        }
    </style>
</head>
<body>
    <!-- Background Audio -->
    {% if audio_url %}
        <audio id="bg-music" loop preload="auto" src="{{ audio_url }}"></audio>
        
        <!-- Tap to Play Music Popup -->
        <div id="audio-popup" class="audio-popup">
            <div class="audio-popup-content">
                <img src="{{ profile_image }}" alt="Logo" class="audio-logo">
                <h2>TAP TO ENABLE MUSIC</h2>
                <p>Click anywhere to start the experience</p>
            </div>
        </div>
    {% endif %}

    <!-- Dynamic Backgrounds -->
    {% if main_bg %}
        {% if main_bg.endswith(('.mp4', '.webm', '.ogg')) %}
            <video id="bg-video" autoplay loop muted playsinline src="{{ main_bg }}"></video>
        {% else %}
            <div id="bg-image"></div>
        {% endif %}
    {% endif %}
    
    <canvas id="matrix-canvas"></canvas>

    <!-- Sidebar Overlay -->
    <div class="overlay" id="overlay"></div>

    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
        {% if sidebar_bg %}
            {% if sidebar_bg.endswith(('.mp4', '.webm', '.ogg')) %}
                <video class="sidebar-bg" autoplay loop muted playsinline src="{{ sidebar_bg }}"></video>
            {% else %}
                <img class="sidebar-bg" src="{{ sidebar_bg }}" alt="Sidebar BG">
            {% endif %}
        {% endif %}
        
        <div class="sidebar-header">
            <h2>MENU</h2>
            <button class="close-btn" id="closeSidebarBtn">&times;</button>
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="{{ profile_image }}" style="width: 100px; height: 100px; border-radius: 50%; border: 2px solid #00ff00; object-fit: cover;">
            <h3 style="color: #fff; margin-top: 10px;">{{ owner_name }}</h3>
            <p style="color: #00ff00; font-size: 0.8rem;">Owner & Developer</p>
        </div>

        <div class="contact-section">
            <h3>CONTACT ME</h3>
            
            <a href="tel:{{ phone }}" class="contact-item">
                <span class="icon">&#128222;</span>
                <div class="info">
                    <span class="label">Phone</span>
                    <span class="value">{{ phone }}</span>
                </div>
            </a>

            <a href="https://t.me/{{ telegram }}" target="_blank" class="contact-item">
                <span class="icon">&#128172;</span>
                <div class="info">
                    <span class="label">Telegram</span>
                    <span class="value">{{ telegram }}</span>
                </div>
            </a>

            <a href="https://wa.me/{{ whatsapp }}" target="_blank" class="contact-item">
                <span class="icon">&#128241;</span>
                <div class="info">
                    <span class="label">WhatsApp</span>
                    <span class="value">{{ whatsapp }}</span>
                </div>
            </a>
        </div>
        
        <div style="margin-top: auto; text-align: center; font-size: 0.7rem; color: #00ff00; padding-top: 20px;">
            &copy; 2024 {{ owner_name }}
        </div>
    </div>

    <div class="header">
        <div class="left-side">
            <div class="menu-icon" id="openSidebarBtn">&#9776;</div>
            <h1>Sukuna Bomber @{{ owner_name }}</h1>
        </div>
        <div class="owner-badge">OWNER</div>
    </div>

    <div class="container">
        <div class="image-area">
            <img id="user-image" src="{{ profile_image }}" alt="User Image">
            <div class="subtitle">Call + Sms Bomber</div>
        </div>

        <div class="form-box">
            <div class="input-group">
                <span class="icon">&#128241;</span>
                <input type="tel" id="numberInput" placeholder="Enter (10) digit number" value="9876543210">
            </div>
            <div class="input-group">
                <span class="icon">&#128290;</span>
                <input type="number" id="countInput" placeholder="How many messages?" value="{{ default_count }}" min="1" max="500">
            </div>
            
            <div class="status-box" id="statusBox">
                <p>Status: Ready to attack</p>
            </div>

            <div class="btn-group">
                <button class="btn" id="attackBtn">ATTCK</button>
                <button class="btn btn-stop" id="stopBtn" disabled>STOP</button>
            </div>
        </div>

        <div class="footer">
            <div class="modded">Modded By @{{ owner_name }}</div>
        </div>
    </div>

    <script>
        // --- Auto Background Music Popup Logic ---
        const bgMusic = document.getElementById('bg-music');
        const audioPopup = document.getElementById('audio-popup');

        if (bgMusic && audioPopup) {
            bgMusic.volume = 0.5; // Set volume to 50%
            let audioUnlocked = false;
            
            const unlockAudio = () => {
                if (audioUnlocked) return;
                bgMusic.play().then(() => {
                    audioUnlocked = true;
                    audioPopup.classList.add('hidden');
                    // Remove listeners once music starts
                    document.removeEventListener('click', unlockAudio);
                    document.removeEventListener('touchstart', unlockAudio);
                }).catch(error => {
                    console.log("Playback failed, will try again on next interaction:", error);
                });
            };

            // Attach to the popup itself
            audioPopup.addEventListener('click', unlockAudio);
            audioPopup.addEventListener('touchstart', unlockAudio);
            
            // Also attach to the whole document just in case
            document.addEventListener('click', unlockAudio);
            document.addEventListener('touchstart', unlockAudio);
            
            // Fallback: If the popup is clicked but audio fails, hide the popup anyway so the user isn't stuck.
            audioPopup.addEventListener('click', () => {
                setTimeout(() => { audioPopup.classList.add('hidden'); }, 1500);
            });
        }

        // --- Sidebar Logic ---
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('overlay');
        const openBtn = document.getElementById('openSidebarBtn');
        const closeBtn = document.getElementById('closeSidebarBtn');

        function openSidebar() {
            sidebar.classList.add('active');
            overlay.classList.add('active');
        }
        function closeSidebar() {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        }

        openBtn.addEventListener('click', openSidebar);
        closeBtn.addEventListener('click', closeSidebar);
        overlay.addEventListener('click', closeSidebar);

        // --- Matrix Rain Effect ---
        const canvas = document.getElementById('matrix-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*()';
        const fontSize = 14;
        const columns = canvas.width / fontSize;
        const drops = [];
        for (let x = 0; x < columns; x++) drops[x] = 1;

        function drawMatrix() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#00ff00';
            ctx.font = fontSize + 'px monospace';
            for (let i = 0; i < drops.length; i++) {
                const text = letters.charAt(Math.floor(Math.random() * letters.length));
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0;
                drops[i]++;
            }
        }
        setInterval(drawMatrix, 50);
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });

        // --- Attack Logic ---
        const attackBtn = document.getElementById('attackBtn');
        const stopBtn = document.getElementById('stopBtn');
        const numberInput = document.getElementById('numberInput');
        const countInput = document.getElementById('countInput');
        const statusBox = document.getElementById('statusBox');
        
        let isAttacking = false;
        let attackInterval = null;
        let currentCount = 0;
        let totalCount = parseInt(countInput.value) || 20;
        const API_KEY = "{{ api_key }}"; 

        function setStatus(msg, isError = false) {
            statusBox.innerHTML = `<p>Status: ${msg}</p>`;
            statusBox.style.color = isError ? '#ff0000' : '#00ff00';
            statusBox.style.borderColor = isError ? '#ff0000' : '#00ff00';
        }

        async function sendAttack(number, counter) {
            try {
                const url = `/api/bomber?key=${API_KEY}&number=${number}&counter=${counter}`;
                const res = await fetch(url);
                const data = await res.json();
                
                if (res.ok) {
                    setStatus(`Success! Message ${counter} of ${totalCount} sent.`);
                } else {
                    setStatus(`Error sending message ${counter}: ${data.error || 'Unknown error'}`, true);
                }
            } catch (err) {
                setStatus(`Network error on message ${counter}`, true);
            }
        }

        attackBtn.addEventListener('click', () => {
            const number = numberInput.value.trim();
            totalCount = parseInt(countInput.value);
            
            if (number.length < 10) { alert('Please enter a valid 10-digit number.'); return; }
            if (!totalCount || totalCount < 1) { alert('Please enter a valid count (1-500).'); return; }
            if (isAttacking) return;

            isAttacking = true;
            attackBtn.disabled = true;
            stopBtn.disabled = false;
            setStatus('Starting attack...');

            let counter = 1;

            const run = () => {
                if (!isAttacking || counter > totalCount) {
                    stopAttack();
                    if (counter > totalCount) setStatus('Attack finished successfully.');
                    return;
                }
                sendAttack(number, counter);
                counter++;
                attackInterval = setTimeout(run, 800); 
            };
            run();
        });

        stopBtn.addEventListener('click', stopAttack);

        function stopAttack() {
            isAttacking = false;
            attackBtn.disabled = false;
            stopBtn.disabled = true;
            if (attackInterval) {
                clearTimeout(attackInterval);
                attackInterval = null;
            }
            setStatus('Attack stopped by user.', true);
        }
    </script>
</body>
</html>
"""

# --- ADMIN PANEL INTERFACE ---
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - Sukuna Bomber</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body {
            background: #0f0c29;
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .admin-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            width: 100%;
            max-width: 600px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }
        .admin-card h1 {
            text-align: center;
            margin-bottom: 30px;
            color: #00ff00;
            text-shadow: 0 0 10px #00ff00;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            font-size: 0.9rem;
            margin-bottom: 8px;
            color: #ccc;
        }
        .form-group input[type="text"],
        .form-group input[type="number"] {
            width: 100%;
            padding: 12px 15px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: #fff;
            font-size: 1rem;
            outline: none;
        }
        .form-group input:focus {
            border-color: #00ff00;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.3);
        }
        .btn-save {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #00ff00, #00aa00);
            color: #000;
            border: none;
            border-radius: 8px;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
            margin-top: 10px;
            margin-bottom: 20px;
        }
        .btn-save:hover { transform: scale(1.02); }
        .back-link {
            display: block;
            text-align: center;
            margin-top: 20px;
            color: #00ff00;
            text-decoration: none;
            font-size: 0.9rem;
        }
        .back-link:hover { text-decoration: underline; }
        hr { border: 1px solid rgba(255,255,255,0.1); margin: 30px 0; }
        .section-title { color: #00ff00; margin-bottom: 15px; font-size: 1.2rem; border-bottom: 1px solid #00ff00; padding-bottom: 5px; display: inline-block;}
        .warning { background: rgba(255, 0, 0, 0.1); border: 1px solid #ff0000; color: #ff5555; padding: 10px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 20px; text-align: center;}
    </style>
</head>
<body>
    <div class="admin-card">
        <h1>⚙️ Admin Panel</h1>
        
        <div class="warning">
            ⚠️ <strong>Vercel Hosting Note:</strong> Vercel does not allow permanent file uploads. For images and audio to work, please upload them to a free image host (like Imgur or Catbox) and paste the <strong>Direct Link</strong> below.
        </div>

        <!-- Text Settings -->
        <form action="/admin/settings" method="POST">
            <h2 class="section-title">General Settings</h2>
            
            <div class="form-group">
                <label>Owner / Developer Name</label>
                <input type="text" name="owner_name" value="{{ owner_name }}" required>
            </div>
            
            <div class="form-group">
                <label>API Key (Hidden on main site)</label>
                <input type="text" name="api_key" value="{{ api_key }}" required>
            </div>
            
            <div class="form-group">
                <label>Default Attack Count</label>
                <input type="number" name="default_count" value="{{ default_count }}" required min="1" max="500">
            </div>

            <div class="form-group">
                <label>Profile Image URL (Direct Link)</label>
                <input type="text" name="profile_image" value="{{ profile_image }}" required>
            </div>

            <div class="form-group">
                <label>Main Background URL (Image or Video Direct Link)</label>
                <input type="text" name="main_bg" value="{{ main_bg }}">
            </div>

            <div class="form-group">
                <label>Sidebar Background URL (Image or Video Direct Link)</label>
                <input type="text" name="sidebar_bg" value="{{ sidebar_bg }}">
            </div>

            <div class="form-group">
                <label>Background Music URL (MP3 Direct Link)</label>
                <input type="text" name="audio_url" value="{{ audio_url }}">
            </div>

            <h2 class="section-title" style="margin-top: 20px;">Contact Information</h2>
            
            <div class="form-group">
                <label>Phone Number</label>
                <input type="text" name="phone" value="{{ phone }}" required>
            </div>
            
            <div class="form-group">
                <label>Telegram Username (without @)</label>
                <input type="text" name="telegram" value="{{ telegram }}" required>
            </div>
            
            <div class="form-group">
                <label>WhatsApp Number (with country code)</label>
                <input type="text" name="whatsapp" value="{{ whatsapp }}" required>
            </div>

            <button type="submit" class="btn-save">Save All Settings</button>
        </form>

        <a href="/" class="back-link">← Go to Main Bomber</a>
    </div>
</body>
</html>
"""

# ----------------------------------------------------------------------
# ROUTES
# ----------------------------------------------------------------------

@app.route('/')
def index():
    settings = load_settings()
    return render_template_string(
        MAIN_HTML, 
        image_url=settings['profile_image'],
        api_key=settings['api_key'],
        default_count=settings['default_count'],
        owner_name=settings['owner_name'],
        profile_image=settings['profile_image'],
        main_bg=settings['main_bg'],
        sidebar_bg=settings['sidebar_bg'],
        audio_url=settings['audio_url'],
        phone=settings['phone'],
        telegram=settings['telegram'],
        whatsapp=settings['whatsapp']
    )

@app.route('/admin')
def admin():
    settings = load_settings()
    return render_template_string(
        ADMIN_HTML,
        profile_image=settings['profile_image'],
        api_key=settings['api_key'],
        default_count=settings['default_count'],
        owner_name=settings['owner_name'],
        main_bg=settings['main_bg'],
        sidebar_bg=settings['sidebar_bg'],
        audio_url=settings['audio_url'],
        phone=settings['phone'],
        telegram=settings['telegram'],
        whatsapp=settings['whatsapp']
    )

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    settings = load_settings()
    settings['owner_name'] = request.form.get('owner_name', settings['owner_name'])
    settings['api_key'] = request.form.get('api_key', settings['api_key'])
    settings['phone'] = request.form.get('phone', settings['phone'])
    settings['telegram'] = request.form.get('telegram', settings['telegram'])
    settings['whatsapp'] = request.form.get('whatsapp', settings['whatsapp'])
    settings['profile_image'] = request.form.get('profile_image', settings['profile_image'])
    settings['main_bg'] = request.form.get('main_bg', settings['main_bg'])
    settings['sidebar_bg'] = request.form.get('sidebar_bg', settings['sidebar_bg'])
    settings['audio_url'] = request.form.get('audio_url', settings['audio_url'])
    try:
        settings['default_count'] = int(request.form.get('default_count', settings['default_count']))
    except ValueError:
        pass
    save_settings(settings)
    return redirect('/admin')

@app.route('/api/bomber', methods=['GET'])
def bomber_proxy():
    key = request.args.get('key')
    number = request.args.get('number')
    counter = request.args.get('counter')

    if not all([key, number, counter]):
        return jsonify({"error": "Missing parameters"}), 400

    target_url = f"{API_BASE_URL}?key={key}&number={number}&counter={counter}"

    try:
        response = requests.get(target_url, timeout=15)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 502

if __name__ == '__main__':
    print("Starting Sukuna Bomber...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 4887)), debug=True)
