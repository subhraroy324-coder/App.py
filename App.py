from flask import Flask, request, jsonify
import time
import random
import string
import os

app = Flask(__name__)

keys_db = {}

def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))


@app.route("/")
def home():
    return "VERNEX API RUNNING"


@app.route("/generate")
def generate():
    try:
        days = request.args.get("days")
        lifetime = request.args.get("lifetime")

        key = generate_key()

        if lifetime == "true":
            expiry = None
            valid = "lifetime"
        else:
            days = int(days)
            expiry = time.time() + (days * 86400)
            valid = f"{days} days"

        keys_db[key] = expiry

        return jsonify({
            "status": "success",
            "key": key,
            "valid": valid,
            "expiry": expiry
        })

    except:
        return jsonify({"status": "error"})


@app.route("/api/numinfo")
def numinfo():
    key = request.args.get("key")
    num = request.args.get("num")

    if key not in keys_db:
        return jsonify({"status": "error", "message": "Invalid key"})

    expiry = keys_db[key]

    if expiry is not None and time.time() > expiry:
        return jsonify({"status": "error", "message": "Key expired"})

    return jsonify({
        "status": "success",
        "number": num,
        "message": "Valid key"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
