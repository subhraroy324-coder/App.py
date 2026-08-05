import os
import json
import smtplib
import threading
import datetime
import random
import hashlib
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import cloudinary
import cloudinary.uploader
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_me')

# --- Database Setup ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keshaadar.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Cloudinary Configuration ---
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# --- Razorpay Keys (public key used in frontend) ---
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_live_TGzOHwqjwcYfov')

# --- Admin Credentials (from env) ---
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# --- SMTP Config ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', 'keshaadar@gmail.com')
SMTP_PASS = os.environ.get('SMTP_PASS', 'zvxb mrbs ccoi vfrl')

# ===================== MODELS =====================
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))  # optional
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)  # street
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    landmark = db.Column(db.String(200))
    items_json = db.Column(db.Text, nullable=False)  # store as JSON string
    total_amount = db.Column(db.Float, nullable=False)
    payment_type = db.Column(db.String(50))  # 'Online Payment' or 'Cash on Delivery'
    payment_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default='placed')  # placed, packaging, shifting, delivered
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.datetime.utcnow)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True)
    value = db.Column(db.Text)

# ===================== HELPERS =====================
def get_logo_url():
    setting = Setting.query.filter_by(key='logo_url').first()
    return setting.value if setting else 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80'

def set_logo_url(url):
    setting = Setting.query.filter_by(key='logo_url').first()
    if setting:
        setting.value = url
    else:
        setting = Setting(key='logo_url', value=url)
        db.session.add(setting)
    db.session.commit()

def send_order_email(recipient_email, name, order_id, amount, items, full_address, tracking_url):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Confirmed: {order_id} - KESH AADAR"
        msg['From'] = f"KESH AADAR <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> - ₹{i['price']}</li>" for i in items])

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
                    <a href="{tracking_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block; box-shadow: 0 5px 15px rgba(27, 67, 50, 0.3);">Check Live Order Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Reply directly to this email or contact customer support at keshaadar@gmail.com</p>
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
        print(f"Confirmation email sent to {recipient_email}")
    except Exception as e:
        print(f"Email send error: {e}")

# ===================== ADMIN AUTH =====================
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ===================== ROUTES (PUBLIC) =====================
@app.route('/')
def index():
    products = Product.query.filter_by(is_active=True).all()
    return render_template_string(PUBLIC_TEMPLATE, products=products, logo_url=get_logo_url())

@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        data = request.get_json()
        # Validate required fields
        required = ['name', 'email', 'phone', 'street', 'city', 'state', 'pincode', 'amount', 'items']
        for field in required:
            if not data.get(field):
                return jsonify({"error": f"Missing {field}"}), 400

        # Generate order ID
        order_id = "KESH-" + str(random.randint(10000, 99999))
        
        # Build full address
        full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
        
        # Create order record
        order = Order(
            order_id=order_id,
            customer_name=data['name'],
            email=data['email'],
            phone=data['phone'],
            address=data['street'],
            city=data['city'],
            state=data['state'],
            pincode=data['pincode'],
            landmark=data.get('landmark', ''),
            items_json=json.dumps(data['items']),
            total_amount=float(data['amount']),
            payment_type=data.get('payment_type', 'Online Payment'),
            payment_id=data.get('payment_id', ''),
            status='placed'
        )
        db.session.add(order)
        db.session.commit()

        # Send confirmation email in background
        tracking_url = url_for('track_order', order_id=order_id, _external=True)
        email_thread = threading.Thread(
            target=send_order_email,
            args=(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, tracking_url)
        )
        email_thread.start()

        return jsonify({"status": "success", "order_id": order_id})
    except Exception as e:
        print("Place order error:", str(e))
        return jsonify({"error": "Internal server error"}), 500

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = Order.query.filter_by(order_id=order_id).first()
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, logo_url=get_logo_url())

@app.route('/track/<order_id>')
def track_order(order_id):
    order = Order.query.filter_by(order_id=order_id).first_or_404()
    items = json.loads(order.items_json)
    return render_template_string(TRACK_TEMPLATE, order=order, items=items, logo_url=get_logo_url())

@app.route('/track_order', methods=['GET'])
def track_order_api():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"found": False})
    # Search by order_id or email
    order = Order.query.filter((Order.order_id == q) | (Order.email == q)).first()
    if order:
        return jsonify({"found": True, "order": {
            "order_id": order.order_id,
            "customer_name": order.customer_name,
            "email": order.email,
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": order.created_at.strftime("%b %d, %Y - %I:%M %p")
        }})
    return jsonify({"found": False})

# ===================== ROUTES (ADMIN) =====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'error')
    return render_template_string(ADMIN_LOGIN_TEMPLATE)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    total_orders = Order.query.count()
    pending_orders = Order.query.filter(Order.status != 'delivered').count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE,
                                  total_orders=total_orders,
                                  pending_orders=pending_orders,
                                  total_revenue=total_revenue,
                                  recent_orders=recent_orders)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template_string(ADMIN_ORDERS_TEMPLATE, orders=orders)

@app.route('/admin/order/update_status', methods=['POST'])
@admin_required
def admin_update_order_status():
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')
    if not order_id or new_status not in ['placed', 'packaging', 'shifting', 'delivered']:
        return jsonify({"error": "Invalid data"}), 400
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    order.status = new_status
    db.session.commit()
    return jsonify({"success": True})

@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template_string(ADMIN_PRODUCTS_TEMPLATE, products=products)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        price = float(request.form.get('price', 0))
        stock = int(request.form.get('stock', 0))
        description = request.form.get('description', '')
        
        # Handle image upload
        image_file = request.files.get('image')
        image_url = ''
        if image_file and image_file.filename:
            upload_result = cloudinary.uploader.upload(image_file, folder='keshaadar/products')
            image_url = upload_result['secure_url']
        
        # Handle video upload
        video_file = request.files.get('video')
        video_url = ''
        if video_file and video_file.filename:
            upload_result = cloudinary.uploader.upload(video_file, resource_type='video', folder='keshaadar/products')
            video_url = upload_result['secure_url']
        
        product = Product(
            name=name,
            category=category,
            price=price,
            stock=stock,
            description=description,
            image_url=image_url,
            video_url=video_url,
            is_active=True
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully', 'success')
        return redirect(url_for('admin_products'))
    return render_template_string(ADMIN_PRODUCT_FORM_TEMPLATE, product=None)

@app.route('/admin/product/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.category = request.form.get('category')
        product.price = float(request.form.get('price', 0))
        product.stock = int(request.form.get('stock', 0))
        product.description = request.form.get('description', '')
        
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            upload_result = cloudinary.uploader.upload(image_file, folder='keshaadar/products')
            product.image_url = upload_result['secure_url']
        
        video_file = request.files.get('video')
        if video_file and video_file.filename:
            upload_result = cloudinary.uploader.upload(video_file, resource_type='video', folder='keshaadar/products')
            product.video_url = upload_result['secure_url']
        
        db.session.commit()
        flash('Product updated', 'success')
        return redirect(url_for('admin_products'))
    return render_template_string(ADMIN_PRODUCT_FORM_TEMPLATE, product=product)

@app.route('/admin/product/toggle/<int:id>')
@admin_required
def admin_toggle_product(id):
    product = Product.query.get_or_404(id)
    product.is_active = not product.is_active
    db.session.commit()
    flash(f'Product {"activated" if product.is_active else "suspended"}', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/product/delete/<int:id>')
@admin_required
def admin_delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/logo', methods=['GET', 'POST'])
@admin_required
def admin_logo():
    if request.method == 'POST':
        logo_file = request.files.get('logo')
        if logo_file and logo_file.filename:
            upload_result = cloudinary.uploader.upload(logo_file, folder='keshaadar/logo')
            logo_url = upload_result['secure_url']
            set_logo_url(logo_url)
            flash('Logo updated successfully', 'success')
        else:
            flash('No file selected', 'error')
        return redirect(url_for('admin_logo'))
    current_logo = get_logo_url()
    return render_template_string(ADMIN_LOGO_TEMPLATE, current_logo=current_logo)

# ===================== TEMPLATES (All HTML) =====================

# --- PUBLIC TEMPLATE (same as before but with logo dynamic) ---
PUBLIC_TEMPLATE = """
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

        /* Sidebar */
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: 0.4s; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.77, 0, 0.175, 1); padding: 30px 20px; overflow-y: auto; }
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
        .product-img-container { height: 230px; overflow: hidden; background: #f7f5f0; }
        .product-img-container img { width: 100%; height: 100%; object-fit: cover; }
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
                <img src="{{ logo_url }}" alt="Logo" class="logo-img">
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
                <div class="product-img-container">
                    {% if p.image_url %}
                        <img src="{{ p.image_url }}" alt="{{ p.name }}" id="img-{{ p.id }}">
                    {% else %}
                        <img src="https://via.placeholder.com/400x300?text=No+Image" alt="No image">
                    {% endif %}
                </div>
                <div class="product-info">
                    <h3 style="color:var(--green-primary); font-size:16px; margin-bottom:5px;">{{ p.name }}</h3>
                    <p style="font-size:12px; color:#666;">{{ p.description or '' }}</p>
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
        // Public templates' JavaScript (same as before, with minor adjustments)
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
            if (!img) return;
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
            let payload = { name, email, phone, pincode, city, state, landmark, street, amount: amt, payment_type: mode === 'cod' ? 'Cash on Delivery' : 'Online Payment', items: cart };

            saveAddressToStorage(payload);

            if(mode === 'online') {
                var options = {
                    "key": "{{ RAZORPAY_KEY_ID }}",
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
                if(data.order_id) {
                    window.location.href = '/order_success/' + data.order_id;
                } else {
                    alert('Order failed. Please try again.');
                }
            })
            .catch(err => {
                alert('Server error. Please try again.');
                console.error(err);
            });
        }

        function trackOrder() {
            let q = document.getElementById('track-input').value.trim();
            if(!q) return;
            fetch('/track_order?q=' + encodeURIComponent(q)).then(r => r.json()).then(data => {
                let d = document.getElementById('track-result');
                if(data.found) {
                    let order = data.order;
                    d.innerHTML = `<div style="background:#e8f5e9; padding:12px; border-radius:8px; font-size:13px;">
                        <h4 style="color:#2e7d32;">Order: ${order.order_id}</h4>
                        <p>Customer: ${order.customer_name}</p>
                        <p>Total: ₹${order.total_amount}</p>
                        <p>Status: ${order.status}</p>
                        <a href="/track/${order.order_id}" target="_blank" style="color:var(--green-primary); font-weight:600;">View Full Tracking</a>
                    </div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- SUCCESS TEMPLATE (same as before) ---
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

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; }
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
            <div class="info-row"><span>Customer:</span><b>{{ order.customer_name }}</b></div>
            <div class="info-row"><span>Total Amount:</span><b>₹{{ order.total_amount }}</b></div>
            <div class="info-row"><span>Payment Mode:</span><b>{{ order.payment_type }}</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 250px; text-align: right;">{{ order.address }}, {{ order.city }}, {{ order.state }} - {{ order.pincode }}</span></div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 20px;"><i class="fa-solid fa-envelope"></i> An official invoice & tracking details have been sent to your email.</p>
        
        <a href="/" class="btn-home">Continue Shopping</a>
    </div>

</body>
</html>
"""

# --- TRACKING TEMPLATE ---
TRACK_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Track Order | KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; --green-light: #2d6a4f; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); padding: 30px 20px; color: #2b2b2b; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); padding: 30px; }

        .track-header { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; }
        .track-header img { width: 50px; height: 50px; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .track-header h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 26px; }
        .track-header a { margin-left: auto; color: var(--green-primary); text-decoration: none; font-weight: 600; }

        .order-summary { background: #FAF7F0; padding: 20px; border-radius: 12px; margin-bottom: 30px; border: 1px solid #eee; }
        .order-summary .row { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 14px; }
        .order-summary .total { font-weight: 700; color: var(--green-primary); font-size: 18px; border-top: 1px dashed #ccc; padding-top: 10px; margin-top: 6px; }

        .timeline { position: relative; padding: 20px 0; }
        .timeline::before { content: ''; position: absolute; top: 0; left: 20px; height: 100%; width: 4px; background: #ddd; }
        .timeline-item { display: flex; margin-bottom: 30px; position: relative; padding-left: 50px; }
        .timeline-item .dot { position: absolute; left: 11px; top: 4px; width: 22px; height: 22px; border-radius: 50%; background: #ddd; border: 3px solid white; box-shadow: 0 0 0 2px #ddd; }
        .timeline-item.active .dot { background: var(--green-primary); box-shadow: 0 0 0 2px var(--green-primary); }
        .timeline-item .content { flex: 1; }
        .timeline-item .content h3 { font-size: 16px; color: #333; margin-bottom: 2px; }
        .timeline-item .content p { font-size: 13px; color: #666; margin: 0; }
        .timeline-item .content .time { font-size: 12px; color: #999; }

        .item-list { margin-top: 20px; border-top: 1px solid #eee; padding-top: 20px; }
        .item-list h3 { font-size: 16px; color: var(--green-primary); margin-bottom: 10px; }
        .item-list ul { list-style: none; padding: 0; }
        .item-list ul li { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f5f5f5; font-size: 14px; }

        .back-home { display: inline-block; margin-top: 20px; background: var(--green-primary); color: white; text-decoration: none; padding: 12px 25px; border-radius: 30px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <div class="track-header">
            <img src="{{ logo_url }}" alt="Logo">
            <h1>Order Tracking</h1>
            <a href="/">← Home</a>
        </div>

        <div class="order-summary">
            <div class="row"><span>Order ID</span><b style="font-family:monospace;">{{ order.order_id }}</b></div>
            <div class="row"><span>Placed On</span>{{ order.created_at.strftime('%b %d, %Y at %I:%M %p') }}</div>
            <div class="row"><span>Customer</span>{{ order.customer_name }}</div>
            <div class="row"><span>Email</span>{{ order.email }}</div>
            <div class="row"><span>Phone</span>{{ order.phone }}</div>
            <div class="row"><span>Address</span>{{ order.address }}, {{ order.city }}, {{ order.state }} - {{ order.pincode }} {% if order.landmark %}(Landmark: {{ order.landmark }}){% endif %}</div>
            <div class="row"><span>Payment</span>{{ order.payment_type }} {% if order.payment_id and order.payment_id != 'COD' %}(ID: {{ order.payment_id }}){% endif %}</div>
            <div class="row total"><span>Total Amount</span>₹{{ order.total_amount }}</div>
        </div>

        <h3 style="margin-bottom: 10px; color: var(--green-primary);">Order Status</h3>
        <div class="timeline">
            {% set statuses = ['placed', 'packaging', 'shifting', 'delivered'] %}
            {% set labels = {'placed': 'Order Placed', 'packaging': 'Packaging', 'shifting': 'Shifting', 'delivered': 'Delivered'} %}
            {% set current_index = statuses.index(order.status) %}
            {% for s in statuses %}
                <div class="timeline-item {% if loop.index0 <= current_index %}active{% endif %}">
                    <div class="dot"></div>
                    <div class="content">
                        <h3>{{ labels[s] }}</h3>
                        <p class="time">{% if loop.index0 <= current_index %}{{ order.created_at.strftime('%b %d, %Y') }}{% else %}Pending{% endif %}</p>
                    </div>
                </div>
            {% endfor %}
        </div>

        <div class="item-list">
            <h3>Items Ordered</h3>
            <ul>
                {% for item in items %}
                <li><span>{{ item.name }}</span><span>₹{{ item.price }}</span></li>
                {% endfor %}
            </ul>
            <div style="text-align: right; font-weight: 700; margin-top: 10px; color: var(--green-primary);">Total: ₹{{ order.total_amount }}</div>
        </div>

        <a href="/" class="back-home">Continue Shopping</a>
    </div>
</body>
</html>
"""

# ===================== ADMIN TEMPLATES =====================
ADMIN_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Login - KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Poppins', sans-serif; background: #FAF7F0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: white; padding: 40px; border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.08); width: 350px; }
        h2 { color: #1b4332; margin-bottom: 20px; text-align: center; }
        input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #1b4332; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
        .flash { color: #c62828; font-size: 14px; margin-bottom: 10px; text-align: center; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Admin Login</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash">{{ messages[0][1] }}</div>
            {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - KESH AADAR</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: 'Poppins', sans-serif; }
        body { background: #FAF7F0; }
        .sidebar { width: 250px; background: #1b4332; color: white; height: 100vh; position: fixed; padding: 20px; }
        .sidebar h2 { font-size: 20px; margin-bottom: 30px; }
        .sidebar a { display: block; color: #ddd; text-decoration: none; padding: 12px 15px; border-radius: 8px; margin-bottom: 5px; }
        .sidebar a:hover, .sidebar a.active { background: #2d6a4f; color: white; }
        .sidebar a i { width: 20px; margin-right: 10px; }
        .main { margin-left: 250px; padding: 30px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
        .stat-card h3 { font-size: 28px; color: #1b4332; }
        .stat-card p { color: #666; font-size: 14px; }
        .recent-orders { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
        .recent-orders table { width: 100%; border-collapse: collapse; }
        .recent-orders th, .recent-orders td { padding: 10px; text-align: left; border-bottom: 1px solid #eee; }
        .btn { background: #1b4332; color: white; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #2d6a4f; }
        .logout { float: right; color: #ddd; text-decoration: none; margin-top: -10px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>KESH AADAR</h2>
        <a href="/admin" class="active"><i class="fas fa-chart-pie"></i> Dashboard</a>
        <a href="/admin/orders"><i class="fas fa-box"></i> Orders</a>
        <a href="/admin/products"><i class="fas fa-cube"></i> Products</a>
        <a href="/admin/logo"><i class="fas fa-image"></i> Logo</a>
        <a href="/admin/logout"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
    <div class="main">
        <a href="/admin/logout" class="logout">Logout</a>
        <h1 style="color:#1b4332; margin-bottom:20px;">Dashboard</h1>
        <div class="stats">
            <div class="stat-card"><h3>{{ total_orders }}</h3><p>Total Orders</p></div>
            <div class="stat-card"><h3>{{ pending_orders }}</h3><p>Pending (not delivered)</p></div>
            <div class="stat-card"><h3>₹{{ total_revenue }}</h3><p>Total Revenue</p></div>
        </div>
        <div class="recent-orders">
            <h3 style="margin-bottom:15px;">Recent Orders</h3>
            <table>
                <tr><th>Order ID</th><th>Customer</th><th>Total</th><th>Status</th><th>Action</th></tr>
                {% for o in recent_orders %}
                <tr>
                    <td>{{ o.order_id }}</td>
                    <td>{{ o.customer_name }}</td>
                    <td>₹{{ o.total_amount }}</td>
                    <td><span style="text-transform:capitalize;">{{ o.status }}</span></td>
                    <td><a href="/admin/orders" class="btn" style="padding:4px 10px; font-size:12px;">View</a></td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

ADMIN_ORDERS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Orders - Admin</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: 'Poppins', sans-serif; }
        body { background: #FAF7F0; }
        .sidebar { width: 250px; background: #1b4332; color: white; height: 100vh; position: fixed; padding: 20px; }
        .sidebar h2 { font-size: 20px; margin-bottom: 30px; }
        .sidebar a { display: block; color: #ddd; text-decoration: none; padding: 12px 15px; border-radius: 8px; margin-bottom: 5px; }
        .sidebar a:hover, .sidebar a.active { background: #2d6a4f; color: white; }
        .sidebar a i { width: 20px; margin-right: 10px; }
        .main { margin-left: 250px; padding: 30px; }
        table { width: 100%; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 5px 15px rgba(0,0,0,0.05); border-collapse: collapse; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f5f5f5; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status-placed { background: #fff3cd; color: #856404; }
        .status-packaging { background: #cce5ff; color: #004085; }
        .status-shifting { background: #d4edda; color: #155724; }
        .status-delivered { background: #d1ecf1; color: #0c5460; }
        .btn-update { padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin: 2px; }
        .btn-update.packaging { background: #cce5ff; color: #004085; }
        .btn-update.shifting { background: #d4edda; color: #155724; }
        .btn-update.delivered { background: #d1ecf1; color: #0c5460; }
        .btn-update:hover { opacity: 0.8; }
        .back { display: inline-block; margin-bottom: 15px; color: #1b4332; text-decoration: none; font-weight: 600; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>KESH AADAR</h2>
        <a href="/admin"><i class="fas fa-chart-pie"></i> Dashboard</a>
        <a href="/admin/orders" class="active"><i class="fas fa-box"></i> Orders</a>
        <a href="/admin/products"><i class="fas fa-cube"></i> Products</a>
        <a href="/admin/logo"><i class="fas fa-image"></i> Logo</a>
        <a href="/admin/logout"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
    <div class="main">
        <a href="/admin" class="back"><i class="fas fa-arrow-left"></i> Back to Dashboard</a>
        <h1 style="color:#1b4332; margin-bottom:20px;">All Orders</h1>
        <table>
            <tr>
                <th>Order ID</th><th>Customer</th><th>Email</th><th>Phone</th><th>Address</th><th>Total</th><th>Status</th><th>Actions</th>
            </tr>
            {% for o in orders %}
            <tr>
                <td>{{ o.order_id }}</td>
                <td>{{ o.customer_name }}</td>
                <td>{{ o.email }}</td>
                <td>{{ o.phone }}</td>
                <td>{{ o.address }}, {{ o.city }}, {{ o.state }} - {{ o.pincode }}</td>
                <td>₹{{ o.total_amount }}</td>
                <td><span class="status-badge status-{{ o.status }}">{{ o.status|capitalize }}</span></td>
                <td>
                    {% if o.status != 'packaging' %}
                        <button class="btn-update packaging" onclick="updateStatus('{{ o.order_id }}', 'packaging')">Packaging</button>
                    {% endif %}
                    {% if o.status != 'shifting' and o.status != 'delivered' %}
                        <button class="btn-update shifting" onclick="updateStatus('{{ o.order_id }}', 'shifting')">Shifting</button>
                    {% endif %}
                    {% if o.status != 'delivered' %}
                        <button class="btn-update delivered" onclick="updateStatus('{{ o.order_id }}', 'delivered')">Delivered</button>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <script>
        function updateStatus(orderId, newStatus) {
            if (!confirm(`Update order ${orderId} to "${newStatus}"?`)) return;
            fetch('/admin/order/update_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId, status: newStatus })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('Status updated!');
                    location.reload();
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(err => alert('Server error'));
        }
    </script>
</body>
</html>
"""

ADMIN_PRODUCTS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Products - Admin</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: 'Poppins', sans-serif; }
        body { background: #FAF7F0; }
        .sidebar { width: 250px; background: #1b4332; color: white; height: 100vh; position: fixed; padding: 20px; }
        .sidebar h2 { font-size: 20px; margin-bottom: 30px; }
        .sidebar a { display: block; color: #ddd; text-decoration: none; padding: 12px 15px; border-radius: 8px; margin-bottom: 5px; }
        .sidebar a:hover, .sidebar a.active { background: #2d6a4f; color: white; }
        .sidebar a i { width: 20px; margin-right: 10px; }
        .main { margin-left: 250px; padding: 30px; }
        .btn { background: #1b4332; color: white; padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #2d6a4f; }
        .product-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px,1fr)); gap: 20px; margin-top: 20px; }
        .product-card { background: white; border-radius: 12px; padding: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); }
        .product-card img { width: 100%; height: 150px; object-fit: cover; border-radius: 8px; }
        .product-card h4 { margin: 10px 0 5px; }
        .product-card .actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
        .product-card .actions a { font-size: 12px; padding: 4px 10px; border-radius: 4px; text-decoration: none; color: white; }
        .edit { background: #007bff; }
        .delete { background: #dc3545; }
        .toggle { background: #ffc107; color: #333 !important; }
        .add-btn { margin-bottom: 20px; }
        .flash { padding: 10px; border-radius: 6px; margin-bottom: 15px; }
        .flash-success { background: #d4edda; color: #155724; }
        .flash-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>KESH AADAR</h2>
        <a href="/admin"><i class="fas fa-chart-pie"></i> Dashboard</a>
        <a href="/admin/orders"><i class="fas fa-box"></i> Orders</a>
        <a href="/admin/products" class="active"><i class="fas fa-cube"></i> Products</a>
        <a href="/admin/logo"><i class="fas fa-image"></i> Logo</a>
        <a href="/admin/logout"><i class="fas fa-sign-out-alt"></i> Logout</a>
    </div>
    <div class="main">
        <a href="/admin" style="color:#1b4332; text-decoration:none; font-weight:600;"><i class="fas fa-arrow-left"></i> Back</a>
        <h1 style="color:#1b4332; margin:15px 0;">Products</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, msg in messages %}
                <div class="flash flash-{{ category }}">{{ msg }}</div>
            {% endfor %}
        {% endwith %}
        <a href="/admin/product/add" class="btn add-btn"><i class="fas fa-plus"></i> Add Product</a>
        <div class="product-grid">
            {% for p in products %}
            <div class="product-card">
                <img src="{{ p.image_url or 'https://via.placeholder.com/300x200?text=No+Image' }}" alt="{{ p.name }}">
                <h4>{{ p.name }}</h4>
                <p>₹{{ p.price }} | Stock: {{ p.stock }}</p>
                <p style="font-size:12px; color:#666;">{{ p.category or 'Uncategorized' }}</p>
                <p style="font-size:12px;"><span style="font-weight:600;">Status:</span> {{ 'Active' if p.is_active else 'Suspended' }}</p>
                <div class="actions">
                    <a href="/admin/product/edit/{{ p.id }}" class="edit">Edit</a>
                    <a href="/admin/product/toggle/{{ p.id }}" class="toggle">{{ 'Suspend' if p.is_active else 'Activate' }}</a>
                    <a href="/admin/product/delete/{{ p.id }}" class="delete" onclick="return confirm('Delete this product?')">Delete</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

ADMIN_PRODUCT_FORM_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{% if product %}Edit{% else %}Add{% endif %} Product</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: 'Poppins', sans-serif; }
        body { background: #FAF7F0; padding: 30px; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
        h1 { color: #1b4332; margin-bottom: 20px; }
        label { font-weight: 600; display: block; margin: 10px 0 5px; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; }
        input[type="file"] { padding: 8px; }
        .btn { background: #1b4332; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; margin-top: 15px; }
        .btn:hover { background: #2d6a4f; }
        .back { color: #1b4332; text-decoration: none; font-weight:600; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/admin/products" class="back"><i class="fas fa-arrow-left"></i> Back to Products</a>
        <h1>{% if product %}Edit{% else %}Add New{% endif %} Product</h1>
        <form method="POST" enctype="multipart/form-data">
            <label>Name *</label>
            <input type="text" name="name" value="{{ product.name if product else '' }}" required>
            
            <label>Category</label>
            <input type="text" name="category" value="{{ product.category if product else '' }}">
            
            <label>Price (₹) *</label>
            <input type="number" step="0.01" name="price" value="{{ product.price if product else '' }}" required>
            
            <label>Stock *</label>
            <input type="number" name="stock" value="{{ product.stock if product else '' }}" required>
            
            <label>Description</label>
            <textarea name="description" rows="3">{{ product.description if product else '' }}</textarea>
            
            <label>Product Image (jpeg, png) *</label>
            <input type="file" name="image" accept="image/*">
            {% if product and product.image_url %}
                <p style="font-size:12px; color:#666;">Current: <a href="{{ product.image_url }}" target="_blank">View</a></p>
            {% endif %}
            
            <label>Product Video (optional)</label>
            <input type="file" name="video" accept="video/*">
            {% if product and product.video_url %}
                <p style="font-size:12px; color:#666;">Current: <a href="{{ product.video_url }}" target="_blank">View</a></p>
            {% endif %}
            
            <button type="submit" class="btn">{% if product %}Update{% else %}Add{% endif %} Product</button>
        </form>
    </div>
</body>
</html>
"""

ADMIN_LOGO_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Logo - Admin</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; font-family: 'Poppins', sans-serif; }
        body { background: #FAF7F0; padding: 30px; }
        .container { max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: center; }
        h1 { color: #1b4332; margin-bottom: 20px; }
        .logo-preview { width: 150px; height: 150px; border-radius: 50%; object-fit: cover; border: 3px solid #d4a373; margin: 20px auto; }
        input[type="file"] { margin: 15px 0; }
        .btn { background: #1b4332; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; }
        .btn:hover { background: #2d6a4f; }
        .back { color: #1b4332; text-decoration: none; font-weight:600; display: inline-block; margin-bottom: 15px; }
        .flash { padding: 10px; border-radius: 6px; margin-bottom: 15px; }
        .flash-success { background: #d4edda; color: #155724; }
        .flash-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <a href="/admin" class="back"><i class="fas fa-arrow-left"></i> Back to Dashboard</a>
        <h1>Update Logo</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, msg in messages %}
                <div class="flash flash-{{ category }}">{{ msg }}</div>
            {% endfor %}
        {% endwith %}
        <img src="{{ current_logo }}" alt="Current Logo" class="logo-preview">
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="logo" accept="image/*" required>
            <br>
            <button type="submit" class="btn">Upload New Logo</button>
        </form>
    </div>
</body>
</html>
"""

# ===================== INIT DB =====================
with app.app_context():
    db.create_all()
    # Create default logo if not exists
    if not Setting.query.filter_by(key='logo_url').first():
        set_logo_url('https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80')

# ===================== RUN =====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)        "category": "Skincare",
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
