from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

# GPS Logger se last received data yaha store hoga
# id: v1, v2, v3, v4 use karna
gps_live_data = {
    "v1": {"lat": "28.6139", "lon": "77.2090", "speed": "0", "last_update": "No GPS Data", "gps_active": False},
    "v2": {"lat": "26.9124", "lon": "75.7873", "speed": "0", "last_update": "No GPS Data", "gps_active": False},
    "v3": {"lat": "19.0760", "lon": "72.8777", "speed": "0", "last_update": "No GPS Data", "gps_active": False},
    "v4": {"lat": "22.5726", "lon": "88.3639", "speed": "0", "last_update": "No GPS Data", "gps_active": False},
}


@app.route("/")
def home():
    return r'''
<!DOCTYPE html>
<html>
<head>
<title>MT GPS Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* { margin:0; padding:0; box-sizing:border-box; font-family:Arial, sans-serif; }
body { background:#f4f7fb; color:#0f172a; overflow-x:hidden; }
.layout { display:flex; min-height:100vh; }
.sidebar { width:310px; background:linear-gradient(180deg,#020617 0%,#07111f 45%,#0f172a 100%); padding:24px 20px; border-right:1px solid rgba(34,211,238,.18); min-height:100vh; position:sticky; top:0; box-shadow:8px 0 30px rgba(15,23,42,.25); }
.logo { display:flex; align-items:center; gap:14px; color:#22d3ee; margin-bottom:28px; padding:18px 16px; border-radius:22px; background:linear-gradient(135deg,rgba(34,211,238,.16),rgba(8,145,178,.06)); border:1px solid rgba(34,211,238,.28); }
.logo-icon { width:52px; height:52px; border-radius:18px; background:rgba(34,211,238,.16); display:flex; align-items:center; justify-content:center; font-size:28px; }
.logo-text { font-size:26px; font-weight:900; letter-spacing:1px; }
.logo small { display:block; font-size:12px; color:#94a3b8; margin-top:5px; }
.menu-title { color:#64748b; font-size:12px; font-weight:bold; margin:20px 12px 12px; text-transform:uppercase; letter-spacing:1.2px; }
.menu div { display:flex; align-items:center; gap:14px; padding:17px 16px; margin-bottom:13px; border-radius:18px; cursor:pointer; background:rgba(255,255,255,.04); color:#cbd5e1; transition:.3s ease; font-size:17px; font-weight:700; border:1px solid rgba(255,255,255,.06); }
.menu div .icon { width:38px; height:38px; border-radius:13px; background:rgba(255,255,255,.06); display:flex; align-items:center; justify-content:center; }
.menu div:hover { background:rgba(34,211,238,.13); color:#22d3ee; transform:translateX(7px); }
.menu div.active-menu { background:linear-gradient(90deg,rgba(34,211,238,.24),rgba(8,145,178,.08)); color:#22d3ee; border:1px solid rgba(34,211,238,.35); }
.sidebar-card { margin-top:28px; padding:18px; border-radius:22px; background:linear-gradient(135deg,rgba(34,211,238,.12),rgba(255,255,255,.04)); border:1px solid rgba(34,211,238,.18); }
.sidebar-card h4 { color:#e2e8f0; font-size:16px; margin-bottom:10px; }
.sidebar-card p { color:#22c55e; font-size:14px; font-weight:bold; }
.sidebar-card small { display:block; color:#94a3b8; font-size:12px; margin-top:8px; }
.main { flex:1; padding:30px; }
.page { display:none; }
.active { display:block; }
.title { font-size:38px; font-weight:bold; color:#0891b2; margin-bottom:8px; }
.subtitle { color:#64748b; margin-bottom:25px; }
.stats { display:grid; grid-template-columns:repeat(4,1fr); gap:18px; margin-bottom:25px; }
.stat { background:#fff; padding:22px; border-radius:18px; border:1px solid #e2e8f0; box-shadow:0 8px 25px rgba(15,23,42,.08); }
.stat h3 { color:#64748b; font-size:14px; }
.stat h2 { font-size:30px; margin-top:12px; color:#0891b2; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
.card { background:#fff; padding:20px; border-radius:20px; border:1px solid #e2e8f0; box-shadow:0 8px 25px rgba(15,23,42,.08); }
.card h2 { color:#0f172a; margin-bottom:12px; }
.map { height:320px; border-radius:16px; overflow:hidden; margin-top:15px; border:1px solid #cbd5e1; position:relative; background:#e5e7eb; }
.map iframe { width:100%; height:100%; border:none; }
.camera { height:320px; border-radius:16px; overflow:hidden; margin-top:15px; position:relative; background:#111827; }
.camera iframe, .camera img { width:100%; height:100%; object-fit:cover; border:none; }
.rec { position:absolute; top:15px; right:15px; background:#ef4444; color:white; padding:7px 14px; border-radius:20px; font-size:13px; font-weight:bold; z-index:5; }
.info, .tracking-info { display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin-top:25px; margin-bottom:22px; }
.box { background:#fff; padding:18px; border-radius:16px; border-left:5px solid #0891b2; box-shadow:0 8px 22px rgba(15,23,42,.07); }
.label { font-size:14px; color:#64748b; margin-bottom:8px; }
.value { font-size:21px; font-weight:bold; color:#0f766e; word-break:break-word; }
.green { color:#16a34a; }
.red { color:#dc2626!important; }
.camera-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:22px; }
.camera-grid .camera { height:300px; }
.mini-map { height:230px; border-radius:14px; overflow:hidden; border:1px solid #cbd5e1; margin-top:12px; background:#e5e7eb; }
.mini-map iframe { width:100%; height:100%; border:none; }
.vehicle-meta { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; color:#334155; font-size:14px; }
.meta-pill { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:10px; }
.table { margin-top:25px; background:#fff; border-radius:20px; overflow:hidden; border:1px solid #e2e8f0; box-shadow:0 8px 25px rgba(15,23,42,.08); }
table { width:100%; border-collapse:collapse; }
th, td { padding:16px; text-align:left; border-bottom:1px solid #e2e8f0; }
th { background:#f1f5f9; color:#475569; }
td { color:#0f172a; }
tr:hover { background:#f8fafc; }
.active-row { background:#ecfeff!important; }
.live { background:#dcfce7; color:#16a34a; padding:6px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
.offline { background:#fee2e2; color:#dc2626; padding:6px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
.gps-live { background:#dbeafe; color:#2563eb; padding:6px 12px; border-radius:20px; font-size:13px; font-weight:bold; display:inline-block; }
select { width:100%; padding:16px; border-radius:14px; background:#fff; color:#0f172a; border:1px solid #0891b2; margin-bottom:20px; font-size:18px; outline:none; }
.gps-help { background:#ecfeff; border:1px solid #67e8f9; border-radius:16px; padding:15px; margin-bottom:20px; color:#0f172a; font-size:14px; line-height:1.7; }
.tracking-grid { min-height:560px; }
.tracking-grid .card { display:flex; flex-direction:column; }
.tracking-grid .map, .tracking-grid .camera { flex:1; height:auto; min-height:520px; }
@media(max-width:1000px){ .sidebar{display:none;} .grid,.camera-grid{grid-template-columns:1fr;} .stats,.info,.tracking-info{grid-template-columns:1fr 1fr;} .tracking-grid .map,.tracking-grid .camera{height:420px; min-height:420px;} }
</style>
</head>
<body>
<div class="layout">
<div class="sidebar">
  <div class="logo"><div class="logo-icon">🚗</div><div><div class="logo-text">MT GPS</div><small>Vehicle Tracking System</small></div></div>
  <div class="menu-title">Main Menu</div>
  <div class="menu">
    <div class="active-menu" onclick="showPage('dashboard', this)"><span class="icon">📊</span><span>Dashboard</span></div>
    <div onclick="showPage('tracking', this)"><span class="icon">📍</span><span>Live Tracking</span></div>
    <div onclick="showPage('camera', this)"><span class="icon">📷</span><span>Camera View</span></div>
    <div onclick="showPage('vehicles', this)"><span class="icon">🚘</span><span>Vehicles</span></div>
  </div>
  <div class="sidebar-card"><h4>System Status</h4><p id="sidebarStatus">● Loading...</p><small>4 Camera + 4 GPS Active</small></div>
</div>

<div class="main">
<div id="dashboard" class="page active">
  <div class="title">LIVE VEHICLE DASHBOARD</div>
  <div class="subtitle">A GPS BASED BARHE CHALO SOFTWARE</div>
  <div class="stats">
    <div class="stat"><h3>Total Vehicles</h3><h2>4</h2></div>
    <div class="stat"><h3>Video Active</h3><h2 id="activeCount">4</h2></div>
    <div class="stat"><h3>GPS Live</h3><h2 id="gpsLiveCount">0</h2></div>
    <div class="stat"><h3>Selected Speed</h3><h2 id="selectedSpeed">--</h2></div>
  </div>
  <div class="grid">
    <div class="card"><h2>📍 Selected Vehicle GPS Tracking</h2><div class="map"><iframe id="dashboardMap" src="https://maps.google.com/maps?q=28.6139,77.2090&z=13&output=embed"></iframe></div></div>
    <div class="card"><h2>📷 Selected Vehicle Camera</h2><div class="camera" id="dashboardCamera"></div></div>
  </div>
  <div class="info">
    <div class="box"><div class="label">Driver Name</div><div class="value" id="topDriver">--</div></div>
    <div class="box"><div class="label">Number Plate</div><div class="value" id="topPlate">--</div></div>
    <div class="box"><div class="label">Speed</div><div class="value" id="topSpeed">--</div></div>
    <div class="box"><div class="label">GPS Last Update</div><div class="value green" id="topStatus">--</div></div>
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
  <div class="title">📍 LIVE TRACKING</div>
  <div class="subtitle">4 vehicles active hain. Dropdown se vehicle select karo.</div>
  <div class="gps-help"><b>GPS Logger URL:</b><br>
    Vehicle 1: https://flaskgps.onrender.com/gps?id=v1&lat=%LAT&lon=%LON&speed=0<br>
    Vehicle 2: https://flaskgps.onrender.com/gps?id=v2&lat=%LAT&lon=%LON&speed=0<br>
    Vehicle 3: https://flaskgps.onrender.com/gps?id=v3&lat=%LAT&lon=%LON&speed=0<br>
    Vehicle 4: https://flaskgps.onrender.com/gps?id=v4&lat=%LAT&lon=%LON&speed=0
  </div>
  <select id="vehicleSelect" onchange="changeVehicle()"></select>
  <div class="tracking-info">
    <div class="box"><div class="label">Driver</div><div class="value" id="trackDriver">--</div></div>
    <div class="box"><div class="label">Number Plate</div><div class="value" id="trackPlate">--</div></div>
    <div class="box"><div class="label">Location</div><div class="value" id="trackLocation">--</div></div>
    <div class="box"><div class="label">GPS Status</div><div class="value green" id="trackStatus">--</div></div>
  </div>
  <div class="grid tracking-grid">
    <div class="card"><h2>📍 Vehicle Live Map</h2><div class="map"><iframe id="mapFrame" src="https://maps.google.com/maps?q=28.6139,77.2090&z=15&output=embed"></iframe></div></div>
    <div class="card"><h2>📷 Vehicle Live Camera</h2><div class="camera" id="trackingCamera"></div></div>
  </div>
</div>

<div id="camera" class="page">
  <div class="title">📷 4 LIVE CAMERA + GPS VIEW</div>
  <div class="subtitle">Yaha 4 active vehicles ke camera aur GPS location ek sath dikhte hain.</div>
  <div class="camera-grid" id="cameraGrid"></div>
</div>

<div id="vehicles" class="page">
  <div class="title">🚘 LIVE VEHICLES</div>
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
let currentDashboardCameraId = null;
let currentTrackingCameraId = null;
let lastDashboardMapSrc = '';
let lastTrackingMapSrc = '';
let cameraGridLoaded = false;
let lastCameraMapSrc = {};

let vehicles = {
  v1: { name:"Vehicle 1", lat:"28.6139", lon:"77.2090", driver:"DRIVER 1", plate:"1234", location:"Delhi", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:true, cameraId:"car1" },
  v2: { name:"Vehicle 2", lat:"26.9124", lon:"75.7873", driver:"DRIVER 2", plate:"5678", location:"Jaipur", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:true, cameraId:"car2" },
  v3: { name:"Vehicle 3", lat:"19.0760", lon:"72.8777", driver:"DRIVER 3", plate:"9012", location:"Mumbai", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:true, cameraId:"car3" },
  v4: { name:"Vehicle 4", lat:"22.5726", lon:"88.3639", driver:"DRIVER 4", plate:"3456", location:"Kolkata", speed:"0 km/h", lastUpdate:"No GPS Data", gpsActive:false, videoActive:true, cameraId:"car4" }
};

function showPage(pageId, menuItem){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.getElementById(pageId).classList.add('active');
  document.querySelectorAll('.menu div').forEach(i=>i.classList.remove('active-menu'));
  menuItem.classList.add('active-menu');
  if(pageId === 'camera') { loadCameraViewOnlyActive(); updateCameraGridInfo(); }
}
function activeBadge(){ return `<span class="live">Video Active</span>`; }
function gpsLiveBadge(){ return `<span class="gps-live">GPS Live</span>`; }
function waitingBadge(){ return `<span class="offline">Waiting GPS</span>`; }
function cameraHtml(id){
  let cam = vehicles[id].cameraId;
  return `<iframe src="https://vdo.ninja/?view=${cam}&cleanoutput&transparent" allow="camera; microphone; autoplay; fullscreen" allowfullscreen></iframe><div class="rec">● REC</div>`;
}
function mapSrc(v, zoom=15){ return `https://maps.google.com/maps?q=${v.lat},${v.lon}&z=${zoom}&output=embed`; }
function getActiveVehicleIds(){ return Object.keys(vehicles).filter(id=>vehicles[id].videoActive === true); }

function loadActiveVehiclesDropdown(){
  let select = document.getElementById('vehicleSelect');
  select.innerHTML = '';
  getActiveVehicleIds().forEach(id=>{
    let v = vehicles[id];
    let opt = document.createElement('option');
    opt.value = id;
    opt.text = `${v.name} - ${v.plate} - ${v.location}`;
    select.appendChild(opt);
  });
}

function updateRowsVisibility(){
  let activeIds = getActiveVehicleIds();
  let gpsCount = 0;
  for(let id in vehicles){
    let v = vehicles[id];
    if(v.gpsActive) gpsCount++;
    ['dashRow-', 'vehicleRow-'].forEach(prefix=>{
      let row = document.getElementById(prefix + id);
      if(row){ row.style.display = 'table-row'; row.classList.toggle('active-row', id === activeVehicle); }
    });
    let ds = document.getElementById('dashStatus-' + id); if(ds) ds.innerHTML = activeBadge();
    let vs = document.getElementById('vehicleStatus-' + id); if(vs) vs.innerHTML = activeBadge();
    let dg = document.getElementById('dashGps-' + id); if(dg) dg.innerHTML = v.gpsActive ? gpsLiveBadge() : waitingBadge();
    let vg = document.getElementById('vehicleGps-' + id); if(vg) vg.innerHTML = v.gpsActive ? gpsLiveBadge() : waitingBadge();
  }
  document.getElementById('activeCount').innerHTML = activeIds.length;
  document.getElementById('gpsLiveCount').innerHTML = gpsCount;
}

function loadCameraViewOnlyActive(){
  if(cameraGridLoaded) return; // camera iframe dobara create nahi hoga

  let grid = document.getElementById('cameraGrid');
  grid.innerHTML = '';

  getActiveVehicleIds().forEach(id=>{
    let v = vehicles[id];
    let card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h2>🚘 ${v.name} - ${v.plate}</h2>
      <div class="camera">${cameraHtml(id)}</div>
      <div class="vehicle-meta">
        <div class="meta-pill"><b>Driver:</b> <span id="camDriver-${id}">${v.driver}</span></div>
        <div class="meta-pill"><b>Speed:</b> <span id="camSpeed-${id}">${v.speed}</span></div>
        <div class="meta-pill"><b>GPS:</b> <span id="camGps-${id}">${v.gpsActive ? 'Live' : 'Waiting GPS'}</span></div>
        <div class="meta-pill"><b>Update:</b> <span id="camUpdate-${id}">${v.lastUpdate}</span></div>
      </div>
      <div class="mini-map"><iframe id="camMap-${id}" src="${mapSrc(v, 15)}"></iframe></div>
    `;
    grid.appendChild(card);
    lastCameraMapSrc[id] = mapSrc(v, 15);
  });

  cameraGridLoaded = true;
}

function updateCameraGridInfo(){
  if(!cameraGridLoaded) return;

  for(let id in vehicles){
    let v = vehicles[id];
    let setText = function(elId, text){
      let el = document.getElementById(elId);
      if(el && el.innerHTML !== text) el.innerHTML = text;
    };

    setText('camDriver-' + id, v.driver);
    setText('camSpeed-' + id, v.speed);
    setText('camGps-' + id, v.gpsActive ? 'Live' : 'Waiting GPS');
    setText('camUpdate-' + id, v.lastUpdate);

    let camMap = document.getElementById('camMap-' + id);
    let newSrc = mapSrc(v, 15);
    if(camMap && lastCameraMapSrc[id] !== newSrc){
      camMap.src = newSrc;
      lastCameraMapSrc[id] = newSrc;
    }
  }
}

function setSelectedCameraIfNeeded(id){
  if(currentDashboardCameraId !== id){
    document.getElementById('dashboardCamera').innerHTML = cameraHtml(id);
    currentDashboardCameraId = id;
  }

  if(currentTrackingCameraId !== id){
    document.getElementById('trackingCamera').innerHTML = cameraHtml(id);
    currentTrackingCameraId = id;
  }
}

function updateMapForVehicle(id){
  let v = vehicles[id];

  let dashboardSrc = mapSrc(v, 15);
  if(lastDashboardMapSrc !== dashboardSrc){
    document.getElementById('dashboardMap').src = dashboardSrc;
    lastDashboardMapSrc = dashboardSrc;
  }

  let trackingSrc = mapSrc(v, 15);
  if(lastTrackingMapSrc !== trackingSrc){
    document.getElementById('mapFrame').src = trackingSrc;
    lastTrackingMapSrc = trackingSrc;
  }
}

function selectVehicle(id){
  let v = vehicles[id];
  if(!v) return;

  activeVehicle = id;
  let sel = document.getElementById('vehicleSelect'); if(sel) sel.value = id;

  updateMapForVehicle(id);
  setSelectedCameraIfNeeded(id); // camera sirf vehicle change hone par reload hoga

  document.getElementById('topDriver').innerHTML = v.driver;
  document.getElementById('topPlate').innerHTML = v.plate;
  document.getElementById('topSpeed').innerHTML = v.speed;
  document.getElementById('topStatus').innerHTML = v.gpsActive ? v.lastUpdate : 'Waiting GPS';
  document.getElementById('trackDriver').innerHTML = v.driver;
  document.getElementById('trackPlate').innerHTML = v.plate;
  document.getElementById('trackLocation').innerHTML = v.location;
  document.getElementById('trackStatus').innerHTML = v.gpsActive ? 'GPS Live' : 'Waiting GPS';
  document.getElementById('selectedSpeed').innerHTML = v.speed;
  document.getElementById('sidebarStatus').innerHTML = '● 4 Vehicles Video Active';
  updateRowsVisibility();
}
function changeVehicle(){ selectVehicle(document.getElementById('vehicleSelect').value); }

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
        if(data[id].gps_active === true) vehicles[id].location = data[id].lat + ', ' + data[id].lon;
      }
    }
    updateVehicleTextFields();
    updateRowsVisibility();

    // GPS refresh par camera iframe reload nahi hoga
    if(activeVehicle){
      let v = vehicles[activeVehicle];
      updateMapForVehicle(activeVehicle);
      document.getElementById('topSpeed').innerHTML = v.speed;
      document.getElementById('selectedSpeed').innerHTML = v.speed;
      document.getElementById('topStatus').innerHTML = v.gpsActive ? v.lastUpdate : 'Waiting GPS';
      document.getElementById('trackLocation').innerHTML = v.location;
      document.getElementById('trackStatus').innerHTML = v.gpsActive ? 'GPS Live' : 'Waiting GPS';
    }

    updateCameraGridInfo();
  }catch(e){ console.log('GPS fetch error:', e); }
}

function initDashboard(){
  loadActiveVehiclesDropdown();
  updateRowsVisibility();
  let ids = getActiveVehicleIds();
  if(ids.length > 0) selectVehicle(ids[0]);
  loadCameraViewOnlyActive(); // 4 camera ek baar load honge, GPS refresh par reload nahi honge
  fetchGPSLoggerData();
  setInterval(fetchGPSLoggerData, 5000);
}
initDashboard();
</script>
</body>
</html>
'''


@app.route("/gps", methods=["GET", "POST"])
@app.route("/gpslogger", methods=["GET", "POST"])
@app.route("/log", methods=["GET", "POST"])
def receive_gps_logger():
    vehicle_id = request.args.get("id", "v1")

    lat = request.args.get("lat") or request.args.get("latitude") or request.args.get("LAT") or request.args.get("Latitude")
    lon = request.args.get("lon") or request.args.get("lng") or request.args.get("longitude") or request.args.get("LON") or request.args.get("Longitude")
    speed = request.args.get("speed") or request.args.get("spd") or request.args.get("SPD") or request.args.get("Speed") or "0"

    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        vehicle_id = data.get("id", vehicle_id)
        lat = data.get("lat") or data.get("latitude") or data.get("LAT") or data.get("Latitude") or lat
        lon = data.get("lon") or data.get("lng") or data.get("longitude") or data.get("LON") or data.get("Longitude") or lon
        speed = data.get("speed") or data.get("spd") or data.get("SPD") or data.get("Speed") or speed

    if vehicle_id not in gps_live_data:
        return jsonify({"status": "error", "message": "Invalid vehicle id. Use v1, v2, v3, v4"}), 400

    if not lat or not lon:
        return jsonify({"status": "error", "message": "lat and lon required", "example": "/gps?id=v1&lat=28.6200&lon=77.2300&speed=45"}), 400

    try:
        lat_float = float(lat)
        lon_float = float(lon)
        try:
            speed_float = float(speed)
        except Exception:
            speed_float = 0.0
    except ValueError:
        return jsonify({"status": "error", "message": "lat and lon must be number"}), 400

    gps_live_data[vehicle_id] = {
        "lat": str(lat_float),
        "lon": str(lon_float),
        "speed": str(speed_float),
        "last_update": datetime.now(IST).strftime("%d-%m-%Y %I:%M:%S %p"),
        "gps_active": True,
    }

    return jsonify({"status": "success", "message": "GPS Logger data received", "vehicle_id": vehicle_id, "data": gps_live_data[vehicle_id]})


@app.route("/gps-data")
def gps_data_api():
    return jsonify(gps_live_data)


@app.route("/gps-test")
def gps_test_page():
    return """
    <h2>GPS Logger Test</h2>
    <p>Click test links:</p>
    <a href="/gps?id=v1&lat=28.6200&lon=77.2300&speed=45">Update Vehicle 1 Test</a><br><br>
    <a href="/gps?id=v2&lat=26.9220&lon=75.8000&speed=55">Update Vehicle 2 Test</a><br><br>
    <a href="/gps?id=v3&lat=19.0900&lon=72.8800&speed=60">Update Vehicle 3 Test</a><br><br>
    <a href="/gps?id=v4&lat=22.5800&lon=88.3700&speed=50">Update Vehicle 4 Test</a><br><br>
    <p>After click, go back to dashboard.</p>
    <a href="/">Open Dashboard</a>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
