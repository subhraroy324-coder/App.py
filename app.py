from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import smtplib
import os
import base64
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

# --- PERSISTENT DATASTORE (Vercel-Compatible In-Memory / File Hybrid) ---
DB_FILE = "/tmp/database.json" if os.path.exists("/tmp") else "database.json"

DEFAULT_PRODUCTS = [
    {
        "id": 1,
        "name": "Aloe Neem Glow Face Wash",
        "category": "Skincare",
        "price": 349,
        "stock": 50,
        "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80",
        "media_type": "image",
        "desc": "Deep cleansing herbal formula for radiant skin."
    },
    {
        "id": 2,
        "name": "Saffron Kumkumadi Night Serum",
        "category": "Skincare",
        "price": 799,
        "stock": 30,
        "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80",
        "media_type": "image",
        "desc": "Fades blemishes and restores natural skin glow."
    }
]

def load_db():
    if not os.path.exists(DB_FILE):
        data = {
            "products": DEFAULT_PRODUCTS,
            "orders": [],
            "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80"
        }
        save_db(data)
        return data
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"products": DEFAULT_PRODUCTS, "orders": [], "logo": ""}

def save_db(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Database write error: {e}")

# --- RELIABLE SYNCHRONOUS EMAIL SENDER ---
def send_order_email(recipient_email, name, order_id, amount, items, full_address, payment_type):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed! Ref #{order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li style='padding:5px 0;'><b>{i['name']}</b> - ₹{i['price']}</li>" for i in items])
        host_url = request.host_url.rstrip('/')
        track_url = f"{host_url}/tracking/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #FAF7F0; padding: 30px 10px; margin: 0;">
            <div style="background: #ffffff; max-width: 600px; margin: 0 auto; padding: 40px; border-radius: 20px; border: 1px solid #e2dcd0; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="font-size: 32px; color: #1b4332; margin: 0; font-weight: 800; letter-spacing: 2px;">KESH AADAR</h1>
                    <p style="color: #d4a373; text-transform: uppercase; font-size: 11px; letter-spacing: 3px; font-weight: bold; margin-top: 5px;">Pure Botanical Remedies</p>
                </div>
                
                <div style="background: #1b4332; color: #ffffff; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 30px;">
                    <h2 style="margin: 0; font-size: 20px;">Thank You for Your Order, {name}!</h2>
                    <p style="margin: 5px 0 0 0; font-size: 13px; color: #d4a373;">We are preparing your botanical order for dispatch.</p>
                </div>

                <div style="background: #FAF7F0; border: 1px dashed #d4a373; padding: 20px; border-radius: 12px; margin-bottom: 25px;">
                    <div style="font-size: 12px; color: #666; text-transform: uppercase; font-weight: bold;">Order Reference ID</div>
                    <div style="font-size: 24px; color: #1b4332; font-family: monospace; font-weight: bold; margin: 5px 0 15px 0;">{order_id}</div>
                    
                    <div style="font-size: 13px; color: #333; margin-bottom: 5px;"><b>Total Paid/Payable:</b> ₹{amount} ({payment_type})</div>
                    <div style="font-size: 13px; color: #333;"><b>Shipping Address:</b> {full_address}</div>
                </div>

                <h3 style="color: #1b4332; font-size: 16px; margin-bottom: 10px; border-bottom: 2px solid #FAF7F0; padding-bottom: 5px;">Ordered Items</h3>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; margin-bottom: 30px;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin: 35px 0;">
                    <a href="{track_url}" style="background-color: #1b4332; color: #ffffff; text-decoration: none; padding: 15px 35px; border-radius: 30px; font-weight: bold; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(27, 67, 50, 0.2);">CLICK HERE TO TRACK ORDER STATUS</a>
                </div>

                <div style="border-top: 1px solid #eee; padding-top: 20px; font-size: 11px; color: #888; text-align: center;">
                    If you have questions, reply directly to this email or reach us at keshaadar@gmail.com
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASS)
        server.sendmail(SMTP_EMAIL, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False

# --- ROUTES ---

@app.route('/')
def index():
    db = load_db()
    return render_template_string(CLIENT_TEMPLATE, products=db["products"], logo=db.get("logo", ""))

@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        data = request.get_json()
        db = load_db()
        order_id = "KESH-" + str(random.randint(100000, 999999))
        
        data['order_id'] = order_id
        data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
        data['status'] = 'Placed'
        
        full_address = f"{data.get('street', '')}, {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
        data['full_address'] = full_address
        
        db['orders'].append(data)
        save_db(db)
        
        # Dispatch email directly in-request for maximum reliability
        send_order_email(
            recipient_email=data['email'],
            name=data['name'],
            order_id=order_id,
            amount=data['amount'],
            items=data['items'],
            full_address=full_address,
            payment_type=data['payment_type']
        )
        
        return jsonify({"status": "success", "order_id": order_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/tracking/<order_id>')
def track_order_page(order_id):
    db = load_db()
    order = next((o for o in db['orders'] if o['order_id'] == order_id), None)
    return render_template_string(TRACKING_TEMPLATE, order=order, order_id=order_id)

@app.route('/admin')
def admin_page():
    return render_template_string(ADMIN_TEMPLATE)

# --- ADMIN API ENDPOINTS ---

@app.route('/api/admin/data', methods=['GET'])
def get_admin_data():
    db = load_db()
    return jsonify({"orders": db["orders"], "products": db["products"], "logo": db.get("logo", "")})

@app.route('/api/admin/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    db = load_db()
    for o in db['orders']:
        if o['order_id'] == data['order_id']:
            o['status'] = data['status']
            break
    save_db(db)
    return jsonify({"status": "success"})

@app.route('/api/admin/product', methods=['POST', 'DELETE'])
def manage_products():
    db = load_db()
    if request.method == 'POST':
        data = request.get_json()
        if 'id' in data and data['id']:
            # Update existing
            for p in db['products']:
                if str(p['id']) == str(data['id']):
                    p['name'] = data['name']
                    p['price'] = float(data['price'])
                    p['stock'] = int(data['stock'])
                    p['desc'] = data['desc']
                    if data.get('image'):
                        p['image'] = data['image']
                        p['media_type'] = data.get('media_type', 'image')
        else:
            # Create new
            new_id = max([p['id'] for p in db['products']], default=0) + 1
            new_prod = {
                "id": new_id,
                "name": data['name'],
                "price": float(data['price']),
                "stock": int(data['stock']),
                "desc": data['desc'],
                "image": data.get('image', ''),
                "media_type": data.get('media_type', 'image')
            }
            db['products'].append(new_prod)
        save_db(db)
        return jsonify({"status": "success"})

    elif request.method == 'DELETE':
        prod_id = request.args.get('id')
        db['products'] = [p for p in db['products'] if str(p['id']) != str(prod_id)]
        save_db(db)
        return jsonify({"status": "success"})

@app.route('/api/admin/update_logo', methods=['POST'])
def update_logo():
    data = request.get_json()
    db = load_db()
    db['logo'] = data.get('logo', '')
    save_db(db)
    return jsonify({"status": "success"})

# --- FRONTEND TEMPLATES ---

CLIENT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KESH AADAR | Pure Herbal Botanicals</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); overflow-x: hidden; scroll-behavior: smooth; }

        /* Smooth Scroll Reveal */
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

        /* Enhanced Sidebar & Overlay */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); backdrop-filter: blur(4px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: 0; width: 320px; height: 100%; background: white; box-shadow: 10px 0 30px rgba(0,0,0,0.1); z-index: 2000; transform: translateX(-100%); transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(0); }
        .close-sidebar { font-size: 24px; cursor: pointer; float: right; color: var(--text-dark); }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 10px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); }

        /* Hero & Products Grid */
        .hero { height: 70vh; display: flex; align-items: center; justify-content: center; text-align: center; background: radial-gradient(circle, #f3efea 0%, #faf7f0 75%); margin-top: 70px; padding: 0 20px; }
        .hero-content h1 { font-family: 'Playfair Display', serif; font-size: clamp(34px, 6vw, 54px); color: var(--green-primary); margin-bottom: 15px; }
        .btn-primary { background: var(--green-primary); color: white; padding: 14px 38px; border-radius: 35px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: 0.3s; }
        .btn-primary:hover { background: var(--green-light); transform: translateY(-2px); }

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

        /* Modal */
        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); backdrop-filter: blur(5px); display: none; justify-content: center; align-items: center; z-index: 3000; padding: 15px; }
        .modal-content { background: white; width: 100%; max-width: 520px; padding: 30px; border-radius: 20px; max-height: 90vh; overflow-y: auto; position: relative; }
        .checkout-form input, .checkout-form select, .checkout-form textarea { width: 100%; padding: 11px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
    </style>
</head>
<body>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
                {% if logo %}
                <img src="{{ logo }}" alt="Logo" class="logo-img">
                {% endif %}
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
        <h3 style="margin: 20px 0 15px 0; font-size: 20px; color: var(--green-primary);">Navigation</h3>
        <button class="menu-item" onclick="toggleSidebar(); window.location.href='#shop'"><i class="fa-solid fa-leaf" style="color:var(--accent-gold);"></i> Shop Products</button>
        <button class="menu-item" onclick="toggleSidebar(); openCartModal()"><i class="fa-solid fa-basket-shopping" style="color:var(--accent-gold);"></i> View Cart</button>
    </div>

    <!-- Hero -->
    <section class="hero reveal">
        <div class="hero-content">
            <h1>Pure Botanical Wellness</h1>
            <p style="margin-bottom:25px; font-size:16px; color:#555;">Formulated with organic extracts for natural skin and hair care.</p>
            <a href="#shop" class="btn-primary">Shop Formulations</a>
        </div>
    </section>

    <!-- Shop -->
    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 28px; color: var(--green-primary); margin-bottom: 30px;" class="reveal">Our Formulations</h2>
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card reveal">
                <div class="product-img-container">
                    {% if p.media_type == 'video' %}
                    <video src="{{ p.image }}" controls autoplay muted loop></video>
                    {% else %}
                    <img src="{{ p.image }}" alt="{{ p.name }}">
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
                        <button class="btn-cart" onclick="addToCart({{ p.id }})">Add to Cart</button>
                        <button class="btn-buy" onclick="buyNow({{ p.id }})">Buy Now</button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Cart Modal -->
    <div class="modal" id="cartModal">
        <div class="modal-content">
            <span class="close-sidebar" onclick="document.getElementById('cartModal').style.display='none'" style="position:absolute; right:20px; top:20px;">&times;</span>
            <h3 style="color:var(--green-primary); margin-bottom:15px;">Your Shopping Basket</h3>
            <div id="cart-items-container"></div>
            
            <div id="checkout-section" style="display:none; margin-top:20px;">
                <h4 style="margin-bottom:12px; font-size:15px; color:var(--green-primary);">Shipping Details</h4>
                <form class="checkout-form" id="checkoutForm" onsubmit="event.preventDefault(); placeOrder();">
                    <input type="text" id="cust-name" placeholder="Full Name *" required>
                    <input type="email" id="cust-email" placeholder="Email Address *" required>
                    <input type="tel" id="cust-phone" placeholder="Phone Number *" required>
                    <input type="text" id="cust-pincode" placeholder="PIN Code *" required>
                    <input type="text" id="cust-city" placeholder="City *" required>
                    <input type="text" id="cust-state" placeholder="State *" required>
                    <input type="text" id="cust-landmark" placeholder="Landmark (Optional)">
                    <textarea id="cust-street" placeholder="Street Address *" rows="2" required></textarea>

                    <h4 style="margin: 15px 0 8px 0; font-size:14px; color:var(--green-primary);">Payment Option</h4>
                    <select id="pay_mode">
                        <option value="Online Payment">Online Payment</option>
                        <option value="Cash on Delivery">Cash on Delivery</option>
                    </select>

                    <button type="submit" class="btn-primary" style="width:100%; border-radius:10px; margin-top:15px;" id="payBtn">Place Order</button>
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

        function addToCart(id) {
            let p = productsData.find(x => x.id === id);
            cart.push(p);
            updateCartUI();
            alert('Item added to cart!');
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
                let total = 0;
                cart.forEach((item, index) => {
                    total += item.price;
                    container.innerHTML += `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid #eee; padding-bottom:8px; font-size:13px;">
                        <div><b>${item.name}</b></div>
                        <div>₹${item.price}</div>
                    </div>`;
                });
                container.innerHTML += `<div style="text-align:right; font-weight:bold; font-size:16px; margin-top:10px; color:var(--green-primary);">Total: ₹${total}</div>`;
                document.getElementById('checkout-section').style.display = 'block';
            }
        }

        function placeOrder() {
            let btn = document.getElementById('payBtn');
            btn.innerText = 'Processing Order...';
            btn.disabled = true;

            let name = document.getElementById('cust-name').value;
            let email = document.getElementById('cust-email').value;
            let phone = document.getElementById('cust-phone').value;
            let pincode = document.getElementById('cust-pincode').value;
            let city = document.getElementById('cust-city').value;
            let state = document.getElementById('cust-state').value;
            let landmark = document.getElementById('cust-landmark').value;
            let street = document.getElementById('cust-street').value;
            let payment_type = document.getElementById('pay_mode').value;

            let amount = cart.reduce((s, i) => s + i.price, 0);

            let payload = { name, email, phone, pincode, city, state, landmark, street, amount, payment_type, items: cart };

            fetch('/place_order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(data => {
                if(data.status === 'success') {
                    window.location.href = '/tracking/' + data.order_id;
                } else {
                    alert('Order Error: ' + data.message);
                    btn.innerText = 'Place Order';
                    btn.disabled = false;
                }
            })
            .catch(err => {
                alert('Order Failed. Please try again.');
                btn.innerText = 'Place Order';
                btn.disabled = false;
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
    <title>Order Status | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; padding: 40px 20px; display: flex; justify-content: center; align-items: center; }

        .card { background: white; max-width: 650px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); }
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 28px; text-align: center; margin-bottom: 5px; }
        p.subtitle { color: #666; font-size: 13px; text-align: center; margin-bottom: 30px; }

        /* Timeline Tracker */
        .tracker-container { display: flex; justify-content: space-between; align-items: center; position: relative; margin: 40px 0; }
        .tracker-line { position: absolute; top: 15px; left: 0; width: 100%; height: 4px; background: #e0e0e0; z-index: 1; }
        .tracker-progress { position: absolute; top: 15px; left: 0; height: 4px; background: #2e7d32; z-index: 2; transition: width 0.5s ease; }
        .step-node { position: relative; z-index: 3; background: white; text-align: center; width: 80px; }
        .node-icon { width: 34px; height: 34px; border-radius: 50%; background: #e0e0e0; color: white; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 14px; }
        .step-node.completed .node-icon { background: #2e7d32; }
        .step-node.active .node-icon { background: var(--accent-gold); box-shadow: 0 0 0 4px rgba(212, 163, 115, 0.3); }
        .node-label { font-size: 11px; font-weight: 600; color: #666; }
        .step-node.completed .node-label, .step-node.active .node-label { color: var(--green-primary); }

        .info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 25px; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 13px; color: #444; }
        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: block; text-align: center; margin-top: 20px; }
    </style>
</head>
<body>

    <div class="card">
        {% if order %}
        <h1>Order Status</h1>
        <p class="subtitle">Reference ID: <b style="font-family:monospace; color:var(--green-primary);">{{ order.order_id }}</b></p>

        <!-- Dynamic Tracking Line -->
        {% set status_map = {'Placed': 0, 'Packaging': 33, 'Shipped': 66, 'Delivered': 100} %}
        {% set current_pct = status_map.get(order.status, 0) %}

        <div class="tracker-container">
            <div class="tracker-line"></div>
            <div class="tracker-progress" style="width: {{ current_pct }}%;"></div>

            <div class="step-node {% if current_pct >= 0 %}completed{% endif %}">
                <div class="node-icon"><i class="fa-solid fa-check"></i></div>
                <div class="node-label">Placed</div>
            </div>
            <div class="step-node {% if current_pct >= 33 %}completed{% elif current_pct == 0 %}active{% endif %}">
                <div class="node-icon"><i class="fa-solid fa-box"></i></div>
                <div class="node-label">Packaging</div>
            </div>
            <div class="step-node {% if current_pct >= 66 %}completed{% elif current_pct == 33 %}active{% endif %}">
                <div class="node-icon"><i class="fa-solid fa-truck"></i></div>
                <div class="node-label">Shipped</div>
            </div>
            <div class="step-node {% if current_pct == 100 %}completed{% endif %}">
                <div class="node-icon"><i class="fa-solid fa-house-chimney"></i></div>
                <div class="node-label">Delivered</div>
            </div>
        </div>

        <div class="info-box">
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Email:</span><b>{{ order.email }}</b></div>
            <div class="info-row"><span>Phone:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Delivery Address:</span><span style="max-width: 250px; text-align: right;">{{ order.full_address }}</span></div>
            <div class="info-row" style="border-top:1px solid #ddd; padding-top:10px; margin-top:10px;">
                <span>Payment Method:</span><b>{{ order.payment_type }}</b>
            </div>
            <div class="info-row">
                <span>Payment Status:</span>
                {% if order.payment_type == 'Online Payment' %}
                <b style="color:#2e7d32;">Paid Online</b>
                {% else %}
                <b style="color:#e65100;">Cash on Delivery</b>
                {% endif %}
            </div>
        </div>

        <h4 style="color:var(--green-primary); margin-bottom:10px;">Items Ordered</h4>
        <div style="background:#fdfdfd; border:1px solid #eee; border-radius:10px; padding:15px; margin-bottom:20px;">
            {% for item in order.items %}
            <div style="display:flex; justify-content:space-between; margin-bottom:8px; font-size:13px;">
                <span>{{ item.name }}</span>
                <b>₹{{ item.price }}</b>
            </div>
            {% endfor %}
            <div style="border-top:1px solid #ddd; padding-top:8px; margin-top:8px; display:flex; justify-content:space-between; font-weight:bold; color:var(--green-primary);">
                <span>Total Bill (Incl. Taxes)</span>
                <span>₹{{ order.amount }}</span>
            </div>
        </div>

        <a href="/" class="btn-home">Return to Home</a>

        {% else %}
        <h1>Order Not Found</h1>
        <p class="subtitle">No details available for Order ID: {{ order_id }}</p>
        <a href="/" class="btn-home">Return to Home</a>
        {% endif %}
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
    <title>KESH AADAR | Admin Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background: #f4f6f8; color: #333; display: flex; min-height: 100vh; }

        /* Admin Sidebar */
        .sidebar { width: 260px; background: var(--green-primary); color: white; padding: 25px 20px; transition: 0.3s; position: fixed; height: 100vh; z-index: 100; }
        .sidebar.closed { transform: translateX(-100%); }
        .sidebar h2 { font-size: 20px; color: var(--accent-gold); margin-bottom: 30px; }
        .nav-item { display: flex; align-items: center; gap: 12px; padding: 12px 15px; color: #ddd; text-decoration: none; border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: 0.2s; }
        .nav-item:hover, .nav-item.active { background: rgba(255,255,255,0.1); color: white; }

        /* Main Content Area */
        .main-content { flex: 1; margin-left: 260px; padding: 30px; transition: 0.3s; }
        .main-content.expanded { margin-left: 0; }

        .top-bar { display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 25px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
        .toggle-btn { font-size: 20px; cursor: pointer; background: none; border: none; color: var(--green-primary); }

        .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); margin-bottom: 25px; }
        h3 { color: var(--green-primary); margin-bottom: 20px; font-size: 18px; }

        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #fafafa; color: #666; font-weight: 600; }

        .status-select { padding: 6px 10px; border-radius: 6px; border: 1px solid #ddd; font-size: 12px; font-weight: 600; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 12px; font-weight: 600; margin-bottom: 5px; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; }
        .btn { background: var(--green-primary); color: white; padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 13px; }
    </style>
</head>
<body>

    <div class="sidebar" id="adminSidebar">
        <h2>KESH AADAR Admin</h2>
        <div class="nav-item active" onclick="showSection('orders')"><i class="fa-solid fa-cart-shopping"></i> Orders</div>
        <div class="nav-item" onclick="showSection('products')"><i class="fa-solid fa-box"></i> Add Product</div>
        <div class="nav-item" onclick="showSection('inventory')"><i class="fa-solid fa-list-check"></i> Inventory</div>
        <div class="nav-item" onclick="showSection('settings')"><i class="fa-solid fa-sliders"></i> Logo Settings</div>
    </div>

    <div class="main-content" id="mainContent">
        <div class="top-bar">
            <button class="toggle-btn" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
            <span style="font-weight: 600; font-size: 14px;">Store Management Console</span>
        </div>

        <!-- Orders Section -->
        <div id="sec-orders" class="card">
            <h3>Customer Orders</h3>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Customer</th>
                            <th>Phone</th>
                            <th>Address</th>
                            <th>Amount</th>
                            <th>Payment</th>
                            <th>Status Control</th>
                        </tr>
                    </thead>
                    <tbody id="orders-table-body"></tbody>
                </table>
            </div>
        </div>

        <!-- Add/Edit Product Section -->
        <div id="sec-products" class="card" style="display:none;">
            <h3 id="form-title">Upload / Edit Product</h3>
            <form id="productForm" onsubmit="event.preventDefault(); saveProduct();">
                <input type="hidden" id="prod-id">
                <div class="form-group">
                    <label>Product Name</label>
                    <input type="text" id="prod-name" required>
                </div>
                <div class="form-group">
                    <label>Price (₹)</label>
                    <input type="number" id="prod-price" required>
                </div>
                <div class="form-group">
                    <label>Stock Quantity</label>
                    <input type="number" id="prod-stock" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="prod-desc" rows="3"></textarea>
                </div>
                <div class="form-group">
                    <label>Media Upload (Image or Video File)</label>
                    <input type="file" id="prod-media-file" accept="image/*,video/*">
                </div>
                <button type="submit" class="btn">Save Product</button>
            </form>
        </div>

        <!-- Inventory Section -->
        <div id="sec-inventory" class="card" style="display:none;">
            <h3>Inventory & Stock Control</h3>
            <table>
                <thead>
                    <tr>
                        <th>Media</th>
                        <th>Name</th>
                        <th>Price</th>
                        <th>Stock</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="inventory-table-body"></tbody>
            </table>
        </div>

        <!-- Settings Section -->
        <div id="sec-settings" class="card" style="display:none;">
            <h3>Website Profile Logo</h3>
            <div class="form-group">
                <label>Upload New Brand Logo</label>
                <input type="file" id="logo-file" accept="image/*">
            </div>
            <button class="btn" onclick="uploadLogo()">Update Store Logo</button>
        </div>
    </div>

    <script>
        let adminData = { orders: [], products: [], logo: "" };

        function loadData() {
            fetch('/api/admin/data')
            .then(r => r.json())
            .then(data => {
                adminData = data;
                renderOrders();
                renderInventory();
            });
        }
        loadData();

        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('closed');
            document.getElementById('mainContent').classList.toggle('expanded');
        }

        function showSection(sec) {
            ['orders','products','inventory','settings'].forEach(s => document.getElementById('sec-'+s).style.display = 'none');
            document.getElementById('sec-'+sec).style.display = 'block';
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            event.currentTarget.classList.add('active');
        }

        function renderOrders() {
            let tbody = document.getElementById('orders-table-body');
            tbody.innerHTML = '';
            adminData.orders.reverse().forEach(o => {
                tbody.innerHTML += `
                <tr>
                    <td><b>${o.order_id}</b></td>
                    <td>${o.name}<br><small>${o.email}</small></td>
                    <td>${o.phone}</td>
                    <td><small>${o.full_address}</small></td>
                    <td>₹${o.amount}</td>
                    <td><small>${o.payment_type}</small></td>
                    <td>
                        <select class="status-select" onchange="updateOrderStatus('${o.order_id}', this.value)">
                            <option value="Placed" ${o.status==='Placed'?'selected':''}>Placed</option>
                            <option value="Packaging" ${o.status==='Packaging'?'selected':''}>Packaging</option>
                            <option value="Shipped" ${o.status==='Shipped'?'selected':''}>Shipped</option>
                            <option value="Delivered" ${o.status==='Delivered'?'selected':''}>Delivered</option>
                        </select>
                    </td>
                </tr>`;
            });
        }

        function updateOrderStatus(order_id, status) {
            fetch('/api/admin/update_status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({order_id, status})
            }).then(() => alert('Order status updated!'));
        }

        function renderInventory() {
            let tbody = document.getElementById('inventory-table-body');
            tbody.innerHTML = '';
            adminData.products.forEach(p => {
                let mediaHtml = p.media_type === 'video' ? 
                    `<video src="${p.image}" style="width:40px; height:40px; object-fit:cover; border-radius:4px;"></video>` :
                    `<img src="${p.image}" style="width:40px; height:40px; object-fit:cover; border-radius:4px;">`;

                tbody.innerHTML += `
                <tr>
                    <td>${mediaHtml}</td>
                    <td><b>${p.name}</b></td>
                    <td>₹${p.price}</td>
                    <td>${p.stock}</td>
                    <td>
                        <button onclick="editProduct(${p.id})" style="background:#2196F3; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">Edit</button>
                        <button onclick="deleteProduct(${p.id})" style="background:#f44336; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">Delete</button>
                    </td>
                </tr>`;
            });
        }

        function editProduct(id) {
            let p = adminData.products.find(x => x.id === id);
            document.getElementById('prod-id').value = p.id;
            document.getElementById('prod-name').value = p.name;
            document.getElementById('prod-price').value = p.price;
            document.getElementById('prod-stock').value = p.stock;
            document.getElementById('prod-desc').value = p.desc;
            showSection('products');
        }

        function saveProduct() {
            let id = document.getElementById('prod-id').value;
            let name = document.getElementById('prod-name').value;
            let price = document.getElementById('prod-price').value;
            let stock = document.getElementById('prod-stock').value;
            let desc = document.getElementById('prod-desc').value;
            let fileInput = document.getElementById('prod-media-file');

            let payload = { id, name, price, stock, desc };

            if(fileInput.files.length > 0) {
                let file = fileInput.files[0];
                let reader = new FileReader();
                reader.onload = function(e) {
                    payload.image = e.target.result;
                    payload.media_type = file.type.startsWith('video') ? 'video' : 'image';
                    sendProductData(payload);
                };
                reader.readAsDataURL(file);
            } else {
                sendProductData(payload);
            }
        }

        function sendProductData(payload) {
            fetch('/api/admin/product', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(r => r.json())
            .then(() => {
                alert('Product saved successfully!');
                loadData();
                showSection('inventory');
            });
        }

        function deleteProduct(id) {
            if(confirm('Are you sure you want to delete/suspend this product?')) {
                fetch('/api/admin/product?id=' + id, { method: 'DELETE' })
                .then(() => {
                    loadData();
                });
            }
        }

        function uploadLogo() {
            let fileInput = document.getElementById('logo-file');
            if(fileInput.files.length === 0) return alert('Select an image file first.');
            
            let file = fileInput.files[0];
            let reader = new FileReader();
            reader.onload = function(e) {
                fetch('/api/admin/update_logo', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ logo: e.target.result })
                })
                .then(() => alert('Store Logo Updated!'));
            };
            reader.readAsDataURL(file);
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
