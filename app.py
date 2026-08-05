from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import smtplib
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
SMTP_EMAIL = "keshaadar@gmail.com"
SMTP_PASS = "zvxb mrbs ccoi vfrl"

# --- DATABASE & STORAGE (In-Memory Serverless State) ---
SETTINGS = {
    "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
    "brand_name": "KESH AADAR"
}

PRODUCTS = [
    {
        "id": 1, 
        "name": "Aloe Neem Glow Face Wash", 
        "category": "Skincare", 
        "price": 349, 
        "stock": 50, 
        "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Deep cleansing herbal formula for radiant skin.",
        "status": "active"
    },
    {
        "id": 2, 
        "name": "Saffron Kumkumadi Night Serum", 
        "category": "Skincare", 
        "price": 799, 
        "stock": 30, 
        "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Fades blemishes and restores natural skin glow.",
        "status": "active"
    },
    {
        "id": 3, 
        "name": "Bhringraj Onion Hair Growth Oil", 
        "category": "Haircare", 
        "price": 499, 
        "stock": 40, 
        "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Stops hair fall and stimulates roots naturally.",
        "status": "active"
    },
    {
        "id": 4, 
        "name": "Hibiscus & Shikakai Herbal Shampoo", 
        "category": "Haircare", 
        "price": 399, 
        "stock": 45, 
        "image": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Nourishing sulfate-free cleanser for smooth hair.",
        "status": "active"
    }
]

ORDERS = []
BLACKLISTED_IPS = []

# --- SYNCHRONOUS EMAIL SENDER (Instant Delivery) ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, payment_type):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> (Qty: 1) - ₹{i['price']}</li>" for i in items])
        track_url = f"https://{request.host}/order_success/{order_id}"

        payment_status_text = "Already Paid (Online Razorpay)" if payment_type == "Online Payment" else "Cash on Delivery (COD)"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 36px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">KESH AADAR</h1>
                <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 12px; font-weight: bold; margin-top: 0; text-align: center;">Pure Botanical Remedies</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <h2 style="color: #1b4332; font-size: 22px;">Thank you for your order, {name}!</h2>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">Your order has been placed successfully and is now being processed by our botanical team.</p>
                
                <div style="background: #F3EFEA; padding: 20px; border-radius: 12px; margin: 25px 0; border: 1px dashed #d4a373;">
                    <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">Order Reference ID</p>
                    <h3 style="margin: 8px 0; font-size: 28px; color: #1b4332; font-family: monospace;">{order_id}</h3>
                    <p style="margin: 5px 0; color: #333; font-size: 14px; font-weight: 600;">Total Bill (Incl. Taxes): ₹{amount}</p>
                    <p style="margin: 5px 0; color: #333; font-size: 14px;"><b>Payment Status:</b> <span style="color: #2e7d32; font-weight: bold;">{payment_status_text}</span></p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;"><b>Shipping Address:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 5px 15px rgba(27, 67, 50, 0.3);">Track Live Order Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact us at {SMTP_EMAIL}</p>
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
        print(f"Confirmation email delivered instantly to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.before_request
def check_ip_blacklist():
    client_ip = request.remote_addr
    if client_ip in BLACKLISTED_IPS:
        return jsonify({"error": "Your IP has been blacklisted by administrator."}), 403

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    active_products = [p for p in PRODUCTS if p.get('status', 'active') == 'active']
    return render_template_string(TEMPLATE, products=active_products, settings=SETTINGS)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status'] = 'Order Placed' # Initial Status
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', 'N/A')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.append(data)
    
    # Send email synchronously for immediate delivery
    send_order_email(
        data['email'], 
        data['name'], 
        order_id, 
        data['amount'], 
        data['items'], 
        full_address,
        data['payment_type']
    )
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, settings=SETTINGS)

@app.route('/api/track')
def api_track():
    q = request.args.get('q', '').strip()
    for o in ORDERS:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order": o})
    return jsonify({"found": False})

# --- ADMIN PANEL ROUTES ---
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE, settings=SETTINGS)

@app.route('/admin/api/data')
def admin_get_data():
    return jsonify({
        "orders": ORDERS,
        "products": PRODUCTS,
        "settings": SETTINGS,
        "blacklist": BLACKLISTED_IPS
    })

@app.route('/admin/api/order_status', methods=['POST'])
def admin_update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status'] = new_status
            return jsonify({"status": "success"})
    return jsonify({"error": "Order not found"}), 404

@app.route('/admin/api/product/add', methods=['POST'])
def admin_add_product():
    data = request.get_json()
    new_id = max([p['id'] for p in PRODUCTS], default=0) + 1
    new_prod = {
        "id": new_id,
        "name": data.get('name'),
        "category": data.get('category', 'Skincare'),
        "price": float(data.get('price', 0)),
        "stock": int(data.get('stock', 10)),
        "image": data.get('image', ''),
        "video": data.get('video', ''),
        "desc": data.get('desc', ''),
        "status": "active"
    }
    PRODUCTS.append(new_prod)
    return jsonify({"status": "success", "products": PRODUCTS})

@app.route('/admin/api/product/edit', methods=['POST'])
def admin_edit_product():
    data = request.get_json()
    prod_id = int(data.get('id'))
    for p in PRODUCTS:
        if p['id'] == prod_id:
            p['name'] = data.get('name', p['name'])
            p['price'] = float(data.get('price', p['price']))
            p['stock'] = int(data.get('stock', p['stock']))
            p['desc'] = data.get('desc', p['desc'])
            if data.get('image'): p['image'] = data.get('image')
            if data.get('video'): p['video'] = data.get('video')
            p['status'] = data.get('status', p['status'])
            return jsonify({"status": "success", "products": PRODUCTS})
    return jsonify({"error": "Product not found"}), 404

@app.route('/admin/api/product/delete', methods=['POST'])
def admin_delete_product():
    data = request.get_json()
    prod_id = int(data.get('id'))
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
    return jsonify({"status": "success", "products": PRODUCTS})

@app.route('/admin/api/logo', methods=['POST'])
def admin_update_logo():
    data = request.get_json()
    logo_data = data.get('logo')
    if logo_data:
        SETTINGS['logo'] = logo_data
    return jsonify({"status": "success", "settings": SETTINGS})

# --- FRONTEND TEMPLATE (STORE) ---
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
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Butter-Smooth Sidebar Drawer */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.77, 0, 0.175, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); background: none; border: none; }
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
        .product-media-container { height: 230px; overflow: hidden; background: #f7f5f0; position: relative; }
        .product-media-container img, .product-media-container video { width: 100%; height: 100%; object-fit: cover; }
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
                <img src="{{ settings.logo }}" alt="Logo" class="logo-img" id="headerLogoImg">
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
        <div class="product-grid" id="productGridContainer">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-media-container">
                    {% if p.video %}
                    <video src="{{ p.video }}" autoplay muted loop playsinline id="img-{{ p.id }}"></video>
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
                <p><i class="fa-solid fa-envelope" style="color:var(--accent-gold);"></i> keshaadar@gmail.com</p>
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
            <button class="close-sidebar" onclick="document.getElementById('cartModal').style.display='none'" style="position:absolute; right:20px; top:20px;">&times;</button>
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
                            <input type="radio" name="pay_mode" value="online" checked> Online Payment (Razorpay)
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
                payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Payment', 
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
            fetch('/api/track?q=' + encodeURIComponent(q)).then(r => r.json()).then(data => {
                let d = document.getElementById('track-result');
                if(data.found) {
                    d.innerHTML = `<div style="background:#e8f5e9; padding:12px; border-radius:8px; font-size:13px;"><h4 style="color:#2e7d32;">Found: ${data.order.order_id}</h4><p>Status: <b>${data.order.status}</b></p><a href="/order_success/${data.order.order_id}" style="color:var(--green-primary); font-weight:bold; display:block; margin-top:5px;">View Live Tracker &rarr;</a></div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- ANIMATED LIVE ORDER SUCCESS & TRACKING TEMPLATE ---
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
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; --green-light: #2d6a4f; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }

        .card { background: white; max-width: 650px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 28px; margin-bottom: 8px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        /* Flipkart / Amazon Style Timeline */
        .timeline-container { display: flex; justify-content: space-between; position: relative; margin: 35px 10px; }
        .timeline-container::before { content: ''; position: absolute; top: 15px; left: 10%; width: 80%; height: 4px; background: #ddd; z-index: 1; }
        .timeline-step { position: relative; z-index: 2; text-align: center; width: 25%; }
        .timeline-icon { width: 34px; height: 34px; background: #ddd; color: #777; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 13px; font-weight: bold; transition: 0.3s; }
        .timeline-step.active .timeline-icon { background: var(--green-primary); color: white; box-shadow: 0 0 0 5px rgba(27,67,50,0.15); }
        .timeline-step.completed .timeline-icon { background: var(--green-light); color: white; }
        .timeline-label { font-size: 11px; font-weight: 600; color: #555; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; margin-top: 15px; }
    </style>
</head>
<body>

    <div class="card">
        <h1>Live Order Tracking</h1>
        <p class="subtitle">Thank you for choosing Kesh Aadar. Track your order status in real-time below.</p>

        {% if order %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Phone & Email:</span><b>{{ order.phone }} | {{ order.email }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color:#2e7d32;">{{ order.payment_type }} (Paid ₹{{ order.amount }})</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 280px; text-align: right;">{{ order.full_address }}</span></div>
            <div class="info-row" style="margin-top:10px; border-top:1px solid #ddd; padding-top:8px;"><span>Ordered Items:</span><b>{{ order.items | map(attribute='name') | join(', ') }}</b></div>
        </div>

        <!-- Progress Timeline -->
        <div class="timeline-container" id="timelineContainer" data-status="{{ order.status }}">
            <div class="timeline-step" id="step-placed">
                <div class="timeline-icon"><i class="fa-solid fa-receipt"></i></div>
                <div class="timeline-label">Order Placed</div>
            </div>
            <div class="timeline-step" id="step-packaging">
                <div class="timeline-icon"><i class="fa-solid fa-box-open"></i></div>
                <div class="timeline-label">Packaging</div>
            </div>
            <div class="timeline-step" id="step-shifting">
                <div class="timeline-icon"><i class="fa-solid fa-truck-fast"></i></div>
                <div class="timeline-label">Shifting</div>
            </div>
            <div class="timeline-step" id="step-delivered">
                <div class="timeline-icon"><i class="fa-solid fa-check"></i></div>
                <div class="timeline-label">Delivered</div>
            </div>
        </div>
        {% else %}
        <div class="order-info-box" style="text-align:center;">
            <p style="color:red; font-size:14px;">Order reference not found.</p>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-top: 15px;"><i class="fa-solid fa-envelope"></i> Automated status updates are synced with your registered email.</p>
        
        <a href="/" class="btn-home">Back to Store</a>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {
            let container = document.getElementById('timelineContainer');
            if(!container) return;
            let currentStatus = container.getAttribute('data-status');
            
            let statuses = ['Order Placed', 'Packaging', 'Shifting', 'Delivered'];
            let currentIndex = statuses.indexOf(currentStatus);
            if(currentIndex === -1) currentIndex = 0;

            let stepIds = ['step-placed', 'step-packaging', 'step-shifting', 'step-delivered'];
            for(let i = 0; i <= currentIndex; i++) {
                let el = document.getElementById(stepIds[i]);
                if(el) {
                    if(i === currentIndex) el.classList.add('active');
                    else el.classList.add('completed');
                }
            }
        });
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); display: flex; min-height: 100vh; }

        /* Admin Sidebar */
        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; padding: 25px 20px; display: flex; flex-direction: column; justify-content: space-between; position: fixed; height: 100vh; z-index: 100; transition: transform 0.3s ease; }
        .admin-brand { font-size: 20px; font-weight: bold; letter-spacing: 1px; color: var(--accent-gold); margin-bottom: 30px; display: flex; align-items: center; gap: 10px; }
        .admin-nav-btn { width: 100%; padding: 12px 15px; background: transparent; border: none; color: #ddd; text-align: left; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 14px; margin-bottom: 8px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .admin-nav-btn:hover, .admin-nav-btn.active { background: rgba(255,255,255,0.1); color: white; }
        .admin-nav-btn i { color: var(--accent-gold); width: 20px; }

        /* Main Admin Content Area */
        .admin-main { margin-left: 260px; flex: 1; padding: 40px; }
        .admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; background: white; padding: 20px 30px; border-radius: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.03); }
        .admin-section { display: none; }
        .admin-section.active { display: block; }

        .card-box { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 5px 20px rgba(0,0,0,0.04); margin-bottom: 25px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); font-weight: 600; }
        
        .status-select { padding: 6px 10px; border-radius: 6px; border: 1px solid #ccc; font-size: 12px; font-weight: 600; outline: none; }
        .btn-action { padding: 6px 12px; background: var(--green-primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; }
        .btn-danger { background: #c62828; }
        
        .form-control { width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
        .form-grid-admin { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
    </style>
</head>
<body>

    <!-- Admin Sidebar -->
    <div class="admin-sidebar" id="adminSidebar">
        <div>
            <div class="admin-brand"><i class="fa-solid fa-shield-halved"></i> KESH ADMIN</div>
            <button class="admin-nav-btn active" onclick="switchAdminTab('orders')"><i class="fa-solid fa-box"></i> Orders Manager</button>
            <button class="admin-nav-btn" onclick="switchAdminTab('products')"><i class="fa-solid fa-tags"></i> Products & Inventory</button>
            <button class="admin-nav-btn" onclick="switchAdminTab('settings')"><i class="fa-solid fa-gear"></i> Website Settings</button>
        </div>
        <div>
            <a href="/" class="admin-nav-btn" style="text-decoration:none;"><i class="fa-solid fa-globe"></i> View Live Website</a>
        </div>
    </div>

    <!-- Admin Main Body -->
    <div class="admin-main">
        <div class="admin-header">
            <h2 id="adminHeaderTitle" style="color: var(--green-primary); font-family: 'Playfair Display';">Orders Management</h2>
            <span style="font-size: 13px; color: #666;"><i class="fa-solid fa-user-shield"></i> Administrator</span>
        </div>

        <!-- Orders Section -->
        <div id="tab-orders" class="admin-section active">
            <div class="card-box">
                <h3 style="margin-bottom: 15px; color: var(--green-primary);">Customer Orders List</h3>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Customer Details</th>
                                <th>Items Ordered</th>
                                <th>Total & Payment</th>
                                <th>Address</th>
                                <th>Order Status Control</th>
                            </tr>
                        </thead>
                        <tbody id="adminOrdersTable">
                            <tr><td colspan="6" style="text-align:center; color:#888;">Loading orders...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Products Section -->
        <div id="tab-products" class="admin-section">
            <div class="card-box">
                <h3 style="margin-bottom: 15px; color: var(--green-primary);">Add New Product</h3>
                <form onsubmit="event.preventDefault(); addProduct();">
                    <div class="form-grid-admin">
                        <input type="text" id="new-prod-name" class="form-control" placeholder="Product Name *" required>
                        <select id="new-prod-cat" class="form-control">
                            <option value="Skincare">Skincare</option>
                            <option value="Haircare">Haircare</option>
                        </select>
                        <input type="number" id="new-prod-price" class="form-control" placeholder="Price (₹) *" required>
                        <input type="number" id="new-prod-stock" class="form-control" placeholder="Stock Quantity *" required>
                        <div style="grid-column: span 2;">
                            <label style="font-size:12px; font-weight:600; color:#555;">Product Image (Upload from Gallery):</label>
                            <input type="file" id="new-prod-img-file" class="form-control" accept="image/*" onchange="encodeFile(this, 'img')">
                            <input type="hidden" id="new-prod-img" value="https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80">
                        </div>
                        <div style="grid-column: span 2;">
                            <label style="font-size:12px; font-weight:600; color:#555;">Product Video / Short Demo (Optional - Upload from Gallery):</label>
                            <input type="file" id="new-prod-vid-file" class="form-control" accept="video/*" onchange="encodeFile(this, 'vid')">
                            <input type="hidden" id="new-prod-vid" value="">
                        </div>
                        <textarea id="new-prod-desc" class="form-control" placeholder="Product Description *" rows="2" style="grid-column: span 2;" required></textarea>
                    </div>
                    <button type="submit" class="btn-action">Upload Product <i class="fa-solid fa-cloud-arrow-up"></i></button>
                </form>
            </div>

            <div class="card-box">
                <h3 style="margin-bottom: 15px; color: var(--green-primary);">Existing Inventory & Management</h3>
                <div style="overflow-x: auto;">
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
                        <tbody id="adminProductsTable">
                            <tr><td colspan="6" style="text-align:center; color:#888;">Loading products...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Settings Section -->
        <div id="tab-settings" class="admin-section">
            <div class="card-box">
                <h3 style="margin-bottom: 15px; color: var(--green-primary);">Website Profile Logo Customization</h3>
                <p style="font-size: 13px; color: #666; margin-bottom: 15px;">Upload a new circular profile logo from your gallery to instantly update the header across the entire website.</p>
                <form onsubmit="event.preventDefault(); updateLogo();">
                    <label style="font-size:12px; font-weight:600; color:#555;">Select Logo Image File:</label>
                    <input type="file" id="logo-file-input" class="form-control" accept="image/*" onchange="encodeLogoFile(this)" required>
                    <input type="hidden" id="logo-base64-val">
                    <button type="submit" class="btn-action">Update Website Logo</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        let adminData = {};

        function fetchAdminData() {
            fetch('/admin/api/data')
            .then(res => res.json())
            .then(data => {
                adminData = data;
                renderOrders();
                renderProducts();
            });
        }
        fetchAdminData();

        function switchAdminTab(tab) {
            document.querySelectorAll('.admin-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.admin-nav-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tab).classList.add('active');
            event.currentTarget.classList.add('active');
            
            let titles = { 'orders': 'Orders Management', 'products': 'Products & Inventory', 'settings': 'Website Settings' };
            document.getElementById('adminHeaderTitle').innerText = titles[tab];
        }

        function renderOrders() {
            let tbody = document.getElementById('adminOrdersTable');
            tbody.innerHTML = '';
            if(!adminData.orders || adminData.orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#888;">No orders received yet.</td></tr>';
                return;
            }
            adminData.orders.forEach(o => {
                let itemsList = o.items.map(i => `<b>${i.name}</b> (₹${i.price})`).join('<br>');
                tbody.innerHTML += `
                <tr>
                    <td><b style="font-family:monospace; color:var(--green-primary);">${o.order_id}</b><br><small style="color:#888;">${o.date}</small></td>
                    <td><b>${o.name}</b><br>${o.phone}<br>${o.email}</td>
                    <td>${itemsList}</td>
                    <td><b>₹${o.amount}</b><br><small style="color:#2e7d32; font-weight:600;">${o.payment_type}</small></td>
                    <td><span style="font-size:11px;">${o.full_address}</span></td>
                    <td>
                        <select class="status-select" onchange="updateOrderStatus('${o.order_id}', this.value)">
                            <option value="Order Placed" ${o.status === 'Order Placed' ? 'selected' : ''}>Order Placed</option>
                            <option value="Packaging" ${o.status === 'Packaging' ? 'selected' : ''}>Packaging</option>
                            <option value="Shifting" ${o.status === 'Shifting' ? 'selected' : ''}>Shifting</option>
                            <option value="Delivered" ${o.status === 'Delivered' ? 'selected' : ''}>Delivered</option>
                        </select>
                    </td>
                </tr>`;
            });
        }

        function updateOrderStatus(orderId, status) {
            fetch('/admin/api/order_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId, status: status })
            }).then(res => res.json()).then(data => {
                if(data.status === 'success') {
                    alert("Order status updated successfully!");
                }
            });
        }

        function encodeFile(input, type) {
            let file = input.files[0];
            if(file) {
                let reader = new FileReader();
                reader.onload = function(e) {
                    if(type === 'img') document.getElementById('new-prod-img').value = e.target.result;
                    if(type === 'vid') document.getElementById('new-prod-vid').value = e.target.result;
                }
                reader.readAsDataURL(file);
            }
        }

        function encodeLogoFile(input) {
            let file = input.files[0];
            if(file) {
                let reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('logo-base64-val').value = e.target.result;
                }
                reader.readAsDataURL(file);
            }
        }

        function addProduct() {
            let payload = {
                name: document.getElementById('new-prod-name').value,
                category: document.getElementById('new-prod-cat').value,
                price: document.getElementById('new-prod-price').value,
                stock: document.getElementById('new-prod-stock').value,
                image: document.getElementById('new-prod-img').value,
                video: document.getElementById('new-prod-vid').value,
                desc: document.getElementById('new-prod-desc').value
            };
            fetch('/admin/api/product/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }).then(res => res.json()).then(data => {
                adminData.products = data.products;
                renderProducts();
                alert('Product uploaded successfully!');
            });
        }

        function renderProducts() {
            let tbody = document.getElementById('adminProductsTable');
            tbody.innerHTML = '';
            adminData.products.forEach(p => {
                tbody.innerHTML += `
                <tr>
                    <td>${p.id}</td>
                    <td><b>${p.name}</b></td>
                    <td>₹${p.price}</td>
                    <td><input type="number" value="${p.stock}" id="stock-${p.id}" style="width:60px; padding:4px;" onchange="editProductStock(${p.id})"></td>
                    <td><span style="color:${p.status === 'active' ? '#2e7d32' : '#c62828'}; font-weight:600;">${p.status.toUpperCase()}</span></td>
                    <td>
                        <button class="btn-action" onclick="toggleSuspend(${p.id})">${p.status === 'active' ? 'Suspend' : 'Activate'}</button>
                        <button class="btn-action btn-danger" onclick="deleteProduct(${p.id})">Delete</button>
                    </td>
                </tr>`;
            });
        }

        function editProductStock(id) {
            let stock = document.getElementById('stock-' + id).value;
            let p = adminData.products.find(x => x.id === id);
            p.stock = parseInt(stock);
            fetch('/admin/api/product/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(p)
            });
        }

        function toggleSuspend(id) {
            let p = adminData.products.find(x => x.id === id);
            p.status = p.status === 'active' ? 'suspended' : 'active';
            fetch('/admin/api/product/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(p)
            }).then(() => renderProducts());
        }

        function deleteProduct(id) {
            if(confirm("Are you sure you want to delete this product?")) {
                fetch('/admin/api/product/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                }).then(res => res.json()).then(data => {
                    adminData.products = data.products;
                    renderProducts();
                });
            }
        }

        function updateLogo() {
            let logoVal = document.getElementById('logo-base64-val').value;
            if(!logoVal) return alert('Please select an image file first.');
            fetch('/admin/api/logo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ logo: logoVal })
            }).then(res => res.json()).then(data => {
                alert('Website logo updated successfully!');
            });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Kesh Aadar Flask Server Running...")
    app.run(host='0.0.0.0', port=5000, debug=True)
