from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import random
import os

app = Flask(__name__)
app.secret_key = 'kesh_aadar_secure_key_2026'

# --- PERSISTENT STORAGE FOR VERCEL (/tmp) ---
DB_FILE = '/tmp/kesh_db.json'

def load_db():
    default_data = {
        "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
        "products": [
            {"id": 1, "name": "Aloe Neem Glow Face Wash", "category": "Skincare", "price": 349, "stock": 50, "status": "Live", "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", "desc": "Deep cleansing herbal formula for radiant skin."},
            {"id": 2, "name": "Saffron Kumkumadi Night Serum", "category": "Skincare", "price": 799, "stock": 30, "status": "Live", "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", "desc": "Fades blemishes and restores natural skin glow."},
            {"id": 3, "name": "Bhringraj Onion Hair Growth Oil", "category": "Haircare", "price": 499, "stock": 40, "status": "Live", "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", "desc": "Stops hair fall and stimulates roots naturally."},
            {"id": 4, "name": "Hibiscus & Shikakai Herbal Shampoo", "category": "Haircare", "price": 399, "stock": 45, "status": "Live", "image": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80", "desc": "Nourishing sulfate-free cleanser for smooth hair."}
        ],
        "orders": [],
        "blacklisted_ips": []
    }
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_data
    return default_data

def save_db(data):
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving DB: {e}")

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "subhraroy324@gmail.com"
SMTP_PASS = "idxv jjob guit vtfb"

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
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block;">Check Live Order Status</a>
                </div>
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

@app.before_request
def check_ip_blacklist():
    db = load_db()
    client_ip = request.remote_addr
    if client_ip in db.get('blacklisted_ips', []):
        return jsonify({"error": "Your IP has been blacklisted by administrator."}), 403

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    db = load_db()
    live_products = [p for p in db['products'] if p.get('status', 'Live') == 'Live']
    return render_template_string(TEMPLATE, products=live_products, logo=db['logo'])

@app.route('/place_order', methods=['POST'])
def place_order():
    db = load_db()
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status'] = 'Order Placed' # Initial Status
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    db['orders'].insert(0, data)
    save_db(db)
    
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address)
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    db = load_db()
    order = next((o for o in db['orders'] if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, logo=db['logo'])

@app.route('/track_order')
def track_order():
    db = load_db()
    q = request.args.get('q', '').strip()
    for o in db['orders']:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order": o})
    return jsonify({"found": False})

# --- ADMIN PANEL ROUTES (/admin) ---
@app.route('/admin')
def admin_panel():
    db = load_db()
    return render_template_string(ADMIN_TEMPLATE, db=db)

@app.route('/admin/api/update_order_status', methods=['POST'])
def admin_update_order_status():
    db = load_db()
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status') # 'Order Placed', 'Packaging', 'Shipped', 'Delivered'
    for o in db['orders']:
        if o['order_id'] == order_id:
            o['status'] = new_status
            save_db(db)
            return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/admin/api/save_logo', methods=['POST'])
def admin_save_logo():
    db = load_db()
    data = request.get_json()
    db['logo'] = data.get('logo_url')
    save_db(db)
    return jsonify({"success": True})

@app.route('/admin/api/products', methods=['GET', 'POST', 'PUT', 'DELETE'])
def admin_manage_products():
    db = load_db()
    if request.method == 'GET':
        return jsonify(db['products'])
    
    data = request.get_json()
    if request.method == 'POST':
        # Add new product
        new_id = max([p['id'] for p in db['products']], default=0) + 1
        new_prod = {
            "id": new_id,
            "name": data.get('name'),
            "category": data.get('category', 'Skincare'),
            "price": float(data.get('price', 0)),
            "stock": int(data.get('stock', 10)),
            "status": data.get('status', 'Live'),
            "image": data.get('image'),
            "desc": data.get('desc', '')
        }
        db['products'].append(new_prod)
        save_db(db)
        return jsonify({"success": True, "product": new_prod})

    elif request.method == 'PUT':
        # Edit or Suspend product
        prod_id = int(data.get('id'))
        for p in db['products']:
            if p['id'] == prod_id:
                p['name'] = data.get('name', p['name'])
                p['category'] = data.get('category', p['category'])
                p['price'] = float(data.get('price', p['price']))
                p['stock'] = int(data.get('stock', p['stock']))
                p['status'] = data.get('status', p['status']) # 'Live' or 'Suspended'
                p['image'] = data.get('image', p['image'])
                p['desc'] = data.get('desc', p['desc'])
                save_db(db)
                return jsonify({"success": True})
        return jsonify({"success": False}), 404

    elif request.method == 'DELETE':
        prod_id = int(data.get('id'))
        db['products'] = [p for p in db['products'] if p['id'] != prod_id]
        save_db(db)
        return jsonify({"success": True})

@app.route('/admin/api/orders_list')
def admin_orders_list():
    db = load_db()
    return jsonify(db['orders'])


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

        .reveal { opacity: 0; transform: translateY(40px); transition: all 0.9s cubic-bezier(0.16, 1, 0.3, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }

        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.05); }
        .nav-left { display: flex; align-items: center; gap: 15px; }
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; transition: transform 0.3s; }
        .menu-btn:hover { transform: scale(1.1); }
        
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: transform 0.3s; }
        .cart-icon-container:hover { transform: scale(1.05); }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Smoothed Sidebar Drawer Animation */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: background 0.2s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); transition: transform 0.2s; }
        .close-sidebar:hover { transform: rotate(90deg); }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); }

        /* Hero */
        .hero { height: 80vh; display: flex; align-items: center; justify-content: center; text-align: center; background: radial-gradient(circle, #f3efea 0%, #faf7f0 75%); margin-top: 70px; padding: 0 20px; }
        .hero-content h1 { font-family: 'Playfair Display', serif; font-size: clamp(34px, 6vw, 54px); color: var(--green-primary); margin-bottom: 15px; }
        .btn-primary { background: var(--green-primary); color: white; padding: 14px 38px; border-radius: 35px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: all 0.3s; }
        .btn-primary:hover { background: var(--green-light); transform: translateY(-2px); box-shadow: 0 5px 15px rgba(27,67,50,0.3); }

        .features-banner { background: var(--green-primary); color: white; display: flex; justify-content: space-around; padding: 20px; flex-wrap: wrap; gap: 15px; }
        .feature-item { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 500; }

        /* Products Grid */
        .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 30px; }
        .product-card { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); transition: transform 0.3s, box-shadow 0.3s; }
        .product-card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
        .product-img-container { height: 230px; overflow: hidden; background: #f7f5f0; }
        .product-img-container img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s; }
        .product-card:hover .product-img-container img { transform: scale(1.05); }
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

        /* Tracking Timeline in Modal/Result */
        .tracking-timeline { margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 10px; }
        .step-item { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; font-size: 13px; color: #777; font-weight: 500; }
        .step-item.active { color: var(--green-primary); font-weight: 600; }
        .step-circle { width: 24px; height: 24px; border-radius: 50%; background: #ddd; color: white; display: flex; align-items: center; justify-content: center; font-size: 11px; }
        .step-item.active .step-circle { background: var(--green-primary); }

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
            <h4 style="font-size: 13px; color: var(--green-primary);">2. How do I track my delivery?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">You will receive live tracking updates on your email and tracking portal.</p>
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
                    }
                })
                .catch(() => console.log("PIN lookup offline"));
            }
        }

        function checkSavedAddressAvailability() {
            if(localStorage.getItem('kesh_saved_address')) {
                document.getElementById('useSavedAddrBtn').style.display = 'flex';
            }
        }

        function saveAddressToStorage(data) {
            localStorage.setItem('kesh_saved_address', JSON.stringify(data));
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
                    let o = data.order;
                    let st = o.status || 'Order Placed';
                    let steps = ['Order Placed', 'Packaging', 'Shipped', 'Delivered'];
                    let currentIdx = steps.indexOf(st);
                    if(currentIdx === -1) currentIdx = 0;

                    let timelineHtml = '<div class="tracking-timeline">';
                    steps.forEach((step, idx) => {
                        let activeClass = idx <= currentIdx ? 'active' : '';
                        timelineHtml += `
                        <div class="step-item ${activeClass}">
                            <div class="step-circle">${idx <= currentIdx ? '<i class="fa-solid fa-check" style="font-size:10px;"></i>' : idx+1}</div>
                            <span>${step}</span>
                        </div>`;
                    });
                    timelineHtml += '</div>';

                    d.innerHTML = `<div style="background:#e8f5e9; padding:15px; border-radius:10px; font-size:13px;"><h4 style="color:#2e7d32; margin-bottom:5px;">Order: ${o.order_id}</h4><p><b>Status:</b> ${st}</p>${timelineHtml}</div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px; margin-top:10px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- SUCCESS PAGE TEMPLATE ---
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

        @keyframes popIn { 0% { transform: scale(0.3); opacity: 0; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); } 70% { box-shadow: 0 0 0 25px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }

        .card { background: white; max-width: 550px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 50px; color: white; background: #2e7d32; border-radius: 50%; width: 90px; height: 90px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 25px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 32px; margin-bottom: 8px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; transition: background 0.3s; }
        .btn-home:hover { background: #2d6a4f; }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Confirmed!</h1>
        <p class="subtitle">Thank you for choosing Kesh Aadar. Your order is being processed.</p>

        {% if order %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Total Amount:</span><b>₹{{ order.amount }}</b></div>
            <div class="info-row"><span>Payment Mode:</span><b>{{ order.payment_type }}</b></div>
            <div class="info-row"><span>Shipping Status:</span><b style="color:#2e7d32;">{{ order.status }}</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 250px; text-align: right;">{{ order.full_address }}</span></div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 20px;"><i class="fa-solid fa-envelope"></i> Official invoice & tracking details sent to your email.</p>
        
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; --bg-light: #f4f6f8; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--bg-light); color: #333; display: flex; height: 100vh; overflow: hidden; }

        /* Admin Sidebar */
        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; display: flex; flex-direction: column; padding: 25px 20px; transition: transform 0.4s ease; z-index: 100; }
        .admin-sidebar h2 { font-size: 20px; color: var(--accent-gold); margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; }
        .admin-sidebar .close-sidebar-btn { display: none; font-size: 22px; cursor: pointer; }
        .admin-nav-btn { background: none; border: none; color: #bbb; padding: 12px 15px; text-align: left; font-size: 14px; font-weight: 500; border-radius: 8px; cursor: pointer; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .admin-nav-btn:hover, .admin-nav-btn.active { background: rgba(255,255,255,0.1); color: white; }
        .admin-nav-btn i { color: var(--accent-gold); width: 20px; }

        /* Main Admin Content */
        .admin-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .admin-header { background: white; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        .mobile-toggle { display: none; font-size: 22px; background: none; border: none; cursor: pointer; color: var(--green-primary); }
        
        .admin-content { flex: 1; overflow-y: auto; padding: 30px; }
        .section-panel { display: none; }
        .section-panel.active { display: block; }

        .card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 5px 20px rgba(0,0,0,0.03); margin-bottom: 25px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #fafafa; color: #555; font-weight: 600; }
        
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge-live { background: #e8f5e9; color: #2e7d32; }
        .badge-suspended { background: #ffebee; color: #c62828; }

        .btn { padding: 8px 14px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; font-size: 12px; }
        .btn-green { background: var(--green-primary); color: white; }
        .btn-red { background: #c62828; color: white; }
        .btn-outline { background: none; border: 1px solid #ccc; color: #333; }

        .form-control { width: 100%; padding: 10px 14px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; }

        @media (max-width: 768px) {
            .admin-sidebar { position: fixed; height: 100%; left: -260px; }
            .admin-sidebar.active { left: 0; }
            .admin-sidebar .close-sidebar-btn { display: block; }
            .mobile-toggle { display: block; }
        }
    </style>
</head>
<body>

    <div class="admin-sidebar" id="adminSidebar">
        <h2>Kesh Aadar Admin <i class="fa-solid fa-xmark close-sidebar-btn" onclick="toggleAdminSidebar()"></i></h2>
        <button class="admin-nav-btn active" onclick="switchTab('orders', this)"><i class="fa-solid fa-box-open"></i> Orders</button>
        <button class="admin-nav-btn" onclick="switchTab('products', this)"><i class="fa-solid fa-store"></i> Products Inventory</button>
        <button class="admin-nav-btn" onclick="switchTab('settings', this)"><i class="fa-solid fa-gear"></i> Website Logo</button>
        <a href="/" target="_blank" class="admin-nav-btn" style="margin-top: auto; text-decoration: none;"><i class="fa-solid fa-external-link"></i> View Storefront</a>
    </div>

    <div class="admin-main">
        <div class="admin-header">
            <div style="display:flex; align-items:center; gap:15px;">
                <button class="mobile-toggle" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
                <h3 style="color:var(--green-primary); font-size: 18px;" id="header-title">Orders Management</h3>
            </div>
            <span style="font-size: 13px; color: #666;"><i class="fa-solid fa-user-shield"></i> Administrator</span>
        </div>

        <div class="admin-content">
            
            <!-- ORDERS PANEL -->
            <div class="section-panel active" id="panel-orders">
                <div class="card">
                    <h3 style="margin-bottom: 15px; color:var(--green-primary);">Customer Orders</h3>
                    <div style="overflow-x:auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Order ID</th>
                                    <th>Customer Details</th>
                                    <th>Items</th>
                                    <th>Amount</th>
                                    <th>Address</th>
                                    <th>Status (Update)</th>
                                </tr>
                            </thead>
                            <tbody id="orders-table-body">
                                <!-- Populated dynamically -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- PRODUCTS / INVENTORY PANEL -->
            <div class="section-panel" id="panel-products">
                <div class="card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                        <h3 style="color:var(--green-primary);">Inventory & Products</h3>
                        <button class="btn btn-green" onclick="openAddProductModal()"><i class="fa-solid fa-plus"></i> Add Product</button>
                    </div>
                    <div style="overflow-x:auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Image</th>
                                    <th>Name</th>
                                    <th>Category</th>
                                    <th>Price</th>
                                    <th>Stock</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="products-table-body">
                                <!-- Populated dynamically -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- SETTINGS / LOGO PANEL -->
            <div class="section-panel" id="panel-settings">
                <div class="card" style="max-width: 500px;">
                    <h3 style="margin-bottom: 15px; color:var(--green-primary);">Change Website Profile Logo</h3>
                    <p style="font-size: 12px; color: #666; margin-bottom: 15px;">Paste your image direct URL or upload to an image hosting service and paste link below.</p>
                    <label style="font-size: 12px; font-weight:600;">Logo Image URL:</label>
                    <input type="text" id="logo-url-input" class="form-control" value="{{ db.logo }}" style="margin-top: 5px;">
                    <button class="btn btn-green" onclick="saveLogo()">Update Logo</button>
                </div>
            </div>

        </div>
    </div>

    <!-- ADD/EDIT PRODUCT MODAL -->
    <div class="modal" id="productModal" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); display:none; justify-content:center; align-items:center; z-index:3000;">
        <div style="background:white; width:100%; max-width:450px; padding:25px; border-radius:12px; position:relative;">
            <span style="position:absolute; right:20px; top:20px; cursor:pointer; font-size:22px;" onclick="closeProductModal()">&times;</span>
            <h3 id="modal-product-title" style="color:var(--green-primary); margin-bottom:15px;">Add Product</h3>
            <input type="hidden" id="prod-edit-id">
            <label style="font-size:12px; font-weight:600;">Product Name</label>
            <input type="text" id="prod-name" class="form-control" style="margin-top:5px;">
            <div style="display:flex; gap:10px;">
                <div style="flex:1;"><label style="font-size:12px; font-weight:600;">Price (₹)</label><input type="number" id="prod-price" class="form-control" style="margin-top:5px;"></div>
                <div style="flex:1;"><label style="font-size:12px; font-weight:600;">Stock</label><input type="number" id="prod-stock" class="form-control" style="margin-top:5px;"></div>
            </div>
            <label style="font-size:12px; font-weight:600;">Category</label>
            <input type="text" id="prod-category" class="form-control" value="Skincare" style="margin-top:5px;">
            <label style="font-size:12px; font-weight:600;">Image URL</label>
            <input type="text" id="prod-image" class="form-control" style="margin-top:5px;">
            <label style="font-size:12px; font-weight:600;">Description</label>
            <textarea id="prod-desc" class="form-control" rows="2" style="margin-top:5px;"></textarea>
            <button class="btn btn-green" style="width:100%; padding:12px;" onclick="submitProductForm()">Save Product</button>
        </div>
    </div>

    <script>
        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('active');
        }

        function switchTab(tab, btn) {
            document.querySelectorAll('.section-panel').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.admin-nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById('panel-' + tab).classList.add('active');
            btn.classList.add('active');
            document.getElementById('header-title').innerText = btn.innerText;
            if(window.innerWidth <= 768) toggleAdminSidebar();
        }

        // Fetch Orders
        function loadOrders() {
            fetch('/admin/api/orders_list')
            .then(res => res.json())
            .then(orders => {
                let tbody = document.getElementById('orders-table-body');
                tbody.innerHTML = '';
                if(orders.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#888;">No orders received yet.</td></tr>';
                    return;
                }
                orders.forEach(o => {
                    let itemsStr = o.items.map(i => `${i.name} (₹${i.price})`).join(', ');
                    let statuses = ['Order Placed', 'Packaging', 'Shipped', 'Delivered'];
                    let selectHtml = `<select class="form-control" style="margin:0; padding:6px;" onchange="updateOrderStatus('${o.order_id}', this.value)">`;
                    statuses.forEach(st => {
                        let sel = (o.status === st) ? 'selected' : '';
                        selectHtml += `<option value="${st}" ${sel}>${st}</option>`;
                    });
                    selectHtml += `</select>`;

                    tbody.innerHTML += `
                    <tr>
                        <td><b>${o.order_id}</b><br><small style="color:#777;">${o.date}</small></td>
                        <td><b>${o.name}</b><br>${o.phone}<br>${o.email}</td>
                        <td><small>${itemsStr}</small></td>
                        <td><b>₹${o.amount}</b><br><small>${o.payment_type}</small></td>
                        <td><small>${o.full_address}</small></td>
                        <td>${selectHtml}</td>
                    </tr>`;
                });
            });
        }

        function updateOrderStatus(orderId, status) {
            fetch('/admin/api/update_order_status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({order_id: orderId, status: status})
            }).then(r => r.json()).then(d => {
                if(d.success) alert("Order status updated successfully!");
            });
        }

        // Fetch Products
        function loadProducts() {
            fetch('/admin/api/products')
            .then(res => res.json())
            .then(products => {
                let tbody = document.getElementById('products-table-body');
                tbody.innerHTML = '';
                products.forEach(p => {
                    let isLive = (p.status || 'Live') === 'Live';
                    let badgeClass = isLive ? 'badge-live' : 'badge-suspended';
                    let toggleText = isLive ? 'Suspend' : 'Make Live';
                    let toggleBtnClass = isLive ? 'btn-red' : 'btn-green';

                    tbody.innerHTML += `
                    <tr>
                        <td><img src="${p.image}" width="40" height="40" style="object-fit:cover; border-radius:6px;"></td>
                        <td><b>${p.name}</b></td>
                        <td>${p.category}</td>
                        <td>₹${p.price}</td>
                        <td>${p.stock}</td>
                        <td><span class="badge ${badgeClass}">${p.status || 'Live'}</span></td>
                        <td>
                            <button class="btn btn-outline" onclick='openEditProduct(${JSON.stringify(p)})'>Edit</button>
                            <button class="btn ${toggleBtnClass}" onclick="toggleProductStatus(${p.id}, '${isLive ? 'Suspended' : 'Live'}')">${toggleText}</button>
                            <button class="btn btn-red" onclick="deleteProduct(${p.id})"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>`;
                });
            });
        }

        function openAddProductModal() {
            document.getElementById('modal-product-title').innerText = 'Add New Product';
            document.getElementById('prod-edit-id').value = '';
            document.getElementById('prod-name').value = '';
            document.getElementById('prod-price').value = '';
            document.getElementById('prod-stock').value = '';
            document.getElementById('prod-category').value = 'Skincare';
            document.getElementById('prod-image').value = '';
            document.getElementById('prod-desc').value = '';
            document.getElementById('productModal').style.display = 'flex';
        }

        function openEditProduct(p) {
            document.getElementById('modal-product-title').innerText = 'Edit Product';
            document.getElementById('prod-edit-id').value = p.id;
            document.getElementById('prod-name').value = p.name;
            document.getElementById('prod-price').value = p.price;
            document.getElementById('prod-stock').value = p.stock;
            document.getElementById('prod-category').value = p.category;
            document.getElementById('prod-image').value = p.image;
            document.getElementById('prod-desc').value = p.desc;
            document.getElementById('productModal').style.display = 'flex';
        }

        function closeProductModal() {
            document.getElementById('productModal').style.display = 'none';
        }

        function submitProductForm() {
            let id = document.getElementById('prod-edit-id').value;
            let payload = {
                id: id ? parseInt(id) : null,
                name: document.getElementById('prod-name').value,
                price: document.getElementById('prod-price').value,
                stock: document.getElementById('prod-stock').value,
                category: document.getElementById('prod-category').value,
                image: document.getElementById('prod-image').value,
                desc: document.getElementById('prod-desc').value,
                status: 'Live'
            };

            let method = id ? 'PUT' : 'POST';
            fetch('/admin/api/products', {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(d => {
                if(d.success) {
                    closeProductModal();
                    loadProducts();
                }
            });
        }

        function toggleProductStatus(id, newStatus) {
            fetch('/admin/api/products', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id, status: newStatus})
            }).then(r => r.json()).then(d => {
                if(d.success) loadProducts();
            });
        }

        function deleteProduct(id) {
            if(confirm("Are you sure you want to delete this product?")) {
                fetch('/admin/api/products', {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: id})
                }).then(r => r.json()).then(d => {
                    if(d.success) loadProducts();
                });
            }
        }

        function saveLogo() {
            let logoUrl = document.getElementById('logo-url-input').value;
            fetch('/admin/api/save_logo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({logo_url: logoUrl})
            }).then(r => r.json()).then(d => {
                if(d.success) alert("Website logo updated successfully!");
            });
        }

        // Initial Load
        loadOrders();
        loadProducts();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Kesh Aadar Flask Server Running...")
    app.run(host='0.0.0.0', port=5000, debug=True)
