from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import random
import base64

app = Flask(__name__)
app.secret_key = 'kesh_aadar_secure_key_2026'

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "subhraroy324@gmail.com"
SMTP_PASS = "idxv jjob guit vtfb"

# --- STORAGE & DATA PERSISTENCE FOR VERCEL ---
DATA_FILE = "/tmp/kesh_store_data.json"

DEFAULT_PRODUCTS = [
    {"id": 1, "name": "Aloe Neem Glow Face Wash", "category": "Skincare", "price": 349, "stock": 50, "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", "desc": "Deep cleansing herbal formula for radiant skin.", "status": "live"},
    {"id": 2, "name": "Saffron Kumkumadi Night Serum", "category": "Skincare", "price": 799, "stock": 30, "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", "desc": "Fades blemishes and restores natural skin glow.", "status": "live"},
    {"id": 3, "name": "Bhringraj Onion Hair Growth Oil", "category": "Haircare", "price": 499, "stock": 40, "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", "desc": "Stops hair fall and stimulates roots naturally.", "status": "live"},
    {"id": 4, "name": "Hibiscus & Shikakai Herbal Shampoo", "category": "Haircare", "price": 399, "stock": 45, "image": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80", "desc": "Nourishing sulfate-free cleanser for smooth hair.", "status": "live"}
]

DEFAULT_LOGO = "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "products": DEFAULT_PRODUCTS,
        "orders": [],
        "blacklisted_ips": [],
        "logo": DEFAULT_LOGO
    }

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving data: {e}")

# --- BACKGROUND EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> - ₹{i['price']}</li>" for i in items])
        track_url = f"https://{request.host}/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 36px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">KESH AADAR</h1>
                <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 12px; font-weight: bold; margin-top: 0; text-align: center;">Pure Botanical Remedies</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <h2 style="color: #1b4332; font-size: 22px;">Thank you for your order, {name}!</h2>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">Your order has been placed successfully. We are currently preparing your botanical items for dispatch.</p>
                
                <div style="background: #F3EFEA; padding: 20px; border-radius: 12px; margin: 25px 0; border: 1px dashed #d4a373;">
                    <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">Order Reference ID</p>
                    <h3 style="margin: 8px 0; font-size: 28px; color: #1b4332; font-family: monospace;">{order_id}</h3>
                    <p style="margin: 5px 0; color: #333; font-size: 14px; font-weight: 600;">Total Paid/Payable: ₹{amount}</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;"><b>Shipping To:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 5px 15px rgba(27, 67, 50, 0.3);">Check Live Order Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact support at subhraroy324@gmail.com</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASS)
        server.sendmail(SMTP_EMAIL, recipient_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.before_request
def check_ip_blacklist():
    data = load_data()
    client_ip = request.remote_addr
    if client_ip in data.get('blacklisted_ips', []):
        return jsonify({"error": "Your IP has been blacklisted by administrator."}), 403

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    data = load_data()
    # Filter only live products for storefront
    live_products = [p for p in data['products'] if p.get('status', 'live') == 'live']
    return render_template_string(TEMPLATE, products=live_products, logo=data['logo'])

@app.route('/place_order', methods=['POST'])
def place_order():
    store = load_data()
    req_data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    req_data['order_id'] = order_id
    req_data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    req_data['client_ip'] = request.remote_addr
    req_data['status'] = 'Processing'  # Initial status: Processing -> Packaging -> Shipped -> Delivered
    
    full_address = f"{req_data.get('street', '')}, Landmark: {req_data.get('landmark', '')}, {req_data.get('city', '')}, {req_data.get('state', '')} - {req_data.get('pincode', '')}"
    req_data['full_address'] = full_address
    
    store['orders'].append(req_data)
    save_data(store)
    
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(req_data['email'], req_data['name'], order_id, req_data['amount'], req_data['items'], full_address)
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": req_data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    store = load_data()
    order = next((o for o in store['orders'] if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, logo=store['logo'])

@app.route('/track_order')
def track_order():
    store = load_data()
    q = request.args.get('q', '').strip()
    for o in store['orders']:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order": o})
    return jsonify({"found": False})

# --- ADMIN PANEL ROUTE ---
@app.route('/admin')
def admin_panel():
    store = load_data()
    return render_template_string(ADMIN_TEMPLATE, store=store)

@app.route('/api/admin/update_order_status', methods=['POST'])
def admin_update_order_status():
    store = load_data()
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status') # Processing, Packaging, Shipped, Delivered
    for o in store['orders']:
        if o['order_id'] == order_id:
            o['status'] = new_status
            save_data(store)
            return jsonify({"status": "success"})
    return jsonify({"error": "Order not found"}), 404

@app.route('/api/admin/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
def admin_manage_products():
    store = load_data()
    if request.method == 'GET':
        return jsonify(store['products'])
    
    data = request.get_json()
    if request.method == 'POST':
        # Add product
        new_id = max([p['id'] for p in store['products']], default=0) + 1
        new_product = {
            "id": new_id,
            "name": data.get('name'),
            "category": data.get('category', 'General'),
            "price": float(data.get('price', 0)),
            "stock": int(data.get('stock', 0)),
            "image": data.get('image', 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=500&q=80'),
            "desc": data.get('desc', ''),
            "status": data.get('status', 'live') # 'live' or 'suspended'
        }
        store['products'].append(new_product)
        save_data(store)
        return jsonify({"status": "success", "product": new_product})
        
    elif request.method == 'PUT':
        # Edit or Suspend product
        prod_id = int(data.get('id'))
        for p in store['products']:
            if p['id'] == prod_id:
                p['name'] = data.get('name', p['name'])
                p['category'] = data.get('category', p['category'])
                p['price'] = float(data.get('price', p['price']))
                p['stock'] = int(data.get('stock', p['stock']))
                p['image'] = data.get('image', p['image'])
                p['desc'] = data.get('desc', p['desc'])
                if 'status' in data:
                    p['status'] = data.get('status')
                save_data(store)
                return jsonify({"status": "success"})
        return jsonify({"error": "Product not found"}), 404

    elif request.method == 'DELETE':
        # Delete product
        prod_id = int(data.get('id'))
        store['products'] = [p for p in store['products'] if p['id'] != prod_id]
        save_data(store)
        return jsonify({"status": "success"})

@app.route('/api/admin/logo', methods=['POST'])
def admin_update_logo():
    store = load_data()
    data = request.get_json()
    new_logo = data.get('logo')
    if new_logo:
        store['logo'] = new_logo
        save_data(store)
        return jsonify({"status": "success", "logo": new_logo})
    return jsonify({"error": "Invalid logo"}), 400

# --- FRONTEND TEMPLATE (STOREFRONT) ---
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KESH AADAR | Pure Herbal Botanicals</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; --shadow: 0 20px 40px rgba(27, 67, 50, 0.15); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); overflow-x: hidden; scroll-behavior: smooth; }

        .reveal { opacity: 0; transform: translateY(40px); transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }

        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.05); }
        .nav-left { display: flex; align-items: center; gap: 15px; }
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; transition: transform 0.3s; }
        .menu-btn:hover { transform: scale(1.1); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: transform 0.2s; }
        .cart-icon-container:hover { transform: scale(1.05); }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Butter-Smooth Sidebar Drawer */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), visibility 0.4s; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: background 0.2s, transform 0.2s; }
        .sidebar button.menu-item:hover { background: #f1f3f5; transform: translateX(4px); }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); transition: transform 0.2s; }
        .close-sidebar:hover { transform: rotate(90deg); color: var(--green-primary); }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); transition: transform 0.2s; }
        .support-card:hover { transform: translateY(-2px); }

        /* Hero */
        .hero { height: 80vh; display: flex; align-items: center; justify-content: center; text-align: center; background: radial-gradient(circle, #f3efea 0%, #faf7f0 75%); margin-top: 70px; padding: 0 20px; }
        .hero-content h1 { font-family: 'Playfair Display', serif; font-size: clamp(34px, 6vw, 54px); color: var(--green-primary); margin-bottom: 15px; }
        .btn-primary { background: var(--green-primary); color: white; padding: 14px 38px; border-radius: 35px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: 0.3s; }
        .btn-primary:hover { background: var(--green-light); transform: translateY(-2px); }

        .features-banner { background: var(--green-primary); color: white; display: flex; justify-content: space-around; padding: 20px; flex-wrap: wrap; gap: 15px; }
        .feature-item { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 500; }

        /* Products Grid */
        .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 30px; }
        .product-card { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); transition: 0.3s; }
        .product-card:hover { transform: translateY(-5px); }
        .product-img-container { height: 230px; overflow: hidden; background: #f7f5f0; }
        .product-img-container img { width: 100%; height: 100%; object-fit: cover; }
        .product-info { padding: 20px; }
        .price-row { display: flex; justify-content: space-between; align-items: center; margin: 15px 0; }
        .price { font-size: 22px; font-weight: 700; color: var(--green-light); }
        .btn-group { display: flex; gap: 10px; }
        .btn-cart { flex: 1; padding: 10px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: background 0.2s; }
        .btn-cart:hover { background: #e5dfd5; }
        .btn-buy { flex: 1; padding: 10px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: background 0.2s; }
        .btn-buy:hover { background: var(--green-light); }

        .fly-item { position: fixed; z-index: 9999; width: 50px; height: 50px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); transition: all 0.8s cubic-bezier(0.2, 1, 0.3, 1); pointer-events: none; }

        /* Modal */
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); display: none; justify-content: center; align-items: center; z-index: 3000; padding: 15px; }
        .modal-content { background: white; width: 100%; max-width: 520px; padding: 30px; border-radius: 20px; max-height: 90vh; overflow-y: auto; position: relative; animation: modalPop 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes modalPop { 0% { transform: scale(0.9); opacity: 0; } 100% { transform: scale(1); opacity: 1; } }

        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .full-width { grid-column: span 2; }
        .checkout-form input, .checkout-form select, .checkout-form textarea { width: 100%; padding: 11px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }

        .bill-summary { background: #FAF7F0; border: 1px solid #EAE5D9; border-radius: 12px; padding: 15px; margin: 15px 0; font-size: 13px; }
        .bill-row { display: flex; justify-content: space-between; margin-bottom: 6px; color: #555; }
        .bill-row.total { border-top: 1px dashed #ccc; padding-top: 8px; font-weight: bold; font-size: 16px; color: var(--green-primary); }

        .saved-addr-btn { background: #e8f5e9; color: #2e7d32; border: 1px dashed #2e7d32; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600; width: 100%; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; gap: 8px; }

        /* Footer */
        .main-footer { background-color: var(--green-primary); color: white; padding: 50px 30px 20px; margin-top: 60px; }
        .footer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 30px; max-width: 1200px; margin: 0 auto; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 30px; }
        .footer-grid h3 { color: var(--accent-gold); font-family: 'Playfair Display'; font-size: 20px; margin-bottom: 15px; }
        .footer-grid p { font-size: 14px; margin-bottom: 10px; color: #ddd; display: flex; align-items: center; gap: 10px; }
        .social-icons { margin-top: 15px; display: flex; gap: 15px; }
        .social-icons a { color: white; font-size: 18px; background: rgba(255,255,255,0.1); width: 38px; height: 38px; display: flex; justify-content: center; align-items: center; border-radius: 50%; text-decoration: none; transition: background 0.2s; }
        .social-icons a:hover { background: var(--accent-gold); }
        .footer-bottom { padding-top: 20px; font-size: 12px; color: #aaa; text-align: center; }
    </style>
</head>
<body>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
                <img src="{{ logo }}" alt="Logo" class="logo-img">
                <div class="logo"><span>Kesh</span> Aadar</div>
            </div>
        </div>
        <div class="cart-icon-container" id="cartTarget" onclick="openCartModal()">
            <i class="fa-solid fa-shopping-basket"></i><span class="cart-badge" id="cart-count">0</span>
        </div>
    </header>

    <!-- Sidebar Drawer -->
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <span class="close-sidebar" onclick="toggleSidebar()">&times;</span>
        
        <div id="sidebar-main-view">
            <h3 style="margin-top: 10px; font-size: 20px;">Welcome</h3>
            <p style="font-size: 13px; color: #666; margin-bottom: 25px;">How can we assist you today?</p>
            <button class="menu-item" onclick="switchSidebarView('track')"><i class="fa-solid fa-map-location-dot"></i> Track Order</button>
            <button class="menu-item" onclick="switchSidebarView('support')"><i class="fa-solid fa-headset"></i> Help & Support</button>
            <button class="menu-item" onclick="switchSidebarView('faq')"><i class="fa-solid fa-circle-question"></i> Product FAQs</button>
            <a href="/admin" class="menu-item" style="text-decoration:none; margin-top:20px; background:#1b4332; color:white;"><i class="fa-solid fa-gauge-high" style="color:var(--accent-gold);"></i> Admin Panel</a>
        </div>

        <div id="sidebar-track-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Track Order</h3>
            <input type="text" id="track-input" placeholder="Order ID or Email Address">
            <button class="action-btn" onclick="trackOrder()">Track Now <i class="fa-solid fa-magnifying-glass"></i></button>
            <div id="track-result" style="margin-top: 20px;"></div>
        </div>

        <div id="sidebar-support-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Customer Support</h3>
            <a href="mailto:subhraroy324@gmail.com" class="support-card"><i class="fa-solid fa-envelope" style="color: var(--accent-gold);"></i><div><h4 style="font-size: 13px; color: var(--green-primary);">Email Support</h4><p style="font-size: 11px; color: #555;">subhraroy324@gmail.com</p></div></a>
            <a href="tel:9163641507" class="support-card"><i class="fa-solid fa-phone-volume" style="color: var(--green-primary);"></i><div><h4 style="font-size: 13px; color: var(--green-primary);">Call Support</h4><p style="font-size: 11px; color: #555;">+91 9163641507</p></div></a>
            <a href="https://wa.me/919163641507" target="_blank" class="support-card" style="background: #e8f5e9;"><i class="fa-brands fa-whatsapp" style="color: #2e7d32; font-size: 20px;"></i><div><h4 style="font-size: 13px; color: #2e7d32;">WhatsApp Support</h4><p style="font-size: 11px; color: #555;">Instant messaging</p></div></a>
        </div>

        <div id="sidebar-faq-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Frequently Asked Questions</h3>
            <h4 style="font-size: 13px; color: var(--green-primary);">1. What is the estimated dispatch time?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Orders are dispatched within 24-48 hours.</p>
            <h4 style="font-size: 13px; color: var(--green-primary);">2. How do I track my delivery?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">You can track live status via order ID in the tracking section.</p>
        </div>
    </div>

    <!-- Hero -->
    <section class="hero reveal">
        <div class="hero-content">
            <h1>Pure Botanical Wellness</h1>
            <p style="margin-bottom:25px; font-size:16px; color:#555;">Formulated with organic extracts for natural skin and hair care.</p>
            <a href="#shop" class="btn-primary">Shop Formulations</a>
        </div>
    </section>

    <!-- Features -->
    <div class="features-banner">
        <div class="feature-item"><i class="fa-solid fa-leaf" style="color:var(--accent-gold);"></i> 100% Organic</div>
        <div class="feature-item"><i class="fa-solid fa-truck-fast" style="color:var(--accent-gold);"></i> Express Shipping</div>
        <div class="feature-item"><i class="fa-solid fa-shield-cat" style="color:var(--accent-gold);"></i> Cruelty-Free</div>
    </div>

    <!-- Shop -->
    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 28px; color: var(--green-primary); margin-bottom: 30px;" class="reveal">Our Formulations</h2>
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-img-container"><img src="{{ p.image }}" alt="{{ p.name }}" id="img-{{ p.id }}"></div>
                <div class="product-info">
                    <h3 style="color:var(--green-primary); font-size:16px; margin-bottom:5px;">{{ p.name }}</h3>
                    <p style="font-size:12px; color:#666;">{{ p.desc }}</p>
                    <div class="price-row">
                        <span class="price">₹{{ p.price }}</span>
                        <span style="font-size:11px; padding:3px 8px; border-radius:6px; background:#e8f5e9; color:#2e7d32; font-weight:600;">Stock: {{ p.stock }}</span>
                    </div>
                    <div class="btn-group">
                        <button class="btn-cart" onclick="addToCartAndFly(event, {{ p.id }})">Add to Cart</button>
                        <button class="btn-buy" onclick="buyNow({{ p.id }})">Buy Now</button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Footer -->
    <footer class="main-footer">
        <div class="footer-grid">
            <div>
                <h3>KESH AADAR</h3>
                <p style="font-size: 13px; line-height: 1.7;">Bringing ancient botanical secrets directly into your daily routine. Pure and natural.</p>
            </div>
            <div>
                <h3>Customer Support</h3>
                <p><i class="fa-solid fa-envelope" style="color:var(--accent-gold);"></i> subhraroy324@gmail.com</p>
                <p><i class="fa-solid fa-phone" style="color:var(--accent-gold);"></i> +91 9163641507</p>
            </div>
            <div>
                <h3>Connect With Us</h3>
                <div class="social-icons">
                    <a href="https://www.instagram.com/kesh_aadar?igsh=dG5wYWVjMm8wanN5" target="_blank"><i class="fa-brands fa-instagram"></i></a>
                    <a href="https://www.facebook.com/share/1GqaNPpsU7/" target="_blank"><i class="fa-brands fa-facebook-f"></i></a>
                </div>
            </div>
        </div>
        <div class="footer-bottom">
            &copy; 2026 Kesh Aadar Botanical Remedies. All Rights Reserved.
        </div>
    </footer>

    <!-- Cart / Checkout Modal -->
    <div class="modal" id="cartModal">
        <div class="modal-content">
            <span class="close-sidebar" onclick="document.getElementById('cartModal').style.display='none'" style="position:absolute; right:20px; top:20px;">&times;</span>
            <h3 style="color:var(--green-primary); margin-bottom:15px;">Your Shopping Basket</h3>
            <div id="cart-items-container"></div>
            
            <div id="checkout-section" style="display:none; margin-top:20px;">
                <button type="button" class="saved-addr-btn" id="useSavedAddrBtn" onclick="loadSavedAddress()" style="display:none;">
                    <i class="fa-solid fa-clock-rotate-left"></i> Fill Saved Address
                </button>

                <h4 style="margin-bottom:12px; font-size:15px; color:var(--green-primary);">Shipping Details</h4>
                <form class="checkout-form" id="checkoutForm" onsubmit="event.preventDefault(); placeOrder();">
                    <div class="form-grid">
                        <input type="text" id="cust-name" class="full-width" placeholder="Full Name *" required>
                        <input type="email" id="cust-email" class="full-width" placeholder="Email Address (For Instant Updates) *" required>
                        <input type="tel" id="cust-phone" class="full-width" placeholder="Phone Number *" required pattern="[0-9]{10}">
                        
                        <input type="text" id="cust-pincode" placeholder="PIN Code *" required pattern="[0-9]{6}" maxlength="6" onkeyup="detectPinCode(this.value)">
                        <input type="text" id="cust-city" placeholder="District / City *" required readonly style="background:#f4f4f4;">
                        <input type="text" id="cust-state" placeholder="State *" required readonly style="background:#f4f4f4;">
                        
                        <select id="cust-landmark" class="full-width">
                            <option value="">Select Landmark / Area (Optional)</option>
                        </select>
                        
                        <textarea id="cust-street" class="full-width" placeholder="House No., Flat, Street Area Name *" rows="2" required></textarea>
                    </div>

                    <h4 style="margin: 15px 0 8px 0; font-size:14px; color:var(--green-primary);">Payment Option</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <label style="display:flex; align-items:center; gap:10px; padding:10px; border:1px solid #ddd; border-radius:8px; cursor:pointer;" onclick="updateTotal()">
                            <input type="radio" name="pay_mode" value="online" checked> Online Payment
                        </label>
                        <label style="display:flex; align-items:center; gap:10px; padding:10px; border:1px solid #ddd; border-radius:8px; cursor:pointer;" onclick="updateTotal()">
                            <input type="radio" name="pay_mode" value="cod"> Cash on Delivery
                        </label>
                    </div>

                    <div class="bill-summary">
                        <div class="bill-row"><span>Items Subtotal:</span><span id="bill-subtotal">₹0</span></div>
                        <div class="bill-row" id="cod-fee-row" style="display:none; color:#c62828;"><span>COD Handling Fee:</span><span>₹99</span></div>
                        <div class="bill-row"><span>Estimated Shipping:</span><span style="color:#2e7d32; font-weight:600;">FREE</span></div>
                        <div class="bill-row total"><span>Total Payable:</span><span id="bill-total">₹0</span></div>
                    </div>

                    <button type="submit" class="btn-primary" style="width:100%; border-radius:10px;" id="payBtn">Proceed to Checkout</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        const productsData = {{ products | tojson }};
        let cart = [];

        function revealElements() {
            var reveals = document.querySelectorAll(".reveal");
            for (var i = 0; i < reveals.length; i++) {
                var windowHeight = window.innerHeight;
                var elementTop = reveals[i].getBoundingClientRect().top;
                if (elementTop < windowHeight - 40) { reveals[i].classList.add("active"); }
            }
        }
        window.addEventListener("scroll", revealElements);
        setTimeout(revealElements, 100);

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('active');
            document.getElementById('sidebarOverlay').classList.toggle('active');
        }
        function switchSidebarView(v) {
            ['main','track','support','faq'].forEach(id => document.getElementById('sidebar-'+id+'-view').style.display = 'none');
            document.getElementById('sidebar-'+v+'-view').style.display = 'block';
        }

        function addToCartAndFly(event, id) {
            let p = productsData.find(x => x.id === id);
            cart.push(p); 
            updateCartUI();

            let img = document.getElementById('img-' + id);
            if(!img) return;
            let flyer = img.cloneNode(true);
            flyer.className = 'fly-item';
            
            let rect = img.getBoundingClientRect();
            flyer.style.top = rect.top + 'px';
            flyer.style.left = rect.left + 'px';
            document.body.appendChild(flyer);

            let targetRect = document.getElementById('cartTarget').getBoundingClientRect();
            setTimeout(() => {
                flyer.style.top = targetRect.top + 'px';
                flyer.style.left = targetRect.left + 'px';
                flyer.style.transform = 'scale(0.1)';
                flyer.style.opacity = '0';
            }, 50);

            setTimeout(() => { flyer.remove(); }, 850);
        }

        function buyNow(id) { 
            let p = productsData.find(x => x.id === id);
            if(p) { cart = [p]; updateCartUI(); openCartModal(); }
        }

        function openCartModal() { 
            document.getElementById('cartModal').style.display = 'flex'; 
            checkSavedAddressAvailability();
            updateCartUI(); 
        }

        function updateCartUI() {
            document.getElementById('cart-count').innerText = cart.length;
            let container = document.getElementById('cart-items-container');
            container.innerHTML = '';
            if(cart.length === 0) {
                container.innerHTML = '<p style="text-align:center; color:#888; margin:20px 0;">Your basket is empty.</p>';
                document.getElementById('checkout-section').style.display = 'none';
            } else {
                cart.forEach((item, index) => { 
                    container.innerHTML += `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:8px; font-size:13px;">
                        <div><b>${item.name}</b></div>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <span>₹${item.price}</span>
                            <i class="fa-solid fa-trash-can" style="color:#c62828; cursor:pointer;" onclick="removeFromCart(${index})"></i>
                        </div>
                    </div>`; 
                });
                document.getElementById('checkout-section').style.display = 'block';
                updateTotal();
            }
        }

        function removeFromCart(index) {
            cart.splice(index, 1);
            updateCartUI();
        }

        function updateTotal() {
            let base = cart.reduce((s, i) => s + i.price, 0);
            let mode = document.querySelector('input[name="pay_mode"]:checked').value;
            
            document.getElementById('bill-subtotal').innerText = `₹${base}`;
            let codFeeRow = document.getElementById('cod-fee-row');
            
            let total = base;
            if(mode === 'cod') {
                codFeeRow.style.display = 'flex';
                total += 99;
                document.getElementById('payBtn').innerText = 'Confirm Order (Cash on Delivery)';
            } else {
                codFeeRow.style.display = 'none';
                document.getElementById('payBtn').innerText = `Pay ₹${total} Now`;
            }
            document.getElementById('bill-total').innerText = `₹${total}`;
            return total;
        }

        function detectPinCode(pin) {
            if(pin.length === 6) {
                fetch(`https://api.postalpincode.in/pincode/${pin}`)
                .then(res => res.json())
                .then(data => {
                    if(data[0].Status === "Success") {
                        let postOffices = data[0].PostOffice;
                        document.getElementById('cust-city').value = postOffices[0].District;
                        document.getElementById('cust-state').value = postOffices[0].State;
                        
                        let landmarkSelect = document.getElementById('cust-landmark');
                        landmarkSelect.innerHTML = '<option value="">Select Landmark / Area (Optional)</option>';
                        postOffices.forEach(po => {
                            landmarkSelect.innerHTML += `<option value="${po.Name}">${po.Name}</option>`;
                        });
                    }
                })
                .catch(() => console.log("PIN code lookup unavailable"));
            }
        }

        function checkSavedAddressAvailability() {
            let saved = localStorage.getItem('kesh_saved_address');
            if(saved) {
                document.getElementById('useSavedAddrBtn').style.display = 'flex';
            }
        }

        function saveAddressToStorage(data) {
            localStorage.setItem('kesh_saved_address', JSON.stringify({
                name: data.name, email: data.email, phone: data.phone,
                pincode: data.pincode, city: data.city, state: data.state,
                landmark: data.landmark, street: data.street
            }));
        }

        function loadSavedAddress() {
            let saved = localStorage.getItem('kesh_saved_address');
            if(saved) {
                let d = JSON.parse(saved);
                document.getElementById('cust-name').value = d.name || '';
                document.getElementById('cust-email').value = d.email || '';
                document.getElementById('cust-phone').value = d.phone || '';
                document.getElementById('cust-pincode').value = d.pincode || '';
                document.getElementById('cust-city').value = d.city || '';
                document.getElementById('cust-state').value = d.state || '';
                document.getElementById('cust-street').value = d.street || '';
                if(d.pincode) detectPinCode(d.pincode);
            }
        }

        function placeOrder() {
            let name = document.getElementById('cust-name').value;
            let email = document.getElementById('cust-email').value;
            let phone = document.getElementById('cust-phone').value;
            let pincode = document.getElementById('cust-pincode').value;
            let city = document.getElementById('cust-city').value;
            let state = document.getElementById('cust-state').value;
            let landmark = document.getElementById('cust-landmark').value;
            let street = document.getElementById('cust-street').value;
            let mode = document.querySelector('input[name="pay_mode"]:checked').value;

            if(!name || !email || !phone || !pincode || !street) {
                return alert('Please fill in all required delivery fields.');
            }

            let amt = updateTotal();
            let payload = { name, email, phone, pincode, city, state, landmark, street, amount: amt, payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Payment', items: cart };

            saveAddressToStorage(payload);

            if(mode === 'online') {
                var options = {
                    "key": "rzp_live_TGzOHwqjwcYfov", 
                    "amount": amt * 100, 
                    "currency": "INR", 
                    "name": "KESH AADAR",
                    "description": "Botanical Products Order",
                    "handler": function (res) { 
                        payload.payment_id = res.razorpay_payment_id;
                        sendData(payload); 
                    },
                    "prefill": { "name": name, "email": email, "contact": phone }, 
                    "theme": { "color": "#1b4332" }
                };
                new Razorpay(options).open();
            } else { 
                payload.payment_id = 'COD';
                sendData(payload); 
            }
        }

        function sendData(payload) {
            document.getElementById('cartModal').style.display = 'none';
            fetch('/place_order', {
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(data => {
                window.location.href = '/order_success/' + data.order_id;
            });
        }

        function trackOrder() {
            let q = document.getElementById('track-input').value.trim();
            if(!q) return;
            fetch('/track_order?q=' + encodeURIComponent(q)).then(r => r.json()).then(data => {
                let d = document.getElementById('track-result');
                if(data.found) {
                    let statusColor = data.order.status === 'Delivered' ? '#2e7d32' : '#d4a373';
                    d.innerHTML = `<div style="background:#e8f5e9; padding:12px; border-radius:8px; font-size:13px;"><h4 style="color:#2e7d32;">Order: ${data.order.order_id}</h4><p>Status: <b style="color:${statusColor}">${data.order.status}</b></p></div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- ENHANCED ORDER SUCCESS TEMPLATE ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmed | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }

        @keyframes successPop { 0% { transform: scale(0.4) rotate(-10deg); opacity: 0; } 70% { transform: scale(1.15) rotate(5deg); opacity: 1; } 100% { transform: scale(1) rotate(0deg); opacity: 1; } }
        @keyframes pulseRing { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.5); } 70% { box-shadow: 0 0 0 30px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

        .card { background: white; max-width: 580px; width: 100%; padding: 45px 35px; border-radius: 24px; box-shadow: 0 25px 50px rgba(27,67,50,0.1); text-align: center; animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .icon-box { font-size: 45px; color: white; background: #2e7d32; border-radius: 50%; width: 95px; height: 95px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 25px; animation: successPop 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards, pulseRing 2s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 34px; margin-bottom: 8px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 22px; border-radius: 12px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; color: #444; }

        /* Timeline Tracker on Success Page */
        .tracker-steps { display: flex; justify-content: space-between; position: relative; margin: 25px 0; padding: 0 10px; }
        .tracker-steps::before { content: ''; position: absolute; top: 14px; left: 30px; right: 30px; height: 3px; background: #ddd; z-index: 1; }
        .step { position: relative; z-index: 2; text-align: center; }
        .step-icon { width: 30px; height: 30px; border-radius: 50%; background: #ddd; color: white; display: flex; align-items: center; justify-content: center; font-size: 11px; margin: 0 auto 6px auto; transition: background 0.3s; }
        .step.active .step-icon { background: #2e7d32; }
        .step span { font-size: 11px; color: #666; font-weight: 500; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; transition: background 0.2s, transform 0.2s; }
        .btn-home:hover { background: #2d6a4f; transform: translateY(-2px); }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Confirmed!</h1>
        <p class="subtitle">Thank you for choosing Kesh Aadar. Your order has been registered.</p>

        {% if order %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Total Amount:</span><b>₹{{ order.amount }}</b></div>
            <div class="info-row"><span>Payment Mode:</span><b>{{ order.payment_type }}</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 260px; text-align: right;">{{ order.full_address }}</span></div>
        </div>

        {% set status = order.status %}
        <div class="tracker-steps">
            <div class="step {% if status in ['Processing', 'Packaging', 'Shipped', 'Delivered'] %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-clipboard-list"></i></div>
                <span>Processing</span>
            </div>
            <div class="step {% if status in ['Packaging', 'Shipped', 'Delivered'] %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-box"></i></div>
                <span>Packaging</span>
            </div>
            <div class="step {% if status in ['Shipped', 'Delivered'] %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-truck"></i></div>
                <span>Shipped</span>
            </div>
            <div class="step {% if status == 'Delivered' %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-house-chimney"></i></div>
                <span>Delivered</span>
            </div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 20px;"><i class="fa-solid fa-envelope"></i> Confirmation & tracking details sent to your registered email.</p>
        
        <a href="/" class="btn-home">Continue Shopping</a>
    </div>

</body>
</html>
"""

# --- ADMIN PANEL TEMPLATE (/admin) ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); display: flex; min-height: 100vh; }

        /* Admin Sidebar */
        .admin-sidebar { width: 280px; background: var(--green-primary); color: white; padding: 30px 20px; position: fixed; height: 100%; transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1); z-index: 1000; }
        .admin-sidebar.closed { transform: translateX(-280px); }
        .admin-brand { font-family: 'Playfair Display', serif; font-size: 22px; color: var(--accent-gold); margin-bottom: 35px; display: flex; align-items: center; justify-content: space-between; }
        .admin-menu-btn { background: none; border: none; color: white; font-size: 20px; cursor: pointer; }
        .admin-nav-item { padding: 12px 15px; border-radius: 8px; cursor: pointer; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 500; transition: background 0.2s; color: #ddd; text-decoration: none; }
        .admin-nav-item:hover, .admin-nav-item.active { background: rgba(255,255,255,0.1); color: white; }
        .admin-nav-item i { color: var(--accent-gold); width: 20px; }

        /* Toggle Button when sidebar closed */
        .open-sidebar-floating { position: fixed; top: 20px; left: 20px; z-index: 999; background: var(--green-primary); color: white; border: none; width: 45px; height: 45px; border-radius: 50%; font-size: 18px; cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,0.2); display: none; align-items: center; justify-content: center; }

        /* Main Content Area */
        .admin-content { margin-left: 280px; flex: 1; padding: 40px; transition: margin-left 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
        .admin-content.expanded { margin-left: 0; }

        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 28px; margin-bottom: 25px; }
        .card { background: white; border-radius: 16px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); margin-bottom: 25px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); font-weight: 600; }
        
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge.live { background: #e8f5e9; color: #2e7d32; }
        .badge.suspended { background: #ffebee; color: #c62828; }

        .btn { padding: 8px 16px; border-radius: 8px; border: none; font-weight: 600; cursor: pointer; font-size: 12px; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.85; }
        .btn-green { background: var(--green-primary); color: white; }
        .btn-red { background: #c62828; color: white; }
        .btn-gold { background: var(--accent-gold); color: white; }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: var(--green-primary); }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }

        .tab-section { display: none; }
        .tab-section.active { display: block; }

        @media(max-width: 900px) {
            .admin-sidebar { transform: translateX(-280px); }
            .admin-sidebar.mobile-open { transform: translateX(0); }
            .admin-content { margin-left: 0; padding: 20px; }
            .open-sidebar-floating { display: flex; }
        }
    </style>
</head>
<body>

    <button class="open-sidebar-floating" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>

    <!-- Admin Sidebar -->
    <div class="admin-sidebar" id="adminSidebar">
        <div class="admin-brand">
            <span>Kesh Admin</span>
            <button class="admin-menu-btn" onclick="toggleAdminSidebar()"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div class="admin-nav-item active" onclick="switchTab('orders', this)"><i class="fa-solid fa-box-open"></i> Orders Management</div>
        <div class="admin-nav-item" onclick="switchTab('products', this)"><i class="fa-solid fa-tags"></i> Products & Inventory</div>
        <div class="admin-nav-item" onclick="switchTab('logo', this)"><i class="fa-solid fa-image"></i> Store Logo</div>
        <a href="/" class="admin-nav-item" style="margin-top: 30px;"><i class="fa-solid fa-store"></i> View Storefront</a>
    </div>

    <!-- Admin Content -->
    <div class="admin-content" id="adminContent">
        
        <!-- ORDERS TAB -->
        <div id="tab-orders" class="tab-section active">
            <h1>Customer Orders</h1>
            <div class="card">
                <div style="overflow-x:auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Customer Details</th>
                                <th>Items & Amount</th>
                                <th>Address</th>
                                <th>Status Update</th>
                            </tr>
                        </thead>
                        <tbody id="orders-table-body">
                            <!-- Populated via JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- PRODUCTS TAB -->
        <div id="tab-products" class="tab-section">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px;">
                <h1>Products & Inventory</h1>
                <button class="btn btn-green" onclick="openProductModal()"><i class="fa-solid fa-plus"></i> Add New Product</button>
            </div>
            <div class="card">
                <div style="overflow-x:auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Image</th>
                                <th>Product Name</th>
                                <th>Category</th>
                                <th>Price</th>
                                <th>Stock</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="products-table-body">
                            <!-- Populated via JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- LOGO TAB -->
        <div id="tab-logo" class="tab-section">
            <h1>Store Logo Management</h1>
            <div class="card" style="max-width: 500px;">
                <div style="text-align:center; margin-bottom:20px;">
                    <img id="current-logo-preview" src="{{ store.logo }}" style="width:100px; height:100px; object-fit:cover; border-radius:50%; border:3px solid var(--accent-gold);">
                </div>
                <div class="form-group">
                    <label>Logo Image URL</label>
                    <input type="text" id="logo-url-input" value="{{ store.logo }}" placeholder="Paste image URL here">
                </div>
                <div class="form-group">
                    <label>Or Upload Image (Drag & Drop or Select file)</label>
                    <input type="file" id="logo-file-input" accept="image/*" onchange="convertLogoFile(this)">
                </div>
                <button class="btn btn-green" style="width:100%; margin-top:10px;" onclick="updateStoreLogo()">Save Logo</button>
            </div>
        </div>

    </div>

    <!-- Product Modal (Add/Edit) -->
    <div class="modal" id="productModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); z-index:3000; align-items:center; justify-content:center;">
        <div style="background:white; max-width:500px; width:100%; padding:30px; border-radius:16px; position:relative;">
            <span onclick="closeProductModal()" style="position:absolute; right:20px; top:20px; cursor:pointer; font-size:22px;">&times;</span>
            <h3 id="modal-title" style="color:var(--green-primary); margin-bottom:20px;">Add New Product</h3>
            <input type="hidden" id="edit-prod-id">
            <div class="form-group">
                <label>Product Name</label>
                <input type="text" id="prod-name" placeholder="e.g. Herbal Hair Oil">
            </div>
            <div class="form-group">
                <label>Category</label>
                <input type="text" id="prod-category" placeholder="e.g. Haircare">
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div class="form-group">
                    <label>Price (₹)</label>
                    <input type="number" id="prod-price" placeholder="499">
                </div>
                <div class="form-group">
                    <label>Stock Quantity</label>
                    <input type="number" id="prod-stock" placeholder="50">
                </div>
            </div>
            <div class="form-group">
                <label>Image URL</label>
                <input type="text" id="prod-image" placeholder="https://images.unsplash.com/...">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea id="prod-desc" rows="2" placeholder="Short description..."></textarea>
            </div>
            <button class="btn btn-green" style="width:100%; padding:12px;" onclick="saveProductData()">Save Product</button>
        </div>
    </div>

    <script>
        let storeData = {{ store | tojson }};

        function toggleAdminSidebar() {
            let sidebar = document.getElementById('adminSidebar');
            let content = document.getElementById('adminContent');
            sidebar.classList.toggle('closed');
            sidebar.classList.toggle('mobile-open');
            content.classList.toggle('expanded');
        }

        function switchTab(tabId, el) {
            document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.admin-nav-item').forEach(i => i.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            if(el) el.classList.add('active');
        }

        function renderOrders() {
            let tbody = document.getElementById('orders-table-body');
            tbody.innerHTML = '';
            if(!storeData.orders || storeData.orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#888;">No orders received yet.</td></tr>';
                return;
            }
            storeData.orders.forEach(o => {
                let itemsList = o.items.map(i => `<li>${i.name} (₹${i.price})</li>`).join('');
                tbody.innerHTML += `
                <tr>
                    <td><b>${o.order_id}</b><br><small style="color:#666;">${o.date}</small></td>
                    <td><b>${o.name}</b><br>${o.phone}<br><small>${o.email}</small></td>
                    <td><ul style="padding-left:15px; margin-bottom:5px;">${itemsList}</ul><b>Total: ₹${o.amount}</b> (${o.payment_type})</td>
                    <td><small>${o.full_address}</small></td>
                    <td>
                        <select onchange="updateOrderStatus('${o.order_id}', this.value)" style="padding:6px; border-radius:6px; font-size:12px; border:1px solid #ddd;">
                            <option value="Processing" ${o.status==='Processing'?'selected':''}>Processing</option>
                            <option value="Packaging" ${o.status==='Packaging'?'selected':''}>Packaging</option>
                            <option value="Shipped" ${o.status==='Shipped'?'selected':''}>Shipped</option>
                            <option value="Delivered" ${o.status==='Delivered'?'selected':''}>Delivered</option>
                        </select>
                    </td>
                </tr>`;
            });
        }

        function updateOrderStatus(orderId, newStatus) {
            fetch('/api/admin/update_order_status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({order_id: orderId, status: newStatus})
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    let ord = storeData.orders.find(x => x.order_id === orderId);
                    if(ord) ord.status = newStatus;
                }
            });
        }

        function renderProducts() {
            let tbody = document.getElementById('products-table-body');
            tbody.innerHTML = '';
            storeData.products.forEach(p => {
                let isLive = (p.status || 'live') === 'live';
                tbody.innerHTML += `
                <tr>
                    <td><img src="${p.image}" style="width:45px; height:45px; object-fit:cover; border-radius:8px;"></td>
                    <td><b>${p.name}</b></td>
                    <td>${p.category || 'General'}</td>
                    <td>₹${p.price}</td>
                    <td>${p.stock}</td>
                    <td><span class="badge ${isLive ? 'live' : 'suspended'}">${isLive ? 'Live' : 'Suspended'}</span></td>
                    <td>
                        <button class="btn btn-gold" onclick="editProduct(${p.id})"><i class="fa-solid fa-pen"></i></button>
                        <button class="btn ${isLive ? 'btn-red' : 'btn-green'}" onclick="toggleSuspend(${p.id})">${isLive ? 'Suspend' : 'Make Live'}</button>
                        <button class="btn btn-red" onclick="deleteProduct(${p.id})"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>`;
            });
        }

        function openProductModal(id = null) {
            document.getElementById('productModal').style.display = 'flex';
            if(id) {
                let p = storeData.products.find(x => x.id === id);
                document.getElementById('modal-title').innerText = 'Edit Product';
                document.getElementById('edit-prod-id').value = p.id;
                document.getElementById('prod-name').value = p.name;
                document.getElementById('prod-category').value = p.category || '';
                document.getElementById('prod-price').value = p.price;
                document.getElementById('prod-stock').value = p.stock;
                document.getElementById('prod-image').value = p.image;
                document.getElementById('prod-desc').value = p.desc || '';
            } else {
                document.getElementById('modal-title').innerText = 'Add New Product';
                document.getElementById('edit-prod-id').value = '';
                document.getElementById('prod-name').value = '';
                document.getElementById('prod-category').value = '';
                document.getElementById('prod-price').value = '';
                document.getElementById('prod-stock').value = '';
                document.getElementById('prod-image').value = '';
                document.getElementById('prod-desc').value = '';
            }
        }

        function closeProductModal() {
            document.getElementById('productModal').style.display = 'none';
        }

        function saveProductData() {
            let id = document.getElementById('edit-prod-id').value;
            let payload = {
                name: document.getElementById('prod-name').value,
                category: document.getElementById('prod-category').value,
                price: document.getElementById('prod-price').value,
                stock: document.getElementById('prod-stock').value,
                image: document.getElementById('prod-image').value,
                desc: document.getElementById('prod-desc').value
            };

            let method = id ? 'PUT' : 'POST';
            if(id) payload.id = parseInt(id);

            fetch('/api/admin/products', {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(res => {
                location.reload();
            });
        }

        function editProduct(id) {
            openProductModal(id);
        }

        function toggleSuspend(id) {
            let p = storeData.products.find(x => x.id === id);
            let newStatus = (p.status || 'live') === 'live' ? 'suspended' : 'live';
            fetch('/api/admin/products', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id, status: newStatus})
            }).then(() => location.reload());
        }

        function deleteProduct(id) {
            if(confirm('Are you sure you want to delete this product?')) {
                fetch('/api/admin/products', {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: id})
                }).then(() => location.reload());
            }
        }

        function convertLogoFile(input) {
            if(input.files && input.files[0]) {
                let reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('logo-url-input').value = e.target.result;
                    document.getElementById('current-logo-preview').src = e.target.result;
                }
                reader.readAsDataURL(input.files[0]);
            }
        }

        function updateStoreLogo() {
            let logo = document.getElementById('logo-url-input').value;
            fetch('/api/admin/logo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({logo: logo})
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    alert('Logo updated successfully!');
                    location.reload();
                }
            });
        }

        renderOrders();
        renderProducts();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Kesh Aadar Flask Server Running...")
    app.run(host='0.0.0.0', port=5000, debug=True)
