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
SMTP_EMAIL = "keshaadar@gmail.com"
SMTP_PASS = "zvxb mrbs ccoi vfrl"

# --- DATABASE & STORAGE (In-memory state optimized for Vercel) ---
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
        "status": "live"
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
        "status": "live"
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
        "status": "live"
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
        "status": "live"
    }
]

ORDERS = []
SETTINGS = {
    "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
    "brand_name": "Kesh Aadar"
}

# --- BACKGROUND EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> (Qty: {i.get('quantity', 1)}) - ₹{i['price']}</li>" for i in items])
        track_url = f"https://{request.host}/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left; border: 1px solid #EAE5D9;">
                <h1 style="font-size: 36px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center; font-family: 'Playfair Display', serif;">KESH AADAR</h1>
                <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 12px; font-weight: bold; margin-top: 0; text-align: center;">Pure Botanical Remedies</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <div style="background: #e8f5e9; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;">
                    <h2 style="color: #2e7d32; font-size: 22px; margin: 0 0 5px 0;">Thank you for your order, {name}!</h2>
                    <p style="font-size: 13px; color: #333; margin: 0;">Your order has been placed successfully and is currently under processing.</p>
                </div>
                
                <div style="background: #F3EFEA; padding: 20px; border-radius: 12px; margin: 25px 0; border: 1px dashed #d4a373;">
                    <p style="margin: 0; color: #666; font-size: 12px; text-transform: uppercase; font-weight: bold;">Order Reference ID</p>
                    <h3 style="margin: 8px 0; font-size: 28px; color: #1b4332; font-family: monospace;">{order_id}</h3>
                    <p style="margin: 5px 0; color: #333; font-size: 14px; font-weight: 600;">Total Payable: ₹{amount}</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;"><b>Shipping To:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px;">Ordered Items:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 5px 15px rgba(27, 67, 50, 0.3);">Click Here to Check Order Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact us at keshaadar@gmail.com or reply directly to this email.</p>
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

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    live_products = [p for p in PRODUCTS if p.get('status', 'live') == 'live']
    return render_template_string(TEMPLATE, products=live_products, settings=SETTINGS)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status_step'] = 'Order Placed' # Initial status
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.append(data)
    
    # Send email in background thread instantly
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address)
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, settings=SETTINGS)

@app.route('/track_order')
def track_order():
    q = request.args.get('q', '').strip()
    for o in ORDERS:
        if q.upper() == o['order_id'] or q.lower() == o['email'].lower():
            return jsonify({"found": True, "order_id": o['order_id']})
    return jsonify({"found": False})

# --- ADMIN PANEL ROUTES (/admin) ---
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, settings=SETTINGS)

@app.route('/admin/api/update_order_status', methods=['POST'])
def admin_update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status') # Order Placed, Packaging, Shipped, Delivered
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status_step'] = new_status
            return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Order not found"}), 404

@app.route('/admin/api/add_product', methods=['POST'])
def admin_add_product():
    try:
        name = request.form.get('name')
        category = request.form.get('category', 'Skincare')
        price = float(request.form.get('price', 0))
        stock = int(request.form.get('stock', 10))
        desc = request.form.get('desc', '')
        
        image_file = request.files.get('image')
        video_file = request.files.get('video')
        
        image_url = "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80"
        video_url = ""
        
        if image_file and image_file.filename != '':
            img_bytes = image_file.read()
            encoded_img = base64.b64encode(img_bytes).decode('utf-8')
            mime = image_file.content_type or 'image/jpeg'
            image_url = f"data:{mime};base64,{encoded_img}"
            
        if video_file and video_file.filename != '':
            vid_bytes = video_file.read()
            encoded_vid = base64.b64encode(vid_bytes).decode('utf-8')
            mime_vid = video_file.content_type or 'video/mp4'
            video_url = f"data:{mime_vid};base64,{encoded_vid}"
            
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
            "status": "live"
        }
        PRODUCTS.append(new_prod)
        return redirect(url_for('admin_panel'))
    except Exception as e:
        return f"Error adding product: {e}", 400

@app.route('/admin/api/edit_product', methods=['POST'])
def admin_edit_product():
    try:
        prod_id = int(request.form.get('id'))
        for p in PRODUCTS:
            if p['id'] == prod_id:
                p['name'] = request.form.get('name', p['name'])
                p['price'] = float(request.form.get('price', p['price']))
                p['stock'] = int(request.form.get('stock', p['stock']))
                p['desc'] = request.form.get('desc', p['desc'])
                p['status'] = request.form.get('status', p['status'])
                
                image_file = request.files.get('image')
                if image_file and image_file.filename != '':
                    img_bytes = image_file.read()
                    encoded_img = base64.b64encode(img_bytes).decode('utf-8')
                    mime = image_file.content_type or 'image/jpeg'
                    p['image'] = f"data:{mime};base64,{encoded_img}"

                video_file = request.files.get('video')
                if video_file and video_file.filename != '':
                    vid_bytes = video_file.read()
                    encoded_vid = base64.b64encode(vid_bytes).decode('utf-8')
                    mime_vid = video_file.content_type or 'video/mp4'
                    p['video'] = f"data:{mime_vid};base64,{encoded_vid}"
        return redirect(url_for('admin_panel'))
    except Exception as e:
        return f"Error editing product: {e}", 400

@app.route('/admin/api/delete_product/<int:prod_id>', methods=['POST'])
def admin_delete_product(prod_id):
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
    return redirect(url_for('admin_panel'))

@app.route('/admin/api/update_logo', methods=['POST'])
def admin_update_logo():
    logo_file = request.files.get('logo')
    if logo_file and logo_file.filename != '':
        img_bytes = logo_file.read()
        encoded = base64.b64encode(img_bytes).decode('utf-8')
        mime = logo_file.content_type or 'image/jpeg'
        SETTINGS['logo'] = f"data:{mime};base64,{encoded}"
    return redirect(url_for('admin_panel'))

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
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Smooth Sidebar Drawer Animation */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.77, 0, 0.175, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); }
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
                <img src="{{ settings.logo }}" alt="Logo" class="logo-img">
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
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-img-container" id="img-container-{{ p.id }}">
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

            let mediaElem = document.getElementById('img-' + id);
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
            let payload = { 
                name, email, phone, pincode, city, state, landmark, street, 
                amount: amt, 
                payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Paid', 
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
                    window.location.href = '/order_success/' + data.order_id;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- ORDER SUCCESS & LIVE TRACKING TEMPLATE ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Order Tracking | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }

        @keyframes popIn { 0% { transform: scale(0.3); opacity: 0; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); } 70% { box-shadow: 0 0 0 25px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }

        .card { background: white; max-width: 600px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 45px; color: white; background: #2e7d32; border-radius: 50%; width: 85px; height: 85px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 30px; margin-bottom: 8px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        /* Flipkart / Amazon Style Straight Line Progress Bar */
        .tracker-container { margin: 30px 0; padding: 10px 0; }
        .tracker-steps { display: flex; justify-content: space-between; position: relative; margin-bottom: 10px; }
        .tracker-steps::before { content: ''; position: absolute; top: 18px; left: 10%; width: 80%; height: 4px; background: #ddd; z-index: 1; }
        
        .step { position: relative; z-index: 2; text-align: center; flex: 1; }
        .step-icon { width: 38px; height: 38px; border-radius: 50%; background: #ddd; color: #777; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px; font-size: 14px; font-weight: bold; transition: 0.3s; }
        .step.active .step-icon { background: var(--green-primary); color: white; box-shadow: 0 0 10px rgba(27,67,50,0.4); }
        .step.completed .step-icon { background: #2e7d32; color: white; }
        .step-label { font-size: 11px; font-weight: 600; color: #666; }
        .step.active .step-label { color: var(--green-primary); font-weight: 700; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; margin-top: 15px; }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Status & Tracking</h1>
        <p class="subtitle">Thank you for choosing Kesh Aadar.</p>

        {% if order %}
        <div class="tracker-container">
            {% set status = order.status_step %}
            <div class="tracker-steps">
                <div class="step {% if status == 'Order Placed' %}active{% elif status in ['Packaging', 'Shipped', 'Delivered'] %}completed{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-receipt"></i></div>
                    <div class="step-label">Order Placed</div>
                </div>
                <div class="step {% if status == 'Packaging' %}active{% elif status in ['Shipped', 'Delivered'] %}completed{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-box-open"></i></div>
                    <div class="step-label">Packaging</div>
                </div>
                <div class="step {% if status == 'Shipped' %}active{% elif status == 'Delivered' %}completed{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-truck-fast"></i></div>
                    <div class="step-label">Shipped</div>
                </div>
                <div class="step {% if status == 'Delivered' %}completed active{% endif %}">
                    <div class="step-icon"><i class="fa-solid fa-house-chimney"></i></div>
                    <div class="step-label">Delivered</div>
                </div>
            </div>
        </div>

        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Date & Time:</span><b>{{ order.date }}</b></div>
            <div class="info-row"><span>Customer:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Email:</span><b>{{ order.email }}</b></div>
            <div class="info-row"><span>Phone:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color:#2e7d32;">{{ order.payment_type }} (Paid)</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 250px; text-align: right;">{{ order.full_address }}</span></div>
            <hr style="border: 0; border-top: 1px dashed #ccc; margin: 12px 0;">
            <div class="info-row"><span>Items Ordered:</span></div>
            <ul style="font-size: 13px; padding-left: 20px; color: #444; margin-top: 5px;">
                {% for item in order.items %}
                <li>{{ item.name }} (Qty: {{ item.get('quantity', 1) }}) - ₹{{ item.price }}</li>
                {% endfor %}
            </ul>
            <div class="info-row" style="margin-top: 12px; font-size: 15px; font-weight: bold; color: var(--green-primary);">
                <span>Total Bill (incl. Taxes & Delivery):</span><span>₹{{ order.amount }}</span>
            </div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
            <p style="color:red; font-size:13px; margin-top:10px;">Order details are currently syncing or invalid.</p>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 10px;"><i class="fa-solid fa-envelope"></i> Confirmation & updates sent to your registered email.</p>
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
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background: #f4f6f8; color: #333; display: flex; min-height: 100vh; }

        /* Admin Sidebar */
        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; padding: 25px 20px; display: flex; flex-direction: column; justify-content: space-between; }
        .admin-sidebar h2 { font-size: 20px; margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; }
        .admin-sidebar .close-admin-sidebar { font-size: 20px; cursor: pointer; display: none; }
        .admin-nav { display: flex; flex-direction: column; gap: 10px; }
        .admin-nav-btn { background: none; border: none; color: white; text-align: left; padding: 12px 15px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .admin-nav-btn:hover, .admin-nav-btn.active { background: rgba(255,255,255,0.15); }

        /* Admin Content */
        .admin-main { flex: 1; padding: 30px; overflow-y: auto; }
        .section-box { background: white; padding: 25px; border-radius: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); margin-bottom: 25px; }
        h3 { color: var(--green-primary); margin-bottom: 20px; font-size: 20px; }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #faf7f0; color: var(--green-primary); font-weight: 600; }

        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: var(--green-primary); }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; outline: none; }
        .btn-submit { background: var(--green-primary); color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; }
        
        .status-select { padding: 6px 10px; border-radius: 6px; border: 1px solid #ccc; font-size: 12px; font-weight: 600; background: #fff; cursor: pointer; }
        
        @media(max-width: 768px) {
            body { flex-direction: column; }
            .admin-sidebar { width: 100%; }
            .admin-sidebar .close-admin-sidebar { display: block; }
        }
    </style>
</head>
<body>

    <div class="admin-sidebar" id="adminSidebar">
        <div>
            <h2><span>Kesh Admin</span> <i class="fa-solid fa-shield-halved" style="color:var(--accent-gold);"></i></h2>
            <div class="admin-nav">
                <button class="admin-nav-btn active" onclick="switchTab('orders')"><i class="fa-solid fa-box"></i> Customer Orders</button>
                <button class="admin-nav-btn" onclick="switchTab('products')"><i class="fa-solid fa-store"></i> Product Inventory</button>
                <button class="admin-nav-btn" onclick="switchTab('logo')"><i class="fa-solid fa-image"></i> Website Logo</button>
                <a href="/" class="admin-nav-btn" style="text-decoration:none;"><i class="fa-solid fa-arrow-left"></i> Back to Store</a>
            </div>
        </div>
        <div style="font-size:11px; opacity:0.7; text-align:center;">Secure Admin Panel v2.6</div>
    </div>

    <div class="admin-main">
        <!-- ORDERS TAB -->
        <div id="tab-orders" class="section-box">
            <h3>Customer Orders Management</h3>
            {% if orders %}
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Date</th>
                            <th>Customer & Contact</th>
                            <th>Delivery Address</th>
                            <th>Items & Total</th>
                            <th>Status Step Control</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for o in orders %}
                        <tr>
                            <td><b style="font-family:monospace; color:var(--green-primary);">{{ o.order_id }}</b><br><span style="font-size:10px; background:#e8f5e9; padding:2px 6px; border-radius:4px; color:#2e7d32;">{{ o.payment_type }}</span></td>
                            <td style="font-size:11px;">{{ o.date }}</td>
                            <td><b>{{ o.name }}</b><br>{{ o.email }}<br>{{ o.phone }}</td>
                            <td style="font-size:12px;">{{ o.full_address }}</td>
                            <td>
                                <b>₹{{ o.amount }}</b><br>
                                <span style="font-size:11px; color:#666;">Items: {{ o.items|length }}</span>
                            </td>
                            <td>
                                <select class="status-select" onchange="updateOrderStatus('{{ o.order_id }}', this.value)">
                                    <option value="Order Placed" {% if o.status_step == 'Order Placed' %}selected{% endif %}>1. Order Placed</option>
                                    <option value="Packaging" {% if o.status_step == 'Packaging' %}selected{% endif %}>2. Packaging</option>
                                    <option value="Shipped" {% if o.status_step == 'Shipped' %}selected{% endif %}>3. Shipped</option>
                                    <option value="Delivered" {% if o.status_step == 'Delivered' %}selected{% endif %}>4. Delivered</option>
                                </select>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <p style="color:#777; font-size:14px;">No customer orders received yet.</p>
            {% endif %}
        </div>

        <!-- PRODUCTS TAB -->
        <div id="tab-products" class="section-box" style="display:none;">
            <h3>Product Upload & Inventory Control</h3>
            <div style="background:#FAF7F0; padding:20px; border-radius:10px; margin-bottom:30px; border:1px dashed var(--accent-gold);">
                <h4 style="color:var(--green-primary); margin-bottom:15px; font-size:16px;">Add New Botanical Formulation</h4>
                <form action="/admin/api/add_product" method="POST" enctype="multipart/form-data">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:15px;">
                        <div class="form-group"><label>Product Name</label><input type="text" name="name" required></div>
                        <div class="form-group"><label>Category</label><input type="text" name="category" value="Skincare" required></div>
                        <div class="form-group"><label>Price (₹)</label><input type="number" step="0.01" name="price" required></div>
                        <div class="form-group"><label>Stock Quantity</label><input type="number" name="stock" required></div>
                        <div class="form-group"><label>Product Image (File Upload)</label><input type="file" name="image" accept="image/*"></div>
                        <div class="form-group"><label>Product Video (Optional File)</label><input type="file" name="video" accept="video/*"></div>
                        <div class="form-group" style="grid-column: span 2;"><label>Description</label><textarea name="desc" rows="2" required></textarea></div>
                    </div>
                    <button type="submit" class="btn-submit">Upload Product</button>
                </form>
            </div>

            <h4 style="color:var(--green-primary); margin-bottom:15px;">Existing Products (Live & Suspended)</h4>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Preview</th>
                        <th>Name & Details</th>
                        <th>Price & Stock</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in products %}
                    <tr>
                        <td>{{ p.id }}</td>
                        <td>
                            {% if p.video %}
                            <video src="{{ p.video }}" width="50" height="50" autoplay muted loop style="object-fit:cover; border-radius:6px;"></video>
                            {% else %}
                            <img src="{{ p.image }}" width="50" height="50" style="object-fit:cover; border-radius:6px;">
                            {% endif %}
                        </td>
                        <td>
                            <form action="/admin/api/edit_product" method="POST" enctype="multipart/form-data" id="edit-form-{{ p.id }}">
                                <input type="hidden" name="id" value="{{ p.id }}">
                                <input type="text" name="name" value="{{ p.name }}" style="font-weight:600; margin-bottom:4px;"><br>
                                <input type="text" name="desc" value="{{ p.desc }}" style="font-size:11px; color:#555;">
                        </td>
                        <td>
                            ₹<input type="number" step="0.01" name="price" value="{{ p.price }}" style="width:80px; display:inline-block;"> / 
                            Stock: <input type="number" name="stock" value="{{ p.stock }}" style="width:60px; display:inline-block;">
                        </td>
                        <td>
                            <select name="status" class="status-select">
                                <option value="live" {% if p.status == 'live' %}selected{% endif %}>Live</option>
                                <option value="suspended" {% if p.status == 'suspended' %}selected{% endif %}>Suspended</option>
                            </select>
                        </td>
                        <td>
                                <button type="submit" style="background:#2e7d32; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:11px; margin-bottom:4px;">Save</button>
                            </form>
                            <form action="/admin/api/delete_product/{{ p.id }}" method="POST" style="display:inline;">
                                <button type="submit" style="background:#c62828; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:11px;" onclick="return confirm('Delete this product?')">Delete</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- LOGO TAB -->
        <div id="tab-logo" class="section-box" style="display:none;">
            <h3>Website Logo Management</h3>
            <div style="background:#FAF7F0; padding:25px; border-radius:10px; border:1px dashed var(--accent-gold); max-width:500px;">
                <div style="margin-bottom:20px; text-align:center;">
                    <img src="{{ settings.logo }}" alt="Current Logo" style="width:80px; height:80px; border-radius:50%; object-fit:cover; border:3px solid var(--accent-gold);">
                    <p style="font-size:12px; color:#666; margin-top:8px;">Current Website Logo</p>
                </div>
                <form action="/admin/api/update_logo" method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Upload New Logo Image (File)</label>
                        <input type="file" name="logo" accept="image/*" required>
                    </div>
                    <button type="submit" class="btn-submit">Update Logo</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tab) {
            ['orders', 'products', 'logo'].forEach(t => {
                document.getElementById('tab-' + t).style.display = (t === tab) ? 'block' : 'none';
            });
            document.querySelectorAll('.admin-nav-btn').forEach(b => b.classList.remove('active'));
            event.currentTarget.classList.add('active');
        }

        function updateOrderStatus(orderId, status) {
            fetch('/admin/api/update_order_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId, status: status })
            }).then(r => r.json()).then(res => {
                if(res.status === 'success') {
                    alert('Order status successfully updated to: ' + status);
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
        "category": "Skincare", 
        "price": 799, 
        "stock": 30, 
        "media_type": "image",
        "media": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", 
        "desc": "Fades blemishes and restores natural skin glow."
    }
]

ORDERS = []
BLACKLISTED_IPS = []
SITE_CONFIG = {
    "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
    "brand_name": "Kesh Aadar"
}

# --- BACKGROUND EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, payment_type):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> (Qty: 1) - ₹{i['price']}</li>" for i in items])
        track_url = f"https://{request.host}/order_success/{order_id}" if request else f"http://127.0.0.1:5000/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 15px 35px rgba(27,67,50,0.1); text-align: left; border: 1px solid #e8e3d9;">
                <div style="text-align: center;">
                    <h1 style="font-size: 32px; color: #1b4332; margin-bottom: 5px; font-weight: 700; letter-spacing: 1px;">KESH AADAR</h1>
                    <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0;">Pure Botanical Remedies</p>
                </div>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <h2 style="color: #1b4332; font-size: 20px; text-align: center;">Thank you for your order, {name}!</h2>
                <p style="font-size: 13px; color: #666; line-height: 1.6; text-align: center;">Your botanical order has been placed securely and is being processed.</p>
                
                <div style="background: linear-gradient(135deg, #f8f6f0 0%, #f0ece1 100%); padding: 25px; border-radius: 14px; margin: 25px 0; border: 1px dashed #d4a373; text-align: center;">
                    <p style="margin: 0; color: #666; font-size: 11px; text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">Order Reference ID</p>
                    <h3 style="margin: 8px 0; font-size: 26px; color: #1b4332; font-family: monospace; letter-spacing: 1px;">{order_id}</h3>
                    <p style="margin: 8px 0 0 0; color: #333; font-size: 14px; font-weight: 600;">Total Bill (incl. GST): ₹{amount} ({payment_type})</p>
                    <p style="margin: 8px 0 0 0; color: #555; font-size: 12px; text-align: left; border-top: 1px solid #e2dac9; padding-top: 10px;"><b>Shipping Address:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Ordered Items:</h4>
                <ul style="font-size: 13px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 35px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 32px; border-radius: 30px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 6px 20px rgba(27, 67, 50, 0.3);">Check Live Order Status & Tracking</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 11px; color: #888; text-align: center;">Need assistance? Contact support at {SMTP_EMAIL}</p>
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
    return render_template_string(TEMPLATE, products=PRODUCTS, config=SITE_CONFIG)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    order_id = "KESH-" + str(random.randint(10000, 99999))
    data['order_id'] = order_id
    data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
    data['client_ip'] = request.remote_addr
    data['status'] = 'Order Placed' # Options: Order Placed -> Packaging -> Shipped -> Delivered
    
    full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', 'None')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
    data['full_address'] = full_address
    
    ORDERS.insert(0, data) # Newest first
    
    email_thread = threading.Thread(
        target=send_order_email, 
        args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, data['payment_type'])
    )
    email_thread.start()
    
    return jsonify({"status": "success", "order_id": order_id, "date": data['date']})

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, config=SITE_CONFIG)

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
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, config=SITE_CONFIG)

@app.route('/api/admin/update_status', methods=['POST'])
def admin_update_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status'] = new_status
            return jsonify({"success": True})
    return jsonify({"success": False, "error": "Order not found"})

@app.route('/api/admin/config', methods=['POST'])
def admin_update_config():
    data = request.get_json()
    if 'brand_name' in data:
        SITE_CONFIG['brand_name'] = data['brand_name']
    if 'logo' in data:
        SITE_CONFIG['logo'] = data['logo']
    return jsonify({"success": True, "config": SITE_CONFIG})

@app.route('/api/admin/product', methods=['POST', 'PUT', 'DELETE'])
def admin_manage_product():
    if request.method == 'POST':
        try:
            new_prod = {
                "id": len(PRODUCTS) + 1 if not PRODUCTS else max(p['id'] for p in PRODUCTS) + 1,
                "name": request.form.get('name'),
                "category": request.form.get('category', 'Skincare'),
                "price": float(request.form.get('price', 0)),
                "stock": int(request.form.get('stock', 10)),
                "desc": request.form.get('desc', ''),
                "media_type": request.form.get('media_type', 'image'),
                "media": request.form.get('media', '')
            }
            PRODUCTS.append(new_prod)
            return redirect(url_for('admin_panel'))
        except Exception as e:
            return str(e), 400

    elif request.method == 'PUT':
        data = request.get_json()
        prod_id = int(data.get('id', 0))
        for p in PRODUCTS:
            if p['id'] == prod_id:
                p['stock'] = int(data.get('stock', p['stock']))
                p['price'] = float(data.get('price', p['price']))
                p['name'] = data.get('name', p['name'])
                p['desc'] = data.get('desc', p['desc'])
                return jsonify({"success": True})
        return jsonify({"success": False, "error": "Product not found"})

    elif request.method == 'DELETE':
        data = request.get_json()
        prod_id = int(data.get('id', 0))
        global PRODUCTS
        PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
        return jsonify({"success": True})

# --- STOREFRONT TEMPLATE ---
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ config.brand_name }} | Pure Herbal Botanicals</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; --shadow: 0 20px 40px rgba(27, 67, 50, 0.15); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); overflow-x: hidden; scroll-behavior: smooth; }

        .reveal { opacity: 0; transform: translateY(30px); transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
        .reveal.active { opacity: 1; transform: translateY(0); }

        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.05); }
        .nav-left { display: flex; align-items: center; gap: 15px; }
        .menu-btn { font-size: 22px; color: var(--green-primary); cursor: pointer; background: none; border: none; transition: transform 0.3s; }
        .menu-btn:hover { transform: scale(1.1); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 24px; font-weight: 700; color: var(--green-primary); letter-spacing: 1px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: background 0.3s; }
        .cart-icon-container:hover { background: #e2dac9; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        /* Premium Smooth Drawer Sidebar */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        
        .sidebar { position: fixed; top: 0; left: -400px; width: 360px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(400px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; font-family: 'Playfair Display', serif; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 10px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: 0.3s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); transform: translateX(4px); }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; font-size: 16px; }
        .sidebar button.btn-back { background: #444; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-bottom: 20px; font-size: 13px; font-weight: 500; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); transition: transform 0.3s; }
        .close-sidebar:hover { transform: rotate(90deg); color: var(--green-primary); }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); transition: 0.3s; }
        .support-card:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.05); }

        /* Hero */
        .hero { height: 80vh; display: flex; align-items: center; justify-content: center; text-align: center; background: radial-gradient(circle, #f3efea 0%, #faf7f0 75%); margin-top: 70px; padding: 0 20px; }
        .hero-content h1 { font-family: 'Playfair Display', serif; font-size: clamp(34px, 6vw, 54px); color: var(--green-primary); margin-bottom: 15px; }
        .btn-primary { background: var(--green-primary); color: white; padding: 14px 38px; border-radius: 35px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: all 0.3s; box-shadow: 0 6px 20px rgba(27,67,50,0.2); }
        .btn-primary:hover { background: var(--green-light); transform: translateY(-2px); box-shadow: 0 8px 25px rgba(27,67,50,0.3); }

        .features-banner { background: var(--green-primary); color: white; display: flex; justify-content: space-around; padding: 20px; flex-wrap: wrap; gap: 15px; }
        .feature-item { display: flex; align-items: center; gap: 10px; font-size: 14px; font-weight: 500; }

        /* Products Grid */
        .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px; }
        .product-card { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); transition: 0.4s cubic-bezier(0.16, 1, 0.3, 1); border: 1px solid #f0ece1; }
        .product-card:hover { transform: translateY(-8px); box-shadow: var(--shadow); }
        .product-media-container { height: 240px; overflow: hidden; background: #f7f5f0; position: relative; }
        .product-media-container img, .product-media-container video { width: 100%; height: 100%; object-fit: cover; }
        .product-info { padding: 22px; }
        .price-row { display: flex; justify-content: space-between; align-items: center; margin: 15px 0; }
        .price { font-size: 22px; font-weight: 700; color: var(--green-light); }
        .btn-group { display: flex; gap: 10px; }
        .btn-cart { flex: 1; padding: 12px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 10px; cursor: pointer; font-weight: 600; transition: 0.3s; }
        .btn-cart:hover { background: #e2dac9; }
        .btn-buy { flex: 1; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; transition: 0.3s; }
        .btn-buy:hover { background: var(--green-light); }

        .fly-item { position: fixed; z-index: 9999; width: 50px; height: 50px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); transition: all 0.8s cubic-bezier(0.2, 1, 0.3, 1); pointer-events: none; }

        /* Modal */
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); display: none; justify-content: center; align-items: center; z-index: 3000; padding: 15px; }
        .modal-content { background: white; width: 100%; max-width: 540px; padding: 35px; border-radius: 24px; max-height: 90vh; overflow-y: auto; position: relative; box-shadow: 0 25px 50px rgba(0,0,0,0.2); }
        
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .full-width { grid-column: span 2; }
        .checkout-form input, .checkout-form select, .checkout-form textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 10px; outline: none; font-size: 13px; transition: border-color 0.3s; }
        .checkout-form input:focus { border-color: var(--green-primary); }

        .bill-summary { background: #FAF7F0; border: 1px solid #EAE5D9; border-radius: 14px; padding: 18px; margin: 18px 0; font-size: 13px; }
        .bill-row { display: flex; justify-content: space-between; margin-bottom: 8px; color: #555; }
        .bill-row.total { border-top: 1px dashed #ccc; padding-top: 10px; font-weight: bold; font-size: 16px; color: var(--green-primary); }

        .saved-addr-btn { background: #e8f5e9; color: #2e7d32; border: 1px dashed #2e7d32; padding: 10px 14px; border-radius: 10px; cursor: pointer; font-size: 12px; font-weight: 600; width: 100%; margin-bottom: 15px; display: flex; align-items: center; justify-content: center; gap: 8px; }

        /* Footer */
        .main-footer { background-color: var(--green-primary); color: white; padding: 50px 30px 20px; margin-top: 60px; }
        .footer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 30px; max-width: 1200px; margin: 0 auto; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 30px; }
        .footer-grid h3 { color: var(--accent-gold); font-family: 'Playfair Display', serif; font-size: 20px; margin-bottom: 15px; }
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
                <img src="{{ config.logo }}" alt="Logo" class="logo-img" id="nav-logo-img">
                <div class="logo"><span>Kesh</span> Aadar</div>
            </div>
        </div>
        <div class="cart-icon-container" id="cartTarget" onclick="openCartModal()">
            <i class="fa-solid fa-shopping-basket"></i><span class="cart-badge" id="cart-count">0</span>
        </div>
    </header>

    <!-- Sidebar Drawer (Public features only) -->
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <span class="close-sidebar" onclick="toggleSidebar()">&times;</span>
        
        <div id="sidebar-main-view">
            <h3 style="margin-top: 10px; font-size: 22px;">Menu & Support</h3>
            <p style="font-size: 13px; color: #666; margin-bottom: 25px;">Explore tracking and assistance.</p>
            <button class="menu-item" onclick="switchSidebarView('track')"><i class="fa-solid fa-map-location-dot"></i> Track Order Status</button>
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
            <a href="mailto:keshaadar@gmail.com" class="support-card"><i class="fa-solid fa-envelope" style="color: var(--accent-gold); font-size: 20px;"></i><div><h4 style="font-size: 13px; color: var(--green-primary);">Email Support</h4><p style="font-size: 11px; color: #555;">keshaadar@gmail.com</p></div></a>
            <a href="tel:9163641507" class="support-card"><i class="fa-solid fa-phone-volume" style="color: var(--green-primary); font-size: 20px;"></i><div><h4 style="font-size: 13px; color: var(--green-primary);">Call Support</h4><p style="font-size: 11px; color: #555;">+91 9163641507</p></div></a>
            <a href="https://wa.me/919163641507" target="_blank" class="support-card" style="background: #e8f5e9;"><i class="fa-brands fa-whatsapp" style="color: #2e7d32; font-size: 20px;"></i><div><h4 style="font-size: 13px; color: #2e7d32;">WhatsApp Support</h4><p style="font-size: 11px; color: #555;">Instant messaging</p></div></a>
        </div>

        <div id="sidebar-faq-view" style="display:none;">
            <button class="btn-back" onclick="switchSidebarView('main')"><i class="fa-solid fa-arrow-left"></i> Back</button>
            <h3>Frequently Asked Questions</h3>
            <h4 style="font-size: 13px; color: var(--green-primary);">1. Dispatch Time?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Orders dispatch within 24-48 hours with live email tracking.</p>
            <h4 style="font-size: 13px; color: var(--green-primary);">2. Organic Purity?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">100% natural formulations without harsh sulfates.</p>
        </div>
    </div>

    <!-- Hero -->
    <section class="hero reveal">
        <div class="hero-content">
            <h1>Pure Botanical Wellness</h1>
            <p style="margin-bottom:25px; font-size:16px; color:#555;">Formulated with authentic organic extracts for natural skin and hair care.</p>
            <a href="#shop" class="btn-primary">Shop Formulations</a>
        </div>
    </section>

    <!-- Features -->
    <div class="features-banner">
        <div class="feature-item"><i class="fa-solid fa-leaf" style="color:var(--accent-gold);"></i> 100% Organic Extracts</div>
        <div class="feature-item"><i class="fa-solid fa-truck-fast" style="color:var(--accent-gold);"></i> Express Live Tracking</div>
        <div class="feature-item"><i class="fa-solid fa-shield-cat" style="color:var(--accent-gold);"></i> Cruelty-Free Certified</div>
    </div>

    <!-- Shop -->
    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 30px; color: var(--green-primary); margin-bottom: 35px;" class="reveal">Our Formulations</h2>
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}">
                <div class="product-media-container" id="media-container-{{ p.id }}">
                    {% if p.media_type == 'video' %}
                    <video src="{{ p.media }}" autoplay muted loop playsinline id="media-{{ p.id }}"></video>
                    {% else %}
                    <img src="{{ p.media }}" alt="{{ p.name }}" id="media-{{ p.id }}">
                    {% endif %}
                </div>
                <div class="product-info">
                    <h3 style="color:var(--green-primary); font-size:16px; margin-bottom:6px;">{{ p.name }}</h3>
                    <p style="font-size:12px; color:#666; line-height: 1.5; margin-bottom: 10px;">{{ p.desc }}</p>
                    <div class="price-row">
                        <span class="price">₹{{ p.price }}</span>
                        <span style="font-size:11px; padding:4px 10px; border-radius:6px; background:#e8f5e9; color:#2e7d32; font-weight:600;">Stock: {{ p.stock }}</span>
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
                <p style="font-size: 13px; line-height: 1.7;">Bringing ancient botanical secrets directly into your daily routine. Pure, natural, and potent.</p>
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
                        <input type="email" id="cust-email" class="full-width" placeholder="Email Address (For Instant Live Tracking) *" required>
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
                        <label style="display:flex; align-items:center; gap:10px; padding:12px; border:1px solid #ddd; border-radius:10px; cursor:pointer;" onclick="updateTotal()">
                            <input type="radio" name="pay_mode" value="online" checked> Online Payment (Instant Razorpay Secure)
                        </label>
                        <label style="display:flex; align-items:center; gap:10px; padding:12px; border:1px solid #ddd; border-radius:10px; cursor:pointer;" onclick="updateTotal()">
                            <input type="radio" name="pay_mode" value="cod"> Cash on Delivery (+₹99 handling fee)
                        </label>
                    </div>

                    <div class="bill-summary">
                        <div class="bill-row"><span>Items Subtotal:</span><span id="bill-subtotal">₹0</span></div>
                        <div class="bill-row" id="cod-fee-row" style="display:none; color:#c62828;"><span>COD Handling Fee:</span><span>₹99</span></div>
                        <div class="bill-row"><span>Estimated Shipping:</span><span style="color:#2e7d32; font-weight:600;">FREE</span></div>
                        <div class="bill-row total"><span>Total Payable (incl. GST):</span><span id="bill-total">₹0</span></div>
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

            let mediaEl = document.getElementById('media-' + id);
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
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid #eee; padding-bottom:10px; font-size:13px;">
                        <div><b>${item.name}</b></div>
                        <div style="display:flex; align-items:center; gap:12px;">
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
                document.getElementById('payBtn').innerText = `Pay ₹${total} Now via Razorpay`;
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
                amount: amt, payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Payment (Razorpay)', items: cart 
            };

            saveAddressToStorage(payload);

            if(mode === 'online') {
                var options = {
                    "key": "rzp_live_TGzOHwqjwcYfov", 
                    "amount": amt * 100, 
                    "currency": "INR", 
                    "name": "{{ config.brand_name }}",
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
                    d.innerHTML = `<div style="background:#e8f5e9; padding:14px; border-radius:10px; font-size:13px;"><h4 style="color:#2e7d32;">Found: ${data.order.order_id}</h4><p>Current Status: <b>${data.order.status}</b></p><a href="/order_success/${data.order.order_id}" style="color:#1b4332; font-weight:bold; display:inline-block; margin-top:8px;">View Detailed Tracker &rarr;</a></div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- DEDICATED ORDER SUCCESS & LIVE STATUS TRACKER TEMPLATE ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmed & Live Tracking | {{ config.brand_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 25px; }

        @keyframes popIn { 0% { transform: scale(0.3); opacity: 0; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); } 70% { box-shadow: 0 0 0 25px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }

        .card { background: white; max-width: 620px; width: 100%; padding: 45px 35px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.08); text-align: center; }
        .icon-box { font-size: 45px; color: white; background: #2e7d32; border-radius: 50%; width: 85px; height: 85px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 30px; margin-bottom: 6px; }
        p.subtitle { color: #666; font-size: 13px; margin-bottom: 25px; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 14px; margin-bottom: 25px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        /* Stepper Tracker */
        .tracker-container { margin: 30px 0 20px 0; text-align: left; }
        .tracker-title { font-size: 14px; font-weight: 600; color: var(--green-primary); margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
        .steps { display: flex; justify-content: space-between; position: relative; margin: 0 15px; }
        .steps::before { content: ''; position: absolute; top: 15px; left: 0; width: 100%; height: 4px; background: #e0dcd0; z-index: 1; }
        .step { position: relative; z-index: 2; text-align: center; width: 25%; }
        .step-circle { width: 34px; height: 34px; border-radius: 50%; background: #e0dcd0; color: #888; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 13px; font-weight: 600; transition: 0.4s; }
        .step.active .step-circle { background: #2e7d32; color: white; box-shadow: 0 0 15px rgba(46,125,50,0.4); }
        .step.completed .step-circle { background: #1b4332; color: white; }
        .step-label { font-size: 11px; color: #666; font-weight: 500; }
        .step.active .step-label { color: #2e7d32; font-weight: 700; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; transition: 0.3s; box-shadow: 0 6px 20px rgba(27,67,50,0.2); }
        .btn-home:hover { background: var(--green-light); }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Confirmed!</h1>
        <p class="subtitle">Thank you for choosing {{ config.brand_name }}. Your live status tracker is active below.</p>

        {% if order %}
        <div class="tracker-container">
            <div class="tracker-title">Live Delivery Status: <span style="color:#2e7d32;">{{ order.status }}</span></div>
            <div class="steps">
                {% set status_list = ['Order Placed', 'Packaging', 'Shipped', 'Delivered'] %}
                {% set current_idx = status_list.index(order.status) if order.status in status_list else 0 %}
                
                <div class="step {% if current_idx >= 0 %}completed{% endif %} {% if current_idx == 0 %}active{% endif %}">
                    <div class="step-circle"><i class="fa-solid fa-clipboard-check"></i></div>
                    <div class="step-label">Placed</div>
                </div>
                <div class="step {% if current_idx > 1 %}completed{% endif %} {% if current_idx == 1 %}active{% endif %}">
                    <div class="step-circle"><i class="fa-solid fa-box"></i></div>
                    <div class="step-label">Packaging</div>
                </div>
                <div class="step {% if current_idx > 2 %}completed{% endif %} {% if current_idx == 2 %}active{% endif %}">
                    <div class="step-circle"><i class="fa-solid fa-truck-fast"></i></div>
                    <div class="step-label">Shipped</div>
                </div>
                <div class="step {% if current_idx == 3 %}completed active{% endif %}">
                    <div class="step-circle"><i class="fa-solid fa-house-chimney"></i></div>
                    <div class="step-label">Delivered</div>
                </div>
            </div>
        </div>

        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Customer Phone:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Customer Email:</span><b>{{ order.email }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color:#2e7d32;">Paid & Verified ({{ order.payment_type }})</b></div>
            <div class="info-row"><span>Total Bill (incl. GST):</span><b style="color:var(--green-primary);">₹{{ order.amount }}</b></div>
            <div class="info-row" style="margin-top:8px; border-top:1px dashed #e2dac9; padding-top:8px;"><span>Shipping Address:</span><span style="max-width: 250px; text-align: right; font-size:12px;">{{ order.full_address }}</span></div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
            <p style="font-size: 12px; color: #888; margin-top: 10px;">Order details retrieved via live record.</p>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 20px;"><i class="fa-solid fa-envelope"></i> Detailed tracking invoice has been emailed to your registered address.</p>
        
        <a href="/" class="btn-home">Continue Shopping</a>
    </div>

</body>
</html>
"""

# --- ADMIN PANEL TEMPLATE (Secure Admin Dashboard) ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard | {{ config.brand_name }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); display: flex; min-height: 100vh; }

        /* Admin Sidebar */
        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; padding: 25px 20px; display: flex; flex-direction: column; justify-content: space-between; position: fixed; height: 100vh; left: 0; top: 0; z-index: 100; transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
        .admin-sidebar h2 { font-family: 'Playfair Display', serif; font-size: 20px; color: var(--accent-gold); margin-bottom: 30px; display: flex; align-items: center; justify-content: space-between; }
        .admin-sidebar .close-admin-menu { display: none; cursor: pointer; font-size: 22px; color: white; }
        .admin-menu-links { display: flex; flex-direction: column; gap: 10px; flex: 1; }
        .admin-menu-links button { background: transparent; border: none; color: white; text-align: left; padding: 12px 15px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 12px; transition: 0.3s; }
        .admin-menu-links button:hover, .admin-menu-links button.active { background: rgba(255,255,255,0.1); color: var(--accent-gold); }
        .admin-menu-links button i { width: 20px; }

        /* Main Admin Content Area */
        .admin-main { flex: 1; margin-left: 260px; padding: 30px; transition: margin-left 0.4s; }
        .admin-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 35px; border-bottom: 1px solid #ddd; padding-bottom: 15px; }
        .mobile-admin-toggle { display: none; font-size: 22px; background: none; border: none; color: var(--green-primary); cursor: pointer; }

        .panel-section { display: none; }
        .panel-section.active { display: block; }

        /* Tables & Cards */
        .card-box { background: white; border-radius: 16px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.04); margin-bottom: 25px; border: 1px solid #eee; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 14px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }
        
        .form-control { width: 100%; padding: 12px; margin: 8px 0 15px 0; border: 1px solid #ccc; border-radius: 8px; outline: none; font-size: 13px; }
        .btn-admin { background: var(--green-primary); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; transition: 0.3s; }
        .btn-admin:hover { background: var(--green-light); }
        .btn-danger { background: #c62828; color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 11px; }

        select.status-select { padding: 8px 12px; border-radius: 6px; border: 1px solid #ddd; font-weight: 500; font-size: 12px; outline: none; background: #fff; cursor: pointer; }

        @media(max-width: 900px) {
            .admin-sidebar { transform: translateX(-260px); }
            .admin-sidebar.active { transform: translateX(0); }
            .admin-main { margin-left: 0; padding: 20px; }
            .mobile-admin-toggle { display: block; }
            .admin-sidebar .close-admin-menu { display: block; }
        }
    </style>
</head>
<body>

    <!-- Admin Sidebar with close option -->
    <div class="admin-sidebar" id="adminSidebar">
        <div>
            <h2>
                <span>Admin Panel</span>
                <i class="fa-solid fa-xmark close-admin-menu" onclick="toggleAdminSidebar()"></i>
            </h2>
            <div class="admin-menu-links">
                <button class="active" onclick="switchAdminTab('orders', this)"><i class="fa-solid fa-box-open"></i> Customer Orders</button>
                <button onclick="switchAdminTab('inventory', this)"><i class="fa-solid fa-boxes-stacked"></i> Inventory & Products</button>
                <button onclick="switchAdminTab('settings', this)"><i class="fa-solid fa-gear"></i> Branding & Logo</button>
                <button onclick="window.location.href='/'"><i class="fa-solid fa-store"></i> View Storefront</button>
            </div>
        </div>
        <div style="font-size: 11px; color: rgba(255,255,255,0.6); text-align: center;">
            {{ config.brand_name }} Secure Admin
        </div>
    </div>

    <!-- Admin Main Content -->
    <div class="admin-main">
        <div class="admin-header">
            <div style="display: flex; align-items: center; gap: 15px;">
                <button class="mobile-admin-toggle" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
                <h1 style="font-family: 'Playfair Display'; font-size: 24px; color: var(--green-primary);">Dashboard Management</h1>
            </div>
            <div style="font-size: 13px; font-weight: 500; color: #555;"><i class="fa-solid fa-circle-user" style="color: var(--accent-gold);"></i> Admin Root</div>
        </div>

        <!-- 1. ORDERS SECTION -->
        <div class="panel-section active" id="section-orders">
            <div class="card-box">
                <h3 style="color: var(--green-primary); margin-bottom: 10px; font-family:'Playfair Display';">Customer Orders Management</h3>
                <p style="font-size: 12px; color: #666; margin-bottom: 20px;">Manage order fulfillment steps. Updating status instantly syncs customer email notifications and live tracking page.</p>
                
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Order ID & Date</th>
                                <th>Customer Details</th>
                                <th>Delivery Address</th>
                                <th>Items & Amount</th>
                                <th>Fulfillment Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for o in orders %}
                            <tr>
                                <td>
                                    <b style="font-family:monospace; color:var(--green-primary);">{{ o.order_id }}</b><br>
                                    <span style="font-size:11px; color:#777;">{{ o.date }}</span><br>
                                    <span style="font-size:11px; background:#e8f5e9; color:#2e7d32; padding:2px 6px; border-radius:4px; font-weight:600;">{{ o.payment_type }}</span>
                                </td>
                                <td>
                                    <b>{{ o.name }}</b><br>
                                    <i class="fa-solid fa-phone" style="font-size:10px;"></i> {{ o.phone }}<br>
                                    <i class="fa-solid fa-envelope" style="font-size:10px;"></i> {{ o.email }}
                                </td>
                                <td style="max-width:220px; font-size:12px;">
                                    {{ o.full_address }}
                                </td>
                                <td>
                                    <b style="color:var(--green-light);">₹{{ o.amount }}</b><br>
                                    <span style="font-size:11px; color:#666;">Items: {{ o.items | length }}</span>
                                </td>
                                <td>
                                    <select class="status-select" onchange="updateOrderStatus('{{ o.order_id }}', this.value)">
                                        <option value="Order Placed" {% if o.status == 'Order Placed' %}selected{% endif %}>1. Order Placed</option>
                                        <option value="Packaging" {% if o.status == 'Packaging' %}selected{% endif %}>2. Packaging</option>
                                        <option value="Shipped" {% if o.status == 'Shipped' %}selected{% endif %}>3. Shipped</option>
                                        <option value="Delivered" {% if o.status == 'Delivered' %}selected{% endif %}>4. Delivered</option>
                                    </select>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="5" style="text-align: center; color: #888; padding: 30px;">No customer orders placed yet.</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 2. INVENTORY & PRODUCT UPLOAD SECTION -->
        <div class="panel-section" id="section-inventory">
            <div class="card-box">
                <h3 style="color: var(--green-primary); margin-bottom: 10px; font-family:'Playfair Display';">Upload New Product</h3>
                <form action="/api/admin/product" method="POST" style="margin-top: 15px;">
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <label style="font-size:12px; font-weight:600;">Product Name *</label>
                            <input type="text" name="name" class="form-control" required placeholder="e.g. Herbal Hair Tonic">
                        </div>
                        <div>
                            <label style="font-size:12px; font-weight:600;">Category *</label>
                            <input type="text" name="category" class="form-control" required placeholder="e.g. Haircare">
                        </div>
                        <div>
                            <label style="font-size:12px; font-weight:600;">Price (₹) *</label>
                            <input type="number" name="price" class="form-control" required placeholder="499">
                        </div>
                        <div>
                            <label style="font-size:12px; font-weight:600;">Stock Quantity *</label>
                            <input type="number" name="stock" class="form-control" required placeholder="40">
                        </div>
                        <div>
                            <label style="font-size:12px; font-weight:600;">Media Type *</label>
                            <select name="media_type" class="form-control" required>
                                <option value="image">Image URL</option>
                                <option value="video">Video MP4 URL</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:12px; font-weight:600;">Media File/Image Link *</label>
                            <input type="url" name="media" class="form-control" required placeholder="https://images.unsplash.com/...">
                        </div>
                        <div style="grid-column: span 2;">
                            <label style="font-size:12px; font-weight:600;">Product Description</label>
                            <textarea name="desc" class="form-control" rows="2" placeholder="Describe botanical ingredients..."></textarea>
                        </div>
                    </div>
                    <button type="submit" class="btn-admin" style="margin-top: 10px;"><i class="fa-solid fa-cloud-arrow-up"></i> Upload Product Live</button>
                </form>
            </div>

            <div class="card-box">
                <h3 style="color: var(--green-primary); margin-bottom: 15px; font-family:'Playfair Display';">Manage Existing Inventory & Stock</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Product Name</th>
                            <th>Category</th>
                            <th>Price (₹)</th>
                            <th>Stock</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr id="prod-row-{{ p.id }}">
                            <td><b>{{ p.name }}</b></td>
                            <td>{{ p.category }}</td>
                            <td><input type="number" id="price-{{ p.id }}" value="{{ p.price }}" style="width:80px; padding:6px; border:1px solid #ccc; border-radius:4px;"></td>
                            <td><input type="number" id="stock-{{ p.id }}" value="{{ p.stock }}" style="width:70px; padding:6px; border:1px solid #ccc; border-radius:4px;"></td>
                            <td>
                                <button class="btn-admin" style="padding:6px 12px; font-size:11px;" onclick="saveProduct({{ p.id }})">Update</button>
                                <button class="btn-danger" onclick="deleteProduct({{ p.id }})">Delete / Suspend</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 3. BRANDING & LOGO SECTION -->
        <div class="panel-section" id="section-settings">
            <div class="card-box" style="max-width: 600px;">
                <h3 style="color: var(--green-primary); margin-bottom: 10px; font-family:'Playfair Display';">Website Branding & Logo</h3>
                <p style="font-size: 12px; color: #666; margin-bottom: 20px;">Update your brand name and logo image displayed across the website and header.</p>
                
                <label style="font-size:12px; font-weight:600;">Brand Name</label>
                <input type="text" id="config-brand" class="form-control" value="{{ config.brand_name }}">

                <label style="font-size:12px; font-weight:600;">Logo Image Link (URL)</label>
                <input type="url" id="config-logo" class="form-control" value="{{ config.logo }}">

                <button type="button" class="btn-admin" onclick="saveConfig()"><i class="fa-solid fa-floppy-disk"></i> Save Branding Settings</button>
            </div>
        </div>
    </div>

    <script>
        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('active');
        }

        function switchAdminTab(tabId, btn) {
            document.querySelectorAll('.panel-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.admin-menu-links button').forEach(b => b.classList.remove('active'));
            document.getElementById('section-' + tabId).classList.add('active');
            btn.classList.add('active');
            if(window.innerWidth <= 900) { toggleAdminSidebar(); }
        }

        function updateOrderStatus(orderId, newStatus) {
            fetch('/api/admin/update_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId, status: newStatus })
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) {
                    alert("Order status successfully updated to " + newStatus);
                } else {
                    alert("Failed to update status.");
                }
            });
        }

        function saveProduct(id) {
            let price = document.getElementById('price-' + id).value;
            let stock = document.getElementById('stock-' + id).value;
            fetch('/api/admin/product', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, price: price, stock: stock })
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) { alert("Product updated successfully."); location.reload(); }
            });
        }

        function deleteProduct(id) {
            if(confirm("Are you sure you want to delete and suspend this product from the storefront?")) {
                fetch('/api/admin/product', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                })
                .then(res => res.json())
                .then(data => {
                    if(data.success) { document.getElementById('prod-row-' + id).remove(); }
                });
            }
        }

        function saveConfig() {
            let brand_name = document.getElementById('config-brand').value;
            let logo = document.getElementById('config-logo').value;
            fetch('/api/admin/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ brand_name: brand_name, logo: logo })
            })
            .then(res => res.json())
            .then(data => {
                if(data.success) { alert("Branding updated successfully!"); location.reload(); }
            });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Kesh Aadar Flask Server Running...")
    app.run(host='0.0.0.0', port=5000, debug=True)
