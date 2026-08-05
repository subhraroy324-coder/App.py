from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'kesh_aadar_secure_key_2026'

# --- CONFIGURATION & STORAGE ---
UPLOAD_FOLDER = '/tmp' if os.environ.get('VERCEL') else 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "keshaadar@gmail.com"
SMTP_PASS = "zvxb mrbs ccoi vfrl"

# In-Memory State (For persistent DB production, attach SQLite/Supabase)
PRODUCTS = [
    {
        "id": 1, 
        "name": "Aloe Neem Glow Face Wash", 
        "category": "Skincare", 
        "price": 349, 
        "stock": 50, 
        "media": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", 
        "media_type": "image",
        "desc": "Deep cleansing herbal formula for radiant skin."
    },
    {
        "id": 2, 
        "name": "Bhringraj Onion Hair Growth Oil", 
        "category": "Haircare", 
        "price": 499, 
        "stock": 40, 
        "media": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", 
        "media_type": "image",
        "desc": "Stops hair fall and stimulates roots naturally."
    }
]

ORDERS = []
STORE_CONFIG = {
    "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80"
}

# --- BACKGROUND EMAIL DISPATCHER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, payment_type):
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
                <p style="font-size: 14px; color: #555; line-height: 1.6;">Your order has been placed successfully and is being prepared.</p>
                
                <div style="background: #F3EFEA; padding: 20px; border-radius: 12px; margin: 25px 0; border: 1px dashed #d4a373;">
                    <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">Order Reference ID</p>
                    <h3 style="margin: 8px 0; font-size: 28px; color: #1b4332; font-family: monospace;">{order_id}</h3>
                    <p style="margin: 5px 0; color: #333; font-size: 14px; font-weight: 600;">Total Bill: ₹{amount} ({payment_type})</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;"><b>Shipping Address:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 5px 15px rgba(27, 67, 50, 0.3);">Track Your Order Live</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Questions? Contact customer care at {SMTP_EMAIL}</p>
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
        print(f"Email failed: {e}")

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    active_products = [p for p in PRODUCTS if p.get('status', 'live') == 'live']
    return render_template_string(TEMPLATE, products=active_products, logo=STORE_CONFIG['logo'])

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KA-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['status_step'] = 1 # 1: Placed, 2: Packaging, 3: Shipped, 4: Delivered
    data['status_text'] = 'Order Placed'
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', 'N/A')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.append(data)
    
    # Fire confirmation email asynchronously
    threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, data['payment_type'])
    ).start()
    
    return jsonify({"status": "success", "order_id": order_id})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id)

@app.route('/track_order')
def track_order_api():
    q = request.args.get('q', '').strip().upper()
    order = next((o for o in ORDERS if o['order_id'] == q or o['email'].upper() == q), None)
    if order:
        return jsonify({"found": True, "order": order})
    return jsonify({"found": False})

# --- HIDDEN ADMIN PANEL ROUTE ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    global PRODUCTS, STORE_CONFIG
    msg = None
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_status':
            oid = request.form.get('order_id')
            step = int(request.form.get('step', 1))
            status_labels = {1: "Order Placed", 2: "Packaging Products", 3: "Shipped", 4: "Delivered"}
            for o in ORDERS:
                if o['order_id'] == oid:
                    o['status_step'] = step
                    o['status_text'] = status_labels.get(step, "Processing")
            msg = f"Order {oid} updated to step {step}."

        elif action == 'add_product':
            name = request.form.get('name')
            category = request.form.get('category')
            price = float(request.form.get('price', 0))
            stock = int(request.form.get('stock', 0))
            desc = request.form.get('desc')
            
            file = request.files.get('media_file')
            media_url = "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=500&q=80"
            media_type = "image"
            
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                media_url = f"/uploads/{filename}"
                if filename.lower().endswith(('.mp4', '.mov', '.webm', '.avi')):
                    media_type = "video"

            new_prod = {
                "id": len(PRODUCTS) + 1,
                "name": name,
                "category": category,
                "price": price,
                "stock": stock,
                "desc": desc,
                "media": media_url,
                "media_type": media_type,
                "status": "live"
            }
            PRODUCTS.append(new_prod)
            msg = "Product successfully uploaded and listed!"

        elif action == 'toggle_status':
            pid = int(request.form.get('product_id'))
            for p in PRODUCTS:
                if p['id'] == pid:
                    p['status'] = 'suspended' if p.get('status', 'live') == 'live' else 'live'
            msg = "Product inventory status updated."

        elif action == 'delete_product':
            pid = int(request.form.get('product_id'))
            PRODUCTS = [p for p in PRODUCTS if p['id'] != pid]
            msg = "Product deleted."

        elif action == 'update_logo':
            l_file = request.files.get('logo_file')
            if l_file and l_file.filename:
                fname = secure_filename(l_file.filename)
                l_file.save(os.path.join(UPLOAD_FOLDER, fname))
                STORE_CONFIG['logo'] = f"/uploads/{fname}"
                msg = "Website logo successfully changed."

    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, msg=msg)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, filename)


# --- HTML FRONTEND TEMPLATE ---
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KESH AADAR | Pure Herbal Botanicals</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; --shadow: 0 20px 40px rgba(27, 67, 50, 0.15); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); overflow-x: hidden; scroll-behavior: smooth; }

        .reveal { opacity: 0; transform: translateY(30px); transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
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

        /* Smooth Drawer */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); }

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
        .footer-bottom { padding-top: 20px; font-size: 12px; color: #aaa; text-align: center; }
    </style>
</head>
<body>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
                <img src="{{ logo }}" alt="Logo" class="logo-img" id="mainLogoImg">
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
    </div>

    <!-- Hero Section -->
    <section class="hero reveal">
        <div class="hero-content">
            <h1>Pure Botanical Wellness</h1>
            <p style="margin-bottom:25px; font-size:16px; color:#555;">Formulated with organic extracts for natural hair & skincare.</p>
            <a href="#shop" class="btn-primary">Shop Formulations</a>
        </div>
    </section>

    <!-- Features Banner -->
    <div class="features-banner">
        <div class="feature-item"><i class="fa-solid fa-leaf" style="color:var(--accent-gold);"></i> 100% Organic Extracts</div>
        <div class="feature-item"><i class="fa-solid fa-truck-fast" style="color:var(--accent-gold);"></i> Express Shipping</div>
        <div class="feature-item"><i class="fa-solid fa-shield-cat" style="color:var(--accent-gold);"></i> Cruelty-Free</div>
    </div>

    <!-- Shop Grid -->
    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 28px; color: var(--green-primary); margin-bottom: 30px;" class="reveal">Our Formulations</h2>
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-img-container" id="media-container-{{ p.id }}">
                    {% if p.media_type == 'video' %}
                    <video src="{{ p.media }}" autoplay muted loop playsinline></video>
                    {% else %}
                    <img src="{{ p.media }}" alt="{{ p.name }}" id="img-{{ p.id }}">
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
                <p style="font-size: 13px; line-height: 1.7;">Bringing ancient botanical secrets directly into your daily routine.</p>
            </div>
            <div>
                <h3>Customer Support</h3>
                <p><i class="fa-solid fa-envelope" style="color:var(--accent-gold);"></i> keshaadar@gmail.com</p>
            </div>
        </div>
        <div class="footer-bottom">
            &copy; 2026 Kesh Aadar Botanical Remedies. All Rights Reserved.
        </div>
    </footer>

    <!-- Cart Modal -->
    <div class="modal" id="cartModal">
        <div class="modal-content">
            <span class="close-sidebar" onclick="document.getElementById('cartModal').style.display='none'" style="position:absolute; right:20px; top:20px;">&times;</span>
            <h3 style="color:var(--green-primary); margin-bottom:15px;">Your Shopping Basket</h3>
            <div id="cart-items-container"></div>
            
            <div id="checkout-section" style="display:none; margin-top:20px;">
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
                            <input type="radio" name="pay_mode" value="Online Payment" checked> Online Payment (Prepaid)
                        </label>
                        <label style="display:flex; align-items:center; gap:10px; padding:10px; border:1px solid #ddd; border-radius:8px; cursor:pointer;" onclick="updateTotal()">
                            <input type="radio" name="pay_mode" value="Cash on Delivery"> Cash on Delivery (+₹99 Fee)
                        </label>
                    </div>

                    <div class="bill-summary">
                        <div class="bill-row"><span>Items Subtotal:</span><span id="bill-subtotal">₹0</span></div>
                        <div class="bill-row" id="cod-fee-row" style="display:none; color:#c62828;"><span>COD Handling Fee:</span><span>₹99</span></div>
                        <div class="bill-row"><span>Estimated Shipping:</span><span style="color:#2e7d32; font-weight:600;">FREE</span></div>
                        <div class="bill-row total"><span>Total Payable:</span><span id="bill-total">₹0</span></div>
                    </div>

                    <button type="submit" class="btn-primary" style="width:100%; border-radius:10px;" id="payBtn">Confirm Order</button>
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
            ['main','track','support'].forEach(id => document.getElementById('sidebar-'+id+'-view').style.display = 'none');
            document.getElementById('sidebar-'+v+'-view').style.display = 'block';
        }

        function addToCartAndFly(event, id) {
            let p = productsData.find(x => x.id === id);
            cart.push(p); 
            updateCartUI();

            let mediaElem = document.getElementById('img-' + id) || document.querySelector(`#media-container-${id} video`);
            let flyer = mediaElem.cloneNode(true);
            flyer.className = 'fly-item';
            
            let rect = mediaElem.getBoundingClientRect();
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
            if(mode === 'Cash on Delivery') {
                codFeeRow.style.display = 'flex';
                total += 99;
                document.getElementById('payBtn').innerText = 'Confirm Order (COD)';
            } else {
                codFeeRow.style.display = 'none';
                document.getElementById('payBtn').innerText = `Pay ₹${total} Now (Online)`;
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
                }).catch(() => {});
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
                return alert('Please fill in all required fields.');
            }

            let amt = updateTotal();
            let payload = { name, email, phone, pincode, city, state, landmark, street, amount: amt, payment_type: mode, items: cart };

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
                    d.innerHTML = `
                    <div style="background:#e8f5e9; padding:15px; border-radius:10px; font-size:13px; margin-top:10px;">
                        <h4 style="color:#2e7d32; margin-bottom:5px;">Order ID: ${o.order_id}</h4>
                        <p><b>Status:</b> ${o.status_text}</p>
                        <p><b>Total Bill:</b> ₹${o.amount} (${o.payment_type})</p>
                        <p style="margin-top:5px; font-size:11px; color:#555;"><b>Address:</b> ${o.full_address}</p>
                    </div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px; margin-top:10px;">No matching order found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- ORDER SUCCESS PAGE TEMPLATE ---
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

        .card { background: white; max-width: 600px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 50px; color: white; background: #2e7d32; border-radius: 50%; width: 90px; height: 90px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 25px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 32px; margin-bottom: 8px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        /* Tracking Timeline Progression */
        .timeline { display: flex; justify-content: space-between; position: relative; margin: 30px 0 20px 0; }
        .timeline::before { content: ''; position: absolute; top: 15px; left: 10%; right: 10%; height: 3px; background: #ddd; z-index: 1; }
        .step { position: relative; z-index: 2; text-align: center; }
        .step-bubble { width: 32px; height: 32px; border-radius: 50%; background: #ddd; color: #777; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; margin: 0 auto 6px auto; transition: 0.3s; }
        .step.active .step-bubble { background: #2e7d32; color: white; box-shadow: 0 0 10px rgba(46,125,50,0.4); }
        .step span { font-size: 11px; color: #666; font-weight: 500; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Confirmed!</h1>
        <p class="subtitle">An email invoice has been instantly dispatched to your inbox.</p>

        {% if order %}
        <div class="order-info-box">
            <div class="info-row"><span>Order Reference:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Phone:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Email:</span><b>{{ order.email }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color:#2e7d32;">Paid / Confirmed ({{ order.payment_type }})</b></div>
            <div class="info-row"><span>Delivery Address:</span><span style="max-width: 250px; text-align: right;">{{ order.full_address }}</span></div>
            <div class="info-row" style="margin-top:10px; border-top:1px solid #ddd; padding-top:8px;"><span>Total Bill:</span><b style="font-size:15px; color:var(--green-primary);">₹{{ order.amount }} (Incl. GST)</b></div>
        </div>

        <!-- Progress Tracker Bar -->
        <h4 style="font-size: 13px; color: var(--green-primary); text-align: left; margin-bottom: 5px;">Live Order Progress:</h4>
        <div class="timeline">
            <div class="step {% if order.status_step >= 1 %}active{% endif %}">
                <div class="step-bubble">1</div><span>Placed</span>
            </div>
            <div class="step {% if order.status_step >= 2 %}active{% endif %}">
                <div class="step-bubble">2</div><span>Packaging</span>
            </div>
            <div class="step {% if order.status_step >= 3 %}active{% endif %}">
                <div class="step-bubble">3</div><span>Shipped</span>
            </div>
            <div class="step {% if order.status_step >= 4 %}active{% endif %}">
                <div class="step-bubble">4</div><span>Delivered</span>
            </div>
        </div>
        {% else %}
        <p style="color:red;">Order data reference not found.</p>
        {% endif %}

        <br>
        <a href="/" class="btn-home">Return to Store</a>
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
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background: #f4f6f8; color: #333; display: flex; min-height: 100vh; }
        
        /* Admin Sidebar */
        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; padding: 25px 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .admin-sidebar h2 { font-size: 20px; margin-bottom: 30px; letter-spacing: 1px; color: var(--accent-gold); }
        .admin-nav { display: flex; flex-direction: column; gap: 10px; }
        .admin-nav button { background: none; border: none; color: #ccc; text-align: left; padding: 12px 15px; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 14px; display: flex; align-items: center; gap: 10px; transition: 0.3s; }
        .admin-nav button.active, .admin-nav button:hover { background: rgba(255,255,255,0.1); color: white; }
        
        /* Main Content */
        .admin-main { flex: 1; padding: 40px; overflow-y: auto; }
        .section-box { background: white; padding: 25px; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); margin-bottom: 30px; }
        h3 { color: var(--green-primary); margin-bottom: 20px; font-size: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #fafafa; color: var(--green-primary); font-weight: 600; }
        
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 5px; color: #555; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
        
        .btn-submit { background: var(--green-primary); color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge-live { background: #e8f5e9; color: #2e7d32; }
        .badge-suspended { background: #ffebee; color: #c62828; }
        
        .alert { background: #e8f5e9; color: #2e7d32; padding: 12px 15px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; font-weight: 500; border-left: 4px solid #2e7d32; }
    </style>
</head>
<body>

    <!-- Admin Sidebar -->
    <div class="admin-sidebar">
        <div>
            <h2>KESH AADAR ADMIN</h2>
            <div class="admin-nav">
                <button class="active" onclick="switchTab('orders', this)"><i class="fa-solid fa-box-open"></i> Customer Orders</button>
                <button onclick="switchTab('products', this)"><i class="fa-solid fa-tags"></i> Upload & Inventory</button>
                <button onclick="switchTab('settings', this)"><i class="fa-solid fa-gear"></i> Store Logo Settings</button>
            </div>
        </div>
        <div><a href="/" style="color:#aaa; text-decoration:none; font-size:12px;"><i class="fa-solid fa-arrow-left"></i> Back to Storefront</a></div>
    </div>

    <!-- Admin Main View Panel -->
    <div class="admin-main">
        {% if msg %}
        <div class="alert"><i class="fa-solid fa-circle-check"></i> {{ msg }}</div>
        {% endif %}

        <!-- TAB 1: ORDERS MANAGEMENT -->
        <div id="tab-orders" class="admin-tab-content">
            <div class="section-box">
                <h3>Customer Orders Management</h3>
                {% if orders %}
                <table>
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Customer Name & Contact</th>
                            <th>Items & Total Bill</th>
                            <th>Shipping Address</th>
                            <th>Update Delivery Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for o in orders %}
                        <tr>
                            <td><b style="font-family:monospace; color:var(--green-primary);">{{ o.order_id }}</b><br><small>{{ o.date }}</small></td>
                            <td><b>{{ o.name }}</b><br>{{ o.phone }}<br>{{ o.email }}</td>
                            <td>
                                <ul style="padding-left:15px; font-size:12px;">
                                    {% for item in o.items %}
                                    <li>{{ item.name }} (₹{{ item.price }})</li>
                                    {% endfor %}
                                </ul>
                                <b>Total: ₹{{ o.amount }}</b> ({{ o.payment_type }})
                            </td>
                            <td><small>{{ o.full_address }}</small></td>
                            <td>
                                <form action="/admin" method="POST" style="display:flex; gap:8px; align-items:center;">
                                    <input type="hidden" name="action" value="update_status">
                                    <input type="hidden" name="order_id" value="{{ o.order_id }}">
                                    <select name="step" style="padding:6px; border-radius:6px; font-size:12px;">
                                        <option value="1" {% if o.status_step == 1 %}selected{% endif %}>1. Placed</option>
                                        <option value="2" {% if o.status_step == 2 %}selected{% endif %}>2. Packaging</option>
                                        <option value="3" {% if o.status_step == 3 %}selected{% endif %}>3. Shipped</option>
                                        <option value="4" {% if o.status_step == 4 %}selected{% endif %}>4. Delivered</option>
                                    </select>
                                    <button type="submit" style="padding:6px 12px; background:var(--green-primary); color:white; border:none; border-radius:6px; cursor:pointer; font-size:11px;">Update</button>
                                </form>
                                <span style="font-size:11px; color:#666; margin-top:4px; display:inline-block;">Current: <b>{{ o.status_text }}</b></span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="color:#777; font-size:13px;">No customer orders received yet.</p>
                {% endif %}
            </div>
        </div>

        <!-- TAB 2: PRODUCT UPLOAD & INVENTORY -->
        <div id="tab-products" class="admin-tab-content" style="display:none;">
            <div class="section-box">
                <h3>Upload New Product (Image or Video)</h3>
                <form action="/admin" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="add_product">
                    <div class="form-group">
                        <label>Product Name</label>
                        <input type="text" name="name" required placeholder="e.g. Herbal Hair Oil">
                    </div>
                    <div class="form-group">
                        <label>Category</label>
                        <input type="text" name="category" required placeholder="Haircare / Skincare">
                    </div>
                    <div style="display:flex; gap:15px;">
                        <div class="form-group" style="flex:1;">
                            <label>Price (₹)</label>
                            <input type="number" name="price" required placeholder="499">
                        </div>
                        <div class="form-group" style="flex:1;">
                            <label>Stock Count</label>
                            <input type="number" name="stock" required placeholder="50">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Product Description</label>
                        <textarea name="desc" rows="2" placeholder="Brief formulation benefits..."></textarea>
                    </div>
                    <div class="form-group">
                        <label>Upload Media File (Image or Video from gallery)</label>
                        <input type="file" name="media_file" accept="image/*,video/*" required>
                    </div>
                    <button type="submit" class="btn-submit">Upload & Publish Product</button>
                </form>
            </div>

            <div class="section-box">
                <h3>Active Inventory Management</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Category</th>
                            <th>Price</th>
                            <th>Stock</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr>
                            <td><b>{{ p.name }}</b></td>
                            <td>{{ p.category }}</td>
                            <td>₹{{ p.price }}</td>
                            <td>{{ p.stock }}</td>
                            <td>
                                <span class="badge {% if p.status == 'suspended' %}badge-suspended{% else %}badge-live{% endif %}">
                                    {{ p.status | default('live') | upper }}
                                </span>
                            </td>
                            <td>
                                <div style="display:flex; gap:8px;">
                                    <form action="/admin" method="POST">
                                        <input type="hidden" name="action" value="toggle_status">
                                        <input type="hidden" name="product_id" value="{{ p.id }}">
                                        <button type="submit" style="padding:5px 10px; background:#f0f0f0; border:none; border-radius:5px; cursor:pointer; font-size:11px;">
                                            {% if p.status == 'suspended' %}Resume{% else %}Suspend{% endif %}
                                        </button>
                                    </form>
                                    <form action="/admin" method="POST">
                                        <input type="hidden" name="action" value="delete_product">
                                        <input type="hidden" name="product_id" value="{{ p.id }}">
                                        <button type="submit" style="padding:5px 10px; background:#ffebee; color:#c62828; border:none; border-radius:5px; cursor:pointer; font-size:11px;">Delete</button>
                                    </form>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 3: STORE LOGO SETTINGS -->
        <div id="tab-settings" class="admin-tab-content" style="display:none;">
            <div class="section-box">
                <h3>Update Store Profile Logo</h3>
                <form action="/admin" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="update_logo">
                    <div class="form-group">
                        <label>Select Logo Image from Gallery</label>
                        <input type="file" name="logo_file" accept="image/*" required>
                    </div>
                    <button type="submit" class="btn-submit">Update Logo</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId, btn) {
            document.querySelectorAll('.admin-tab-content').forEach(el => el.style.display = 'none');
            document.getElementById('tab-' + tabId).style.display = 'block';
            document.querySelectorAll('.admin-nav button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
