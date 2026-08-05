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
SMTP_PASS = "azku hebm gpsr pggo"

# --- DATABASE & STORAGE ---
PRODUCTS = [
    {"id": 1, "name": "Aloe Neem Glow Face Wash", "category": "Skincare", "price": 349, "stock": 50, "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", "desc": "Deep cleansing herbal formula for radiant skin.", "status": "Live"},
    {"id": 2, "name": "Saffron Kumkumadi Night Serum", "category": "Skincare", "price": 799, "stock": 30, "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", "desc": "Fades blemishes and restores natural skin glow.", "status": "Live"},
    {"id": 3, "name": "Bhringraj Onion Hair Growth Oil", "category": "Haircare", "price": 499, "stock": 40, "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", "desc": "Stops hair fall and stimulates roots naturally.", "status": "Live"},
    {"id": 4, "name": "Hibiscus & Shikakai Herbal Shampoo", "category": "Haircare", "price": 399, "stock": 45, "image": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80", "desc": "Nourishing sulfate-free cleanser for smooth hair.", "status": "Live"}
]

ORDERS = []
BLACKLISTED_IPS = []

# --- BACKGROUND EMAIL SENDER ---
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
                    <p style="margin: 5px 0; color: #333; font-size: 14px; font-weight: 600;">Total Amount: ₹{amount} ({payment_type})</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;"><b>Shipping To:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 5px 15px rgba(27, 67, 50, 0.3);">Track Live Order Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Reply directly to this email or contact customer support.</p>
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

# --- ROUTES ---
@app.route('/')
def index():
    active_products = [p for p in PRODUCTS if p.get('status', 'Live') == 'Live']
    return render_template_string(TEMPLATE, products=active_products)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['fulfillment_status'] = 'Order Placed' # Order Placed -> Packaging -> Shifting -> Delivered
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.insert(0, data)
    
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, data['payment_type'])
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id)

@app.route('/track_order')
def track_order():
    q = request.args.get('q', '').strip()
    for o in ORDERS:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order": o})
    return jsonify({"found": False})

# --- ADMIN PANEL ROUTE ---
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS)

@app.route('/admin/update_status', methods=['POST'])
def admin_update_status():
    d = request.get_json()
    oid = d.get('order_id')
    new_status = d.get('status')
    for o in ORDERS:
        if o['order_id'] == oid:
            o['fulfillment_status'] = new_status
            return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/admin/save_product', methods=['POST'])
def admin_save_product():
    pid = request.form.get('id')
    name = request.form.get('name')
    category = request.form.get('category')
    price = float(request.form.get('price', 0))
    stock = int(request.form.get('stock', 0))
    desc = request.form.get('desc')
    status = request.form.get('status', 'Live')
    
    image_url = request.form.get('existing_image', '')
    file = request.files.get('image_file')
    if file and file.filename != '':
        img_bytes = file.read()
        encoded = base64.b64encode(img_bytes).decode('utf-8')
        image_url = f"data:{file.content_type};base64,{encoded}"

    if pid: # Edit
        for p in PRODUCTS:
            if p['id'] == int(pid):
                p['name'] = name
                p['category'] = category
                p['price'] = price
                p['stock'] = stock
                p['desc'] = desc
                p['status'] = status
                if image_url:
                    p['image'] = image_url
    else: # Add New
        new_id = max([p['id'] for p in PRODUCTS], default=0) + 1
        PRODUCTS.append({
            "id": new_id,
            "name": name,
            "category": category,
            "price": price,
            "stock": stock,
            "image": image_url or "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=500&q=80",
            "desc": desc,
            "status": status
        })
    return redirect('/admin')

@app.route('/admin/delete_product/<int:pid>', methods=['POST'])
def admin_delete_product(pid):
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p['id'] != pid]
    return redirect('/admin')


# --- FRONTEND TEMPLATE ---
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
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Drawer Animation */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: background 0.2s; }
        .sidebar button.menu-item:hover { background: #f1f3f5; }
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

        .saved-addr-btn { background: #e8f5e9; color: #2e7d32; border: 1px dashed #2e7d32; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600; width: 100%; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; gap: 8px; }

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
            <h4 style="font-size: 13px; color: var(--green-primary);">2. How do I track my delivery?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">You will receive an automated tracking link on your registered email address.</p>
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
                <div class="product-img-container">
                    {% if p.image.endswith('.mp4') or 'video' in p.image %}
                    <video src="{{ p.image }}" autoplay muted loop playsinline id="img-{{ p.id }}"></video>
                    {% else %}
                    <img src="{{ p.image }}" alt="{{ p.name }}" id="img-{{ p.id }}">
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

            let mediaEl = document.getElementById('img-' + id);
            let flyer = mediaEl.cloneNode(true);
            flyer.className = 'fly-item';
            
            let rect = mediaEl.getBoundingClientRect();
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
                .catch(() => console.log("PIN lookup error"));
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
            let payload = { 
                name, email, phone, pincode, city, state, landmark, street, 
                amount: amt, 
                payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Payment (Prepaid)', 
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
                    let st = data.order.fulfillment_status;
                    d.innerHTML = `<div style="background:#e8f5e9; padding:12px; border-radius:8px; font-size:13px;"><h4 style="color:#2e7d32;">Found: ${data.order.order_id}</h4><p><b>Status:</b> ${st}</p></div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- DEDICATED SUCCESS & STEP TRACKER TEMPLATE ---
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

        .card { background: white; max-width: 620px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 50px; color: white; background: #2e7d32; border-radius: 50%; width: 90px; height: 90px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 25px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 32px; margin-bottom: 8px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        /* Timeline Tracker UI */
        .tracker-container { margin: 25px 0; padding: 20px; background: #fff; border: 1px solid #eee; border-radius: 12px; }
        .steps { display: flex; justify-content: space-between; position: relative; margin-top: 15px; }
        .steps::before { content: ''; position: absolute; top: 15px; left: 10%; width: 80%; height: 4px; background: #ddd; z-index: 1; }
        .step { position: relative; z-index: 2; text-align: center; width: 25%; }
        .step-icon { width: 34px; height: 34px; border-radius: 50%; background: #ddd; color: #fff; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 12px; font-weight: bold; transition: background 0.3s; }
        .step.completed .step-icon { background: #2e7d32; }
        .step.active .step-icon { background: var(--accent-gold); box-shadow: 0 0 10px rgba(212,163,115,0.6); }
        .step-label { font-size: 11px; color: #666; font-weight: 500; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Confirmed!</h1>
        <p class="subtitle">Thank you for choosing Kesh Aadar. Your order summary and updates are below.</p>

        {% if order %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Phone:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Email:</span><b>{{ order.email }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color: #2e7d32;">{{ order.payment_type }} (Paid / Confirmed)</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 250px; text-align: right;">{{ order.full_address }}</span></div>
            <hr style="border:0; border-top:1px solid #ddd; margin: 10px 0;">
            <div class="info-row"><span>Total Bill:</span><b style="font-size:15px; color:var(--green-primary);">₹{{ order.amount }} (Incl. GST & Taxes)</b></div>
        </div>

        <!-- Live Step Tracker -->
        <div class="tracker-container">
            <h4 style="font-size: 14px; color: var(--green-primary); margin-bottom: 5px;">Live Order Progress</h4>
            <div class="steps" id="stepsWrapper" data-status="{{ order.fulfillment_status }}">
                <div class="step" id="step-1">
                    <div class="step-icon"><i class="fa-solid fa-clipboard-check"></i></div>
                    <div class="step-label">Placed</div>
                </div>
                <div class="step" id="step-2">
                    <div class="step-icon"><i class="fa-solid fa-box-open"></i></div>
                    <div class="step-label">Packaging</div>
                </div>
                <div class="step" id="step-3">
                    <div class="step-icon"><i class="fa-solid fa-truck-fast"></i></div>
                    <div class="step-label">Shifting</div>
                </div>
                <div class="step" id="step-4">
                    <div class="step-icon"><i class="fa-solid fa-house-chimney"></i></div>
                    <div class="step-label">Delivered</div>
                </div>
            </div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 20px;"><i class="fa-solid fa-envelope"></i> Official email confirmation sent to your inbox.</p>
        
        <a href="/" class="btn-home">Continue Shopping</a>
    </div>

    <script>
        const statusMap = {
            'Order Placed': 1,
            'Packaging': 2,
            'Shifting': 3,
            'Delivered': 4
        };
        const currentStatus = document.getElementById('stepsWrapper')?.getAttribute('data-status') || 'Order Placed';
        const currentLevel = statusMap[currentStatus] || 1;

        for(let i=1; i<=4; i++) {
            let el = document.getElementById('step-' + i);
            if(i < currentLevel) {
                el.classList.add('completed');
            } else if(i === currentLevel) {
                el.classList.add('completed', 'active');
            }
        }
    </script>
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: #2b2b2b; display: flex; min-height: 100vh; }

        /* Admin Sidebar */
        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; padding: 30px 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .admin-sidebar h2 { font-size: 20px; color: var(--accent-gold); margin-bottom: 30px; }
        .admin-menu { display: flex; flex-direction: column; gap: 10px; flex-grow: 1; }
        .admin-menu button { background: none; border: none; color: white; padding: 12px 15px; border-radius: 8px; text-align: left; cursor: pointer; font-size: 14px; display: flex; align-items: center; gap: 12px; font-weight: 500; }
        .admin-menu button.active, .admin-menu button:hover { background: rgba(255,255,255,0.1); }
        .admin-menu button i { color: var(--accent-gold); width: 20px; }

        /* Admin Main Content */
        .admin-content { flex-grow: 1; padding: 40px; overflow-y: auto; max-height: 100vh; }
        .section-box { display: none; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
        .section-box.active { display: block; }

        h3 { color: var(--green-primary); margin-bottom: 20px; font-size: 22px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); font-weight: 600; }

        .badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge.placed { background: #e3f2fd; color: #1565c0; }
        .badge.packaging { background: #fff3e0; color: #ef6c00; }
        .badge.shifting { background: #ede7f6; color: #512da8; }
        .badge.delivered { background: #e8f5e9; color: #2e7d32; }

        .form-control { width: 100%; padding: 10px 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
        .btn-submit { background: var(--green-primary); color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-weight: 600; }
        
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    </style>
</head>
<body>

    <div class="admin-sidebar">
        <div>
            <h2>KESH AADAR Admin</h2>
            <div class="admin-menu">
                <button class="active" onclick="switchTab('orders', event)"><i class="fa-solid fa-box"></i> Orders Management</button>
                <button onclick="switchTab('inventory', event)"><i class="fa-solid fa-store"></i> Products & Inventory</button>
            </div>
        </div>
        <div>
            <a href="/" style="color: #aaa; text-decoration: none; font-size: 13px;"><i class="fa-solid fa-arrow-left"></i> Back to Store</a>
        </div>
    </div>

    <div class="admin-content">
        <!-- Orders Section -->
        <div id="section-orders" class="section-box active">
            <h3>Customer Orders</h3>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Order ID & Date</th>
                            <th>Customer Info</th>
                            <th>Address & Items</th>
                            <th>Total Amount</th>
                            <th>Update Fulfillment Stage</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if orders %}
                            {% for o in orders %}
                            <tr>
                                <td><b>{{ o.order_id }}</b><br><span style="font-size:11px; color:#777;">{{ o.date }}</span></td>
                                <td><b>{{ o.name }}</b><br>{{ o.phone }}<br>{{ o.email }}</td>
                                <td>
                                    {{ o.full_address }}<br>
                                    <span style="font-size:11px; color:#555;"><b>Items:</b> {% for i in o.items %}{{ i.name }} (₹{{ i.price }}), {% endfor %}</span>
                                </td>
                                <td><b>₹{{ o.amount }}</b><br><span style="font-size:11px; color:#2e7d32;">{{ o.payment_type }}</span></td>
                                <td>
                                    <select class="form-control" style="margin-bottom:0;" onchange="updateOrderStatus('{{ o.order_id }}', this.value)">
                                        <option value="Order Placed" {% if o.fulfillment_status == 'Order Placed' %}selected{% endif %}>Order Placed</option>
                                        <option value="Packaging" {% if o.fulfillment_status == 'Packaging' %}selected{% endif %}>Packaging</option>
                                        <option value="Shifting" {% if o.fulfillment_status == 'Shifting' %}selected{% endif %}>Shifting</option>
                                        <option value="Delivered" {% if o.fulfillment_status == 'Delivered' %}selected{% endif %}>Delivered</option>
                                    </select>
                                </td>
                            </tr>
                            {% endfor %}
                        {% else %}
                            <tr><td colspan="5" style="text-align:center; color:#888; padding:30px;">No customer orders received yet.</td></tr>
                        {% endif %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Inventory Section -->
        <div id="section-inventory" class="section-box">
            <h3>Product Inventory & Upload Manager</h3>
            
            <div style="background:#f9f9f9; padding:20px; border-radius:12px; margin-bottom:30px; border:1px solid #eee;">
                <h4 style="color:var(--green-primary); margin-bottom:15px; font-size:16px;">Add / Update Product</h4>
                <form action="/admin/save_product" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="id" id="prod-id">
                    <div class="grid-2">
                        <input type="text" name="name" id="prod-name" class="form-control" placeholder="Product Name *" required>
                        <input type="text" name="category" id="prod-category" class="form-control" placeholder="Category (e.g. Haircare, Skincare) *" required>
                        <input type="number" name="price" id="prod-price" class="form-control" placeholder="Price (₹) *" required>
                        <input type="number" name="stock" id="prod-stock" class="form-control" placeholder="Stock Count *" required>
                    </div>
                    <textarea name="desc" id="prod-desc" class="form-control" placeholder="Product Description *" rows="2" required></textarea>
                    
                    <div class="grid-2" style="align-items: center;">
                        <div>
                            <label style="font-size: 12px; color: #555; display: block; margin-bottom: 5px;">Upload Media (Image or Video from Gallery):</label>
                            <input type="file" name="image_file" class="form-control" accept="image/*,video/*">
                            <input type="hidden" name="existing_image" id="prod-existing-img">
                        </div>
                        <div>
                            <label style="font-size: 12px; color: #555; display: block; margin-bottom: 5px;">Storefront Status:</label>
                            <select name="status" id="prod-status" class="form-control">
                                <option value="Live">Live (Visible on Store)</option>
                                <option value="Suspended">Suspended (Hidden from Store)</option>
                            </select>
                        </div>
                    </div>
                    <button type="submit" class="btn-submit">Save Product</button>
                    <button type="button" onclick="resetForm()" style="background:#6c757d; color:white; border:none; padding:12px 20px; border-radius:8px; cursor:pointer; margin-left:10px;">Clear Form</button>
                </form>
            </div>

            <h4>Existing Inventory List</h4>
            <table>
                <thead>
                    <tr>
                        <th>Media</th>
                        <th>Name & Category</th>
                        <th>Price & Stock</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in products %}
                    <tr>
                        <td>
                            {% if p.image.endswith('.mp4') or 'video' in p.image %}
                            <video src="{{ p.image }}" width="45" height="45" style="border-radius:6px; object-fit:cover;" muted></video>
                            {% else %}
                            <img src="{{ p.image }}" width="45" height="45" style="border-radius:6px; object-fit:cover;">
                            {% endif %}
                        </td>
                        <td><b>{{ p.name }}</b><br><span style="font-size:11px; color:#777;">{{ p.category }}</span></td>
                        <td>₹{{ p.price }}<br><span style="font-size:11px; color:#2e7d32;">Stock: {{ p.stock }}</span></td>
                        <td><span class="badge {% if p.status == 'Live' %}delivered{% else %}placed{% endif %}">{{ p.status or 'Live' }}</span></td>
                        <td>
                            <button type="button" onclick="editProduct({{ p.id }}, '{{ p.name }}', '{{ p.category }}', {{ p.price }}, {{ p.stock }}, '{{ p.desc }}', '{{ p.image }}', '{{ p.status or 'Live' }}')" style="background:#ffc107; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:600; font-size:11px;">Edit</button>
                            <form action="/admin/delete_product/{{ p.id }}" method="POST" style="display:inline;" onsubmit="return confirm('Are you sure you want to delete this product?');">
                                <button type="submit" style="background:#dc3545; color:white; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; font-weight:600; font-size:11px; margin-left:5px;">Delete</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function switchTab(tab, evt) {
            document.querySelectorAll('.section-box').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.admin-menu button').forEach(el => el.classList.remove('active'));
            document.getElementById('section-' + tab).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        function updateOrderStatus(orderId, status) {
            fetch('/admin/update_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId, status: status })
            }).then(r => r.json()).then(res => {
                if(res.success) {
                    console.log("Status updated successfully");
                }
            });
        }

        function editProduct(id, name, category, price, stock, desc, image, status) {
            document.getElementById('prod-id').value = id;
            document.getElementById('prod-name').value = name;
            document.getElementById('prod-category').value = category;
            document.getElementById('prod-price').value = price;
            document.getElementById('prod-stock').value = stock;
            document.getElementById('prod-desc').value = desc;
            document.getElementById('prod-existing-img').value = image;
            document.getElementById('prod-status').value = status;
            window.scrollTo({top: 0, behavior: 'smooth'});
        }

        function resetForm() {
            document.getElementById('prod-id').value = '';
            document.getElementById('prod-name').value = '';
            document.getElementById('prod-category').value = '';
            document.getElementById('prod-price').value = '';
            document.getElementById('prod-stock').value = '';
            document.getElementById('prod-desc').value = '';
            document.getElementById('prod-existing-img').value = '';
            document.getElementById('prod-status').value = 'Live';
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
