from flask import Flask, render_template_string, request, jsonify, redirect, url_for, send_file
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
import razorpay
import requests  # <-- for SMS API

# --- REPORTLAB PDF LIBRARIES ---
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    try:
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics.shapes import Drawing
        QR_AVAILABLE = True
    except Exception as e:
        print(f"ReportLab QR import skipped: {e}")
        QR_AVAILABLE = False
    REPORTLAB_AVAILABLE = True
except Exception as e:
    print(f"ReportLab import notice: {e}")
    REPORTLAB_AVAILABLE = False

app = Flask(__name__)
app.secret_key = 'chiranjeevi_adorica_botanicals_secure_key_2026'

# --- RAZORPAY CONFIGURATION ---
RAZORPAY_KEY_ID = "rzp_live_TNBc6IiPsiAkOD"
RAZORPAY_KEY_SECRET = "iLeTigZRFMEzubj7hEbW9mnR"
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "keshaadar@gmail.com"
SMTP_PASS = "zvxb mrbs ccoi vfrl"

# --- SMS CONFIGURATION (TextBee) ---
TEXTBEE_API_KEY = "txb_O8FN8nZ2Lejzky2iQBWZeg7whnf7XFI3"  # your actual key
TEXTBEE_BASE_URL = "https://api.textbee.dev/api/v1"
TEXTBEE_DEVICE_ID = "6a881aaa300559904690fcd7"           # your device ID

# --- DDOS PROTECTION & RATE LIMITING ---
IP_REQUESTS = defaultdict(list)
RATE_LIMIT_WINDOW = 60
MAX_REQUESTS_PER_WINDOW = 80
BLACKLISTED_IPS = []

# --- DATABASE & STORAGE (in-memory) ---
SETTINGS = {
    "logo": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=150&q=80",
    "brand_name": "",
    "tagline": "Where Nature Meets Care"
}

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

ADS = [
    {
        "id": 1,
        "image": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&w=600&q=80",
        "link": "https://example.com/offer",
        "title": "Special Offer!",
        "desc": "Get 20% off on all hair oils"
    }
]

# ---------- UPDATED PRODUCTS WITH ORIGINAL PRICE & BADGES ----------
PRODUCTS = [
    {
        "id": 1,
        "name": "Black Cotton Oversize T-Shirt",
        "category": "Apparel",
        "image": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=500&q=80",
        "media": [
            {"type": "image", "url": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=800&q=80"},
            {"type": "image", "url": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=800&q=80"},
        ],
        "video": "",
        "desc": "Premium oversized black cotton tee, perfect for everyday style.",
        "ingredients": "100% Organic Cotton",
        "geography": "Crafted in India with fair-trade practices.",
        "extraction": "Ethically sourced and manufactured.",
        "rating": 4.8,
        "reviews_count": 96,
        "badge": "CUSTOMISABLE",
        "original_price": 1599,
        "status": "active",
        "variants": [
            {"size": "S", "price": 999, "stock": 20},
            {"size": "M", "price": 999, "stock": 30},
            {"size": "L", "price": 999, "stock": 25}
        ]
    },
    {
        "id": 2,
        "name": "OUD White Oud Perfume",
        "category": "Fragrance",
        "image": "https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=500&q=80",
        "media": [
            {"type": "image", "url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=800&q=80"},
            {"type": "image", "url": "https://images.unsplash.com/photo-1594035910387-fea47794261f?auto=format&fit=crop&w=800&q=80"},
        ],
        "video": "",
        "desc": "A blend of character and elegance. Crafted for those who love scent. Leave a lasting impression.",
        "ingredients": "Oud, White Musk, Sandalwood",
        "geography": "Sourced from premium Arabian perfumers.",
        "extraction": "Hydro-distilled essential oils.",
        "rating": 4.9,
        "reviews_count": 142,
        "badge": "PREMIUM LONG LASTING",
        "original_price": 999,
        "status": "active",
        "variants": [
            {"size": "50ml", "price": 499, "stock": 40},
            {"size": "100ml", "price": 799, "stock": 25}
        ]
    },
    {
        "id": 3,
        "name": "Green Tea Face Wash",
        "category": "Skin Care",
        "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80",
        "media": [
            {"type": "image", "url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=800&q=80"},
            {"type": "image", "url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=800&q=80"},
        ],
        "video": "",
        "desc": "Cleanse. Refresh. Glow naturally. Gentle freshness for all skin types.",
        "ingredients": "Green Tea Extract, Aloe Vera, Neem",
        "geography": "Organic green tea from Assam.",
        "extraction": "Cold-pressed and steam distilled.",
        "rating": 4.7,
        "reviews_count": 215,
        "badge": "GENTLE FRESHNESS",
        "original_price": 599,
        "status": "active",
        "variants": [
            {"size": "100ml", "price": 349, "stock": 50}
        ]
    }
]

ORDERS = []
CUSTOMERS = []      # list of dict {name, email, phone}
COUPONS = []        # list of dict {code, discount, active}

# --- CERTIFICATIONS (Brands & Logos for Marquee) ---
CERTIFICATIONS = [
    {"name": "Razorpay", "logo": "https://razorpay.com/logo.png", "link": "https://razorpay.com"},
    {"name": "GST Certified", "logo": "https://example.com/gst.png", "link": "#"},
    {"name": "Shopify", "logo": "https://example.com/shopify.png", "link": "#"}
]

# --- SECURITY GUARD ---
@app.before_request
def security_and_ddos_guard():
    client_ip = request.remote_addr
    if client_ip in BLACKLISTED_IPS:
        return jsonify({"error": "Your IP address has been blacklisted by administrator."}), 403

    now = time.time()
    timestamps = IP_REQUESTS[client_ip]
    IP_REQUESTS[client_ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]

    if len(IP_REQUESTS[client_ip]) >= MAX_REQUESTS_PER_WINDOW:
        return jsonify({"error": "DDoS Guard Active: Too many requests. Please slow down."}), 429

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

# --- SMS SENDING FUNCTION ---
def send_sms(phone, message):
    """Send an SMS via TextBee API."""
    if not phone or len(phone) < 10:
        return False
    # Ensure phone is in international format (add +91 if 10 digits)
    phone_str = str(phone).strip()
    if phone_str.isdigit() and len(phone_str) == 10:
        phone_str = "+91" + phone_str
    elif not phone_str.startswith('+'):
        phone_str = "+" + phone_str  # fallback

    payload = {
        "deviceId": TEXTBEE_DEVICE_ID,
        "recipients": [phone_str],
        "message": message[:160]  # SMS length limit
    }
    headers = {"x-api-key": TEXTBEE_API_KEY}
    try:
        resp = requests.post(f"{TEXTBEE_BASE_URL}/gateway/send-sms",
                             json=payload, headers=headers, timeout=8)
        if resp.status_code == 200:
            print(f"SMS sent to {phone_str}: {message[:50]}...")
            return True
        else:
            print(f"SMS failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"SMS error: {e}")
        return False

# --- ASYNCHRONOUS SMS SENDER ---
def _send_sms_thread(phone, message):
    send_sms(phone, message)

def trigger_async_sms(phone, message):
    t = threading.Thread(target=_send_sms_thread, args=(phone, message))
    t.daemon = True
    t.start()

# --- NUMBER TO WORDS CONVERTER (INR) ---
def num_to_words_inr(number):
    try:
        n = int(round(float(number)))
        if n == 0:
            return "Zero Rupees Only"
        
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
                 "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
                 "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        def convert_below_thousand(num):
            if num == 0:
                return ""
            elif num < 20:
                return units[num] + " "
            elif num < 100:
                return tens[num // 10] + " " + convert_below_thousand(num % 10)
            else:
                return units[num // 100] + " Hundred " + convert_below_thousand(num % 100)

        words = ""
        if n >= 10000000:
            words += convert_below_thousand(n // 10000000) + "Crore "
            n %= 10000000
        if n >= 100000:
            words += convert_below_thousand(n // 100000) + "Lakh "
            n %= 100000
        if n >= 1000:
            words += convert_below_thousand(n // 1000) + "Thousand "
            n %= 1000
        if n > 0:
            words += convert_below_thousand(n)

        return words.strip() + " Rupees Only"
    except Exception:
        return f"{number} Rupees Only"

# --- NATIVE REPORTLAB VECTOR QR CODE DRAWING ---
def create_native_qr_drawing(url_text, size=80):
    if not QR_AVAILABLE:
        return None
    try:
        qr_widget = QrCodeWidget(url_text)
        bounds = qr_widget.getBounds()
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
        d.add(qr_widget)
        return d
    except Exception as e:
        print(f"Native QR creation error: {e}")
        return None

# --- PDF INVOICE GENERATOR ---
def generate_order_pdf(order_data, order_id, qr_target_url):
    if not REPORTLAB_AVAILABLE:
        return None
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#1b4332'), alignment=1, spaceAfter=2)
        tagline_style = ParagraphStyle('DocTag', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#555555'), alignment=1, spaceAfter=2)
        invoice_title_style = ParagraphStyle('DocInvTitle', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#d4a373'), alignment=1, spaceAfter=15)
        section_banner_style = ParagraphStyle('SecBanner', fontName='Helvetica-Bold', fontSize=11, textColor=colors.white, alignment=0)
        normal_text = ParagraphStyle('NormText', fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#1F2937'))
        bold_label = ParagraphStyle('BoldLbl', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#374151'))
        
        story = []

        # Logo & Header
        logo_image = None
        try:
            logo_src = SETTINGS['logo']
            if logo_src.startswith('data:image'):
                header, encoded = logo_src.split(",", 1)
                logo_data = base64.b64decode(encoded)
                logo_image = RLImage(io.BytesIO(logo_data), width=55, height=55)
            else:
                req = urllib.request.Request(logo_src, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    logo_image = RLImage(io.BytesIO(resp.read()), width=55, height=55)
        except Exception as e:
            print(f"Logo fetch skipped for PDF: {e}")

        center_text_flow = [
            Paragraph("CHIRANJEEVI ", title_style),
            Paragraph("Where Nature Meets Care", tagline_style),
            Paragraph("ORDER PRICE INVOICE", invoice_title_style)
        ]

        if logo_image:
            header_table = Table([[logo_image, center_text_flow]], colWidths=[65, 475])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (0,0), 'LEFT'),
            ]))
        else:
            header_table = Table([[ "", center_text_flow ]], colWidths=[10, 530])

        story.append(header_table)
        story.append(Spacer(1, 10))

        # Metadata
        inv_no = f"INV-{order_id.replace('ADOR-', '')}"
        inv_date = datetime.datetime.now().strftime("%d-%m-%Y")
        cust_name = order_data.get('name', 'Customer Name')
        cust_details = f"{order_data.get('phone', '')} / {order_data.get('email', '')} / {order_data.get('street', '')}, {order_data.get('city', '')}"
        cust_state = order_data.get('state', 'West Bengal')

        meta_grid_data = [
            [Paragraph("Invoice Number", bold_label), Paragraph(inv_no, normal_text), Paragraph("Invoice Date", bold_label), Paragraph(inv_date, normal_text)],
            [Paragraph("Order ID", bold_label), Paragraph(order_id, normal_text), Paragraph("Customer Name", bold_label), Paragraph(cust_name, normal_text)],
            [Paragraph("Customer Details", bold_label), Paragraph(cust_details, normal_text), Paragraph("Customer State", bold_label), Paragraph(cust_state, normal_text)]
        ]

        meta_table = Table(meta_grid_data, colWidths=[110, 160, 110, 160])
        meta_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F3F4F6')),
            ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#F3F4F6')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))

        # Order Details
        banner_table = Table([[Paragraph("ORDER DETAILS", section_banner_style)]], colWidths=[540])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1b4332')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(banner_table)

        # Items
        particulars_data = [
            [Paragraph("Particulars", bold_label), Paragraph("Qty", bold_label), Paragraph("Unit Price", bold_label), Paragraph("Amount", bold_label)]
        ]

        subtotal = 0.0
        for item in order_data.get('items', []):
            qty = int(item.get('quantity', 1))
            price = float(item.get('price', 0))
            amt = price * qty
            subtotal += amt
            size_str = f" ({item.get('size', '')})" if item.get('size') else ""
            name_str = f"{item.get('name', 'Product')}{size_str}"
            particulars_data.append([
                Paragraph(name_str, normal_text),
                Paragraph(str(qty), normal_text),
                Paragraph(f"₹{price:.2f}", normal_text),
                Paragraph(f"₹{amt:.2f}", normal_text)
            ])

        tax_amt = round(subtotal * 0.18, 2)
        grand_total = float(order_data.get('amount', subtotal + tax_amt))

        particulars_data.append([Paragraph("Subtotal", bold_label), "", "", Paragraph(f"₹{subtotal:.2f}", bold_label)])
        particulars_data.append([Paragraph("Tax (18% GST Incl.)", bold_label), "", "", Paragraph(f"₹{tax_amt:.2f}", bold_label)])
        particulars_data.append([Paragraph("Grand Total", bold_label), "", "", Paragraph(f"₹{grand_total:.2f}", bold_label)])

        particulars_table = Table(particulars_data, colWidths=[270, 50, 100, 120])
        particulars_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F9FAFB')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#1b4332')),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F3EFEA')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(particulars_table)
        story.append(Spacer(1, 10))

        # Total in words
        words_str = num_to_words_inr(grand_total)
        words_data = [[
            Paragraph("Total Amount (in words):", bold_label),
            Paragraph(words_str, normal_text)
        ]]
        words_table = Table(words_data, colWidths=[150, 390])
        words_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
            ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F3F4F6')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(words_table)
        story.append(Spacer(1, 12))

        # QR Code
        qr_drawing = create_native_qr_drawing(qr_target_url, size=75) if QR_AVAILABLE else None
        qr_text_html = """
        <b style="color:#1b4332; font-size:10px;">SCAN QR CODE FOR BOTANICAL PRODUCT ORIGIN & HISTORY</b><br/>
        <span style="font-size:8px; color:#555;">
        Scan this code to open your dedicated product certificate page. Displays harvest locations, extraction techniques, and formula details exclusively for your ordered items.
        </span>
        """

        qr_table_data = [[ Paragraph(qr_text_html, normal_text), qr_drawing if qr_drawing else "" ]]
        qr_table = Table(qr_table_data, colWidths=[430, 110])
        qr_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAF7F0')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#D4A373')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (1,0), (1,0), 'RIGHT')
        ]))
        story.append(qr_table)
        story.append(Spacer(1, 12))

        # Footer
        hr_table = Table([[""]], colWidths=[540], rowHeights=[1])
        hr_table.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#D1D5DB')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(hr_table)
        story.append(Spacer(1, 8))

        footer_data = [[
            Paragraph("<b>Thank you for choosing CHIRANJEEVI .</b>", normal_text),
            Paragraph("Authorized Signature", normal_text)
        ]]
        footer_table = Table(footer_data, colWidths=[360, 180])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('PADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(footer_table)
        story.append(Spacer(1, 4))

        sub_footer = Paragraph("Order price invoice generated for customer orders.", ParagraphStyle('SubFoot', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#888888'), alignment=1))
        story.append(sub_footer)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"Error inside generate_order_pdf: {e}")
        return None

# --- ASYNCHRONOUS EMAIL SENDER (Ultra‑Fast) ---
def _send_email_thread(msg_obj, recipient_email):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=12)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASS)
        server.sendmail(SMTP_EMAIL, recipient_email, msg_obj.as_string())
        server.quit()
        print(f"Email successfully sent to {recipient_email}")
    except Exception as e:
        print(f"Async email transmission error: {e}")

def trigger_async_email(msg_obj, recipient_email):
    t = threading.Thread(target=_send_email_thread, args=(msg_obj, recipient_email))
    t.daemon = True
    t.start()

# --- HELPER: add/update customer ---
def add_or_update_customer(name, email, phone):
    # check if exists
    for c in CUSTOMERS:
        if c['email'] == email:
            c['name'] = name
            c['phone'] = phone
            return
    # new customer
    CUSTOMERS.append({"name": name, "email": email, "phone": phone})

# --- EMAIL + SMS SENDERS FOR EACH EVENT ---
def send_order_email_and_sms(order_data, order_id, qr_target_url):
    # Email part (as before)
    try:
        recipient_email = order_data['email']
        name = order_data['name']
        amount = order_data['amount']
        items = order_data['items']
        full_address = order_data['full_address']

        msg = MIMEMultipart('mixed')
        msg['Subject'] = f"Order Confirmed & PDF Invoice: {order_id} - CHIRANJEEVI "
        msg['From'] = f"CHIRANJEEVI  <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        items_html = "".join([f"<li><b>{i['name']}</b> {i.get('size', '')} (Qty: {i.get('quantity', 1)}) - ₹{i['price']}</li>" for i in items])

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 26px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">CHIRANJEEVI </h1>
                <p style="letter-spacing: 3px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">Where Nature Meets Care</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <div style="background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%); color: white; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px;">
                    <h2 style="margin: 0 0 10px 0; font-size: 24px;">Thank you for ordering, {name}!</h2>
                    <p style="margin: 0; font-size: 14px; opacity: 0.9;">Your botanical order has been successfully placed.</p>
                    <div style="background: rgba(255,255,255,0.15); padding: 12px; border-radius: 10px; margin-top: 15px;">
                        <span style="font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Order Reference ID</span>
                        <h3 style="margin: 5px 0 0 0; font-size: 26px; font-family: monospace; letter-spacing: 2px;">{order_id}</h3>
                    </div>
                </div>

                <p style="font-size: 14px; color: #555; line-height: 1.6;">We have attached your official <b>PDF Order Price Invoice & Botanical Sourcing Certificate</b> to this email. You can scan the QR code on the PDF to view the origin history of your items.</p>
                
                <div style="background: #F3EFEA; padding: 15px 20px; border-radius: 12px; margin: 20px 0; border: 1px dashed #d4a373;">
                    <p style="margin: 5px 0; color: #333; font-size: 14px;"><b>Total Amount Paid:</b> ₹{amount}</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;"><b>Shipping Address:</b> {full_address}</p>
                </div>

                <h4 style="color: #1b4332; margin-bottom: 10px;">Items Ordered:</h4>
                <ul style="font-size: 14px; color: #444; padding-left: 20px; line-height: 1.8;">
                    {items_html}
                </ul>

                <div style="text-align: center; margin-top: 35px;">
                    <a href="{qr_target_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 35px; border-radius: 30px; font-weight: bold; font-size: 15px; display: inline-block;">View Product History & Geography</a>
                </div>

                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact support at {SMTP_EMAIL}</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))

        if REPORTLAB_AVAILABLE:
            pdf_bytes = generate_order_pdf(order_data, order_id, qr_target_url)
            if pdf_bytes:
                part = MIMEApplication(pdf_bytes, _subtype="pdf")
                part.add_header('Content-Disposition', 'attachment', filename=f"Invoice_{order_id}.pdf")
                msg.attach(part)

        trigger_async_email(msg, recipient_email)
    except Exception as e:
        print(f"Error compiling send_order_email: {e}")

    # SMS part
    try:
        sms_msg = f"CHIRANJEEVI : Order {order_id} confirmed! Total ₹{order_data['amount']}. Track at {qr_target_url}. Thank you!"
        trigger_async_sms(order_data['phone'], sms_msg)
    except Exception as e:
        print(f"SMS send error: {e}")

def send_rejection_email_and_sms(order_data, order_id, amount):
    # Email
    try:
        recipient_email = order_data['email']
        name = order_data['name']
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Order Cancelled & Refund Initiated: {order_id} - CHIRANJEEVI "
        msg['From'] = f"CHIRANJEEVI  <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 24px; color: #991b1b; margin-bottom: 5px; font-weight: bold; text-align: center;">Order Cancellation Alert</h1>
                <p style="letter-spacing: 2px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">CHIRANJEEVI </p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <p style="font-size: 15px; color: #333;">Dear <b>{name}</b>,</p>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">We regret to inform you that your order reference ID <b style="font-family:monospace; color:#1b4332;">{order_id}</b> could not be accepted and has been cancelled by our fulfillment team.</p>
                
                <div style="background: #fee2e2; border: 1.5px solid #ef4444; color: #991b1b; padding: 20px; border-radius: 12px; margin: 25px 0;">
                    <h3 style="margin: 0 0 8px 0; font-size: 16px;">Automatic Refund Processing</h3>
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

    # SMS
    try:
        sms_msg = f"CHIRANJEEVI: Order {order_id} cancelled. Refund of ₹{amount} initiated. Track: http://127.0.0.1:5644/order_success/{order_id}"
        trigger_async_sms(order_data['phone'], sms_msg)
    except Exception as e:
        print(f"SMS reject error: {e}")

def send_refund_email_and_sms(order_data, order_id, amount):
    # Email
    try:
        recipient_email = order_data['email']
        name = order_data['name']
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Refund Processed for Order {order_id} - CHIRANJEEVI "
        msg['From'] = f"CHIRANJEEVI  <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 24px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">Refund Confirmed</h1>
                <p style="letter-spacing: 2px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">CHIRANJEEVI </p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <p style="font-size: 15px; color: #333;">Dear <b>{name}</b>,</p>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">Your order <b style="font-family:monospace; color:#1b4332;">{order_id}</b> has been marked as <b>refunded</b> in our system.</p>
                
                <div style="background: #dcfce7; border: 1.5px solid #22c55e; color: #166534; padding: 20px; border-radius: 12px; margin: 25px 0;">
                    <h3 style="margin: 0 0 8px 0; font-size: 16px;">Refund Successfully Processed</h3>
                    <p style="margin: 0; font-size: 13.5px; line-height: 1.5;">
                        An amount of <b>₹{amount}</b> has been refunded to your original payment method. It should reflect in your account within <b>2‑3 business days</b>.
                    </p>
                </div>

                <p style="font-size: 13px; color: #666; line-height: 1.5;">We hope to serve you again. If you have any questions, please don't hesitate to contact our support team.</p>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0 15px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">Need assistance? Contact support at {SMTP_EMAIL}</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))
        trigger_async_email(msg, recipient_email)
    except Exception as e:
        print(f"Refund email failed: {e}")

    # SMS
    try:
        sms_msg = f"CHIRANJEEVI : Refund of ₹{amount} for order {order_id} has been processed. It will reflect in 2-3 days."
        trigger_async_sms(order_data['phone'], sms_msg)
    except Exception as e:
        print(f"SMS refund error: {e}")

def send_status_update_email_and_sms(order_data, order_id, step, status_text):
    # Email (as before)
    try:
        recipient_email = order_data['email']
        name = order_data['name']
        msg = MIMEMultipart('alternative')
        msg['From'] = f"CHIRANJEEVI  <{SMTP_EMAIL}>"
        msg['To'] = recipient_email

        track_url = f"http://127.0.0.1:5644/order_success/{order_id}"

        if step == 2:
            subject = f"📦 Packaging Completed: Order {order_id} - CHIRANJEEVI"
            status_heading = "Packaging Completed & Ready for Dispatch"
            status_msg = f"Great news, <b>{name}</b>! The packaging for your order <b>{order_id}</b> has been completed with extreme botanical care. Your products are sanitized, securely sealed, and ready for courier pickup."
            badge_bg = "#fff8e1"
            badge_border = "#f59e0b"
            badge_text_color = "#b45309"
        elif step == 3:
            subject = f"🚚 Order Shipped: {order_id} is On Its Way! - CHIRANJEEVI"
            status_heading = "Order Dispatched & In Transit"
            status_msg = f"Exciting news, <b>{name}</b>! Your order <b>{order_id}</b> has been shipped. Our courier partner has picked up your package and it is currently on its way to your shipping address."
            badge_bg = "#ede7f6"
            badge_border = "#7c3aed"
            badge_text_color = "#5b21b6"
        elif step == 4:
            subject = f"🎉 Order Delivered: {order_id} - CHIRANJEEVI"
            status_heading = "Order Delivered Successfully"
            status_msg = f"Wonderful news, <b>{name}</b>! Your order <b>{order_id}</b> has been delivered. We hope you enjoy your pure botanical remedies!"
            badge_bg = "#f0fdf4"
            badge_border = "#22c55e"
            badge_text_color = "#166534"
        elif step == 5:
            subject = f"💵 Refund Processed: {order_id} - CHIRANJEEVI"
            status_heading = "Refund Completed"
            status_msg = f"Dear <b>{name}</b>, your order <b>{order_id}</b> has been refunded. The amount will be credited back to your payment method shortly."
            badge_bg = "#fef9c3"
            badge_border = "#eab308"
            badge_text_color = "#854d0e"
        else:
            subject = f"Order Status Update: {order_id} - CHIRANJEEVI"
            status_heading = f"Status: {status_text}"
            status_msg = f"Dear <b>{name}</b>, your order <b>{order_id}</b> status has been updated to {status_text}."
            badge_bg = "#e3f2fd"
            badge_border = "#3b82f6"
            badge_text_color = "#1d4ed8"

        msg['Subject'] = subject

        html_content = f"""
        <html>
        <body style="font-family: 'Poppins', 'Arial', sans-serif; background-color: #FAF7F0; padding: 40px 20px; text-align: center; color: #2b2b2b;">
            <div style="background: white; max-width: 600px; margin: 0 auto; padding: 40px 30px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); text-align: left;">
                <h1 style="font-size: 24px; color: #1b4332; margin-bottom: 5px; font-weight: bold; text-align: center;">CHIRANJEEVI</h1>
                <p style="letter-spacing: 2px; color: #d4a373; text-transform: uppercase; font-size: 11px; font-weight: bold; margin-top: 0; text-align: center;">Where Nature Meets Care</p>
                <hr style="border: 0; border-top: 2px solid #F3EFEA; margin: 25px 0;">
                
                <p style="font-size: 15px; color: #333;">Dear <b>{name}</b>,</p>
                <p style="font-size: 14px; color: #555; line-height: 1.6;">{status_msg}</p>
                
                <div style="background: {badge_bg}; border: 1.5px solid {badge_border}; color: {badge_text_color}; padding: 20px; border-radius: 12px; margin: 20px 0; text-align: center;">
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">Current Status</span>
                    <h2 style="margin: 5px 0 0 0; font-size: 22px; color: {badge_text_color};">{status_heading}</h2>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{track_url}" style="background: #1b4332; color: white; text-decoration: none; padding: 14px 35px; border-radius: 30px; font-weight: bold; font-size: 14px; display: inline-block;">Track Live Order Details</a>
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

    # SMS
    try:
        status_map = {1: "Placed", 2: "Packaging", 3: "Shipped", 4: "Delivered", 5: "Refunded"}
        step_text = status_map.get(step, status_text)
        sms_msg = f"CHIRANJEEVI: Order {order_id} status: {step_text}. Track: http://127.0.0.1:5644/order_success/{order_id}"
        trigger_async_sms(order_data['phone'], sms_msg)
    except Exception as e:
        print(f"SMS status error: {e}")

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    active_products = [p for p in PRODUCTS if p.get('status', 'active') == 'active']
    return render_template_string(TEMPLATE, products=active_products, settings=SETTINGS, slides=SLIDES, certifications=CERTIFICATIONS, coupons=COUPONS)

@app.route('/product/<int:prod_id>')
def product_detail(prod_id):
    product = next((p for p in PRODUCTS if p['id'] == prod_id), None)
    if not product:
        return "Product not found", 404
    related = [p for p in PRODUCTS if p['category'] == product['category'] and p['id'] != prod_id and p.get('status', 'active') == 'active']
    if len(related) < 6:
        others = [p for p in PRODUCTS if p['id'] != prod_id and p.get('status', 'active') == 'active' and p['category'] != product['category']]
        related.extend(others[:6-len(related)])
    related = related[:6]
    ad = random.choice(ADS) if ADS else None
    return render_template_string(PRODUCT_DETAIL_TEMPLATE, product=product, settings=SETTINGS, related=related, ad=ad, coupons=COUPONS)

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

# --- DYNAMIC UPI QR CODE ---
@app.route('/create_qr_code', methods=['POST'])
def create_qr_code():
    try:
        data = request.get_json() or {}
        amount_inr = float(data.get('amount', 0))
        if amount_inr <= 0:
            return jsonify({'success': False, 'error': 'Invalid amount entered'})

        amount_in_paise = int(round(amount_inr * 100))
        owner_name = SETTINGS['brand_name']

        qr_data = razorpay_client.qrcode.create({
            "type": "upi_qr",
            "name": owner_name,
            "usage": "single_use",
            "fixed_amount": True,
            "payment_amount": amount_in_paise,
            "description": f"Payment for {owner_name}",
            "close_by": int(time.time()) + 900
        })

        return jsonify({
            'success': True,
            'qr_id': qr_data['id'],
            'image_url': qr_data['image_url']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/check_qr_status/<qr_id>', methods=['GET'])
def check_qr_status(qr_id):
    try:
        qr_data = razorpay_client.qrcode.fetch(qr_id)
        if (qr_data.get('status') == 'closed' and qr_data.get('close_reason') == 'paid') or qr_data.get('payments_count_received', 0) > 0:
            return jsonify({'success': True, 'paid': True})
        else:
            return jsonify({'success': True, 'paid': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# --- PLACE ORDER ---
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
        elif payment_mode == 'qr':
            razorpay_qr_id = data.get('razorpay_qr_id')
            if not razorpay_qr_id:
                return jsonify({"status": "error", "message": "Missing Razorpay QR payment identifier."}), 400
            
            data['payment_type'] = f"Online Paid (Dynamic QR ID: {razorpay_qr_id})"
        else:
            data['payment_type'] = "Cash on Delivery (COD)"

        order_id = "ADOR-" + str(random.randint(10000, 99999))
        data['order_id'] = order_id
        data['date'] = datetime.datetime.now().strftime("%b %d, %Y - %I:%M %p")
        data['client_ip'] = request.remote_addr
        data['status_step'] = 1
        data['status_text'] = "Order Placed"
        data['acceptance_status'] = "Accepted"
        data['payment_mode'] = payment_mode

        full_address = f"{data.get('street', '')}, Landmark: {data.get('landmark', '')}, {data.get('city', '')}, {data.get('state', '')} - {data.get('pincode', '')}"
        data['full_address'] = full_address

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

        # Register customer
        add_or_update_customer(data['name'], data['email'], data['phone'])

        # Send email + SMS
        qr_target_url = f"http://127.0.0.1:5644/order_history/{order_id}"
        send_order_email_and_sms(data, order_id, qr_target_url)

        return jsonify({"status": "success", "order_id": order_id, "date": data['date']})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/order_success/<order_id>')
def order_success_page(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    return render_template_string(SUCCESS_TEMPLATE, order=order, order_id=order_id, settings=SETTINGS)

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

@app.route('/admin/download_invoice/<order_id>')
def admin_download_invoice(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    if not order:
        return "Order not found", 404
    
    qr_target_url = f"http://127.0.0.1:5644/order_history/{order_id}"
    
    if REPORTLAB_AVAILABLE:
        pdf_bytes = generate_order_pdf(order, order_id, qr_target_url)
        if pdf_bytes:
            return send_file(io.BytesIO(pdf_bytes), download_name=f"Invoice_{order_id}.pdf", mimetype='application/pdf')
    
    return render_template_string(HTML_INVOICE_TEMPLATE, order=order, settings=SETTINGS)

@app.route('/admin/print_label/<order_id>')
def admin_print_label(order_id):
    order = next((o for o in ORDERS if o['order_id'] == order_id), None)
    if not order:
        return "Order not found", 404
    return render_template_string(SHIPPING_LABEL_TEMPLATE, order=order, settings=SETTINGS)

@app.route('/api/admin/resend_invoice', methods=['POST'])
def admin_resend_invoice():
    try:
        data = request.get_json() or {}
        order_id = data.get('order_id')
        order = next((o for o in ORDERS if o['order_id'] == order_id), None)
        if not order:
            return jsonify({"success": False, "message": "Order not found"}), 404
        
        full_address = order.get('full_address', '')
        qr_target_url = f"http://127.0.0.1:5644/order_history/{order_id}"
        send_order_email_and_sms(order, order_id, qr_target_url)
        return jsonify({"success": True, "message": "Invoice email and SMS initiated successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# --- CERTIFICATIONS ADMIN ROUTES ---
@app.route('/api/admin/add_certification', methods=['POST'])
def admin_add_certification():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    link = data.get('link', '#').strip()
    logo = data.get('logo', '').strip()
    if not name:
        return jsonify({"success": False, "message": "Name is required"}), 400
    CERTIFICATIONS.append({"name": name, "link": link, "logo": logo})
    return jsonify({"success": True})

@app.route('/api/admin/delete_certification', methods=['POST'])
def admin_delete_certification():
    data = request.get_json() or {}
    idx = data.get('index')
    if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(CERTIFICATIONS):
        return jsonify({"success": False, "message": "Invalid index"}), 400
    del CERTIFICATIONS[idx]
    return jsonify({"success": True})

# --- BROADCAST MESSAGE (ADMIN) ---
@app.route('/api/admin/send_broadcast', methods=['POST'])
def admin_send_broadcast():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"success": False, "message": "Message cannot be empty"}), 400

    # Send to all customers (email + SMS)
    for customer in CUSTOMERS:
        name = customer.get('name', 'Customer')
        email = customer.get('email')
        phone = customer.get('phone')

        # Email
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📢 Important Update from CHIRANJEEVI"
            msg['From'] = f"CHIRANJEEVI <{SMTP_EMAIL}>"
            msg['To'] = email

            html_content = f"""
            <html>
            <body style="font-family: 'Poppins', sans-serif; background: #FAF7F0; padding: 30px;">
                <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 20px;">
                    <h2 style="color: #1b4332;">Hello {name},</h2>
                    <p style="font-size: 15px; line-height: 1.6;">{message}</p>
                    <br>
                    <p style="font-size: 13px; color: #777;">— CHIRANJEEVI  Team</p>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(html_content, 'html'))
            trigger_async_email(msg, email)
        except Exception as e:
            print(f"Broadcast email to {email} failed: {e}")

        # SMS
        try:
            sms_msg = f"CHIRANJEEVI: {message[:140]}"
            trigger_async_sms(phone, sms_msg)
        except Exception as e:
            print(f"Broadcast SMS to {phone} failed: {e}")

    return jsonify({"success": True, "message": f"Broadcast sent to {len(CUSTOMERS)} customers."})

# --- COUPON MANAGEMENT (ADMIN) ---
@app.route('/api/admin/create_coupon', methods=['POST'])
def admin_create_coupon():
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    discount = data.get('discount', 0)
    if not code or discount <= 0:
        return jsonify({"success": False, "message": "Coupon code and discount (positive) required."}), 400
    # Check if code already exists
    for c in COUPONS:
        if c['code'] == code:
            return jsonify({"success": False, "message": "Coupon code already exists."}), 400
    COUPONS.append({"code": code, "discount": float(discount), "active": True})
    return jsonify({"success": True, "message": f"Coupon {code} created with {discount}% discount."})

@app.route('/api/admin/delete_coupon', methods=['POST'])
def admin_delete_coupon():
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    for i, c in enumerate(COUPONS):
        if c['code'] == code:
            del COUPONS[i]
            return jsonify({"success": True, "message": "Coupon deleted."})
    return jsonify({"success": False, "message": "Coupon not found."}), 404

@app.route('/api/admin/toggle_coupon', methods=['POST'])
def admin_toggle_coupon():
    data = request.get_json() or {}
    code = data.get('code', '').strip().upper()
    for c in COUPONS:
        if c['code'] == code:
            c['active'] = not c.get('active', True)
            return jsonify({"success": True, "message": f"Coupon {code} {'activated' if c['active'] else 'deactivated'}."})
    return jsonify({"success": False, "message": "Coupon not found."}), 404

# --- ADMIN PANEL ROUTES ---
@app.route('/admin')
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE, products=PRODUCTS, orders=ORDERS, settings=SETTINGS, slides=SLIDES, ads=ADS, certifications=CERTIFICATIONS, customers=CUSTOMERS, coupons=COUPONS)

@app.route('/api/admin/update_status', methods=['POST'])
def admin_update_status():
    data = request.get_json()
    order_id = data.get('order_id')
    step = int(data.get('step', 1))
    status_map = {1: "Order Placed", 2: "Packaging", 3: "Shipped", 4: "Delivered", 5: "Refunded"}
    
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['status_step'] = step
            new_text = status_map.get(step, "Processing")
            o['status_text'] = new_text
            # Send email + SMS
            if step == 5:
                send_refund_email_and_sms(o, o['order_id'], o['amount'])
            else:
                send_status_update_email_and_sms(o, o['order_id'], step, new_text)
    return jsonify({"success": True})

@app.route('/api/admin/accept_order', methods=['POST'])
def admin_accept_order():
    data = request.get_json()
    order_id = data.get('order_id')
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['acceptance_status'] = "Accepted"
            o['status_step'] = 1
            o['status_text'] = "Order Placed"
            # Optionally send acceptance SMS/email? We already send on place_order.
    return jsonify({"success": True})

@app.route('/api/admin/reject_order', methods=['POST'])
def admin_reject_order():
    data = request.get_json()
    order_id = data.get('order_id')
    for o in ORDERS:
        if o['order_id'] == order_id:
            o['acceptance_status'] = "Rejected"
            o['status_step'] = 0
            o['status_text'] = "Order Cancelled & Refunded"
            send_rejection_email_and_sms(o, o['order_id'], o['amount'])
    return jsonify({"success": True})

@app.route('/api/admin/add_ad', methods=['POST'])
def admin_add_ad():
    title = request.form.get('title', 'Advertisement')
    link = request.form.get('link', '#')
    desc = request.form.get('desc', '')
    image_file = request.files.get('image_file')
    if not image_file or image_file.filename == '':
        return "Image required", 400
    img_bytes = image_file.read()
    image_b64 = f"data:{image_file.content_type};base64,{base64.b64encode(img_bytes).decode('utf-8')}"
    new_id = max([a['id'] for a in ADS], default=0) + 1
    ADS.append({
        "id": new_id,
        "image": image_b64,
        "link": link,
        "title": title,
        "desc": desc
    })
    return redirect('/admin')

@app.route('/api/admin/delete_ad', methods=['POST'])
def admin_delete_ad():
    data = request.get_json()
    ad_id = int(data.get('id'))
    global ADS
    ADS = [a for a in ADS if a['id'] != ad_id]
    return jsonify({"success": True})

@app.route('/api/admin/add_product', methods=['POST'])
def admin_add_product():
    name = request.form.get('name')
    category = request.form.get('category')
    desc = request.form.get('desc', '')
    ingredients = request.form.get('ingredients', '')
    geography = request.form.get('geography', 'Organically sourced from indigenous Indian herb fields.')
    extraction = request.form.get('extraction', 'Cold pressed & hydro-distilled.')
    original_price = request.form.get('original_price')
    
    # Variants
    sizes = request.form.getlist('variant_size[]')
    prices = request.form.getlist('variant_price[]')
    stocks = request.form.getlist('variant_stock[]')
    variants = []
    for i in range(len(sizes)):
        if sizes[i].strip() and prices[i].strip() and stocks[i].strip():
            variants.append({
                "size": sizes[i].strip(),
                "price": float(prices[i]),
                "stock": int(stocks[i])
            })
    if not variants:
        variants = [{"size": "Standard", "price": float(request.form.get('price', 0)), "stock": int(request.form.get('stock', 0))}]

    # Main image
    image_file = request.files.get('image_file')
    if image_file and image_file.filename != '':
        img_bytes = image_file.read()
        main_image = f"data:{image_file.content_type};base64,{base64.b64encode(img_bytes).decode('utf-8')}"
    else:
        main_image = "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=500&q=80"

    # Media: images and videos (unlimited)
    media = []
    gallery_images = request.files.getlist('gallery_images[]')
    for gf in gallery_images:
        if gf and gf.filename != '':
            gb = gf.read()
            media.append({"type": "image", "url": f"data:{gf.content_type};base64,{base64.b64encode(gb).decode('utf-8')}"})
    gallery_videos = request.files.getlist('gallery_videos[]')
    for vf in gallery_videos:
        if vf and vf.filename != '':
            vb = vf.read()
            media.append({"type": "video", "url": f"data:{vf.content_type};base64,{base64.b64encode(vb).decode('utf-8')}"})

    if not media:
        media.append({"type": "image", "url": main_image})

    video_file = request.files.get('video_file')
    video_b64 = ""
    if video_file and video_file.filename != '':
        vid_bytes = video_file.read()
        video_b64 = f"data:{video_file.content_type};base64,{base64.b64encode(vid_bytes).decode('utf-8')}"
        if not any(m['type'] == 'video' for m in media):
            media.append({"type": "video", "url": video_b64})

    new_id = max([p['id'] for p in PRODUCTS], default=0) + 1
    new_prod = {
        "id": new_id,
        "name": name,
        "category": category,
        "image": main_image,
        "media": media,
        "video": video_b64,
        "desc": desc,
        "ingredients": ingredients,
        "geography": geography,
        "extraction": extraction,
        "rating": 5.0,
        "reviews_count": 1,
        "badge": "New",
        "original_price": float(original_price) if original_price else None,
        "status": "active",
        "variants": variants
    }
    PRODUCTS.append(new_prod)
    return redirect('/admin')

@app.route('/api/admin/update_gallery', methods=['POST'])
def admin_update_gallery():
    prod_id = int(request.form.get('product_id'))
    product = next((p for p in PRODUCTS if p['id'] == prod_id), None)
    if not product:
        return "Product not found", 404
    new_media = []
    gallery_images = request.files.getlist('gallery_images[]')
    for gf in gallery_images:
        if gf and gf.filename != '':
            gb = gf.read()
            new_media.append({"type": "image", "url": f"data:{gf.content_type};base64,{base64.b64encode(gb).decode('utf-8')}"})
    gallery_videos = request.files.getlist('gallery_videos[]')
    for vf in gallery_videos:
        if vf and vf.filename != '':
            vb = vf.read()
            new_media.append({"type": "video", "url": f"data:{vf.content_type};base64,{base64.b64encode(vb).decode('utf-8')}"})
    if new_media:
        product['media'] = new_media
    return redirect('/admin')

@app.route('/api/admin/edit_product', methods=['POST'])
def admin_edit_product():
    data = request.get_json()
    prod_id = int(data.get('id'))
    for p in PRODUCTS:
        if p['id'] == prod_id:
            p['name'] = data.get('name', p['name'])
            p['status'] = data.get('status', p['status'])
            if data.get('variants'):
                p['variants'] = data['variants']
            if data.get('original_price'):
                p['original_price'] = data['original_price']
    return jsonify({"success": True})

@app.route('/api/admin/delete_product', methods=['POST'])
def admin_delete_product():
    data = request.get_json()
    prod_id = int(data.get('id'))
    global PRODUCTS
    PRODUCTS = [p for p in PRODUCTS if p['id'] != prod_id]
    return jsonify({"success": True})

@app.route('/api/admin/add_slide', methods=['POST'])
def admin_add_slide():
    image_files = request.files.getlist('image_files')
    if not image_files:
        return "At least one image required", 400
    titles = request.form.getlist('title[]')
    badges = request.form.getlist('badge[]')
    descs = request.form.getlist('desc[]')
    videos = request.files.getlist('video_files')
    for idx, img_file in enumerate(image_files):
        if img_file and img_file.filename != '':
            img_bytes = img_file.read()
            image_b64 = f"data:{img_file.content_type};base64,{base64.b64encode(img_bytes).decode('utf-8')}"
            title = titles[idx] if idx < len(titles) and titles[idx].strip() else f"Slide {idx+1}"
            badge = badges[idx] if idx < len(badges) and badges[idx].strip() else ""
            desc = descs[idx] if idx < len(descs) and descs[idx].strip() else ""
            video_b64 = ""
            if idx < len(videos) and videos[idx] and videos[idx].filename != '':
                vid_bytes = videos[idx].read()
                video_b64 = f"data:{videos[idx].content_type};base64,{base64.b64encode(vid_bytes).decode('utf-8')}"
            new_id = max([s['id'] for s in SLIDES], default=0) + 1
            SLIDES.append({
                "id": new_id,
                "image": image_b64,
                "video": video_b64,
                "badge": badge,
                "title": title,
                "desc": desc
            })
    return redirect('/admin')

@app.route('/api/admin/delete_slide', methods=['POST'])
def admin_delete_slide():
    data = request.get_json()
    slide_id = int(data.get('id'))
    global SLIDES
    SLIDES = [s for s in SLIDES if s['id'] != slide_id]
    return jsonify({"success": True})

@app.route('/api/admin/update_logo', methods=['POST'])
def admin_update_logo():
    logo_file = request.files.get('logo_file')
    if logo_file and logo_file.filename != '':
        logo_bytes = logo_file.read()
        logo_b64 = f"data:{logo_file.content_type};base64,{base64.b64encode(logo_bytes).decode('utf-8')}"
        SETTINGS['logo'] = logo_b64
    return redirect('/admin')

# ==================== UPDATED TEMPLATE – with coupon integration ====================
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CHIRANJEEVI  | Pure Herbal & Botanical Solutions</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
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
        
        /* Search + Filter bar */
        .search-filter-bar { 
            display: flex; 
            flex-wrap: wrap; 
            gap: 15px; 
            margin-bottom: 35px; 
            background: white; 
            padding: 18px 25px; 
            border-radius: 16px; 
            box-shadow: 0 5px 20px rgba(0,0,0,0.03); 
            align-items: center; 
            justify-content: space-between;
        }
        .search-box {
            display: flex;
            align-items: center;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 30px;
            padding: 5px 15px;
            flex: 1 1 260px;
            max-width: 380px;
        }
        .search-box input {
            border: none;
            background: transparent;
            padding: 10px 5px;
            font-size: 13px;
            outline: none;
            width: 100%;
            font-weight: 400;
            color: var(--text-dark);
        }
        .search-box i {
            color: #94a3b8;
            font-size: 14px;
        }
        .category-tabs { display: flex; flex-wrap: wrap; gap: 10px; }
        .cat-tab { padding: 9px 20px; border-radius: 25px; border: 1px solid #ddd; background: #f9f9f9; color: var(--text-dark); font-size: 13px; font-weight: 500; cursor: pointer; transition: 0.3s; }
        .cat-tab:hover, .cat-tab.active { background: var(--green-primary); color: white; border-color: var(--green-primary); }
        
        .sort-dropdown-container select { padding: 10px 18px; border-radius: 20px; border: 1px solid #ddd; background: #f9f9f9; font-size: 13px; color: var(--text-dark); outline: none; cursor: pointer; font-weight: 500; }

        /* ---------- UPDATED PRODUCT GRID (4‑col, clean cards) ---------- */
        .product-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); 
            gap: 25px; 
        }
        @media (max-width: 768px) {
            .product-grid { grid-template-columns: repeat(2, 1fr); gap: 15px; }
        }
        @media (max-width: 480px) {
            .product-grid { grid-template-columns: 1fr; }
        }

        .product-card { 
            background: white; 
            border-radius: 16px; 
            overflow: hidden; 
            box-shadow: 0 8px 24px rgba(0,0,0,0.04); 
            transition: 0.3s; 
            position: relative; 
            display: flex; 
            flex-direction: column; 
            border: 1px solid #f0f0f0;
            padding-bottom: 12px;
        }
        .product-card:hover { 
            transform: translateY(-4px); 
            box-shadow: 0 12px 32px rgba(27, 67, 50, 0.08); 
            border-color: #e0e0e0; 
        }

        .product-badge { 
            position: absolute; top: 10px; left: 10px; 
            background: var(--accent-gold); color: white; 
            font-size: 9px; font-weight: 700; 
            padding: 3px 10px; border-radius: 12px; 
            z-index: 2; text-transform: uppercase; letter-spacing: 0.3px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .product-badge.green { background: var(--green-primary); }
        .product-badge.dark { background: #2b2b2b; }

        .product-media-container { 
            height: 200px; 
            overflow: hidden; 
            background: #f7f5f0; 
            position: relative; 
            cursor: pointer; 
        }
        .product-media-container img, 
        .product-media-container video { 
            width: 100%; 
            height: 100%; 
            object-fit: cover; 
            transition: transform 0.5s ease; 
        }
        .product-card:hover .product-media-container img { transform: scale(1.03); }

        .product-info { 
            padding: 12px 14px 8px; 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            justify-content: space-between; 
        }
        .product-name { 
            font-size: 14px; 
            font-weight: 600; 
            color: var(--text-dark); 
            margin-bottom: 2px; 
            line-height: 1.3; 
            white-space: nowrap; 
            overflow: hidden; 
            text-overflow: ellipsis; 
        }
        .rating-row {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            color: #f59e0b;
            margin-bottom: 4px;
        }
        .rating-row span {
            color: #777;
            margin-left: 4px;
            font-weight: 400;
        }

        .price-row { 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            margin: 4px 0 6px 0; 
            flex-wrap: wrap; 
        }
        .current-price { 
            font-size: 18px; 
            font-weight: 700; 
            color: var(--green-light); 
        }
        .original-price { 
            font-size: 13px; 
            color: #999; 
            text-decoration: line-through; 
        }
        .discount-badge { 
            background: #fee2e2; 
            color: #b91c1c; 
            font-size: 10px; 
            font-weight: 700; 
            padding: 1px 6px; 
            border-radius: 10px; 
        }

        /* "Or Pay ₹..." installment hint */
        .installment-row {
            font-size: 11px;
            color: #555;
            display: flex;
            align-items: center;
            gap: 4px;
            margin-bottom: 6px;
        }
        .installment-row i {
            color: #22c55e;
            font-size: 12px;
        }
        .installment-row strong {
            color: var(--green-primary);
        }

        .btn-group { 
            display: flex; 
            gap: 8px; 
            margin-top: 6px; 
        }
        .btn-cart { 
            flex: 1; 
            padding: 8px 0; 
            background: var(--cream-dark); 
            color: var(--green-primary); 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600; 
            font-size: 12px; 
            transition: 0.2s; 
        }
        .btn-cart:hover { background: #e5dfd5; }
        .btn-buy { 
            flex: 1; 
            padding: 8px 0; 
            background: var(--green-primary); 
            color: white; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600; 
            font-size: 12px; 
            transition: 0.2s; 
        }
        .btn-buy:hover { background: var(--green-light); }

        /* Hide variant selector on main grid – keep it simple */
        .variant-selector { display: none; }

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

        .saved-addr-dropdown { width: 100%; padding: 12px; border: 1.5px solid #e2e8f0; border-radius: 12px; background: #f8fafc; font-size: 13.5px; margin-bottom: 12px; outline: none; cursor: pointer; }
        .saved-addr-dropdown:focus { border-color: var(--green-primary); }
        .new-addr-label { font-size: 12px; color: #64748b; margin-top: 4px; display: block; }

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

        .marquee-section { background: #1a2e26; padding: 12px 0; overflow: hidden; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .marquee-track { display: flex; animation: marqueeScroll 25s linear infinite; width: max-content; }
        .marquee-track:hover { animation-play-state: paused; }
        .marquee-item { display: flex; align-items: center; gap: 12px; padding: 0 30px; color: #ccc; font-size: 13px; font-weight: 500; white-space: nowrap; }
        .marquee-item img { height: 28px; width: auto; filter: brightness(0) invert(1); opacity: 0.7; transition: 0.3s; }
        .marquee-item:hover img { opacity: 1; }
        .marquee-item a { color: #ccc; text-decoration: none; display: flex; align-items: center; gap: 10px; }
        .marquee-item a:hover { color: var(--accent-gold); }
        @keyframes marqueeScroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
    </style>
</head>
<body>

    <div id="toast"><i class="fa-solid fa-circle-check" style="font-size: 18px;"></i> <span id="toast-msg">Item added to your basket</span></div>

    <header>
        <div class="nav-left">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
            <div class="brand-container" onclick="window.scrollTo(0,0)">
                <img src="{{ settings.logo }}" alt="Logo" class="logo-img" id="header-logo">
                <div class="logo"><span>Chiranjeevi</span></div>
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

    <!-- HERO SLIDER -->
    <section class="hero-slider" data-aos="fade-in" data-aos-duration="1000">
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

    <div class="features-banner" data-aos="fade-up" data-aos-delay="100">
        <div class="feature-item"><i class="fa-solid fa-leaf" style="color:var(--accent-gold); font-size: 18px;"></i> 100% Certified Organic</div>
        <div class="feature-item"><i class="fa-solid fa-truck-fast" style="color:var(--accent-gold); font-size: 18px;"></i> Express Pan-India Shipping</div>
        <div class="feature-item"><i class="fa-solid fa-shield-cat" style="color:var(--accent-gold); font-size: 18px;"></i> Cruelty-Free & Vegan</div>
        <div class="feature-item"><i class="fa-solid fa-flask" style="color:var(--accent-gold); font-size: 18px;"></i> Zero Sulfates & Parabens</div>
    </div>

    <div class="container" id="shop">
        <h2 style="font-family: 'Playfair Display'; font-size: 30px; color: var(--green-primary); margin-bottom: 10px;" class="reveal" data-aos="fade-right">Similar Products</h2>
        <p style="color: #666; font-size: 14px; margin-bottom: 25px;" class="reveal" data-aos="fade-right" data-aos-delay="100">Explore our curated collection of premium botanical essentials.</p>
        
        <div class="search-filter-bar reveal" data-aos="fade-up" data-aos-delay="150">
            <div class="search-box">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" id="searchInput" placeholder="Search products..." onkeyup="filterProducts()">
            </div>
            <div class="category-tabs">
                <button class="cat-tab active" onclick="filterCategory('All', this)">All</button>
                <button class="cat-tab" onclick="filterCategory('Apparel', this)">Apparel</button>
                <button class="cat-tab" onclick="filterCategory('Fragrance', this)">Fragrance</button>
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
            <div class="product-card reveal" data-id="{{ p.id }}" data-category="{{ p.category }}" data-name="{{ p.name }}" data-variants="{{ p.variants | tojson }}" data-aos="fade-up" data-aos-delay="{{ loop.index0 * 50 }}">
                {% if p.badge %}
                <div class="product-badge {% if 'PREMIUM' in p.badge %}green{% elif 'GENTLE' in p.badge %}dark{% endif %}">{{ p.badge }}</div>
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
                        <div class="product-name">{{ p.name }}</div>
                        <div class="rating-row">
                            {% set full_stars = (p.rating|default(0))|int %}
                            {% set half_star = (p.rating|default(0)) % 1 >= 0.5 %}
                            {% for s in range(5) %}
                                {% if s < full_stars %}
                                    <i class="fa-solid fa-star"></i>
                                {% elif s == full_stars and half_star %}
                                    <i class="fa-solid fa-star-half-stroke"></i>
                                {% else %}
                                    <i class="fa-regular fa-star"></i>
                                {% endif %}
                            {% endfor %}
                            <span>({{ p.reviews_count|default(0) }})</span>
                        </div>
                        <div class="price-row">
                            {% set first_variant = p.variants[0] %}
                            <span class="current-price" id="price-display-{{ p.id }}">₹{{ first_variant.price }}</span>
                            {% if p.original_price %}
                            <span class="original-price">₹{{ p.original_price }}</span>
                            {% set discount = ((p.original_price - first_variant.price) / p.original_price * 100) | round(0) %}
                            <span class="discount-badge">{{ discount }}%</span>
                            {% endif %}
                        </div>
                        <!-- "Or Pay ₹..." installment hint -->
                        <div class="installment-row">
                            <i class="fa-regular fa-circle-check"></i>
                            <span>Or Pay <strong>₹{{ (first_variant.price * 0.7)|round(0) }}</strong> + 🟢 <strong>{{ (first_variant.price / 50)|round(0) }}</strong></span>
                        </div>
                    </div>
                    <div class="btn-group">
                        <button class="btn-cart" onclick="addToCartAndFly(event, {{ p.id }})"><i class="fa-solid fa-cart-plus"></i> Add</button>
                        <button class="btn-buy" onclick="buyNow({{ p.id }})">Buy Now</button>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Testimonials -->
    <section class="testimonials-section" data-aos="fade-up">
        <h2 style="font-family: 'Playfair Display'; font-size: 28px; color: var(--green-primary); margin-bottom: 10px;">Loved by Our Botanical Community</h2>
        <p style="color: #666; font-size: 14px;">Here is what our customers have to say about their transformations.</p>
        <div class="testimonials-grid">
            <div class="testimonial-card" data-aos="zoom-in" data-aos-delay="100">
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
            <div class="testimonial-card" data-aos="zoom-in" data-aos-delay="200">
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
            <div class="testimonial-card" data-aos="zoom-in" data-aos-delay="300">
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

    <!-- CERTIFICATIONS MARQUEE -->
    <div class="marquee-section">
        <div class="marquee-track">
            {% for cert in certifications %}
            <div class="marquee-item">
                <a href="{{ cert.link }}" target="_blank">
                    {% if cert.logo %}
                    <img src="{{ cert.logo }}" alt="{{ cert.name }}">
                    {% else %}
                    <span style="color:var(--accent-gold); font-weight:700;">✦</span>
                    {% endif %}
                    <span>{{ cert.name }}</span>
                </a>
            </div>
            {% endfor %}
            <!-- Duplicate for seamless loop -->
            {% for cert in certifications %}
            <div class="marquee-item">
                <a href="{{ cert.link }}" target="_blank">
                    {% if cert.logo %}
                    <img src="{{ cert.logo }}" alt="{{ cert.name }}">
                    {% else %}
                    <span style="color:var(--accent-gold); font-weight:700;">✦</span>
                    {% endif %}
                    <span>{{ cert.name }}</span>
                </a>
            </div>
            {% endfor %}
        </div>
    </div>

    <footer class="main-footer">
        <div class="footer-grid">
            <div>
                <h3>CHIRANJEEVI </h3>
                <p style="font-size: 13px; line-height: 1.7; color: #ddd;">Helping you reach the peak of your physical, mental, and spiritual well-being — nurturing harmony within, inspiring conscious living, and connecting you with the healing essence of nature..</p>
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
            &copy; 2026 CHIRANJEEVI. All Rights Reserved. Crafted with pure herbal care.
        </div>
    </footer>

    <!-- CART MODAL -->
    <div class="modal" id="cartModal">
        <div class="modal-content">
            <span class="close-sidebar" onclick="document.getElementById('cartModal').style.display='none'" style="position:absolute; right:24px; top:24px; z-index:10; font-size:22px;">&times;</span>
            <div id="checkout-step-1">
                <h3 style="color:var(--green-primary); margin-bottom:16px; font-family:'Playfair Display'; font-size:22px;">Shipping Address</h3>
                <select class="saved-addr-dropdown" id="savedAddressSelect" onchange="loadSelectedAddress(this.value)">
                    <option value="">— Select a saved address —</option>
                </select>
                <span class="new-addr-label">Or fill in a new address below (it will be saved automatically)</span>
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
                                <span style="font-weight:600; display:block;">Online Payment (Razorpay Checkout)</span>
                                <span style="font-size:11.5px; color:#64748b;">UPI (GPay/PhonePe), Credit/Debit Cards, NetBanking</span>
                            </div>
                        </div>
                        <span class="payment-fee-badge fee-online">+₹0 Shipping</span>
                    </label>
                    <label class="payment-card" id="payCardQr" onclick="selectPaymentMode('qr')">
                        <div class="payment-card-left">
                            <input type="radio" name="pay_mode" value="qr">
                            <div>
                                <span style="font-weight:600; display:block;">UPI QR Code (Instant Scan)</span>
                                <span style="font-size:11.5px; color:#64748b;">Scan dynamic QR using any UPI app (GPay/PhonePe/Paytm)</span>
                            </div>
                        </div>
                        <span class="payment-fee-badge fee-online">+₹0 Shipping</span>
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
                    <div class="bill-row" id="discount-row" style="display:none; color:#166534;"><span>Discount (<span id="coupon-discount-percent">10</span>% OFF):</span><span id="bill-discount" style="font-weight:600;">-₹0</span></div>
                    <div class="bill-row" id="shipping-fee-row"><span>Shipping Fee:</span><span id="shipping-fee-val" style="font-weight:600;">₹0</span></div>
                    <div class="bill-row" id="cod-fee-row" style="display:none; color:#991b1b;"><span>COD Handling Fee:</span><span style="font-weight:600;">₹99</span></div>
                    <div class="bill-row"><span>GST (Included 18%):</span><span id="bill-gst" style="font-weight:600;">₹0</span></div>
                    <div class="bill-row total"><span>Total Payable:</span><span id="bill-total">₹0</span></div>
                </div>
                <button type="button" class="btn-primary" style="width:100%; border-radius:14px; font-size:15px;" id="payBtn" onclick="placeOrder()">Confirm Order</button>
            </div>
            <div id="checkout-step-qr" style="display:none; text-align:center;">
                <button class="btn-back" onclick="cancelQrFlow()" style="margin-bottom:15px; padding:6px 14px; border-radius:8px; font-size:12px; float: left;"><i class="fa-solid fa-arrow-left"></i> Change Method</button>
                <div style="clear:both;"></div>
                <h3 style="color:var(--green-primary); margin:10px 0 5px; font-family:'Playfair Display'; font-size:22px;">Scan & Pay Instantly</h3>
                <p style="font-size:12px; color:#666; margin-bottom:15px;">Scan using any UPI app (GPay, PhonePe, Paytm, BHIM)</p>
                <div style="background: white; border: 2.5px solid var(--accent-gold); display: inline-block; padding: 20px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 15px;">
                    <img id="checkout-qr-image" style="width: 300px; height: 300px; object-fit: contain; margin: 0 auto;" alt="Dynamic UPI QR Code">
                </div>
                <h3 id="checkout-qr-brand" style="color:var(--green-primary); font-size:16px; font-weight:700; margin-bottom:4px;">CHIRANJEEVI</h3>
                <p id="checkout-qr-amount" style="font-size:22px; font-weight:800; color:var(--green-light); margin-bottom:15px;"></p>
                <div style="display:flex; align-items:center; justify-content:center; gap:8px; background:rgba(27,67,50,0.08); padding:10px; border-radius:10px; margin-bottom:15px;">
                    <i class="fa-solid fa-circle-notch fa-spin" style="color:var(--green-primary);"></i>
                    <span style="font-size:12px; color:var(--green-primary); font-weight:500;">Waiting for dynamic payment confirmation...</span>
                </div>
                <button type="button" onclick="manualCheckQrStatus()" class="btn-primary" style="width:100%; border-radius:12px; font-size:13px; padding:10px; background:var(--green-light); margin-bottom:12px;">⚡ Verify Payment Status (Instant Check)</button>
                <p style="font-size:11px; color:#888;">Do not close this screen or press back until your transaction completes.</p>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <script>
        AOS.init({ once: true, offset: 80, duration: 800 });

        const productsData = {{ products | tojson }};
        // Coupons from server
        const couponsData = {{ coupons | tojson }};
        let cart = JSON.parse(localStorage.getItem('adorica_cart') || '[]');
        let currentCategory = 'All';
        let discountPercent = 0; // will be set by coupon

        // ----- ADDRESS MANAGEMENT -----
        let savedAddresses = JSON.parse(localStorage.getItem('adorica_addresses') || '[]');

        function populateSavedAddresses() {
            const select = document.getElementById('savedAddressSelect');
            select.innerHTML = '<option value="">— Select a saved address —</option>';
            savedAddresses.forEach((addr, idx) => {
                const opt = document.createElement('option');
                opt.value = idx;
                opt.textContent = `${addr.name} - ${addr.city} (${addr.phone})`;
                select.appendChild(opt);
            });
        }

        function loadSelectedAddress(index) {
            if (index === '') {
                document.getElementById('cust-name').value = '';
                document.getElementById('cust-email').value = '';
                document.getElementById('cust-phone').value = '';
                document.getElementById('cust-pincode').value = '';
                document.getElementById('cust-city').value = '';
                document.getElementById('cust-state').value = '';
                document.getElementById('cust-street').value = '';
                document.getElementById('cust-landmark').value = '';
                return;
            }
            const addr = savedAddresses[parseInt(index)];
            if (addr) {
                document.getElementById('cust-name').value = addr.name || '';
                document.getElementById('cust-email').value = addr.email || '';
                document.getElementById('cust-phone').value = addr.phone || '';
                document.getElementById('cust-pincode').value = addr.pincode || '';
                document.getElementById('cust-city').value = addr.city || '';
                document.getElementById('cust-state').value = addr.state || '';
                document.getElementById('cust-street').value = addr.street || '';
                document.getElementById('cust-landmark').value = addr.landmark || '';
                if (addr.pincode) detectPinCode(addr.pincode);
            }
        }

        function saveCurrentAddress() {
            const addr = {
                name: document.getElementById('cust-name').value.trim(),
                email: document.getElementById('cust-email').value.trim(),
                phone: document.getElementById('cust-phone').value.trim(),
                pincode: document.getElementById('cust-pincode').value.trim(),
                city: document.getElementById('cust-city').value.trim(),
                state: document.getElementById('cust-state').value.trim(),
                landmark: document.getElementById('cust-landmark').value.trim(),
                street: document.getElementById('cust-street').value.trim()
            };
            const exists = savedAddresses.some(a => a.email === addr.email && a.phone === addr.phone);
            if (!exists && addr.name && addr.email && addr.phone) {
                savedAddresses.push(addr);
                localStorage.setItem('adorica_addresses', JSON.stringify(savedAddresses));
                populateSavedAddresses();
            }
            localStorage.setItem('adorica_last_address', JSON.stringify(addr));
        }

        function loadLastUsedAddress() {
            const last = localStorage.getItem('adorica_last_address');
            if (last) {
                try {
                    const addr = JSON.parse(last);
                    if (!document.getElementById('cust-name').value) {
                        document.getElementById('cust-name').value = addr.name || '';
                        document.getElementById('cust-email').value = addr.email || '';
                        document.getElementById('cust-phone').value = addr.phone || '';
                        document.getElementById('cust-pincode').value = addr.pincode || '';
                        document.getElementById('cust-city').value = addr.city || '';
                        document.getElementById('cust-state').value = addr.state || '';
                        document.getElementById('cust-street').value = addr.street || '';
                        document.getElementById('cust-landmark').value = addr.landmark || '';
                        if (addr.pincode) detectPinCode(addr.pincode);
                    }
                } catch(e) {}
            }
        }

        function clearAddressForm() {
            document.getElementById('cust-name').value = '';
            document.getElementById('cust-email').value = '';
            document.getElementById('cust-phone').value = '';
            document.getElementById('cust-pincode').value = '';
            document.getElementById('cust-city').value = '';
            document.getElementById('cust-state').value = '';
            document.getElementById('cust-street').value = '';
            document.getElementById('cust-landmark').value = '';
            document.getElementById('savedAddressSelect').value = '';
        }

        // ----- END ADDRESS MANAGEMENT -----

        updateCartUI();
        populateSavedAddresses();

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

        // ----- COMBINED FILTER (category + search) -----
        function filterCategory(category, btn) {
            currentCategory = category;
            document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            filterProducts();
        }

        function sortProducts() {
            filterProducts();
        }

        function filterProducts() {
            let grid = document.getElementById('productGrid');
            let cards = Array.from(grid.getElementsByClassName('product-card'));
            let sortVal = document.getElementById('sortSelect').value;
            let searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();

            cards.forEach(card => {
                let cat = card.getAttribute('data-category');
                let name = card.getAttribute('data-name').toLowerCase();
                let matchCategory = (currentCategory === 'All' || cat.toLowerCase() === currentCategory.toLowerCase());
                let matchSearch = (searchTerm === '' || name.includes(searchTerm));
                card.style.display = (matchCategory && matchSearch) ? 'flex' : 'none';
            });

            let visibleCards = cards.filter(c => c.style.display !== 'none');
            visibleCards.sort((a, b) => {
                let priceA = parseFloat(a.querySelector('.current-price')?.innerText.replace('₹','') || 0);
                let priceB = parseFloat(b.querySelector('.current-price')?.innerText.replace('₹','') || 0);
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

        document.getElementById('searchInput').addEventListener('input', filterProducts);

        function updateProductPrice(prodId) {}

        function addToCartAndFly(event, id) {
            let p = productsData.find(x => x.id === id);
            let firstVariant = p.variants[0];
            let price = firstVariant.price;

            let cartItem = {
                id: p.id,
                name: p.name,
                size: firstVariant.size,
                price: price,
                quantity: 1,
                image: p.image
            };

            let existing = cart.find(x => x.id === id && x.size === firstVariant.size);
            if(existing) { existing.quantity += 1; }
            else { cart.push(cartItem); }
            
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
            let firstVariant = p.variants[0];
            let price = firstVariant.price;

            let cartItem = {
                id: p.id,
                name: p.name,
                size: firstVariant.size,
                price: price,
                quantity: 1,
                image: p.image
            };
            cart = [cartItem]; 
            localStorage.setItem('adorica_cart', JSON.stringify(cart));
            updateCartUI(); 
            openCartModal(); 
        }

        function openCartModal() { 
            document.getElementById('cartModal').style.display = 'flex'; 
            loadLastUsedAddress();
            populateSavedAddresses();
            showCheckoutStep(1);
            updateCartUI(); 
        }

        function showCheckoutStep(stepNum) {
            if(stepNum === 1) {
                document.getElementById('checkout-step-1').style.display = 'block';
                document.getElementById('checkout-step-2').style.display = 'none';
                document.getElementById('checkout-step-qr').style.display = 'none';
            } else {
                document.getElementById('checkout-step-1').style.display = 'none';
                document.getElementById('checkout-step-2').style.display = 'block';
                document.getElementById('checkout-step-qr').style.display = 'none';
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

            saveCurrentAddress();
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
            document.getElementById('payCardQr').classList.toggle('selected', mode === 'qr');
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
                                <div><b style="color:var(--text-dark);">${item.name}</b> <span style="color:#64748b; font-size:12px;">${item.size || ''}</span><br><span style="color:#64748b; font-size:12px;">₹${item.price}</span></div>
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
                        <span class="bt-price">₹${p.variants[0].price}</span>
                        <button type="button" class="bt-add-btn" onclick="addCrossSell(${p.id})">+ Add</button>
                    </div>
                </div>`;
            });
        }

        function addCrossSell(id) {
            let p = productsData.find(x => x.id === id);
            let firstVariant = p.variants[0];
            let cartItem = {
                id: p.id,
                name: p.name,
                size: firstVariant.size,
                price: firstVariant.price,
                quantity: 1,
                image: p.image
            };
            cart.push(cartItem);
            localStorage.setItem('adorica_cart', JSON.stringify(cart));
            updateCartUI();
            renderBetterTogether();
            showToast(`${p.name} added instantly!`);
        }

        // ----- COUPON APPLICATION (dynamic) -----
        function applyCoupon() {
            let code = document.getElementById('coupon-input').value.trim().toUpperCase();
            let msg = document.getElementById('coupon-msg');
            // Find coupon in server data
            const coupon = couponsData.find(c => c.code === code && c.active === true);
            if (coupon) {
                discountPercent = coupon.discount;
                msg.style.color = '#166534';
                msg.innerHTML = `<i class="fa-solid fa-check"></i> Coupon applied: ${discountPercent}% OFF!`;
                document.getElementById('coupon-discount-percent').innerText = discountPercent;
            } else {
                discountPercent = 0;
                msg.style.color = '#991b1b';
                msg.innerHTML = '<i class="fa-solid fa-xmark"></i> Invalid or inactive coupon code.';
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
                document.getElementById('coupon-discount-percent').innerText = discountPercent;
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
                document.getElementById('shipping-fee-val').innerText = '₹0';
                codFeeRow.style.display = 'none';
                total += 0;
                document.getElementById('payBtn').innerHTML = `<i class="fa-solid fa-lock"></i> Pay ₹${total} via Razorpay`;
            } else if(mode === 'qr') {
                shippingFeeRow.style.display = 'flex';
                document.getElementById('shipping-fee-val').innerText = '₹0';
                codFeeRow.style.display = 'none';
                total += 0;
                document.getElementById('payBtn').innerHTML = `<i class="fa-solid fa-qrcode"></i> Generate QR — ₹${total}`;
            } else {
                shippingFeeRow.style.display = 'none';
                codFeeRow.style.display = 'flex';
                total += 99;
                document.getElementById('payBtn').innerHTML = `<i class="fa-solid fa-truck"></i> Confirm Order (COD) — ₹${total}`;
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

        let qrPollInterval = null;
        let activeQrId = null;
        let activeQrAmount = 0;

        function showQrModal(qrId, imageUrl, amount) {
            activeQrId = qrId;
            activeQrAmount = amount;
            document.getElementById('checkout-qr-image').src = imageUrl;
            document.getElementById('checkout-qr-amount').innerText = `₹${amount.toLocaleString('en-IN')}`;
            document.getElementById('checkout-step-1').style.display = 'none';
            document.getElementById('checkout-step-2').style.display = 'none';
            document.getElementById('checkout-step-qr').style.display = 'block';
            startQrPolling(qrId);
        }

        function cancelQrFlow() {
            if (qrPollInterval) clearInterval(qrPollInterval);
            activeQrId = null;
            document.getElementById('checkout-step-qr').style.display = 'none';
            document.getElementById('checkout-step-2').style.display = 'block';
            let payBtn = document.getElementById('payBtn');
            payBtn.disabled = false;
            updateTotal();
        }

        function startQrPolling(qrId) {
            if (qrPollInterval) clearInterval(qrPollInterval);
            qrPollInterval = setInterval(async () => {
                await verifyQrStatus(qrId);
            }, 1000);
        }

        async function manualCheckQrStatus() {
            if (!activeQrId) return;
            await verifyQrStatus(activeQrId);
        }

        async function verifyQrStatus(qrId) {
            try {
                let response = await fetch(`/check_qr_status/${qrId}`);
                let data = await response.json();
                if (data.success && data.paid) {
                    if (qrPollInterval) clearInterval(qrPollInterval);
                    qrPollInterval = null;
                    await finalizeQrOrder();
                }
            } catch (err) {
                console.error("QR status verify error:", err);
            }
        }

        async function finalizeQrOrder() {
            let name = document.getElementById('cust-name').value;
            let email = document.getElementById('cust-email').value;
            let phone = document.getElementById('cust-phone').value;
            let pincode = document.getElementById('cust-pincode').value;
            let city = document.getElementById('cust-city').value;
            let state = document.getElementById('cust-state').value;
            let landmark = document.getElementById('cust-landmark').value;
            let street = document.getElementById('cust-street').value;

            let payload = {
                name, email, phone, pincode, city, state, landmark, street,
                amount: activeQrAmount,
                payment_mode: 'qr',
                items: cart,
                razorpay_qr_id: activeQrId
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
                    clearAddressForm();
                    activeQrId = null;
                    window.location.href = '/order_success/' + data.order_id;
                } else {
                    alert("Order placement failed: " + data.message);
                    cancelQrFlow();
                }
            } catch (e) {
                alert("An error occurred during order confirmation. Please contact support.");
                cancelQrFlow();
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
            saveCurrentAddress();

            let payBtn = document.getElementById('payBtn');
            payBtn.disabled = true;

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
                        clearAddressForm();
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
            } else if (mode === 'qr') {
                payBtn.innerText = "Generating Secure QR Code...";
                try {
                    let response = await fetch('/create_qr_code', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ amount: amt })
                    });
                    let qrData = await response.json();
                    if (qrData.success) {
                        showQrModal(qrData.qr_id, qrData.image_url, amt);
                    } else {
                        alert("QR Generation Error: " + (qrData.error || "Failed to generate"));
                        payBtn.disabled = false;
                        updateTotal();
                    }
                } catch(err) {
                    alert("Failed to connect with payment server. Please try again.");
                    payBtn.disabled = false;
                    updateTotal();
                }
            } else {
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
                        "name": "CHIRANJEEVI",
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
                                    clearAddressForm();
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

        (function() {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('openCart') === 'true') {
                setTimeout(() => {
                    openCartModal();
                    if (window.history && window.history.replaceState) {
                        let cleanUrl = window.location.origin + window.location.pathname;
                        window.history.replaceState({}, document.title, cleanUrl);
                    }
                }, 300);
            }
        })();
    </script>
</body>
</html>
"""

# --- PRODUCT DETAIL TEMPLATE (unchanged) ---
PRODUCT_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ product.name }} | CHIRANJEEVI</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
    <style>
        :root { --cream: #FAF7F0; --cream-dark: #F3EFEA; --green-primary: #1b4332; --green-light: #2d6a4f; --accent-gold: #d4a373; --text-dark: #2b2b2b; --shadow: 0 20px 40px rgba(27, 67, 50, 0.15); }
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }
        body { background-color: var(--cream); color: var(--text-dark); }
        
        header { position: fixed; top: 0; left: 0; width: 100%; background: rgba(250, 247, 240, 0.95); backdrop-filter: blur(12px); display: flex; justify-content: space-between; align-items: center; padding: 15px 30px; z-index: 1000; box-shadow: 0 4px 25px rgba(0,0,0,0.05); }
        .brand-container { display: flex; align-items: center; gap: 12px; cursor: pointer; text-decoration: none; }
        .logo-img { width: 42px; height: 42px; object-fit: cover; border-radius: 50%; border: 2px solid var(--accent-gold); }
        .logo { font-family: 'Playfair Display', serif; font-size: 20px; font-weight: 700; color: var(--green-primary); text-transform: uppercase; }
        .logo span { color: var(--accent-gold); }
        
        .back-link { display: inline-flex; align-items: center; gap: 8px; color: var(--green-primary); font-weight: 600; text-decoration: none; font-size: 14px; transition: 0.2s; margin-bottom: 20px; }
        .back-link:hover { color: var(--accent-gold); }

        .gallery-container { display: flex; flex-direction: column; gap: 12px; }
        .main-image { width: 100%; height: 400px; background: #1a1a1a; border-radius: 16px; overflow: hidden; position: relative; }
        .main-image img, .main-image video { width: 100%; height: 100%; object-fit: contain; }
        .thumbnails { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: thin; }
        .thumb { width: 80px; height: 80px; object-fit: cover; border-radius: 10px; border: 2px solid transparent; cursor: pointer; transition: 0.2s; flex-shrink: 0; }
        .thumb.active { border-color: var(--accent-gold); transform: scale(1.05); }
        .thumb:hover { transform: scale(1.03); }
        .play-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.6); color: white; width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 28px; pointer-events: none; }

        .detail-section { padding: 40px 20px; max-width: 1100px; margin: 80px auto 0; }
        .detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 50px; background: white; padding: 40px; border-radius: 24px; box-shadow: 0 15px 35px rgba(0,0,0,0.05); }
        @media(max-width: 768px) { .detail-grid { grid-template-columns: 1fr; padding: 20px; } }
        
        .product-details-info h1 { font-family: 'Playfair Display', serif; font-size: 32px; color: var(--green-primary); margin-bottom: 12px; }
        .price-tag { font-size: 28px; font-weight: 700; color: var(--green-light); margin: 15px 0; display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
        .orig-price { font-size: 18px; color: #999; text-decoration: line-through; font-weight: 400; }
        .discount-badge { background: #fee2e2; color: #b91c1c; font-size: 14px; font-weight: 700; padding: 4px 12px; border-radius: 20px; }
        .desc-text { font-size: 15px; color: #555; line-height: 1.8; margin-bottom: 20px; }
        .ingredients-box { background: var(--cream-dark); padding: 15px; border-radius: 12px; margin-bottom: 20px; font-size: 14px; }
        .variant-selector-detail { margin: 20px 0; }
        .variant-selector-detail label { font-weight: 600; display: block; margin-bottom: 6px; color: var(--green-primary); }
        .variant-selector-detail select { width: 100%; padding: 12px; border-radius: 12px; border: 1.5px solid #cbd5e1; background: #f8fafc; font-size: 14px; outline: none; cursor: pointer; }

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

        .ad-banner { max-width: 1100px; margin: 40px auto; padding: 0 20px; }
        .ad-banner img { width: 100%; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }
        .ad-banner .ad-link { display: block; text-decoration: none; }

        .related-section { max-width: 1100px; margin: 60px auto; padding: 0 20px; }
        .related-section h2 { font-family: 'Playfair Display', serif; font-size: 28px; color: var(--green-primary); margin-bottom: 25px; text-align: center; }
        .related-scroll { display: flex; gap: 20px; overflow-x: auto; padding-bottom: 15px; scroll-snap-type: x mandatory; }
        .related-card { min-width: 200px; background: white; border-radius: 16px; padding: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.04); text-align: center; border: 1px solid #f0f0f0; scroll-snap-align: start; transition: 0.3s; }
        .related-card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.08); }
        .related-card img { width: 100%; height: 150px; object-fit: cover; border-radius: 12px; }
        .related-card h4 { font-size: 14px; margin: 10px 0 5px; color: var(--green-primary); }
        .related-card .price { font-weight: 700; color: var(--green-light); }
        .related-card a { text-decoration: none; color: inherit; }

        #toast { position: fixed; bottom: 30px; right: 30px; background: var(--green-primary); color: white; padding: 14px 24px; border-radius: 12px; box-shadow: var(--shadow); z-index: 9999; display: flex; align-items: center; gap: 12px; transform: translateY(120px); transition: transform 0.4s ease; font-size: 14px; font-weight: 500; }
        #toast.show { transform: translateY(0); }
    </style>
</head>
<body>

    <div id="toast"><i class="fa-solid fa-circle-check" style="font-size: 18px;"></i> <span id="toast-msg">Item added to your basket</span></div>

    <header>
        <a href="/" class="brand-container">
            <img src="{{ settings.logo }}" alt="Logo" class="logo-img">
            <div class="logo"><span>Chiranjeevi</span></div>
        </a>
        <div style="cursor: pointer; font-size: 18px; color: var(--green-primary); background: var(--cream-dark); padding: 10px 14px; border-radius: 50%;" onclick="window.location.href='/'">
            <i class="fa-solid fa-house"></i>
        </div>
    </header>

    <div class="detail-section" data-aos="fade-up" data-aos-duration="800">
        <div class="detail-grid">
            <div class="gallery-container" data-aos="fade-right">
                <div class="main-image" id="mainImageContainer">
                    <img id="mainImage" src="{{ product.media[0].url if product.media else product.image }}" alt="{{ product.name }}">
                    <div class="play-overlay" id="playOverlay" style="display:none;"><i class="fa-solid fa-play"></i></div>
                </div>
                <div class="thumbnails" id="thumbnailContainer">
                    {% for media in product.media %}
                    <img src="{{ media.url }}" class="thumb {% if loop.first %}active{% endif %}" data-index="{{ loop.index0 }}" data-type="{{ media.type }}" onclick="setMainMedia({{ loop.index0 }})">
                    {% endfor %}
                </div>
            </div>
            <div class="product-details-info" data-aos="fade-left">
                {% if product.badge %}
                <span style="display:inline-block; background:var(--accent-gold); color:white; font-size:11px; font-weight:700; text-transform:uppercase; padding:4px 12px; border-radius:20px; margin-bottom:10px; letter-spacing:1px;">{{ product.badge }}</span>
                {% endif %}
                
                <h1>{{ product.name }}</h1>
                
                <div style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: #f59e0b; margin-bottom: 10px;">
                    <i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star-half-stroke"></i>
                    <span style="color:#666; margin-left: 5px;">({{ product.reviews_count | default(45) }} reviews)</span>
                </div>

                <div class="variant-selector-detail">
                    <label for="variant-select">Choose Size / Volume</label>
                    <select id="variant-select" onchange="updateDetailPrice()">
                        {% for v in product.variants %}
                        <option value="{{ v.size }}" data-price="{{ v.price }}" data-stock="{{ v.stock }}">{{ v.size }} - ₹{{ v.price }} (Stock: {{ v.stock }})</option>
                        {% endfor %}
                    </select>
                </div>

                <div class="price-tag" id="detail-price">
                    ₹{{ product.variants[0].price }}
                    {% if product.original_price %}
                    <span class="orig-price">₹{{ product.original_price }}</span>
                    {% set discount = ((product.original_price - product.variants[0].price) / product.original_price * 100) | round(0) %}
                    <span class="discount-badge">{{ discount }}% OFF</span>
                    {% endif %}
                </div>
                <p style="font-size:13px; color:#2e7d32; font-weight:600;" id="detail-stock">In Stock: {{ product.variants[0].stock }}</p>
                
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

    <!-- Advertisement Banner -->
    {% if ad %}
    <div class="ad-banner" data-aos="fade-up" data-aos-delay="200">
        <a href="{{ ad.link }}" target="_blank" class="ad-link">
            <img src="{{ ad.image }}" alt="{{ ad.title }}">
            <div style="text-align:center; margin-top:8px; font-weight:600; color:var(--green-primary); font-size:16px;">{{ ad.title }} - {{ ad.desc }}</div>
        </a>
    </div>
    {% endif %}

    <!-- Related Products -->
    <div class="related-section" data-aos="fade-up" data-aos-delay="400">
        <h2>You May Also Like</h2>
        <div class="related-scroll">
            {% for r in related %}
            <div class="related-card" data-aos="zoom-in" data-aos-delay="{{ loop.index0 * 50 }}">
                <a href="/product/{{ r.id }}">
                    <img src="{{ r.image }}" alt="{{ r.name }}">
                    <h4>{{ r.name }}</h4>
                    <div class="price">₹{{ r.variants[0].price }}</div>
                </a>
            </div>
            {% endfor %}
        </div>
    </div>

    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <script>
        AOS.init({ once: true });

        // Gallery
        const mediaItems = {{ product.media | tojson }};
        let currentMediaIndex = 0;

        function setMainMedia(index) {
            const media = mediaItems[index];
            if (!media) return;
            currentMediaIndex = index;
            const mainImage = document.getElementById('mainImage');
            const playOverlay = document.getElementById('playOverlay');
            const container = document.getElementById('mainImageContainer');

            if (media.type === 'video') {
                const existingVideo = container.querySelector('video');
                if (existingVideo) existingVideo.remove();
                const img = container.querySelector('img');
                if (img) img.style.display = 'none';

                let video = container.querySelector('video');
                if (!video) {
                    video = document.createElement('video');
                    video.controls = true;
                    video.muted = true;
                    video.autoplay = false;
                    video.style.width = '100%';
                    video.style.height = '100%';
                    video.style.objectFit = 'contain';
                    container.appendChild(video);
                }
                video.src = media.url;
                video.load();
                video.style.display = 'block';
                playOverlay.style.display = 'none';
            } else {
                const video = container.querySelector('video');
                if (video) video.style.display = 'none';
                const img = container.querySelector('img');
                if (img) {
                    img.src = media.url;
                    img.style.display = 'block';
                }
                playOverlay.style.display = 'none';
            }

            document.querySelectorAll('.thumb').forEach((thumb, i) => {
                thumb.classList.toggle('active', i === index);
            });
        }

        window.addEventListener('load', () => {
            const firstMedia = mediaItems[0];
            if (firstMedia && firstMedia.type === 'video') {
                setMainMedia(0);
            }
        });

        let currentQty = 1;
        function adjustQty(delta) {
            currentQty += delta;
            if(currentQty < 1) currentQty = 1;
            document.getElementById('qty-val').innerText = currentQty;
        }

        function updateDetailPrice() {
            let select = document.getElementById('variant-select');
            let selected = select.options[select.selectedIndex];
            let price = selected.getAttribute('data-price');
            let stock = selected.getAttribute('data-stock');
            let origPrice = {{ product.original_price | tojson }};
            let priceHtml = `₹${price}`;
            if (origPrice) {
                let discount = Math.round(((origPrice - parseFloat(price)) / origPrice) * 100);
                priceHtml += ` <span class="orig-price">₹${origPrice}</span> <span class="discount-badge">${discount}% OFF</span>`;
            }
            document.getElementById('detail-price').innerHTML = priceHtml;
            document.getElementById('detail-stock').innerText = 'In Stock: ' + stock;
        }

        function showToast(msg) {
            let t = document.getElementById('toast');
            document.getElementById('toast-msg').innerText = msg;
            t.classList.add('show');
            setTimeout(() => { t.classList.remove('show'); }, 3000);
        }

        function addToCartDetail() {
            let select = document.getElementById('variant-select');
            let selectedSize = select.value;
            let selectedOption = select.options[select.selectedIndex];
            let price = parseFloat(selectedOption.getAttribute('data-price'));

            let product = {{ product | tojson }};
            let cartItem = {
                id: product.id,
                name: product.name,
                size: selectedSize,
                price: price,
                quantity: currentQty,
                image: product.image
            };

            let existingCart = JSON.parse(localStorage.getItem('adorica_cart') || '[]');
            let found = existingCart.find(x => x.id === product.id && x.size === selectedSize);
            if(found) {
                found.quantity += currentQty;
            } else {
                existingCart.push(cartItem);
            }
            localStorage.setItem('adorica_cart', JSON.stringify(existingCart));
            showToast(`${currentQty} x ${product.name} (${selectedSize}) added to your basket!`);
        }

        function buyNowDetail() {
            let select = document.getElementById('variant-select');
            let selectedSize = select.value;
            let selectedOption = select.options[select.selectedIndex];
            let price = parseFloat(selectedOption.getAttribute('data-price'));

            let product = {{ product | tojson }};
            let cartItem = {
                id: product.id,
                name: product.name,
                size: selectedSize,
                price: price,
                quantity: currentQty,
                image: product.image
            };
            localStorage.setItem('adorica_cart', JSON.stringify([cartItem]));
            window.location.href = '/?openCart=true';
        }
    </script>
</body>
</html>
"""

# --- ADMIN TEMPLATE (with Broadcast and Coupon tabs) ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard | CHIRANJEEVI </title>
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
        .btn-add-variant { background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
        .btn-remove-variant { background: #dc2626; color: white; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .variant-row { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; }
        .variant-row input { flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 6px; }
        
        .status-badge { padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
        .status-0 { background: #fee2e2; color: #991b1b; }
        .status-1 { background: #e3f2fd; color: #1565c0; }
        .status-2 { background: #fff8e1; color: #f57f17; }
        .status-3 { background: #ede7f6; color: #512da8; }
        .status-4 { background: #e8f5e9; color: #2e7d32; }
        .status-5 { background: #fef9c3; color: #854d0e; }

        .btn-accept { background: #166534; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; margin-right: 5px; }
        .btn-reject { background: #991b1b; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; }
        .btn-submit-status { background: var(--green-primary); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 11.5px; transition: 0.2s; }
        .btn-submit-status:hover { background: var(--green-light); }

        .btn-doc-action { display: inline-flex; align-items: center; gap: 6px; background: #e2e8f0; color: #1e293b; text-decoration: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; transition: 0.2s; border: none; cursor: pointer; }
        .btn-doc-action:hover { background: #cbd5e1; }
        .btn-doc-pdf { background: #1b4332; color: white; }
        .btn-doc-pdf:hover { background: #2d6a4f; }
        .btn-doc-print { background: #d4a373; color: white; }
        .btn-doc-print:hover { background: #c59261; }

        .drop-zone { border: 2px dashed #ccc; border-radius: 12px; padding: 30px; text-align: center; background: #fafafa; cursor: pointer; transition: 0.3s; }
        .drop-zone.dragover { border-color: var(--green-primary); background: #f0fdf4; }
        .drop-zone i { font-size: 36px; color: #aaa; }
        .drop-zone p { margin-top: 8px; color: #888; }
        .preview-container { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
        .preview-item { position: relative; width: 80px; height: 80px; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1); border: 2px solid #eee; }
        .preview-item img, .preview-item video { width: 100%; height: 100%; object-fit: cover; }
        .preview-item .remove-btn { position: absolute; top: 2px; right: 2px; background: #dc2626; color: white; border: none; border-radius: 50%; width: 20px; height: 20px; cursor: pointer; font-size: 14px; line-height: 20px; text-align: center; }
        .cert-list-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid #eee; }
        .cert-list-item span { font-weight: 500; }
        .cert-list-item button { background: #dc2626; color: white; border: none; border-radius: 6px; padding: 4px 12px; cursor: pointer; font-size: 12px; }

        .coupon-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; padding: 10px 0; }
        .coupon-row span { font-weight: 500; }
        .coupon-row .status-toggle { background: #e2e8f0; border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 12px; }
        .coupon-row .status-toggle.active { background: #22c55e; color: white; }
        .coupon-row .status-toggle.inactive { background: #ef4444; color: white; }
        .coupon-row .delete-coupon { background: #dc2626; color: white; border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .customer-list { max-height: 200px; overflow-y: auto; border: 1px solid #eee; border-radius: 8px; padding: 10px; }
        .customer-item { display: flex; gap: 20px; padding: 6px 0; border-bottom: 1px solid #f1f5f9; font-size: 13px; }
        .customer-item span:first-child { font-weight: 500; width: 120px; }
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
                <button class="active" onclick="switchAdminTab('orders', this)"><i class="fa-solid fa-box"></i> Orders</button>
                <button onclick="switchAdminTab('inventory', this)"><i class="fa-solid fa-warehouse"></i> Inventory</button>
                <button onclick="switchAdminTab('banners', this)"><i class="fa-solid fa-images"></i> Banners</button>
                <button onclick="switchAdminTab('ads', this)"><i class="fa-solid fa-ad"></i> Ads</button>
                <button onclick="switchAdminTab('upload', this)"><i class="fa-solid fa-circle-plus"></i> Upload Product</button>
                <button onclick="switchAdminTab('branding', this)"><i class="fa-solid fa-image"></i> Logo</button>
                <button onclick="switchAdminTab('certifications', this)"><i class="fa-solid fa-award"></i> Certifications</button>
                <button onclick="switchAdminTab('broadcast', this)"><i class="fa-solid fa-bullhorn"></i> Broadcast</button>
                <button onclick="switchAdminTab('coupons', this)"><i class="fa-solid fa-ticket"></i> Coupons</button>
            </div>
        </div>
        <div>
            <a href="/" target="_blank" style="color: white; text-decoration: none; font-size: 13px; display: flex; align-items: center; gap: 8px;"><i class="fa-solid fa-arrow-up-right-from-square"></i> Visit Storefront</a>
        </div>
    </div>

    <div class="admin-content" id="adminContent">
        <div class="admin-topbar">
            <button class="admin-menu-toggle" onclick="toggleAdminSidebar()"><i class="fa-solid fa-bars"></i></button>
            <span style="font-weight: 600; color: var(--green-primary); font-size: 15px;">CHIRANJEEVI  - Management Dashboard</span>
        </div>

        <!-- Orders Tab -->
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
                            <th>Documents</th>
                            <th>Accept / Reject</th>
                            <th>Status Control</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for o in orders %}
                        <tr id="order-row-{{ o.order_id }}">
                            <td><b>{{ o.order_id }}</b><br><span style="font-size:11px; color:#888;">{{ o.date }}</span></td>
                            <td><b>{{ o.name }}</b><br>{{ o.phone }}<br><span style="font-size:11px; color:#666;">{{ o.email }}</span></td>
                            <td>
                                {% for i in o['items'] %}
                                <div>• {{ i.name }} {% if i.size %}({{ i.size }}){% endif %} (x{{ i.quantity | default(1) }})</div>
                                {% endfor %}
                                <b style="color:var(--green-primary); margin-top:5px; display:inline-block;">Total: ₹{{ o.amount }}</b>
                            </td>
                            <td><span style="color:#2e7d32; font-weight:600; font-size:11.5px;">{{ o.payment_type }}</span><br><span style="font-size:11px; color:#666;">{{ o.full_address }}</span></td>
                            <td>
                                <div style="display:flex; flex-direction:column; gap:6px; min-width: 145px;">
                                    <a href="/admin/download_invoice/{{ o.order_id }}" class="btn-doc-action btn-doc-pdf"><i class="fa-solid fa-file-pdf"></i> Invoice</a>
                                    <a href="/admin/print_label/{{ o.order_id }}" target="_blank" class="btn-doc-action btn-doc-print"><i class="fa-solid fa-print"></i> Label</a>
                                    <button class="btn-doc-action" onclick="resendInvoiceEmail('{{ o.order_id }}')"><i class="fa-solid fa-paper-plane"></i> Resend</button>
                                </div>
                            </td>
                            <td>
                                {% if o.acceptance_status == 'Rejected' %}
                                <span style="color:#991b1b; font-weight:700; font-size:12px;"><i class="fa-solid fa-circle-xmark"></i> Rejected</span>
                                {% elif o.acceptance_status == 'Accepted' %}
                                <span style="color:#166534; font-weight:700; font-size:12px; display:block; margin-bottom:5px;"><i class="fa-solid fa-circle-check"></i> Accepted</span>
                                <button class="btn-reject" onclick="rejectOrder('{{ o.order_id }}')">Reject & Refund</button>
                                {% else %}
                                <button class="btn-accept" onclick="acceptOrder('{{ o.order_id }}')">Accept</button>
                                <button class="btn-reject" onclick="rejectOrder('{{ o.order_id }}')">Reject & Refund</button>
                                {% endif %}
                            </td>
                            <td>
                                <div style="display:flex; gap:6px; align-items:center;">
                                    <select id="status-select-{{ o.order_id }}" class="form-control" style="margin-bottom:0; width:125px; font-size:12px;">
                                        <option value="1" {% if o.status_step == 1 %}selected{% endif %}>1. Placed</option>
                                        <option value="2" {% if o.status_step == 2 %}selected{% endif %}>2. Packaging</option>
                                        <option value="3" {% if o.status_step == 3 %}selected{% endif %}>3. Shipped</option>
                                        <option value="4" {% if o.status_step == 4 %}selected{% endif %}>4. Delivered</option>
                                        <option value="5" {% if o.status_step == 5 %}selected{% endif %}>5. Refunded</option>
                                    </select>
                                    <button type="button" class="btn-submit-status" onclick="submitStatusUpdate('{{ o.order_id }}')"><i class="fa-solid fa-paper-plane"></i></button>
                                </div>
                                <div style="margin-top:6px;"><span class="status-badge status-{{ o.status_step }}">{{ o.status_text }}</span></div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="color: #666; text-align: center; padding: 20px;">No orders yet.</p>
                {% endif %}
            </div>
        </div>

        <!-- Banners Tab -->
        <div id="tab-banners" class="admin-section">
            <h2>Slider Banners</h2>
            <div class="card" style="max-width: 600px;">
                <form action="/api/admin/add_slide" method="POST" enctype="multipart/form-data">
                    <label style="font-weight:600; font-size:13px;">Select multiple images (each becomes a slide)</label>
                    <input type="file" name="image_files" class="form-control" accept="image/*" multiple required>
                    <label style="font-weight:600; font-size:13px;">Titles (optional, one per image)</label>
                    <input type="text" name="title[]" class="form-control" placeholder="Title for first">
                    <input type="text" name="title[]" class="form-control" placeholder="Title for second">
                    <label style="font-weight:600; font-size:13px;">Badges (optional)</label>
                    <input type="text" name="badge[]" class="form-control" placeholder="Badge for first">
                    <input type="text" name="badge[]" class="form-control" placeholder="Badge for second">
                    <label style="font-weight:600; font-size:13px;">Descriptions (optional)</label>
                    <textarea name="desc[]" class="form-control" placeholder="Desc for first"></textarea>
                    <textarea name="desc[]" class="form-control" placeholder="Desc for second"></textarea>
                    <label style="font-weight:600; font-size:13px;">Videos (optional)</label>
                    <input type="file" name="video_files" class="form-control" accept="video/*" multiple>
                    <button type="submit" class="btn-submit">Upload Slides</button>
                </form>
            </div>
            <div class="card">
                <table>
                    <thead><tr><th>Image</th><th>Details</th><th>Action</th></tr></thead>
                    <tbody>
                        {% for s in slides %}
                        <tr id="slide-row-{{ s.id }}">
                            <td><img src="{{ s.image }}" style="width:100px; height:60px; object-fit:cover; border-radius:8px;"></td>
                            <td><b>{{ s.title }}</b><br><small>{{ s.badge }}</small></td>
                            <td><button onclick="deleteSlide({{ s.id }})" style="background:#c62828; color:white; border:none; padding:8px 15px; border-radius:8px; cursor:pointer;"><i class="fa-solid fa-trash"></i> Remove</button></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Ads Tab -->
        <div id="tab-ads" class="admin-section">
            <h2>Advertisements</h2>
            <div class="card" style="max-width: 600px;">
                <form action="/api/admin/add_ad" method="POST" enctype="multipart/form-data">
                    <input type="text" name="title" class="form-control" placeholder="Ad Title" required>
                    <input type="text" name="link" class="form-control" placeholder="Ad Link URL" value="#">
                    <textarea name="desc" class="form-control" placeholder="Ad Description"></textarea>
                    <label style="font-weight:600; font-size:13px;">Ad Image *</label>
                    <input type="file" name="image_file" class="form-control" accept="image/*" required>
                    <button type="submit" class="btn-submit">Upload Ad</button>
                </form>
            </div>
            <div class="card">
                <table>
                    <thead><tr><th>Image</th><th>Title / Link</th><th>Action</th></tr></thead>
                    <tbody>
                        {% for a in ads %}
                        <tr id="ad-row-{{ a.id }}">
                            <td><img src="{{ a.image }}" style="width:80px; height:50px; object-fit:cover; border-radius:6px;"></td>
                            <td><b>{{ a.title }}</b><br><small>{{ a.link }}</small></td>
                            <td><button onclick="deleteAd({{ a.id }})" style="background:#c62828; color:white; border:none; padding:8px 15px; border-radius:8px; cursor:pointer;"><i class="fa-solid fa-trash"></i> Remove</button></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Inventory Tab -->
        <div id="tab-inventory" class="admin-section">
            <h2>Inventory & Product Management</h2>
            <div class="card">
                <table>
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Category</th>
                            <th>Variants</th>
                            <th>Media</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr id="prod-row-{{ p.id }}">
                            <td><b>{{ p.name }}</b></td>
                            <td>{{ p.category }}</td>
                            <td>
                                <div id="variant-display-{{ p.id }}">
                                    {% for v in p.variants %}
                                    <span style="display:inline-block; background:#f3f4f6; padding:4px 8px; border-radius:4px; margin:2px; font-size:11px;">{{ v.size }}: ₹{{ v.price }} ({{ v.stock }})</span>
                                    {% endfor %}
                                </div>
                                <div id="variant-edit-{{ p.id }}" style="display:none; margin-top:5px;">
                                    <div id="variant-list-{{ p.id }}">
                                        {% for v in p.variants %}
                                        <div class="variant-row" data-index="{{ loop.index0 }}">
                                            <input type="text" value="{{ v.size }}" class="variant-size-{{ p.id }}" placeholder="Size">
                                            <input type="number" value="{{ v.price }}" class="variant-price-{{ p.id }}" placeholder="Price">
                                            <input type="number" value="{{ v.stock }}" class="variant-stock-{{ p.id }}" placeholder="Stock">
                                            <button class="btn-remove-variant" onclick="removeVariant({{ p.id }}, {{ loop.index0 }})">✕</button>
                                        </div>
                                        {% endfor %}
                                    </div>
                                    <button type="button" class="btn-add-variant" onclick="addVariant({{ p.id }})"><i class="fa-solid fa-plus"></i> Add</button>
                                </div>
                            </td>
                            <td>
                                <span>{{ p.media|length }} items</span>
                                <form action="/api/admin/update_gallery" method="POST" enctype="multipart/form-data" style="margin-top:5px;">
                                    <input type="hidden" name="product_id" value="{{ p.id }}">
                                    <label style="font-size:11px;">Images:</label>
                                    <input type="file" name="gallery_images[]" accept="image/*" multiple>
                                    <label style="font-size:11px;">Videos:</label>
                                    <input type="file" name="gallery_videos[]" accept="video/*" multiple>
                                    <button type="submit" class="btn-submit" style="padding:4px 10px; font-size:11px;">Update</button>
                                </form>
                            </td>
                            <td>
                                <select id="edit-status-{{ p.id }}" style="padding:5px; border:1px solid #ddd; border-radius:4px;">
                                    <option value="active" {% if p.status == 'active' %}selected{% endif %}>Active</option>
                                    <option value="suspended" {% if p.status == 'suspended' %}selected{% endif %}>Suspended</option>
                                </select>
                            </td>
                            <td>
                                <button onclick="toggleEditVariants({{ p.id }})" style="background:#2563eb; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;"><i class="fa-solid fa-pen"></i></button>
                                <button onclick="saveProduct({{ p.id }})" style="background:#2e7d32; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;"><i class="fa-solid fa-save"></i></button>
                                <button onclick="deleteProduct({{ p.id }})" style="background:#c62828; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;"><i class="fa-solid fa-trash"></i></button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Upload Product Tab -->
        <div id="tab-upload" class="admin-section">
            <h2>Upload New Product (Ultimate Media Uploader)</h2>
            <div class="card" style="max-width: 700px;">
                <form action="/api/admin/add_product" method="POST" enctype="multipart/form-data" id="productForm">
                    <label style="font-weight:600; font-size:13px;">Product Name *</label>
                    <input type="text" name="name" class="form-control" required placeholder="e.g. Rosemary Hair Tonic">
                    
                    <label style="font-weight:600; font-size:13px;">Category *</label>
                    <select name="category" class="form-control" required>
                        <option value="Apparel">Apparel</option>
                        <option value="Fragrance">Fragrance</option>
                        <option value="Skin Care">Skin Care</option>
                        <option value="Hair Care">Hair Care</option>
                        <option value="Oil">Oil</option>
                        <option value="Shampoo">Shampoo</option>
                    </select>

                    <label style="font-weight:600; font-size:13px;">Original Price (MRP)</label>
                    <input type="number" name="original_price" class="form-control" placeholder="e.g. 1599" step="0.01">

                    <div style="margin-bottom:15px;">
                        <label style="font-weight:600; font-size:13px;">Product Variants (Size, Price, Stock)</label>
                        <div id="variant-container">
                            <div class="variant-row">
                                <input type="text" name="variant_size[]" placeholder="Size (e.g. 100ml)" required>
                                <input type="number" name="variant_price[]" placeholder="Price (₹)" required>
                                <input type="number" name="variant_stock[]" placeholder="Stock" required>
                                <button type="button" class="btn-remove-variant" onclick="removeVariantUpload(this)">✕</button>
                            </div>
                        </div>
                        <button type="button" class="btn-add-variant" onclick="addVariantUpload()"><i class="fa-solid fa-plus"></i> Add Variant</button>
                    </div>

                    <label style="font-weight:600; font-size:13px;">Main Product Image *</label>
                    <input type="file" name="image_file" class="form-control" accept="image/*" required>

                    <div style="margin: 20px 0;">
                        <label style="font-weight:600; font-size:13px; display:block; margin-bottom:8px;">Additional Images (drag & drop or click to select multiple)</label>
                        <div id="imageDropZone" class="drop-zone">
                            <i class="fa-solid fa-cloud-upload-alt"></i>
                            <p>Drop images here or click to select</p>
                            <input type="file" name="gallery_images[]" id="imageInput" accept="image/*" multiple style="display:none;">
                        </div>
                        <div id="imagePreviewContainer" class="preview-container"></div>
                    </div>

                    <div style="margin: 20px 0;">
                        <label style="font-weight:600; font-size:13px; display:block; margin-bottom:8px;">Additional Videos (drag & drop or click to select multiple)</label>
                        <div id="videoDropZone" class="drop-zone">
                            <i class="fa-solid fa-cloud-upload-alt"></i>
                            <p>Drop videos here or click to select</p>
                            <input type="file" name="gallery_videos[]" id="videoInput" accept="video/*" multiple style="display:none;">
                        </div>
                        <div id="videoPreviewContainer" class="preview-container"></div>
                    </div>

                    <label style="font-weight:600; font-size:13px;">Key Ingredients</label>
                    <input type="text" name="ingredients" class="form-control" placeholder="e.g. Rosemary Extract">

                    <label style="font-weight:600; font-size:13px;">Sourcing Geography</label>
                    <input type="text" name="geography" class="form-control" placeholder="e.g. Western Ghats">

                    <label style="font-weight:600; font-size:13px;">Extraction Technique</label>
                    <input type="text" name="extraction" class="form-control" placeholder="e.g. Cold pressed">

                    <label style="font-weight:600; font-size:13px;">Description</label>
                    <textarea name="desc" class="form-control" rows="3" placeholder="Brief description..."></textarea>

                    <button type="submit" class="btn-submit">Publish Product</button>
                </form>
            </div>
        </div>

        <!-- Branding Tab -->
        <div id="tab-branding" class="admin-section">
            <h2>Website Logo</h2>
            <div class="card" style="max-width: 500px; text-align: center;">
                <img src="{{ settings.logo }}" alt="Current Logo" style="width: 100px; height: 100px; object-fit: cover; border-radius: 50%; border: 3px solid var(--accent-gold); margin-bottom: 20px;">
                <form action="/api/admin/update_logo" method="POST" enctype="multipart/form-data">
                    <input type="file" name="logo_file" class="form-control" accept="image/*" required>
                    <button type="submit" class="btn-submit" style="width:100%;">Update Logo</button>
                </form>
            </div>
        </div>

        <!-- Certifications Tab -->
        <div id="tab-certifications" class="admin-section">
            <h2>Brands & Certifications (Marquee)</h2>
            <div class="card" style="max-width: 600px;">
                <h4>Add New Certification / Brand</h4>
                <form id="certForm" onsubmit="addCertification(event)">
                    <input type="text" id="certName" class="form-control" placeholder="Name (e.g. Razorpay)" required>
                    <input type="text" id="certLink" class="form-control" placeholder="Link URL (optional)" value="#">
                    <input type="text" id="certLogo" class="form-control" placeholder="Logo Image URL (optional)">
                    <button type="submit" class="btn-submit">Add Certification</button>
                </form>
            </div>
            <div class="card">
                <h4>Current Certifications</h4>
                {% if certifications %}
                <div id="certList">
                    {% for cert in certifications %}
                    <div class="cert-list-item" data-index="{{ loop.index0 }}">
                        <span><strong>{{ cert.name }}</strong> {% if cert.link %}🔗 {{ cert.link }}{% endif %}</span>
                        <button onclick="deleteCertification({{ loop.index0 }})">Remove</button>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p>No certifications added yet.</p>
                {% endif %}
            </div>
        </div>

        <!-- Broadcast Tab -->
        <div id="tab-broadcast" class="admin-section">
            <h2>Send Broadcast Message to All Customers</h2>
            <div class="card" style="max-width: 700px;">
                <div style="margin-bottom: 15px;">
                    <strong>Registered Customers ({{ customers|length }}):</strong>
                    <div class="customer-list">
                        {% for c in customers %}
                        <div class="customer-item">
                            <span>{{ c.name }}</span>
                            <span>{{ c.email }}</span>
                            <span>{{ c.phone }}</span>
                        </div>
                        {% else %}
                        <div>No customers registered yet.</div>
                        {% endfor %}
                    </div>
                </div>
                <form id="broadcastForm" onsubmit="sendBroadcast(event)">
                    <label style="font-weight:600; font-size:13px;">Message (supports plain text, will be sent to email and SMS)</label>
                    <textarea id="broadcastMessage" class="form-control" rows="4" placeholder="Type your message to all customers..." required></textarea>
                    <button type="submit" class="btn-submit"><i class="fa-solid fa-paper-plane"></i> Send Broadcast</button>
                </form>
                <div id="broadcastStatus" style="margin-top:15px; font-weight:600;"></div>
            </div>
        </div>

        <!-- Coupons Tab -->
        <div id="tab-coupons" class="admin-section">
            <h2>Coupon Management</h2>
            <div class="card" style="max-width: 700px;">
                <h4>Create New Coupon</h4>
                <form id="couponForm" onsubmit="createCoupon(event)">
                    <input type="text" id="couponCode" class="form-control" placeholder="Coupon Code (e.g. SUMMER20)" required>
                    <input type="number" id="couponDiscount" class="form-control" placeholder="Discount Percentage (e.g. 10)" required min="1" max="100">
                    <button type="submit" class="btn-submit"><i class="fa-solid fa-plus"></i> Create Coupon</button>
                </form>
                <div id="couponCreateStatus" style="margin-top:10px; font-weight:600;"></div>
            </div>
            <div class="card">
                <h4>Existing Coupons</h4>
                {% if coupons %}
                <div id="couponList">
                    {% for c in coupons %}
                    <div class="coupon-row" data-code="{{ c.code }}">
                        <span><strong>{{ c.code }}</strong> - {{ c.discount }}% OFF</span>
                        <span>
                            <button class="status-toggle {% if c.active %}active{% else %}inactive{% endif %}" onclick="toggleCoupon('{{ c.code }}')">
                                {{ 'Active' if c.active else 'Inactive' }}
                            </button>
                            <button class="delete-coupon" onclick="deleteCoupon('{{ c.code }}')"><i class="fa-solid fa-trash"></i></button>
                        </span>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p>No coupons created yet.</p>
                {% endif %}
            </div>
        </div>
    </div>

    <script>
        function toggleAdminSidebar() { document.getElementById('adminSidebar').classList.toggle('collapsed'); document.getElementById('adminContent').classList.toggle('expanded'); }
        function switchAdminTab(tabId, btn) {
            document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.admin-nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            btn.classList.add('active');
        }
        function submitStatusUpdate(orderId) {
            let step = document.getElementById('status-select-' + orderId).value;
            let statusMap = { "1": "Order Placed", "2": "Packaging", "3": "Shipped", "4": "Delivered", "5": "Refunded" };
            let confirmMsg = `Send email & SMS notification to customer for status "${statusMap[step]}"?`;
            if (step === '5') confirmMsg = "This will send a refund confirmation email & SMS to the customer. Continue?";
            if(confirm(confirmMsg)) {
                fetch('/api/admin/update_status', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ order_id: orderId, step: step })
                }).then(r => r.json()).then(d => { if(d.success) location.reload(); });
            }
        }
        function resendInvoiceEmail(orderId) {
            if(confirm(`Resend invoice email & SMS for order ${orderId}?`)) {
                fetch('/api/admin/resend_invoice', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ order_id: orderId })
                }).then(r => r.json()).then(d => { alert(d.success ? "Invoice resent!" : "Failed: " + d.message); });
            }
        }
        function acceptOrder(orderId) {
            fetch('/api/admin/accept_order', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: orderId }) })
                .then(r => r.json()).then(d => { if(d.success) location.reload(); });
        }
        function rejectOrder(orderId) {
            if(confirm("Reject this order? Customer will receive cancellation & refund alert via email and SMS.")) {
                fetch('/api/admin/reject_order', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ order_id: orderId }) })
                    .then(r => r.json()).then(d => { if(d.success) location.reload(); });
            }
        }
        function deleteSlide(id) {
            if(confirm("Remove this slide?")) {
                fetch('/api/admin/delete_slide', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: id }) })
                    .then(r => r.json()).then(d => { if(d.success) document.getElementById('slide-row-'+id).remove(); });
            }
        }
        function deleteAd(id) {
            if(confirm("Remove this ad?")) {
                fetch('/api/admin/delete_ad', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: id }) })
                    .then(r => r.json()).then(d => { if(d.success) document.getElementById('ad-row-'+id).remove(); });
            }
        }
        function toggleEditVariants(prodId) {
            let display = document.getElementById('variant-display-' + prodId);
            let edit = document.getElementById('variant-edit-' + prodId);
            if (display.style.display === 'none') { display.style.display = 'block'; edit.style.display = 'none'; } else { display.style.display = 'none'; edit.style.display = 'block'; }
        }
        function addVariant(prodId) {
            let container = document.getElementById('variant-list-' + prodId);
            let index = container.children.length;
            let row = document.createElement('div'); row.className = 'variant-row'; row.dataset.index = index;
            row.innerHTML = `<input type="text" class="variant-size-${prodId}" placeholder="Size">
                <input type="number" class="variant-price-${prodId}" placeholder="Price">
                <input type="number" class="variant-stock-${prodId}" placeholder="Stock">
                <button class="btn-remove-variant" onclick="removeVariant(${prodId}, ${index})">✕</button>`;
            container.appendChild(row);
        }
        function removeVariant(prodId, index) {
            let container = document.getElementById('variant-list-' + prodId);
            let rows = container.querySelectorAll('.variant-row');
            if (rows.length > 1) {
                rows[index].remove();
                rows = container.querySelectorAll('.variant-row');
                rows.forEach((row, i) => row.dataset.index = i);
            } else alert("At least one variant required.");
        }
        function saveProduct(prodId) {
            let status = document.getElementById('edit-status-' + prodId).value;
            let variantSizes = document.querySelectorAll('.variant-size-' + prodId);
            let variantPrices = document.querySelectorAll('.variant-price-' + prodId);
            let variantStocks = document.querySelectorAll('.variant-stock-' + prodId);
            let variants = [];
            for (let i = 0; i < variantSizes.length; i++) {
                let size = variantSizes[i].value.trim();
                let price = parseFloat(variantPrices[i].value);
                let stock = parseInt(variantStocks[i].value);
                if (size && !isNaN(price) && !isNaN(stock)) variants.push({ size, price, stock });
            }
            if (variants.length === 0) return alert("At least one valid variant required.");
            fetch('/api/admin/edit_product', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: prodId, status: status, variants: variants })
            }).then(r => r.json()).then(d => { if(d.success) location.reload(); });
        }
        function deleteProduct(id) {
            if(confirm("Delete this product?")) {
                fetch('/api/admin/delete_product', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: id }) })
                    .then(r => r.json()).then(d => { if(d.success) document.getElementById('prod-row-'+id).remove(); });
            }
        }
        function addVariantUpload() {
            let container = document.getElementById('variant-container');
            let row = document.createElement('div'); row.className = 'variant-row';
            row.innerHTML = `<input type="text" name="variant_size[]" placeholder="Size" required>
                <input type="number" name="variant_price[]" placeholder="Price" required>
                <input type="number" name="variant_stock[]" placeholder="Stock" required>
                <button type="button" class="btn-remove-variant" onclick="removeVariantUpload(this)">✕</button>`;
            container.appendChild(row);
        }
        function removeVariantUpload(btn) {
            let container = document.getElementById('variant-container');
            let rows = container.querySelectorAll('.variant-row');
            if (rows.length > 1) btn.parentElement.remove();
            else alert("At least one variant required.");
        }

        // ---- Certifications ----
        function addCertification(e) {
            e.preventDefault();
            const name = document.getElementById('certName').value.trim();
            const link = document.getElementById('certLink').value.trim();
            const logo = document.getElementById('certLogo').value.trim();
            if (!name) return alert("Name is required.");
            fetch('/api/admin/add_certification', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, link, logo })
            }).then(r => r.json()).then(d => {
                if (d.success) location.reload();
                else alert("Failed to add: " + d.message);
            });
        }

        function deleteCertification(index) {
            if (!confirm("Remove this certification?")) return;
            fetch('/api/admin/delete_certification', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index })
            }).then(r => r.json()).then(d => {
                if (d.success) location.reload();
                else alert("Failed to delete: " + d.message);
            });
        }

        // ---- Broadcast ----
        function sendBroadcast(e) {
            e.preventDefault();
            const msg = document.getElementById('broadcastMessage').value.trim();
            if (!msg) return alert("Please enter a message.");
            const statusDiv = document.getElementById('broadcastStatus');
            statusDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending broadcast...';
            fetch('/api/admin/send_broadcast', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            }).then(r => r.json()).then(d => {
                if (d.success) {
                    statusDiv.innerHTML = `<span style="color:#166534;"><i class="fa-solid fa-check-circle"></i> ${d.message}</span>`;
                } else {
                    statusDiv.innerHTML = `<span style="color:#991b1b;"><i class="fa-solid fa-circle-exclamation"></i> ${d.message}</span>`;
                }
            }).catch(() => {
                statusDiv.innerHTML = `<span style="color:#991b1b;">Failed to send broadcast.</span>`;
            });
        }

        // ---- Coupons ----
        function createCoupon(e) {
            e.preventDefault();
            const code = document.getElementById('couponCode').value.trim().toUpperCase();
            const discount = parseFloat(document.getElementById('couponDiscount').value);
            if (!code || discount <= 0) return alert("Valid code and discount required.");
            const statusDiv = document.getElementById('couponCreateStatus');
            statusDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating...';
            fetch('/api/admin/create_coupon', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code, discount })
            }).then(r => r.json()).then(d => {
                if (d.success) {
                    statusDiv.innerHTML = `<span style="color:#166534;"><i class="fa-solid fa-check-circle"></i> ${d.message}</span>`;
                    setTimeout(() => location.reload(), 1500);
                } else {
                    statusDiv.innerHTML = `<span style="color:#991b1b;">${d.message}</span>`;
                }
            });
        }

        function deleteCoupon(code) {
            if (!confirm(`Delete coupon ${code}?`)) return;
            fetch('/api/admin/delete_coupon', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            }).then(r => r.json()).then(d => {
                if (d.success) location.reload();
                else alert("Failed: " + d.message);
            });
        }

        function toggleCoupon(code) {
            fetch('/api/admin/toggle_coupon', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            }).then(r => r.json()).then(d => {
                if (d.success) location.reload();
                else alert("Failed: " + d.message);
            });
        }

        // ---- Media uploader drag & drop ----
        const imageDropZone = document.getElementById('imageDropZone');
        const imageInput = document.getElementById('imageInput');
        const imagePreviewContainer = document.getElementById('imagePreviewContainer');

        imageDropZone.addEventListener('click', () => imageInput.click());
        imageDropZone.addEventListener('dragover', (e) => { e.preventDefault(); imageDropZone.classList.add('dragover'); });
        imageDropZone.addEventListener('dragleave', () => { imageDropZone.classList.remove('dragover'); });
        imageDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            imageDropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            imageInput.files = files;
            handleFiles(files, imagePreviewContainer, 'image');
        });
        imageInput.addEventListener('change', function() {
            handleFiles(this.files, imagePreviewContainer, 'image');
        });

        const videoDropZone = document.getElementById('videoDropZone');
        const videoInput = document.getElementById('videoInput');
        const videoPreviewContainer = document.getElementById('videoPreviewContainer');

        videoDropZone.addEventListener('click', () => videoInput.click());
        videoDropZone.addEventListener('dragover', (e) => { e.preventDefault(); videoDropZone.classList.add('dragover'); });
        videoDropZone.addEventListener('dragleave', () => { videoDropZone.classList.remove('dragover'); });
        videoDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            videoDropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            videoInput.files = files;
            handleFiles(files, videoPreviewContainer, 'video');
        });
        videoInput.addEventListener('change', function() {
            handleFiles(this.files, videoPreviewContainer, 'video');
        });

        function handleFiles(files, container, type) {
            container.innerHTML = '';
            for (let file of files) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const div = document.createElement('div');
                    div.className = 'preview-item';
                    if (type === 'image') {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        div.appendChild(img);
                    } else {
                        const video = document.createElement('video');
                        video.src = e.target.result;
                        video.muted = true;
                        div.appendChild(video);
                    }
                    const removeBtn = document.createElement('button');
                    removeBtn.className = 'remove-btn';
                    removeBtn.innerHTML = '×';
                    removeBtn.onclick = function(e) {
                        e.stopPropagation();
                        div.remove();
                        showAdminToast('File removed from preview.');
                    };
                    div.appendChild(removeBtn);
                    container.appendChild(div);
                };
                reader.readAsDataURL(file);
            }
        }

        function showAdminToast(msg) {
            const t = document.createElement('div');
            t.style.position = 'fixed';
            t.style.bottom = '30px';
            t.style.right = '30px';
            t.style.background = '#1b4332';
            t.style.color = 'white';
            t.style.padding = '14px 24px';
            t.style.borderRadius = '12px';
            t.style.boxShadow = '0 20px 40px rgba(27,67,50,0.15)';
            t.style.zIndex = '9999';
            t.style.fontSize = '14px';
            t.style.fontWeight = '500';
            t.innerText = msg;
            document.body.appendChild(t);
            setTimeout(() => { t.remove(); }, 3000);
        }
    </script>
</body>
</html>
"""

# --- SUCCESS, HISTORY, SHIPPING, INVOICE templates remain unchanged ---
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Status | CHIRANJEEVI </title>
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
        .icon-box-rejected { font-size: 45px; color: white; background: #991b1b; border-radius: 50%; width: 85px; height: 85px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; animation: popIn 0.6s ease-out forwards; }
        h1 { font-family: 'Playfair Display', serif; color: var(--green-primary); font-size: 26px; margin-bottom: 5px; }
        p.subtitle { color: #666; font-size: 14px; margin-bottom: 25px; }
        .tracker-container { display: flex; justify-content: space-between; position: relative; margin: 35px 0 25px 0; padding: 0 20px; }
        .tracker-container::before { content: ''; position: absolute; top: 18px; left: 40px; right: 40px; height: 4px; background: #e0e0e0; z-index: 1; }
        .tracker-step { position: relative; z-index: 2; text-align: center; flex: 1; }
        .step-icon { width: 38px; height: 38px; border-radius: 50%; background: #e0e0e0; color: #777; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px auto; font-size: 14px; font-weight: bold; transition: 0.3s; }
        .tracker-step.completed .step-icon { background: var(--green-light); color: white; }
        .tracker-step.active .step-icon { background: var(--green-primary); color: white; box-shadow: 0 0 15px rgba(27, 67, 50, 0.4); }
        .tracker-step.rejected .step-icon { background: #991b1b; color: white; box-shadow: 0 0 15px rgba(153, 27, 27, 0.4); }
        .tracker-step span { font-size: 11px; color: #666; font-weight: 500; display: block; }
        .order-info-box { background: #FAF7F0; border: 1px dashed var(--accent-gold); padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: left; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; color: #444; }
        .rejection-notice-box { background: #fee2e2; border: 1.5px solid #ef4444; color: #991b1b; padding: 18px; border-radius: 12px; margin-bottom: 20px; text-align: left; }
        .btn-home { background: var(--green-primary); color: white; text-decoration: none; padding: 14px 30px; border-radius: 30px; font-weight: 600; display: inline-block; width: 100%; margin-top: 10px; transition: 0.3s; }
        .btn-home:hover { background: var(--green-light); }
    </style>
</head>
<body>
    <div class="card">
        {% if order and (order.acceptance_status == 'Rejected' or order.status_step == 0) %}
            <div class="icon-box-rejected"><i class="fa-solid fa-circle-xmark"></i></div>
            <h1 style="color: #991b1b;">Order Cancelled & Refund Initiated</h1>
            <p class="subtitle">This order was cancelled by store management.</p>
            <div class="rejection-notice-box">
                <h3 style="margin-bottom:8px; font-size:15px; color:#991b1b;"><i class="fa-solid fa-clock-rotate-left"></i> Automatic Refund Processing</h3>
                <p style="font-size:13px; color:#7F1D1D; line-height:1.6;">If you paid online via Razorpay, your payment of <b>₹{{ order.amount }}</b> will be automatically credited back to your original payment method within <b>2 to 3 business days</b>.</p>
            </div>
            <div class="order-info-box">
                <div class="info-row"><span>Order ID:</span><b style="font-family:monospace; font-size:15px; color:#991b1b;">{{ order.order_id }}</b></div>
                <div class="info-row"><span>Customer Name:</span><b>{{ order.name }}</b></div>
                <div class="info-row"><span>Order Status:</span><b style="color:#991b1b;">Cancelled / Rejected</b></div>
                <div class="info-row"><span>Total Amount:</span><b>₹{{ order.amount }}</b></div>
            </div>
            <a href="/" class="btn-home">Return to Storefront</a>
        {% else %}
            <div class="icon-box"><i class="fa-solid fa-check"></i></div>
            <h1>Order Confirmed Successfully!</h1>
            <p class="subtitle">Thank you for choosing CHIRANJEEVI . Track your live shipment status below.</p>
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
                {% if order.status_step == 5 %}
                <div class="tracker-step active">
                    <div class="step-icon" style="background:#854d0e; color:white;"><i class="fa-solid fa-coins"></i></div>
                    <span>Refunded</span>
                </div>
                {% endif %}
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
                    <li>{{ i.name }} {% if i.size %}({{ i.size }}){% endif %} (Qty: {{ i.quantity | default(1) }}) — ₹{{ i.price * (i.quantity | default(1)) }}</li>
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
        {% endif %}
    </div>
</body>
</html>
"""

PRODUCT_HISTORY_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Botanical Origin Certificate</title>
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
            <div class="meta-item"><span>Customer Name</span><strong>{{ order.name }}</strong></div>
            <div class="meta-item"><span>Order Reference ID</span><strong>{{ order.order_id }}</strong></div>
            <div class="meta-item"><span>Date of Purchase</span><strong>{{ order.date }}</strong></div>
            <div class="meta-item"><span>Verification Status</span><strong style="color: #2e7d32;"><i class="fa-solid fa-circle-check"></i> Authentic Botanical Batch</strong></div>
        </div>
        <div class="history-section-title"><i class="fa-solid fa-seedling" style="color: var(--accent-gold);"></i> Sourced Ingredients & Product History (Your Order)</div>
        {% for item in order.items %}
        <div class="prod-history-card">
            <div class="prod-history-title"><span>{{ item.name }} {% if item.size %}({{ item.size }}){% endif %}</span><span class="geo-badge">Quantity: {{ item.quantity | default(1) }}</span></div>
            <div class="geo-detail"><i class="fa-solid fa-map-location-dot"></i> <b>Geographical Origin:</b> {{ item.geography | default('Sourced from organic Indian herb fields.') }}</div>
            <div class="geo-detail"><i class="fa-solid fa-flask"></i> <b>Extraction & Harvesting Technique:</b> {{ item.extraction | default('Cold-pressed & steam-distilled.') }}</div>
            {% if item.ingredients %}
            <div class="geo-detail"><i class="fa-solid fa-leaf"></i> <b>Botanical Formula:</b> {{ item.ingredients }}</div>
            {% endif %}
        </div>
        {% endfor %}
        <div class="cert-footer">
            <p><i class="fa-solid fa-shield-halved"></i> Verified by CHIRANJEEVI  Quality Control Laboratory.</p>
            <p style="margin-top:4px;">100% Organic • Cruelty-Free • Zero Paraben Formulation</p>
        </div>
    </div>
</body>
</html>
"""

SHIPPING_LABEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Shipping Label - {{ order.order_id }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: 'Poppins', Arial, sans-serif; margin: 0; padding: 20px; background: #f0f2f5; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; }
        .label-card { width: 450px; background: #fff; border: 3px solid #1b4332; border-radius: 12px; padding: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); position: relative; }
        .label-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1b4332; padding-bottom: 12px; margin-bottom: 15px; }
        .logo-text { font-size: 16px; font-weight: 800; color: #1b4332; text-transform: uppercase; letter-spacing: 0.5px; }
        .ship-tag { background: #1b4332; color: #fff; padding: 4px 10px; font-size: 11px; font-weight: bold; border-radius: 4px; text-transform: uppercase; }
        .section-title { font-size: 11px; text-transform: uppercase; color: #666; font-weight: bold; letter-spacing: 1px; margin-bottom: 4px; }
        .address-box { margin-bottom: 15px; background: #f9f9f9; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; }
        .address-box p { margin: 2px 0; font-size: 13px; color: #333; line-height: 1.4; }
        .bold-text { font-weight: 700; color: #1b4332; font-size: 14.5px; }
        .pincode-large { font-size: 24px; font-weight: 800; color: #1b4332; letter-spacing: 2px; border: 2px dashed #1b4332; display: inline-block; padding: 4px 12px; border-radius: 6px; margin-top: 8px; background: #fff; }
        .payment-banner { text-align: center; border-radius: 8px; padding: 12px; margin-bottom: 15px; font-weight: bold; font-size: 18px; text-transform: uppercase; letter-spacing: 1px; }
        .prepaid { background: #dcfce7; color: #166534; border: 2px solid #22c55e; }
        .cod { background: #fee2e2; color: #991b1b; border: 2px solid #ef4444; }
        .details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px; }
        .detail-item { font-size: 12px; color: #555; }
        .qr-container { display: flex; justify-content: space-between; align-items: center; border-top: 2px dashed #1b4332; padding-top: 15px; margin-top: 15px; }
        .qr-text { font-size: 11px; color: #555; max-width: 260px; line-height: 1.4; }
        .qr-image { width: 95px; height: 95px; }
        .no-print-btn { display: inline-block; padding: 10px 20px; background: #1b4332; color: #fff; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; text-decoration: none; margin-bottom: 15px; transition: 0.2s; }
        .no-print-btn:hover { background: #2d6a4f; }
        .actions-container { text-align: center; width: 450px; }
        @media print { body { background: #fff; padding: 0; display: block; } .label-card { border: 2px solid #000; box-shadow: none; width: 100%; max-width: 100%; border-radius: 0; padding: 15px; page-break-inside: avoid; } .no-print-btn, .actions-container { display: none !important; } }
    </style>
</head>
<body>
    <div class="actions-container"><button class="no-print-btn" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Shipping Label</button></div>
    <div class="label-card">
        <div class="label-header"><div class="logo-text">{{ settings.brand_name }}</div><div class="ship-tag">E-Commerce Shipment</div></div>
        {% if order.payment_mode == 'cod' %}<div class="payment-banner cod">COD - Collect ₹{{ order.amount }}</div>
        {% else %}<div class="payment-banner prepaid">PREPAID - Do Not Collect Cash</div>{% endif %}
        <div class="address-box">
            <div class="section-title">Ship To (Deliver to):</div>
            <p class="bold-text">{{ order.name }}</p>
            <p>{{ order.street }}</p>
            {% if order.landmark %}<p>Landmark: {{ order.landmark }}</p>{% endif %}
            <p>{{ order.city }}, {{ order.state }}</p>
            <p class="bold-text" style="margin-top: 5px;">Phone: {{ order.phone }}</p>
            <div class="pincode-large">{{ order.pincode }}</div>
        </div>
        <div class="address-box" style="background:#fff;">
            <div class="section-title">Seller Details (From):</div>
            <p class="bold-text">{{ settings.brand_name }}</p>
            <p>Support Phone: +91 9163641507</p>
            <p>Email: keshaadar@gmail.com</p>
        </div>
        <div class="details-grid">
            <div class="detail-item"><span class="section-title">Order reference:</span><br><strong style="color:#1b4332; font-family: monospace; font-size: 13px;">{{ order.order_id }}</strong></div>
            <div class="detail-item"><span class="section-title">Date:</span><br><strong>{{ order.date.split(' - ')[0] }}</strong></div>
        </div>
        <div style="font-size: 11px; border-top: 1px solid #ddd; padding-top: 8px;">
            <span class="section-title">Items Checklist:</span>
            <ul style="margin: 4px 0 0 15px; padding: 0; color: #444;">
                {% for item in order.items %}
                <li>{{ item.name }} {% if item.size %}({{ item.size }}){% endif %} [Qty: {{ item.quantity | default(1) }}]</li>
                {% endfor %}
            </ul>
        </div>
        <div class="qr-container">
            <div class="qr-text"><strong style="color:#1b4332; display:block; margin-bottom: 2px;">SCAN TO VERIFY BATCH AUTHENTICITY</strong> This QR code links directly to the customer's secure botanical sourcing record, tracing organic harvest geography and ingredients.</div>
            <img class="qr-image" src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://127.0.0.1:5644/order_history/{{ order.order_id }}" alt="QR Code">
        </div>
    </div>
</body>
</html>
"""

HTML_INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Invoice - {{ order.order_id }}</title>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: 'Poppins', sans-serif; background: #f0f2f5; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; }
        .invoice-card { width: 700px; background: #fff; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; }
        .invoice-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px; }
        .brand-logo-container { display: flex; align-items: center; gap: 15px; }
        .brand-logo { width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #d4a373; }
        .brand-title { font-size: 20px; font-weight: 700; color: #1b4332; text-transform: uppercase; margin: 0; }
        .brand-tagline { font-size: 11px; color: #666; margin: 2px 0 0 0; }
        .invoice-title { font-size: 16px; font-weight: 700; color: #d4a373; text-transform: uppercase; text-align: right; letter-spacing: 1px; }
        .meta-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        .meta-table td { padding: 10px; border: 1px solid #d1d5db; font-size: 13px; vertical-align: middle; }
        .meta-label { background: #f3f4f6; font-weight: 700; color: #374151; width: 20%; }
        .meta-value { color: #1f2937; width: 30%; }
        .section-banner { background: #1b4332; color: white; padding: 8px 12px; font-size: 12px; font-weight: 700; border-radius: 4px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; }
        .items-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        .items-table th, .items-table td { padding: 10px 12px; border: 1px solid #e5e7eb; font-size: 13px; text-align: left; }
        .items-table th { background: #f9fafb; color: #1b4332; font-weight: 700; border-bottom: 2px solid #1b4332; }
        .items-table td { color: #1f2937; }
        .total-row { background: #fcfbf9; font-weight: 700; }
        .words-box { border: 1px solid #d1d5db; background: #f8fafc; padding: 12px; border-radius: 6px; font-size: 13px; margin-bottom: 25px; display: flex; gap: 10px; }
        .words-label { font-weight: 700; color: #374151; }
        .words-value { color: #1f2937; }
        .qr-section { display: flex; justify-content: space-between; align-items: center; background: #faf7f0; border: 1px solid #d4a373; padding: 15px; border-radius: 8px; margin-bottom: 25px; }
        .qr-text { font-size: 12px; color: #1f2937; max-width: 480px; line-height: 1.5; }
        .qr-img { width: 90px; height: 90px; }
        .footer-hr { border: 0; border-top: 1px solid #d1d5db; margin-bottom: 15px; }
        .footer-grid { display: flex; justify-content: space-between; font-size: 12px; color: #475569; }
        .no-print-btn { display: inline-block; padding: 10px 20px; background: #1b4332; color: #fff; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; text-decoration: none; margin-bottom: 15px; transition: 0.2s; }
        .no-print-btn:hover { background: #2d6a4f; }
        .actions-container { text-align: center; width: 700px; }
        @media print { body { background: #fff; padding: 0; display: block; } .invoice-card { border: none; box-shadow: none; width: 100%; max-width: 100%; padding: 0; } .no-print-btn, .actions-container { display: none !important; } }
    </style>
</head>
<body>
    <div class="actions-container"><button class="no-print-btn" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Invoice / Save as PDF</button></div>
    <div class="invoice-card">
        <div class="invoice-header">
            <div class="brand-logo-container"><img src="{{ settings.logo }}" class="brand-logo" alt="Logo"><div><h1 class="brand-title">{{ settings.brand_name }}</h1><p class="brand-tagline">{{ settings.tagline }}</p></div></div>
            <div class="invoice-title">Order Price Invoice</div>
        </div>
        <table class="meta-table">
            <tr><td class="meta-label">Invoice Number</td><td class="meta-value">INV-{{ order.order_id.replace('ADOR-', '') }}</td><td class="meta-label">Invoice Date</td><td class="meta-value">{{ order.date.split(' - ')[0] }}</td></tr>
            <tr><td class="meta-label">Order ID</td><td class="meta-value">{{ order.order_id }}</td><td class="meta-label">Customer Name</td><td class="meta-value">{{ order.name }}</td></tr>
            <tr><td class="meta-label">Customer Details</td><td class="meta-value">{{ order.phone }} / {{ order.email }} / {{ order.street }}</td><td class="meta-label">Customer State</td><td class="meta-value">{{ order.state }}</td></tr>
        </table>
        <div class="section-banner">Order Details</div>
        <table class="items-table">
            <thead><tr><th>Particulars</th><th style="width: 10%; text-align: center;">Qty</th><th style="width: 20%; text-align: right;">Unit Price</th><th style="width: 20%; text-align: right;">Amount</th></tr></thead>
            <tbody>
                {% set ns = namespace(subtotal=0) %}
                {% for item in order.items %}
                {% set amt = item.price * (item.quantity | default(1)) %}
                {% set ns.subtotal = ns.subtotal + amt %}
                <tr><td>{{ item.name }} {% if item.size %}({{ item.size }}){% endif %}</td><td style="text-align: center;">{{ item.quantity | default(1) }}</td><td style="text-align: right;">₹{{ "{:.2f}".format(item.price) }}</td><td style="text-align: right;">₹{{ "{:.2f}".format(amt) }}</td></tr>
                {% endfor %}
                <tr class="total-row"><td colspan="3" style="text-align: right;">Subtotal:</td><td style="text-align: right;">₹{{ "{:.2f}".format(ns.subtotal) }}</td></tr>
                <tr class="total-row"><td colspan="3" style="text-align: right;">Tax (18% GST Incl.):</td><td style="text-align: right;">₹{{ "{:.2f}".format(ns.subtotal * 0.18) }}</td></tr>
                <tr class="total-row" style="background: #faf7f2; color: #1b4332; font-size: 14px;"><td colspan="3" style="text-align: right; text-transform: uppercase;">Grand Total:</td><td style="text-align: right;">₹{{ "{:.2f}".format(order.amount) }}</td></tr>
            </tbody>
        </table>
        <div class="words-box"><span class="words-label">Total Amount (in words):</span><span class="words-value" id="words-text"></span></div>
        <div class="qr-section"><div class="qr-text"><strong style="color: #1b4332; display: block; margin-bottom: 4px;">SCAN QR CODE FOR BOTANICAL PRODUCT ORIGIN & HISTORY</strong> Scan this code to open your dedicated product certificate page. Displays harvest locations, extraction techniques, and formula details exclusively for your ordered items.</div><img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=http://127.0.0.1:5644/order_history/{{ order.order_id }}" class="qr-img" alt="QR Code"></div>
        <hr class="footer-hr"><div class="footer-grid"><span>Thank you for choosing CHIRANJEEVI .</span><strong>Authorized Signature</strong></div>
    </div>
    <script>
        function numToWordsINR(amount) {
            try {
                let n = Math.round(amount);
                if (n === 0) return "Zero Rupees Only";
                const units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
                const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];
                function convertBelowThousand(num) {
                    if (num === 0) return "";
                    else if (num < 20) return units[num] + " ";
                    else if (num < 100) return tens[Math.floor(num / 10)] + " " + convertBelowThousand(num % 10);
                    else return units[Math.floor(num / 100)] + " Hundred " + convertBelowThousand(num % 100);
                }
                let words = "";
                if (n >= 10000000) { words += convertBelowThousand(Math.floor(n / 10000000)) + "Crore "; n %= 10000000; }
                if (n >= 100000) { words += convertBelowThousand(Math.floor(n / 100000)) + "Lakh "; n %= 100000; }
                if (n >= 1000) { words += convertBelowThousand(Math.floor(n / 1000)) + "Thousand "; n %= 1000; }
                if (n > 0) { words += convertBelowThousand(n); }
                return words.trim() + " Rupees Only";
            } catch (e) { return amount + " Rupees Only"; }
        }
        document.getElementById("words-text").innerText = numToWordsINR({{ order.amount }});
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7784, debug=True)

