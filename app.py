from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
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

# --- IN-MEMORY DATABASE ---
SITE_SETTINGS = {
    "logo_url": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
    "brand_name": "KESH AADAR"
}

PRODUCTS = [
    {
        "id": 1,
        "name": "Aloe Neem Glow Face Wash",
        "category": "Skincare",
        "price": 349.0,
        "stock": 50,
        "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80",
        "desc": "Deep cleansing herbal formula for radiant skin.",
        "status": "active"
    },
    {
        "id": 2,
        "name": "Saffron Kumkumadi Night Serum",
        "category": "Skincare",
        "price": 799.0,
        "stock": 30,
        "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80",
        "desc": "Fades blemishes and restores natural skin glow.",
        "status": "active"
    },
    {
        "id": 3,
        "name": "Bhringraj Onion Hair Growth Oil",
        "category": "Haircare",
        "price": 499.0,
        "stock": 40,
        "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80",
        "desc": "Stops hair fall and stimulates roots naturally.",
        "status": "active"
    },
    {
        "id": 4,
        "name": "Hibiscus & Shikakai Herbal Shampoo",
        "category": "Haircare",
        "price": 399.0,
        "stock": 45,
        "image": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80",
        "desc": "Nourishing sulfate-free cleanser for smooth hair.",
        "status": "active"
    }
]

ORDERS = []
BLACKLISTED_IPS = []

# --- STATUS STEPS MAPPING ---
STATUS_MAP = {
    "Placed": 1,
    "Packed": 2,
    "Shipped": 3,
    "Out for Delivery": 4,
    "Delivered": 5
}

# --- BACKGROUND EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> - ₹{i['price']}</li>" for i in items])
        track_url = f"http://127.0.0.1:5000/order_success/{order_id}"

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
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Reply directly to this email or contact customer support at subhraroy324@gmail.com</p>
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
    client_ip = request.remote_addr
    if client_ip in BLACKLISTED_IPS:
        return jsonify({"error": "Your IP has been blacklisted by administrator."}), 403

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    active_products = [p for p in PRODUCTS if p.get('status') == 'active']
    return render_template_string(TEMPLATE, products=active_products, settings=SITE_SETTINGS)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status'] = "Placed"
    data['status_step'] = 1
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.append(data)
    
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address)
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, settings=SITE_SETTINGS)

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
    return render_template_string(ADMIN_TEMPLATE, settings=SITE_SETTINGS)

@app.route('/api/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    global SITE_SETTINGS
    if request.method == 'POST':
        data = request.get_json()
        if 'logo_url' in data and data['logo_url']:
            SITE_SETTINGS['logo_url'] = data['logo_url']
        if 'brand_name' in data and data['brand_name']:
            SITE_SETTINGS['brand_name'] = data['brand_name']
        return jsonify({"status": "success", "settings": SITE_SETTINGS})
    return jsonify(SITE_SETTINGS)

@app.route('/api/admin/orders', methods=['GET'])
def admin_get_orders():
    return jsonify(ORDERS)

@app.route('/api/admin/order/update_status', methods=['POST'])
def admin_update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')
    
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status'] = new_status
            o['status_step'] = STATUS_MAP.get(new_status, 1)
            return jsonify({"status": "success", "order": o})
            
    return jsonify({"error": "Order not found"}), 444

@app.route('/api/admin/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
def admin_products():
    global PRODUCTS
    if request.method == 'GET':
        return jsonify(PRODUCTS)
        
    if request.method == 'POST':
        data = request.get_json()
        new_id = max([p['id'] for p in PRODUCTS], default=0) + 1
        data['id'] = new_id
        data['status'] = 'active'
        data['price'] = float(data.get('price', 0))
        data['stock'] = int(data.get('stock', 0))
        PRODUCTS.append(data)
        return jsonify({"status": "success", "product": data})
        
    if request.method == 'PUT':
        data = request.get_json()
        prod_id = data.get('id')
        for p in PRODUCTS:
            if p['id'] == prod_id:
                p['name'] = data.get('name', p['name'])
                p['price'] = float(data.get('price', p['price']))
                p['stock'] = int(data.get('stock', p['stock']))
                p['desc'] = data.get('desc', p['desc'])
                if 'image' in data and data['image']:
                    p['image'] = data['image']
                if 'status' in data:
                    p['status'] = data['status']
                return jsonify({"status": "success", "product": p})
        return jsonify({"error": "Product not found"}), 404
        
    if request.method == 'DELETE':
        data = request.get_json()
        prod_id = data.get('id')
        PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
        return jsonify({"status": "success"})

# --- FRONTEND TEMPLATE ---
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ settings.brand_name }} | Pure Herbal Botanicals</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; --shadow: 0 20px 40px rgba(27, 67, 50, 0.15); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); overflow-x: hidden; scroll-behavior: smooth; }

        .reveal { opacity: 0; transform: translateY(30px); transition: all 0.7s cubic-bezier(0.16, 1, 0.3, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }

        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.88); backdrop-filter: blur(14px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.04); transition: all 0.3s ease; }
        .nav-left { display: flex; align-items: center; gap: 18px; }
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; transition: transform 0.2s; }
        .menu-btn:hover { transform: scale(1.1); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: transform 0.2s ease; }
        .cart-icon-container:hover { transform: scale(1.05); }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; transition: all 0.3s ease; }

        /* Smooth Sliding Sidebar Drawer */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.45); backdrop-filter: blur(6px); z-index: 1500; opacity: 0; visibility: hidden; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: 0; width: 340px; height: 100%; background: #ffffff; box-shadow: var(--shadow); z-index: 2000; transform: translateX(-100%); transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 24px; overflow-y: auto; }
        .sidebar.active { transform: translateX(0); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; font-weight: 600; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #fdfdfd; color: var(--green-primary); border: 1px solid #eaeaea; border-radius: 12px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 12px; transition: all 0.25s ease; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); border-color: var(--accent-gold); transform: translateX(4px); }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; margin-bottom: 20px; font-size: 12px; }
        .close-sidebar { font-size: 24px; cursor: pointer; color: var(--text-dark); transition: transform 0.2s; }
        .close-sidebar:hover { transform: rotate(90deg); color: #c62828; }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 12px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); transition: transform 0.2s; }
        .support-card:hover { transform: translateY(-2px); }

        /* Tracking Visual Status Line */
        .track-timeline { display: flex; justify-content: space-between; position: relative; margin: 25px 0 10px 0; }
        .track-timeline::before { content: ''; position: absolute; top: 14px; left: 10%; width: 80%; height: 3px; background: #e0e0e0; z-index: 1; }
        .track-timeline-progress { position: absolute; top: 14px; left: 10%; height: 3px; background: #2e7d32; z-index: 1; transition: width 0.5s ease; }
        .track-step { position: relative; z-index: 2; background: white; width: 30px; height: 30px; border-radius: 50%; border: 2px solid #ccc; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; color: #777; transition: all 0.3s; }
        .track-step.active { border-color: #2e7d32; background: #2e7d32; color: white; }

        /* Hero */
        .hero { height: 80vh; display: flex; align-items: center; justify-content: center; text-align: center; background: radial-gradient(circle, #f3efea 0%, #faf7f0 75%); margin-top: 70px; padding: 0 20px; }
        .hero-content h1 { font-family: 'Playfair Display', serif; font-size: clamp(34px, 6vw, 54px); color: var(--green-primary); margin-bottom: 15px; }
        .btn-primary { background: var(--green-primary); color: white; padding: 14px 38px; border-radius: 35px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: 0.3s; }
        .btn-primary:hover { background: var(--green-light); transform: translateY(-2px); box-shadow: 0 10px 20px rgba(27,67,50,0.2); }

        .features-banner { background: var(--green-primary); color: white; display: flex; justify-content: space-around; padding: 20px; flex-wrap: wrap; gap: 15px; }
        .feature-item { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 500; }

        /* Products Grid */
        .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 30px; }
        .product-card { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.04); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
        .product-card:hover { transform: translateY(-6px); box-shadow: 0 18px 35px rgba(0,0,0,0.08); }
        .product-img-container { height: 230px; overflow: hidden; background: #f7f5f0; }
        .product-img-container img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s ease; }
        .product-card:hover .product-img-container img { transform: scale(1.05); }
        .product-info { padding: 20px; }
        .price-row { display: flex; justify-content: space-between; align-items: center; margin: 15px 0; }
        .price { font-size: 22px; font-weight: 700; color: var(--green-light); }
        .btn-group { display: flex; gap: 10px; }
        .btn-cart { flex: 1; padding: 10px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: background 0.2s; }
        .btn-cart:hover { background: #e3ded6; }
        .btn-buy { flex: 1; padding: 10px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: background 0.2s; }
        .btn-buy:hover { background: var(--green-light); }

        .fly-item { position: fixed; z-index: 9999; width: 50px; height: 50px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); transition: all 0.8s cubic-bezier(0.2, 1, 0.3, 1); pointer-events: none; }

        /* Modal */
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.55); backdrop-filter: blur(5px); display: none; justify-content: center; align-items: center; z-index: 3000; padding: 15px; }
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
                {% if settings.logo_url %}
                <img src="{{ settings.logo_url }}" alt="Logo" class="logo-img" id="main-nav-logo">
                {% endif %}
                <div class="logo"><span id="main-nav-title">{{ settings.brand_name }}</span></div>
            </div>
        </div>
        <div class="cart-icon-container" id="cartTarget" onclick="openCartModal()">
            <i class="fa-solid fa-shopping-basket"></i><span class="cart-badge" id="cart-count">0</span>
        </div>
    </header>

    <!-- Sidebar Drawer -->
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                {% if settings.logo_url %}<img src="{{ settings.logo_url }}" style="width:32px; height:32px; border-radius:50%; border:1px solid var(--accent-gold);">{% endif %}
                <h3 style="margin:0; font-size:16px;">Navigation</h3>
            </div>
            <span class="close-sidebar" onclick="toggleSidebar()">&times;</span>
        </div>
        
        <div id="sidebar-main-view">
            <p style="font-size: 13px; color: #666; margin-bottom: 25px;">How can we assist you today?</p>
            <button class="menu-item" onclick="switchSidebarView('track')"><i class="fa-solid fa-map-location-dot"></i> Track Order</button>
            <button class="menu-item" onclick="switchSidebarView('support')"><i class="fa-solid fa-headset"></i> Help & Support</button>
            <button class="menu-item" onclick="switchSidebarView('faq')"><i class="fa-solid fa-circle-question"></i> Product FAQs</button>
            <a href="/admin" class="menu-item" style="text-decoration:none; margin-top:20px; background:#f4efe6; border-color:var(--accent-gold);"><i class="fa-solid fa-user-shield"></i> Admin Panel Access</a>
        </div>

        <div id="sidebar-track-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Track Order Status</h3>
            <input type="text" id="track-input" placeholder="Order ID (e.g., KESH-12345) or Email">
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
            <h4 style="font-size: 13px; color: var(--green-primary);">2. How do I track my delivery?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Use the Track Order tab with your Order ID or email.</p>
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
        <div class="product-grid" id="main-product-grid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-img-container"><img src="{{ p.image }}" alt="{{ p.name }}" id="img-{{ p.id }}"></div>
                <div class="product-info">
                    <h3 style="color:var(--green-primary); font-size:16px; margin-bottom:5px;">{{ p.name }}</h3>
                    <p style="font-size:12px; color:#666; margin-bottom:10px;">{{ p.desc }}</p>
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
                <h3>{{ settings.brand_name }}</h3>
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
            &copy; 2026 {{ settings.brand_name }} Botanical Remedies. All Rights Reserved.
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
                        <input type="email" id="cust-email" class="full-width" placeholder="Email Address *" required>
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
            if(!p) return;
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
            let p = productsData.find(x => x.id === id);
            if(p) {
                cart = [p]; 
                updateCartUI(); 
                openCartModal(); 
            }
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
                .catch(() => console.log("PIN lookup error"));
            }
        }

        function checkSavedAddressAvailability() {
            let saved = localStorage.getItem('kesh_saved_address');
            if(saved) document.getElementById('useSavedAddrBtn').style.display = 'flex';
        }

        function saveAddressToStorage(data) {
            localStorage.setItem('kesh_saved_address', JSON.stringify({
                name: data.name, email: data.email, phone: data.phone, pincode: data.pincode, city: data.city, state: data.state, landmark: data.landmark, street: data.street
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
                    "name": "{{ settings.brand_name }}",
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
                    let ord = data.order;
                    let step = ord.status_step || 1;
                    let pct = ((step - 1) / 4) * 100;

                    d.innerHTML = `
                    <div style="background:#FAF7F0; border:1px solid #EAE5D9; padding:15px; border-radius:12px; font-size:13px;">
                        <h4 style="color:var(--green-primary); margin-bottom:5px;">Order #${ord.order_id}</h4>
                        <p style="font-size:12px; color:#555;"><b>Status:</b> ${ord.status}</p>

                        <div class="track-timeline">
                            <div class="track-timeline-progress" style="width:${pct}%;"></div>
                            <div class="track-step ${step >= 1 ? 'active':''}">1</div>
                            <div class="track-step ${step >= 2 ? 'active':''}">2</div>
                            <div class="track-step ${step >= 3 ? 'active':''}">3</div>
                            <div class="track-step ${step >= 4 ? 'active':''}">4</div>
                            <div class="track-step ${step >= 5 ? 'active':''}">5</div>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:10px; color:#666;">
                            <span>Placed</span><span>Packed</span><span>Shipped</span><span>Out</span><span>Delivered</span>
                        </div>
                    </div>`;
                } else { 
                    d.innerHTML = '<p style="color:#c62828; font-size:12px;">No matching order found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- ORDER SUCCESS TEMPLATE ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmed | {{ settings.brand_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }

        @keyframes popIn { 0% { transform: scale(0.3); opacity: 0; } 70% { transform: scale(1.08); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); } 70% { box-shadow: 0 0 0 20px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }

        .card { background: white; max-width: 550px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 45px; color: white; background: #2e7d32; border-radius: 50%; width: 85px; height: 85px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 25px; animation: popIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards, pulseGlow 2s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 30px; margin-bottom: 8px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        /* Order Status Pipeline Indicator */
        .status-pipeline { display: flex; justify-content: space-between; position: relative; margin: 20px 0 10px 0; }
        .status-pipeline::before { content: ''; position: absolute; top: 12px; left: 8%; width: 84%; height: 3px; background: #e0e0e0; z-index: 1; }
        .pipeline-progress { position: absolute; top: 12px; left: 8%; height: 3px; background: #2e7d32; z-index: 1; transition: width 0.6s ease; }
        .pipe-step { position: relative; z-index: 2; background: white; width: 26px; height: 26px; border-radius: 50%; border: 2px solid #ccc; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #666; }
        .pipe-step.active { border-color: #2e7d32; background: #2e7d32; color: white; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; transition: background 0.2s; }
        .btn-home:hover { background: #2d6a4f; }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Confirmed!</h1>
        <p class="subtitle">Thank you for choosing {{ settings.brand_name }}. Your order is now being processed.</p>

        {% if order %}
        {% set step = order.status_step if order.status_step else 1 %}
        {% set pct = ((step - 1) / 4) * 100 %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Total Paid/Payable:</span><b>₹{{ order.amount }}</b></div>
            <div class="info-row"><span>Payment Mode:</span><b>{{ order.payment_type }}</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 250px; text-align: right;">{{ order.full_address }}</span></div>
            <div class="info-row" style="margin-top:10px; border-top:1px dashed #ddd; padding-top:10px;"><span>Current Status:</span><b style="color:#2e7d32;">{{ order.status }}</b></div>

            <div class="status-pipeline">
                <div class="pipeline-progress" style="width: {{ pct }}%;"></div>
                <div class="pipe-step {% if step >= 1 %}active{% endif %}">1</div>
                <div class="pipe-step {% if step >= 2 %}active{% endif %}">2</div>
                <div class="pipe-step {% if step >= 3 %}active{% endif %}">3</div>
                <div class="pipe-step {% if step >= 4 %}active{% endif %}">4</div>
                <div class="pipe-step {% if step >= 5 %}active{% endif %}">5</div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:10px; color:#666;">
                <span>Placed</span><span>Packed</span><span>Shipped</span><span>Out</span><span>Delivered</span>
            </div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 20px;"><i class="fa-solid fa-envelope"></i> An official invoice & tracking link have been dispatched to your email.</p>
        
        <a href="/" class="btn-home">Continue Shopping</a>
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
    <title>Admin Dashboard | {{ settings.brand_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --admin-bg: #f4f6f9; --sidebar-bg: #1b4332; --card-bg: #ffffff; --text-main: #2b2b2b; --accent: #d4a373; }
        * { margin:0; padding:0; box-sizing:border-box; font-family:'Poppins', sans-serif; }
        body { background: var(--admin-bg); color: var(--text-main); display: flex; min-height: 100vh; }

        /* Sidebar Drawer */
        .admin-sidebar { width: 260px; background: var(--sidebar-bg); color: white; padding: 25px 20px; flex-shrink: 0; transition: all 0.3s ease; position: fixed; height: 100vh; z-index: 100; }
        .admin-sidebar.collapsed { transform: translateX(-260px); }
        .admin-brand { display: flex; align-items: center; gap: 12px; margin-bottom: 35px; }
        .admin-brand img { width: 38px; height: 38px; border-radius: 50%; object-fit: cover; border: 2px solid var(--accent); }
        .admin-brand h2 { font-size: 18px; font-weight: 600; color: white; }

        .nav-item { width: 100%; padding: 12px 15px; background: transparent; border: none; color: #d1d5db; display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 500; border-radius: 10px; cursor: pointer; margin-bottom: 8px; transition: all 0.2s; text-align: left; }
        .nav-item:hover, .nav-item.active { background: rgba(255,255,255,0.12); color: white; }
        .nav-item i { width: 20px; color: var(--accent); }

        /* Main Content */
        .main-wrapper { flex-grow: 1; margin-left: 260px; transition: all 0.3s ease; width: calc(100% - 260px); }
        .main-wrapper.expanded { margin-left: 0; width: 100%; }

        header { background: white; padding: 18px 30px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
        .toggle-btn { font-size: 20px; cursor: pointer; color: var(--sidebar-bg); background: none; border: none; }

        .content-body { padding: 30px; }
        .page-section { display: none; }
        .page-section.active { display: block; }

        .card { background: white; border-radius: 16px; padding: 25px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); margin-bottom: 25px; }
        .card h3 { font-size: 18px; margin-bottom: 20px; color: var(--sidebar-bg); }

        /* Data Tables */
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #fafafa; font-weight: 600; color: #555; }
        
        .badge { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; display: inline-block; }
        .badge-placed { background: #e3f2fd; color: #1976d2; }
        .badge-packed { background: #fff3e0; color: #f57c00; }
        .badge-shipped { background: #e8eaf6; color: #3f51b5; }
        .badge-out { background: #f3e5f5; color: #7b1fa2; }
        .badge-delivered { background: #e8f5e9; color: #388e3c; }

        .status-select { padding: 6px 10px; border-radius: 6px; border: 1px solid #ddd; font-size: 12px; outline: none; }

        /* Forms & Upload UI */
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 5px; color: #555; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; }

        .drop-zone { border: 2px dashed var(--accent); border-radius: 12px; padding: 25px; text-align: center; cursor: pointer; background: #faf8f5; transition: background 0.2s; }
        .drop-zone:hover { background: #f3ede2; }
        .drop-zone img { max-height: 100px; margin-top: 10px; border-radius: 8px; display: none; }

        .btn { padding: 10px 20px; background: var(--sidebar-bg); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; transition: background 0.2s; }
        .btn:hover { background: #2d6a4f; }
        .btn-danger { background: #c62828; }
        .btn-danger:hover { background: #b71c1c; }
        .btn-warning { background: #f57c00; }
        .btn-warning:hover { background: #e65100; }
    </style>
</head>
<body>

    <!-- Sidebar Drawer -->
    <div class="admin-sidebar" id="adminSidebar">
        <div class="admin-brand">
            <img src="{{ settings.logo_url }}" id="admin-logo-preview" alt="Logo">
            <h2>Admin Control</h2>
        </div>
        <button class="nav-item active" onclick="showSection('orders', this)"><i class="fa-solid fa-cart-flatbed"></i> Orders</button>
        <button class="nav-item" onclick="showSection('add-product', this)"><i class="fa-solid fa-plus-circle"></i> Add Product</button>
        <button class="nav-item" onclick="showSection('inventory', this)"><i class="fa-solid fa-boxes-stacked"></i> Inventory</button>
        <button class="nav-item" onclick="showSection('branding', this)"><i class="fa-solid fa-paint-roller"></i> Site Branding</button>
        <a href="/" class="nav-item" style="text-decoration:none; margin-top:30px;"><i class="fa-solid fa-arrow-left"></i> Main Website</a>
    </div>

    <!-- Main Content Area -->
    <div class="main-wrapper" id="mainWrapper">
        <header>
            <button class="toggle-btn" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
            <span style="font-size: 14px; font-weight: 500; color: #666;">Kesh Aadar Management System</span>
        </header>

        <div class="content-body">
            
            <!-- ORDERS SECTION -->
            <div id="orders-section" class="page-section active">
                <div class="card">
                    <h3><i class="fa-solid fa-list-check" style="color:var(--accent);"></i> Live Customer Orders</h3>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Order ID</th>
                                    <th>Customer Details</th>
                                    <th>Delivery Address</th>
                                    <th>Items</th>
                                    <th>Total</th>
                                    <th>Status Pipeline</th>
                                    <th>Update Status</th>
                                </tr>
                            </thead>
                            <tbody id="orders-table-body">
                                <tr><td colspan="7" style="text-align:center; color:#888;">Loading orders...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- ADD PRODUCT SECTION -->
            <div id="add-product-section" class="page-section">
                <div class="card" style="max-width: 650px; margin:0 auto;">
                    <h3><i class="fa-solid fa-square-plus" style="color:var(--accent);"></i> Add New Product</h3>
                    <form id="newProductForm" onsubmit="event.preventDefault(); submitNewProduct();">
                        <div class="form-group">
                            <label>Product Name *</label>
                            <input type="text" id="prod-name" required placeholder="e.g. Pure Organic Kumkumadi Oil">
                        </div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                            <div class="form-group">
                                <label>Price (₹) *</label>
                                <input type="number" id="prod-price" required step="0.01" placeholder="499">
                            </div>
                            <div class="form-group">
                                <label>Initial Stock *</label>
                                <input type="number" id="prod-stock" required placeholder="50">
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Product Description</label>
                            <textarea id="prod-desc" rows="3" placeholder="Brief formulation details..."></textarea>
                        </div>
                        <div class="form-group">
                            <label>Product Image (Drag & Drop or Choose File)</label>
                            <div class="drop-zone" onclick="document.getElementById('prod-img-file').click()">
                                <i class="fa-solid fa-cloud-arrow-up" style="font-size:28px; color:var(--accent);"></i>
                                <p style="font-size:12px; color:#666; margin-top:5px;">Click or Drag & Drop image file here</p>
                                <img id="new-prod-img-preview">
                            </div>
                            <input type="file" id="prod-img-file" accept="image/*" style="display:none;" onchange="handleImageUpload(this, 'new-prod-img-preview')">
                        </div>
                        <button type="submit" class="btn" style="width:100%;">Upload Product to Website</button>
                    </form>
                </div>
            </div>

            <!-- INVENTORY SECTION -->
            <div id="inventory-section" class="page-section">
                <div class="card">
                    <h3><i class="fa-solid fa-boxes-packing" style="color:var(--accent);"></i> Product Inventory Management</h3>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Image</th>
                                    <th>Product Name</th>
                                    <th>Price</th>
                                    <th>Stock Level</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="inventory-table-body">
                                <tr><td colspan="6" style="text-align:center; color:#888;">Loading inventory...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- SITE BRANDING SECTION -->
            <div id="branding-section" class="page-section">
                <div class="card" style="max-width: 550px; margin:0 auto;">
                    <h3><i class="fa-solid fa-pen-ruler" style="color:var(--accent);"></i> Website Branding & Logo</h3>
                    <form onsubmit="event.preventDefault(); saveSiteBranding();">
                        <div class="form-group">
                            <label>Brand Name</label>
                            <input type="text" id="brand-title-input" value="{{ settings.brand_name }}">
                        </div>
                        <div class="form-group">
                            <label>Upload Brand Logo</label>
                            <div class="drop-zone" onclick="document.getElementById('logo-file-input').click()">
                                <i class="fa-solid fa-image" style="font-size:28px; color:var(--accent);"></i>
                                <p style="font-size:12px; color:#666; margin-top:5px;">Upload custom website logo from gallery</p>
                                <img id="branding-logo-preview" src="{{ settings.logo_url }}" style="display:block; margin:10px auto;">
                            </div>
                            <input type="file" id="logo-file-input" accept="image/*" style="display:none;" onchange="handleImageUpload(this, 'branding-logo-preview')">
                        </div>
                        <button type="submit" class="btn" style="width:100%;">Save Brand Changes</button>
                    </form>
                </div>
            </div>

        </div>
    </div>

    <!-- EDIT INVENTORY MODAL -->
    <div id="editProdModal" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); display:none; justify-content:center; align-items:center; z-index:2000;">
        <div style="background:white; padding:25px; border-radius:15px; width:100%; max-width:450px;">
            <h3 style="margin-bottom:15px; color:var(--sidebar-bg);">Edit Product Stock / Details</h3>
            <form onsubmit="event.preventDefault(); saveProductEdit();">
                <input type="hidden" id="edit-prod-id">
                <div class="form-group">
                    <label>Product Name</label>
                    <input type="text" id="edit-prod-name" required>
                </div>
                <div class="form-group">
                    <label>Price (₹)</label>
                    <input type="number" id="edit-prod-price" required step="0.01">
                </div>
                <div class="form-group">
                    <label>Stock Quantity</label>
                    <input type="number" id="edit-prod-stock" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="edit-prod-desc" rows="2"></textarea>
                </div>
                <div style="display:flex; gap:10px; margin-top:20px;">
                    <button type="submit" class="btn" style="flex:1;">Save Changes</button>
                    <button type="button" class="btn btn-danger" style="flex:1;" onclick="document.getElementById('editProdModal').style.display='none'">Cancel</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let uploadedImages = {};

        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('collapsed');
            document.getElementById('mainWrapper').classList.toggle('expanded');
        }

        function showSection(sec, btn) {
            document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
            
            document.getElementById(sec + '-section').classList.add('active');
            if(btn) btn.classList.add('active');

            if(sec === 'orders') fetchOrders();
            if(sec === 'inventory') fetchInventory();
        }

        function handleImageUpload(input, previewId) {
            if(input.files && input.files[0]) {
                let reader = new FileReader();
                reader.onload = function(e) {
                    let preview = document.getElementById(previewId);
                    preview.src = e.target.result;
                    preview.style.display = 'block';
                    uploadedImages[previewId] = e.target.result;
                };
                reader.readAsDataURL(input.files[0]);
            }
        }

        // Fetch and Render Orders
        function fetchOrders() {
            fetch('/api/admin/orders')
            .then(r => r.json())
            .then(data => {
                let tbody = document.getElementById('orders-table-body');
                tbody.innerHTML = '';
                if(data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#888;">No orders placed yet.</td></tr>';
                    return;
                }
                data.reverse().forEach(o => {
                    let itemsList = o.items ? o.items.map(i => i.name).join(', ') : 'N/A';
                    let badgeClass = 'badge-' + (o.status ? o.status.toLowerCase().split(' ')[0] : 'placed');

                    tbody.innerHTML += `
                    <tr>
                        <td><b style="font-family:monospace; color:var(--sidebar-bg);">${o.order_id}</b><br><span style="font-size:10px; color:#888;">${o.date || ''}</span></td>
                        <td><b>${o.name}</b><br><span style="font-size:11px; color:#666;">${o.phone}</span><br><span style="font-size:11px; color:#666;">${o.email}</span></td>
                        <td style="max-width:180px; font-size:11px;">${o.full_address || ''}</td>
                        <td style="font-size:11px;">${itemsList}</td>
                        <td><b>₹${o.amount}</b><br><span style="font-size:10px; color:#666;">${o.payment_type}</span></td>
                        <td><span class="badge ${badgeClass}">${o.status || 'Placed'}</span></td>
                        <td>
                            <select class="status-select" onchange="updateOrderStatus('${o.order_id}', this.value)">
                                <option value="Placed" ${o.status==='Placed'?'selected':''}>Placed</option>
                                <option value="Packed" ${o.status==='Packed'?'selected':''}>Packed</option>
                                <option value="Shipped" ${o.status==='Shipped'?'selected':''}>Shipped</option>
                                <option value="Out for Delivery" ${o.status==='Out for Delivery'?'selected':''}>Out for Delivery</option>
                                <option value="Delivered" ${o.status==='Delivered'?'selected':''}>Delivered</option>
                            </select>
                        </td>
                    </tr>`;
                });
            });
        }

        function updateOrderStatus(order_id, status) {
            fetch('/api/admin/order/update_status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ order_id, status })
            })
            .then(r => r.json())
            .then(() => fetchOrders());
        }

        // Product Upload
        function submitNewProduct() {
            let name = document.getElementById('prod-name').value;
            let price = document.getElementById('prod-price').value;
            let stock = document.getElementById('prod-stock').value;
            let desc = document.getElementById('prod-desc').value;
            let image = uploadedImages['new-prod-img-preview'] || 'https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80';

            fetch('/api/admin/products', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name, price, stock, desc, image })
            })
            .then(r => r.json())
            .then(() => {
                alert('Product successfully added live to store!');
                document.getElementById('newProductForm').reset();
                document.getElementById('new-prod-img-preview').style.display = 'none';
                delete uploadedImages['new-prod-img-preview'];
            });
        }

        // Inventory Management
        function fetchInventory() {
            fetch('/api/admin/products')
            .then(r => r.json())
            .then(data => {
                let tbody = document.getElementById('inventory-table-body');
                tbody.innerHTML = '';
                data.forEach(p => {
                    let statusBadge = p.status === 'suspended' ? 
                        '<span class="badge" style="background:#ffebee; color:#c62828;">Suspended</span>' : 
                        '<span class="badge" style="background:#e8f5e9; color:#2e7d32;">Active</span>';

                    tbody.innerHTML += `
                    <tr>
                        <td><img src="${p.image}" style="width:40px; height:40px; border-radius:8px; object-fit:cover;"></td>
                        <td><b>${p.name}</b></td>
                        <td>₹${p.price}</td>
                        <td><b>${p.stock} units</b></td>
                        <td>${statusBadge}</td>
                        <td>
                            <button class="btn" style="padding:4px 8px; font-size:11px;" onclick="openEditModal(${p.id}, '${p.name}', ${p.price}, ${p.stock}, '${p.desc || ''}')">Edit</button>
                            <button class="btn btn-warning" style="padding:4px 8px; font-size:11px;" onclick="toggleSuspendProduct(${p.id}, '${p.status}')">${p.status === 'suspended' ? 'Unsuspend' : 'Suspend'}</button>
                            <button class="btn btn-danger" style="padding:4px 8px; font-size:11px;" onclick="deleteProduct(${p.id})">Delete</button>
                        </td>
                    </tr>`;
                });
            });
        }

        function openEditModal(id, name, price, stock, desc) {
            document.getElementById('edit-prod-id').value = id;
            document.getElementById('edit-prod-name').value = name;
            document.getElementById('edit-prod-price').value = price;
            document.getElementById('edit-prod-stock').value = stock;
            document.getElementById('edit-prod-desc').value = desc;
            document.getElementById('editProdModal').style.display = 'flex';
        }

        function saveProductEdit() {
            let id = parseInt(document.getElementById('edit-prod-id').value);
            let name = document.getElementById('edit-prod-name').value;
            let price = parseFloat(document.getElementById('edit-prod-price').value);
            let stock = parseInt(document.getElementById('edit-prod-stock').value);
            let desc = document.getElementById('edit-prod-desc').value;

            fetch('/api/admin/products', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, name, price, stock, desc })
            })
            .then(r => r.json())
            .then(() => {
                document.getElementById('editProdModal').style.display = 'none';
                fetchInventory();
            });
        }

        function toggleSuspendProduct(id, currentStatus) {
            let newStatus = currentStatus === 'suspended' ? 'active' : 'suspended';
            fetch('/api/admin/products', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id, status: newStatus })
            })
            .then(r => r.json())
            .then(() => fetchInventory());
        }

        function deleteProduct(id) {
            if(confirm('Are you sure you want to permanently delete this product?')) {
                fetch('/api/admin/products', {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id })
                })
                .then(r => r.json())
                .then(() => fetchInventory());
            }
        }

        // Site Branding Save
        function saveSiteBranding() {
            let brand_name = document.getElementById('brand-title-input').value;
            let logo_url = uploadedImages['branding-logo-preview'];

            let payload = { brand_name };
            if(logo_url) payload.logo_url = logo_url;

            fetch('/api/admin/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(data => {
                alert('Site branding updated successfully!');
                if(data.settings.logo_url) {
                    document.getElementById('admin-logo-preview').src = data.settings.logo_url;
                }
            });
        }

        // Initialize
        fetchOrders();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
