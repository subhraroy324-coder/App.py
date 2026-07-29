import time
import httpx
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI(title="SHAYAN_EXPLORER HUB", version="2.0.0")
security = HTTPBasic()
templates = Jinja2Templates(directory="templates")

# Admin Credentials
ADMIN_USER = "vernex"
ADMIN_PASS = "vernex@16vx"

# In-Memory Database (For production, swap with PostgreSQL/MongoDB)
API_KEYS_DB = {
    "vx-osint": {
        "key": "vx-osint",
        "customer_name": "Master Deployment",
        "email": "admin@shayan.hub",
        "type": "Lifetime",
        "expiry": "Lifetime",
        "daily_limit": 5000,
        "usage_count": 0,
        "scope": ["ALL"],
        "status": "Active",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
}

REQUEST_LOGS = []

# Available OSINT Endpoints Mapping
ENDPOINTS_MAP = {
    "adv": "https://ft-osint-api.duckdns.org/api/adv?key={key}&num={num}",
    "paytm": "https://ft-osint-api.duckdns.org/api/paytm?key={key}&num={num}",
    "imei": "https://ft-osint-api.duckdns.org/api/imei?key={key}&imei={imei}",
    "calltracer": "https://ft-osint-api.duckdns.org/api/calltracer?key={key}&num={num}",
    "upi": "https://ft-osint-api.duckdns.org/api/upi?key={key}&upi={upi}",
    "ifsc": "https://ft-osint-api.duckdns.org/api/ifsc?key={key}&ifsc={ifsc}",
    "number": "https://ft-osint-api.duckdns.org/api/number?key={key}&num={num}",
    "pincode": "https://ft-osint-api.duckdns.org/api/pincode?key={key}&pin={pin}",
    "ip": "https://ft-osint-api.duckdns.org/api/ip?key={key}&ip={ip}",
    "challan": "https://ft-osint-api.duckdns.org/api/challan?key={key}&vehicle={vehicle}",
    "ff": "https://ft-osint-api.duckdns.org/api/ff?key={key}&uid={uid}",
    "bgmi": "https://ft-osint-api.duckdns.org/api/bgmi?key={key}&uid={uid}",
    "snap": "https://ft-osint-api.duckdns.org/api/snap?key={key}&username={username}",
    "email": "https://ft-osint-api.duckdns.org/api/email?key={key}&email={email}",
    "vehicle": "https://ft-osint-api.duckdns.org/api/vehicle?key={key}&vehicle={vehicle}",
    "git": "https://ft-osint-api.duckdns.org/api/git?key={key}&username={username}",
    "insta": "https://ft-osint-api.duckdns.org/api/insta?key={key}&username={username}",
    "tg": "https://ft-osint-api.duckdns.org/api/tg?key={key}&info={info}",
    "tgidinfo": "https://ft-osint-api.duckdns.org/api/tgidinfo?key={key}&id={id}",
    "numleak": "https://ft-osint-api.duckdns.org/api/numleak?key={key}&num={num}"
}

class KeyCreateRequest(BaseModel):
    customer_name: str
    email: Optional[str] = ""
    custom_key: Optional[str] = ""
    key_type: str = "Lifetime"  # Lifetime or Custom Expiry
    expiry: Optional[str] = None
    daily_limit: int = 1000
    scope_type: str = "ALL"  # ALL or Specific
    tools: List[str] = []

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != ADMIN_USER or credentials.password != ADMIN_PASS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, username: str = Depends(verify_admin)):
    return templates.TemplateResponse("index.html", {"request": request, "tools": list(ENDPOINTS_MAP.keys())})

@app.get("/api/admin/keys")
def get_keys(username: str = Depends(verify_admin)):
    return list(API_KEYS_DB.values())

@app.post("/api/admin/keys")
def create_key(data: KeyCreateRequest, username: str = Depends(verify_admin)):
    key_str = data.custom_key.strip() if data.custom_key else f"vx-{int(time.time())}"
    if key_str in API_KEYS_DB:
        raise HTTPException(status_code=400, detail="Key already exists!")
    
    API_KEYS_DB[key_str] = {
        "key": key_str,
        "customer_name": data.customer_name,
        "email": data.email,
        "type": data.key_type,
        "expiry": data.expiry if data.key_type != "Lifetime" else "Lifetime",
        "daily_limit": data.daily_limit,
        "usage_count": 0,
        "scope": ["ALL"] if data.scope_type == "ALL" else data.tools,
        "status": "Active",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"status": "success", "key": key_str}

@app.delete("/api/admin/keys/{key_id}")
def delete_key(key_id: str, username: str = Depends(verify_admin)):
    if key_id in API_KEYS_DB:
        del API_KEYS_DB[key_id]
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Key not found")

@app.post("/api/admin/keys/{key_id}/toggle")
def toggle_key(key_id: str, username: str = Depends(verify_admin)):
    if key_id in API_KEYS_DB:
        current = API_KEYS_DB[key_id]["status"]
        API_KEYS_DB[key_id]["status"] = "Suspended" if current == "Active" else "Active"
        return {"status": "success", "new_status": API_KEYS_DB[key_id]["status"]}
    raise HTTPException(status_code=404, detail="Key not found")

@app.get("/api/admin/logs")
def get_logs(username: str = Depends(verify_admin)):
    return REQUEST_LOGS[::-1] # latest first

# Proxy Unified Endpoints
@app.get("/api/v1/{tool}")
async def proxy_tool(tool: str, key: str = Query(...), request: Request = None):
    if tool not in ENDPOINTS_MAP:
        raise HTTPException(status_code=404, detail="Invalid OSINT tool endpoint.")
    
    if key not in API_KEYS_DB:
        raise HTTPException(status_code=403, detail="Invalid API Key.")
    
    key_data = API_KEYS_DB[key]
    if key_data["status"] != "Active":
        raise HTTPException(status_code=403, detail="API Key is suspended or disabled.")
    
    if "ALL" not in key_data["scope"] and tool not in key_data["scope"]:
        raise HTTPException(status_code=403, detail="Your API Key does not have authorization scope for this tool.")
    
    if key_data["usage_count"] >= key_data["daily_limit"]:
        raise HTTPException(status_code=429, detail="API Rate limit / Daily limit exceeded.")

    # Increment usage
    key_data["usage_count"] += 1

    # Extract query parameters dynamically
    query_params = dict(request.query_params)
    query_params["key"] = "vernex-6a9dc4fdd5923c40b0aba27bf1e39e3f" # Upstream Master Key Connector

    target_url_template = ENDPOINTS_MAP[tool]
    # Build target URL
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(target_url_template.split("?")[0], params=query_params)
            res_json = resp.json()
        except Exception as e:
            res_json = {"error": "Upstream service timeout or parsing failure", "details": str(e)}

    # Log Request
    REQUEST_LOGS.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "key": key,
        "endpoint": tool,
        "params": str(dict(request.query_params))
    })
    if len(REQUEST_LOGS) > 200:
        REQUEST_LOGS.pop(0)

    return JSONResponse(content=res_json)
