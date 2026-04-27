from http.server import BaseHTTPRequestHandler
import json
import time
import random
import string
from urllib.parse import urlparse, parse_qs

# TEMP storage (NOT reliable on Vercel)
keys_db = {}


def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self.respond({"message": "VERNEX API RUNNING"})

        elif path == "/generate":
            try:
                days = query.get("days", [None])[0]
                lifetime = query.get("lifetime", [None])[0]

                key = generate_key()

                if lifetime == "true":
                    expiry = None
                    valid = "lifetime"
                else:
                    days = int(days)
                    expiry = time.time() + (days * 86400)
                    valid = f"{days} days"

                keys_db[key] = expiry

                self.respond({
                    "status": "success",
                    "key": key,
                    "valid": valid,
                    "expiry": expiry
                })

            except:
                self.respond({"status": "error"})

        elif path == "/api/numinfo":
            key = query.get("key", [None])[0]
            num = query.get("num", [None])[0]

            if key not in keys_db:
                self.respond({"status": "error", "message": "Invalid key"})
                return

            expiry = keys_db[key]

            if expiry is not None and time.time() > expiry:
                self.respond({"status": "error", "message": "Key expired"})
                return

            self.respond({
                "status": "success",
                "number": num,
                "message": "Valid key"
            })

        else:
            self.respond({"error": "Not found"})

    def respond(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
