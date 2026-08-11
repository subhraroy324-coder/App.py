From flask import Flask, render_template_string, request, jsonify, redirect, url_for, send_file
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import datetime
import random
import base64
import hmac
import hashlib
import urllib.request
import urllib.parse
import io
import time
import threading
from collections import defaultdict

# --- REPORTLAB PDF LIBRARIES ---
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'adorica_botanicals_secure_key_2026'

# --- RAZORPAY CONFIGURATION ---
RAZORPAY_KEY_ID = "rzp_live_TNBc6IiPsiAkOD"
RAZORPAY_KEY_SECRET = "iLeTigZRFMEzubj7hEbW9mnR"

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "keshaadar@gmail.com"
SMTP_PASS = "zvxb mrbs ccoi vfrl"

# --- DDOS PROTECTION & RATE LIMITING ---
IP_REQUESTS = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 80  # Max 80 requests per minute per IP
BLACKLISTED_IPS = []

# --- DATABASE & STORAGE ---
SETTINGS = {
    "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
    "brand_name": "THE ADORICA BOTANICALS"
}

# Dynamic Banner/Slider Storage
SLIDES = [
    {
        "id": 1,
        "image": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=1400&q=80",
        "video": "",
        "badge": "New Launch",
        "title": "Rosemary Oil Shots",
        "desc": "Precise 20% dose to promote hair follicle health, stimulate growth, and fight hair thinning naturally."
    },
    {
        "id": 2,
        "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=1400&q=80",
        "video": "",
        "badge": "Luxury Care",
        "title": "Saffron Kumkumadi Serum",
        "desc": "Traditional Ayurvedic formulation infused with pure Kashmiri saffron and sandalwood to fade pigmentation."
    }
]

PRODUCTS = [
    {
        "id": 1, 
        "name": "Aloe Neem Glow Face Wash", 
        "category": "Skin Care", 
        "price": 349, 
        "stock": 50, 
        "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Deep cleansing herbal formula with pure aloe vera and fresh neem extracts for radiant, blemish-free skin.",
        "ingredients": "Aloe Barbadensis Leaf Extract, Azadirachta Indica (Neem), Tea Tree Oil, Glycerin",
        "geography": "Neem organically cultivated in Jodhpur (Rajasthan); Aloe Vera hand-harvested from Anand (Gujarat).",
        "extraction": "Cold-pressed botanical extraction within 6 hours of harvest.",
        "rating": 4.9,
        "reviews_count": 128,
        "badge": "Best Seller",
        "status": "active"
    },
    {
        "id": 2, 
        "name": "Saffron Kumkumadi Night Serum", 
        "category": "Skin Care", 
        "price": 799, 
        "stock": 30, 
        "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Traditional Ayurvedic formulation infused with pure Kashmiri saffron and sandalwood to fade pigmentation and restore natural glow.",
        "ingredients": "Kashmiri Saffron, Sandalwood Oil, Lotus Extract, Goat Milk, Sesame Oil",
        "geography": "Grade-A Mongra Saffron sourced directly from Pampore (Kashmir Valley); Pure Sandalwood from Mysore (Karnataka).",
        "extraction": "Ancient Taila Paka Vidhi (16-step slow Ayurvedic infusion).",
        "rating": 4.8,
        "reviews_count": 94,
        "badge": "Luxury Care",
        "status": "active"
    },
    {
        "id": 3, 
        "name": "Bhringraj Onion Hair Growth Oil", 
        "category": "Oil", 
        "price": 499, 
        "stock": 40, 
        "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Potent blend of red onion extract and wildcrafted bhringraj to stop hair fall, stimulate hair roots, and promote dense growth.",
        "ingredients": "Red Onion Seed Oil, Bhringraj Extract, Amla, Brahmi, Virgin Coconut Oil",
        "geography": "Wildcrafted Bhringraj harvested from Western Ghats (Kerala); Small-batch Red Seed Onions from Nashik (Maharashtra).",
        "extraction": "Sun-macerated herb oil infusion process.",
        "rating": 4.9,
        "reviews_count": 215,
        "badge": "Top Rated",
        "status": "active"
    },
    {
        "id": 4, 
        "name": "Hibiscus & Shikakai Herbal Shampoo", 
        "category": "Shampoo", 
        "price": 399, 
        "stock": 45, 
        "image": "https://images.unsplash.com/photo-1526947425960-945c6e72858f?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Nourishing sulfate-free cleanser enriched with fresh hibiscus flowers and shikakai for silky, manageable hair.",
        "ingredients": "Hibiscus Rosa-Sinensis, Shikakai, Reetha, Plant Keratin, Provitamin B5",
        "geography": "Fresh Crimson Hibiscus petals sourced from Madurai (Tamil Nadu); Natural Wild Shikakai pods from Central Indian Forests.",
        "extraction": "Aqueous botanical boiling and natural surfactant concentration.",
        "rating": 4.7,
        "reviews_count": 82,
        "badge": "Sulfate-Free",
        "status": "active"
    },
    {
        "id": 5, 
        "name": "Rose Water Hydrating Toner", 
        "category": "Skin Care", 
        "price": 299, 
        "stock": 60, 
        "image": "https://images.unsplash.com/photo-1608248597359-994c6aa39a62?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Pure steam-distilled Kannauj rose water that tightens pores, balances skin pH, and gives an instant refreshing boost.",
        "ingredients": "Rosa Damascena Flower Water, Witch Hazel Extract",
        "geography": "100% Hydro-distilled Damask Roses from Kannauj (Uttar Pradesh - 'The Perfume Capital of India').",
        "extraction": "Traditional copper vessel steam distillation (Deg & Bhapka method).",
        "rating": 4.9,
        "reviews_count": 142,
        "badge": "Pure & Natural",
        "status": "active"
    },
    {
        "id": 6, 
        "name": "Amla & Rosemary Scalp Nourishment Oil", 
        "category": "Oil", 
        "price": 549, 
        "stock": 35, 
        "image": "https://images.unsplash.com/photo-1608248597359-994c6aa39a62?auto=format&fit=crop&w=500&q=80", 
        "video": "",
        "desc": "Advanced botanical scalp therapy with organic rosemary essential oil and vitamin-c rich amla to combat dandruff and soothe irritation.",
        "ingredients": "Rosmarinus Officinalis (Rosemary) Oil, Emblica Officinalis (Amla), Almond Oil",
        "geography": "Wild Forest Amla from Himachal Pradesh foothills; Organic Rosemary oil steam-distilled in Nilgiri Hills (Tamil Nadu).",
        "extraction": "Steam distillation and cold-pressed base oil blending.",
        "rating": 4.8,
        "reviews_count": 76,
        "badge": "New Launch",
        "status": "active"
    }
]

ORDERS = []

# --- DDOS THROTTLING & SECURITY MIDDLEWARE ---
@app.before_request
def security_and_ddos_guard():
    client_ip = request.remote_addr
    if client_ip in BLACKLISTED_IPS:
        return jsonify({"error": "Your IP address has been blacklisted by administrator due to policy violations."}), 403

    now = time.time()
    timestamps = IP_REQUESTS[client_ip]
    IP_REQUESTS[client_ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]

    if len(IP_REQUESTS[client_ip]) >= MAX_REQUESTS_PER_WINDOW:
        return jsonify({"error": "DDoS Guard Active: Too many requests. Please try again in a minute."}), 429

    IP_REQUESTS[client_ip].append(now)

@app.after_request
def inject_security_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# --- QR CODE GENERATOR UTILITY ---
def get_qr_code_bytes(data_url):
    try:
        qr_api_url = f"https://quickchart.io/qr?text={urllib.parse.quote(data_url)}&size=150"
        req = urllib.request.Request(qr_api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read()
    except Exception as e:
        print(f"QR API Error: {e}")
        return None

# --- PDF INVOICE GENERATOR ---
def generate_order_pdf(order_data, order_id, qr_target_url):
    if not REPORTLAB_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#1b4332'), spaceAfter=4)
    subtitle_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#d4a373'), spaceAfter=15)
    section_heading = ParagraphStyle('SecHead', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1b4332'), spaceBefore=10, spaceAfter=8)
    normal_text = ParagraphStyle('NormText', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#333333'))
    bold_text = ParagraphStyle('BoldText', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=13, textColor=colors.HexColor('#1b4332'))

    story = []

    # Header Row with Logo (Left) and Title (Right)
    logo_image_bytes = None
    try:
        req = urllib.request.Request(SETTINGS['logo'], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            logo_image_bytes = io.BytesIO(resp.read())
    except Exception as e:
        print(f"Logo download skipped: {e}")

    header_table_data = []
    if logo_image_bytes:
        logo_img = RLImage(logo_image_bytes, width=50, height=50)
        header_table_data = [[
            logo_img,
            [Paragraph("THE ADORICA BOTANICALS", title_style), Paragraph("Pure Botanical Remedies & Sourcing Certificate", subtitle_style)]
        ]]
    else:
        header_table_data = [[
            "",
            [Paragraph("THE ADORICA BOTANICALS", title_style), Paragraph("Pure Botanical Remedies & Sourcing Certificate", subtitle_style)]
        ]]

    header_table = Table(header_table_data, colWidths=[60, 480])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#F3EFEA'), spaceAfter=15))

    # Customer & Order Information
    cust_info_html = f"""
    <b>Customer Name:</b> {order_data.get('name')}<br/>
    <b>Email:</b> {order_data.get('email')}<br/>
    <b>Phone Number:</b> {order_data.get('phone')}<br/>
    <b>Shipping Address:</b> {order_data.get('full_address')}
    """

    order_info_html = f"""
    <b>Order Reference ID:</b> {order_id}<br/>
    <b>Order Date:</b> {order_data.get('date')}<br/>
    <b>Payment Status:</b> {order_data.get('payment_type')}<br/>
    <b>Verification:</b> Verified Authentic
    """

    details_table_data = [
        [Paragraph("<b>CUSTOMER INFORMATION</b>", section_heading), Paragraph("<b>ORDER DETAILS</b>", section_heading)],
        [Paragraph(cust_info_html, normal_text), Paragraph(order_info_html, normal_text)]
    ]

    details_table = Table(details_table_data, colWidths=[270, 270])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAF7F0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 15))

    # Ordered Items Table
    items_table_data = [
        [Paragraph("Item Description", bold_text), Paragraph("Qty", bold_text), Paragraph("Unit Price", bold_text), Paragraph("Total", bold_text)]
    ]

    for item in order_data.get('items', []):
        qty = item.get('quantity', 1)
        price = item.get('price', 0)
        items_table_data.append([
            Paragraph(f"<b>{item.get('name')}</b>", normal_text),
            Paragraph(str(qty), normal_text),
            Paragraph(f"₹{price}", normal_text),
            Paragraph(f"₹{price * qty}", normal_text)
        ])

    items_table_data.append([
        Paragraph("<b>Total Amount Paid (Inc. GST)</b>", bold_text), "", "", Paragraph(f"<b>₹{order_data.get('amount')}</b>", bold_text)
    ])

    items_table = Table(items_table_data, colWidths=[280, 50, 100, 110])
    items_table.setStyle(TableStyle([
        ('HEADERBACKGROUND', (0,0), (-1,0), colors.HexColor('#1b4332')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#CBD5E1')),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, colors.HexColor('#1b4332')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F3EFEA')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 20))

    # Bottom QR Code Row
    qr_bytes = get_qr_code_bytes(qr_target_url)
    qr_img_flowable = ""
    if qr_bytes:
        qr_img_flowable = RLImage(io.BytesIO(qr_bytes), width=90, height=90)

    qr_text_html = """
    <b style="color:#1b4332; font-size:11px;">SCAN QR CODE FOR BOTANICAL PRODUCT ORIGIN & HISTORY</b><br/>
    <span style="font-size:8.5px; color:#555; leading:11px;">
    Scan this code with your mobile camera to view your dedicated product history & sourcing certificate.
    Displays harvest locations, extraction techniques, and formula details exclusively for your ordered items.
    </span>
    """

    qr_table_data = [[
        Paragraph(qr_text_html, normal_text),
        qr_img_flowable
    ]]

    qr_table = Table(qr_table_data, colWidths=[420, 120])
    qr_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAF7F0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D4A373')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (1,0), (1,0), 'RIGHT')
    ]))

    story.append(qr_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# --- ASYNCHRONOUS EMAIL SENDER FUNCTIONS ---
def _send_email_thread(msg_obj, recipient_email):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASS)
        server.sendmail(SMTP_EMAIL, recipient_email, msg_obj.as_string())
        server.quit()
    except Exception as e:
        print(f"Async email error: {e}")

def trigger_async_email(msg_obj, recipient_email):
    t = threading.Thread(target=_send_email_thread, args=(msg_obj, recipient_email))
    t.daemon = True
    t.start()

# 1. ORDER CONFIRMATION EMAIL WITH PDF ATTACHMENT
def send_order_email(recipient_email, name, order_id, amount, items, full_address, order_data):
    try:
        qr_target_url = f"http://127.0.0.1:5644/order_history/{order_id}"

        msg = MIMEMultipart('mixed')
        msg['Subject'] = f"Order Confirmed & Invoice PDF: {order_id} - THE ADORICA BOTANICALS"
        msg['From'] = f"THE ADORICA BOTANICALS <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> (Qty: {i.get('quantity', 1)}) - ₹{i['price']}</li>" for i in items])

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 26px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">THE ADORICA BOTANICALS</h1>
                <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">Pure Botanical Remedies</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <div style="background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%); color: white; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px;">
                    <h2 style="margin: 0 0 10px 0; font-size: 24px;">Thank you for ordering, {name}!</h2>
                    <p style="margin: 0; font-size: 14px; opacity: 0.9;">Your botanical order has been successfully placed.</p>
                    <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 10px; margin-top: 15px;">
                        <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Order Reference ID</span>
                        <h3 style="margin: 5px 0 0 0; font-size: 26px; font-family: monospace; letter-spacing: 2px;">{order_id}</h3>
                    </div>
                </div>

                <p style="font-size: 14px; color: #555; line-height: 1.6;">We have attached your official <b>PDF Invoice & Botanical Sourcing Certificate</b> to this email. You can scan the QR code on the PDF to view the origin history of your items.</p>
                
                <div style="background: #F3EFEA; padding: 15px 20px; border-radius: 12px; margin: 20px 0; border: 1px dashed #d4a373;">
                    <p style="margin: 5px 0; color: #333; font-size: 14px;"><b>Total Amount Paid:</b> ₹{amount}</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;"><b>Shipping Address:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 35px;">
                    <a href="{qr_target_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 35px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block;">View Product History & Sourcing</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact support at {SMTP_EMAIL}</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))

        # GENERATE AND ATTACH PDF
        pdf_bytes = generate_order_pdf(order_data, order_id, qr_target_url)
        if pdf_bytes:
            part = MIMEApplication(pdf_bytes, Name=f"Invoice_{order_id}.pdf")
            part['Content-Disposition'] = f'attachment; filename="Invoice_{order_id}.pdf"'
            msg.attach(part)

        trigger_async_email(msg, recipient_email)
    except Exception as e:
        print(f"Email compilation skipped/failed: {e}")

# 2. ORDER REJECTION / REFUND ALERT EMAIL
def send_rejection_email(recipient_email, name, order_id, amount):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Cancelled & Refund Initiated: {order_id} - THE ADORICA BOTANICALS"
        msg['From'] = f"THE ADORICA BOTANICALS <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 24px; color: #991b1b; margin-bottom: 5px; font-weight: bold; text-align: center;">Order Cancellation Alert</h1>
                <p style="letter-spacing: 2px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">THE ADORICA BOTANICALS</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <p style="font-size: 15px; color: #333;">Dear <b>{name}</b>,</p>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">We regret to inform you that your order reference ID <b style="font-family:monospace; color:#1b4332;">{order_id}</b> could not be accepted and has been cancelled by our fulfillment team.</p>
                
                <div style="background: #fee2e2; border: 1.5px solid #ef4444; color: #991b1b; padding: 20px; border-radius: 12px; margin: 25px 0;">
                    <h3 style="margin: 0 0 8px 0; font-size: 16px;"><i class="fa-solid fa-clock-rotate-left"></i> Automatic Refund Processing</h3>
                    <p style="margin: 0; font-size: 13.5px; line-height: 1.5;">
                        If you paid online via Razorpay, your payment of <b>₹{amount}</b> will be automatically refunded back to your original payment method within <b>2 to 3 business days</b>.
                    </p>
                </div>

                <p style="font-size: 13px; color: #666; line-height: 1.5;">We apologize for any inconvenience caused. If you have questions regarding your refund, please feel free to reach out to our team.</p>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact support at {SMTP_EMAIL}</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))
        trigger_async_email(msg, recipient_email)
    except Exception as e:
        print(f"Rejection email failed: {e}")

# 3. ORDER STATUS UPDATE EMAIL
def send_status_update_email(recipient_email, name, order_id, status_text):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Shipment Alert: {order_id} is now {status_text} - THE ADORICA BOTANICALS"
        msg['From'] = f"THE ADORICA BOTANICALS <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        track_url = f"http://127.0.0.1:5644/order_success/{order_id}"

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 24px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">Order Status Update</h1>
                <p style="letter-spacing: 2px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">THE ADORICA BOTANICALS</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <p style="font-size: 15px; color: #333;">Dear <b>{name}</b>,</p>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">Your order <b style="font-family:monospace; color:#1b4332;">{order_id}</b> has been updated!</p>
                
                <div style="background: #f0fdf4; border: 1.5px solid #22c55e; color: #166534; padding: 20px; border-radius: 12px; margin: 20px 0; text-align: center;">
                    <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Current Order Status</span>
                    <h2 style="margin: 5px 0 0 0; font-size: 24px; color: #166534;">{status_text}</h2>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 35px; border-radius: 30px; font-weight: bold; font-size: 14px; display: inline-block;">Track Live Shipment Status</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact support at {SMTP_EMAIL}</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))
        trigger_async_email(msg, recipient_email)
    except Exception as e:
        print(f"Status email failed: {e}")


# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    active_products = [p for p in PRODUCTS if p.get('status', 'active') == 'active']
    return render_template_string(TEMPLATE, products=active_products, settings=SETTINGS, slides=SLIDES)

@app.route('/product/<int:prod_id>')
def product_detail(prod_id):
    product = next((p for p in PRODUCTS if p['id'] == prod_id), None)
    if not product:
        return "Product not found", 404
    return render_template_string(PRODUCT_DETAIL_TEMPLATE, product=product, settings=SETTINGS)

# --- RAZORPAY PAYMENT ENDPOINT ---
@app.route('/create_razorpay_order', methods=['POST'])
def create_razorpay_order():
    try:
        data = request.get_json() or {}
        amount_in_rupees = float(data.get('amount', 0))
        amount_in_paise = int(round(amount_in_rupees * 100))

        if amount_in_paise <= 0:
            return jsonify({"status": "error", "message": "Invalid amount for order creation"}), 400

        url = "https://api.razorpay.com/v1/orders"
        payload = json.dumps({
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": f"rcpt_{random.randint(10000, 99999)}"
        }).encode('utf-8')

        auth_str = f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

        req = urllib.request.Request(url, data=payload, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Basic {b64_auth}'
        })

        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return jsonify({
                "status": "success",
                "razorpay_order_id": res_data['id'],
                "amount": res_data['amount'],
                "key_id": RAZORPAY_KEY_ID
            })
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        return jsonify({"status": "error", "message": f"Razorpay API Error: {err_msg}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- PLACE ORDER ROUTE ---
@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        data = request.get_json()
        payment_mode = data.get('payment_mode', 'online')

        if payment_mode == 'online':
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_signature = data.get('razorpay_signature')

            if not (razorpay_order_id and razorpay_payment_id and razorpay_signature):
                return jsonify({"status": "error", "message": "Missing Razorpay payment parameters."}), 400

            msg = f"{razorpay_order_id}|{razorpay_payment_id}"
            generated_signature = hmac.new(
                RAZORPAY_KEY_SECRET.encode('utf-8'),
                msg.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            if generated_signature != razorpay_signature:
                return jsonify({"status": "error", "message": "Razorpay payment verification failed! Invalid signature."}), 400

            data['payment_type'] = f"Online Paid (Razorpay ID: {razorpay_payment_id})"
        else:
            data['payment_type'] = "Cash on Delivery (COD)"

        order_id = "ADOR-" + str(random.randint(10000, 99999))
        data['order_id'] = order_id
        data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
        data['client_ip'] = request.remote_addr
        data['status_step'] = 1
        data['status_text'] = "Order Placed"
        data['acceptance_status'] = "Accepted"  # Default status

        full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
        data['full_address'] = full_address

        # ENRICH ORDER ITEMS WITH BOTANICAL GEOGRAPHY INFO
        enriched_items = []
        for item in data.get('items', []):
            match_prod = next((p for p in PRODUCTS if p['id'] == item.get('id')), None)
            item_copy = dict(item)
            if match_prod:
                item_copy['geography'] = match_prod.get('geography', 'Sourced from certified organic Indian botanical reserves.')
                item_copy['extraction'] = match_prod.get('extraction', 'Ethically cold-pressed and steam-distilled.')
                item_copy['ingredients'] = match_prod.get('ingredients', '')
            enriched_items.append(item_copy)
        data['items'] = enriched_items

        ORDERS.append(data)

        # FAST ASYNCHRONOUS EMAIL SENDING WITH PDF
        send_order_email(data['email'], data['name'], order_id, data['amount'], data['items'], full_address, data)

        return jsonify({"status": "success", "order_id": order_id, "date": data['date']})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, settings=SETTINGS)

# --- DEDICATED QR CODE SCANNED PRODUCT HISTORY PAGE ---
@app.route('/order_history/<order_id>')
def order_product_history_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    if not order:
        return "Order / Product Authenticity Record Not Found", 404
    return render_template_string(PRODUCT_HISTORY_TEMPLATE, order=order, settings=SETTINGS)

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
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, settings=SETTINGS, slides=SLIDES)

@app.route('/api/admin/update_status', methods=['POST'])
def admin_update_status():
    data = request.get_json()
    order_id = data.get('order_id')
    step = int(data.get('step', 1))
    status_map = {1: "Order Placed", 2: "Packaging", 3: "Shipped", 4: "Delivered"}
    
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status_step'] = step
            new_text = status_map.get(step, "Processing")
            o['status_text'] = new_text
            # Trigger instant status alert email to customer
            send_status_update_email(o['email'], o['name'], o['order_id'], new_text)
    return jsonify({"success": True})

@app.route('/api/admin/accept_order', methods=['POST'])
def admin_accept_order():
    data = request.get_json()
    order_id = data.get('order_id')
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['acceptance_status'] = "Accepted"
    return jsonify({"success": True})

@app.route('/api/admin/reject_order', methods=['POST'])
def admin_reject_order():
    data = request.get_json()
    order_id = data.get('order_id')
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['acceptance_status'] = "Rejected"
            o['status_text'] = "Order Rejected & Refunded"
            # Send instant cancellation & 2-3 day refund email alert
            send_rejection_email(o['email'], o['name'], o['order_id'], o['amount'])
    return jsonify({"success": True})

@app.route('/api/admin/add_product', methods=['POST'])
def admin_add_product():
    name = request.form.get('name')
    category = request.form.get('category')
    price = float(request.form.get('price', 0))
    stock = int(request.form.get('stock', 0))
    desc = request.form.get('desc', '')
    ingredients = request.form.get('ingredients', '')
    geography = request.form.get('geography', 'Organically sourced from indigenous Indian herb fields.')
    extraction = request.form.get('extraction', 'Cold pressed & hydro-distilled.')
    
    image_file = request.files.get('image_file')
    if image_file and image_file.filename != '':
        img_bytes = image_file.read()
        image_b64 = f"data:{image_file.content_type};base64,{base64.b64encode(img_bytes).decode('utf-8')}"
    else:
        image_b64 = "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80"

    video_file = request.files.get('video_file')
    video_b64 = ""
    if video_file and video_file.filename != '':
        vid_bytes = video_file.read()
        video_b64 = f"data:{video_file.content_type};base64,{base64.b64encode(vid_bytes).decode('utf-8')}"

    new_id = max([p['id'] for p in PRODUCTS], default=0) + 1
    new_prod = {
        "id": new_id,
        "name": name,
        "category": category,
        "price": price,
        "stock": stock,
        "image": image_b64,
        "video": video_b64,
        "desc": desc,
        "ingredients": ingredients,
        "geography": geography,
        "extraction": extraction,
        "rating": 5.0,
        "reviews_count": 1,
        "badge": "New",
        "status": "active"
    }
    PRODUCTS.append(new_prod)
    return redirect('/admin')

@app.route('/api/admin/add_slide', methods=['POST'])
def admin_add_slide():
    title = request.form.get('title')
    badge = request.form.get('badge')
    desc = request.form.get('desc')
    
    image_file = request.files.get('image_file')
    image_b64 = ""
    if image_file:
        img_bytes = image_file.read()
        image_b64 = f"data:{image_file.content_type};base64,{base64.b64encode(img_bytes).decode('utf-8')}"

    video_file = request.files.get('video_file')
    video_b64 = ""
    if video_file and video_file.filename != '':
        vid_bytes = video_file.read()
        video_b64 = f"data:{video_file.content_type};base64,{base64.b64encode(vid_bytes).decode('utf-8')}"

    new_id = max([s['id'] for s in SLIDES], default=0) + 1
    SLIDES.append({
        "id": new_id,
        "title": title,
        "badge": badge,
        "desc": desc,
        "image": image_b64,
        "video": video_b64
    })
    return redirect('/admin')

@app.route('/api/admin/delete_slide', methods=['POST'])
def admin_delete_slide():
    data = request.get_json()
    slide_id = int(data.get('id'))
    global SLIDES
    SLIDES = [s for s in SLIDES if s['id'] != slide_id]
    return jsonify({"success": True})

@app.route('/api/admin/edit_product', methods=['POST'])
def admin_edit_product():
    data = request.get_json()
    prod_id = int(data.get('id'))
    for p in PRODUCTS:
        if p['id'] == prod_id:
            p['name'] = data.get('name', p['name'])
            p['price'] = float(data.get('price', p['price']))
            p['stock'] = int(data.get('stock', p['stock']))
            p['desc'] = data.get('desc', p['desc'])
            p['status'] = data.get('status', p['status'])
    return jsonify({"success": True})

@app.route('/api/admin/delete_product', methods=['POST'])
def admin_delete_product():
    data = request.get_json()
    prod_id = int(data.get('id'))
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
    return jsonify({"success": True})

@app.route('/api/admin/update_logo', methods=['POST'])
def admin_update_logo():
    logo_file = request.files.get('logo_file')
    if logo_file and logo_file.filename != '':
        logo_bytes = logo_file.read()
        logo_b64 = f"data:{logo_file.content_type};base64,{base64.b64encode(logo_bytes).decode('utf-8')}"
        SETTINGS['logo'] = logo_b64
    return redirect('/admin')


# --- TEMPLATES ---
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>THE ADORICA BOTANICALS | Pure Herbal & Botanical Solutions</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- RAZORPAY CHECKOUT SDK -->
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
        .logo { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700; color: var(--green-primary); letter-spacing: 0.5px; text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        .cart-icon-container { position: relative; cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%; transition: 0.2s; }
        .cart-icon-container:hover { background: #e8e2d5; }
        .cart-badge { position: absolute; top: -5px; right: -5px; background: var(--green-light); color: white; font-size: 11px; font-weight: 600; padding: 2px 7px; border-radius: 50%; }

        #toast { position: fixed; bottom: 30px; right: 30px; background: var(--green-primary); color: white; padding: 14px 24px; border-radius: 12px; box-shadow: var(--shadow); z-index: 9999; display: flex; align-items: center; gap: 12px; transform: translateY(120px); transition: transform 0.4s ease; font-size: 14px; font-weight: 500; }
        #toast.show { transform: translateY(0); }

        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px); z-index: 1500; opacity: 0; visibility: hidden; transition: opacity 0.4s ease, visibility 0.4s ease; }
        .sidebar-overlay.active { opacity: 1; visibility: visible; }
        .sidebar { position: fixed; top: 0; left: -380px; width: 340px; height: 100%; background: white; box-shadow: var(--shadow); z-index: 2000; transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1); padding: 30px 20px; overflow-y: auto; }
        .sidebar.active { transform: translateX(380px); }
        .sidebar h3 { color: var(--green-primary); margin-bottom: 15px; font-size: 18px; }
        .sidebar button.menu-item { width: 100%; padding: 14px; background: #f8f9fa; color: var(--green-primary); border: 1px solid #eee; border-radius: 8px; cursor: pointer; font-weight: 600; text-align: left; font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .sidebar button.menu-item:hover { background: var(--cream-dark); }
        .sidebar button.menu-item i { color: var(--accent-gold); width: 20px; }
        .sidebar button.btn-back { background: #555; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; margin-bottom: 20px; }
        .close-sidebar { font-size: 26px; cursor: pointer; float: right; color: var(--text-dark); transition: 0.2s; }
        .close-sidebar:hover { color: var(--green-primary); transform: rotate(90deg); }
        .sidebar input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 8px; outline: none; }
        .sidebar button.action-btn { width: 100%; padding: 12px; background: var(--green-primary); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .support-card { background: var(--cream-dark); padding: 15px; border-radius: 10px; margin-bottom: 12px; display: flex; align-items: center; gap: 15px; text-decoration: none; color: var(--text-dark); }

        .hero-slider { position: relative; height: 500px; margin-top: 70px; overflow: hidden; background: #2b2b2b; }
        .slider-container { width: 100%; height: 100%; position: relative; }
        .slide { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; transition: opacity 0.8s ease-in-out; background-size: cover; background-position: center; display: flex; align-items: center; padding: 0 8%; }
        .slide.active { opacity: 1; z-index: 2; }
        .slide::before { content: ''; position: absolute; top:0; left:0; width:100%; height:100%; background: linear-gradient(90deg, rgba(27,67,50,0.85) 0%, rgba(27,67,50,0.4) 60%, rgba(0,0,0,0.1) 100%); z-index: 1; }
        .slide video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }
        .slide-content { position: relative; z-index: 3; max-width: 550px; color: white; animation: slideUpContent 0.8s ease forwards; }
        @keyframes slideUpContent { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        .slide-badge { display: inline-block; background: var(--accent-gold); color: white; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 5px 14px; border-radius: 20px; margin-bottom: 15px; letter-spacing: 1px; }
        .slide-content h2 { font-family: 'Playfair Display', serif; font-size: clamp(32px, 5vw, 48px); margin-bottom: 12px; line-height: 1.2; }
        .slide-content p { font-size: 15px; margin-bottom: 25px; opacity: 0.9; line-height: 1.6; }
        
        .slider-btn { position: absolute; top: 50%; transform: translateY(-50%); background: rgba(250,247,240,0.85); border: none; width: 45px; height: 45px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; color: var(--green-primary); font-size: 16px; z-index: 10; transition: 0.3s; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .slider-btn:hover { background: white; transform: translateY(-50%) scale(1.1); }
        .prev-btn { left: 20px; }
        .next-btn { right: 20px; }
        
        .slider-dots { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; z-index: 10; }
        .dot { width: 35px; height: 5px; background: rgba(255,255,255,0.4); border-radius: 3px; cursor: pointer; transition: 0.3s; }
        .dot.active { width: 50px; background: white; }

        .btn-primary { background: var(--green-primary); color: white; padding: 14px 38px; border-radius: 35px; text-decoration: none; font-weight: 600; border: none; cursor: pointer; display: inline-block; transition: 0.3s; }
        .slide-content .btn-primary { background: white; color: var(--green-primary); }
        .slide-content .btn-primary:hover { background: var(--accent-gold); color: white; transform: translateY(-2px); }

        .features-banner { background: var(--green-primary); color: white; display: flex; justify-content: space-around; padding: 25px; flex-wrap: wrap; gap: 20px; }
        .feature-item { display: flex; align-items: center; gap: 12px; font-size: 14px; font-weight: 500; }

        .container { max-width: 1200px; margin: 0 auto; padding: 50px 20px; }
        
        .filter-sort-bar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; margin-bottom: 35px; background: white; padding: 18px 25px; border-radius: 16px; box-shadow: 0 5px 20px rgba(0,0,0,0.03); }
        .category-tabs { display: flex; flex-wrap: wrap; gap: 10px; }
        .cat-tab { padding: 9px 20px; border-radius: 25px; border: 1px solid #ddd; background: #f9f9f9; color: var(--text-dark); font-size: 13px; font-weight: 500; cursor: pointer; transition: 0.3s; }
        .cat-tab:hover, .cat-tab.active { background: var(--green-primary); color: white; border-color: var(--green-primary); }
        
        .sort-dropdown-container select { padding: 10px 18px; border-radius: 20px; border: 1px solid #ddd; background: #f9f9f9; font-size: 13px; color: var(--text-dark); outline: none; cursor: pointer; font-weight: 500; }

        .product-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 30px; }
        .product-card { background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); transition: 0.3s; position: relative; display: flex; flex-direction: column; justify-content: space-between; }
        .product-card:hover { transform: translateY(-6px); box-shadow: 0 20px 40px rgba(27, 67, 50, 0.12); }
        
        .product-badge { position: absolute; top: 15px; left: 15px; background: var(--accent-gold); color: white; font-size: 11px; font-weight: 600; padding: 4px 12px; border-radius: 20px; z-index: 2; text-transform: uppercase; letter-spacing: 0.5px; }

        .product-media-container { height: 250px; overflow: hidden; background: #f7f5f0; position: relative; cursor: pointer; }
        .product-media-container img, .product-media-container video { width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s ease; }
        .product-card:hover .product-media-container img { transform: scale(1.05); }

        .product-info { padding: 22px; flex: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-rating { display: flex; align-items: center; gap: 5px; font-size: 12px; color: #f59e0b; margin-bottom: 8px; }
        .product-rating span { color: #666; margin-left: 5px; }

        .price-row { display: flex; justify-content: space-between; align-items: center; margin: 15px 0; }
        .price { font-size: 22px; font-weight: 700; color: var(--green-light); }
        .btn-group { display: flex; gap: 10px; }
        .btn-cart { flex: 1; padding: 11px; background: var(--cream-dark); color: var(--green-primary); border: none; border-radius: 10px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-cart:hover { background: #e5dfd5; }
        .btn-buy { flex: 1; padding: 11px; background: var(--green-primary); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; transition: 0.2s; }
        .btn-buy:hover { background: var(--green-light); }

        .fly-item { position: fixed; z-index: 9999; width: 50px; height: 50px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); transition: all 0.8s cubic-bezier(0.2, 1, 0.3, 1); pointer-events: none; }

        .testimonials-section { background: #f3efea; padding: 70px 20px; margin-top: 60px; text-align: center; }
        .testimonials-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; max-width: 1200px; margin: 40px auto 0; }
        .testimonial-card { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.03); text-align: left; position: relative; }
        .testimonial-card p { font-size: 14px; color: #555; line-height: 1.7; margin-bottom: 20px; font-style: italic; }
        .client-info { display: flex; align-items: center; gap: 15px; }
        .client-avatar { width: 45px; height: 45px; border-radius: 50%; object-fit: cover; background: var(--accent-gold); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; }

        .modal { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(8px); display: none; justify-content: center; align-items: center; z-index: 3000; padding: 15px; }
        .modal-content { background: #ffffff; width: 100%; max-width: 580px; padding: 32px; border-radius: 24px; max-height: 92vh; overflow-y: auto; position: relative; box-shadow: 0 25px 60px rgba(0,0,0,0.2); }
        
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .full-width { grid-column: span 2; }
        .checkout-form input, .checkout-form select, .checkout-form textarea { width: 100%; padding: 13px 16px; margin-bottom: 4px; border: 1.5px solid #e2e8f0; border-radius: 12px; outline: none; font-size: 13.5px; transition: 0.2s; background: #f8fafc; }
        .checkout-form input:focus, .checkout-form select:focus, .checkout-form textarea:focus { border-color: var(--green-primary); background: #fff; box-shadow: 0 0 0 4px rgba(27,67,50,0.08); }

        .saved-addr-btn { background: #f0fdf4; color: #166534; border: 1.5px dashed #22c55e; padding: 12px 16px; border-radius: 12px; cursor: pointer; font-size: 13px; font-weight: 600; width: 100%; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 10px; transition: 0.2s; }
        .saved-addr-btn:hover { background: #dcfce7; }

        .better-together-container { margin-top: 24px; border-top: 1px solid #f1f5f9; padding-top: 18px; }
        .better-together-title { font-size: 16px; font-weight: 700; color: var(--green-primary); margin-bottom: 14px; font-family: 'Playfair Display', serif; }
        .bt-scroll { display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: thin; }
        .bt-card { min-width: 195px; background: #fff; border: 1.5px solid #f1f5f9; border-radius: 16px; padding: 12px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 6px 20px rgba(0,0,0,0.03); transition: 0.2s; }
        .bt-card:hover { border-color: var(--accent-gold); transform: translateY(-2px); }
        .bt-card img { width: 100%; height: 95px; object-fit: cover; border-radius: 10px; margin-bottom: 10px; }
        .bt-card h5 { font-size: 12.5px; color: var(--text-dark); margin-bottom: 6px; line-height: 1.35; font-weight: 600; }
        .bt-card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
        .bt-price { font-weight: 700; font-size: 14px; color: var(--green-light); }
        .bt-add-btn { background: #f8fafc; color: var(--green-primary); border: 1.5px solid var(--green-primary); padding: 6px 14px; border-radius: 10px; font-size: 11.5px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .bt-add-btn:hover { background: var(--green-primary); color: white; }

        .payment-options-group { display: flex; flex-direction: column; gap: 10px; margin: 16px 0 20px 0; }
        .payment-card { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border: 1.5px solid #e2e8f0; border-radius: 14px; cursor: pointer; background: #fafaf9; transition: 0.2s; }
        .payment-card:hover { border-color: #cbd5e1; background: #f8fafc; }
        .payment-card.selected { border-color: var(--green-primary); background: #f0fdf4; box-shadow: 0 4px 15px rgba(27,67,50,0.06); }
        .payment-card-left { display: flex; align-items: center; gap: 12px; font-size: 13.5px; font-weight: 500; color: var(--text-dark); }
        .payment-card input[type="radio"] { accent-color: var(--green-primary); width: 18px; height: 18px; cursor: pointer; }
        .payment-fee-badge { font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 8px; }
        .fee-online { background: #dcfce7; color: #166534; }
        .fee-cod { background: #fee2e2; color: #991b1b; }

        .coupon-box { display: flex; gap: 10px; margin-top: 15px; }
        .coupon-box input { flex: 1; padding: 11px 14px; border: 1.5px solid #e2e8f0; border-radius: 12px; outline: none; font-size: 13px; background: #f8fafc; }
        .btn-apply { background: #334155; color: white; border: none; padding: 0 20px; border-radius: 12px; font-weight: 600; font-size: 13px; cursor: pointer; transition: 0.2s; }
        .btn-apply:hover { background: #1e293b; }

        .bill-summary { background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 16px; padding: 20px; margin: 18px 0; font-size: 13.5px; }
        .bill-row { display: flex; justify-content: space-between; margin-bottom: 9px; color: #475569; }
        .bill-row.total { border-top: 1.5px dashed #cbd5e1; padding-top: 12px; margin-top: 10px; font-weight: 700; font-size: 17px; color: var(--green-primary); }

        .main-footer { background-color: var(--green-primary); color: white; padding: 60px 30px 20px; margin-top: 60px; }
        .footer-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 30px; max-width: 1200px; margin: 0 auto; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 40px; }
        .footer-grid h3 { color: var(--accent-gold); font-family: 'Playfair Display'; font-size: 20px; margin-bottom: 15px; }
        .footer-grid p { font-size: 14px; margin-bottom: 12px; color: #ddd; display: flex; align-items: center; gap: 10px; }
        .social-icons { margin-top: 15px; display: flex; gap: 15px; }
        .social-icons a { color: white; font-size: 18px; background: rgba(255,255,255,0.1); width: 40px; height: 40px; display: flex; justify-content: center; align-items: center; border-radius: 50%; text-decoration: none; transition: 0.2s; }
        .social-icons a:hover { background: var(--accent-gold); }
        .footer-bottom { padding-top: 25px; font-size: 12px; color: #aaa; text-align: center; }
    </style>
</head>
<body>

    <div id="toast"><i class="fa-solid fa-circle-check" style="font-size: 18px;"></i> <span id="toast-msg">Item added to your basket</span></div>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
                <img src="{{ settings.logo }}" alt="Logo" class="logo-img" id="header-logo">
                <div class="logo"><span>The</span> Adorica Botanicals</div>
            </div>
        </div>
        <div class="cart-icon-container" id="cartTarget" onclick="openCartModal()">
            <i class="fa-solid fa-shopping-basket"></i><span class="cart-badge" id="cart-count">0</span>
        </div>
    </header>

    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <span class="close-sidebar" onclick="toggleSidebar()">&times;</span>
        
        <div id="sidebar-main-view">
            <h3 style="margin-top: 10px; font-size: 20px;">Welcome</h3>
            <p style="font-size: 13px; color: #666; margin-bottom: 25px;">How can we assist your botanical journey today?</p>
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
            <h4 style="font-size: 13px; color: var(--green-primary);">1. Are your products 100% natural?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Yes, all our formulations are free from parabens, sulfates, and synthetic chemicals.</p>
            <h4 style="font-size: 13px; color: var(--green-primary);">2. What is the estimated delivery time?</h4><p style="font-size: 12px; color: #666; margin-bottom: 12px;">Standard orders arrive within 3-5 business days across India.</p>
        </div>
    </div>

    <!-- DYNAMIC HERO SLIDER -->
    <section class="hero-slider">
        <div class="slider-container" id="heroSliderContainer">
            {% for s in slides %}
            <div class="slide {% if loop.first %}active{% endif %}" style="background-image: url('{{ s.image }}');">
                {% if s.video %}
                <video src="{{ s.video }}" autoplay muted loop playsinline></video>
                {% endif %}
                <div class="slide-content">
                    {% if s.badge %}<span class="slide-badge">{{ s.badge }}</span>{% endif %}
                    <h2>{{ s.title }}</h2>
                    <p>{{ s.desc }}</p>
                    <a href="#shop" class="btn-primary">Shop Now</a>
                </div>
            </div>
            {% endfor %}
        </div>
        <button class="slider-btn prev-btn" onclick="changeSlide(-1)"><i class="fa-solid fa-chevron-left"></i></button>
        <button class="slider-btn next-btn" onclick="changeSlide(1)"><i class="fa-solid fa-chevron-right"></i></button>
        <div class="slider-dots" id="sliderDots">
            {% for s in slides %}
            <span class="dot {% if loop.first %}active{% endif %}" onclick="currentSlide({{ loop.index0 }})"></span>
            {% endfor %}
        </div>
    </section>

    <div class="features-banner">
        <div class="feature-item"><i class="fa-solid fa-leaf" style="color:var(--accent-gold); font-size: 18px;"></i> 100% Certified Organic</div>
        <div class="feature-item"><i class="fa-solid fa-truck-fast" style="color:var(--accent-gold); font-size: 18px;"></i> Express Pan-India Shipping</div>
        <div class="feature-item"><i class="fa-solid fa-shield-cat" style="color:var(--accent-gold); font-size: 18px;"></i> Cruelty-Free & Vegan</div>
        <div class="feature-item"><i class="fa-solid fa-flask" style="color:var(--accent-gold); font-size: 18px;"></i> Zero Sulfates & Parabens</div>
    </div>

    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 30px; color: var(--green-primary); margin-bottom: 10px;" class="reveal">Our Handcrafted Collections</h2>
        <p style="color: #666; font-size: 14px; margin-bottom: 25px;" class="reveal">Choose from our pure botanical range designed for your daily self-care rituals.</p>
        
        <div class="filter-sort-bar reveal">
            <div class="category-tabs">
                <button class="cat-tab active" onclick="filterCategory('All', this)">All</button>
                <button class="cat-tab" onclick="filterCategory('Hair Care', this)">Hair Care</button>
                <button class="cat-tab" onclick="filterCategory('Oil', this)">Oils</button>
                <button class="cat-tab" onclick="filterCategory('Shampoo', this)">Shampoos</button>
                <button class="cat-tab" onclick="filterCategory('Skin Care', this)">Skin Care</button>
            </div>
            <div class="sort-dropdown-container">
                <select id="sortSelect" onchange="sortProducts()">
                    <option value="">Sort By</option>
                    <option value="low-high">Price: Low to High</option>
                    <option value="high-low">Price: High to Low</option>
                    <option value="az">Name: A to Z</option>
                    <option value="za">Name: Z to A</option>
                </select>
            </div>
        </div>

        <div class="product-grid" id="productGrid">
            {% for p in products %}
            <div class="product-card reveal" data-id="{{ p.id }}" data-category="{{ p.category }}" data-name="{{ p.name }}" data-price="{{ p.price }}">
                {% if p.badge %}
                <div class="product-badge">{{ p.badge }}</div>
                {% endif %}
                <div class="product-media-container" onclick="window.location.href='/product/{{ p.id }}'">
                    {% if p.video %}
                    <video src="{{ p.video }}" autoplay muted loop playsinline id="media-{{ p.id }}"></video>
                    {% else %}
                    <img src="{{ p.image }}" alt="{{ p.name }}" id="media-{{ p.id }}">
                    {% endif %}
                </div>
                <div class="product-info">
                    <div>
                        <div class="product-rating">
                            <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star-half-stroke"></i>
                            <span>({{ p.reviews_count | default(45) }})</span>
                        </div>
                        <h3 style="color:var(--green-primary); font-size:16px; margin-bottom:6px; cursor:pointer;" onclick="window.location.href='/product/{{ p.id }}'">{{ p.name }}</h3>
                        <p style="font-size:12px; color:#666; line-height: 1.5; margin-bottom: 12px;">{{ p.desc }}</p>
                    </div>
                    <div>
                        <div class="price-row">
                            <span class="price">₹{{ p.price }}</span>
                            <span style="font-size:11px; padding:3px 10px; border-radius:6px; background:#e8f5e9; color:#2e7d32; font-weight:600;">In Stock: {{ p.stock }}</span>
                        </div>
                        <div class="btn-group">
                            <button class="btn-cart" onclick="addToCartAndFly(event, {{ p.id }})"><i class="fa-solid fa-cart-plus"></i> Add</button>
                            <button class="btn-buy" onclick="buyNow({{ p.id }})">Buy Now</button>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Testimonials Section -->
    <section class="testimonials-section">
        <h2 style="font-family: 'Playfair Display'; font-size: 28px; color: var(--green-primary); margin-bottom: 10px;">Loved by Our Botanical Community</h2>
        <p style="color: #666; font-size: 14px;">Here is what our customers have to say about their transformations.</p>
        
        <div class="testimonials-grid">
            <div class="testimonial-card">
                <div class="product-rating" style="margin-bottom: 12px;"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div>
                <p>"The Bhringraj Onion Hair Oil completely transformed my postpartum hair fall. Within 3 weeks, I noticed baby hairs sprouting. Absolute magic in a bottle!"</p>
                <div class="client-info">
                    <div class="client-avatar">SN</div>
                    <div>
                        <h4 style="font-size: 14px; color: var(--green-primary);">Sneha Nambiar</h4>
                        <span style="font-size: 11px; color: #777;">Verified Buyer</span>
                    </div>
                </div>
            </div>
            <div class="testimonial-card">
                <div class="product-rating" style="margin-bottom: 12px;"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div>
                <p>"The Saffron Kumkumadi Night Serum gave my dull skin a radiant bridal glow without making it greasy. It smells divine and feels so luxurious!"</p>
                <div class="client-info">
                    <div class="client-avatar" style="background: var(--green-light);">AP</div>
                    <div>
                        <h4 style="font-size: 14px; color: var(--green-primary);">Ananya Priyadarshini</h4>
                        <span style="font-size: 11px; color: #777;">Verified Buyer</span>
                    </div>
                </div>
            </div>
            <div class="testimonial-card">
                <div class="product-rating" style="margin-bottom: 12px;"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div>
                <p>"Finding a sulfate-free shampoo that actually lathers well and keeps my hair smooth was tough until I found the Hibiscus Shikakai cleanser."</p>
                <div class="client-info">
                    <div class="client-avatar" style="background: var(--accent-gold);">RK</div>
                    <div>
                        <h4 style="font-size: 14px; color: var(--green-primary);">Rohan Kapoor</h4>
                        <span style="font-size: 11px; color: #777;">Verified Buyer</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <footer class="main-footer">
        <div class="footer-grid">
            <div>
                <h3>THE ADORICA BOTANICALS</h3>
                <p style="font-size: 13px; line-height: 1.7; color: #ddd;">Bringing ancient botanical secrets directly into your daily routine. Pure, chemical-free, and sustainably sourced.</p>
            </div>
            <div>
                <h3>Customer Support</h3>
                <p><i class="fa-solid fa-envelope" style="color:var(--accent-gold);"></i> keshaadar@gmail.com</p>
                <p><i class="fa-solid fa-phone" style="color:var(--accent-gold);"></i> +91 9163641507</p>
                <p><i class="fa-solid fa-clock" style="color:var(--accent-gold);"></i> Mon - Sat: 9:00 AM - 7:00 PM</p>
            </div>
            <div>
                <h3>Connect With Us</h3>
                <p>Follow our green journey on social media for skincare tips and exclusive offers.</p>
                <div class="social-icons">
                    <a href="https://www.instagram.com/kesh_aadar?igsh=dG5wYWVjMm8wanN5" target="_blank"><i class="fa-brands fa-instagram"></i></a>
                    <a href="https://www.facebook.com/share/1GqaNPpsU7/" target="_blank"><i class="fa-brands fa-facebook-f"></i></a>
                </div>
            </div>
        </div>
        <div class="footer-bottom">
            &copy; 2026 The Adorica Botanicals. All Rights Reserved. Crafted with pure herbal care.
        </div>
    </footer>

    <!-- CHECKOUT MODAL -->
    <div class="modal" id="cartModal">
        <div class="modal-content">
            <span class="close-sidebar" onclick="document.getElementById('cartModal').style.display='none'" style="position:absolute; right:24px; top:24px; z-index:10; font-size:22px;">&times;</span>
            
            <div id="checkout-step-1">
                <h3 style="color:var(--green-primary); margin-bottom:16px; font-family:'Playfair Display'; font-size:22px;">Shipping Address</h3>
                <button type="button" class="saved-addr-btn" id="useSavedAddrBtn" onclick="loadSavedAddress()" style="display:none;">
                    <i class="fa-solid fa-clock-rotate-left"></i> Fill with Saved Shipping Address
                </button>
                <form class="checkout-form" id="addressForm" onsubmit="event.preventDefault(); goToCartStep();">
                    <div class="form-grid">
                        <input type="text" id="cust-name" class="full-width" placeholder="Full Name *" required>
                        <input type="email" id="cust-email" class="full-width" placeholder="Email Address (For Instant Order Updates) *" required>
                        <input type="tel" id="cust-phone" class="full-width" placeholder="10-Digit Phone Number *" required pattern="[0-9]{10}">
                        
                        <input type="text" id="cust-pincode" placeholder="PIN Code *" required pattern="[0-9]{6}" maxlength="6" onkeyup="detectPinCode(this.value)">
                        <input type="text" id="cust-city" placeholder="District / City *" required readonly style="background:#f1f5f9;">
                        <input type="text" id="cust-state" placeholder="State *" required readonly style="background:#f1f5f9;">
                        
                        <select id="cust-landmark" class="full-width">
                            <option value="">Select Landmark / Area (Optional)</option>
                        </select>
                        
                        <textarea id="cust-street" class="full-width" placeholder="House No., Flat, Street, Locality Name *" rows="2" required></textarea>
                    </div>
                    <button type="submit" class="btn-primary" style="width:100%; border-radius:14px; margin-top:14px; font-size:14.5px;">Proceed to Cart & Bill &rarr;</button>
                </form>
            </div>

            <div id="checkout-step-2" style="display:none;">
                <button class="btn-back" onclick="backToAddressStep()" style="margin-bottom:12px; padding:6px 14px; border-radius:8px; font-size:12px;"><i class="fa-solid fa-arrow-left"></i> Edit Address</button>
                <h3 style="color:var(--green-primary); margin-bottom:16px; font-family:'Playfair Display'; font-size:22px;" id="cart-modal-title">Your Cart</h3>
                
                <div id="cart-items-container"></div>

                <div class="better-together-container">
                    <div class="better-together-title">Better Together</div>
                    <div class="bt-scroll" id="betterTogetherContainer"></div>
                </div>

                <div class="coupon-box">
                    <input type="text" id="coupon-input" placeholder="Coupon Code (e.g. BOTANICAL10)">
                    <button type="button" class="btn-apply" onclick="applyCoupon()">Apply</button>
                </div>
                <div id="coupon-msg" style="font-size:12px; margin-top:6px; margin-bottom:12px; font-weight:500;"></div>

                <h4 style="margin: 18px 0 10px 0; font-size:14px; font-weight:700; color:var(--green-primary);">Select Payment Option</h4>
                
                <div class="payment-options-group">
                    <label class="payment-card selected" id="payCardOnline" onclick="selectPaymentMode('online')">
                        <div class="payment-card-left">
                            <input type="radio" name="pay_mode" value="online" checked>
                            <div>
                                <span style="font-weight:600; display:block;">Online Payment (Razorpay)</span>
                                <span style="font-size:11.5px; color:#64748b;">UPI (GPay/PhonePe), Credit/Debit Cards, NetBanking</span>
                            </div>
                        </div>
                        <span class="payment-fee-badge fee-online">+₹40 Shipping</span>
                    </label>

                    <label class="payment-card" id="payCardCod" onclick="selectPaymentMode('cod')">
                        <div class="payment-card-left">
                            <input type="radio" name="pay_mode" value="cod">
                            <div>
                                <span style="font-weight:600; display:block;">Cash on Delivery (COD)</span>
                                <span style="font-size:11.5px; color:#64748b;">Pay cash when your order arrives</span>
                            </div>
                        </div>
                        <span class="payment-fee-badge fee-cod">+₹99 Handling</span>
                    </label>
                </div>

                <div class="bill-summary">
                    <div class="bill-row"><span>Items Subtotal:</span><span id="bill-subtotal" style="font-weight:600;">₹0</span></div>
                    <div class="bill-row" id="discount-row" style="display:none; color:#166534;"><span>Discount (10% OFF):</span><span id="bill-discount" style="font-weight:600;">-₹0</span></div>
                    <div class="bill-row" id="shipping-fee-row"><span>Shipping Fee:</span><span id="shipping-fee-val" style="font-weight:600;">₹40</span></div>
                    <div class="bill-row" id="cod-fee-row" style="display:none; color:#991b1b;"><span>COD Handling Fee:</span><span style="font-weight:600;">₹99</span></div>
                    <div class="bill-row"><span>GST (Included 18%):</span><span id="bill-gst" style="font-weight:600;">₹0</span></div>
                    <div class="bill-row total"><span>Total Payable:</span><span id="bill-total">₹0</span></div>
                </div>

                <button type="button" class="btn-primary" style="width:100%; border-radius:14px; font-size:15px;" id="payBtn" onclick="placeOrder()">Confirm Order</button>
            </div>

        </div>
    </div>

    <script>
        const productsData = {{ products | tojson }};
        let cart = JSON.parse(localStorage.getItem('adorica_cart') || '[]');
        let currentCategory = 'All';
        let discountPercent = 0;

        updateCartUI();

        let currentSlideIndex = 0;
        const slides = document.querySelectorAll('.slide');
        const dots = document.querySelectorAll('.dot');
        let slideTimer = setInterval(() => { changeSlide(1); }, 5000);

        function showSlide(index) {
            if (slides.length === 0) return;
            slides.forEach(slide => slide.classList.remove('active'));
            dots.forEach(dot => dot.classList.remove('active'));
            currentSlideIndex = (index + slides.length) % slides.length;
            slides[currentSlideIndex].classList.add('active');
            dots[currentSlideIndex].classList.add('active');
        }

        function changeSlide(n) {
            showSlide(currentSlideIndex + n);
            resetSlideTimer();
        }

        function currentSlide(n) {
            showSlide(n);
            resetSlideTimer();
        }

        function resetSlideTimer() {
            clearInterval(slideTimer);
            slideTimer = setInterval(() => { changeSlide(1); }, 5000);
        }

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

        function showToast(msg) {
            let t = document.getElementById('toast');
            document.getElementById('toast-msg').innerText = msg;
            t.classList.add('show');
            setTimeout(() => { t.classList.remove('show'); }, 3000);
        }

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('active');
            document.getElementById('sidebarOverlay').classList.toggle('active');
        }
        function switchSidebarView(v) {
            ['main','track','support','faq'].forEach(id => document.getElementById('sidebar-'+id+'-view').style.display = 'none');
            document.getElementById('sidebar-'+v+'-view').style.display = 'block';
        }

        function filterCategory(category, btn) {
            currentCategory = category;
            document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            applyFilterAndSort();
        }

        function sortProducts() {
            applyFilterAndSort();
        }

        function applyFilterAndSort() {
            let grid = document.getElementById('productGrid');
            let cards = Array.from(grid.getElementsByClassName('product-card'));
            let sortVal = document.getElementById('sortSelect').value;

            cards.forEach(card => {
                let cat = card.getAttribute('data-category');
                let match = false;
                if (currentCategory === 'All') {
                    match = true;
                } else if (currentCategory === 'Hair Care') {
                    match = (cat === 'Haircare' || cat === 'Hair Care' || cat === 'Oil' || cat === 'Shampoo');
                } else {
                    match = (cat.toLowerCase() === currentCategory.toLowerCase());
                }
                card.style.display = match ? 'flex' : 'none';
            });

            let visibleCards = cards.filter(c => c.style.display !== 'none');
            visibleCards.sort((a, b) => {
                let priceA = parseFloat(a.getAttribute('data-price'));
                let priceB = parseFloat(b.getAttribute('data-price'));
                let nameA = a.getAttribute('data-name').toLowerCase();
                let nameB = b.getAttribute('data-name').toLowerCase();

                if (sortVal === 'low-high') return priceA - priceB;
                if (sortVal === 'high-low') return priceB - priceA;
                if (sortVal === 'az') return nameA.localeCompare(nameB);
                if (sortVal === 'za') return nameB.localeCompare(nameA);
                return 0;
            });

            visibleCards.forEach(card => grid.appendChild(card));
        }

        function addToCartAndFly(event, id) {
            let p = productsData.find(x => x.id === id);
            let existing = cart.find(x => x.id === id);
            if(existing) { existing.quantity = (existing.quantity || 1) + 1; }
            else { let copy = Object.assign({}, p); copy.quantity = 1; cart.push(copy); }
            
            localStorage.setItem('adorica_cart', JSON.stringify(cart));
            updateCartUI();
            showToast(`${p.name} added to your basket!`);

            let mediaEl = document.getElementById('media-' + id);
            if(mediaEl) {
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
        }

        function buyNow(id) { 
            let p = productsData.find(x => x.id === id);
            let copy = Object.assign({}, p);
            copy.quantity = 1;
            cart = [copy]; 
            localStorage.setItem('adorica_cart', JSON.stringify(cart));
            updateCartUI(); 
            openCartModal(); 
        }

        function openCartModal() { 
            document.getElementById('cartModal').style.display = 'flex'; 
            checkSavedAddressAvailability();
            showCheckoutStep(1);
            updateCartUI(); 
        }

        function showCheckoutStep(stepNum) {
            if(stepNum === 1) {
                document.getElementById('checkout-step-1').style.display = 'block';
                document.getElementById('checkout-step-2').style.display = 'none';
            } else {
                document.getElementById('checkout-step-1').style.display = 'none';
                document.getElementById('checkout-step-2').style.display = 'block';
                renderBetterTogether();
                updateTotal();
            }
        }

        function goToCartStep() {
            let name = document.getElementById('cust-name').value;
            let email = document.getElementById('cust-email').value;
            let phone = document.getElementById('cust-phone').value;
            let pincode = document.getElementById('cust-pincode').value;
            let street = document.getElementById('cust-street').value;

            if(!name || !email || !phone || !pincode || !street) {
                return alert('Please fill in all required shipping address fields.');
            }

            saveAddressToStorage();
            showCheckoutStep(2);
        }

        function backToAddressStep() {
            showCheckoutStep(1);
        }

        function selectPaymentMode(mode) {
            document.querySelectorAll('input[name="pay_mode"]').forEach(input => {
                input.checked = (input.value === mode);
            });
            document.getElementById('payCardOnline').classList.toggle('selected', mode === 'online');
            document.getElementById('payCardCod').classList.toggle('selected', mode === 'cod');
            updateTotal();
        }

        function updateCartUI() {
            let totalCount = cart.reduce((sum, item) => sum + (item.quantity || 1), 0);
            document.getElementById('cart-count').innerText = totalCount;
            if(document.getElementById('cart-modal-title')) {
                document.getElementById('cart-modal-title').innerText = `Your Cart (${totalCount} items)`;
            }
            
            let container = document.getElementById('cart-items-container');
            if(container) {
                container.innerHTML = '';
                if(cart.length === 0) {
                    container.innerHTML = '<p style="text-align:center; color:#888; margin:20px 0;">Your shopping basket is empty.</p>';
                } else {
                    cart.forEach((item, index) => { 
                        container.innerHTML += `
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid #f1f5f9; padding-bottom:12px; font-size:13.5px;">
                            <div style="display:flex; gap:12px; align-items:center;">
                                <img src="${item.image}" style="width:48px; height:48px; object-fit:cover; border-radius:10px;">
                                <div><b style="color:var(--text-dark);">${item.name}</b><br><span style="color:#64748b; font-size:12px;">₹${item.price}</span></div>
                            </div>
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="display:flex; align-items:center; border:1px solid #cbd5e1; border-radius:8px; background:#f8fafc;">
                                    <button type="button" style="border:none; background:none; padding:4px 9px; cursor:pointer; color:#334155; font-weight:bold;" onclick="changeQty(${index}, -1)">-</button>
                                    <span style="padding:0 6px; font-weight:600; font-size:12.5px; color:#1e293b;">${item.quantity || 1}</span>
                                    <button type="button" style="border:none; background:none; padding:4px 9px; cursor:pointer; color:#334155; font-weight:bold;" onclick="changeQty(${index}, 1)">+</button>
                                </div>
                                <span style="font-weight:700; color:var(--green-primary); min-width:60px; text-align:right;">₹${item.price * (item.quantity || 1)}</span>
                                <i class="fa-solid fa-trash-can" style="color:#ef4444; cursor:pointer; font-size:14px;" onclick="removeFromCart(${index})"></i>
                            </div>
                        </div>`; 
                    });
                }
            }
            if(document.getElementById('checkout-step-2') && document.getElementById('checkout-step-2').style.display === 'block') {
                updateTotal();
            }
        }

        function changeQty(index, delta) {
            cart[index].quantity = (cart[index].quantity || 1) + delta;
            if(cart[index].quantity <= 0) {
                cart.splice(index, 1);
            }
            localStorage.setItem('adorica_cart', JSON.stringify(cart));
            updateCartUI();
            showToast("Cart updated successfully");
        }

        function removeFromCart(index) {
            cart.splice(index, 1);
            localStorage.setItem('adorica_cart', JSON.stringify(cart));
            updateCartUI();
            showToast("Item removed from cart");
        }

        function renderBetterTogether() {
            let btContainer = document.getElementById('betterTogetherContainer');
            if(!btContainer) return;
            btContainer.innerHTML = '';
            
            let cartIds = cart.map(i => i.id);
            let availableCrossSells = productsData.filter(p => !cartIds.includes(p.id));

            if(availableCrossSells.length === 0) {
                btContainer.innerHTML = '<p style="font-size:12px; color:#777;">All items are already in your cart!</p>';
                return;
            }

            availableCrossSells.forEach(p => {
                btContainer.innerHTML += `
                <div class="bt-card">
                    <img src="${p.image}" alt="${p.name}">
                    <h5>${p.name}</h5>
                    <div class="bt-card-footer">
                        <span class="bt-price">₹${p.price}</span>
                        <button type="button" class="bt-add-btn" onclick="addCrossSell(${p.id})">+ Add</button>
                    </div>
                </div>`;
            });
        }

        function addCrossSell(id) {
            let p = productsData.find(x => x.id === id);
            let copy = Object.assign({}, p);
            copy.quantity = 1;
            cart.push(copy);
            localStorage.setItem('adorica_cart', JSON.stringify(cart));
            updateCartUI();
            renderBetterTogether();
            showToast(`${p.name} added instantly!`);
        }

        function applyCoupon() {
            let code = document.getElementById('coupon-input').value.trim().toUpperCase();
            let msg = document.getElementById('coupon-msg');
            if(code === 'BOTANICAL10') {
                discountPercent = 10;
                msg.style.color = '#166534';
                msg.innerHTML = '<i class="fa-solid fa-check"></i> Coupon applied: 10% OFF!';
            } else {
                discountPercent = 0;
                msg.style.color = '#991b1b';
                msg.innerHTML = '<i class="fa-solid fa-xmark"></i> Invalid coupon code.';
            }
            updateTotal();
        }

        function updateTotal() {
            let base = cart.reduce((s, i) => s + (i.price * (i.quantity || 1)), 0);
            let modeInput = document.querySelector('input[name="pay_mode"]:checked');
            let mode = modeInput ? modeInput.value : 'online';
            
            document.getElementById('bill-subtotal').innerText = `₹${base}`;
            
            let discountAmt = Math.round(base * (discountPercent / 100));
            if(discountPercent > 0) {
                document.getElementById('discount-row').style.display = 'flex';
                document.getElementById('bill-discount').innerText = `-₹${discountAmt}`;
            } else {
                document.getElementById('discount-row').style.display = 'none';
            }

            let taxable = base - discountAmt;
            let gst = Math.round(taxable * 0.18);
            document.getElementById('bill-gst').innerText = `₹${gst} (18% incl.)`;
            
            let total = taxable;
            let shippingFeeRow = document.getElementById('shipping-fee-row');
            let codFeeRow = document.getElementById('cod-fee-row');
            
            if(mode === 'online') {
                shippingFeeRow.style.display = 'flex';
                document.getElementById('shipping-fee-val').innerText = '₹40';
                codFeeRow.style.display = 'none';
                total += 40;
                document.getElementById('payBtn').innerHTML = `<i class="fa-solid fa-lock"></i> Pay ₹${total} via Razorpay`;
            } else {
                shippingFeeRow.style.display = 'none';
                codFeeRow.style.display = 'flex';
                total += 99;
                document.getElementById('payBtn').innerHTML = `<i class="fa-solid fa-truck"></i> Confirm Order (COD) - ₹${total}`;
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
                        showToast("Invalid PIN Code entered.");
                    }
                })
                .catch(() => console.log("PIN lookup unavailable"));
            }
        }

        function checkSavedAddressAvailability() {
            let saved = localStorage.getItem('adorica_saved_address');
            if(saved) { document.getElementById('useSavedAddrBtn').style.display = 'flex'; }
        }

        function saveAddressToStorage() {
            localStorage.setItem('adorica_saved_address', JSON.stringify({
                name: document.getElementById('cust-name').value, 
                email: document.getElementById('cust-email').value, 
                phone: document.getElementById('cust-phone').value,
                pincode: document.getElementById('cust-pincode').value, 
                city: document.getElementById('cust-city').value, 
                state: document.getElementById('cust-state').value,
                landmark: document.getElementById('cust-landmark').value, 
                street: document.getElementById('cust-street').value
            }));
        }

        function loadSavedAddress() {
            let saved = localStorage.getItem('adorica_saved_address');
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
                showToast("Saved address loaded successfully!");
            }
        }

        async function placeOrder() {
            let name = document.getElementById('cust-name').value;
            let email = document.getElementById('cust-email').value;
            let phone = document.getElementById('cust-phone').value;
            let pincode = document.getElementById('cust-pincode').value;
            let city = document.getElementById('cust-city').value;
            let state = document.getElementById('cust-state').value;
            let landmark = document.getElementById('cust-landmark').value;
            let street = document.getElementById('cust-street').value;
            let modeInput = document.querySelector('input[name="pay_mode"]:checked');
            let mode = modeInput ? modeInput.value : 'online';

            if(!name || !email || !phone || !pincode || !street) {
                return alert('Please fill in all required delivery fields.');
            }

            if(cart.length === 0) {
                return alert('Your cart is empty.');
            }

            let amt = updateTotal();
            saveAddressToStorage();

            let payBtn = document.getElementById('payBtn');
            payBtn.disabled = true;

            // --- OPTION 1: CASH ON DELIVERY (COD) ---
            if (mode === 'cod') {
                payBtn.innerText = "Placing COD Order...";
                let payload = {
                    name, email, phone, pincode, city, state, landmark, street,
                    amount: amt,
                    payment_mode: 'cod',
                    items: cart
                };

                try {
                    let response = await fetch('/place_order', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    let data = await response.json();
                    if (data.status === 'success') {
                        localStorage.removeItem('adorica_cart');
                        window.location.href = '/order_success/' + data.order_id;
                    } else {
                        alert("Order failed: " + data.message);
                        payBtn.disabled = false;
                        updateTotal();
                    }
                } catch (e) {
                    alert("Error placing order. Please try again.");
                    payBtn.disabled = false;
                    updateTotal();
                }
            } 
            // --- OPTION 2: ONLINE PAYMENT (RAZORPAY) ---
            else {
                payBtn.innerText = "Initializing Razorpay...";
                try {
                    let response = await fetch('/create_razorpay_order', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ amount: amt })
                    });

                    let rzData = await response.json();

                    if (rzData.status !== 'success') {
                        alert("Payment Gateway Error: " + (rzData.message || "Failed to initialize"));
                        payBtn.disabled = false;
                        updateTotal();
                        return;
                    }

                    var options = {
                        "key": rzData.key_id,
                        "amount": rzData.amount,
                        "currency": "INR",
                        "name": "THE ADORICA BOTANICALS",
                        "description": "Pure Botanical Products Purchase",
                        "image": "{{ settings.logo }}",
                        "order_id": rzData.razorpay_order_id,
                        "handler": function (rzResponse) {
                            payBtn.innerText = "Verifying Payment & Generating PDF...";
                            let payload = {
                                name, email, phone, pincode, city, state, landmark, street,
                                amount: amt,
                                payment_mode: 'online',
                                items: cart,
                                razorpay_order_id: rzResponse.razorpay_order_id,
                                razorpay_payment_id: rzResponse.razorpay_payment_id,
                                razorpay_signature: rzResponse.razorpay_signature
                            };

                            fetch('/place_order', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(payload)
                            })
                            .then(r => r.json())
                            .then(data => {
                                if (data.status === "success") {
                                    localStorage.removeItem('adorica_cart');
                                    window.location.href = '/order_success/' + data.order_id;
                                } else {
                                    alert("Payment verification failed: " + data.message);
                                    payBtn.disabled = false;
                                    updateTotal();
                                }
                            })
                            .catch(err => {
                                alert("Order placement error. Please contact customer support.");
                                payBtn.disabled = false;
                                updateTotal();
                            });
                        },
                        "prefill": {
                            "name": name,
                            "email": email,
                            "contact": phone
                        },
                        "theme": {
                            "color": "#1b4332"
                        },
                        "modal": {
                            "ondismiss": function() {
                                payBtn.disabled = false;
                                updateTotal();
                            }
                        }
                    };
                    var rzp1 = new Razorpay(options);
                    rzp1.open();

                } catch (err) {
                    alert("Failed to connect with payment server. Please try again.");
                    payBtn.disabled = false;
                    updateTotal();
                }
            }
        }

        function trackOrder() {
            let q = document.getElementById('track-input').value.trim();
            if(!q) return;
            fetch('/track_order?q=' + encodeURIComponent(q)).then(r => r.json()).then(data => {
                let d = document.getElementById('track-result');
                if(data.found) {
                    d.innerHTML = `<div style="background:#e8f5e9; padding:12px; border-radius:8px; font-size:13px;"><h4 style="color:#2e7d32;">Found: ${data.order.order_id}</h4><p>Status: <b>${data.order.status_text}</b></p><a href="/order_success/${data.order.order_id}" style="color:var(--green-primary); font-weight:600; display:inline-block; margin-top:8px;">View Full Tracking &rarr;</a></div>`;
                } else { 
                    d.innerHTML = '<p style="color:red; font-size:12px;">No order matching details found.</p>'; 
                }
            });
        }
    </script>
</body>
</html>
"""

# --- DEDICATED QR SCANNED PRODUCT HISTORY & GEOGRAPHY TEMPLATE ---
PRODUCT_HISTORY_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Botanical Origin & Sourcing Geography Certificate | THE ADORICA BOTANICALS</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; }
        * { margin:0; padding:0; box-sizing:border-box; font-family:'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); padding: 30px 15px; }

        .cert-card { max-width: 800px; margin: 0 auto; background: white; border-radius: 24px; padding: 40px; box-shadow: 0 20px 50px rgba(0,0,0,0.06); border: 2px solid var(--cream-dark); }
        .cert-header { text-align: center; border-bottom: 2px dashed #E2E8F0; padding-bottom: 25px; margin-bottom: 30px; }
        .cert-logo { width: 70px; height: 70px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); margin-bottom: 12px; }
        .cert-title { font-family: 'Playfair Display', serif; font-size: 26px; color: var(--green-primary); }
        .cert-subtitle { font-size: 12px; color: var(--accent-gold); font-weight: 700; text-transform: uppercase; letter-spacing: 2px; margin-top: 4px; }

        .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; background: #FAF7F0; padding: 20px; border-radius: 16px; margin-bottom: 30px; font-size: 13px; border: 1px solid #E2E8F0; }
        .meta-item span { color: #64748B; font-size: 11px; text-transform: uppercase; display: block; font-weight: 600; }
        .meta-item strong { color: var(--green-primary); font-size: 14px; }

        .history-section-title { font-family: 'Playfair Display', serif; font-size: 20px; color: var(--green-primary); margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }

        .prod-history-card { background: #FAF7F0; border-radius: 16px; padding: 22px; margin-bottom: 20px; border-left: 5px solid var(--green-primary); box-shadow: 0 4px 15px rgba(0,0,0,0.02); }
        .prod-history-title { font-size: 17px; color: var(--green-primary); font-weight: 700; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .geo-badge { background: #dcfce7; color: #166534; font-size: 11px; padding: 4px 10px; border-radius: 20px; font-weight: 600; }
        
        .geo-detail { font-size: 13px; color: #475569; margin-bottom: 8px; line-height: 1.6; }
        .geo-detail i { color: var(--accent-gold); width: 20px; }

        .cert-footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #94A3B8; }
    </style>
</head>
<body>

    <div class="cert-card">
        <div class="cert-header">
            <img src="{{ settings.logo }}" class="cert-logo" alt="Logo">
            <h1 class="cert-title">Botanical Origin & Sourcing Certificate</h1>
            <div class="cert-subtitle">Official Authenticity & Geographical Sourcing Record</div>
        </div>

        <div class="meta-grid">
            <div class="meta-item">
                <span>Customer Name</span>
                <strong>{{ order.name }}</strong>
            </div>
            <div class="meta-item">
                <span>Order Reference ID</span>
                <strong>{{ order.order_id }}</strong>
            </div>
            <div class="meta-item">
                <span>Date of Purchase</span>
                <strong>{{ order.date }}</strong>
            </div>
            <div class="meta-item">
                <span>Verification Status</span>
                <strong style="color: #2e7d32;"><i class="fa-solid fa-circle-check"></i> Authentic Botanical Batch</strong>
            </div>
        </div>

        <div class="history-section-title">
            <i class="fa-solid fa-seedling" style="color: var(--accent-gold);"></i> Sourced Ingredients & Product History (Your Order)
        </div>

        {% for item in order.items %}
        <div class="prod-history-card">
            <div class="prod-history-title">
                <span>{{ item.name }}</span>
                <span class="geo-badge">Quantity: {{ item.quantity | default(1) }}</span>
            </div>
            <div class="geo-detail">
                <i class="fa-solid fa-map-location-dot"></i> <b>Geographical Origin:</b> {{ item.geography | default('Sourced from organic Indian herb fields.') }}
            </div>
            <div class="geo-detail">
                <i class="fa-solid fa-flask"></i> <b>Extraction & Harvesting Technique:</b> {{ item.extraction | default('Cold-pressed & steam-distilled.') }}
            </div>
            {% if item.ingredients %}
            <div class="geo-detail">
                <i class="fa-solid fa-leaf"></i> <b>Botanical Formula:</b> {{ item.ingredients }}
            </div>
            {% endif %}
        </div>
        {% endfor %}

        <div class="cert-footer">
            <p><i class="fa-solid fa-shield-halved"></i> Verified by The Adorica Botanicals Quality Control Laboratory.</p>
            <p style="margin-top:4px;">100% Organic • Cruelty-Free • Zero Paraben Formulation</p>
        </div>
    </div>

</body>
</html>
"""

# --- PRODUCT DETAIL PAGE TEMPLATE ---
PRODUCT_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ product.name }} | THE ADORICA BOTANICALS</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; --shadow: 0 20px 40px rgba(27, 67, 50, 0.15); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); }
        
        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.05); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; text-decoration: none; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700; color: var(--green-primary); text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        
        .detail-container { max-width: 1100px; margin: 100px auto 50px; padding: 30px 20px; }
        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--green-primary); font-weight: 600; text-decoration: none; margin-bottom: 25px; font-size: 14px; transition: 0.2s; }
        .back-link:hover { color: var(--accent-gold); }
        
        .product-detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 15px 35px rgba(0,0,0,0.05); }
        @media(max-width: 768px) { .product-detail-grid { grid-template-columns: 1fr; padding: 20px; } }
        
        .product-image-box { border-radius: 16px; overflow: hidden; background: #f8fafc; height: 420px; position: relative; }
        .product-image-box img, .product-image-box video { width: 100%; height: 100%; object-fit: cover; }
        
        .product-details-info h1 { font-family: 'Playfair Display', serif; font-size: 28px; color: var(--green-primary); margin-bottom: 12px; }
        .price-tag { font-size: 28px; font-weight: 700; color: var(--green-light); margin: 15px 0; }
        .desc-text { font-size: 14px; color: #555; line-height: 1.7; margin-bottom: 20px; }
        .ingredients-box { background: var(--cream-dark); padding: 15px; border-radius: 12px; margin-bottom: 20px; font-size: 13px; }
        
        .qty-cart-row { display: flex; align-items: center; gap: 15px; margin: 25px 0; flex-wrap: wrap; }
        .quantity-selector { display: flex; align-items: center; border: 1.5px solid #cbd5e1; border-radius: 12px; background: #f8fafc; overflow: hidden; }
        .quantity-selector button { border: none; background: none; padding: 12px 18px; cursor: pointer; font-size: 16px; font-weight: bold; color: var(--green-primary); transition: 0.2s; }
        .quantity-selector button:hover { background: #e2e8f0; }
        .quantity-selector span { padding: 0 15px; font-weight: 600; font-size: 15px; }
        
        .btn-action { flex: 1; min-width: 140px; padding: 14px 20px; border-radius: 12px; font-weight: 600; font-size: 14.5px; border: none; cursor: pointer; transition: 0.2s; text-align: center; }
        .btn-add-cart { background: var(--cream-dark); color: var(--green-primary); }
        .btn-add-cart:hover { background: #e2dcd0; }
        .btn-buy-now { background: var(--green-primary); color: white; }
        .btn-buy-now:hover { background: var(--green-light); }

        #toast { position: fixed; bottom: 30px; right: 30px; background: var(--green-primary); color: white; padding: 14px 24px; border-radius: 12px; box-shadow: var(--shadow); z-index: 9999; display: flex; align-items: center; gap: 12px; transform: translateY(120px); transition: transform 0.4s ease; font-size: 14px; font-weight: 500; }
        #toast.show { transform: translateY(0); }
    </style>
</head>
<body>

    <div id="toast"><i class="fa-solid fa-circle-check" style="font-size: 18px;"></i> <span id="toast-msg">Item added to your basket</span></div>

    <header>
        <a href="/" class="brand-container">
            <img src="{{ settings.logo }}" alt="Logo" class="logo-img">
            <div class="logo"><span>The</span> Adorica Botanicals</div>
        </a>
        <div style="cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%;" onclick="window.location.href='/'">
            <i class="fa-solid fa-house"></i>
        </div>
    </header>

    <div class="detail-container">
        <a href="/" class="back-link"><i class="fa-solid fa-arrow-left"></i> Back to Collections</a>
        
        <div class="product-detail-grid">
            <div class="product-image-box">
                {% if product.video %}
                <video src="{{ product.video }}" autoplay muted loop playsinline></video>
                {% else %}
                <img src="{{ product.image }}" alt="{{ product.name }}">
                {% endif %}
            </div>
            
            <div class="product-details-info">
                {% if product.badge %}
                <span style="display:inline-block; background:var(--accent-gold); color:white; font-size:11px; font-weight:700; text-transform:uppercase; padding:4px 12px; border-radius:20px; margin-bottom:10px; letter-spacing:1px;">{{ product.badge }}</span>
                {% endif %}
                
                <h1>{{ product.name }}</h1>
                
                <div style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: #f59e0b; margin-bottom: 10px;">
                    <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star-half-stroke"></i>
                    <span style="color:#666; margin-left: 5px;">({{ product.reviews_count | default(45) }} reviews)</span>
                </div>

                <div class="price-tag">₹{{ product.price }}</div>
                
                <p class="desc-text">{{ product.desc }}</p>
                
                {% if product.geography %}
                <div class="ingredients-box">
                    <strong style="color:var(--green-primary); display:block; margin-bottom:4px;"><i class="fa-solid fa-map-location-dot"></i> Botanical Origin:</strong>
                    <span style="color:#555;">{{ product.geography }}</span>
                </div>
                {% endif %}

                {% if product.ingredients %}
                <div class="ingredients-box">
                    <strong style="color:var(--green-primary); display:block; margin-bottom:4px;"><i class="fa-solid fa-seedling"></i> Key Botanical Ingredients:</strong>
                    <span style="color:#555;">{{ product.ingredients }}</span>
                </div>
                {% endif %}

                <div style="font-size:13px; color:#2e7d32; font-weight:600; margin-bottom: 15px;">
                    <i class="fa-solid fa-box-archive"></i> In Stock: {{ product.stock }} units available
                </div>

                <div class="qty-cart-row">
                    <div class="quantity-selector">
                        <button type="button" onclick="adjustQty(-1)">-</button>
                        <span id="qty-val">1</span>
                        <button type="button" onclick="adjustQty(1)">+</button>
                    </div>
                    <button type="button" class="btn-action btn-add-cart" onclick="addToCartDetail()"><i class="fa-solid fa-cart-plus"></i> Add to Cart</button>
                    <button type="button" class="btn-action btn-buy-now" onclick="buyNowDetail()">Buy Now</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentQty = 1;
        function adjustQty(delta) {
            currentQty += delta;
            if(currentQty < 1) currentQty = 1;
            document.getElementById('qty-val').innerText = currentQty;
        }

        function showToast(msg) {
            let t = document.getElementById('toast');
            document.getElementById('toast-msg').innerText = msg;
            t.classList.add('show');
            setTimeout(() => { t.classList.remove('show'); }, 3000);
        }

        function addToCartDetail() {
            let product = {{ product | tojson }};
            product.quantity = currentQty;
            
            let existingCart = JSON.parse(localStorage.getItem('adorica_cart') || '[]');
            let found = existingCart.find(x => x.id === product.id);
            if(found) {
                found.quantity = (found.quantity || 1) + currentQty;
            } else {
                existingCart.push(product);
            }
            localStorage.setItem('adorica_cart', JSON.stringify(existingCart));
            showToast(`${currentQty} x ${product.name} added to your basket!`);
        }

        function buyNowDetail() {
            let product = {{ product | tojson }};
            product.quantity = currentQty;
            localStorage.setItem('adorica_cart', JSON.stringify([product]));
            window.location.href = '/';
        }
    </script>
</body>
</html>
"""

SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmation | THE ADORICA BOTANICALS</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --green-light: #2d6a4f; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }

        @keyframes popIn { 0% { transform: scale(0.3); opacity: 0; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
        @keyframes pulseGlow { 0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.4); } 70% { box-shadow: 0 0 0 25px rgba(46, 125, 50, 0); } 100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); } }

        .card { background: white; max-width: 650px; width: 100%; padding: 40px 30px; border-radius: 24px; box-shadow: 0 20px 40px rgba(0,0,0,0.06); text-align: center; }
        .icon-box { font-size: 45px; color: white; background: #2e7d32; border-radius: 50%; width: 85px; height: 85px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; animation: popIn 0.6s ease-out forwards, pulseGlow 1.8s infinite; }
        
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 26px; margin-bottom: 5px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }

        .tracker-container { display: flex; justify-content: space-between; position: relative; margin: 35px 0 25px 0; padding: 0 20px; }
        .tracker-container::before { content: ''; position: absolute; top: 18px; left: 40px; right: 40px; height: 4px; background: #e0e0e0; z-index: 1; }
        .tracker-step { position: relative; z-index: 2; text-align: center; flex: 1; }
        .step-icon { width: 38px; height: 38px; border-radius: 50%; background: #e0e0e0; color: #777; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 14px; font-weight: bold; transition: 0.3s; }
        .tracker-step.completed .step-icon { background: var(--green-light); color: white; }
        .tracker-step.active .step-icon { background: var(--green-primary); color: white; box-shadow: 0 0 15px rgba(27, 67, 50, 0.4); }
        .tracker-step span { font-size: 11px; color: #666; font-weight: 500; display: block; }

        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }

        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; margin-top: 10px; transition: 0.3s; }
        .btn-home:hover { background: var(--green-light); }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-box"><i class="fa-solid fa-check"></i></div>
        <h1>Order Confirmed Successfully!</h1>
        <p class="subtitle">Thank you for choosing The Adorica Botanicals. Track your live shipment status below.</p>

        {% if order %}
        <div class="tracker-container">
            <div class="tracker-step {% if order.status_step >= 1 %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-clipboard-list"></i></div>
                <span>Order Placed</span>
            </div>
            <div class="tracker-step {% if order.status_step > 1 %}completed{% elif order.status_step == 2 %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-box-open"></i></div>
                <span>Packaging</span>
            </div>
            <div class="tracker-step {% if order.status_step > 2 %}completed{% elif order.status_step == 3 %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-truck-fast"></i></div>
                <span>Shipped</span>
            </div>
            <div class="tracker-step {% if order.status_step > 3 %}completed{% elif order.status_step == 4 %}active{% endif %}">
                <div class="step-icon"><i class="fa-solid fa-house-chimney"></i></div>
                <span>Delivered</span>
            </div>
        </div>

        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:var(--green-primary);">{{ order.order_id }}</b></div>
            <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
            <div class="info-row"><span>Email:</span><b>{{ order.email }}</b></div>
            <div class="info-row"><span>Phone:</span><b>{{ order.phone }}</b></div>
            <div class="info-row"><span>Payment Status:</span><b style="color: #2e7d32;">{{ order.payment_type }}</b></div>
            <div class="info-row"><span>Shipping Address:</span><span style="max-width: 250px; text-align: right;">{{ order.full_address }}</span></div>
            <hr style="border: 0; border-top: 1px dashed #ddd; margin: 12px 0;">
            <div class="info-row"><span>Ordered Items:</span></div>
            <ul style="padding-left: 20px; font-size: 12px; color: #555; margin-bottom: 10px;">
                {% for i in order['items'] %}
                <li>{{ i.name }} (Qty: {{ i.quantity | default(1) }}) — ₹{{ i.price * (i.quantity | default(1)) }}</li>
                {% endfor %}
            </ul>
            <div class="info-row total" style="border-top:1px dashed #ccc; padding-top:8px; font-weight:bold; font-size:15px; color:var(--green-primary);"><span>Total Amount:</span><span>₹{{ order.amount }}</span></div>
        </div>
        {% else %}
        <div class="order-info-box">
            <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:16px; color:var(--green-primary);">{{ order_id }}</b></div>
            <p style="color: #2e7d32; font-size: 13px; margin-top: 10px;">Order details retrieved successfully.</p>
        </div>
        {% endif %}

        <p style="font-size: 12px; color: #888; margin-bottom: 15px;"><i class="fa-solid fa-file-pdf" style="color: #c62828;"></i> PDF Invoice & Scannable Sourcing Certificate attached to your email inbox.</p>
        <a href="/" class="btn-home">Continue Shopping</a>
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
    <title>Admin Dashboard | THE ADORICA BOTANICALS</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root { --green-primary: #1b4332; --cream: #FAF7F0; --accent-gold: #d4a373; }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); display: flex; min-height: 100vh; overflow-x: hidden; }

        .admin-sidebar { width: 260px; background: var(--green-primary); color: white; padding: 30px 20px; display: flex; flex-direction: column; justify-content: space-between; position: fixed; height: 100%; left: 0; top: 0; z-index: 100; transition: transform 0.3s ease; }
        .admin-sidebar.collapsed { transform: translateX(-100%); }
        
        .admin-brand { font-size: 16px; font-weight: 700; margin-bottom: 30px; letter-spacing: 0.5px; display: flex; align-items: center; justify-content: space-between; }
        .close-admin-sidebar { font-size: 22px; cursor: pointer; color: white; background: none; border: none; }
        
        .admin-nav { display: flex; flex-direction: column; gap: 10px; flex: 1; }
        .admin-nav button { background: none; border: none; color: white; padding: 12px 15px; text-align: left; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; display: flex; align-items: center; gap: 12px; transition: 0.2s; }
        .admin-nav button:hover, .admin-nav button.active { background: rgba(255,255,255,0.15); color: var(--accent-gold); }
        .admin-nav button i { width: 20px; }

        .admin-content { margin-left: 260px; flex: 1; padding: 30px; overflow-y: auto; transition: margin-left 0.3s ease; }
        .admin-content.expanded { margin-left: 0; }
        
        .admin-topbar { display: flex; align-items: center; gap: 15px; margin-bottom: 25px; background: white; padding: 15px 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
        .admin-menu-toggle { background: none; border: none; font-size: 20px; color: var(--green-primary); cursor: pointer; }

        .admin-section { display: none; }
        .admin-section.active { display: block; }
        
        h2 { color: var(--green-primary); margin-bottom: 25px; font-size: 24px; }
        .card { background: white; padding: 25px; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 25px; overflow-x: auto; }

        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: var(--green-primary); font-weight: 600; }

        .form-control { width: 100%; padding: 10px 14px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 13px; }
        .btn-submit { background: var(--green-primary); color: white; border: none; padding: 12px 25px; border-radius: 8px; cursor: pointer; font-weight: 600; }
        
        .status-badge { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
        .status-1 { background: #e3f2fd; color: #1565c0; }
        .status-2 { background: #fff8e1; color: #f57f17; }
        .status-3 { background: #ede7f6; color: #512da8; }
        .status-4 { background: #e8f5e9; color: #2e7d32; }

        .btn-accept { background: #166534; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; margin-right: 5px; }
        .btn-reject { background: #991b1b; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; }
    </style>
</head>
<body>

    <div class="admin-sidebar" id="adminSidebar">
        <div>
            <div class="admin-brand">
                <span><i class="fa-solid fa-shield-halved" style="color:var(--accent-gold);"></i> Admin Panel</span>
                <button class="close-admin-sidebar" onclick="toggleAdminSidebar()">&times;</button>
            </div>
            <div class="admin-nav">
                <button class="active" onclick="switchAdminTab('orders', this)"><i class="fa-solid fa-box"></i> Orders Management</button>
                <button onclick="switchAdminTab('inventory', this)"><i class="fa-solid fa-warehouse"></i> Inventory & Stock</button>
                <button onclick="switchAdminTab('banners', this)"><i class="fa-solid fa-images"></i> Slider Banners</button>
                <button onclick="switchAdminTab('upload', this)"><i class="fa-solid fa-circle-plus"></i> Upload New Product</button>
                <button onclick="switchAdminTab('branding', this)"><i class="fa-solid fa-image"></i> Website Logo</button>
            </div>
        </div>
        <div>
            <a href="/" target="_blank" style="color: white; text-decoration: none; font-size: 13px; display: flex; align-items: center; gap: 8px;"><i class="fa-solid fa-arrow-up-right-from-square"></i> Visit Storefront</a>
        </div>
    </div>

    <div class="admin-content" id="adminContent">
        <div class="admin-topbar">
            <button class="admin-menu-toggle" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
            <span style="font-weight: 600; color: var(--green-primary); font-size: 15px;">THE ADORICA BOTANICALS - Management Dashboard</span>
        </div>

        <div id="tab-orders" class="admin-section active">
            <h2>Customer Orders Management</h2>
            <div class="card">
                {% if orders %}
                <table>
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Customer Details</th>
                            <th>Items & Total</th>
                            <th>Payment & Address</th>
                            <th>Accept / Reject Action</th>
                            <th>Delivery Status Control</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for o in orders %}
                        <tr id="order-row-{{ o.order_id }}">
                            <td><b>{{ o.order_id }}</b><br><span style="font-size:11px; color:#888;">{{ o.date }}</span></td>
                            <td><b>{{ o.name }}</b><br>{{ o.phone }}<br><span style="font-size:11px; color:#666;">{{ o.email }}</span></td>
                            <td>
                                {% for i in o['items'] %}
                                <div>• {{ i.name }} (x{{ i.quantity | default(1) }})</div>
                                {% endfor %}
                                <b style="color:var(--green-primary); margin-top:5px; display:inline-block;">Total: ₹{{ o.amount }}</b>
                            </td>
                            <td><span style="color:#2e7d32; font-weight:600; font-size:11.5px;">{{ o.payment_type }}</span><br><span style="font-size:11px; color:#666;">{{ o.full_address }}</span></td>
                            <td>
                                {% if o.acceptance_status == 'Rejected' %}
                                <span style="color:#991b1b; font-weight:700; font-size:12px;"><i class="fa-solid fa-circle-xmark"></i> Rejected & Refund Alert Sent</span>
                                {% elif o.acceptance_status == 'Accepted' %}
                                <span style="color:#166534; font-weight:700; font-size:12px; display:block; margin-bottom:5px;"><i class="fa-solid fa-circle-check"></i> Accepted Order</span>
                                <button class="btn-reject" onclick="rejectOrder('{{ o.order_id }}')">Reject & Refund</button>
                                {% else %}
                                <button class="btn-accept" onclick="acceptOrder('{{ o.order_id }}')">Accept</button>
                                <button class="btn-reject" onclick="rejectOrder('{{ o.order_id }}')">Reject & Refund</button>
                                {% endif %}
                            </td>
                            <td>
                                <select class="form-control" style="margin-bottom:0; width:150px; font-size:12px;" onchange="updateOrderStatus('{{ o.order_id }}', this.value)">
                                    <option value="1" {% if o.status_step == 1 %}selected{% endif %}>1. Order Placed</option>
                                    <option value="2" {% if o.status_step == 2 %}selected{% endif %}>2. Packaging</option>
                                    <option value="3" {% if o.status_step == 3 %}selected{% endif %}>3. Shipped</option>
                                    <option value="4" {% if o.status_step == 4 %}selected{% endif %}>4. Delivered</option>
                                </select>
                                <div style="margin-top:5px;"><span class="status-badge status-{{ o.status_step }}">{{ o.status_text }}</span></div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="color: #666; text-align: center; padding: 20px;">No customer orders placed yet.</p>
                {% endif %}
            </div>
        </div>

        <div id="tab-banners" class="admin-section">
            <h2>Slider Banners Management</h2>
            <div class="card" style="max-width: 600px;">
                <form action="/api/admin/add_slide" method="POST" enctype="multipart/form-data">
                    <input type="text" name="title" class="form-control" placeholder="Banner Title *" required>
                    <input type="text" name="badge" class="form-control" placeholder="Badge (e.g. New Launch)">
                    <textarea name="desc" class="form-control" placeholder="Banner Description *" rows="2" required></textarea>
                    
                    <label style="font-weight:600; font-size:13px;">Banner Image *</label>
                    <input type="file" name="image_file" class="form-control" accept="image/*" required>
                    
                    <label style="font-weight:600; font-size:13px;">Banner Video (Optional)</label>
                    <input type="file" name="video_file" class="form-control" accept="video/*">
                    
                    <button type="submit" class="btn-submit">Upload to Slider</button>
                </form>
            </div>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Image Preview</th>
                            <th>Details</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for s in slides %}
                        <tr id="slide-row-{{ s.id }}">
                            <td><img src="{{ s.image }}" style="width:100px; height:60px; object-fit:cover; border-radius:8px;"></td>
                            <td><b>{{ s.title }}</b><br><small>{{ s.badge }}</small></td>
                            <td>
                                <button onclick="deleteSlide({{ s.id }})" style="background:#c62828; color:white; border:none; padding:8px 15px; border-radius:8px; cursor:pointer;"><i class="fa-solid fa-trash"></i> Remove</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div id="tab-inventory" class="admin-section">
            <h2>Inventory & Product Management</h2>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Product Name</th>
                            <th>Category</th>
                            <th>Price (₹)</th>
                            <th>Stock</th>
                            <th>Live Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr id="prod-row-{{ p.id }}">
                            <td><b>{{ p.name }}</b></td>
                            <td>{{ p.category }}</td>
                            <td><input type="number" value="{{ p.price }}" id="edit-price-{{ p.id }}" style="width:80px; padding:5px; border:1px solid #ddd; border-radius:4px;"></td>
                            <td><input type="number" value="{{ p.stock }}" id="edit-stock-{{ p.id }}" style="width:70px; padding:5px; border:1px solid #ddd; border-radius:4px;"></td>
                            <td>
                                <select id="edit-status-{{ p.id }}" style="padding:5px; border:1px solid #ddd; border-radius:4px;">
                                    <option value="active" {% if p.status == 'active' %}selected{% endif %}>Active (Live)</option>
                                    <option value="suspended" {% if p.status == 'suspended' %}selected{% endif %}>Suspended (Hidden)</option>
                                </select>
                            </td>
                            <td>
                                <button onclick="saveProduct({{ p.id }})" style="background:#2e7d32; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;"><i class="fa-solid fa-save"></i></button>
                                <button onclick="deleteProduct({{ p.id }})" style="background:#c62828; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;"><i class="fa-solid fa-trash"></i></button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div id="tab-upload" class="admin-section">
            <h2>Upload New Botanical Product</h2>
            <div class="card" style="max-width: 600px;">
                <form action="/api/admin/add_product" method="POST" enctype="multipart/form-data">
                    <label style="font-weight:600; font-size:13px;">Product Name *</label>
                    <input type="text" name="name" class="form-control" required placeholder="e.g. Rosemary Hair Tonic">
                    
                    <label style="font-weight:600; font-size:13px;">Category *</label>
                    <select name="category" class="form-control" required>
                        <option value="Skin Care">Skin Care</option>
                        <option value="Hair Care">Hair Care</option>
                        <option value="Oil">Oil</option>
                        <option value="Shampoo">Shampoo</option>
                    </select>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px;">
                        <div>
                            <label style="font-weight:600; font-size:13px;">Price (₹) *</label>
                            <input type="number" name="price" class="form-control" required placeholder="499">
                        </div>
                        <div>
                            <label style="font-weight:600; font-size:13px;">Initial Stock *</label>
                            <input type="number" name="stock" class="form-control" required placeholder="50">
                        </div>
                    </div>

                    <label style="font-weight:600; font-size:13px;">Product Image File *</label>
                    <input type="file" name="image_file" class="form-control" accept="image/*" required>

                    <label style="font-weight:600; font-size:13px;">Product Video File (Optional)</label>
                    <input type="file" name="video_file" class="form-control" accept="video/*">

                    <label style="font-weight:600; font-size:13px;">Key Ingredients</label>
                    <input type="text" name="ingredients" class="form-control" placeholder="e.g. Rosemary Extract, Almond Oil">

                    <label style="font-weight:600; font-size:13px;">Sourcing Geography / Origin Details</label>
                    <input type="text" name="geography" class="form-control" placeholder="e.g. Harvested from Western Ghats (Kerala)">

                    <label style="font-weight:600; font-size:13px;">Extraction Technique</label>
                    <input type="text" name="extraction" class="form-control" placeholder="e.g. Cold pressed steam distillation">

                    <label style="font-weight:600; font-size:13px;">Description</label>
                    <textarea name="desc" class="form-control" rows="3" placeholder="Brief description of herbal ingredients..."></textarea>

                    <button type="submit" class="btn-submit">Publish Product</button>
                </form>
            </div>
        </div>

        <div id="tab-branding" class="admin-section">
            <h2>Website Profile Logo Management</h2>
            <div class="card" style="max-width: 500px; text-align: center;">
                <img src="{{ settings.logo }}" alt="Current Logo" style="width: 100px; height: 100px; object-fit: cover; border-radius: 50%; border: 3px solid var(--accent-gold); margin-bottom: 20px;">
                <form action="/api/admin/update_logo" method="POST" enctype="multipart/form-data">
                    <label style="font-weight:600; font-size:13px; display:block; text-align:left; margin-bottom:8px;">Upload New Logo Image</label>
                    <input type="file" name="logo_file" class="form-control" accept="image/*" required>
                    <button type="submit" class="btn-submit" style="width:100%;">Update Store Logo</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        function toggleAdminSidebar() {
            document.getElementById('adminSidebar').classList.toggle('collapsed');
            document.getElementById('adminContent').classList.toggle('expanded');
        }

        function switchAdminTab(tabId, btn) {
            document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.admin-nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            btn.classList.add('active');
        }

        function updateOrderStatus(orderId, step) {
            fetch('/api/admin/update_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId, step: step })
            }).then(r => r.json()).then(d => {
                if(d.success) alert("Status updated and notification email sent!");
            });
        }

        function acceptOrder(orderId) {
            fetch('/api/admin/accept_order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId })
            }).then(r => r.json()).then(d => {
                if(d.success) location.reload();
            });
        }

        function rejectOrder(orderId) {
            if(confirm("Are you sure you want to reject this order? An automatic cancellation & 2-3 day refund notice will be emailed to the customer.")) {
                fetch('/api/admin/reject_order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ order_id: orderId })
                }).then(r => r.json()).then(d => {
                    if(d.success) location.reload();
                });
            }
        }

        function deleteSlide(id) {
            if(confirm("Are you sure you want to remove this banner?")) {
                fetch('/api/admin/delete_slide', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                }).then(r => r.json()).then(d => {
                    if(d.success) document.getElementById('slide-row-' + id).remove();
                });
            }
        }

        function saveProduct(id) {
            let price = document.getElementById('edit-price-' + id).value;
            let stock = document.getElementById('edit-stock-' + id).value;
            let status = document.getElementById('edit-status-' + id).value;

            fetch('/api/admin/edit_product', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id, price: price, stock: stock, status: status })
            }).then(r => r.json()).then(d => {
                if(d.success) alert("Product updated successfully.");
            });
        }

        function deleteProduct(id) {
            if(confirm("Are you sure you want to delete this product?")) {
                fetch('/api/admin/delete_product', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id })
                }).then(r => r.json()).then(d => {
                    if(d.success) document.getElementById('prod-row-' + id).remove();
                });
            }
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5644, debug=True)
