from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import random
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'kesh_aadar_secure_key_2026'

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "subhraroy324@gmail.com"
SMTP_PASS = "azku hebm gpsr pggo"

# --- DATABASE & STORAGE (In-memory serverless compatible) ---
LOGO_STATE = {
    "url": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
    "name": "Kesh Aadar"
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

# --- BACKGROUND EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, payment_type):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> (Qty: 1) - ₹{i['price']}</li>" for i in items])
        track_url = f"https://{request.host}/order_success/{order_id}" if request.host else f"http://127.0.0.1:5000/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: left;">
                <h1 style="font-size: 32px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">KESH AADAR</h1>
                <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">Pure Botanical Remedies</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <h2 style="color: #1b4332; font-size: 20px;">Thank you for your order, {name}!</h2>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">Your order has been placed successfully and is being prepared with care.</p>
                
                <div style="background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%); color: white; padding: 25px; border-radius: 14px; margin: 25px 0; text-align: center;">
                    <p style="margin: 0; color: #d4a373; font-size: 11px; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">Order Reference ID</p>
                    <h3 style="margin: 10px 0; font-size: 30px; font-family: monospace; letter-spacing: 2px;">{order_id}</h3>
                    <p style="margin: 5px 0; font-size: 15px; font-weight: 500;">Total Amount: ₹{amount} ({payment_type})</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px; font-size: 15px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8; margin-bottom: 25px;">
                    {items_html}
                </ul>

                <p style="font-size: 13px; color: #555; margin-bottom: 8px;"><b>Shipping Address:</b> {full_address}</p>

                <div style="text-align: center; margin-top: 35px;">
                    <a href="{track_url}" style="background: #d4a373; color: #1b4332; text-decoration: none; padding: 14px 35px; border-radius: 30px; font-weight: 700; font-size: 15px; display: inline-block; box-shadow: 0 5px 15px rgba(212, 163, 115, 0.4);">Click Here to Track Your Order Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact support at {SMTP_EMAIL}</p>
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
    return render_template_string(TEMPLATE, products=active_products, logo=LOGO_STATE)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status_step'] = 'Order Placed' # Order Placed -> Packaging -> Shipped -> Delivered
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', 'N/A')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.append(data)
    
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, data.get('payment_type', 'Online Payment'))
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, logo=LOGO_STATE)

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
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, logo=LOGO_STATE, blacklisted=BLACKLISTED_IPS)

@app.route('/admin/api/update_status', methods=['POST'])
def admin_update_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status_step')
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status_step'] = new_status
            return jsonify({"status": "success"})
    return jsonify({"error": "Order not found"}), 404

@app.route('/admin/api/delete_order', methods=['POST'])
def admin_delete_order():
    global ORDERS
    data = request.get_json()
    order_id = data.get('order_id')
    ORDERS = [o for o in ORDERS if o['order_id'] != order_id]
    return jsonify({"status": "success"})

@app.route('/admin/api/logo', methods=['POST'])
def admin_update_logo():
    global LOGO_STATE
    if 'logo_file' in request.files:
        file = request.files['logo_file']
        if file and file.filename != '':
            encoded = base64.b64encode(file.read()).decode('utf-8')
            mime = file.mimetype or 'image/png'
            LOGO_STATE['url'] = f"data:{mime};base64,{encoded}"
    return jsonify({"status": "success", "logo": LOGO_STATE})

@app.route('/admin/api/product/add', methods=['POST'])
def admin_add_product():
    global PRODUCTS
    name = request.form.get('name')
    category = request.form.get('category', 'Skincare')
    price = float(request.form.get('price', 0))
    stock = int(request.form.get('stock', 10))
    desc = request.form.get('desc', '')
    
    image_url = request.form.get('image_url', 'https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80')
    if 'image_file' in request.files:
        img_file = request.files['image_file']
        if img_file and img_file.filename != '':
            encoded = base64.b64encode(img_file.read()).decode('utf-8')
            image_url = f"data:{img_file.mimetype or 'image/jpeg'};base64,{encoded}"

    video_url = ""
    if 'video_file' in request.files:
        vid_file = request.files['video_file']
        if vid_file and vid_file.filename != '':
            encoded = base64.b64encode(vid_file.read()).decode('utf-8')
            video_url = f"data:{vid_file.mimetype or 'video/mp4'};base64,{encoded}"

    new_id = max([p['id'] for p in PRODUCTS], default=0) + 1
    new_prod = {
        "id": new_id,
        "name": name,
        "category": category,
        "price": price,
        "stock": stock,
        "image": image_url,
        "video": video_url,
        "desc": desc,
        "status": "active"
    }
    PRODUCTS.append(new_prod)
    return redirect(url_for('admin_panel'))

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
            p['status'] = data.get('status', p.get('status', 'active'))
            return jsonify({"status": "success"})
    return jsonify({"error": "Product not found"}), 404

@app.route('/admin/api/product/toggle_status', methods=['POST'])
def admin_toggle_product_status():
    data = request.get_json()
    prod_id = int(data.get('id'))
    for p in PRODUCTS:
        if p['id'] == prod_id:
            p['status'] = 'suspended' if p.get('status', 'active') == 'active' else 'active'
            return jsonify({"status": "success", "new_status": p['status']})
    return jsonify({"error": "Product not found"}), 404

@app.route('/admin/api/product/delete', methods=['POST'])
def admin_delete_product():
    global PRODUCTS
    data = request.get_json()
    prod_id = int(data.get('id'))
    PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
    return jsonify({"status": "success"})


# --- TEMPLATES ---
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
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; transition: transform 0.3s ease; }
        .menu-btn:hover { transform: scale(1.1); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: 0.3s; }
        .cart-icon-container:hover { background: var(--accent-gold); color: white; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Butter-smooth Sidebar Drawer */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.4s; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); transition: transform 0.3s; }
        .close-sidebar:hover { transform: rotate(90deg); color: #c62828; }
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
        .product-media-container { height: 230px; overflow: hidden; background: #f7f5f0; position: relative; }
        .product-media-container img, .product-media-container video { width: 100%; height: 100%; object-fit: cover; }
        .product-info { padding: 20px; }
        .price-row { display: flex; justify-content: space-between; align-items: center; margin: 15px 0; }
        .price { font-size: 22px; font-weight: 700; color: var(--green-light); }
        .btn-group { display: flex; gap: 10px; }
        .btn-cart { flex: 1; padding: 10px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-cart:hover { background: #e5dfd3; }
        .btn-buy { flex: 1; padding: 10px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-buy:hover { background: var(--green-light); }

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
                <img src="{{ logo.url }}" alt="Logo" class="logo-img" id="headerLogoImg">
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
                <div class="product-media-container" id="media-{{ p.id }}">
                    {% if p.video %}
                    <video src="{{ p.video }}" autoplay muted loop playsinline></video>
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

            let mediaContainer = document.getElementById('media-' + id);
            let flyer = document.createElement('img');
            flyer.src = p.image || 'https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80';
            flyer.className = 'fly-item';
            
            let rect = mediaContainer.getBoundingClientRect();
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
                name: data.name,
                email: data.email,
                phone: data.phone,
                pincode: data.pincode,
                city: data.city,
                state: data.state,
                landmark: data.landmark,
                street: data.street
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
            let paymentTypeStr = mode === 'cod' ? 'Cash on Delivery' : 'Online Payment (Paid)';
            let payload = { name, email, phone, pincode, city, state, landmark, street, amount: amt, payment_type: paymentTypeStr, items: cart };

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
                    window.location.href = '/order_success/' + data.order.order_id;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- ANIMATED ORDER SUCCESS / TRACKING TEMPLATE ---
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
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; --green-light: #2d6a4f; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }

        @keyframes popIn { 0% { transform: scale(0.3); opacity: 0; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); } 70% { box-shadow: 0 0 0 25px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }

        .card { background: white; max-width: 620px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 45px; color: white; background: #2e7d32; border-radius: 50%; width: 85px; height: 85px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 28px; margin-bottom: 6px; }
        p.subtitle { color: #666; font-size: 13px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 14px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        /* Flipkart / Amazon Style Progress Line */
        .tracker-container { margin: 30px 0 20px 0; padding: 10px 0; }
        .tracker-steps { display: flex; justify-content: space-between; position: relative; max-width: 450px; margin: 0 auto; }
        .tracker-steps::before { content: ''; position: absolute; top: 18px; left: 30px; right: 30px; height: 4px; background: #e0e0e0; z-index: 1; }
        
        .step { position: relative; z-index: 2; text-align: center; flex: 1; }
        .step-icon { width: 40px; height: 40px; border-radius: 50%; background: #e0e0e0; color: #777; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 14px; font-weight: bold; transition: 0.3s; }
        .step.completed .step-icon { background: var(--green-primary); color: white; box-shadow: 0 0 10px rgba(27, 67, 50, 0.3); }
        .step.active .step-icon { background: var(--accent-gold); color: white; box-shadow: 0 0 12px rgba(212, 163, 115, 0.6); transform: scale(1.1); }
        .step-label { font-size: 11px; font-weight: 600; color: #666; }
        .step.completed .step-label, .step.active .step-label { color: var(--green-primary); }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; transition: 0.3s; }
        .btn-home:hover { background: var(--green-light); }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Tracking & Details</h1>
        <p class="subtitle">Live status updates for your Kesh Aadar botanical shipment</p>

        {% if order %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Email / Phone:</span><b>{{ order.email }} | {{ order.phone }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color:#2e7d32;">{{ order.payment_type }}</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 260px; text-align: right;">{{ order.full_address }}</span></div>
            <hr style="border: 0; border-top: 1px solid #ddd; margin: 12px 0;">
            <div class="info-row"><span>Ordered Items:</span></div>
            <ul style="padding-left: 20px; font-size: 12px; color: #555; margin-bottom: 8px;">
                {% for item in order.items %}
                <li>{{ item.name }} - ₹{{ item.price }}</li>
                {% endfor %}
            </ul>
            <div class="info-row" style="font-weight: bold; font-size: 14px; color: var(--green-primary); border-top: 1px dashed #d4a373; padding-top: 8px;">
                <span>Total Bill (incl. taxes/fees):</span><span>₹{{ order.amount }}</span>
            </div>
        </div>

        {% set current_step = order.status_step %}
        <div class="tracker-container">
            <h4 style="font-size: 14px; color: var(--green-primary); margin-bottom: 15px;">Delivery Progress</h4>
            <div class="tracker-steps">
                <div class="step {% if current_step in ['Order Placed', 'Packaging', 'Shipped', 'Delivered'] %}completed{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-file-invoice"></i></div>
                    <div class="step-label">Placed</div>
                </div>
                <div class="step {% if current_step in ['Packaging', 'Shipped', 'Delivered'] %}completed{% elif current_step == 'Packaging' %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-box-open"></i></div>
                    <div class="step-label">Packaging</div>
                </div>
                <div class="step {% if current_step in ['Shipped', 'Delivered'] %}completed{% elif current_step == 'Shipped' %}active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-truck-fast"></i></div>
                    <div class="step-label">Shipped</div>
                </div>
                <div class="step {% if current_step == 'Delivered' %}completed active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-house-chimney"></i></div>
                    <div class="step-label">Delivered</div>
                </div>
            </div>
        </div>
        {% else %}
        <div class="order-info-box" style="text-align: center;">
            <p style="color: #c62828;">Order reference not found or expired.</p>
            <b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b>
        </div>
        {% endif %}

        <a href="/" class="btn-home" style="margin-top: 15px;">Return to Storefront</a>
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
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --cream-dark: #F3EFEA; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); display: flex; min-height: 100vh; color: #333; }

        /* Admin Sidebar */
        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; padding: 30px 20px; display: flex; flex-direction: column; justify-content: space-between; position: fixed; height: 100%; left: 0; top: 0; z-index: 100; transition: transform 0.4s ease; }
        .admin-logo { font-size: 20px; font-weight: 700; color: var(--accent-gold); margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; }
        .admin-nav { display: flex; flex-direction: column; gap: 10px; flex: 1; }
        .admin-nav button { background: none; border: none; color: white; padding: 12px 15px; text-align: left; border-radius: 8px; cursor: pointer; font-weight: 500; font-size: 14px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .admin-nav button:hover, .admin-nav button.active { background: rgba(255,255,255,0.1); color: var(--accent-gold); }

        /* Main Content */
        .admin-main { margin-left: 260px; flex: 1; padding: 40px; overflow-y: auto; }
        .tab-section { display: none; }
        .tab-section.active { display: block; }

        h2 { color: var(--green-primary); margin-bottom: 25px; font-size: 24px; }
        .card { background: white; padding: 25px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); margin-bottom: 25px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); font-weight: 600; }

        .form-control { width: 100%; padding: 10px; margin-bottom: 12px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
        .btn { background: var(--green-primary); color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
        .btn-danger { background: #c62828; }
        .btn-warning { background: #e65100; }
        
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .badge-active { background: #e8f5e9; color: #2e7d32; }
        .badge-suspended { background: #ffebee; color: #c62828; }
    </style>
</head>
<body>

    <!-- Admin Sidebar -->
    <div class="admin-sidebar" id="adminSidebar">
        <div>
            <div class="admin-logo">
                <span>KESH ADMIN</span>
                <i class="fa-solid fa-xmark" style="cursor:pointer;" onclick="toggleAdminSidebar()"></i>
            </div>
            <div class="admin-nav">
                <button class="active" onclick="switchTab('orders', this)"><i class="fa-solid fa-box"></i> Customer Orders</button>
                <button onclick="switchTab('products', this)"><i class="fa-solid fa-tags"></i> Product Management</button>
                <button onclick="switchTab('logo', this)"><i class="fa-solid fa-image"></i> Website Logo</button>
                <button onclick="window.location.href='/'"><i class="fa-solid fa-store"></i> View Storefront</button>
            </div>
        </div>
        <div style="font-size: 11px; color: #aaa; text-align: center;">Secure Admin Panel v2.6</div>
    </div>

    <!-- Main Dashboard Area -->
    <div class="admin-main">
        
        <!-- Top bar with toggle button if closed -->
        <div style="margin-bottom: 20px;">
            <button class="btn" onclick="toggleAdminSidebar()" style="background: var(--green-primary);"><i class="fa-solid fa-bars"></i> Toggle Menu</button>
        </div>

        <!-- ORDERS TAB -->
        <div id="tab-orders" class="tab-section active">
            <h2>Customer Orders Management</h2>
            <div class="card">
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Order ID & Date</th>
                                <th>Customer Details</th>
                                <th>Items & Amount</th>
                                <th>Shipping Address</th>
                                <th>Status Control</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% if orders %}
                                {% for o in orders %}
                                <tr>
                                    <td><b>{{ o.order_id }}</b><br><span style="font-size:11px; color:#666;">{{ o.date }}</span></td>
                                    <td><b>{{ o.name }}</b><br>{{ o.phone }}<br>{{ o.email }}</td>
                                    <td>₹<b>{{ o.amount }}</b> ({{ o.payment_type }})<br><span style="font-size:11px; color:#555;">{{ o.items | length }} items</span></td>
                                    <td style="font-size:12px; max-width:200px;">{{ o.full_address }}</td>
                                    <td>
                                        <select class="form-control" style="margin:0; width:140px; font-size:12px;" onchange="updateOrderStatus('{{ o.order_id }}', this.value)">
                                            <option value="Order Placed" {% if o.status_step == 'Order Placed' %}selected{% endif %}>Order Placed</option>
                                            <option value="Packaging" {% if o.status_step == 'Packaging' %}selected{% endif %}>Packaging</option>
                                            <option value="Shipped" {% if o.status_step == 'Shipped' %}selected{% endif %}>Shipped</option>
                                            <option value="Delivered" {% if o.status_step == 'Delivered' %}selected{% endif %}>Delivered</option>
                                        </select>
                                    </td>
                                    <td>
                                        <button class="btn btn-danger" style="padding:6px 10px; font-size:11px;" onclick="deleteOrder('{{ o.order_id }}')"><i class="fa-solid fa-trash"></i></button>
                                    </td>
                                </tr>
                                {% endfor %}
                            {% else %}
                                <tr><td colspan="6" style="text-align:center; color:#888; padding:30px;">No orders placed yet.</td></tr>
                            {% endif %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- PRODUCTS TAB -->
        <div id="tab-products" class="tab-section">
            <h2>Product & Inventory Management</h2>
            
            <div class="card">
                <h3 style="font-size:16px; color:var(--green-primary); margin-bottom:15px;"><i class="fa-solid fa-plus-circle"></i> Add New Botanical Product</h3>
                <form action="/admin/api/product/add" method="POST" enctype="multipart/form-data">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                        <input type="text" name="name" class="form-control" placeholder="Product Name *" required>
                        <input type="text" name="category" class="form-control" placeholder="Category (e.g., Skincare) *" required>
                        <input type="number" name="price" class="form-control" placeholder="Price (INR) *" required>
                        <input type="number" name="stock" class="form-control" placeholder="Stock Quantity *" required>
                    </div>
                    <textarea name="desc" class="form-control" placeholder="Product Description *" rows="2" required></textarea>
                    
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:10px; font-size:13px;">
                        <div>
                            <label style="display:block; font-weight:600; margin-bottom:5px;">Product Image File (Gallery):</label>
                            <input type="file" name="image_file" accept="image/*" class="form-control">
                        </div>
                        <div>
                            <label style="display:block; font-weight:600; margin-bottom:5px;">Product Video File (Optional):</label>
                            <input type="file" name="video_file" accept="video/*" class="form-control">
                        </div>
                    </div>
                    <button type="submit" class="btn">Upload Product</button>
                </form>
            </div>

            <div class="card">
                <h3 style="font-size:16px; color:var(--green-primary); margin-bottom:15px;">Existing Inventory</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Preview</th>
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
                                <img src="{{ p.image }}" style="width:45px; height:45px; object-fit:cover; border-radius:6px;">
                            </td>
                            <td><b>{{ p.name }}</b><br><span style="font-size:11px; color:#666;">{{ p.category }}</span></td>
                            <td>₹<input type="number" id="price-{{ p.id }}" value="{{ p.price }}" style="width:70px; padding:4px;" /> | Stock: <input type="number" id="stock-{{ p.id }}" value="{{ p.stock }}" style="width:50px; padding:4px;" /></td>
                            <td>
                                {% if p.status == 'suspended' %}
                                <span class="badge badge-suspended">Suspended</span>
                                {% else %}
                                <span class="badge badge-active">Live</span>
                                {% endif %}
                            </td>
                            <td>
                                <button class="btn" style="padding:6px 10px; font-size:11px;" onclick="saveProduct({{ p.id }})">Save</button>
                                <button class="btn btn-warning" style="padding:6px 10px; font-size:11px;" onclick="toggleProductStatus({{ p.id }})">Toggle</button>
                                <button class="btn btn-danger" style="padding:6px 10px; font-size:11px;" onclick="deleteProduct({{ p.id }})"><i class="fa-solid fa-trash"></i></button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- LOGO TAB -->
        <div id="tab-logo" class="tab-section">
            <h2>Website Logo & Branding</h2>
            <div class="card" style="max-width: 500px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <img src="{{ logo.url }}" style="width: 90px; height: 90px; object-fit: cover; border-radius: 50%; border: 3px solid var(--accent-gold);">
                    <p style="margin-top: 10px; font-size: 13px; color: #666;">Current Storefront Logo</p>
                </div>
                <form id="logoForm" onsubmit="event.preventDefault(); uploadLogo();">
                    <label style="display:block; font-weight:600; margin-bottom:8px; font-size:13px;">Upload New Logo from Gallery:</label>
                    <input type="file" id="logoFileInput" accept="image/*" class="form-control" required>
                    <button type="submit" class="btn" style="width:100%; margin-top:10px;">Update Website Logo</button>
                </form>
            </div>
        </div>

    </div>

    <script>
        function toggleAdminSidebar() {
            let sb = document.getElementById('adminSidebar');
            sb.style.transform = sb.style.transform === 'translateX(-260px)' ? 'translateX(0)' : 'translateX(-260px)';
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.admin-nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            btn.classList.add('active');
        }

        function updateOrderStatus(order_id, status_step) {
            fetch('/admin/api/update_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id, status_step })
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    alert('Order status successfully updated to: ' + status_step);
                }
            });
        }

        function deleteOrder(order_id) {
            if(confirm('Are you sure you want to delete order ' + order_id + '?')) {
                fetch('/admin/api/delete_order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ order_id })
                }).then(() => location.reload());
            }
        }

        function saveProduct(id) {
            let price = document.getElementById('price-' + id).value;
            let stock = document.getElementById('stock-' + id).value;
            fetch('/admin/api/product/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, price, stock })
            }).then(() => alert('Product updated successfully!'));
        }

        function toggleProductStatus(id) {
            fetch('/admin/api/product/toggle_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            }).then(() => location.reload());
        }

        function deleteProduct(id) {
            if(confirm('Permanently delete this product?')) {
                fetch('/admin/api/product/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                }).then(() => location.reload());
            }
        }

        function uploadLogo() {
            let fileInput = document.getElementById('logoFileInput');
            if(fileInput.files.length === 0) return alert('Please select an image file.');
            let formData = new FormData();
            formData.append('logo_file', fileInput.files[0]);

            fetch('/admin/api/logo', {
                method: 'POST',
                body: formData
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    alert('Website logo updated successfully!');
                    location.reload();
                }
            });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Kesh Aadar Flask Server Running...")
    app.run(host='0.0.0.0', port=5000, debug=True)
