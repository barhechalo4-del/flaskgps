import os
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request


app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
GPS_TIMEOUT_SECONDS = 60
VIDEO_TIMEOUT_SECONDS = 60
GPS_API_TOKEN = os.environ.get("GPS_API_TOKEN")
CAMERA_IDS = {
    "v1": "9100000001",
    "v2": "9100000002",
    "v3": "9100000003",
    "v4": "9100000004",
}
camera_enabled = {vehicle_id: True for vehicle_id in CAMERA_IDS}


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
        "accuracy": None,
    }


gps_live_data = {
    "v1": make_vehicle("28.6139", "77.2090"),
    "v2": make_vehicle("26.9124", "75.7873"),
    "v3": make_vehicle("19.0760", "72.8777"),
    "v4": make_vehicle("22.5726", "88.3639"),
}


def public_vehicle_data(data, vehicle_id=None):
    updated_at = data.get("updated_at")
    video_updated_at = data.get("video_updated_at")
    gps_active = bool(data.get("gps_active"))
    camera_on = bool(camera_enabled.get(vehicle_id, True))
    video_active = bool(data.get("video_active")) and camera_on

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
        "camera_on": camera_on,
        "video_last_update": data["video_last_update"],
        "accuracy": data.get("accuracy"),
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


def parse_speed(value, unit=None):
    try:
        speed = float(value)
    except (TypeError, ValueError):
        return 0.0

    speed = max(speed, 0.0)
    unit = (unit or "mps").strip().lower()

    if unit in ("kmh", "kph", "km/h", "kmph"):
        speed_kmh = speed
    elif unit in ("mph", "mi/h"):
        speed_kmh = speed * 1.609344
    elif unit in ("kn", "knot", "knots"):
        speed_kmh = speed * 1.852
    else:
        speed_kmh = speed * 3.6

    return round(speed_kmh, 1)


def parse_accuracy(value):
    if value in (None, ""):
        return None

    try:
        accuracy = float(value)
    except (TypeError, ValueError):
        return None

    if accuracy < 0:
        return None

    return round(accuracy, 1)


@app.route("/")
def home():
    return r"""
<!DOCTYPE html>
<html lang="en">
<head>
<title>MT GPS Dashboard</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="preconnect" href="https://vdo.ninja">
<link rel="dns-prefetch" href="https://vdo.ninja">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
* { box-sizing:border-box; margin:0; padding:0; font-family:Inter,Segoe UI,Arial,sans-serif; }
:root {
  --ink:#0f172a;
  --muted:#64748b;
  --line:#dbe3ee;
  --panel:#ffffff;
  --canvas:#eef3f8;
  --nav:#07111f;
  --nav-2:#0b1628;
  --accent:#0891b2;
  --accent-2:#0f766e;
  --good:#16a34a;
  --bad:#dc2626;
}
body { background:var(--canvas); color:var(--ink); overflow-x:hidden; }
.layout { display:flex; min-height:100vh; background:linear-gradient(180deg,#f8fbff 0%,#eef3f8 100%); }
.sidebar { width:296px; min-height:100vh; position:sticky; top:0; padding:22px 14px; background:linear-gradient(180deg,var(--nav),#0c1729 62%,#101827); border-right:1px solid rgba(148,163,184,.18); box-shadow:10px 0 28px rgba(15,23,42,.18); }
.logo { display:flex; align-items:center; gap:12px; color:#e0faff; margin-bottom:24px; padding:15px; border-radius:8px; background:linear-gradient(135deg,rgba(8,145,178,.22),rgba(15,118,110,.10)); border:1px solid rgba(103,232,249,.24); }
.logo-icon,.icon { display:flex; align-items:center; justify-content:center; font-weight:900; }
.logo-icon { width:44px; height:44px; border-radius:8px; background:#073749; color:#67e8f9; font-size:12px; }
.logo-text { font-size:22px; font-weight:900; letter-spacing:.5px; }
.logo small { display:block; font-size:11px; color:#94a3b8; margin-top:3px; }
.menu-title { color:#718096; font-size:11px; font-weight:900; margin:18px 8px 10px; text-transform:uppercase; letter-spacing:.9px; }
.menu div { display:flex; align-items:center; gap:11px; min-height:48px; padding:10px 12px; margin-bottom:8px; border-radius:8px; cursor:pointer; background:transparent; color:#cbd5e1; transition:.18s ease; font-size:14px; font-weight:800; border:1px solid transparent; }
.menu div:hover { background:rgba(255,255,255,.06); color:#ffffff; border-color:rgba(148,163,184,.14); }
.menu div.active-menu { background:#083344; color:#67e8f9; border-color:rgba(34,211,238,.32); box-shadow:inset 3px 0 0 #22d3ee; }
.icon { width:30px; height:30px; border-radius:8px; background:rgba(148,163,184,.14); font-size:10px; color:#dbeafe; }
.sidebar-card { margin-top:20px; padding:14px; border-radius:8px; background:#082f3d; border:1px solid rgba(34,211,238,.26); }
.sidebar-card h4 { color:#f8fafc; font-size:13px; margin-bottom:9px; }
.sidebar-card p { color:#22c55e; font-size:13px; font-weight:900; }
.sidebar-card small { display:block; color:#a6b3c4; font-size:11px; margin-top:8px; }
.main { flex:1; min-width:0; padding:24px 28px 34px; }
.page { display:none; }
.active { display:block; }
.title { font-size:30px; line-height:1.1; font-weight:900; color:var(--ink); margin-bottom:7px; letter-spacing:0; }
.subtitle { color:var(--muted); margin-bottom:18px; font-size:14px; font-weight:600; }
.stats,.info,.tracking-info { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-bottom:18px; }
.stat,.card,.box,.table { background:rgba(255,255,255,.92); border:1px solid var(--line); box-shadow:0 10px 28px rgba(15,23,42,.07); }
.stat { padding:16px; border-radius:8px; position:relative; overflow:hidden; }
.stat::before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:linear-gradient(180deg,var(--accent),var(--accent-2)); }
.stat h3 { color:#475569; font-size:12px; font-weight:800; }
.stat h2 { font-size:26px; line-height:1; margin-top:10px; color:var(--accent); font-weight:900; }
.grid,.camera-grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:14px; }
.card { padding:14px; border-radius:8px; }
.card h2 { color:var(--ink); margin-bottom:10px; font-size:17px; line-height:1.2; font-weight:900; }
.panel-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px; }
.panel-head h2 { margin-bottom:0; }
.fullscreen-btn { width:38px; height:38px; border:1px solid #cbd5e1; border-radius:8px; background:#ffffff; color:#0f172a; cursor:pointer; display:flex; align-items:center; justify-content:center; font-size:18px; font-weight:900; box-shadow:0 6px 14px rgba(15,23,42,.08); transition:.18s ease; }
.fullscreen-btn:hover { border-color:var(--accent); color:var(--accent); transform:translateY(-1px); }
.fullscreen-btn:focus { outline:3px solid rgba(8,145,178,.2); outline-offset:2px; }
.fullscreen-target:fullscreen { background:#0f172a; padding:14px; display:flex; flex-direction:column; width:100vw; height:100vh; border-radius:0; }
.fullscreen-target:fullscreen .map,.fullscreen-target:fullscreen .camera { flex:1; height:auto; min-height:0; margin-top:0; }
.fullscreen-target:fullscreen .panel-head { color:#ffffff; }
.fullscreen-target:fullscreen .panel-head h2 { color:#ffffff; }
.fullscreen-target:fullscreen .fullscreen-btn { border-color:rgba(255,255,255,.25); background:rgba(255,255,255,.12); color:#ffffff; }
.map,.camera { overflow:hidden; border-radius:8px; background:#111827; }
.map { height:330px; margin-top:10px; border:1px solid #b8c7d9; background:#dbeafe; position:relative; box-shadow:inset 0 0 0 1px rgba(255,255,255,.65), inset 0 -30px 60px rgba(15,23,42,.08); }
.camera { height:330px; margin-top:10px; position:relative; }
iframe,img { width:100%; height:100%; border:none; object-fit:cover; }
.map .leaflet-container { width:100%; height:100%; font:12px/1.4 Inter,Segoe UI,Arial,sans-serif; }
.map .leaflet-tile-pane { filter:saturate(1.12) contrast(1.03); }
.map .leaflet-control-zoom a { color:#0f172a; border-color:#cbd5e1; font-weight:900; }
.map .leaflet-control-attribution { background:rgba(255,255,255,.78); color:#475569; font-weight:700; backdrop-filter:blur(8px); }
.car-marker {
  width:74px;
  height:74px;
  border-radius:50%;
  background:radial-gradient(circle at 35% 28%,#ffffff 0 20%,#ecfeff 42%,rgba(14,116,144,.92) 72%,rgba(2,6,23,.92) 100%);
  display:flex;
  align-items:center;
  justify-content:center;
  border:3px solid #0891b2;
  box-shadow:0 0 0 0 rgba(8,145,178,.75), 0 18px 30px rgba(15,23,42,.42);
  position:relative;
  transform-style:preserve-3d;
  animation:carBlink 1s infinite;
}
.car-marker::before {
  content:"";
  position:absolute;
  inset:-10px;
  border-radius:50%;
  background:conic-gradient(from 160deg,rgba(34,211,238,.0),rgba(34,211,238,.42),rgba(34,211,238,.0) 62%);
  z-index:-1;
  animation:radarSpin 2.4s linear infinite;
}
.car-marker::after {
  content:"";
  position:absolute;
  left:50%;
  bottom:-15px;
  width:42px;
  height:14px;
  border-radius:50%;
  background:rgba(2,6,23,.38);
  filter:blur(3px);
  transform:translateX(-50%);
  z-index:-2;
}
.car-logo {
  width:58px;
  height:58px;
  display:block;
  filter:drop-shadow(0 8px 8px rgba(2,6,23,.42));
}
.car-label {
  position:absolute;
  left:50%;
  bottom:-17px;
  transform:translateX(-50%);
  background:#020617;
  color:#ffffff;
  border:2px solid #ffffff;
  border-radius:999px;
  padding:3px 9px;
  font-size:9px;
  font-weight:900;
  letter-spacing:.6px;
  line-height:1;
  box-shadow:0 7px 16px rgba(15,23,42,.25);
}
.car-heading {
  position:absolute;
  top:-16px;
  left:50%;
  width:0;
  height:0;
  border-left:8px solid transparent;
  border-right:8px solid transparent;
  border-bottom:14px solid #22d3ee;
  filter:drop-shadow(0 4px 5px rgba(8,145,178,.4));
  transform:translateX(-50%);
}
@keyframes carBlink {
  0% { transform:scale(.96) rotateX(12deg); box-shadow:0 0 0 0 rgba(8,145,178,.75), 0 18px 30px rgba(15,23,42,.42); }
  70% { transform:scale(1.06) rotateX(12deg); box-shadow:0 0 0 20px rgba(8,145,178,0), 0 18px 30px rgba(15,23,42,.42); }
  100% { transform:scale(.96) rotateX(12deg); box-shadow:0 0 0 0 rgba(8,145,178,0), 0 18px 30px rgba(15,23,42,.42); }
}
@keyframes radarSpin {
  to { transform:rotate(360deg); }
}
.rec { position:absolute; top:12px; right:12px; background:#ef4444; color:white; padding:6px 11px; border-radius:999px; font-size:12px; font-weight:900; z-index:5; }
.info,.tracking-info { margin-top:18px; gap:12px; }
.box { padding:14px; border-radius:8px; border-left:4px solid var(--accent); }
.label { font-size:12px; color:var(--muted); margin-bottom:7px; font-weight:700; }
.value { font-size:18px; font-weight:900; color:var(--accent-2); word-break:break-word; }
.table { margin-top:18px; border-radius:8px; overflow:auto; }
table { width:100%; border-collapse:collapse; }
th,td { padding:12px; text-align:left; border-bottom:1px solid #e2e8f0; font-size:13px; white-space:nowrap; }
th { background:#f8fafc; color:#475569; font-weight:900; position:sticky; top:0; z-index:1; }
td { color:#1e293b; font-weight:600; }
tr:hover { background:#f8fafc!important; }
.active-row { background:#ecfeff!important; box-shadow:inset 3px 0 0 var(--accent); }
.live,.offline,.gps-live { padding:5px 10px; border-radius:999px; font-size:12px; font-weight:900; display:inline-block; }
.live { background:#dcfce7; color:#16a34a; }
.offline { background:#fee2e2; color:#dc2626; }
.gps-live { background:#dbeafe; color:#2563eb; }
.camera-actions { display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.camera-toggle { border:0; border-radius:999px; padding:7px 12px; font-size:12px; font-weight:900; cursor:pointer; color:#ffffff; box-shadow:0 8px 16px rgba(15,23,42,.12); transition:.18s ease; }
.camera-toggle.on { background:#16a34a; }
.camera-toggle.off { background:#dc2626; }
.camera-toggle:hover { transform:translateY(-1px); filter:brightness(1.04); }
.camera-toggle:disabled { cursor:wait; opacity:.72; transform:none; }
.vehicle-legend { display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 18px; color:#334155; font-size:12px; font-weight:900; }
.legend-item { display:flex; align-items:center; gap:7px; background:#fff; border:1px solid #e2e8f0; border-radius:999px; padding:6px 10px; box-shadow:0 4px 12px rgba(15,23,42,.05); }
.legend-dot { width:13px; height:13px; border-radius:50%; display:inline-block; }
select { width:100%; padding:13px 14px; border-radius:8px; background:#fff; color:var(--ink); border:1px solid #94a3b8; margin-bottom:16px; font-size:15px; font-weight:700; outline:none; box-shadow:0 5px 14px rgba(15,23,42,.04); }
select:focus { border-color:var(--accent); box-shadow:0 0 0 4px rgba(8,145,178,.12); }
.gps-help { background:#f0fdfa; border:1px solid #99f6e4; border-radius:8px; padding:13px; margin-bottom:16px; color:#134e4a; font-size:13px; line-height:1.65; font-weight:600; }
.tracking-grid { min-height:560px; }
.tracking-grid .card { display:flex; flex-direction:column; }
.tracking-grid .map,.tracking-grid .camera { flex:1; height:auto; min-height:520px; }
.vehicle-meta { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; color:#334155; font-size:14px; }
.meta-pill { background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:10px; font-weight:700; }
.camera-grid .card { display:flex; flex-direction:column; gap:10px; }
.camera-grid .card h2 { margin-bottom:0; }
.camera-grid .camera { height:300px; margin-top:0; }
.camera-title-row { display:flex; justify-content:space-between; gap:10px; align-items:flex-start; }
.camera-title-row small { display:block; color:var(--muted); font-size:12px; margin-top:3px; }
.camera-offline { height:100%; color:#e2e8f0; display:flex; align-items:center; justify-content:center; font-weight:900; letter-spacing:.4px; }
@media(max-width:1000px){ .layout{display:block;} .sidebar{display:none;} .grid,.camera-grid,.stats,.info,.tracking-info{grid-template-columns:1fr;} .main{padding:16px;} .title{font-size:26px;} .map,.camera{height:360px;} .tracking-grid .map,.tracking-grid .camera{height:420px; min-height:420px;} th,td{padding:10px; font-size:12px;} .vehicle-meta{grid-template-columns:1fr;} }
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
    <div class="card fullscreen-target" id="dashboardMapPanel"><div class="panel-head"><h2>MAP - Selected Vehicle GPS Tracking</h2><button class="fullscreen-btn" type="button" onclick="toggleFullscreen('dashboardMapPanel')" title="Full screen map" aria-label="Full screen map">⛶</button></div><div class="map" id="dashboardMap"></div></div>
    <div class="card fullscreen-target" id="dashboardCameraPanel"><div class="panel-head"><h2>CAMERA - Selected Vehicle Camera</h2><button class="fullscreen-btn" type="button" onclick="toggleFullscreen('dashboardCameraPanel')" title="Full screen camera" aria-label="Full screen camera">⛶</button></div><div class="camera" id="dashboardCamera"></div></div>
  </div>
  <div class="vehicle-legend">
    <span class="legend-item"><span class="legend-dot" style="background:#0891b2"></span>V1</span>
    <span class="legend-item"><span class="legend-dot" style="background:#16a34a"></span>V2</span>
    <span class="legend-item"><span class="legend-dot" style="background:#f97316"></span>V3</span>
    <span class="legend-item"><span class="legend-dot" style="background:#9333ea"></span>V4</span>
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
  <select id="vehicleSelect" onchange="changeVehicle()"></select>
  <div class="tracking-info">
    <div class="box"><div class="label">Driver</div><div class="value" id="trackDriver">--</div></div>
    <div class="box"><div class="label">Number Plate</div><div class="value" id="trackPlate">--</div></div>
    <div class="box"><div class="label">Location</div><div class="value" id="trackLocation">--</div></div>
    <div class="box"><div class="label">GPS Status</div><div class="value" id="trackStatus">--</div></div>
  </div>
  <div class="grid tracking-grid">
    <div class="card"><h2>MAP - Vehicle Live Map</h2><div class="map" id="mapFrame"></div></div>
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
let dashboardLeafletMap = null;
let trackingLeafletMap = null;
let dashboardMarker = null;
let trackingMarker = null;
let dashboardRoute = null;
let trackingRoute = null;
let routeHistory = { v1: [], v2: [], v3: [], v4: [] };
let cameraGridState = {};
const pageToken = new URLSearchParams(window.location.search).get('token') || new URLSearchParams(window.location.search).get('api_token') || new URLSearchParams(window.location.search).get('key') || '';

let vehicles = {
  v1: { name:"Vehicle 1", lat:"28.6139", lon:"77.2090", driver:"DRIVER 1", plate:"1234", location:"Delhi", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraOn:true, accuracy:null, cameraId:"9100000001" },
  v2: { name:"Vehicle 2", lat:"26.9124", lon:"75.7873", driver:"DRIVER 2", plate:"5678", location:"Jaipur", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraOn:true, accuracy:null, cameraId:"9100000002" },
  v3: { name:"Vehicle 3", lat:"19.0760", lon:"72.8777", driver:"DRIVER 3", plate:"9012", location:"Mumbai", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraOn:true, accuracy:null, cameraId:"9100000003" },
  v4: { name:"Vehicle 4", lat:"22.5726", lon:"88.3639", driver:"DRIVER 4", plate:"3456", location:"Kolkata", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:false, cameraOn:true, accuracy:null, cameraId:"9100000004" }
};

async function toggleFullscreen(elementId){
  let el = document.getElementById(elementId);
  if(!el) return;
  try{
    if(document.fullscreenElement){
      await document.exitFullscreen();
    }else{
      await el.requestFullscreen();
    }
  }catch(e){
    console.log('Fullscreen error:', e);
  }
}

document.addEventListener('fullscreenchange', ()=>{
  setTimeout(()=>{
    if(dashboardLeafletMap) dashboardLeafletMap.invalidateSize();
    if(trackingLeafletMap) trackingLeafletMap.invalidateSize();
    if(activeVehicle) updateMapForVehicle(activeVehicle);
  }, 120);
});

function showPage(pageId, menuItem){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.getElementById(pageId).classList.add('active');
  document.querySelectorAll('.menu div').forEach(i=>i.classList.remove('active-menu'));
  menuItem.classList.add('active-menu');
  if(pageId === 'camera') loadCameraViewOnlyActive();
  if(pageId === 'dashboard' || pageId === 'tracking'){
    setTimeout(()=>{
      if(dashboardLeafletMap) dashboardLeafletMap.invalidateSize();
      if(trackingLeafletMap) trackingLeafletMap.invalidateSize();
      if(activeVehicle) updateMapForVehicle(activeVehicle);
    }, 100);
  }
}
function activeBadge(){ return `<span class="live">Video Active</span>`; }
function offlineBadge(){ return `<span class="offline">Video Offline</span>`; }
function cameraOffBadge(){ return `<span class="offline">Camera Off</span>`; }
function gpsLiveBadge(){ return `<span class="gps-live">GPS Live</span>`; }
function waitingBadge(){ return `<span class="offline">Waiting GPS</span>`; }
function gpsStatusText(v){
  if(!v.gpsActive) return 'Waiting GPS';
  return v.accuracy ? `GPS Live ±${v.accuracy} m` : 'GPS Live';
}
function cameraHtml(id){
  let cam = vehicles[id].cameraId;
  return `<iframe src="https://vdo.ninja/?view=${cam}&cleanoutput&transparent" loading="eager" allow="camera; microphone; autoplay; fullscreen" allowfullscreen></iframe><div class="rec">&bull; REC</div>`;
}
async function toggleCamera(id){
  let v = vehicles[id];
  if(!v) return;
  let nextState = !v.cameraOn;
  let btn = document.getElementById('cameraToggle-' + id);
  if(btn) btn.disabled = true;
  try{
    let tokenPart = pageToken ? `&token=${encodeURIComponent(pageToken)}` : '';
    let res = await fetch(`/camera-toggle?id=${id}&enabled=${nextState ? '1' : '0'}${tokenPart}&ts=${Date.now()}`, {method:'POST', cache:'no-store'});
    let data = await res.json();
    if(!res.ok) throw new Error(data.message || 'Camera toggle failed');
    v.cameraOn = data.camera_on;
    v.videoActive = data.video_active;
    dashboardCameraVehicle = null;
    trackingCameraVehicle = null;
    updateRowsVisibility();
    if(activeVehicle === id) selectVehicle(id);
    loadCameraViewOnlyActive(true);
  }catch(e){
    console.log('Camera toggle error:', e);
  }finally{
    if(btn) btn.disabled = false;
  }
}
function mapSrc(v, zoom=15){ return `https://maps.google.com/maps?q=${v.lat},${v.lon}&z=${zoom}&output=embed`; }
const vehicleColors = {
  v1: {main:'#0891b2', roof:'#67e8f9', body:'#0f766e'},
  v2: {main:'#16a34a', roof:'#bbf7d0', body:'#15803d'},
  v3: {main:'#f97316', roof:'#fed7aa', body:'#c2410c'},
  v4: {main:'#9333ea', roof:'#e9d5ff', body:'#7e22ce'}
};
function vehicleColor(id){
  return vehicleColors[id] || vehicleColors.v1;
}
function carIcon(id){
  let c = vehicleColor(id);
  return L.divIcon({
    className: '',
    html: `<div class="car-marker" style="border-color:${c.main};"><span class="car-heading" style="border-bottom-color:${c.main};"></span><svg class="car-logo" viewBox="0 0 72 72" aria-hidden="true"><defs><linearGradient id="body-${id}" x1="10" x2="62" y1="20" y2="58" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="${c.roof}"/><stop offset=".42" stop-color="${c.main}"/><stop offset="1" stop-color="${c.body}"/></linearGradient><linearGradient id="glass-${id}" x1="22" x2="50" y1="22" y2="39" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#f8fdff"/><stop offset="1" stop-color="#67e8f9"/></linearGradient></defs><path d="M16 36h40l-6-16H22l-6 16z" fill="url(#body-${id})"/><path d="M22 20h28l5 16H17l5-16z" fill="${c.main}" opacity=".92"/><path d="M25 24h22l3 11H21l4-11z" fill="url(#glass-${id})"/><path d="M12 36h48c3.8 0 7 3.2 7 7v8c0 2-1.6 3.5-3.5 3.5h-55C6.6 54.5 5 53 5 51v-8c0-3.8 3.2-7 7-7z" fill="url(#body-${id})"/><path d="M9 42c7 3.4 46 3.4 54 0" stroke="#ffffff" stroke-width="3" stroke-linecap="round" opacity=".7"/><path d="M13 50h46" stroke="#020617" stroke-width="2" opacity=".25"/><circle cx="20" cy="55" r="7.5" fill="#020617"/><circle cx="52" cy="55" r="7.5" fill="#020617"/><circle cx="20" cy="55" r="3" fill="#cbd5e1"/><circle cx="52" cy="55" r="3" fill="#cbd5e1"/><path d="M8 45h7M57 45h7" stroke="#fef08a" stroke-width="3" stroke-linecap="round"/><path d="M25 25h10" stroke="#ffffff" stroke-width="2" stroke-linecap="round" opacity=".78"/></svg><span class="car-label" style="background:${c.main};">LIVE GPS</span></div>`,
    iconSize: [74, 90],
    iconAnchor: [37, 74]
  });
}
function initLeafletMaps(){
  let start = [28.6139, 77.2090];
  dashboardLeafletMap = L.map('dashboardMap').setView(start, 13);
  trackingLeafletMap = L.map('mapFrame').setView(start, 15);
  [dashboardLeafletMap, trackingLeafletMap].forEach(map=>{
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    }).addTo(map);
  });
  dashboardMarker = L.marker(start, {icon: carIcon('v1')}).addTo(dashboardLeafletMap);
  trackingMarker = L.marker(start, {icon: carIcon('v1')}).addTo(trackingLeafletMap);
  dashboardRoute = L.polyline([], {color:'#0891b2', weight:6, opacity:.88, lineCap:'round', lineJoin:'round'}).addTo(dashboardLeafletMap);
  trackingRoute = L.polyline([], {color:'#0891b2', weight:6, opacity:.88, lineCap:'round', lineJoin:'round'}).addTo(trackingLeafletMap);
}
function validLatLon(v){
  let lat = Number(v.lat);
  let lon = Number(v.lon);
  if(!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return [lat, lon];
}
function addRoutePoint(id){
  let point = validLatLon(vehicles[id]);
  if(!point || vehicles[id].gpsActive !== true) return;
  let history = routeHistory[id] || [];
  let last = history[history.length - 1];
  if(!last || last[0] !== point[0] || last[1] !== point[1]){
    history.push(point);
    if(history.length > 500) history.shift();
    routeHistory[id] = history;
  }
}
function getActiveVehicleIds(){ return Object.keys(vehicles).filter(id=>vehicles[id].videoActive === true); }
function getGpsVehicleIds(){ return Object.keys(vehicles).filter(id=>vehicles[id].gpsActive === true); }

function loadActiveVehiclesDropdown(){
  let select = document.getElementById('vehicleSelect');
  let currentValue = select.value;
  select.innerHTML = '';
  Object.keys(vehicles).forEach(id=>{
    let v = vehicles[id];
    let opt = document.createElement('option');
    opt.value = id;
    let gpsText = v.gpsActive ? 'GPS Live' : 'Waiting GPS';
    let videoText = v.videoActive ? 'Video Active' : 'Video Offline';
    opt.text = `${v.name} - ${v.plate} - ${gpsText} - ${videoText}`;
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
    let videoStatus = !v.cameraOn ? cameraOffBadge() : (videoActive ? activeBadge() : offlineBadge());
    if(v.gpsActive) gpsCount++;
    ['dashRow-', 'vehicleRow-'].forEach(prefix=>{
      let row = document.getElementById(prefix + id);
      if(row){ row.style.display = 'table-row'; row.classList.toggle('active-row', id === activeVehicle); }
    });
    let ds = document.getElementById('dashStatus-' + id); if(ds) ds.innerHTML = videoStatus;
    let vs = document.getElementById('vehicleStatus-' + id); if(vs) vs.innerHTML = videoStatus;
    let dg = document.getElementById('dashGps-' + id); if(dg) dg.innerHTML = v.gpsActive ? gpsLiveBadge() : waitingBadge();
    let vg = document.getElementById('vehicleGps-' + id); if(vg) vg.innerHTML = v.gpsActive ? gpsLiveBadge() : waitingBadge();
  }
  document.getElementById('activeCount').innerHTML = activeIds.length;
  document.getElementById('gpsLiveCount').innerHTML = gpsCount;
}

function loadCameraViewOnlyActive(force=false){
  let grid = document.getElementById('cameraGrid');
  if(force){
    grid.innerHTML = '';
    cameraGridState = {};
  }
  Object.keys(vehicles).forEach(id=>{
    let v = vehicles[id];
    let state = `${v.videoActive === true}|${v.cameraOn === true}|${v.cameraId}`;
    let card = document.getElementById('cameraCard-' + id);
    if(card && cameraGridState[id] === state) return;
    if(!card){
      card = document.createElement('div');
      card.className = 'card';
      card.id = 'cameraCard-' + id;
      grid.appendChild(card);
    }
    cameraGridState[id] = state;
    let videoHtml = !v.cameraOn ? '<div class="camera-offline">CAMERA OFF</div>' : (v.videoActive ? cameraHtml(id) : '<div class="camera-offline">VIDEO OFFLINE</div>');
    let statusHtml = !v.cameraOn ? cameraOffBadge() : (v.videoActive ? activeBadge() : offlineBadge());
    let toggleClass = v.cameraOn ? 'on' : 'off';
    let toggleText = v.cameraOn ? 'ON' : 'OFF';
    card.innerHTML = `
      <div class="camera-title-row">
        <div>
          <h2>${v.name}</h2>
          <small>Plate: ${v.plate} | Driver: ${v.driver}</small>
        </div>
        <div class="camera-actions">${statusHtml}<button class="camera-toggle ${toggleClass}" id="cameraToggle-${id}" type="button" onclick="toggleCamera('${id}')">${toggleText}</button></div>
      </div>
      <div class="camera">${videoHtml}</div>
      <div class="vehicle-meta">
        <div class="meta-pill"><b>Driver:</b> ${v.driver}</div>
        <div class="meta-pill"><b>Plate:</b> ${v.plate}</div>
        <div class="meta-pill"><b>Veh Type:</b> ${v.name}</div>
        <div class="meta-pill"><b>Mob No:</b> ${v.cameraId}</div>
      </div>
    `;
  });
}

function updateMapForVehicle(id){
  let v = vehicles[id];
  let point = validLatLon(v);
  if(!point || !dashboardLeafletMap || !trackingLeafletMap) return;
  addRoutePoint(id);
  let color = vehicleColor(id).main;
  dashboardMarker.setIcon(carIcon(id));
  trackingMarker.setIcon(carIcon(id));
  dashboardMarker.setLatLng(point);
  trackingMarker.setLatLng(point);
  dashboardRoute.setStyle({color: color, weight: 6, opacity: .9});
  trackingRoute.setStyle({color: color, weight: 6, opacity: .9});
  dashboardRoute.setLatLngs(routeHistory[id] || []);
  trackingRoute.setLatLngs(routeHistory[id] || []);
  dashboardLeafletMap.setView(point, Math.max(dashboardLeafletMap.getZoom(), 15));
  trackingLeafletMap.setView(point, Math.max(trackingLeafletMap.getZoom(), 15));
  setTimeout(()=>{ dashboardLeafletMap.invalidateSize(); trackingLeafletMap.invalidateSize(); }, 80);
}

function updateCameraIfNeeded(id){
  let v = vehicles[id];
  if(!v || v.cameraOn !== true || v.videoActive !== true){
    let message = v && v.cameraOn !== true ? 'CAMERA OFF' : 'NO VIDEO ACTIVE';
    document.getElementById('dashboardCamera').innerHTML = `<div style="color:white;display:flex;align-items:center;justify-content:center;height:100%;font-weight:bold;">${message}</div>`;
    document.getElementById('trackingCamera').innerHTML = `<div style="color:white;display:flex;align-items:center;justify-content:center;height:100%;font-weight:bold;">${message}</div>`;
    dashboardCameraVehicle = null;
    trackingCameraVehicle = null;
    return;
  }
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
  if(!v) return;
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
  document.getElementById('trackStatus').innerHTML = gpsStatusText(v);
  document.getElementById('selectedSpeed').innerHTML = v.speed;
  document.getElementById('sidebarStatus').innerHTML = v.videoActive ? '&bull; ' + v.name + ' Video Active' : '&bull; No Video Active';
  updateRowsVisibility();
}
function changeVehicle(){ selectVehicle(document.getElementById('vehicleSelect').value); }

function showNoActiveVideo(){
  dashboardCameraVehicle = null;
  trackingCameraVehicle = null;
  document.getElementById('dashboardCamera').innerHTML = '<div style="color:white;display:flex;align-items:center;justify-content:center;height:100%;font-weight:bold;">NO VIDEO ACTIVE</div>';
  document.getElementById('trackingCamera').innerHTML = '<div style="color:white;display:flex;align-items:center;justify-content:center;height:100%;font-weight:bold;">NO VIDEO ACTIVE</div>';
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
    let res = await fetch('/gps-data?ts=' + Date.now(), {cache:'no-store'});
    let data = await res.json();
    for(let id in data){
      if(vehicles[id]){
        vehicles[id].lat = data[id].lat;
        vehicles[id].lon = data[id].lon;
        vehicles[id].speed = data[id].speed + ' km/h';
        vehicles[id].lastUpdate = data[id].last_update;
        vehicles[id].gpsActive = data[id].gps_active;
        vehicles[id].videoActive = data[id].video_active;
        vehicles[id].cameraOn = data[id].camera_on;
        vehicles[id].accuracy = data[id].accuracy;
        if(data[id].gps_active === true) vehicles[id].location = data[id].lat + ', ' + data[id].lon;
        addRoutePoint(id);
      }
    }
    loadActiveVehiclesDropdown();
    updateVehicleTextFields();
    updateRowsVisibility();
    let gpsIds = getGpsVehicleIds();
    if(activeVehicle) selectVehicle(activeVehicle);
    else if(gpsIds.length > 0) selectVehicle(gpsIds[0]);
    else selectVehicle('v1');
    if(document.getElementById('camera').classList.contains('active')) loadCameraViewOnlyActive();
  }catch(e){ console.log('GPS fetch error:', e); }
}

function initDashboard(){
  initLeafletMaps();
  loadActiveVehiclesDropdown();
  updateRowsVisibility();
  selectVehicle('v1');
  fetchGPSLoggerData();
  setInterval(fetchGPSLoggerData, 1000);
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
    speed = first_value(data, "speed_kmh", "speedKmh", "kmh", "speed", "spd", "SPD", "Speed") or "0"
    speed_unit = first_value(data, "speed_unit", "unit", "speedUnit")
    accuracy = parse_accuracy(first_value(data, "accuracy", "acc", "horizontal_accuracy", "hacc"))

    if vehicle_id not in gps_live_data:
        return jsonify({"status": "error", "message": "Invalid vehicle id. Use v1, v2, v3, v4"}), 400

    try:
        lat_float = parse_coordinate(lat, "lat", -90, 90)
        lon_float = parse_coordinate(lon, "lon", -180, 180)
    except ValueError as exc:
        return jsonify({
            "status": "error",
            "message": str(exc),
            "example": "/gps?id=v1&lat=28.6200&lon=77.2300&speed=12.5",
        }), 400

    if first_value(data, "speed_kmh", "speedKmh", "kmh") is not None and speed_unit is None:
        speed_unit = "kmh"

    speed_float = parse_speed(speed, speed_unit)
    current_time = now_ist()

    vehicle = gps_live_data[vehicle_id]
    vehicle.update({
        "lat": str(lat_float),
        "lon": str(lon_float),
        "speed": str(speed_float),
        "last_update": current_time.strftime("%d-%m-%Y %I:%M:%S %p"),
        "gps_active": True,
        "updated_at": current_time,
        "accuracy": accuracy,
    })

    return jsonify({
        "status": "success",
        "message": "GPS Logger data received",
        "vehicle_id": vehicle_id,
        "data": public_vehicle_data(vehicle, vehicle_id),
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
        "data": public_vehicle_data(vehicle, vehicle_id),
    })


@app.route("/camera-toggle", methods=["GET", "POST"])
def camera_toggle():
    data = merged_payload()

    if not token_valid(data):
        return jsonify({"status": "error", "message": "Invalid or missing GPS token"}), 401

    vehicle_id = first_value(data, "id") or "v1"
    if vehicle_id not in gps_live_data:
        return jsonify({"status": "error", "message": "Invalid vehicle id. Use v1, v2, v3, v4"}), 400

    enabled_value = str(first_value(data, "enabled", "on", "camera_on") or "").strip().lower()
    if enabled_value in ("1", "true", "yes", "on"):
        camera_enabled[vehicle_id] = True
    elif enabled_value in ("0", "false", "no", "off"):
        camera_enabled[vehicle_id] = False
    else:
        return jsonify({"status": "error", "message": "Use enabled=1 or enabled=0"}), 400

    public_data = public_vehicle_data(gps_live_data[vehicle_id], vehicle_id)
    return jsonify({
        "status": "success",
        "vehicle_id": vehicle_id,
        "camera_on": public_data["camera_on"],
        "video_active": public_data["video_active"],
        "data": public_data,
    })


@app.route("/mobile-camera")
def mobile_camera_page():
    data = merged_payload()

    if not token_valid(data):
        return "Invalid or missing GPS token", 401

    vehicle_id = first_value(data, "id") or "v1"
    if vehicle_id not in gps_live_data:
        return "Invalid vehicle id. Use v1, v2, v3, v4", 400

    camera_id = CAMERA_IDS[vehicle_id]
    token = first_value(data, "token", "api_token", "key") or ""
    token_query = f"&token={token}" if token else ""
    heartbeat_url = f"/video?id={vehicle_id}{token_query}"
    vdo_push_url = f"https://vdo.ninja/?push={camera_id}"

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<title>{vehicle_id.upper()} Mobile Feed</title>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {{ box-sizing:border-box; }}
body {{ margin:0; background:#0f172a; color:white; font-family:Arial,sans-serif; }}
.top {{ padding:14px; background:#020617; display:flex; gap:10px; align-items:center; justify-content:space-between; }}
.title {{ font-weight:800; font-size:16px; }}
.status {{ color:#22c55e; font-size:13px; font-weight:700; }}
.open {{ color:white; background:#0891b2; text-decoration:none; padding:10px 12px; border-radius:10px; font-size:13px; font-weight:800; }}
iframe {{ width:100vw; height:calc(100vh - 58px); border:0; display:block; background:#111827; }}
</style>
</head>
<body>
<div class="top">
  <div>
    <div class="title">{vehicle_id.upper()} Mob No ({camera_id})</div>
    <div class="status" id="status">Starting video heartbeat...</div>
  </div>
  <a class="open" href="{vdo_push_url}" target="_blank">Open Feed</a>
</div>
<iframe src="{vdo_push_url}" allow="camera; microphone; autoplay; fullscreen" allowfullscreen></iframe>
<script>
const heartbeatUrl = "{heartbeat_url}";
let wakeLock = null;
async function sendHeartbeat(){{
  try {{
    const response = await fetch(heartbeatUrl + "&ts=" + Date.now(), {{cache:"no-store"}});
    document.getElementById("status").textContent = response.ok ? "Video active heartbeat running" : "Heartbeat error";
  }} catch (error) {{
    document.getElementById("status").textContent = "Heartbeat network error";
  }}
}}
async function keepScreenAwake(){{
  try {{
    if ("wakeLock" in navigator && wakeLock === null) {{
      wakeLock = await navigator.wakeLock.request("screen");
      wakeLock.addEventListener("release", () => {{ wakeLock = null; }});
    }}
  }} catch (error) {{}}
}}
document.addEventListener("visibilitychange", () => {{
  if (document.visibilityState === "visible") keepScreenAwake();
}});
sendHeartbeat();
keepScreenAwake();
setInterval(sendHeartbeat, 2000);
setInterval(keepScreenAwake, 15000);
</script>
</body>
</html>
"""


@app.route("/gps-data")
def gps_data_api():
    return jsonify({
        vehicle_id: public_vehicle_data(data, vehicle_id)
        for vehicle_id, data in gps_live_data.items()
    })


@app.route("/gps-test")
def gps_test_page():
    token_hint = "&token=YOUR_TOKEN" if GPS_API_TOKEN else ""
    return f"""
    <h2>GPS Logger Test</h2>
    <p>Click test links:</p>
    <a href="/gps?id=v1&lat=28.6200&lon=77.2300&speed=45&unit=kmh{token_hint}">Update Vehicle 1 Test</a><br><br>
    <a href="/gps?id=v2&lat=26.9220&lon=75.8000&speed=55&unit=kmh{token_hint}">Update Vehicle 2 Test</a><br><br>
    <a href="/gps?id=v3&lat=19.0900&lon=72.8800&speed=60&unit=kmh{token_hint}">Update Vehicle 3 Test</a><br><br>
    <a href="/gps?id=v4&lat=22.5800&lon=88.3700&speed=50&unit=kmh{token_hint}">Update Vehicle 4 Test</a><br><br>
    <p>Video active test links:</p>
    <a href="/video?id=v1{token_hint}">Vehicle 1 Video Active</a><br><br>
    <a href="/video?id=v2{token_hint}">Vehicle 2 Video Active</a><br><br>
    <a href="/video?id=v3{token_hint}">Vehicle 3 Video Active</a><br><br>
    <a href="/video?id=v4{token_hint}">Vehicle 4 Video Active</a><br><br>
    <p>Mobile camera links:</p>
    <a href="/mobile-camera?id=v1{token_hint}">Vehicle 1 Mobile Camera</a><br><br>
    <a href="/mobile-camera?id=v2{token_hint}">Vehicle 2 Mobile Camera</a><br><br>
    <a href="/mobile-camera?id=v3{token_hint}">Vehicle 3 Mobile Camera</a><br><br>
    <a href="/mobile-camera?id=v4{token_hint}">Vehicle 4 Mobile Camera</a><br><br>
    <p>After click, go back to dashboard.</p>
    <a href="/">Open Dashboard</a>
    """


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
