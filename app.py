from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import random

app = Flask(__name__)
app.secret_key = 'kesh_aadar_secure_key_2026'

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "subhraroy324@gmail.com"
SMTP_PASS = "idxv jjob guit vtfb"

# --- PERSISTENT STORAGE FOR VERCEL (/tmp) ---
DATA_DIR = "/tmp"
PRODUCTS_FILE = os.path.join(DATA_DIR, "products.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

DEFAULT_PRODUCTS = [
    {"id": 1, "name": "Aloe Neem Glow Face Wash", "category": "Skincare", "price": 349, "stock": 50, "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", "desc": "Deep cleansing herbal formula for radiant skin.", "status": "active"},
    {"id": 2, "name": "Saffron Kumkumadi Night Serum", "category": "Skincare", "price": 799, "stock": 30, "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", "desc": "Fades blemishes and restores natural skin glow.", "status": "active"},
    {"id": 3, "name": "Bhringraj Onion Hair Growth Oil", "category": "Haircare", "price": 499, "stock": 40, "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", "desc": "Stops hair fall and stimulates roots naturally.", "status": "active"},
    {"id": 4, "name": "Hibiscus & Shikakai Herbal Shampoo", "category": "Haircare", "price": 399, "stock": 45, "image": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80", "desc": "Nourishing sulfate-free cleanser for smooth hair.", "status": "active"}
]

def load_json(filepath, default):
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(filepath, data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

def get_products():
    return load_json(PRODUCTS_FILE, DEFAULT_PRODUCTS)

def save_products(prods):
    save_json(PRODUCTS_FILE, prods)

def get_orders():
    return load_json(ORDERS_FILE, [])

def save_orders(ords):
    save_json(ORDERS_FILE, ords)

def get_config():
    return load_json(CONFIG_FILE, {"logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80"})

def save_config(cfg):
    save_json(CONFIG_FILE, cfg)

BLACKLISTED_IPS = []

# --- BACKGROUND EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, payment_type):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li style='margin-bottom: 8px;'><b>{i['name']}</b> (₹{i['price']})</li>" for i in items])
        track_url = f"https://kesh-aadar.vercel.app/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 15px 35px rgba(27,67,50,0.08); text-align: left;">
                <h1 style="font-size: 32px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center; font-family: 'Playfair Display', serif;">KESH AADAR</h1>
                <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">Pure Botanical Remedies</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <h2 style="color: #1b4332; font-size: 22px;">Thank you for your order, {name}!</h2>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">Your order has been placed successfully and is currently being prepared for dispatch.</p>
                
                <div style="background: linear-gradient(135deg, #FAF7F0 0%, #F3EFEA 100%); padding: 25px; border-radius: 14px; margin: 25px 0; border: 1px dashed #d4a373;">
                    <p style="margin: 0; color: #666; font-size: 11px; text-transform: uppercase; font-weight: bold;">Order Reference ID</p>
                    <h3 style="margin: 8px 0; font-size: 26px; color: #1b4332; font-family: monospace;">{order_id}</h3>
                    <p style="margin: 8px 0 4px 0; color: #333; font-size: 14px; font-weight: 600;">Total Bill: ₹{amount} ({payment_type})</p>
                    <p style="margin: 4px 0 0 0; color: #555; font-size: 13px;"><b>Shipping Address:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px; font-size: 15px;">Items Ordered:</h4>
                <ul style="font-size: 13px; color: #444; padding-left: 20px; line-height: 1.7;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 35px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 32px; border-radius: 30px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 6px 20px rgba(27, 67, 50, 0.3);">Track Live Order Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 35px 0 15px 0;">
                <p style="font-size: 11px; color: #888; text-align: center;">Need assistance? Contact support at subhraroy324@gmail.com | +91 9163641507</p>
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
        print(f"Confirmation email successfully delivered to {recipient_email}")
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
    client_ip = request.remote_addr
    if client_ip in BLACKLISTED_IPS:
        return jsonify({"error": "Your IP has been blacklisted by administrator."}), 403

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    prods = [p for p in get_products() if p.get('status', 'active') == 'active']
    config = get_config()
    return render_template_string(TEMPLATE, products=prods, config=config)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status_step'] = 1  # 1: Placed, 2: Packaging, 3: Shipped, 4: Delivered
    data['status_text'] = "Order Placed"
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', 'N/A')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    orders = get_orders()
    orders.insert(0, data)
    save_orders(orders)
    
    # Send email in background thread
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, data['payment_type'])
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    orders = get_orders()
    order = next((o for o in orders if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id)

@app.route('/track_order')
def track_order():
    q = request.args.get('q', '').strip()
    orders = get_orders()
    for o in orders:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order": o})
    return jsonify({"found": False})

# --- ADMIN PANEL ROUTE ---
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE)

@app.route('/api/admin/data')
def admin_data():
    return jsonify({
        "products": get_products(),
        "orders": get_orders(),
        "config": get_config()
    })

@app.route('/api/admin/order_status', methods=['POST'])
def admin_update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    step = int(data.get('step', 1))
    status_texts = {1: "Order Placed", 2: "Packaging", 3: "Shipped", 4: "Delivered"}
    
    orders = get_orders()
    for o in orders:
        if o['order_id'] == order_id:
            o['status_step'] = step
            o['status_text'] = status_texts.get(step, "Processing")
            break
    save_orders(orders)
    return jsonify({"status": "success", "orders": orders})

@app.route('/api/admin/products', methods=['POST', 'PUT', 'DELETE'])
def admin_manage_products():
    prods = get_products()
    data = request.get_json()
    
    if request.method == 'POST':
        new_id = max([p['id'] for p in prods], default=0) + 1
        new_prod = {
            "id": new_id,
            "name": data.get('name'),
            "category": data.get('category', 'Skincare'),
            "price": float(data.get('price', 0)),
            "stock": int(data.get('stock', 10)),
            "image": data.get('image', 'https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80'),
            "desc": data.get('desc', ''),
            "status": "active"
        }
        prods.append(new_prod)
    elif request.method == 'PUT':
        prod_id = int(data.get('id'))
        for p in prods:
            if p['id'] == prod_id:
                p['name'] = data.get('name', p['name'])
                p['category'] = data.get('category', p['category'])
                p['price'] = float(data.get('price', p['price']))
                p['stock'] = int(data.get('stock', p['stock']))
                p['desc'] = data.get('desc', p['desc'])
                if 'image' in data and data['image']:
                    p['image'] = data['image']
                if 'status' in data:
                    p['status'] = data['status']
                break
    elif request.method == 'DELETE':
        prod_id = int(data.get('id'))
        prods = [p for p in prods if p['id'] != prod_id]
        
    save_products(prods)
    return jsonify({"status": "success", "products": prods})

@app.route('/api/admin/config', methods=['POST'])
def admin_update_config():
    data = request.get_json()
    config = get_config()
    if 'logo' in data:
        config['logo'] = data['logo']
    save_config(config)
    return jsonify({"status": "success", "config": config})


# --- PUBLIC FRONTEND TEMPLATE ---
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

        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 18px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.05); }
        .nav-left { display: flex; align-items: center; gap: 18px; }
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; transition: 0.3s; }
        .menu-btn:hover { color: var(--accent-gold); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: 0.3s; }
        .cart-icon-container:hover { background: var(--green-primary); color: white; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Smooth Animated Sidebar Drawer */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.77, 0, 0.175, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; font-family: 'Playfair Display', serif; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; font-size: 12px; font-weight: 600; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); transition: 0.2s; }
        .close-sidebar:hover { color: var(--green-light); }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); transition: 0.2s; }
        .support-card:hover { transform: translateX(3px); }

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
        .btn-cart { flex: 1; padding: 10px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-cart:hover { background: #e5dfd5; }
        .btn-buy { flex: 1; padding: 10px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-buy:hover { background: var(--green-light); }

        /* Flying Cart Animation */
        .fly-item { position: fixed; z-index: 9999; width: 50px; height: 50px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); transition: all 0.8s cubic-bezier(0.2, 1, 0.3, 1); pointer-events: none; }

        /* Modal */
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); display: none; justify-content: center; align-items: center; z-index: 3000; padding: 15px; }
        .modal-content { background: white; width: 100%; max-width: 520px; padding: 30px; border-radius: 20px; max-height: 90vh; overflow-y: auto; position: relative; }
        
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
        .social-icons a { color: white; font-size: 18px; background: rgba(255,255,255,0.1); width: 38px; height: 38px; display: flex; justify-content: center; align-items: center; border-radius: 50%; text-decoration: none; transition: 0.3s; }
        .social-icons a:hover { background: var(--accent-gold); }
        .footer-bottom { padding-top: 20px; font-size: 12px; color: #aaa; text-align: center; }
    </style>
</head>
<body>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
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
            <a href="mailto:subhraroy324@gmail.com" class="support-card"><i class="fa-solid fa-envelope" style="color: var(--accent-gold); font-size:18px;"></i><div><h4 style="font-size: 13px; color: var(--green-primary);">Email Support</h4><p style="font-size: 11px; color: #555;">subhraroy324@gmail.com</p></div></a>
            <a href="tel:9163641507" class="support-card"><i class="fa-solid fa-phone-volume" style="color: var(--green-primary); font-size:18px;"></i><div><h4 style="font-size: 13px; color: var(--green-primary);">Call Support</h4><p style="font-size: 11px; color: #555;">+91 9163641507</p></div></a>
            <a href="https://wa.me/919163641507" target="_blank" class="support-card" style="background: #e8f5e9;"><i class="fa-brands fa-whatsapp" style="color: #2e7d32; font-size: 20px;"></i><div><h4 style="font-size: 13px; color: #2e7d32;">WhatsApp Support</h4><p style="font-size: 11px; color: #555;">Instant messaging</p></div></a>
        </div>

        <div id="sidebar-faq-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>FAQs</h3>
            <h4 style="font-size: 13px; color: var(--green-primary); margin-top:10px;">1. Estimated dispatch time?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Orders are dispatched within 24-48 hours.</p>
            <h4 style="font-size: 13px; color: var(--green-primary);">2. How do I track delivery?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Use the tracking tool with your Order ID or Email.</p>
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
            <h3 style="color:var(--green-primary); margin-bottom:15px; font-family:'Playfair Display';">Your Shopping Basket</h3>
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
                            <input type="radio" name="pay_mode" value="online" checked> Online Payment (Razorpay)
                        </label>
                        <label style="display:flex; align-items:center; gap:10px; padding:10px; border:1px solid #ddd; border-radius:8px; cursor:pointer;" onclick="updateTotal()">
                            <input type="radio" name="pay_mode" value="cod"> Cash on Delivery (+₹99 Fee)
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

        // Flying Cart Animation
        function addToCartAndFly(event, id) {
            let p = productsData.find(x => x.id === id);
            cart.push(p); 
            updateCartUI();

            let img = document.getElementById('img-' + id);
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
            cart = [productsData.find(x => x.id === id)]; 
            updateCartUI(); 
            openCartModal(); 
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
                    } else {
                        alert("Invalid PIN Code entered.");
                    }
                })
                .catch(() => console.log("PIN lookup offline"));
            }
        }

        function checkSavedAddressAvailability() {
            let saved = localStorage.getItem('kesh_saved_address');
            if(saved) { document.getElementById('useSavedAddrBtn').style.display = 'flex'; }
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
            let payload = { 
                name, email, phone, pincode, city, state, landmark, street, 
                amount: amt, payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Payment (Razorpay)', 
                items: cart 
            };

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
                    d.innerHTML = `<div style="background:#e8f5e9; padding:12px; border-radius:8px; font-size:13px; margin-top:10px;"><h4 style="color:#2e7d32;">Found: ${data.order.order_id}</h4><p>Status: ${data.order.status_text}</p><a href="/order_success/${data.order.order_id}" style="color:var(--green-primary); font-weight:600; display:inline-block; margin-top:6px;">View Full Tracking &rarr;</a></div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px; margin-top:10px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- DEDICATED ORDER SUCCESS & LIVE TRACKING TEMPLATE ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Status & Tracking | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 25px; }

        @keyframes popIn { 0% { transform: scale(0.3); opacity: 0; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); } 70% { box-shadow: 0 0 0 25px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }

        .card { background: white; max-width: 620px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 45px; color: white; background: #2e7d32; border-radius: 50%; width: 85px; height: 85px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 30px; margin-bottom: 6px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        /* Amazon/Flipkart Style Tracker Line */
        .tracker-container { margin: 30px 0; padding: 20px 10px; background: #FAF7F0; border-radius: 14px; border: 1px solid #EAE5D9; }
        .track-steps { display: flex; justify-content: space-between; position: relative; margin: 0 20px; }
        .track-steps::before { content: ''; position: absolute; top: 15px; left: 10px; right: 10px; height: 3px; background: #ddd; z-index: 1; }
        .progress-line { position: absolute; top: 15px; left: 10px; height: 3px; background: #2e7d32; z-index: 2; transition: width 0.6s ease; }
        
        .step { position: relative; z-index: 3; text-align: center; }
        .step-icon { width: 34px; height: 34px; border-radius: 50%; background: #ddd; color: white; display: flex; align-items: center; justify-content: center; font-size: 13px; margin: 0 auto 8px auto; transition: 0.3s; }
        .step.active .step-icon { background: #2e7d32; box-shadow: 0 0 10px rgba(46,125,50,0.4); }
        .step.completed .step-icon { background: #2e7d32; }
        .step span { font-size: 11px; font-weight: 600; color: #666; display: block; }
        .step.active span { color: #2e7d32; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; transition: 0.3s; }
        .btn-home:hover { background: var(--green-light); }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Status & Tracking</h1>
        <p class="subtitle">Thank you for choosing Kesh Aadar.</p>

        {% if order %}
        {% set step = order.get('status_step', 1) %}
        <div class="tracker-container">
            <h4 style="font-size: 14px; color: var(--green-primary); margin-bottom: 15px;">Live Progress: <b>{{ order.get('status_text', 'Order Placed') }}</b></h4>
            <div class="track-steps">
                <div class="progress-line" id="progLine" style="width: {% if step == 1 %}0%{% elif step == 2 %}33%{% elif step == 3 %}66%{% else %}100%{% endif %};"></div>
                
                <div class="step {% if step >= 1 %}completed {% endif %}{% if step == 1 %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-clipboard-list"></i></div>
                    <span>Placed</span>
                </div>
                <div class="step {% if step >= 2 %}completed {% endif %}{% if step == 2 %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-box-open"></i></div>
                    <span>Packaging</span>
                </div>
                <div class="step {% if step >= 3 %}completed {% endif %}{% if step == 3 %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-truck-fast"></i></div>
                    <span>Shipped</span>
                </div>
                <div class="step {% if step >= 4 %}completed {% endif %}{% if step == 4 %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-house-chimney"></i></div>
                    <span>Delivered</span>
                </div>
            </div>
        </div>

        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Phone Number:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Email:</span><b>{{ order.email }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color: #2e7d32;">{{ order.payment_type }} (Paid)</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 260px; text-align: right;">{{ order.full_address }}</span></div>
            
            <div style="border-top: 1px solid #ddd; margin: 12px 0 8px 0; padding-top: 8px;">
                <p style="font-size: 12px; font-weight: bold; color: var(--green-primary); margin-bottom: 5px;">Items Ordered:</p>
                {% for item in order.items %}
                <div class="info-row"><span>{{ item.name }}</span><span>₹{{ item.price }}</span></div>
                {% endfor %}
            </div>
            
            <div style="border-top: 1px dashed #d4a373; margin-top: 8px; padding-top: 8px;" class="info-row">
                <span style="font-weight: bold; color: var(--green-primary);">Total Bill (Incl. GST & Shipping):</span>
                <b style="font-size: 15px; color: var(--green-primary);">₹{{ order.amount }}</b>
            </div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
            <p style="font-size: 13px; color: red; margin-top: 10px;">Order details could not be retrieved or are still syncing.</p>
        </div>
        {% endif %}

        <p style="font-size: 11px; color: #888; margin-bottom: 20px;"><i class="fa-solid fa-envelope"></i> Confirmation & tracking details sent to your registered email.</p>
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
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); display: flex; min-height: 100vh; }

        /* Admin Sidebar */
        .admin-sidebar { width: 280px; background: var(--green-primary); color: white; padding: 25px 20px; display: flex; flex-direction: column; justify-content: space-between; position: fixed; height: 100vh; left: 0; top: 0; transition: transform 0.4s ease; z-index: 100; }
        .admin-brand { font-family: 'Playfair Display', serif; font-size: 22px; color: white; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; }
        .close-admin-sidebar { font-size: 22px; cursor: pointer; display: none; }
        
        .admin-nav { display: flex; flex-direction: column; gap: 10px; flex-grow: 1; }
        .admin-nav-btn { background: rgba(255,255,255,0.08); color: white; border: none; padding: 12px 16px; border-radius: 8px; text-align: left; cursor: pointer; font-weight: 500; font-size: 14px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .admin-nav-btn:hover, .admin-nav-btn.active { background: var(--accent-gold); color: var(--green-primary); font-weight: 600; }
        
        /* Main Admin Content */
        .admin-main { margin-left: 280px; flex-grow: 1; padding: 40px; max-width: calc(100vw - 280px); }
        .admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 35px; border-bottom: 1px solid #ddd; padding-bottom: 15px; }
        .admin-header h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 26px; }

        .dashboard-card { background: white; padding: 25px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); margin-bottom: 30px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); font-weight: 600; }

        .badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge.active { background: #e8f5e9; color: #2e7d32; }
        .badge.suspended { background: #ffebee; color: #c62828; }

        .btn { padding: 8px 14px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; font-size: 12px; transition: 0.2s; }
        .btn-green { background: var(--green-primary); color: white; }
        .btn-green:hover { background: var(--green-light); }
        .btn-red { background: #c62828; color: white; }
        .btn-gold { background: var(--accent-gold); color: white; }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; color: var(--green-primary); margin-bottom: 6px; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; }

        .toggle-sidebar-mob { display: none; font-size: 22px; cursor: pointer; color: var(--green-primary); background: none; border: none; }

        @media(max-width: 900px) {
            .admin-sidebar { transform: translateX(-280px); }
            .admin-sidebar.active { transform: translateX(0); }
            .admin-main { margin-left: 0; max-width: 100%; padding: 20px; }
            .toggle-sidebar-mob { display: block; }
            .close-admin-sidebar { display: block; }
        }
    </style>
</head>
<body>

    <!-- Admin Sidebar -->
    <div class="admin-sidebar" id="adminSidebar">
        <div>
            <div class="admin-brand">
                <span>KESH ADMIN</span>
                <span class="close-admin-sidebar" onclick="toggleAdminSidebar()">&times;</span>
            </div>
            <div class="admin-nav">
                <button class="admin-nav-btn active" onclick="switchTab('orders')"><i class="fa-solid fa-box-archive"></i> Customer Orders</button>
                <button class="admin-nav-btn" onclick="switchTab('inventory')"><i class="fa-solid fa-boxes-stacked"></i> Product Inventory</button>
                <button class="admin-nav-btn" onclick="switchTab('settings')"><i class="fa-solid fa-gear"></i> Store Settings & Logo</button>
            </div>
        </div>
        <div>
            <a href="/" class="admin-nav-btn" style="text-decoration:none; text-align:center; justify-content:center; background:rgba(255,255,255,0.15);"><i class="fa-solid fa-store"></i> Visit Live Store</a>
        </div>
    </div>

    <!-- Main Admin Area -->
    <div class="admin-main">
        <div class="admin-header">
            <div style="display:flex; align-items:center; gap:15px;">
                <button class="toggle-sidebar-mob" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
                <h1 id="pageTitle">Customer Orders</h1>
            </div>
            <span style="font-size: 13px; color: #666;">Admin Dashboard v2.6</span>
        </div>

        <!-- Orders Tab -->
        <div id="tab-orders" class="admin-tab-content">
            <div class="dashboard-card">
                <h3 style="color:var(--green-primary); margin-bottom:15px;">Manage Incoming Orders</h3>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Order ID & Date</th>
                                <th>Customer Details</th>
                                <th>Shipping Address</th>
                                <th>Items & Amount</th>
                                <th>Status Control</th>
                            </tr>
                        </thead>
                        <tbody id="ordersTableBody">
                            <tr><td colspan="5" style="text-align:center; color:#888;">Loading orders...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Inventory Tab -->
        <div id="tab-inventory" class="admin-tab-content" style="display:none;">
            <div class="dashboard-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                    <h3 style="color:var(--green-primary);">Product Inventory Management</h3>
                    <button class="btn btn-green" onclick="openAddProductModal()"><i class="fa-solid fa-plus"></i> Add New Product</button>
                </div>
                <div style="overflow-x: auto;">
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
                        <tbody id="inventoryTableBody">
                            <tr><td colspan="7" style="text-align:center; color:#888;">Loading inventory...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Settings Tab -->
        <div id="tab-settings" class="admin-tab-content" style="display:none;">
            <div class="dashboard-card" style="max-width: 600px;">
                <h3 style="color:var(--green-primary); margin-bottom:20px;">Store Branding & Logo</h3>
                <form onsubmit="event.preventDefault(); updateConfig();">
                    <div class="form-group">
                        <label>Store Logo Image URL</label>
                        <input type="text" id="configLogoInput" placeholder="https://image-url.com/logo.jpg">
                    </div>
                    <button type="submit" class="btn btn-green">Save Settings</button>
                </form>
            </div>
        </div>
    </div>

    <!-- Add/Edit Product Modal -->
    <div id="productModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); z-index:2000; justify-content:center; align-items:center;">
        <div style="background:white; width:100%; max-width:500px; padding:30px; border-radius:16px; position:relative;">
            <span onclick="document.getElementById('productModal').style.display='none'" style="position:absolute; right:20px; top:20px; cursor:pointer; font-size:22px;">&times;</span>
            <h3 id="modalProdTitle" style="color:var(--green-primary); margin-bottom:20px;">Add New Product</h3>
            <form onsubmit="event.preventDefault(); saveProductForm();">
                <input type="hidden" id="editProdId">
                <div class="form-group"><label>Product Name</label><input type="text" id="prodName" required></div>
                <div class="form-group"><label>Category</label><input type="text" id="prodCategory" value="Skincare" required></div>
                <div class="form-group"><label>Price (₹)</label><input type="number" id="prodPrice" required></div>
                <div class="form-group"><label>Stock Quantity</label><input type="number" id="prodStock" required></div>
                <div class="form-group"><label>Image URL</label><input type="text" id="prodImage" placeholder="https://..." required></div>
                <div class="form-group"><label>Description</label><textarea id="prodDesc" rows="2"></textarea></div>
                <button type="submit" class="btn btn-green" style="width:100%;">Save Product</button>
            </form>
        </div>
    </div>

    <script>
        let adminData = {};

        function fetchAdminData() {
            fetch('/api/admin/data')
            .then(res => res.json())
            .then(data => {
                adminData = data;
                renderOrders();
                renderInventory();
                if(data.config) {
                    document.getElementById('configLogoInput').value = data.config.logo || '';
                }
            });
        }
        fetchAdminData();

        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('active');
        }

        function switchTab(tab) {
            document.querySelectorAll('.admin-tab-content').forEach(el => el.style.display = 'none');
            document.querySelectorAll('.admin-nav-btn').forEach(el => el.classList.remove('active'));
            
            document.getElementById('tab-' + tab).style.display = 'block';
            event.currentTarget.classList.add('active');
            
            let titles = { 'orders': 'Customer Orders', 'inventory': 'Product Inventory', 'settings': 'Store Settings & Logo' };
            document.getElementById('pageTitle').innerText = titles[tab];
            if(window.innerWidth <= 900) toggleAdminSidebar();
        }

        function renderOrders() {
            let tbody = document.getElementById('ordersTableBody');
            tbody.innerHTML = '';
            if(!adminData.orders || adminData.orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#888;">No orders received yet.</td></tr>';
                return;
            }
            adminData.orders.forEach(o => {
                let itemsList = o.items.map(i => `<li>${i.name} (x1) - ₹${i.price}</li>`).join('');
                let currentStep = o.status_step || 1;
                
                tbody.innerHTML += `
                <tr>
                    <td><b>${o.order_id}</b><br><span style="font-size:11px; color:#777;">${o.date}</span></td>
                    <td><b>${o.name}</b><br><span style="font-size:11px; color:#555;">📞 ${o.phone}</span><br><span style="font-size:11px; color:#555;">✉️ ${o.email}</span></td>
                    <td><span style="font-size:12px;">${o.full_address}</span></td>
                    <td><ul style="padding-left:15px; font-size:12px; margin-bottom:5px;">${itemsList}</ul><b>Total: ₹${o.amount}</b> (${o.payment_type})</td>
                    <td>
                        <select onchange="updateOrderStatus('${o.order_id}', this.value)" style="padding:6px; border-radius:6px; border:1px solid #ddd; font-size:12px; font-weight:600; background:#f9f9f9;">
                            <option value="1" ${currentStep == 1 ? 'selected' : ''}>1. Order Placed</option>
                            <option value="2" ${currentStep == 2 ? 'selected' : ''}>2. Packaging</option>
                            <option value="3" ${currentStep == 3 ? 'selected' : ''}>3. Shipped</option>
                            <option value="4" ${currentStep == 4 ? 'selected' : ''}>4. Delivered</option>
                        </select>
                    </td>
                </tr>`;
            });
        }

        function updateOrderStatus(order_id, step) {
            fetch('/api/admin/order_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id, step: parseInt(step) })
            })
            .then(res => res.json())
            .then(data => {
                adminData.orders = data.orders;
                renderOrders();
            });
        }

        function renderInventory() {
            let tbody = document.getElementById('inventoryTableBody');
            tbody.innerHTML = '';
            if(!adminData.products || adminData.products.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#888;">No products found.</td></tr>';
                return;
            }
            adminData.products.forEach(p => {
                let isSuspended = p.status === 'suspended';
                tbody.innerHTML += `
                <tr>
                    <td><img src="${p.image}" width="40" height="40" style="object-fit:cover; border-radius:6px;"></td>
                    <td><b>${p.name}</b><br><span style="font-size:11px; color:#666;">${p.desc}</span></td>
                    <td>${p.category}</td>
                    <td>₹${p.price}</td>
                    <td>${p.stock}</td>
                    <td><span class="badge ${isSuspended ? 'suspended' : 'active'}">${isSuspended ? 'Suspended' : 'Live'}</span></td>
                    <td>
                        <div style="display:flex; gap:6px;">
                            <button class="btn btn-gold" onclick="openEditProductModal(${p.id})">Edit</button>
                            <button class="btn ${isSuspended ? 'btn-green' : 'btn-red'}" onclick="toggleSuspendProduct(${p.id}, '${isSuspended ? 'active' : 'suspended'}')">${isSuspended ? 'Restore' : 'Suspend'}</button>
                            <button class="btn btn-red" onclick="deleteProduct(${p.id})"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </td>
                </tr>`;
            });
        }

        function openAddProductModal() {
            document.getElementById('modalProdTitle').innerText = 'Add New Product';
            document.getElementById('editProdId').value = '';
            document.getElementById('prodName').value = '';
            document.getElementById('prodCategory').value = 'Skincare';
            document.getElementById('prodPrice').value = '';
            document.getElementById('prodStock').value = '50';
            document.getElementById('prodImage').value = '';
            document.getElementById('prodDesc').value = '';
            document.getElementById('productModal').style.display = 'flex';
        }

        function openEditProductModal(id) {
            let p = adminData.products.find(x => x.id === id);
            if(!p) return;
            document.getElementById('modalProdTitle').innerText = 'Edit Product';
            document.getElementById('editProdId').value = p.id;
            document.getElementById('prodName').value = p.name;
            document.getElementById('prodCategory').value = p.category;
            document.getElementById('prodPrice').value = p.price;
            document.getElementById('prodStock').value = p.stock;
            document.getElementById('prodImage').value = p.image;
            document.getElementById('prodDesc').value = p.desc;
            document.getElementById('productModal').style.display = 'flex';
        }

        function saveProductForm() {
            let id = document.getElementById('editProdId').value;
            let payload = {
                name: document.getElementById('prodName').value,
                category: document.getElementById('prodCategory').value,
                price: document.getElementById('prodPrice').value,
                stock: document.getElementById('prodStock').value,
                image: document.getElementById('prodImage').value,
                desc: document.getElementById('prodDesc').value
            };

            let method = 'POST';
            if(id) {
                method = 'PUT';
                payload.id = parseInt(id);
            }

            fetch('/api/admin/products', {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                adminData.products = data.products;
                renderInventory();
                document.getElementById('productModal').style.display = 'none';
            });
        }

        function toggleSuspendProduct(id, newStatus) {
            fetch('/api/admin/products', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, status: newStatus })
            })
            .then(res => res.json())
            .then(data => {
                adminData.products = data.products;
                renderInventory();
            });
        }

        function deleteProduct(id) {
            if(!confirm("Are you sure you want to permanently delete this product?")) return;
            fetch('/api/admin/products', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            })
            .then(res => res.json())
            .then(data => {
                adminData.products = data.products;
                renderInventory();
            });
        }

        function updateConfig() {
            let logo = document.getElementById('configLogoInput').value;
            fetch('/api/admin/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ logo })
            })
            .then(res => res.json())
            .then(() => alert("Settings updated successfully!"));
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Kesh Aadar Flask Server Running...")
    app.run(host='0.0.0.0', port=5000, debug=True)
