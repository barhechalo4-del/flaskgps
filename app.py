import os
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request


app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
GPS_TIMEOUT_SECONDS = 60
VIDEO_TIMEOUT_SECONDS = 60
GPS_API_TOKEN = os.environ.get("GPS_API_TOKEN")


def now_ist():
    return datetime.now(IST)


def make_vehicle(lat, lon):
    return {
        "lat": lat,
        "lon": lon,
        "speed": "0",
        "last_update": "No GPS Data",
        "gps_active": False,
        "updated_at": None,
        "video_active": False,
        "video_last_update": "No Video Data",
        "video_updated_at": None,
    }


gps_live_data = {
    "v1": make_vehicle("28.6139", "77.2090"),
    "v2": make_vehicle("26.9124", "75.7873"),
    "v3": make_vehicle("19.0760", "72.8777"),
    "v4": make_vehicle("22.5726", "88.3639"),
}


def public_vehicle_data(data):
    updated_at = data.get("updated_at")
    video_updated_at = data.get("video_updated_at")
    gps_active = bool(data.get("gps_active"))
    video_active = bool(data.get("video_active"))

    if updated_at is None:
        gps_active = False
    elif (now_ist() - updated_at).total_seconds() > GPS_TIMEOUT_SECONDS:
        gps_active = False

    if video_updated_at is None:
        video_active = False
    elif (now_ist() - video_updated_at).total_seconds() > VIDEO_TIMEOUT_SECONDS:
        video_active = False

    return {
        "lat": data["lat"],
        "lon": data["lon"],
        "speed": data["speed"],
        "last_update": data["last_update"],
        "gps_active": gps_active,
        "video_active": video_active,
        "video_last_update": data["video_last_update"],
    }


def merged_payload():
    data = {}
    data.update(request.args.to_dict())

    if request.method == "POST":
        data.update(request.form.to_dict())
        data.update(request.get_json(silent=True) or {})

    return data


def first_value(data, *names):
    for name in names:
        value = data.get(name)
        if value not in (None, ""):
            return value
    return None


def token_valid(data):
    if not GPS_API_TOKEN:
        return True

    token = (
        request.headers.get("X-GPS-Token")
        or data.get("token")
        or data.get("api_token")
        or data.get("key")
    )
    return token == GPS_API_TOKEN


def parse_coordinate(value, label, low, high):
    if value in (None, ""):
        raise ValueError(f"{label} required")

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be number") from exc

    if number < low or number > high:
        raise ValueError(f"{label} must be between {low} and {high}")

    return number


def parse_speed(value):
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(speed, 0.0)


@app.route("/")
def home():
    return r"""
<!DOCTYPE html>
<html lang="en">
<head>
<title>MT GPS Dashboard</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { box-sizing:border-box; margin:0; padding:0; font-family:Arial,sans-serif; }
body { background:#f4f7fb; color:#0f172a; overflow-x:hidden; }
.layout { display:flex; min-height:100vh; }
.sidebar { width:310px; min-height:100vh; position:sticky; top:0; padding:24px 20px; background:linear-gradient(180deg,#020617,#07111f 45%,#0f172a); border-right:1px solid rgba(34,211,238,.18); box-shadow:8px 0 30px rgba(15,23,42,.25); }
.logo { display:flex; align-items:center; gap:14px; color:#22d3ee; margin-bottom:28px; padding:18px 16px; border-radius:18px; background:rgba(34,211,238,.12); border:1px solid rgba(34,211,238,.28); }
.logo-icon,.icon { display:flex; align-items:center; justify-content:center; font-weight:900; }
.logo-icon { width:52px; height:52px; border-radius:16px; background:rgba(34,211,238,.16); font-size:15px; }
.logo-text { font-size:26px; font-weight:900; letter-spacing:1px; }
.logo small { display:block; font-size:12px; color:#94a3b8; margin-top:5px; }
.menu-title { color:#64748b; font-size:12px; font-weight:bold; margin:20px 12px 12px; text-transform:uppercase; letter-spacing:1.2px; }
.menu div { display:flex; align-items:center; gap:14px; padding:17px 16px; margin-bottom:13px; border-radius:16px; cursor:pointer; background:rgba(255,255,255,.04); color:#cbd5e1; transition:.2s ease; font-size:17px; font-weight:700; border:1px solid rgba(255,255,255,.06); }
.menu div:hover,.menu div.active-menu { background:rgba(34,211,238,.14); color:#22d3ee; border-color:rgba(34,211,238,.35); }
.icon { width:38px; height:38px; border-radius:12px; background:rgba(255,255,255,.06); font-size:12px; }
.sidebar-card { margin-top:28px; padding:18px; border-radius:18px; background:rgba(34,211,238,.10); border:1px solid rgba(34,211,238,.18); }
.sidebar-card h4 { color:#e2e8f0; font-size:16px; margin-bottom:10px; }
.sidebar-card p { color:#22c55e; font-size:14px; font-weight:bold; }
.sidebar-card small { display:block; color:#94a3b8; font-size:12px; margin-top:8px; }
.main { flex:1; padding:30px; }
.page { display:none; }
.active { display:block; }
.title { font-size:38px; font-weight:bold; color:#0891b2; margin-bottom:8px; }
.subtitle { color:#64748b; margin-bottom:25px; }
.stats,.info,.tracking-info { display:grid; grid-template-columns:repeat(4,1fr); gap:18px; margin-bottom:25px; }
.stat,.card,.box,.table { background:#fff; border:1px solid #e2e8f0; box-shadow:0 8px 25px rgba(15,23,42,.08); }
.stat { padding:22px; border-radius:16px; }
.stat h3 { color:#64748b; font-size:14px; }
.stat h2 { font-size:30px; margin-top:12px; color:#0891b2; }
.grid,.camera-grid { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
.card { padding:20px; border-radius:18px; }
.card h2 { color:#0f172a; margin-bottom:12px; }
.map,.camera,.mini-map { overflow:hidden; border-radius:14px; background:#111827; }
.map { height:320px; margin-top:15px; border:1px solid #cbd5e1; background:#e5e7eb; }
.camera { height:320px; margin-top:15px; position:relative; }
.mini-map { height:230px; margin-top:12px; border:1px solid #cbd5e1; background:#e5e7eb; }
iframe,img { width:100%; height:100%; border:none; object-fit:cover; }
.rec { position:absolute; top:15px; right:15px; background:#ef4444; color:white; padding:7px 14px; border-radius:20px; font-size:13px; font-weight:bold; z-index:5; }
.info,.tracking-info { margin-top:25px; gap:15px; }
.box { padding:18px; border-radius:14px; border-left:5px solid #0891b2; }
.label { font-size:14px; color:#64748b; margin-bottom:8px; }
.value { font-size:21px; font-weight:bold; color:#0f766e; word-break:break-word; }
.table { margin-top:25px; border-radius:18px; overflow:hidden; }
table { width:100%; border-collapse:collapse; }
th,td { padding:16px; text-align:left; border-bottom:1px solid #e2e8f0; }
th { background:#f1f5f9; color:#475569; }
tr:hover,.active-row { background:#ecfeff!important; }
.live,.offline,.gps-live { padding:6px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
.live { background:#dcfce7; color:#16a34a; }
.offline { background:#fee2e2; color:#dc2626; }
.gps-live { background:#dbeafe; color:#2563eb; }
select { width:100%; padding:16px; border-radius:14px; background:#fff; color:#0f172a; border:1px solid #0891b2; margin-bottom:20px; font-size:18px; outline:none; }
.gps-help { background:#ecfeff; border:1px solid #67e8f9; border-radius:16px; padding:15px; margin-bottom:20px; color:#0f172a; font-size:14px; line-height:1.7; }
.tracking-grid { min-height:560px; }
.tracking-grid .card { display:flex; flex-direction:column; }
.tracking-grid .map,.tracking-grid .camera { flex:1; height:auto; min-height:520px; }
.vehicle-meta { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; color:#334155; font-size:14px; }
.meta-pill { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:10px; }
@media(max-width:1000px){ .sidebar{display:none;} .grid,.camera-grid,.stats,.info,.tracking-info{grid-template-columns:1fr;} .main{padding:16px;} .title{font-size:28px;} .tracking-grid .map,.tracking-grid .camera{height:420px; min-height:420px;} th,td{padding:11px; font-size:13px;} .vehicle-meta{grid-template-columns:1fr;} }
</style>
</head>
<body>
<div class="layout">
<div class="sidebar">
  <div class="logo"><div class="logo-icon">CAR</div><div><div class="logo-text">MT GPS</div><small>Vehicle Tracking System</small></div></div>
  <div class="menu-title">Main Menu</div>
  <div class="menu">
    <div class="active-menu" onclick="showPage('dashboard', this)"><span class="icon">DASH</span><span>Dashboard</span></div>
    <div onclick="showPage('tracking', this)"><span class="icon">MAP</span><span>Live Tracking</span></div>
    <div onclick="showPage('camera', this)"><span class="icon">CAM</span><span>Camera View</span></div>
    <div onclick="showPage('vehicles', this)"><span class="icon">CAR</span><span>Vehicles</span></div>
  </div>
  <div class="sidebar-card"><h4>System Status</h4><p id="sidebarStatus">&bull; Loading...</p><small>4 Camera + 4 GPS System</small></div>
</div>

<div class="main">
<div id="dashboard" class="page active">
  <div class="title">LIVE VEHICLE DASHBOARD</div>
  <div class="subtitle">GPS based vehicle tracking dashboard</div>
  <div class="stats">
    <div class="stat"><h3>Total Vehicles</h3><h2>4</h2></div>
    <div class="stat"><h3>Video Active</h3><h2 id="activeCount">0</h2></div>
    <div class="stat"><h3>GPS Live</h3><h2 id="gpsLiveCount">0</h2></div>
    <div class="stat"><h3>Selected Speed</h3><h2 id="selectedSpeed">--</h2></div>
  </div>
  <div class="grid">
    <div class="card"><h2>MAP - Selected Vehicle GPS Tracking</h2><div class="map"><iframe id="dashboardMap" src="https://maps.google.com/maps?q=28.6139,77.2090&z=13&output=embed"></iframe></div></div>
    <div class="card"><h2>CAMERA - Selected Vehicle Camera</h2><div class="camera" id="dashboardCamera"></div></div>
  </div>
  <div class="info">
    <div class="box"><div class="label">Driver Name</div><div class="value" id="topDriver">--</div></div>
    <div class="box"><div class="label">Number Plate</div><div class="value" id="topPlate">--</div></div>
    <div class="box"><div class="label">Speed</div><div class="value" id="topSpeed">--</div></div>
    <div class="box"><div class="label">GPS Last Update</div><div class="value" id="topStatus">--</div></div>
  </div>
  <div class="table"><table>
    <tr><th>Vehicle</th><th>Driver</th><th>Plate</th><th>Location</th><th>Speed</th><th>Video</th><th>GPS</th></tr>
    <tr id="dashRow-v1" onclick="selectVehicle('v1')" style="cursor:pointer;"><td>Vehicle 1</td><td>DRIVER 1</td><td>1234</td><td id="dashLocation-v1">Delhi</td><td id="dashSpeed-v1">0 km/h</td><td id="dashStatus-v1"></td><td id="dashGps-v1"></td></tr>
    <tr id="dashRow-v2" onclick="selectVehicle('v2')" style="cursor:pointer;"><td>Vehicle 2</td><td>DRIVER 2</td><td>5678</td><td id="dashLocation-v2">Jaipur</td><td id="dashSpeed-v2">0 km/h</td><td id="dashStatus-v2"></td><td id="dashGps-v2"></td></tr>
    <tr id="dashRow-v3" onclick="selectVehicle('v3')" style="cursor:pointer;"><td>Vehicle 3</td><td>DRIVER 3</td><td>9012</td><td id="dashLocation-v3">Mumbai</td><td id="dashSpeed-v3">0 km/h</td><td id="dashStatus-v3"></td><td id="dashGps-v3"></td></tr>
    <tr id="dashRow-v4" onclick="selectVehicle('v4')" style="cursor:pointer;"><td>Vehicle 4</td><td>DRIVER 4</td><td>3456</td><td id="dashLocation-v4">Kolkata</td><td id="dashSpeed-v4">0 km/h</td><td id="dashStatus-v4"></td><td id="dashGps-v4"></td></tr>
  </table></div>
</div>

<div id="tracking" class="page">
  <div class="title">LIVE TRACKING</div>
  <div class="subtitle">Dropdown me active vehicles dikhenge. GPS Logger se map update hoga.</div>
  <div class="gps-help">
    <b>GPS Logger URL Format:</b><br>
    Vehicle 1: /gps?id=v1&amp;lat=%LAT&amp;lon=%LON&amp;speed=%SPD<br>
    Vehicle 2: /gps?id=v2&amp;lat=%LAT&amp;lon=%LON&amp;speed=%SPD<br>
    Vehicle 3: /gps?id=v3&amp;lat=%LAT&amp;lon=%LON&amp;speed=%SPD<br>
    Vehicle 4: /gps?id=v4&amp;lat=%LAT&amp;lon=%LON&amp;speed=%SPD<br>
    Video active heartbeat: /video?id=v1<br>
    Token enabled ho to URL me &amp;token=YOUR_TOKEN add karein ya X-GPS-Token header bhejein.
  </div>
  <select id="vehicleSelect" onchange="changeVehicle()"></select>
  <div class="tracking-info">
    <div class="box"><div class="label">Driver</div><div class="value" id="trackDriver">--</div></div>
    <div class="box"><div class="label">Number Plate</div><div class="value" id="trackPlate">--</div></div>
    <div class="box"><div class="label">Location</div><div class="value" id="trackLocation">--</div></div>
    <div class="box"><div class="label">GPS Status</div><div class="value" id="trackStatus">--</div></div>
  </div>
  <div class="grid tracking-grid">
    <div class="card"><h2>MAP - Vehicle Live Map</h2><div class="map"><iframe id="mapFrame" src="https://maps.google.com/maps?q=28.6139,77.2090&z=15&output=embed"></iframe></div></div>
    <div class="card"><h2>CAMERA - Vehicle Live Camera</h2><div class="camera" id="trackingCamera"></div></div>
  </div>
</div>

<div id="camera" class="page">
  <div class="title">LIVE CAMERA VIEW</div>
  <div class="subtitle">4 vehicles ke camera aur GPS location yaha show honge.</div>
  <div class="camera-grid" id="cameraGrid"></div>
</div>

<div id="vehicles" class="page">
  <div class="title">LIVE VEHICLES</div>
  <div class="subtitle">4 vehicles active hain.</div>
  <div class="table"><table>
    <tr><th>Vehicle</th><th>Driver</th><th>Plate</th><th>Location</th><th>GPS Update</th><th>Video</th><th>GPS</th></tr>
    <tr id="vehicleRow-v1"><td>Vehicle 1</td><td>DRIVER 1</td><td>1234</td><td id="vehicleLocation-v1">Delhi</td><td id="gpsUpdate-v1">No GPS Data</td><td id="vehicleStatus-v1"></td><td id="vehicleGps-v1"></td></tr>
    <tr id="vehicleRow-v2"><td>Vehicle 2</td><td>DRIVER 2</td><td>5678</td><td id="vehicleLocation-v2">Jaipur</td><td id="gpsUpdate-v2">No GPS Data</td><td id="vehicleStatus-v2"></td><td id="vehicleGps-v2"></td></tr>
    <tr id="vehicleRow-v3"><td>Vehicle 3</td><td>DRIVER 3</td><td>9012</td><td id="vehicleLocation-v3">Mumbai</td><td id="gpsUpdate-v3">No GPS Data</td><td id="vehicleStatus-v3"></td><td id="vehicleGps-v3"></td></tr>
    <tr id="vehicleRow-v4"><td>Vehicle 4</td><td>DRIVER 4</td><td>3456</td><td id="vehicleLocation-v4">Kolkata</td><td id="gpsUpdate-v4">No GPS Data</td><td id="vehicleStatus-v4"></td><td id="vehicleGps-v4"></td></tr>
  </table></div>
</div>
</div>
</div>

<script>
let activeVehicle = null;
let dashboardCameraVehicle = null;
let trackingCameraVehicle = null;

let vehicles = {
  v1: { name:"Vehicle 1", lat:"28.6139", lon:"77.2090", driver:"DRIVER 1", plate:"1234", location:"Delhi", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraId:"car1" },
  v2: { name:"Vehicle 2", lat:"26.9124", lon:"75.7873", driver:"DRIVER 2", plate:"5678", location:"Jaipur", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraId:"car2" },
  v3: { name:"Vehicle 3", lat:"19.0760", lon:"72.8777", driver:"DRIVER 3", plate:"9012", location:"Mumbai", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraId:"car3" },
  v4: { name:"Vehicle 4", lat:"22.5726", lon:"88.3639", driver:"DRIVER 4", plate:"3456", location:"Kolkata", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraId:"car4" }
};

function showPage(pageId, menuItem){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.getElementById(pageId).classList.add('active');
  document.querySelectorAll('.menu div').forEach(i=>i.classList.remove('active-menu'));
  menuItem.classList.add('active-menu');
  if(pageId === 'camera') loadCameraViewOnlyActive();
}
function activeBadge(){ return `<span class="live">Video Active</span>`; }
function offlineBadge(){ return `<span class="offline">Video Offline</span>`; }
function gpsLiveBadge(){ return `<span class="gps-live">GPS Live</span>`; }
function waitingBadge(){ return `<span class="offline">Waiting GPS</span>`; }
function cameraHtml(id){
  let cam = vehicles[id].cameraId;
  return `<iframe src="https://vdo.ninja/?view=${cam}&cleanoutput&transparent" allow="camera; microphone; autoplay; fullscreen" allowfullscreen></iframe><div class="rec">&bull; REC</div>`;
}
function mapSrc(v, zoom=15){ return `https://maps.google.com/maps?q=${v.lat},${v.lon}&z=${zoom}&output=embed`; }
function getActiveVehicleIds(){ return Object.keys(vehicles).filter(id=>vehicles[id].videoActive === true); }

function loadActiveVehiclesDropdown(){
  let select = document.getElementById('vehicleSelect');
  let currentValue = select.value;
  select.innerHTML = '';
  let activeIds = getActiveVehicleIds();
  if(activeIds.length === 0){
    let opt = document.createElement('option');
    opt.value = '';
    opt.text = 'No video active vehicle';
    select.appendChild(opt);
    return;
  }
  activeIds.forEach(id=>{
    let v = vehicles[id];
    let opt = document.createElement('option');
    opt.value = id;
    opt.text = `${v.name} - ${v.plate} - ${v.location}`;
    select.appendChild(opt);
  });
  if(currentValue && vehicles[currentValue]) select.value = currentValue;
}

function updateRowsVisibility(){
  let activeIds = getActiveVehicleIds();
  let gpsCount = 0;
  for(let id in vehicles){
    let v = vehicles[id];
    let videoActive = v.videoActive === true;
    if(v.gpsActive) gpsCount++;
    ['dashRow-', 'vehicleRow-'].forEach(prefix=>{
      let row = document.getElementById(prefix + id);
      if(row){ row.style.display = 'table-row'; row.classList.toggle('active-row', id === activeVehicle); }
    });
    let ds = document.getElementById('dashStatus-' + id); if(ds) ds.innerHTML = videoActive ? activeBadge() : offlineBadge();
    let vs = document.getElementById('vehicleStatus-' + id); if(vs) vs.innerHTML = videoActive ? activeBadge() : offlineBadge();
    let dg = document.getElementById('dashGps-' + id); if(dg) dg.innerHTML = v.gpsActive ? gpsLiveBadge() : waitingBadge();
    let vg = document.getElementById('vehicleGps-' + id); if(vg) vg.innerHTML = v.gpsActive ? gpsLiveBadge() : waitingBadge();
  }
  document.getElementById('activeCount').innerHTML = activeIds.length;
  document.getElementById('gpsLiveCount').innerHTML = gpsCount;
}

function loadCameraViewOnlyActive(){
  let grid = document.getElementById('cameraGrid');
  grid.innerHTML = '';
  let activeIds = getActiveVehicleIds();
  if(activeIds.length === 0){
    grid.innerHTML = `<div class="card"><h2>No Video Active</h2><p>Abhi kisi vehicle ka camera active nahi hai.</p></div>`;
    return;
  }
  activeIds.forEach(id=>{
    let v = vehicles[id];
    let card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h2>CAR - ${v.name} - ${v.plate}</h2>
      <div class="camera">${cameraHtml(id)}</div>
      <div class="vehicle-meta">
        <div class="meta-pill"><b>Driver:</b> ${v.driver}</div>
        <div class="meta-pill"><b>Speed:</b> ${v.speed}</div>
        <div class="meta-pill"><b>GPS:</b> ${v.gpsActive ? 'Live' : 'Waiting GPS'}</div>
        <div class="meta-pill"><b>Update:</b> ${v.lastUpdate}</div>
      </div>
      <div class="mini-map"><iframe src="${mapSrc(v, 15)}"></iframe></div>
    `;
    grid.appendChild(card);
  });
}

function updateMapForVehicle(id){
  let v = vehicles[id];
  document.getElementById('dashboardMap').src = mapSrc(v, 15);
  document.getElementById('mapFrame').src = mapSrc(v, 15);
}

function updateCameraIfNeeded(id){
  if(dashboardCameraVehicle !== id){
    document.getElementById('dashboardCamera').innerHTML = cameraHtml(id);
    dashboardCameraVehicle = id;
  }
  if(trackingCameraVehicle !== id){
    document.getElementById('trackingCamera').innerHTML = cameraHtml(id);
    trackingCameraVehicle = id;
  }
}

function selectVehicle(id){
  let v = vehicles[id];
  if(!v || v.videoActive !== true) {
    showNoActiveVideo();
    return;
  }
  activeVehicle = id;
  let sel = document.getElementById('vehicleSelect'); if(sel) sel.value = id;
  updateMapForVehicle(id);
  updateCameraIfNeeded(id);
  document.getElementById('topDriver').innerHTML = v.driver;
  document.getElementById('topPlate').innerHTML = v.plate;
  document.getElementById('topSpeed').innerHTML = v.speed;
  document.getElementById('topStatus').innerHTML = v.gpsActive ? v.lastUpdate : 'Waiting GPS';
  document.getElementById('trackDriver').innerHTML = v.driver;
  document.getElementById('trackPlate').innerHTML = v.plate;
  document.getElementById('trackLocation').innerHTML = v.location;
  document.getElementById('trackStatus').innerHTML = v.gpsActive ? 'GPS Live' : 'Waiting GPS';
  document.getElementById('selectedSpeed').innerHTML = v.speed;
  document.getElementById('sidebarStatus').innerHTML = '&bull; ' + v.name + ' Video Active';
  updateRowsVisibility();
}
function changeVehicle(){ selectVehicle(document.getElementById('vehicleSelect').value); }

function showNoActiveVideo(){
  activeVehicle = null;
  dashboardCameraVehicle = null;
  trackingCameraVehicle = null;
  document.getElementById('dashboardCamera').innerHTML = '<div style="color:white;display:flex;align-items:center;justify-content:center;height:100%;font-weight:bold;">NO VIDEO ACTIVE</div>';
  document.getElementById('trackingCamera').innerHTML = '<div style="color:white;display:flex;align-items:center;justify-content:center;height:100%;font-weight:bold;">NO VIDEO ACTIVE</div>';
  document.getElementById('topDriver').innerHTML = '--';
  document.getElementById('topPlate').innerHTML = '--';
  document.getElementById('topSpeed').innerHTML = '--';
  document.getElementById('topStatus').innerHTML = 'No Video Active';
  document.getElementById('trackDriver').innerHTML = '--';
  document.getElementById('trackPlate').innerHTML = '--';
  document.getElementById('trackLocation').innerHTML = '--';
  document.getElementById('trackStatus').innerHTML = 'No Video Active';
  document.getElementById('selectedSpeed').innerHTML = '--';
  document.getElementById('sidebarStatus').innerHTML = '&bull; No Video Active';
  updateRowsVisibility();
}

function updateVehicleTextFields(){
  for(let id in vehicles){
    let v = vehicles[id];
    let fields = {
      ['dashSpeed-' + id]: v.speed,
      ['dashLocation-' + id]: v.location,
      ['vehicleLocation-' + id]: v.location,
      ['gpsUpdate-' + id]: v.lastUpdate
    };
    for(let k in fields){ let el = document.getElementById(k); if(el) el.innerHTML = fields[k]; }
  }
}

async function fetchGPSLoggerData(){
  try{
    let res = await fetch('/gps-data?ts=' + Date.now());
    let data = await res.json();
    for(let id in data){
      if(vehicles[id]){
        vehicles[id].lat = data[id].lat;
        vehicles[id].lon = data[id].lon;
        vehicles[id].speed = data[id].speed + ' km/h';
        vehicles[id].lastUpdate = data[id].last_update;
        vehicles[id].gpsActive = data[id].gps_active;
        vehicles[id].videoActive = data[id].video_active;
        if(data[id].gps_active === true) vehicles[id].location = data[id].lat + ', ' + data[id].lon;
      }
    }
    loadActiveVehiclesDropdown();
    updateVehicleTextFields();
    updateRowsVisibility();
    let activeIds = getActiveVehicleIds();
    if(activeVehicle) selectVehicle(activeVehicle);
    else if(activeIds.length > 0) selectVehicle(activeIds[0]);
    else showNoActiveVideo();
    loadCameraViewOnlyActive();
  }catch(e){ console.log('GPS fetch error:', e); }
}

function initDashboard(){
  loadActiveVehiclesDropdown();
  updateRowsVisibility();
  let ids = getActiveVehicleIds();
  if(ids.length > 0) selectVehicle(ids[0]);
  else showNoActiveVideo();
  fetchGPSLoggerData();
  setInterval(fetchGPSLoggerData, 5000);
}
initDashboard();
</script>
</body>
</html>
"""


@app.route("/gps", methods=["GET", "POST"])
@app.route("/gpslogger", methods=["GET", "POST"])
@app.route("/log", methods=["GET", "POST"])
def receive_gps_logger():
    data = merged_payload()

    if not token_valid(data):
        return jsonify({"status": "error", "message": "Invalid or missing GPS token"}), 401

    vehicle_id = first_value(data, "id") or "v1"
    lat = first_value(data, "lat", "latitude", "LAT", "Latitude")
    lon = first_value(data, "lon", "lng", "longitude", "LON", "Longitude")
    speed = first_value(data, "speed", "spd", "SPD", "Speed") or "0"

    if vehicle_id not in gps_live_data:
        return jsonify({"status": "error", "message": "Invalid vehicle id. Use v1, v2, v3, v4"}), 400

    try:
        lat_float = parse_coordinate(lat, "lat", -90, 90)
        lon_float = parse_coordinate(lon, "lon", -180, 180)
    except ValueError as exc:
        return jsonify({
            "status": "error",
            "message": str(exc),
            "example": "/gps?id=v1&lat=28.6200&lon=77.2300&speed=45",
        }), 400

    speed_float = parse_speed(speed)
    current_time = now_ist()

    vehicle = gps_live_data[vehicle_id]
    vehicle.update({
        "lat": str(lat_float),
        "lon": str(lon_float),
        "speed": str(speed_float),
        "last_update": current_time.strftime("%d-%m-%Y %I:%M:%S %p"),
        "gps_active": True,
        "updated_at": current_time,
    })

    return jsonify({
        "status": "success",
        "message": "GPS Logger data received",
        "vehicle_id": vehicle_id,
        "data": public_vehicle_data(vehicle),
    })


@app.route("/video", methods=["GET", "POST"])
@app.route("/camera", methods=["GET", "POST"])
@app.route("/video-active", methods=["GET", "POST"])
def receive_video_heartbeat():
    data = merged_payload()

    if not token_valid(data):
        return jsonify({"status": "error", "message": "Invalid or missing GPS token"}), 401

    vehicle_id = first_value(data, "id") or "v1"
    if vehicle_id not in gps_live_data:
        return jsonify({"status": "error", "message": "Invalid vehicle id. Use v1, v2, v3, v4"}), 400

    current_time = now_ist()
    vehicle = gps_live_data[vehicle_id]
    vehicle.update({
        "video_active": True,
        "video_last_update": current_time.strftime("%d-%m-%Y %I:%M:%S %p"),
        "video_updated_at": current_time,
    })

    return jsonify({
        "status": "success",
        "message": "Video heartbeat received",
        "vehicle_id": vehicle_id,
        "data": public_vehicle_data(vehicle),
    })


@app.route("/gps-data")
def gps_data_api():
    return jsonify({
        vehicle_id: public_vehicle_data(data)
        for vehicle_id, data in gps_live_data.items()
    })


@app.route("/gps-test")
def gps_test_page():
    token_hint = "&token=YOUR_TOKEN" if GPS_API_TOKEN else ""
    return f"""
    <h2>GPS Logger Test</h2>
    <p>Click test links:</p>
    <a href="/gps?id=v1&lat=28.6200&lon=77.2300&speed=45{token_hint}">Update Vehicle 1 Test</a><br><br>
    <a href="/gps?id=v2&lat=26.9220&lon=75.8000&speed=55{token_hint}">Update Vehicle 2 Test</a><br><br>
    <a href="/gps?id=v3&lat=19.0900&lon=72.8800&speed=60{token_hint}">Update Vehicle 3 Test</a><br><br>
    <a href="/gps?id=v4&lat=22.5800&lon=88.3700&speed=50{token_hint}">Update Vehicle 4 Test</a><br><br>
    <p>Video active test links:</p>
    <a href="/video?id=v1{token_hint}">Vehicle 1 Video Active</a><br><br>
    <a href="/video?id=v2{token_hint}">Vehicle 2 Video Active</a><br><br>
    <a href="/video?id=v3{token_hint}">Vehicle 3 Video Active</a><br><br>
    <a href="/video?id=v4{token_hint}">Vehicle 4 Video Active</a><br><br>
    <p>After click, go back to dashboard.</p>
    <a href="/">Open Dashboard</a>
    """


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
