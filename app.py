from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
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
SMTP_EMAIL = "keshaadar@gmail.com"
SMTP_PASS = "zvxb mrbs ccoi vfrl"

# --- IN-MEMORY DATABASE & STORAGE ---
SITE_LOGO = "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80"

PRODUCTS = [
    {
        "id": 1,
        "name": "Aloe Neem Glow Face Wash",
        "category": "Skincare",
        "price": 349,
        "stock": 50,
        "media_type": "image",
        "media_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80",
        "desc": "Deep cleansing herbal formula for radiant skin.",
        "status": "active"
    },
    {
        "id": 2,
        "name": "Saffron Kumkumadi Night Serum",
        "category": "Skincare",
        "price": 799,
        "stock": 30,
        "media_type": "image",
        "media_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80",
        "desc": "Fades blemishes and restores natural skin glow.",
        "status": "active"
    },
    {
        "id": 3,
        "name": "Bhringraj Onion Hair Growth Oil",
        "category": "Haircare",
        "price": 499,
        "stock": 40,
        "media_type": "image",
        "media_url": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80",
        "desc": "Stops hair fall and stimulates roots naturally.",
        "status": "active"
    }
]

ORDERS = []
BLACKLISTED_IPS = []

# --- BACKGROUND EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, req_host):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed! Ref: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> (Qty: {i.get('qty', 1)}) - ₹{i['price']}</li>" for i in items])
        track_url = f"https://{req_host}/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Segoe UI', sans-serif; background-color: #FAF7F0; padding: 30px 10px; margin: 0; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 35px; border-radius: 20px; box-shadow: 0 15px 35px rgba(27, 67, 50, 0.08); border-top: 6px solid #1b4332;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="font-size: 32px; color: #1b4332; margin: 0; font-family: Georgia, serif; letter-spacing: 1px;">KESH AADAR</h1>
                    <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 4px;">Pure Botanical Remedies</p>
                </div>
                
                <hr style="border: 0; border-top: 1px dashed #EAE5D9; margin: 20px 0;">
                
                <h2 style="color: #1b4332; font-size: 20px; margin-bottom: 10px;">Thank you for your purchase, {name}!</h2>
                <p style="font-size: 14px; color: #555; line-height: 1.6; margin-top: 0;">We are preparing your botanical items for dispatch. Here is your order breakdown:</p>
                
                <div style="background: #F8F5EE; padding: 20px; border-radius: 12px; margin: 20px 0; border: 1px solid #E3DDCF;">
                    <p style="margin: 0; color: #888; font-size: 11px; text-transform: uppercase; font-weight: bold;">Order Tracking Reference</p>
                    <h3 style="margin: 6px 0; font-size: 26px; color: #1b4332; font-family: monospace; letter-spacing: 1px;">{order_id}</h3>
                    <p style="margin: 8px 0 0 0; color: #2b2b2b; font-size: 14px; font-weight: 600;">Total Amount Paid / Payable: ₹{amount}</p>
                    <p style="margin: 6px 0 0 0; color: #666; font-size: 13px;"><b>Deliver To:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 8px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 35px;">
                    <a href="{track_url}" style="background: #1b4332; color: #ffffff; text-decoration: none; padding: 15px 32px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 8px 20px rgba(27, 67, 50, 0.25);">Click Here To Check Live Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">For queries, reply directly to this email or contact keshaadar@gmail.com</p>
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
    active_products = [p for p in PRODUCTS if p.get('status', 'active') == 'active']
    return render_template_string(TEMPLATE, products=active_products, logo=SITE_LOGO)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status'] = 'Placed' # Initial Status
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.append(data)
    
    # Deduct stock
    for item in data.get('items', []):
        for p in PRODUCTS:
            if p['id'] == item.get('id'):
                p['stock'] = max(0, p['stock'] - 1)

    req_host = request.host
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, req_host)
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, logo=SITE_LOGO)

@app.route('/track_order')
def track_order():
    q = request.args.get('q', '').strip()
    for o in ORDERS:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order": o})
    return jsonify({"found": False})

# --- ADMIN PANEL ROUTES ---
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, logo=SITE_LOGO)

@app.route('/api/admin/update_order_status', methods=['POST'])
def update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status') # 'Placed', 'Packaging', 'Shipped', 'Delivered'
    
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status'] = new_status
            return jsonify({"status": "success", "order": o})
    return jsonify({"status": "error", "message": "Order not found"}), 404

@app.route('/api/admin/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_admin_products():
    global PRODUCTS
    if request.method == 'GET':
        return jsonify(PRODUCTS)
    
    data = request.get_json()
    if request.method == 'POST': # Add Product
        new_id = max([p['id'] for p in PRODUCTS], default=0) + 1
        new_prod = {
            "id": new_id,
            "name": data.get("name"),
            "category": data.get("category", "General"),
            "price": float(data.get("price", 0)),
            "stock": int(data.get("stock", 0)),
            "media_type": data.get("media_type", "image"),
            "media_url": data.get("media_url", ""),
            "desc": data.get("desc", ""),
            "status": "active"
        }
        PRODUCTS.append(new_prod)
        return jsonify({"status": "success", "product": new_prod})

    elif request.method == 'PUT': # Edit Product or Toggle Suspend
        prod_id = data.get("id")
        for p in PRODUCTS:
            if p['id'] == prod_id:
                if 'status' in data:
                    p['status'] = data['status']
                if 'name' in data:
                    p['name'] = data['name']
                if 'price' in data:
                    p['price'] = float(data['price'])
                if 'stock' in data:
                    p['stock'] = int(data['stock'])
                if 'desc' in data:
                    p['desc'] = data['desc']
                return jsonify({"status": "success", "product": p})
        return jsonify({"status": "error", "message": "Not found"}), 404

    elif request.method == 'DELETE': # Delete Product
        prod_id = data.get("id")
        PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
        return jsonify({"status": "success"})

@app.route('/api/admin/update_logo', methods=['POST'])
def update_logo():
    global SITE_LOGO
    data = request.get_json()
    if data and data.get('logo_data'):
        SITE_LOGO = data.get('logo_data')
        return jsonify({"status": "success", "logo": SITE_LOGO})
    return jsonify({"status": "error"}), 400

# --- STOREFRONT TEMPLATE ---
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
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; --shadow: 0 20px 40px rgba(27, 67, 50, 0.12); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); overflow-x: hidden; scroll-behavior: smooth; }

        .reveal { opacity: 0; transform: translateY(40px); transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }

        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.05); }
        .nav-left { display: flex; align-items: center; gap: 15px; }
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Public Drawer Sidebar */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: 0.4s; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.77, 0, 0.175, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); border: none; background: none; }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); }

        /* Hero */
        .hero { height: 75vh; display: flex; align-items: center; justify-content: center; text-align: center; background: radial-gradient(circle, #f3efea 0%, #faf7f0 75%); margin-top: 70px; padding: 0 20px; }
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
        .product-img-container { height: 230px; overflow: hidden; background: #f7f5f0; position: relative; }
        .product-img-container img, .product-img-container video { width: 100%; height: 100%; object-fit: cover; }
        .product-info { padding: 20px; }
        .price-row { display: flex; justify-content: space-between; align-items: center; margin: 15px 0; }
        .price { font-size: 22px; font-weight: 700; color: var(--green-light); }
        .btn-group { display: flex; gap: 10px; }
        .btn-cart { flex: 1; padding: 10px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .btn-buy { flex: 1; padding: 10px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }

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

        /* Footer */
        .main-footer { background-color: var(--green-primary); color: white; padding: 50px 30px 20px; margin-top: 60px; }
        .footer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 30px; max-width: 1200px; margin: 0 auto; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 30px; }
        .footer-grid h3 { color: var(--accent-gold); font-family: 'Playfair Display'; font-size: 20px; margin-bottom: 15px; }
        .footer-grid p { font-size: 14px; margin-bottom: 10px; color: #ddd; display: flex; align-items: center; gap: 10px; }
        .social-icons { margin-top: 15px; display: flex; gap: 15px; }
        .social-icons a { color: white; font-size: 18px; background: rgba(255,255,255,0.1); width: 38px; height: 38px; display: flex; justify-content: center; align-items: center; border-radius: 50%; text-decoration: none; }
        .footer-bottom { padding-top: 20px; font-size: 12px; color: #aaa; text-align: center; }
    </style>
</head>
<body>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
                <img src="{{ logo }}" alt="Logo" class="logo-img" id="headerLogo">
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
        <button class="close-sidebar" onclick="toggleSidebar()">&times;</button>
        
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
            <a href="mailto:keshaadar@gmail.com" class="support-card"><i class="fa-solid fa-envelope" style="color: var(--accent-gold);"></i><div><h4 style="font-size: 13px; color: var(--green-primary);">Email Support</h4><p style="font-size: 11px; color: #555;">keshaadar@gmail.com</p></div></a>
        </div>

        <div id="sidebar-faq-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Frequently Asked Questions</h3>
            <h4 style="font-size: 13px; color: var(--green-primary);">1. What is the estimated dispatch time?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Orders are dispatched within 24-48 hours.</p>
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

    <!-- Features Banner -->
    <div class="features-banner">
        <div class="feature-item"><i class="fa-solid fa-leaf" style="color:var(--accent-gold);"></i> 100% Organic</div>
        <div class="feature-item"><i class="fa-solid fa-truck-fast" style="color:var(--accent-gold);"></i> Express Shipping</div>
        <div class="feature-item"><i class="fa-solid fa-shield-cat" style="color:var(--accent-gold);"></i> Cruelty-Free</div>
    </div>

    <!-- Shop Grid -->
    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 28px; color: var(--green-primary); margin-bottom: 30px;" class="reveal">Our Formulations</h2>
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-img-container">
                    {% if p.media_type == 'video' %}
                        <video src="{{ p.media_url }}" autoplay muted loop playsinline></video>
                    {% else %}
                        <img src="{{ p.media_url }}" alt="{{ p.name }}" id="img-{{ p.id }}">
                    {% endif %}
                </div>
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
                <p><i class="fa-solid fa-envelope" style="color:var(--accent-gold);"></i> keshaadar@gmail.com</p>
            </div>
            <div>
                <h3>Connect With Us</h3>
                <div class="social-icons">
                    <a href="https://www.instagram.com/kesh_aadar" target="_blank"><i class="fa-brands fa-instagram"></i></a>
                    <a href="https://www.facebook.com/" target="_blank"><i class="fa-brands fa-facebook-f"></i></a>
                </div>
            </div>
        </div>
        <div class="footer-bottom">
            &copy; 2026 Kesh Aadar Botanical Remedies. All Rights Reserved.
        </div>
    </footer>

    <!-- Cart Modal -->
    <div class="modal" id="cartModal">
        <div class="modal-content">
            <button class="close-sidebar" onclick="document.getElementById('cartModal').style.display='none'" style="position:absolute; right:20px; top:20px;">&times;</button>
            <h3 style="color:var(--green-primary); margin-bottom:15px;">Your Shopping Basket</h3>
            <div id="cart-items-container"></div>
            
            <div id="checkout-section" style="display:none; margin-top:20px;">
                <h4 style="margin-bottom:12px; font-size:15px; color:var(--green-primary);">Shipping Details</h4>
                <form class="checkout-form" id="checkoutForm" onsubmit="event.preventDefault(); placeOrder();">
                    <div class="form-grid">
                        <input type="text" id="cust-name" class="full-width" placeholder="Full Name *" required>
                        <input type="email" id="cust-email" class="full-width" placeholder="Email Address *" required>
                        <input type="tel" id="cust-phone" class="full-width" placeholder="Phone Number *" required pattern="[0-9]{10}">
                        
                        <input type="text" id="cust-pincode" placeholder="PIN Code *" required pattern="[0-9]{6}" maxlength="6" onkeyup="detectPinCode(this.value)">
                        <input type="text" id="cust-city" placeholder="District / City *" required readonly style="background:#f4f4f4;">
                        <input type="text" id="cust-state" placeholder="State *" required readonly style="background:#f4f4f4;">
                        
                        <select id="cust-landmark" class="full-width">
                            <option value="">Select Area / Landmark (Optional)</option>
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
                        <div class="bill-row" id="cod-fee-row" style="display:none; color:#c62828;"><span>COD Charge:</span><span>₹99</span></div>
                        <div class="bill-row"><span>Estimated Shipping:</span><span style="color:#2e7d32; font-weight:600;">FREE</span></div>
                        <div class="bill-row total"><span>Total Amount:</span><span id="bill-total">₹0</span></div>
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
            if(img) {
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
        }

        function buyNow(id) { 
            cart = [productsData.find(x => x.id === id)]; 
            updateCartUI(); 
            openCartModal(); 
        }

        function openCartModal() { 
            document.getElementById('cartModal').style.display = 'flex'; 
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
                document.getElementById('payBtn').innerText = 'Confirm Order (COD)';
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
                        landmarkSelect.innerHTML = '<option value="">Select Area / Landmark (Optional)</option>';
                        postOffices.forEach(po => {
                            landmarkSelect.innerHTML += `<option value="${po.Name}">${po.Name}</option>`;
                        });
                    }
                });
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

            let amt = updateTotal();
            let payload = { name, email, phone, pincode, city, state, landmark, street, amount: amt, payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Payment', items: cart };

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
            window.location.href = '/order_success/' + q;
        }
    </script>
</body>
</html>
"""

# --- DEDICATED ORDER TRACKING / SUCCESS TEMPLATE ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Status | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; padding: 40px 20px; display: flex; justify-content: center; align-items: center; }

        .card { background: white; max-width: 650px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); }
        .brand-header { text-align: center; margin-bottom: 30px; }
        .brand-header img { width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid var(--accent-gold); }
        .brand-header h2 { font-family: 'Playfair Display', serif; color: var(--green-primary); }

        /* Step Progress Bar */
        .tracker-container { margin: 35px 0; position: relative; }
        .progress-line { position: absolute; top: 20px; left: 10%; right: 10%; height: 4px; background: #E0E0E0; z-index: 1; }
        .progress-line-fill { position: absolute; top: 20px; left: 10%; height: 4px; background: #2e7d32; z-index: 2; transition: width 0.5s ease; }
        .steps { display: flex; justify-content: space-between; position: relative; z-index: 3; }
        .step { text-align: center; width: 25%; }
        .step-icon { width: 42px; height: 42px; background: white; border: 3px solid #E0E0E0; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px; color: #888; font-size: 14px; font-weight: bold; transition: 0.3s; }
        .step.active .step-icon { border-color: #2e7d32; background: #2e7d32; color: white; box-shadow: 0 0 12px rgba(46, 125, 50, 0.4); }
        .step-label { font-size: 12px; font-weight: 600; color: #666; }
        .step.active .step-label { color: var(--green-primary); }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        .items-list { border-top: 1px solid #eee; padding-top: 15px; margin-top: 15px; }
        .item-row { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }

        .badge-paid { background: #e8f5e9; color: #2e7d32; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block; }
        .badge-cod { background: #fff3e0; color: #e65100; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: block; text-align: center; margin-top: 25px; }
    </style>
</head>
<body>

    <div class="card">
        <div class="brand-header">
            <img src="{{ logo }}" alt="Logo">
            <h2>KESH AADAR</h2>
            <p style="font-size: 13px; color: #666;">Live Order Tracking</p>
        </div>

        {% if order %}
        {% set status = order.status or 'Placed' %}
        {% set fill_width = '0%' %}
        {% if status == 'Packaging' %}{% set fill_width = '33%' %}{% endif %}
        {% if status == 'Shipped' %}{% set fill_width = '66%' %}{% endif %}
        {% if status == 'Delivered' %}{% set fill_width = '80%' %}{% endif %}

        <!-- Visual Progress Line -->
        <div class="tracker-container">
            <div class="progress-line"></div>
            <div class="progress-line-fill" style="width: {{ fill_width }};"></div>
            <div class="steps">
                <div class="step active">
                    <div class="step-icon"><i class="fa-solid fa-receipt"></i></div>
                    <div class="step-label">Order Placed</div>
                </div>
                <div class="step {% if status in ['Packaging', 'Shipped', 'Delivered'] %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-box-open"></i></div>
                    <div class="step-label">Packaging</div>
                </div>
                <div class="step {% if status in ['Shipped', 'Delivered'] %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-truck-fast"></i></div>
                    <div class="step-label">Shipped</div>
                </div>
                <div class="step {% if status == 'Delivered' %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-house-chimney"></i></div>
                    <div class="step-label">Delivered</div>
                </div>
            </div>
        </div>

        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Order Date:</span><b>{{ order.date }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Contact Phone:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Payment Status:</span>
                {% if order.payment_type == 'Online Payment' %}
                <span class="badge-paid"><i class="fa-solid fa-circle-check"></i> Already Paid Online</span>
                {% else %}
                <span class="badge-cod"><i class="fa-solid fa-hand-holding-dollar"></i> Cash on Delivery</span>
                {% endif %}
            </div>
            <div class="info-row" style="margin-top: 8px;"><span>Shipping Address:</span><span style="max-width:280px; text-align:right;">{{ order.full_address }}</span></div>

            <div class="items-list">
                <h4 style="margin-bottom: 8px; color:var(--green-primary);">Items Summary</h4>
                {% for item in order.items %}
                <div class="item-row">
                    <span>{{ item.name }}</span>
                    <b>₹{{ item.price }}</b>
                </div>
                {% endfor %}
                <hr style="margin: 10px 0; border: 0; border-top: 1px dashed #ccc;">
                <div class="info-row" style="font-size: 15px; color: var(--green-primary);">
                    <b>Total Bill (Incl. GST):</b><b>₹{{ order.amount }}</b>
                </div>
            </div>
        </div>
        {% else %}
        <div style="text-align: center; padding: 30px 0;">
            <i class="fa-solid fa-triangle-exclamation" style="font-size: 40px; color: #d4a373; margin-bottom: 15px;"></i>
            <h3>Order Not Found</h3>
            <p style="font-size: 13px; color: #666;">No active order matching ID: <b>{{ order_id }}</b></p>
        </div>
        {% endif %}

        <a href="/" class="btn-home">Return to Storefront</a>
    </div>

</body>
</html>
"""

# --- ADMIN PANEL TEMPLATE ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --accent-gold: #d4a373; --bg-light: #f4f6f8; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--bg-light); color: #333; display: flex; min-height: 100vh; }

        /* Admin Drawer Sidebar */
        .sidebar { width: 260px; background: var(--green-primary); color: white; padding: 25px 20px; transition: 0.3s; position: fixed; height: 100vh; z-index: 100; }
        .sidebar.closed { transform: translateX(-260px); }
        .sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .sidebar-header h2 { font-size: 20px; color: var(--accent-gold); }
        .close-admin-btn { background: none; border: none; color: white; font-size: 24px; cursor: pointer; }

        .nav-link { display: flex; align-items: center; gap: 12px; padding: 12px 15px; color: #ddd; text-decoration: none; border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: 0.2s; }
        .nav-link:hover, .nav-link.active { background: rgba(255,255,255,0.1); color: white; }

        .main-content { flex: 1; margin-left: 260px; padding: 30px; transition: 0.3s; }
        .main-content.expanded { margin-left: 0; }

        .top-bar { display: flex; align-items: center; gap: 20px; margin-bottom: 30px; background: white; padding: 15px 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
        .toggle-btn { background: none; border: none; font-size: 20px; color: var(--green-primary); cursor: pointer; }

        .card-box { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 25px; }

        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #fafafa; color: var(--green-primary); }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 5px; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; outline: none; }

        .btn { background: var(--green-primary); color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .btn-danger { background: #c62828; }
        .btn-warn { background: #ef6c00; }

        .status-select { padding: 6px; border-radius: 6px; border: 1px solid #ddd; font-weight: bold; }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div class="sidebar" id="adminSidebar">
        <div class="sidebar-header">
            <h2>KESH ADMIN</h2>
            <button class="close-admin-btn" onclick="toggleAdminSidebar()">&times;</button>
        </div>
        <div class="nav-link active" onclick="showTab('orders')"><i class="fa-solid fa-list-check"></i> Orders Management</div>
        <div class="nav-link" onclick="showTab('inventory')"><i class="fa-solid fa-boxes-stacked"></i> Inventory Control</div>
        <div class="nav-link" onclick="showTab('add-product')"><i class="fa-solid fa-square-plus"></i> Add New Product</div>
        <div class="nav-link" onclick="showTab('branding')"><i class="fa-solid fa-paint-roller"></i> Website Branding</div>
    </div>

    <!-- Main Content -->
    <div class="main-content" id="mainContent">
        <div class="top-bar">
            <button class="toggle-btn" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
            <h3 style="color: var(--green-primary);">Admin Dashboard</h3>
        </div>

        <!-- Orders Section -->
        <div id="orders-tab" class="card-box">
            <h3>Customer Orders</h3>
            <table>
                <thead>
                    <tr>
                        <th>Order ID</th>
                        <th>Customer</th>
                        <th>Address</th>
                        <th>Items</th>
                        <th>Total</th>
                        <th>Payment</th>
                        <th>Order Progress</th>
                    </tr>
                </thead>
                <tbody>
                    {% for o in orders %}
                    <tr>
                        <td><b>{{ o.order_id }}</b><br><small>{{ o.date }}</small></td>
                        <td>{{ o.name }}<br><small>{{ o.phone }}</small></td>
                        <td><small>{{ o.full_address }}</small></td>
                        <td>
                            {% for i in o.items %}
                            <small>• {{ i.name }}</small><br>
                            {% endfor %}
                        </td>
                        <td><b>₹{{ o.amount }}</b></td>
                        <td><small>{{ o.payment_type }}</small></td>
                        <td>
                            <select class="status-select" onchange="updateStatus('{{ o.order_id }}', this.value)">
                                <option value="Placed" {% if o.status == 'Placed' %}selected{% endif %}>Placed</option>
                                <option value="Packaging" {% if o.status == 'Packaging' %}selected{% endif %}>Packaging</option>
                                <option value="Shipped" {% if o.status == 'Shipped' %}selected{% endif %}>Shipped</option>
                                <option value="Delivered" {% if o.status == 'Delivered' %}selected{% endif %}>Delivered</option>
                            </select>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Inventory Control Section -->
        <div id="inventory-tab" class="card-box" style="display:none;">
            <h3>Live Inventory</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Price</th>
                        <th>Stock</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in products %}
                    <tr>
                        <td>{{ p.id }}</td>
                        <td><b>{{ p.name }}</b></td>
                        <td>₹{{ p.price }}</td>
                        <td>{{ p.stock }}</td>
                        <td>
                            <span style="color: {% if p.status == 'active' %}green{% else %}red{% endif %}; font-weight:bold;">
                                {{ p.status or 'active' }}
                            </span>
                        </td>
                        <td>
                            <button class="btn btn-warn" onclick="toggleSuspend({{ p.id }}, '{{ p.status }}')">
                                {% if p.status == 'suspended' %}Resume{% else %}Suspend{% endif %}
                            </button>
                            <button class="btn btn-danger" onclick="deleteProduct({{ p.id }})">Delete</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Add Product Section -->
        <div id="add-product-tab" class="card-box" style="display:none;">
            <h3>Upload New Product</h3>
            <form onsubmit="event.preventDefault(); submitProduct();">
                <div class="form-group">
                    <label>Product Name</label>
                    <input type="text" id="p-name" required>
                </div>
                <div class="form-group">
                    <label>Price (₹)</label>
                    <input type="number" id="p-price" required>
                </div>
                <div class="form-group">
                    <label>Stock Quantity</label>
                    <input type="number" id="p-stock" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="p-desc" rows="3"></textarea>
                </div>
                <div class="form-group">
                    <label>Product Media File (Upload Image or Video from Gallery)</label>
                    <input type="file" id="p-file" accept="image/*,video/*" required>
                </div>
                <button type="submit" class="btn">Upload Product</button>
            </form>
        </div>

        <!-- Branding Section -->
        <div id="branding-tab" class="card-box" style="display:none;">
            <h3>Update Website Logo</h3>
            <div class="form-group">
                <label>Current Logo Preview</label><br>
                <img src="{{ logo }}" style="width:70px; height:70px; border-radius:50%; object-fit:cover;">
            </div>
            <div class="form-group">
                <label>Select New Logo Image from Device</label>
                <input type="file" id="logo-file" accept="image/*">
            </div>
            <button class="btn" onclick="uploadLogo()">Save Logo</button>
        </div>
    </div>

    <script>
        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('closed');
            document.getElementById('mainContent').classList.toggle('expanded');
        }

        function showTab(tab) {
            ['orders', 'inventory', 'add-product', 'branding'].forEach(t => {
                document.getElementById(t + '-tab').style.display = 'none';
            });
            document.getElementById(tab + '-tab').style.display = 'block';
        }

        function updateStatus(order_id, status) {
            fetch('/api/admin/update_order_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id, status })
            }).then(r => r.json()).then(() => alert('Order status updated!'));
        }

        function toggleSuspend(id, currentStatus) {
            let newStatus = currentStatus === 'suspended' ? 'active' : 'suspended';
            fetch('/api/admin/products', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, status: newStatus })
            }).then(() => location.reload());
        }

        function deleteProduct(id) {
            if(confirm("Are you sure you want to delete this product?")) {
                fetch('/api/admin/products', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                }).then(() => location.reload());
            }
        }

        function submitProduct() {
            let fileInput = document.getElementById('p-file').files[0];
            if(!fileInput) return alert('Select a media file');

            let reader = new FileReader();
            reader.onload = function(e) {
                let media_url = e.target.result;
                let media_type = fileInput.type.startsWith('video') ? 'video' : 'image';

                let payload = {
                    name: document.getElementById('p-name').value,
                    price: document.getElementById('p-price').value,
                    stock: document.getElementById('p-stock').value,
                    desc: document.getElementById('p-desc').value,
                    media_type: media_type,
                    media_url: media_url
                };

                fetch('/api/admin/products', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                }).then(() => location.reload());
            };
            reader.readAsDataURL(fileInput);
        }

        function uploadLogo() {
            let fileInput = document.getElementById('logo-file').files[0];
            if(!fileInput) return alert('Select an image');

            let reader = new FileReader();
            reader.onload = function(e) {
                fetch('/api/admin/update_logo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ logo_data: e.target.result })
                }).then(() => location.reload());
            };
            reader.readAsDataURL(fileInput);
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
