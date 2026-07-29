const ADMIN_USER = "vernex";
const ADMIN_PASS = "vernex@16vx";
const MASTER_API_KEY = "explorer16";

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

    // Helper for KV storage fallback if KV isn't bound yet
    const kv = env.SHAYAN_KV;

    // --- API GATEWAY ENDPOINT ---
    if (path.startsWith("/api/")) {
      const toolName = path.split("/")[2];
      const userKey = url.searchParams.get("key");

      let keysData = kv ? JSON.parse(await kv.get("KEYS") || "{}") : {
        "vx-osint": { owner: "Master Deployment", expiry: "LIFETIME", limit: 5000, used: 0, tools: ["all"], status: "Active" }
      };

      if (!userKey || !keysData[userKey]) {
        return Response.json({ error: "Unauthorized", message: "Invalid or missing API key. Developer: SHAYAN_EXPLORER" }, { status: 403 });
      }

      const keyData = keysData[userKey];

      if (keyData.status !== "Active") {
        return Response.json({ error: "Forbidden", message: "API Key is suspended or inactive." }, { status: 403 });
      }

      if (keyData.expiry !== "LIFETIME" && keyData.expiry && new Date() > new Date(keyData.expiry)) {
        return Response.json({ error: "Forbidden", message: "API Key has expired." }, { status: 403 });
      }

      if (keyData.used >= keyData.limit) {
        return Response.json({ error: "Forbidden", message: "API Key limit exhausted." }, { status: 403 });
      }

      if (!keyData.tools.includes("all") && !keyData.tools.includes(toolName)) {
        return Response.json({ error: "Forbidden", message: "Unauthorized tool access." }, { status: 403 });
      }

      if (!TOOLS_MAP[toolName]) {
        return Response.json({ error: "Not Found", message: "Invalid tool endpoint." }, { status: 404 });
      }

      const [baseUrl, paramName] = TOOLS_MAP[toolName];
      const paramVal = url.searchParams.get(paramName) || "";

      keyData.used += 1;
      keysData[userKey] = keyData;
      if (kv) await kv.put("KEYS", JSON.stringify(keysData));

      // Log request
      let logs = kv ? JSON.parse(await kv.get("LOGS") || "[]") : [];
      logs.unshift({
        time: new Date().toISOString().replace('T', ' ').substring(0, 19),
        key: userKey,
        tool: toolName,
        query: paramVal
      });
      if (logs.length > 50) logs.pop();
      if (kv) await kv.put("LOGS", JSON.stringify(logs));

      const targetUrl = `${baseUrl}?key=${MASTER_API_KEY}&${paramName}=${encodeURIComponent(paramVal)}`;

      try {
        const apiResp = await fetch(targetUrl);
        let textData = await apiResp.text();
        textData = textData.replace(/ftgamer2/g, "SHAYAN_EXPLORER").replace(/bornex/g, "SHAYAN_EXPLORER").replace(/Ultra/g, "SHAYAN_EXPLORER");
        
        let jsonData;
        try { jsonData = JSON.parse(textData); } catch { jsonData = { response: textData }; }
        if (typeof jsonData === "object" && jsonData !== null) jsonData.developer = "SHAYAN_EXPLORER";
        return Response.json(jsonData);
      } catch (err) {
        return Response.json({ error: "Gateway Error", message: err.message, developer: "SHAYAN_EXPLORER" }, { status: 500 });
      }
    }

    // --- AUTH ---
    const cookie = request.headers.get("Cookie") || "";
    const isLoggedIn = cookie.includes("auth=shayan_verified=true");

    if (path === "/logout") {
      return new Response("Logged out", { status: 302, headers: { Location: "/login", "Set-Cookie": "auth=shayan_verified=false; Path=/;" } });
    }

    if (path === "/login" && request.method === "POST") {
      const formData = await request.formData();
      if (formData.get("username") === ADMIN_USER && formData.get("password") === ADMIN_PASS) {
        return new Response("", { status: 302, headers: { Location: "/", "Set-Cookie": "auth=shayan_verified=true; Path=/; HttpOnly" } });
      }
      return Response.redirect(`${url.origin}/login?error=1`, 302);
    }

    if (!isLoggedIn && path !== "/login") return Response.redirect(`${url.origin}/login`, 302);
    if (path === "/login") return new HtmlResponse(loginPageHtml());

    // --- ADMIN ACTIONS (PROVISION / DELETE / TOGGLE / RESET) ---
    let keysData = kv ? JSON.parse(await kv.get("KEYS") || "{}") : {
      "vx-osint": { owner: "Master Deployment", expiry: "LIFETIME", limit: 5000, used: 0, tools: ["all"], status: "Active" }
    };

    if (request.method === "POST") {
      const formData = await request.formData();
      const action = formData.get("action");

      if (action === "provision") {
        const owner = formData.get("owner") || "Client Profile";
        let customKey = formData.get("custom_key").trim();
        if (!customKey) customKey = 'vx-' + Math.random().toString(36.substring(2, 9));
        const limit = parseInt(formData.get("limit") || "2500");
        const isLifetime = formData.get("lifetime");
        let expiry = formData.get("expiry") || "LIFETIME";
        if (isLifetime === "on") expiry = "LIFETIME";
        const tools = formData.getAll("tools");

        keysData[customKey] = { owner, expiry, limit, used: 0, tools, status: "Active" };
        if (kv) await kv.put("KEYS", JSON.stringify(keysData));
      } else if (action === "delete") {
        const targetKey = formData.get("key");
        delete keysData[targetKey];
        if (kv) await kv.put("KEYS", JSON.stringify(keysData));
      } else if (action === "toggle") {
        const targetKey = formData.get("key");
        if (keysData[targetKey]) {
          keysData[targetKey].status = keysData[targetKey].status === "Active" ? "Suspended" : "Active";
          if (kv) await kv.put("KEYS", JSON.stringify(keysData));
        }
      } else if (action === "reset") {
        const targetKey = formData.get("key");
        if (keysData[targetKey]) {
          keysData[targetKey].used = 0;
          if (kv) await kv.put("KEYS", JSON.stringify(keysData));
        }
      }
      return Response.redirect(`${url.origin}/`, 302);
    }

    let logs = kv ? JSON.parse(await kv.get("LOGS") || "[]") : [];
    return new HtmlResponse(dashboardHtml(keysData, logs));
  }
};

class HtmlResponse extends Response {
  constructor(html) { super(html, { headers: { "Content-Type": "text/html;charset=UTF-8" } }); }
}

function loginPageHtml() {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Login - SHAYAN_EXPLORER</title>
  <style>
    body{background:#0a0b10;color:#e2e8f0;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
    .box{background:#111420;border:1px solid #1e2538;padding:35px;border-radius:12px;width:320px;box-shadow:0 15px 35px rgba(0,0,0,0.7);text-align:center;}
    h2{color:#00ffcc;margin-top:0;}
    input{width:100%;padding:11px;margin:10px 0;background:#06080e;border:1px solid #252f4a;color:#fff;border-radius:6px;box-sizing:border-box;}
    button{background:linear-gradient(135deg,#d946ef,#8b5cf6);color:#fff;border:none;padding:12px;width:100%;border-radius:6px;font-weight:bold;cursor:pointer;margin-top:10px;}
  </style></head>
  <body><div class="box">
    <h2>⚡ SHAYAN_EXPLORER</h2>
    <p style="font-size:12px;color:#94a3b8;">Enter credentials (vernex / vernex@16vx)</p>
    <form action="/login" method="POST">
      <input type="text" name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Authenticate</button>
    </form>
  </div></body></html>`;
}

function dashboardHtml(keys, logs) {
  let toolKeys = Object.keys(TOOLS_MAP);

  let keyRows = Object.entries(keys).map(([k, d]) => `
    <tr>
      <td style="color:#fff; font-weight:600;">${d.owner}<br><span style="font-size:11px; color:#64748b;">${k}</span></td>
      <td><code style="color:#d946ef;">${k}</code></td>
      <td><span style="color:#d946ef; font-weight:bold;">${d.expiry}</span></td>
      <td style="color:#38bdf8;">${d.used} / ${d.limit}</td>
      <td><span style="padding:2px 8px; border-radius:4px; font-size:11px; background:${d.status === 'Active' ? 'rgba(16,185,129,0.2); color:#34d399;' : 'rgba(239,68,68,0.2); color:#f87171;'}">${d.status}</span></td>
      <td><span style="font-size:11px; color:#94a3b8;">${d.tools.join(', ')}</span></td>
      <td>
        <form method="POST" style="display:inline;"><input type="hidden" name="action" value="reset"><input type="hidden" name="key" value="${k}"><button class="btn-action" style="background:#0284c7;">RESET</button></form>
        <form method="POST" style="display:inline;"><input type="hidden" name="action" value="toggle"><input type="hidden" name="key" value="${k}"><button class="btn-action" style="background:#d97706;">TOGGLE</button></form>
        <form method="POST" style="display:inline;" onsubmit="return confirm('Delete key?');"><input type="hidden" name="action" value="delete"><input type="hidden" name="key" value="${k}"><button class="btn-action" style="background:#dc2626;">DEL</button></form>
      </td>
    </tr>
  `).join('');

  let logRows = logs.length ? logs.map(l => `
    <tr>
      <td>${l.time}</td>
      <td><code>${l.key}</code></td>
      <td><span style="color:#38bdf8; font-weight:bold;">${l.tool.toUpperCase()}</span></td>
      <td><code>${l.query}</code></td>
    </tr>
  `).join('') : `<tr><td colspan="4" style="text-align:center; color:#64748b; padding:20px;">No active request stream metrics tracking currently.</td></tr>`;

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>SHAYAN_EXPLORER HUB</title>
  <style>
    body{background:#07080c;color:#cbd5e1;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:15px;}
    header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1a2234;padding-bottom:15px;margin-bottom:20px;}
    h1{color:#d946ef;font-size:16px;letter-spacing:1px;margin:0;}
    .btn-top{background:transparent;border:1px solid #2a3650;color:#94a3b8;padding:6px 12px;border-radius:6px;font-size:11px;cursor:pointer;text-decoration:none;}
    .section-title{color:#d946ef;font-size:12px;letter-spacing:1.5px;margin:25px 0 10px 0;text-transform:uppercase;font-weight:700;}
    .card{background:#0d111a;border:1px solid #1a2234;border-radius:10px;padding:20px;margin-bottom:20px;}
    .grid-2{display:grid;grid-template-columns:1fr 1fr;gap:15px;}
    .input-group{margin-bottom:12px;}
    label{display:block;font-size:11px;color:#64748b;margin-bottom:5px;text-transform:uppercase;}
    input[type="text"],input[type="number"],input[type="datetime-local"]{width:100%;padding:10px;background:#05070a;border:1px solid #1e293b;color:#fff;border-radius:6px;box-sizing:border-box;font-size:13px;}
    .tools-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;background:#05070a;padding:12px;border-radius:6px;border:1px solid #1e293b;max-height:140px;overflow-y:auto;}
    .tools-grid label{color:#cbd5e1;font-size:11px;display:flex;align-items:center;gap:6px;cursor:pointer;text-transform:none;}
    .btn-pro{background:linear-gradient(135deg,#d946ef,#8b5cf6);color:#fff;border:none;padding:12px;border-radius:6px;width:100%;font-weight:bold;cursor:pointer;margin-top:15px;box-shadow:0 4px 15px rgba(217,70,239,0.3);}
    table{width:100%;border-collapse:collapse;margin-top:5px;}
    th,td{padding:10px;text-align:left;border-bottom:1px solid #141c2e;font-size:12px;}
    th{color:#64748b;font-weight:600;text-transform:uppercase;font-size:10px;}
    code{background:#05070a;padding:2px 6px;border-radius:4px;color:#f472b6;}
    .btn-action{padding:3px 8px;border-radius:4px;font-size:10px;font-weight:bold;cursor:pointer;border:none;color:#fff;margin-right:3px;}
    @media(max-width:768px){.grid-2{grid-template-columns:1fr;}.tools-grid{grid-template-columns:repeat(2,1fr);}}
  </style></head>
  <body>
    <header>
      <h1>SHAYAN_EXPLORER HUB</h1>
      <div>
        <a href="#" class="btn-top" onclick="alert('All 20+ OSINT Endpoints operational.')">VIEW_SYSTEM_APIS</a>
        <a href="/logout" class="btn-top" style="border-color:#7f1d1d;color:#f87171;">LOGOUT</a>
      </div>
    </header>

    <!-- PROVISION KEY -->
    <div class="section-title">PROPOSE SYSTEM COMMUNICATIONS KEY</div>
    <div class="card">
      <form method="POST">
        <input type="hidden" name="action" value="provision">
        <div class="grid-2">
          <div class="input-group">
            <label>Target Owner Name</label>
            <input type="text" name="owner" placeholder="e.g. Client Profile" required>
          </div>
          <div class="input-group">
            <label>Custom Assignment String</label>
            <input type="text" name="custom_key" placeholder="Random token if empty">
          </div>
        </div>
        <div class="grid-2">
          <div class="input-group">
            <label>Daily Call Limit Volume</label>
            <input type="number" name="limit" value="2500" required>
          </div>
          <div class="input-group">
            <label>Target Expiration Lifecycle</label>
            <input type="datetime-local" name="expiry">
          </div>
        </div>
        <div class="input-group" style="display:flex; align-items:center; gap:8px;">
          <input type="checkbox" name="lifetime" style="width:auto;" checked>
          <label style="display:inline; color:#cbd5e1; margin:0;">LIFETIME ACCESS TIER</label>
        </div>
        <div class="input-group">
          <label>Route Authorization Privileges Scope</label>
          <div class="tools-grid">
            <label><input type="checkbox" name="tools" value="all" checked> ALL TOOLS</label>
            ${toolKeys.map(t => `<label><input type="checkbox" name="tools" value="${t}"> ${t.toUpperCase()}</label>`).join('')}
          </div>
        </div>
        <button type="submit" class="btn-pro">PROVISION_KEY</button>
      </form>
    </div>

    <!-- KEY REGISTRY MATRIX -->
    <div class="section-title">KEY REGISTRY MATRIX</div>
    <div class="card" style="overflow-x:auto;">
      <table>
        <tr><th>Owner Identity</th><th>Authorization Token Key</th><th>Dynamic Expiry</th><th>Usage Velocity</th><th>Status</th><th>Route Scope</th><th>System Controls</th></tr>
        ${keyRows}
      </table>
    </div>

    <!-- REQUEST LOGS -->
    <div class="section-title">INTERCEPTED REQUEST STREAMS PIPELINE LOGS</div>
    <div class="card" style="overflow-x:auto;">
      <table>
        <tr><th>Time Intercepted</th><th>Executing Key Token ID</th><th>Endpoint Route Call</th><th>Query Data Parameters Passed</th></tr>
        ${logRows}
      </table>
    </div>
  </body></html>`;
}
