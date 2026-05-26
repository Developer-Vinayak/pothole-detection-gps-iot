// static/js/map.js

// ── Initialise Leaflet map ────────────────────────────────────
const map = L.map('leaflet-map', {
  center: [20.5937, 78.9629],   // India centre
  zoom: 5,
  zoomControl: true,
});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors',
  maxZoom: 19,
}).addTo(map);

// Custom marker icon
function makeIcon(conf){
  const color = conf >= 0.75 ? '#ef4444' : conf >= 0.55 ? '#f97316' : '#38bdf8';
  return L.divIcon({
    html: `<div style="
      width:14px;height:14px;border-radius:50%;
      background:${color};border:2px solid #fff;
      box-shadow:0 0 8px ${color};
    "></div>`,
    className: '',
    iconSize: [14,14],
    iconAnchor: [7,7],
  });
}

let markers = [];

function clearMarkers(){
  markers.forEach(m => map.removeLayer(m));
  markers = [];
}

function addMarker(d, isDemo=false){
  if(d.latitude == null || d.longitude == null) return;
  const conf  = d.confidence || 0;
  const label = isDemo ? ' (demo)' : '';
  const m = L.marker([d.latitude, d.longitude], { icon: makeIcon(conf) })
    .addTo(map)
    .bindPopup(`
      <b style="color:#f97316">${isDemo?'[DEMO] ':''}Detection #${d.id}</b><br>
      🕳️ Potholes: ${d.count || 1}<br>
      📊 Confidence: ${Math.round(conf*100)}%<br>
      📐 Area: ${d.area_m2 || 0} m²<br>
      📍 ${d.latitude.toFixed(5)}, ${d.longitude.toFixed(5)}<br>
      🕐 ${d.timestamp || 'N/A'}
      ${label}
    `);
  markers.push(m);
}

// ── Load real detections with GPS ─────────────────────────────
async function loadMapPoints(){
  try{
    const r    = await fetch('/api/map-points');
    const data = await r.json();
    const totalR = await fetch('/api/stats');
    const stats  = await totalR.json();

    document.getElementById('mp-count').textContent = data.length;
    document.getElementById('mp-total').textContent = stats.total || 0;
    document.getElementById('ms-count').textContent = `${data.length} entries`;

    const list = document.getElementById('map-det-list');
    if(!data.length){
      list.innerHTML = `<div class="map-empty">
        <div>📭</div>
        <div>No detections with GPS data yet</div>
        <div style="font-size:11px;margin-top:6px;color:#2a3d5a">GPS module coming soon</div>
      </div>`;
      return;
    }

    clearMarkers();
    data.forEach(d => addMarker(d));
    if(data.length > 0){
      map.setView([data[0].latitude, data[0].longitude], 14);
    }

    list.innerHTML = data.map(d => `
      <div class="map-det-item" onclick="flyTo(${d.latitude},${d.longitude},${d.id})">
        <div class="mdi-top">
          <span class="mdi-id">#${d.id} — ${d.count} pothole${d.count>1?'s':''}</span>
          <span class="mdi-time">${d.timestamp||''}</span>
        </div>
        <div class="mdi-coords">📍 ${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}</div>
      </div>`).join('');

  } catch(e){ console.error('Map load error:', e); }
}

function flyTo(lat, lng, id){
  map.flyTo([lat, lng], 16, { duration: 1 });
  markers.forEach(m => {
    if(m.getLatLng().lat === lat && m.getLatLng().lng === lng)
      m.openPopup();
  });
}

// ── Demo pins ─────────────────────────────────────────────────
const DEMO_PINS = [
  { id:'D1', confidence:0.82, count:2, area_m2:1.2,  latitude:28.6139, longitude:77.2090, timestamp:'Demo — New Delhi' },
  { id:'D2', confidence:0.67, count:1, area_m2:0.6,  latitude:19.0760, longitude:72.8777, timestamp:'Demo — Mumbai' },
  { id:'D3', confidence:0.91, count:3, area_m2:2.1,  latitude:12.9716, longitude:77.5946, timestamp:'Demo — Bengaluru' },
  { id:'D4', confidence:0.55, count:1, area_m2:0.4,  latitude:22.5726, longitude:88.3639, timestamp:'Demo — Kolkata' },
  { id:'D5', confidence:0.78, count:2, area_m2:1.8,  latitude:13.0827, longitude:80.2707, timestamp:'Demo — Chennai' },
];

let demoPinsLoaded = false;

function loadDemoPins(){
  if(demoPinsLoaded){ clearDemoPins(); return; }
  DEMO_PINS.forEach(d => addMarker(d, true));
  map.setView([20.5937, 78.9629], 5);
  demoPinsLoaded = true;

  const list = document.getElementById('map-det-list');
  list.innerHTML = DEMO_PINS.map(d => `
    <div class="map-det-item" onclick="flyTo(${d.latitude},${d.longitude},'${d.id}')">
      <div class="mdi-top">
        <span class="mdi-id" style="color:#f97316">[DEMO] ${d.timestamp.split('—')[1]}</span>
        <span style="font-size:11px;color:#ef4444">${Math.round(d.confidence*100)}%</span>
      </div>
      <div class="mdi-coords">📍 ${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}</div>
    </div>`).join('');

  document.getElementById('mp-count').textContent = DEMO_PINS.length + ' (demo)';
}

function clearDemoPins(){
  clearMarkers();
  demoPinsLoaded = false;
  document.getElementById('mp-count').textContent = '0';
  loadMapPoints();
}

// ── Init ──────────────────────────────────────────────────────
loadMapPoints();
