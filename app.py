from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import random
import base64

app = Flask(__name__)
app.secret_key = 'kesh_aadar_secure_key_2026_prod'

# --- SMTP EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "keshaadar@gmail.com"
SMTP_PASS = "zvxb mrbs ccoi vfrl"

# --- IN-MEMORY DATABASE & CONFIG ---
SITE_CONFIG = {
    "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80"
}

PRODUCTS = [
    {
        "id": 1, 
        "name": "Aloe Neem Glow Face Wash", 
        "category": "Skincare", 
        "price": 349, 
        "stock": 50, 
        "media_type": "image",
        "media_src": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", 
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
        "media_src": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", 
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
        "media_src": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", 
        "desc": "Stops hair fall and stimulates roots naturally.",
        "status": "active"
    },
    {
        "id": 4, 
        "name": "Hibiscus & Shikakai Herbal Shampoo", 
        "category": "Haircare", 
        "price": 399, 
        "stock": 45, 
        "media_type": "image",
        "media_src": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80", 
        "desc": "Nourishing sulfate-free cleanser for smooth hair.",
        "status": "active"
    }
]

ORDERS = []

# --- BACKGROUND EMAIL FUNCTION ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, payment_type, base_url):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: #{order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> (Qty: {i.get('qty', 1)}) - ₹{i['price'] * i.get('qty', 1)}</li>" for i in items])
        track_url = f"{base_url}/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Segoe UI', sans-serif; background-color: #FAF7F0; padding: 40px 15px; margin: 0; color: #2b2b2b;">
            <div style="background: #ffffff; max-width: 600px; margin: 0 auto; border-radius: 20px; overflow: hidden; box-shadow: 0 15px 35px rgba(27,67,50,0.1); border: 1px solid #EAE5D9;">
                
                <!-- HEADER BANNER -->
                <div style="background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%); padding: 35px 20px; text-align: center; color: white;">
                    <h1 style="font-family: 'Georgia', serif; font-size: 32px; margin: 0; letter-spacing: 2px;">KESH AADAR</h1>
                    <p style="letter-spacing: 4px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: 700; margin-top: 5px;">Pure Botanical Remedies</p>
                </div>

                <!-- MAIN BODY -->
                <div style="padding: 35px 30px;">
                    <h2 style="color: #1b4332; font-size: 22px; margin-top: 0;">Thank you for your order, {name}! 🎉</h2>
                    <p style="font-size: 14px; color: #555; line-height: 1.6;">We have received your botanical order and are currently preparing it for dispatch.</p>
                    
                    <!-- ORDER INFO BOX -->
                    <div style="background: #FAF7F0; border: 1px dashed #d4a373; border-radius: 14px; padding: 20px; margin: 25px 0;">
                        <p style="margin: 0; color: #888; font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;">Order Reference ID</p>
                        <h3 style="margin: 6px 0 12px 0; font-size: 26px; color: #1b4332; font-family: monospace;">{order_id}</h3>
                        <p style="margin: 4px 0; color: #333; font-size: 14px;"><b>Payment Status:</b> <span style="color: #2e7d32; font-weight: bold;">{payment_type}</span></p>
                        <p style="margin: 4px 0; color: #333; font-size: 14px;"><b>Total Payable:</b> ₹{amount}</p>
                        <p style="margin: 4px 0 0 0; color: #555; font-size: 13px;"><b>Shipping Address:</b> {full_address}</p>
                    </div>

                    <h4 style="color: #1b4332; font-size: 16px; margin-bottom: 12px; border-bottom: 2px solid #FAF7F0; padding-bottom: 6px;">Ordered Items:</h4>
                    <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8; margin-bottom: 30px;">
                        {items_html}
                    </ul>

                    <!-- TRACK BUTTON -->
                    <div style="text-align: center; margin: 35px 0 15px 0;">
                        <a href="{track_url}" style="background: #1b4332; color: #ffffff; text-decoration: none; padding: 16px 36px; border-radius: 30px; font-weight: 700; font-size: 15px; display: inline-block; box-shadow: 0 8px 20px rgba(27, 67, 50, 0.25);">Track Order Status & Details</a>
                    </div>
                </div>

                <!-- FOOTER -->
                <div style="background: #FAF7F0; padding: 20px; text-align: center; border-top: 1px solid #EAE5D9;">
                    <p style="font-size: 12px; color: #777; margin: 0;">Need assistance? Reply directly to this email or contact support at <a href="mailto:{SMTP_EMAIL}" style="color: #1b4332; font-weight: bold;">{SMTP_EMAIL}</a></p>
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
        
        # Also notify store owner
        msg_owner = MIMEMultipart('alternative')
        msg_owner['Subject'] = f"🔔 NEW ORDER RECEIVED: #{order_id}"
        msg_owner['From'] = f"KESH AADAR Store <{SMTP_EMAIL}>"
        msg_owner['To'] = SMTP_EMAIL
        msg_owner.attach(MIMEText(f"New Order #{order_id} placed by {name} worth ₹{amount}. Check Admin Panel.", 'plain'))
        server.sendmail(SMTP_EMAIL, SMTP_EMAIL, msg_owner.as_string())
        
        server.quit()
    except Exception as e:
        print(f"SMTP Error: {e}")

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    active_products = [p for p in PRODUCTS if p.get('status', 'active') == 'active']
    return render_template_string(MAIN_TEMPLATE, products=active_products, site_config=SITE_CONFIG)

@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        data = request.get_json()
        order_id = "KESH-" + str(random.randint(100000, 999999))
        data['order_id'] = order_id
        data['status'] = 'Placed'  # Default Order Status: Placed -> Packaging -> Shipped -> Delivered
        data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
        
        full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', 'N/A')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
        data['full_address'] = full_address
        
        ORDERS.append(data)
        
        # Determine host dynamically
        base_url = request.host_url.rstrip('/')
        
        # Background Email dispatch to eliminate connection timeout or lag
        email_thread = threading.Thread(
            target=send_order_email, 
            args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, data['payment_type'], base_url)
        )
        email_thread.start()
        
        return jsonify({"status": "success", "order_id": order_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(TRACKING_TEMPLATE, order=order, order_id=order_id, site_config=SITE_CONFIG)

@app.route('/track_order')
def track_order():
    q = request.args.get('q', '').strip()
    for o in ORDERS:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order": o})
    return jsonify({"found": False})

# --- ADMIN ROUTES ---
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, site_config=SITE_CONFIG)

@app.route('/admin/update_logo', methods=['POST'])
def update_logo():
    data = request.get_json()
    if data and 'logo_base64' in data:
        SITE_CONFIG['logo'] = data['logo_base64']
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    data = request.get_json()
    new_id = len(PRODUCTS) + 1
    new_prod = {
        "id": new_id,
        "name": data.get("name"),
        "category": data.get("category", "General"),
        "price": float(data.get("price", 0)),
        "stock": int(data.get("stock", 0)),
        "media_type": data.get("media_type", "image"),
        "media_src": data.get("media_src"),
        "desc": data.get("desc", ""),
        "status": "active"
    }
    PRODUCTS.append(new_prod)
    return jsonify({"status": "success", "product": new_prod})

@app.route('/admin/update_product', methods=['POST'])
def update_product():
    data = request.get_json()
    prod_id = int(data.get("id"))
    for p in PRODUCTS:
        if p['id'] == prod_id:
            p['name'] = data.get('name', p['name'])
            p['price'] = float(data.get('price', p['price']))
            p['stock'] = int(data.get('stock', p['stock']))
            p['desc'] = data.get('desc', p['desc'])
            return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

@app.route('/admin/toggle_product', methods=['POST'])
def toggle_product():
    data = request.get_json()
    prod_id = int(data.get("id"))
    for p in PRODUCTS:
        if p['id'] == prod_id:
            p['status'] = 'suspended' if p.get('status') == 'active' else 'active'
            return jsonify({"status": "success", "new_status": p['status']})
    return jsonify({"status": "error"}), 404

@app.route('/admin/delete_product', methods=['POST'])
def delete_product():
    data = request.get_json()
    prod_id = int(data.get("id"))
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
    return jsonify({"status": "success"})

@app.route('/admin/update_order_status', methods=['POST'])
def update_order_status():
    data = request.get_json()
    order_id = data.get("order_id")
    new_status = data.get("status")  # Placed, Packaging, Shipped, Delivered
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status'] = new_status
            return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404


# ==============================================================================
# TEMPLATES SECTION
# ==============================================================================

MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KESH AADAR | Pure Botanical Remedies</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); overflow-x: hidden; }

        /* Smooth reveal animation */
        .reveal { opacity: 0; transform: translateY(30px); transition: all 0.7s cubic-bezier(0.16, 1, 0.3, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }

        /* Header */
        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 20px rgba(0,0,0,0.04); }
        .nav-left { display: flex; align-items: center; gap: 18px; }
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; transition: transform 0.2s; }
        .menu-btn:hover { transform: scale(1.1); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 44px; height: 44px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: background 0.3s; }
        .cart-icon-container:hover { background: #e8e2d5; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Drawer Sidebar & Smooth Sliding Animation */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); backdrop-filter: blur(4px); z-index: 1500; opacity: 0; visibility: hidden; transition: all 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -360px; width: 340px; height: 100%; background: white; box-shadow: 0 0 30px rgba(0,0,0,0.15); z-index: 2000; transition: transform 0.4s cubic-bezier(0.25, 1, 0.5, 1); padding: 30px 22px; overflow-y: auto; }
        .sidebar.active { transform: translateX(360px); }
        .close-sidebar { font-size: 24px; cursor: pointer; float: right; color: var(--text-dark); transition: color 0.2s; }
        .close-sidebar:hover { color: #c62828; }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 20px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 10px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 12px; transition: 0.3s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); padding-left: 18px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 6px; cursor: pointer; margin-bottom: 20px; font-size: 12px; }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }

        /* Hero */
        .hero { height: 75vh; display: flex; align-items: center; justify-content: center; text-align: center; background: radial-gradient(circle, #f3efea 0%, #faf7f0 75%); margin-top: 70px; padding: 0 20px; }
        .hero-content h1 { font-family: 'Playfair Display', serif; font-size: clamp(34px, 6vw, 54px); color: var(--green-primary); margin-bottom: 15px; }
        .btn-primary { background: var(--green-primary); color: white; padding: 14px 38px; border-radius: 35px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: 0.3s; }
        .btn-primary:hover { background: var(--green-light); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(27,67,50,0.2); }

        .features-banner { background: var(--green-primary); color: white; display: flex; justify-content: space-around; padding: 20px; flex-wrap: wrap; gap: 15px; }
        .feature-item { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 500; }

        /* Products Grid */
        .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 30px; }
        .product-card { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.04); transition: 0.3s; border: 1px solid #EAE5D9; }
        .product-card:hover { transform: translateY(-6px); box-shadow: 0 15px 35px rgba(0,0,0,0.08); }
        .product-media-container { height: 240px; overflow: hidden; background: #f7f5f0; position: relative; }
        .product-media-container img, .product-media-container video { width: 100%; height: 100%; object-fit: cover; }
        .product-info { padding: 20px; }
        .price-row { display: flex; justify-content: space-between; align-items: center; margin: 15px 0; }
        .price { font-size: 22px; font-weight: 700; color: var(--green-light); }
        .btn-group { display: flex; gap: 10px; }
        .btn-cart { flex: 1; padding: 11px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-buy { flex: 1; padding: 11px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-cart:hover { background: #e2dbcd; }
        .btn-buy:hover { background: var(--green-light); }

        /* Flying Item Animation */
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

        footer { background-color: var(--green-primary); color: white; padding: 50px 30px 20px; margin-top: 60px; }
        .footer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 30px; max-width: 1200px; margin: 0 auto; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 30px; }
        .footer-grid h3 { color: var(--accent-gold); font-family: 'Playfair Display'; font-size: 20px; margin-bottom: 15px; }
        .footer-grid p { font-size: 14px; margin-bottom: 10px; color: #ddd; }
        .footer-bottom { padding-top: 20px; font-size: 12px; color: #aaa; text-align: center; }
    </style>
</head>
<body>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
                <img src="{{ site_config.logo }}" alt="Logo" class="logo-img" id="siteLogo">
                <div class="logo"><span>Kesh</span> Aadar</div>
            </div>
        </div>
        <div class="cart-icon-container" id="cartTarget" onclick="openCartModal()">
            <i class="fa-solid fa-shopping-basket"></i><span class="cart-badge" id="cart-count">0</span>
        </div>
    </header>

    <!-- Sidebar Drawer (No Admin Link Present) -->
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <span class="close-sidebar" onclick="toggleSidebar()">&times;</span>
        
        <div id="sidebar-main-view">
            <h3 style="margin-top: 10px;">Menu</h3>
            <p style="font-size: 13px; color: #666; margin-bottom: 25px;">Welcome to Kesh Aadar</p>
            <button class="menu-item" onclick="switchSidebarView('track')"><i class="fa-solid fa-map-location-dot" style="color:var(--accent-gold);"></i> Track Live Order</button>
            <button class="menu-item" onclick="switchSidebarView('support')"><i class="fa-solid fa-headset" style="color:var(--accent-gold);"></i> Help & Support</button>
            <button class="menu-item" onclick="switchSidebarView('faq')"><i class="fa-solid fa-circle-question" style="color:var(--accent-gold);"></i> Product FAQs</button>
        </div>

        <div id="sidebar-track-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Track Order</h3>
            <input type="text" id="track-input" placeholder="Enter Order ID or Email">
            <button class="action-btn" onclick="trackOrder()">Track Now</button>
            <div id="track-result" style="margin-top: 20px;"></div>
        </div>

        <div id="sidebar-support-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Customer Support</h3>
            <p style="font-size:13px; margin-top:10px;"><i class="fa-solid fa-envelope"></i> keshaadar@gmail.com</p>
            <p style="font-size:13px; margin-top:5px;"><i class="fa-solid fa-phone"></i> +91 9163641507</p>
        </div>

        <div id="sidebar-faq-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>FAQs</h3>
            <p style="font-size:12px; margin-top:10px; font-weight:600;">How long does shipping take?</p>
            <p style="font-size:12px; color:#666;">Usually dispatches within 24 hours.</p>
        </div>
    </div>

    <!-- Hero Section -->
    <section class="hero reveal">
        <div class="hero-content">
            <h1>Pure Botanical Remedies</h1>
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

    <!-- Products Container -->
    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 28px; color: var(--green-primary); margin-bottom: 30px;" class="reveal">Our Formulations</h2>
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-media-container">
                    {% if p.media_type == 'video' %}
                        <video src="{{ p.media_src }}" controls id="img-{{ p.id }}"></video>
                    {% else %}
                        <img src="{{ p.media_src }}" alt="{{ p.name }}" id="img-{{ p.id }}">
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
    <footer>
        <div class="footer-grid">
            <div>
                <h3>KESH AADAR</h3>
                <p>Bringing ancient botanical secrets directly into your daily routine. Pure and natural.</p>
            </div>
            <div>
                <h3>Support</h3>
                <p><i class="fa-solid fa-envelope"></i> keshaadar@gmail.com</p>
                <p><i class="fa-solid fa-phone"></i> +91 9163641507</p>
            </div>
        </div>
        <div class="footer-bottom">&copy; 2026 Kesh Aadar Botanical Remedies. All Rights Reserved.</div>
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
                        <input type="email" id="cust-email" class="full-width" placeholder="Email Address *" required>
                        <input type="tel" id="cust-phone" class="full-width" placeholder="Phone Number *" required pattern="[0-9]{10}">
                        <input type="text" id="cust-pincode" placeholder="PIN Code *" required pattern="[0-9]{6}" maxlength="6" onkeyup="detectPinCode(this.value)">
                        <input type="text" id="cust-city" placeholder="City *" required readonly style="background:#f4f4f4;">
                        <input type="text" id="cust-state" placeholder="State *" required readonly style="background:#f4f4f4;">
                        <input type="text" id="cust-landmark" class="full-width" placeholder="Landmark (Optional)">
                        <textarea id="cust-street" class="full-width" placeholder="Flat, House No., Building, Street *" rows="2" required></textarea>
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

                    <button type="submit" class="btn-primary" style="width:100%; border-radius:10px;" id="payBtn">Proceed to Place Order</button>
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
                if (elementTop < windowHeight - 30) { reveals[i].classList.add("active"); }
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

        // Animated Flying Cart Item
        function addToCartAndFly(event, id) {
            let p = productsData.find(x => x.id === id);
            let existing = cart.find(x => x.id === id);
            if(existing) { existing.qty += 1; } else { cart.push({...p, qty: 1}); }
            updateCartUI();

            let target = document.getElementById('img-' + id);
            if(target && target.tagName === 'IMG') {
                let flyer = target.cloneNode(true);
                flyer.className = 'fly-item';
                let rect = target.getBoundingClientRect();
                flyer.style.top = rect.top + 'px';
                flyer.style.left = rect.left + 'px';
                document.body.appendChild(flyer);

                let dest = document.getElementById('cartTarget').getBoundingClientRect();
                setTimeout(() => {
                    flyer.style.top = dest.top + 'px';
                    flyer.style.left = dest.left + 'px';
                    flyer.style.transform = 'scale(0.1)';
                    flyer.style.opacity = '0';
                }, 50);
                setTimeout(() => flyer.remove(), 850);
            }
        }

        function buyNow(id) {
            let p = productsData.find(x => x.id === id);
            cart = [{...p, qty: 1}];
            updateCartUI();
            openCartModal();
        }

        function openCartModal() {
            document.getElementById('cartModal').style.display = 'flex';
            updateCartUI();
        }

        function updateCartUI() {
            let totalItems = cart.reduce((s, i) => s + i.qty, 0);
            document.getElementById('cart-count').innerText = totalItems;
            let container = document.getElementById('cart-items-container');
            container.innerHTML = '';
            
            if(cart.length === 0) {
                container.innerHTML = '<p style="text-align:center; color:#888; margin:20px 0;">Your basket is empty.</p>';
                document.getElementById('checkout-section').style.display = 'none';
            } else {
                cart.forEach((item, index) => {
                    container.innerHTML += `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:8px; font-size:13px;">
                        <div><b>${item.name}</b> x${item.qty}</div>
                        <div style="display:flex; align-items:center; gap:10px;">
                            <span>₹${item.price * item.qty}</span>
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
            let base = cart.reduce((s, i) => s + (i.price * i.qty), 0);
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
                        let po = data[0].PostOffice[0];
                        document.getElementById('cust-city').value = po.District;
                        document.getElementById('cust-state').value = po.State;
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
                return alert('Please complete all required address fields.');
            }

            let amt = updateTotal();
            let payload = { 
                name, email, phone, pincode, city, state, landmark, street, 
                amount: amt, 
                payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Paid (Razorpay)', 
                items: cart 
            };

            if(mode === 'online') {
                var options = {
                    "key": "rzp_test_dummykey", 
                    "amount": amt * 100, 
                    "currency": "INR", 
                    "name": "KESH AADAR",
                    "description": "Order Payment",
                    "handler": function (res) { 
                        payload.payment_id = res.razorpay_payment_id || 'RZP_SUCCESS';
                        sendData(payload); 
                    },
                    "prefill": { "name": name, "email": email, "contact": phone }, 
                    "theme": { "color": "#1b4332" }
                };
                try {
                    new Razorpay(options).open();
                } catch(e) {
                    payload.payment_id = 'RZP_MOCK_SUCCESS';
                    sendData(payload);
                }
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
                if(data.status === 'success') {
                    window.location.href = '/order_success/' + data.order_id;
                } else {
                    alert('Error placing order: ' + data.message);
                }
            });
        }

        function trackOrder() {
            let q = document.getElementById('track-input').value.trim();
            if(!q) return;
            fetch('/track_order?q=' + encodeURIComponent(q)).then(r => r.json()).then(data => {
                let d = document.getElementById('track-result');
                if(data.found) {
                    window.location.href = '/order_success/' + data.order.order_id;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No matching order found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

TRACKING_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Status #{{ order_id }} | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; padding: 40px 20px; color: #2b2b2b; }

        .container { max-width: 700px; margin: 0 auto; background: white; padding: 40px 30px; border-radius: 24px; box-shadow: 0 15px 35px rgba(0,0,0,0.05); border: 1px solid #EAE5D9; }
        .header-brand { text-align: center; margin-bottom: 30px; }
        .header-brand h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 28px; }

        /* AMAZON / FLIPKART STYLE TRACKING BAR */
        .tracking-bar-wrapper { margin: 40px 0; }
        .tracking-bar { display: flex; justify-content: space-between; position: relative; }
        .tracking-bar::before { content: ''; position: absolute; top: 18px; left: 10%; width: 80%; height: 4px; background: #e0e0e0; z-index: 1; }
        .tracking-progress { position: absolute; top: 18px; left: 10%; height: 4px; background: #2e7d32; z-index: 1; transition: width 0.5s ease; }
        
        .step { position: relative; z-index: 2; text-align: center; flex: 1; }
        .step .node { width: 40px; height: 40px; border-radius: 50%; background: #e0e0e0; color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto 10px auto; font-size: 16px; transition: 0.3s; }
        .step.completed .node { background: #2e7d32; }
        .step.active .node { background: var(--accent-gold); box-shadow: 0 0 0 5px rgba(212,163,115,0.25); }
        .step-label { font-size: 12px; font-weight: 600; color: #777; }
        .step.completed .step-label, .step.active .step-label { color: var(--green-primary); }

        .details-box { background: #FAF7F0; border-radius: 16px; padding: 20px; border: 1px dashed var(--accent-gold); margin-bottom: 25px; }
        .detail-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; }
        .items-list { margin: 20px 0; font-size: 14px; border-top: 1px solid #eee; padding-top: 15px; }
        .item-line { display: flex; justify-content: space-between; margin-bottom: 8px; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: block; text-align: center; margin-top: 25px; }
    </style>
</head>
<body>

    <div class="container">
        <div class="header-brand">
            <h1>KESH AADAR</h1>
            <p style="font-size: 12px; color: var(--accent-gold); text-transform: uppercase; letter-spacing: 2px;">Official Order Tracking</p>
        </div>

        {% if order %}
        {% set status = order.get('status', 'Placed') %}
        
        <!-- TRACKING PROGRESS LOGIC -->
        {% set prog = '0%' %}
        {% if status == 'Placed' %}{% set prog = '0%' %}{% endif %}
        {% if status == 'Packaging' %}{% set prog = '33%' %}{% endif %}
        {% if status == 'Shipped' %}{% set prog = '66%' %}{% endif %}
        {% if status == 'Delivered' %}{% set prog = '80%' %}{% endif %}

        <div class="tracking-bar-wrapper">
            <div class="tracking-bar">
                <div class="tracking-progress" style="width: {{ prog }};"></div>

                <div class="step {% if status in ['Placed', 'Packaging', 'Shipped', 'Delivered'] %}completed{% endif %}">
                    <div class="node"><i class="fa-solid fa-check"></i></div>
                    <div class="step-label">Order Placed</div>
                </div>

                <div class="step {% if status in ['Packaging', 'Shipped', 'Delivered'] %}completed{% elif status == 'Packaging' %}active{% endif %}">
                    <div class="node"><i class="fa-solid fa-box"></i></div>
                    <div class="step-label">Packaging</div>
                </div>

                <div class="step {% if status in ['Shipped', 'Delivered'] %}completed{% elif status == 'Shipped' %}active{% endif %}">
                    <div class="node"><i class="fa-solid fa-truck-fast"></i></div>
                    <div class="step-label">Shipped</div>
                </div>

                <div class="step {% if status == 'Delivered' %}completed{% endif %}">
                    <div class="node"><i class="fa-solid fa-house-chimney"></i></div>
                    <div class="step-label">Delivered</div>
                </div>
            </div>
        </div>

        <div class="details-box">
            <div class="detail-row"><span>Order ID:</span><b style="font-family: monospace;">#{{ order.order_id }}</b></div>
            <div class="detail-row"><span>Date & Time:</span><b>{{ order.date }}</b></div>
            <div class="detail-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="detail-row"><span>Phone:</span><b>{{ order.phone }}</b></div>
            <div class="detail-row"><span>Payment Status:</span><b style="color: #2e7d32;">{{ order.payment_type }}</b></div>
            <div class="detail-row"><span>Shipping Address:</span><span style="max-width:250px; text-align:right; font-size:12px;">{{ order.full_address }}</span></div>
        </div>

        <h4 style="color:var(--green-primary);">Order Items Summary:</h4>
        <div class="items-list">
            {% for i in order.items %}
            <div class="item-line">
                <span>{{ i.name }} (Qty: {{ i.get('qty', 1) }})</span>
                <b>₹{{ i.price * i.get('qty', 1) }}</b>
            </div>
            {% endfor %}
            <hr style="margin: 10px 0; border: 0; border-top: 1px dashed #ccc;">
            <div class="item-line" style="font-size: 16px; color: var(--green-primary); font-weight: bold;">
                <span>Total Amount Paid/Payable:</span>
                <span>₹{{ order.amount }}</span>
            </div>
        </div>

        {% else %}
        <div style="text-align: center; padding: 30px;">
            <i class="fa-solid fa-circle-exclamation" style="font-size:40px; color:#c62828;"></i>
            <h3 style="margin-top:15px;">Order #{{ order_id }} Not Found</h3>
            <p style="font-size:13px; color:#666;">Please check your Order ID and try again.</p>
        </div>
        {% endif %}

        <a href="/" class="btn-home">Return to Storefront</a>
    </div>

</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kesh Aadar Admin Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: #f4f6f8; color: #333; }

        header { background: var(--green-primary); color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
        .admin-sidebar { position: fixed; top: 0; left: -280px; width: 260px; height: 100%; background: white; box-shadow: 2px 0 15px rgba(0,0,0,0.1); z-index: 2000; transition: 0.3s; padding: 25px 20px; }
        .admin-sidebar.active { left: 0; }
        .admin-sidebar h2 { font-size: 18px; color: var(--green-primary); margin-bottom: 20px; }
        .admin-sidebar button { width: 100%; padding: 12px; background: #f8f9fa; border: 1px solid #ddd; margin-bottom: 10px; border-radius: 8px; text-align: left; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 10px; }

        .container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
        .card { background: white; padding: 25px; border-radius: 16px; box-shadow: 0 5px 20px rgba(0,0,0,0.04); margin-bottom: 25px; }
        .card h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; border-bottom: 2px solid var(--cream); padding-bottom: 8px; }

        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); }

        .btn { padding: 8px 14px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; font-size: 12px; }
        .btn-green { background: var(--green-primary); color: white; }
        .btn-red { background: #c62828; color: white; }
        .btn-gold { background: var(--accent-gold); color: white; }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 5px; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; outline: none; }
    </style>
</head>
<body>

    <header>
        <div style="display:flex; align-items:center; gap:15px;">
            <i class="fa-solid fa-bars" style="font-size:22px; cursor:pointer;" onclick="toggleAdminSidebar()"></i>
            <h2>KESH AADAR - Admin Control Panel</h2>
        </div>
        <a href="/" target="_blank" style="color:white; text-decoration:none; font-size:13px;"><i class="fa-solid fa-globe"></i> View Website</a>
    </header>

    <div class="admin-sidebar" id="adminSidebar">
        <span style="float:right; cursor:pointer; font-size:20px;" onclick="toggleAdminSidebar()">&times;</span>
        <h2>Admin Menu</h2>
        <button onclick="showTab('orders')"><i class="fa-solid fa-cart-shopping"></i> Manage Orders</button>
        <button onclick="showTab('inventory')"><i class="fa-solid fa-boxes-stacked"></i> Inventory</button>
        <button onclick="showTab('add-product')"><i class="fa-solid fa-plus"></i> Add New Product</button>
        <button onclick="showTab('settings')"><i class="fa-solid fa-gear"></i> Branding Settings</button>
    </div>

    <div class="container">
        
        <!-- ORDERS TAB -->
        <div id="tab-orders" class="card">
            <h3><i class="fa-solid fa-cart-shopping"></i> Customer Orders Manager</h3>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Customer & Address</th>
                            <th>Total Amount</th>
                            <th>Payment</th>
                            <th>Status Control</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for o in orders %}
                        <tr>
                            <td><b>#{{ o.order_id }}</b><br><small>{{ o.date }}</small></td>
                            <td>
                                <b>{{ o.name }}</b> ({{ o.phone }})<br>
                                <small>{{ o.full_address }}</small>
                            </td>
                            <td>₹{{ o.amount }}</td>
                            <td><span style="padding:2px 6px; background:#e8f5e9; color:#2e7d32; border-radius:4px; font-weight:bold;">{{ o.payment_type }}</span></td>
                            <td>
                                <select onchange="updateOrderStatus('{{ o.order_id }}', this.value)" style="padding:6px; border-radius:6px;">
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
        </div>

        <!-- INVENTORY TAB -->
        <div id="tab-inventory" class="card" style="display:none;">
            <h3><i class="fa-solid fa-boxes-stacked"></i> Live Inventory Management</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Product Name</th>
                        <th>Price (₹)</th>
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
                        <td><input type="number" id="price-{{ p.id }}" value="{{ p.price }}" style="width:70px;"></td>
                        <td><input type="number" id="stock-{{ p.id }}" value="{{ p.stock }}" style="width:70px;"></td>
                        <td>
                            <span style="font-weight:bold; color: {% if p.status == 'active' %}green{% else %}red{% endif %};">
                                {{ p.status }}
                            </span>
                        </td>
                        <td>
                            <button class="btn btn-green" onclick="saveInventory({{ p.id }})">Save</button>
                            <button class="btn btn-gold" onclick="toggleProduct({{ p.id }})">Suspend/Unsuspend</button>
                            <button class="btn btn-red" onclick="deleteProduct({{ p.id }})">Delete</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- ADD PRODUCT TAB -->
        <div id="tab-add-product" class="card" style="display:none;">
            <h3><i class="fa-solid fa-plus"></i> Upload New Product (Image or Video)</h3>
            <form onsubmit="event.preventDefault(); submitNewProduct();">
                <div class="form-group">
                    <label>Product Name</label>
                    <input type="text" id="new-p-name" required>
                </div>
                <div class="form-group">
                    <label>Price (₹)</label>
                    <input type="number" id="new-p-price" required>
                </div>
                <div class="form-group">
                    <label>Available Stock</label>
                    <input type="number" id="new-p-stock" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="new-p-desc" rows="2"></textarea>
                </div>
                <div class="form-group">
                    <label>Upload Product File (Image/Video from Gallery)</label>
                    <input type="file" id="new-p-file" accept="image/*,video/*" required>
                </div>
                <button type="submit" class="btn btn-green">Upload Product</button>
            </form>
        </div>

        <!-- BRANDING SETTINGS TAB -->
        <div id="tab-settings" class="card" style="display:none;">
            <h3><i class="fa-solid fa-gear"></i> Website Branding Control</h3>
            <div class="form-group">
                <label>Change Website Logo (Upload Image)</label>
                <input type="file" id="logo-file" accept="image/*">
            </div>
            <button class="btn btn-green" onclick="uploadLogo()">Update Logo</button>
        </div>

    </div>

    <script>
        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('active');
        }

        function showTab(tab) {
            ['orders','inventory','add-product','settings'].forEach(t => document.getElementById('tab-'+t).style.display = 'none');
            document.getElementById('tab-'+tab).style.display = 'block';
            toggleAdminSidebar();
        }

        function updateOrderStatus(orderId, status) {
            fetch('/admin/update_order_status', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({order_id: orderId, status: status})
            }).then(r => r.json()).then(d => alert('Order status updated successfully!'));
        }

        function saveInventory(id) {
            let price = document.getElementById('price-'+id).value;
            let stock = document.getElementById('stock-'+id).value;
            fetch('/admin/update_product', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({id: id, price: price, stock: stock})
            }).then(r => r.json()).then(d => alert('Product updated!'));
        }

        function toggleProduct(id) {
            fetch('/admin/toggle_product', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({id: id})
            }).then(r => r.json()).then(d => location.reload());
        }

        function deleteProduct(id) {
            if(confirm('Delete product permanently?')) {
                fetch('/admin/delete_product', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({id: id})
                }).then(r => r.json()).then(d => location.reload());
            }
        }

        function submitNewProduct() {
            let name = document.getElementById('new-p-name').value;
            let price = document.getElementById('new-p-price').value;
            let stock = document.getElementById('new-p-stock').value;
            let desc = document.getElementById('new-p-desc').value;
            let fileInput = document.getElementById('new-p-file').files[0];

            let reader = new FileReader();
            reader.onload = function(e) {
                let mediaSrc = e.target.result;
                let mediaType = fileInput.type.startsWith('video') ? 'video' : 'image';

                fetch('/admin/add_product', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({ name, price, stock, desc, media_src: mediaSrc, media_type: mediaType })
                }).then(r => r.json()).then(d => {
                    alert('Product uploaded successfully!');
                    location.reload();
                });
            };
            reader.readAsDataURL(fileInput);
        }

        function uploadLogo() {
            let file = document.getElementById('logo-file').files[0];
            if(!file) return alert('Select an image');
            let reader = new FileReader();
            reader.onload = function(e) {
                fetch('/admin/update_logo', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({ logo_base64: e.target.result })
                }).then(r => r.json()).then(d => alert('Logo updated!'));
            };
            reader.readAsDataURL(file);
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
