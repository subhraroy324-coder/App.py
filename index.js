const ADMIN_USER = "vernex";
const ADMIN_PASS = "vernex@16vx";
const MASTER_API_KEY = "explorer16";

// Persistent global store fallback (In production, bind to Cloudflare KV)
let GLOBAL_KEYS = {
  "SHAYAN_MASTER_KEY": {
    expiry: "2099-12-31T23:59",
    limit: 999999,
    used: 0,
    tools: ["all"],
    status: "active",
    created: new Date().toISOString()
  }
};

let GLOBAL_LOGS = [];

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

    // --- API GATEWAY ENDPOINT ---
    if (path.startsWith("/api/")) {
      const toolName = path.split("/")[2];
      const userKey = url.searchParams.get("key");

      if (!userKey || !GLOBAL_KEYS[userKey]) {
        return Response.json({ error: "Unauthorized", message: "Invalid or missing API key. Developer: SHAYAN_EXPLORER" }, { status: 403 });
      }

      const keyData = GLOBAL_KEYS[userKey];

      if (keyData.status === "suspended") {
        return Response.json({ error: "Forbidden", message: "API Key is currently suspended by SHAYAN_EXPLORER." }, { status: 403 });
      }

      if (keyData.expiry !== "LIFETIME" && keyData.expiry && new Date() > new Date(keyData.expiry)) {
        return Response.json({ error: "Forbidden", message: "API Key has expired. Contact SHAYAN_EXPLORER." }, { status: 403 });
      }

      if (keyData.used >= keyData.limit) {
        return Response.json({ error: "Forbidden", message: "API Key request quota exhausted." }, { status: 403 });
      }

      if (!keyData.tools.includes("all") && !keyData.tools.includes(toolName)) {
        return Response.json({ error: "Forbidden", message: "Unauthorized tool access for this key." }, { status: 403 });
      }

      if (!TOOLS_MAP[toolName]) {
        return Response.json({ error: "Not Found", message: "Invalid OSINT tool endpoint." }, { status: 404 });
      }

      const [baseUrl, paramName] = TOOLS_MAP[toolName];
      const paramVal = url.searchParams.get(paramName) || "";

      keyData.used += 1;
      GLOBAL_LOGS.unshift({
        key: userKey,
        tool: toolName,
        query: paramVal,
        ip: request.headers.get("CF-Connecting-IP") || "127.0.0.1",
        timestamp: new Date().toISOString()
      });
      if (GLOBAL_LOGS.length > 200) GLOBAL_LOGS.pop(); // keep last 200 logs

      const targetUrl = `${baseUrl}?key=${MASTER_API_KEY}&${paramName}=${encodeURIComponent(paramVal)}`;

      try {
        const apiResp = await fetch(targetUrl);
        let textData = await apiResp.text();

        textData = textData
          .replace(/ftgamer2/g, "SHAYAN_EXPLORER")
          .replace(/bornex/g, "SHAYAN_EXPLORER")
          .replace(/Ultra/g, "SHAYAN_EXPLORER");

        let jsonData;
        try { jsonData = JSON.parse(textData); } catch { jsonData = { response: textData }; }

        if (typeof jsonData === "object" && jsonData !== null) {
          jsonData.developer = "SHAYAN_EXPLORER";
        }
        return Response.json(jsonData);
      } catch (err) {
        return Response.json({ error: "Gateway Error", message: err.message, developer: "SHAYAN_EXPLORER" }, { status: 500 });
      }
    }

    // --- AUTH & ADMIN PANEL ---
    const cookie = request.headers.get("Cookie") || "";
    const isLoggedIn = cookie.includes("auth=shayan_verified=true");

    if (path === "/logout") {
      return new Response("Logged out", {
        status: 302,
        headers: { Location: "/login", "Set-Cookie": "auth=shayan_verified=false; Path=/;" }
      });
    }

    if (path === "/login" && request.method === "POST") {
      const formData = await request.formData();
      if (formData.get("username") === ADMIN_USER && formData.get("password") === ADMIN_PASS) {
        return new Response("", {
          status: 302,
          headers: { Location: "/", "Set-Cookie": "auth=shayan_verified=true; Path=/; HttpOnly" }
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

    // ACTIONS: Create, Delete, Suspend, Unsuspend, Edit
    if (request.method === "POST") {
      const formData = await request.formData();
      const action = formData.get("action");

      if (action === "create") {
        const keyName = formData.get("key_name");
        let expiry = formData.get("expiry");
        const isLifetime = formData.get("lifetime");
        const limit = parseInt(formData.get("limit") || "1000");
        const tools = formData.getAll("tools");

        if (isLifetime === "on") expiry = "LIFETIME";
        if (keyName) {
          GLOBAL_KEYS[keyName] = { expiry, limit, used: 0, tools, status: "active", created: new Date().toISOString() };
        }
      } else if (action === "edit") {
        const keyName = formData.get("key_name");
        let expiry = formData.get("expiry");
        const isLifetime = formData.get("lifetime");
        const limit = parseInt(formData.get("limit") || "1000");
        const tools = formData.getAll("tools");

        if (isLifetime === "on") expiry = "LIFETIME";
        if (GLOBAL_KEYS[keyName]) {
          GLOBAL_KEYS[keyName].expiry = expiry;
          GLOBAL_KEYS[keyName].limit = limit;
          GLOBAL_KEYS[keyName].tools = tools;
        }
      } else if (action === "delete") {
        const keyName = formData.get("key_name");
        delete GLOBAL_KEYS[keyName];
      } else if (action === "toggle_status") {
        const keyName = formData.get("key_name");
        if (GLOBAL_KEYS[keyName]) {
          GLOBAL_KEYS[keyName].status = GLOBAL_KEYS[keyName].status === "active" ? "suspended" : "active";
        }
      }
      return Response.redirect(`${url.origin}/`, 302);
    }

    return new HtmlResponse(dashboardHtml(GLOBAL_KEYS, GLOBAL_LOGS, url.origin));
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
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Login - SHAYAN_EXPLORER</title>
<style>
body { background: #07090e; color: #e1e7ec; font-family: 'Segoe UI', Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
.card { background: linear-gradient(145deg, #121824, #0d121c); border: 1px solid #1f2937; padding: 40px; border-radius: 16px; width: 360px; box-shadow: 0 20px 50px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.1); text-align: center; }
h2 { color: #00ffcc; margin-top: 0; }
input { width: 100%; padding: 12px; margin: 12px 0; background: #080c14; border: 1px solid #2d3748; color: #fff; border-radius: 8px; box-sizing: border-box; font-size: 14px; }
input:focus { border-color: #00ffcc; outline: none; box-shadow: 0 0 10px rgba(0,255,204,0.3); }
button { background: linear-gradient(135deg, #00ffcc, #00bfff); color: #07090e; border: none; padding: 14px; width: 100%; border-radius: 8px; font-weight: bold; font-size: 15px; cursor: pointer; margin-top: 15px; transition: 0.3s; }
button:hover { opacity: 0.9; transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0,255,204,0.4); }
</style></head>
<body>
<div class="card">
    <h2>⚡ SHAYAN_EXPLORER</h2>
    <p style="font-size:12px; color:#94a3b8;">Admin Portal Access</p>
    <form action="/login" method="POST">
        <input type="text" name="username" placeholder="Username (vernex)" required>
        <input type="password" name="password" placeholder="Password (vernex@16vx)" required>
        <button type="submit">Authenticate Securely</button>
    </form>
</div></body></html>`;
}

function dashboardHtml(keys, logs, origin) {
  let toolList = Object.keys(TOOLS_MAP);
  
  let keyRows = Object.entries(keys).map(([name, data]) => `
    <tr>
      <td><b>${name}</b></td>
      <td><span class="badge ${data.status === 'active' ? 'badge-green' : 'badge-red'}">${data.status.toUpperCase()}</span></td>
      <td>${data.expiry}</td>
      <td>${data.used} / ${data.limit}</td>
      <td><span style="font-size:11px; color:#94a3b8;">${data.tools.join(', ')}</span></td>
      <td>
        <form style="display:inline;" method="POST">
          <input type="hidden" name="action" value="toggle_status">
          <input type="hidden" name="key_name" value="${name}">
          <button type="submit" class="btn-xs ${data.status === 'active' ? 'btn-warn' : 'btn-success'}">${data.status === 'active' ? 'Suspend' : 'Unsuspend'}</button>
        </form>
        <form style="display:inline;" method="POST" onsubmit="return confirm('Delete this key?');">
          <input type="hidden" name="action" value="delete">
          <input type="hidden" name="key_name" value="${name}">
          <button type="submit" class="btn-xs btn-danger">Delete</button>
        </form>
      </td>
    </tr>
  `).join('');

  let logRows = logs.slice(0, 50).lmap ? logs.slice(0, 50).map(l => `
    <tr>
      <td style="font-size:12px; color:#94a3b8;">${l.timestamp.replace('T', ' ').substring(0, 19)}</td>
      <td><code>${l.key}</code></td>
      <td><span class="badge badge-blue">${l.tool}</span></td>
      <td><code>${l.query}</code></td>
      <td style="font-size:12px;">${l.ip}</td>
    </tr>
  `).join('') : '';

  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>SHAYAN_EXPLORER OSINT Enterprise Control Center</title>
<style>
:root { --bg: #07090e; --panel: #111827; --border: #1f2937; --accent: #00ffcc; --text: #f3f4f6; --muted: #9ca3af; }
body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 0; }
header { background: rgba(17, 24, 39, 0.8); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
header h1 { color: var(--accent); font-size: 18px; margin: 0; display: flex; align-items: center; gap: 10px; }
.logout { background: #ef4444; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; transition: 0.2s; }
.logout:hover { background: #dc2626; }
.container { max-width: 1300px; margin: 30px auto; padding: 0 20px; }
.grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 25px; }
.card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05); transition: 0.3s; }
.card:hover { border-color: rgba(0,255,204,0.3); box-shadow: 0 15px 40px rgba(0,255,204,0.1); }
.stat-box h3 { margin: 0; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
.stat-box p { font-size: 26px; font-weight: 800; color: #60a5fa; margin: 10px 0 0 0; }
h2 { font-size: 18px; color: var(--text); margin-top: 0; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; }
.row { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 15px; }
.group { text-align: left; font-size: 13px; color: var(--muted); }
input, select { width: 100%; padding: 11px; background: #080c14; border: 1px solid var(--border); color: var(--text); border-radius: 8px; box-sizing: border-box; margin-top: 6px; font-size: 14px; }
input:focus, select:focus { border-color: var(--accent); outline: none; }
.tools-box { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; background: #080c14; padding: 12px; border-radius: 8px; border: 1px solid var(--border); max-height: 150px; overflow-y: auto; margin-top: 6px; font-size: 13px; }
.tools-box label { display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--text); }
.btn-primary { background: linear-gradient(135deg, #00ffcc, #00bfff); color: #07090e; border: none; padding: 13px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; font-size: 15px; transition: 0.2s; margin-top: 10px; }
.btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
table { width: 100%; border-collapse: collapse; margin-top: 10px; }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 13px; }
th { color: var(--muted); font-weight: 600; }
code { background: #080c14; padding: 3px 7px; border-radius: 4px; color: #f472b6; font-family: monospace; }
.badge { padding: 3px 8px; border-radius: 5px; font-size: 11px; font-weight: bold; text-transform: uppercase; }
.badge-green { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-red { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
.badge-blue { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
.btn-xs { padding: 5px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; cursor: pointer; border: none; }
.btn-success { background: #10b981; color: white; }
.btn-warn { background: #f59e0b; color: white; }
.btn-danger { background: #ef4444; color: white; }
.endpoints-box { background: #080c14; padding: 15px; border-radius: 8px; border: 1px solid var(--border); font-family: monospace; font-size: 12px; color: #38bdf8; overflow-x: auto; margin-top: 10px; }
@media (max-width: 768px) { .grid-3 { grid-template-columns: 1fr; } .row { grid-template-columns: 1fr; } }
</style></head>
<body>
<header>
    <h1>⚡ SHAYAN_EXPLORER OSINT Enterprise Hub</h1>
    <a href="/logout" class="logout">Logout</a>
</header>
<div class="container">
    <div class="grid-3">
        <div class="card stat-box"><h3>Active API Keys</h3><p>${Object.keys(keys).length}</p></div>
        <div class="card stat-box"><h3>Captured Request Logs</h3><p>${logs.length}</p></div>
        <div class="card stat-box"><h3>System Status</h3><p style="color:#34d399;">🟢 Operational</p></div>
    </div>

    <!-- Generate Key Card -->
    <div class="card">
        <h2>🔑 Create & Configure New API Key</h2>
        <form method="POST">
            <input type="hidden" name="action" value="create">
            <div class="row">
                <div class="group">Key Identifier / Name<input type="text" name="key_name" placeholder="client_tag_01" required></div>
                <div class="group">Expiration Date & Time<input type="datetime-local" name="expiry"></div>
                <div class="group">Request Limit Quota<input type="number" name="limit" value="500" required></div>
            </div>
            <div class="row" style="align-items: center; margin-top: 10px;">
                <div class="group"><label style="display:flex; align-items:center; gap:8px; cursor:pointer;"><input type="checkbox" name="lifetime" style="width:auto;"> **Enable Lifetime Validity** (Never Expires)</label></div>
            </div>
            <div class="group" style="margin-top:15px;">Assign Tool Access Permissions
                <div class="tools-box">
                    <label><input type="checkbox" name="tools" value="all" checked> 🌟 ALL TOOLS (Full)</label>
                    ${toolList.map(t => `<label><input type="checkbox" name="tools" value="${t}"> ${t.toUpperCase()}</label>`).join('')}
                </div>
            </div>
            <button type="submit" class="btn-primary">Generate & Deploy Key Instantly</button>
        </form>
    </div>

    <!-- Key Management Table -->
    <div class="card">
        <h2>📋 Active Keys Management & Control Panel</h2>
        <div style="overflow-x:auto;">
            <table>
                <tr><th>Key Name</th><th>Status</th><th>Expiry</th><th>Usage / Limit</th><th>Allowed Tools</th><th>Actions</th></tr>
                ${keyRows}
            </table>
        </div>
    </div>

    <!-- API Endpoints Reference -->
    <div class="card">
        <h2>🚀 Complete API Endpoints Reference</h2>
        <p style="font-size:13px; color:var(--muted);">Use your generated API keys with these endpoints across all tools:</p>
        <div class="endpoints-box">
            ${toolList.map(t => `<div><b>${t.toUpperCase()}:</b> ${origin}/api/${t}?key=YOUR_KEY&${TOOLS_MAP[t][1]}=EXAMPLE_VALUE</div>`).join('<br>')}
        </div>
    </div>

    <!-- Real-time Activity Logs -->
    <div class="card">
        <h2>📊 Real-Time Query Audit Logs & History</h2>
        <div style="overflow-x:auto;">
            <table>
                <tr><th>Timestamp</th><th>API Key</th><th>Tool</th><th>Query Payload</th><th>Client IP</th></tr>
                ${logRows || '<tr><td colspan="5" style="text-align:center; color:var(--muted);">No queries logged yet.</td></tr>'}
            </table>
        </div>
    </div>
</div></body></html>`;
}
