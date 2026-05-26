// static/js/dashboard.js

let currentId = null;

function cc(c){ return c>=.75?'ch':c>=.55?'cm':'cl' }
function cl(c){ return c>=.75?'HIGH':c>=.55?'MED':'LOW' }
function ft(ts){
  if(!ts) return 'N/A';
  const d = new Date(ts.replace(' ','T'));
  return d.toLocaleString('en-IN',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
}

async function loadData(){
  try{
    const [dr, sr] = await Promise.all([
      fetch('/api/detections'),
      fetch('/api/stats'),
    ]);
    const dets  = await dr.json();
    const stats = await sr.json();

    document.getElementById('s-total').textContent = stats.total || 0;
    document.getElementById('s-area').textContent  = (stats.total_area||0)+' m²';
    document.getElementById('s-conf').textContent  = (stats.avg_confidence||0)+'%';
    document.getElementById('s-last').textContent  =
      stats.last_detection !== 'N/A' ? ft(stats.last_detection) : 'None yet';
    document.getElementById('m-cement').textContent = stats.total_cement    || 0;
    document.getElementById('m-sand').textContent   = stats.total_sand      || 0;
    document.getElementById('m-agg').textContent    = stats.total_aggregate || 0;

    const list = document.getElementById('det-list');
    if(!dets.length){
      list.innerHTML = '<div class="empty"><div class="empty-icon">🕳️</div><div class="empty-text">No detections yet</div></div>';
      return;
    }

    list.innerHTML = dets.slice(0,50).map(d => `
      <div class="det-item${currentId===d.id?' selected':''}"
           onclick="showImg(${d.id},'${d.image_path||''}',this)">
        <div class="det-top">
          <span class="det-id">#${d.id} — ${d.count} pothole${d.count>1?'s':''}</span>
          <span class="det-time">${ft(d.timestamp)}</span>
        </div>
        <div class="det-badges">
          <span class="area-badge">📐 ${d.area_m2} m²</span>
          <span class="conf-badge ${cc(d.confidence)}">${cl(d.confidence)} ${Math.round(d.confidence*100)}%</span>
        </div>
        <div class="det-mats">
          <div class="mat-box"><div class="v">${d.cement_kg}</div><div class="l">Cement (kg)</div></div>
          <div class="mat-box"><div class="v">${d.sand_kg}</div><div class="l">Sand (kg)</div></div>
          <div class="mat-box"><div class="v">${d.aggregate_kg}</div><div class="l">Aggregate (kg)</div></div>
        </div>
      </div>`).join('');

    if(dets.length > 0 && dets[0].image_path && !currentId)
      showImg(dets[0].id, dets[0].image_path, null, dets[0]);

  } catch(e){ console.error(e); }
}

async function showImg(id, path, el, detData){
  currentId = id;
  document.querySelectorAll('.det-item').forEach(e => e.classList.remove('selected'));
  if(el) el.classList.add('selected');
  if(!path) return;

  let d = detData;
  if(!d){
    const dr   = await fetch('/api/detections');
    const dets = await dr.json();
    d = dets.find(x => x.id === id) || {};
  }

  document.getElementById('img-panel').innerHTML = `
    <div class="img-card">
      <div class="img-header">
        <span>Detection #${id}</span>
        <span class="conf-badge ${cc(d.confidence||0)}">${cl(d.confidence||0)} — ${Math.round((d.confidence||0)*100)}%</span>
      </div>
      <img src="/api/image/${path}" alt="Pothole #${id}" loading="lazy"/>
      <div class="img-mats">
        <div class="imb"><div class="v">${d.cement_kg||0}</div><div class="l">🏗️ Cement (kg)</div></div>
        <div class="imb"><div class="v">${d.sand_kg||0}</div><div class="l">🪨 Sand (kg)</div></div>
        <div class="imb"><div class="v">${d.aggregate_kg||0}</div><div class="l">⚫ Aggregate (kg)</div></div>
      </div>
      <div class="img-meta">
        <span>📅 ${ft(d.timestamp)}</span>
        <span>📐 Area: <b style="color:#38bdf8">${d.area_m2} m²</b></span>
        <span>📦 Volume: <b style="color:#4ade80">${d.volume_m3} m³</b></span>
        <span>🕳️ Potholes: <b style="color:var(--accent)">${d.count}</b></span>
      </div>
    </div>`;
}

loadData();
setInterval(loadData, 10000);
