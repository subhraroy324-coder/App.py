const ADMIN_USER = "vernex";
const ADMIN_PASS = "vernex@16vx";
const MASTER_API_KEY = "explorer16";

let API_KEYS = {
  "SHAYAN_DEMO_KEY": {
    expiry: "2030-12-31T23:59",
    limit: 500,
    used: 0,
    tools: ["all"]
  }
};

let ACTIVITY_LOGS = [];

const TOOLS_MAP = {
  "adv": ["https://ft-osint-api.duckdns.org/api/adv", "num"],
  "paytm": ["https://ft-osint-api.duckdns.org/api/paytm", "num"],
  "imei": ["https://ft-osint-api.duckdns.org/api/imei", "imei"],
  "calltracer": ["https://ft-osint-api.duckdns.org/api/calltracer", "num"],
  "upi": ["https://ft-osint-api.duckdns.org/api/upi", "upi"],
  "ifsc": ["https://ft-osint-api.duckdns.org/api/ifsc", "ifsc"],
  "pincode": ["https://ft-osint-api.duckdns.org/api/pincode", "pin"],
  "ip": ["https://ft-osint-api.duckdns.org/api/ip", "ip"],
  "challan": ["https://ft-osint-api.duckdns.org/api/challan", "vehicle"],
  "ff": ["https://ft-osint-api.duckdns.org/api/ff", "uid"],
  "bgmi": ["https://ft-osint-api.duckdns.org/api/bgmi", "uid"],
  "snap": ["https://ft-osint-api.duckdns.org/api/snap", "username"],
  "number": ["https://ft-osint-api.duckdns.org/api/number", "num"],
  "email": ["https://ft-osint-api.duckdns.org/api/email", "email"],
  "vehicle": ["https://ft-osint-api.duckdns.org/api/vehicle", "vehicle"],
  "git": ["https://ft-osint-api.duckdns.org/api/git", "username"],
  "insta": ["https://ft-osint-api.duckdns.org/api/insta", "username"],
  "tg": ["https://ft-osint-api.duckdns.org/api/tg", "info"],
  "tgidinfo": ["https://ft-osint-api.duckdns.org/api/tgidinfo", "id"],
  "numleak": ["https://ft-osint-api.duckdns.org/api/numleak", "num"]
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path.startsWith("/api/")) {
      const toolName = path.split("/")[2];
      const userKey = url.searchParams.get("key");

      if (!userKey || !API_KEYS[userKey]) {
        return Response.json({ error: "Unauthorized", message: "Invalid or missing API key. Developer: SHAYAN_EXPLORER" }, { status: 403 });
      }

      const keyData = API_KEYS[userKey];

      if (keyData.expiry && new Date() > new Date(keyData.expiry)) {
        return Response.json({ error: "Forbidden", message: "API Key has expired. Developer: SHAYAN_EXPLORER" }, { status: 403 });
      }

      if (keyData.used >= keyData.limit) {
        return Response.json({ error: "Forbidden", message: "API Key request limit exhausted. Developer: SHAYAN_EXPLORER" }, { status: 403 });
      }

      if (!keyData.tools.includes("all") && !keyData.tools.includes(toolName)) {
        return Response.json({ error: "Forbidden", message: "Your key is not authorized for this specific tool." }, { status: 403 });
      }

      if (!TOOLS_MAP[toolName]) {
        return Response.json({ error: "Not Found", message: "Invalid tool endpoint." }, { status: 404 });
      }

      const [baseUrl, paramName] = TOOLS_MAP[toolName];
      const paramVal = url.searchParams.get(paramName) || "";

      keyData.used += 1;
      ACTIVITY_LOGS.push({
        key: userKey,
        tool: toolName,
        query: paramVal,
        timestamp: new Date().toISOString()
      });

      const targetUrl = `${baseUrl}?key=${MASTER_API_KEY}&${paramName}=${encodeURIComponent(paramVal)}`;

      try {
        const apiResp = await fetch(targetUrl);
        let textData = await apiResp.text();

        textData = textData
          .replace(/ftgamer2/g, "SHAYAN_EXPLORER")
          .replace(/bornex/g, "SHAYAN_EXPLORER")
          .replace(/Ultra/g, "SHAYAN_EXPLORER");

        let jsonData;
        try {
          jsonData = JSON.parse(textData);
        } catch {
          jsonData = { response: textData };
        }

        if (typeof jsonData === "object" && jsonData !== null) {
          jsonData.developer = "SHAYAN_EXPLORER";
        }

        return Response.json(jsonData);
      } catch (err) {
        return Response.json({ error: "Gateway Error", message: err.message, developer: "SHAYAN_EXPLORER" }, { status: 500 });
      }
    }

    const cookie = request.headers.get("Cookie") || "";
    const isLoggedIn = cookie.includes("auth=true");

    if (path === "/logout") {
      return new Response("Logged out", {
        status: 302,
        headers: { Location: "/login", "Set-Cookie": "auth=false; Path=/;" }
      });
    }

    if (path === "/login" && request.method === "POST") {
      const formData = await request.formData();
      if (formData.get("username") === ADMIN_USER && formData.get("password") === ADMIN_PASS) {
        return new Response("", {
          status: 302,
          headers: { Location: "/", "Set-Cookie": "auth=true; Path=/; HttpOnly" }
        });
      }
      return Response.redirect(`${url.origin}/login?error=1`, 302);
    }

    if (!isLoggedIn && path !== "/login") {
      return Response.redirect(`${url.origin}/login`, 302);
    }

    if (path === "/login") {
      return new HtmlResponse(loginPageHtml());
    }

    if (path === "/create_key" && request.method === "POST") {
      const formData = await request.formData();
      const keyName = formData.get("key_name");
      const expiry = formData.get("expiry");
      const limit = parseInt(formData.get("limit") || "100");
      const tools = formData.getAll("tools");

      if (keyName) {
        API_KEYS[keyName] = { expiry, limit, used: 0, tools };
      }
      return Response.redirect(`${url.origin}/`, 302);
    }

    if (path.startsWith("/delete_key/")) {
      const keyName = path.split("/")[2];
      if (API_KEYS[keyName]) delete API_KEYS[keyName];
      return Response.redirect(`${url.origin}/`, 302);
    }

    return new HtmlResponse(dashboardHtml(API_KEYS, ACTIVITY_LOGS));
  }
};

class HtmlResponse extends Response {
  constructor(html) {
    super(html, { headers: { "Content-Type": "text/html;charset=UTF-8" } });
  }
}

function loginPageHtml() {
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Login - SHAYAN_EXPLORER</title>
<style>
body { background: #0d1117; color: #c9d1d9; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
.card { background: #161b22; border: 1px solid #30363d; padding: 30px; border-radius: 12px; width: 320px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: center; }
input { width: 100%; padding: 10px; margin: 10px 0; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 6px; box-sizing: border-box; }
button { background: #238636; color: white; border: none; padding: 12px; width: 100%; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 10px; }
</style></head>
<body>
<div class="card">
    <h2>🚀 SHAYAN Portal</h2>
    <p style="font-size:12px; color:#8b949e;">Login: vernex / vernex@16vx</p>
    <form action="/login" method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login Securely</button>
    </form>
</div></body></html>`;
}

function dashboardHtml(keys, logs) {
  let keyRows = Object.entries(keys).map(([name, data]) => `
    <tr><td><b>${name}</b></td><td>${data.expiry}</td><td>${data.used} / ${data.limit}</td><td>${data.tools.join(', ')}</td><td><a href="/delete_key/${name}" style="color:#ff7b72; text-decoration:none;">Revoke</a></td></tr>
  `).join('');

  let logRows = logs.slice(-25).reverse().map(l => `
    <tr><td>${l.timestamp}</td><td><code>${l.key}</code></td><td><span style="background:#1f6feb; padding:2px 6px; border-radius:4px; font-size:11px;">${l.tool}</span></td><td><code>${l.query}</code></td></tr>
  `).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>SHAYAN_EXPLORER Control Center</title>
<style>
body { background: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; }
nav { background: #111418; padding: 15px 30px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
nav h1 { color: #00ffcc; font-size: 18px; margin: 0; }
.container { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }
.stat { background: #111418; padding: 15px; border-radius: 8px; border: 1px solid #30363d; }
.stat h3 { margin: 0; font-size: 13px; color: #8b949e; }
.stat p { font-size: 20px; font-weight: bold; color: #58a6ff; margin: 8px 0 0 0; }
input { width: 100%; padding: 10px; background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; border-radius: 6px; box-sizing: border-box; margin-top: 5px; }
.row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 15px; }
.group { text-align: left; margin-bottom: 15px; font-size: 13px; color: #8b949e; }
.tools-box { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; background: #0d1117; padding: 10px; border-radius: 6px; border: 1px solid #30363d; max-height: 100px; overflow-y: auto; }
button { background: linear-gradient(135deg, #238636, #2ea043); color: white; border: none; padding: 12px; border-radius: 6px; font-weight: bold; cursor: pointer; width: 100%; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { padding: 10px; text-align: left; border-bottom: 1px solid #30363d; font-size: 13px; }
th { color: #8b949e; }
code { background: #0d1117; padding: 2px 6px; border-radius: 4px; color: #ff7b72; }
.logout { background: #da3633; color: white; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 13px; }
</style></head>
<body>
<nav>
    <h1>⚡ SHAYAN_EXPLORER Cloudflare Gateway</h1>
    <a href="/logout" class="logout">Logout</a>
</nav>
<div class="container">
    <div class="grid">
        <div class="card stat"><h3>Active Keys</h3><p>${Object.keys(keys).length}</p></div>
        <div class="card stat"><h3>Total Logs</h3><p>${logs.length}</p></div>
        <div class="card stat"><h3>Status</h3><p style="color:#00ffcc">GitHub & CF Connected</p></div>
    </div>
    <div class="card">
        <h2>🔑 Generate Custom API Key</h2>
        <form action="/create_key" method="POST">
            <div class="row">
                <div class="group">Key Name<input type="text" name="key_name" placeholder="client_01" required></div>
                <div class="group">Expiry Date & Time<input type="datetime-local" name="expiry" required></div>
                <div class="group">Request Limit<input type="number" name="limit" value="100" required></div>
            </div>
            <div class="group">Tool Permissions
                <div class="tools-box">
                    <label><input type="checkbox" name="tools" value="all" checked> ALL TOOLS</label>
                    ${Object.keys(TOOLS_MAP).map(t => `<label><input type="checkbox" name="tools" value="${t}"> ${t.toUpperCase()}</label>`).join('')}
                </div>
            </div>
            <button type="submit">Deploy Key to Edge</button>
        </form>
    </div>
    <div class="card">
        <h2>Manage Keys</h2>
        <table><tr><th>Key Name</th><th>Expires</th><th>Limit</th><th>Tools</th><th>Action</th></tr>${keyRows}</table>
    </div>
    <div class="card">
        <h2>📊 Real-Time Logs</h2>
        <table><tr><th>Timestamp</th><th>Key</th><th>Tool</th><th>Query</th></tr>${logRows}</table>
    </div>
</div></body></html>`;
}
