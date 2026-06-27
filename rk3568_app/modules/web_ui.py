"""
Web 管理仪表盘 — 专业级航空风格。
零外部依赖，基于 Python 标准库 http.server。
功能：心跳脉冲、告警弹窗、连接健康面板、事件日志、配置管理、指令下发。
"""
import json
import logging
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ANMK8639 机库控制台</title>
<style>
:root {
  --bg: #0d1117;
  --panel: #161b22;
  --border: #21262d;
  --text: #c9d1d9;
  --dim: #8b949e;
  --green: #3fb950;
  --yellow: #d2991d;
  --red: #da3633;
  --blue: #58a6ff;
  --accent: #1f6feb;
  --toast-bg: #161b22;
}
*{margin:0;padding:0;box-sizing:border-box}
body{font:13px/1.5 'Segoe UI','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;overflow-x:hidden}

/* ===== TOP BAR ===== */
#topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:10px 20px;background:var(--panel);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;
}
#topbar .title{display:flex;align-items:center;gap:12px}
#topbar h1{font-size:16px;font-weight:600;letter-spacing:0.5px}
#topbar h1 span{color:var(--blue)}

/* heartbeat pulse */
.hb-dot{
  width:14px;height:14px;border-radius:50%;position:relative;
}
.hb-dot::after{
  content:'';position:absolute;inset:-4px;border-radius:50%;
  animation:pulse 1.2s ease-in-out infinite;
}
.hb-dot.ok{background:var(--green)}
.hb-dot.ok::after{border:2px solid var(--green)}
.hb-dot.warn{background:var(--yellow)}
.hb-dot.warn::after{border:2px solid var(--yellow)}
.hb-dot.bad{background:var(--red)}
.hb-dot.bad::after{border:2px solid var(--red)}
@keyframes pulse{
  0%{transform:scale(1);opacity:1}
  100%{transform:scale(2.2);opacity:0}
}
#uptime-display{font-size:12px;color:var(--dim);font-family:monospace}

/* ===== NAV ===== */
nav{display:flex;gap:0;padding:0 20px;background:var(--panel);border-bottom:1px solid var(--border)}
nav button{
  padding:10px 18px;border:none;background:none;color:var(--dim);
  cursor:pointer;font-size:13px;border-bottom:2px solid transparent;
  transition:all .15s;
}
nav button:hover{color:var(--text)}
nav button.active{color:var(--blue);border-bottom-color:var(--blue)}

/* ===== MAIN ===== */
main{padding:20px;max-width:1400px;margin:0 auto}
.tab{display:none}
.tab.active{display:block}
.grid2{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:900px){.grid4{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.grid3{grid-template-columns:repeat(2,1fr)}}

/* ===== CARDS ===== */
.card{
  background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:16px;
}
.card h3{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.card .val{font-size:28px;font-weight:600;font-family:monospace}
.card .sub{font-size:11px;color:var(--dim);margin-top:4px}
.card .fresh{font-size:10px;margin-top:4px;font-family:monospace}
.card .fresh.live{color:var(--green)}
.card .fresh.stale{color:var(--yellow)}
.card .fresh.dead{color:var(--red)}

/* health cards */
.hcard{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:14px;display:flex;align-items:center;gap:12px}
.hcard .icon{font-size:24px}
.hcard .info{flex:1}
.hcard .info .name{font-size:13px;font-weight:600}
.hcard .info .ago{font-size:11px;color:var(--dim);font-family:monospace}
.hcard .status-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.hcard .status-dot.on{background:var(--green);box-shadow:0 0 8px var(--green)}
.hcard .status-dot.off{background:var(--red);box-shadow:0 0 8px var(--red)}
.hcard .status-dot.idle{background:var(--yellow)}

/* ===== EVENT LOG ===== */
.ev-log{background:var(--panel);border:1px solid var(--border);border-radius:8px;max-height:500px;overflow-y:auto;font-family:monospace;font-size:12px}
.ev-row{display:flex;padding:6px 12px;border-bottom:1px solid var(--border);gap:10px;align-items:flex-start}
.ev-row:last-child{border-bottom:none}
.ev-row .ev-ts{color:var(--dim);white-space:nowrap;min-width:85px}
.ev-row .ev-src{color:var(--blue);min-width:60px;text-align:center;font-weight:600}
.ev-row .ev-lvl{min-width:42px;text-align:center;font-weight:700;font-size:11px}
.ev-row .ev-lvl.info{color:var(--blue)}
.ev-row .ev-lvl.warn{color:var(--yellow)}
.ev-row .ev-lvl.error{color:var(--red)}
.ev-row .ev-msg{flex:1;word-break:break-all}

/* ===== ALERT TOAST ===== */
#toasts{position:fixed;top:60px;right:20px;z-index:999;display:flex;flex-direction:column;gap:8px;max-width:380px}
.toast{
  background:var(--toast-bg);border:1px solid var(--border);border-radius:8px;
  padding:12px 16px;box-shadow:0 8px 24px rgba(0,0,0,.5);
  animation:slideIn .3s ease;position:relative;overflow:hidden;
}
.toast .toast-bar{position:absolute;top:0;left:0;width:4px;height:100%}
.toast.warn .toast-bar{background:var(--yellow)}
.toast.error .toast-bar{background:var(--red)}
.toast.info .toast-bar{background:var(--blue)}
.toast .toast-title{font-weight:600;font-size:13px;margin-bottom:2px}
.toast .toast-msg{font-size:12px;color:var(--dim)}
.toast .toast-close{position:absolute;top:6px;right:10px;cursor:pointer;color:var(--dim);font-size:14px}
@keyframes slideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}

/* ===== TABLES / FORMS ===== */
table{width:100%;border-collapse:collapse}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--border)}
th{color:var(--dim);font-weight:500;font-size:11px;text-transform:uppercase}
textarea,select,input{
  width:100%;background:var(--bg);border:1px solid var(--border);
  color:var(--text);padding:10px;border-radius:6px;font-family:monospace;font-size:13px
}
textarea{height:400px;resize:vertical}
.btn{
  padding:8px 20px;border:none;border-radius:6px;cursor:pointer;font-size:13px;
  font-weight:500;transition:all .15s;margin-right:8px;margin-top:10px
}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:#388bfd}
.btn-danger{background:var(--red);color:#fff}
.btn-secondary{background:var(--border);color:var(--text)}
.btn-secondary:hover{background:#30363d}
.msg{padding:10px;margin-top:10px;border-radius:6px;display:none}
.msg.success{background:#0d3320;color:var(--green);display:block}
.msg.error{background:#3d1616;color:var(--red);display:block}

/* ===== GAUGES ===== */
.gauge-row{display:flex;gap:20px;align-items:center;margin:10px 0}
.gauge-label{font-size:12px;color:var(--dim);width:70px}
.gauge-bar{flex:1;height:8px;background:var(--border);border-radius:4px;overflow:hidden}
.gauge-fill{height:100%;border-radius:4px;transition:width .5s}
.gauge-fill.ok{background:var(--green)}
.gauge-fill.warn{background:var(--yellow)}
.gauge-fill.bad{background:var(--red)}
footer{text-align:center;padding:20px;color:var(--dim);font-size:11px;border-top:1px solid var(--border);margin-top:30px}
</style>
</head>
<body>

<!-- TOP BAR -->
<div id="topbar">
<div class="title">
  <div class="hb-dot ok" id="hb-dot" title="系统心跳"></div>
  <h1>ANMK<span>8639</span> 机库控制台</h1>
</div>
<div id="uptime-display">运行中...</div>
</div>

<!-- NAV -->
<nav>
<button class="active" onclick="switchTab('status',this)">📊 总览</button>
<button onclick="switchTab('drone',this)">🛸 无人机</button>
<button onclick="switchTab('hangar',this)">🏠 机库</button>
<button onclick="switchTab('events',this)">📋 事件</button>
<button onclick="switchTab('config',this)">⚙️ 配置</button>
<button onclick="switchTab('cmd',this)">🎮 控制</button>
<button onclick="switchTab('logs',this)">📜 日志</button>
</nav>

<!-- TOAST CONTAINER -->
<div id="toasts"></div>

<main>

<!-- TAB: 总览 -->
<div id="tab-status" class="tab active">
  <h3 style="margin-bottom:12px;color:var(--dim);text-transform:uppercase;font-size:12px">🔗 连接健康</h3>
  <div class="grid4" id="health-cards"></div>
  <h3 style="margin:20px 0 12px;color:var(--dim);text-transform:uppercase;font-size:12px">📡 无人机摘要</h3>
  <div class="grid3" id="drone-summary"></div>
  <h3 style="margin:20px 0 12px;color:var(--dim);text-transform:uppercase;font-size:12px">🏠 机库摘要</h3>
  <div class="grid3" id="hangar-summary"></div>
</div>

<!-- TAB: 无人机 -->
<div id="tab-drone" class="tab">
<div class="grid3" id="drone-detail"></div>
<div style="margin-top:16px"><div class="card"><h3>GPS 卫星</h3><div class="gauge-row" id="gps-gauge"></div></div></div>
</div>

<!-- TAB: 机库 -->
<div id="tab-hangar" class="tab">
<div class="grid3" id="hangar-detail"></div>
</div>

<!-- TAB: 事件 -->
<div id="tab-events" class="tab">
<div style="display:flex;gap:10px;align-items:center;margin-bottom:12px">
  <select id="ev-filter" onchange="loadEvents()" style="width:auto">
    <option value="all">全部级别</option>
    <option value="info">INFO</option>
    <option value="warn">WARN</option>
    <option value="error">ERROR</option>
  </select>
  <button class="btn btn-secondary" onclick="loadEvents()">🔄 刷新</button>
</div>
<div class="ev-log" id="ev-log"></div>
</div>

<!-- TAB: 配置 -->
<div id="tab-config" class="tab">
<h3>config.yaml</h3>
<textarea id="config-text" spellcheck="false"></textarea>
<div id="config-msg" class="msg"></div>
<button class="btn btn-primary" onclick="saveConfig()">💾 保存配置</button>
<button class="btn btn-secondary" onclick="loadConfig()">🔄 重新加载</button>
<button class="btn btn-danger" onclick="restartService()">🔃 重启服务</button>
</div>

<!-- TAB: 控制 -->
<div id="tab-cmd" class="tab">
<h3>STM32 指令下发</h3>
<table>
<tr><td>开门：</td><td><button class="btn btn-primary" onclick="sendCmd('OPEN_DOOR')">🚪 开舱门</button></td></tr>
<tr><td>关门：</td><td><button class="btn btn-primary" onclick="sendCmd('CLOSE_DOOR')">🚪 关舱门</button></td></tr>
<tr><td>上锁：</td><td><button class="btn btn-primary" onclick="sendCmd('LOCK')">🔐 上锁</button></td></tr>
<tr><td>解锁：</td><td><button class="btn btn-primary" onclick="sendCmd('UNLOCK')">🔓 解锁</button></td></tr>
</table>
<div id="cmd-msg" class="msg"></div>
</div>

<!-- TAB: 日志 -->
<div id="tab-logs" class="tab">
<h3>最近日志 (app.log)</h3>
<div class="ev-log" id="log-content" style="white-space:pre-wrap">加载中...</div>
</div>

</main>
<footer>ANMK8639 Hangar Control System &copy; 2026 — RK3568 + STM32H743</footer>

<script>
// ============ GLOBALS ============
var lastAlerts = {};
var prevHealth = '';
var TOAST_TIMEOUT = 8000;

// ============ TABS ============
// v2 - onclick+this 模式，最大兼容性
window.onerror = function(msg,url,line){
  document.getElementById('uptime-display').textContent = 'JS ERROR: '+msg+' L'+line;
};

function switchTab(name, btn){
  if(!btn) return;
  var tabs = document.querySelectorAll('.tab');
  for(var i=0;i<tabs.length;i++) tabs[i].classList.remove('active');
  var tab = document.getElementById('tab-'+name);
  if(tab) tab.classList.add('active');
  var buttons = document.querySelectorAll('nav button');
  for(var j=0;j<buttons.length;j++) buttons[j].classList.remove('active');
  btn.classList.add('active');
  try{if(name==='events') loadEvents();}catch(e){}
  try{if(name==='config') loadConfig();}catch(e){}
  try{if(name==='logs') loadLogs();}catch(e){}
}

// ============ API ============
async function api(path, opts){
  opts = opts || {};
  try{
    var r = await fetch(path, opts);
    if(!r.ok) return null;
    return await r.json();
  }catch(e){return null;}
}

// ============ HEALTH CARDS ============
function renderHealth(h){
  h = h || {};
  var cards = document.getElementById('health-cards');
  var items = [
    {icon:'🛸',name:'MAVLink 无人机',key:'mavlink',fields:['connected','last_hb_sec']},
    {icon:'📡',name:'MQTT 地面站',key:'mqtt',fields:['connected','last_msg_sec']},
    {icon:'🔌',name:'STM32 下位机',key:'stm32',fields:['connected','last_status_sec']},
    {icon:'📷',name:'摄像头',key:'camera',fields:['last_snapshot_sec']},
  ];
  var html = '';
  for(var i=0;i<items.length;i++){
    var it = items[i];
    var d = h[it.key] || {};
    var conn = (d.connected !== undefined) ? d.connected : (d.last_snapshot_sec !== undefined ? (d.last_snapshot_sec !== null) : null);
    var cs = 'off', label = '离线', ago = '';
    if(conn === true){cs = 'on'; label = '在线';}
    else if(conn === false){cs = 'off'; label = '离线';}
    else{cs = 'idle'; label = '未启用';}
    if(d.last_hb_sec !== undefined && d.last_hb_sec !== null) ago = fmtAge(d.last_hb_sec);
    else if(d.last_msg_sec !== undefined && d.last_msg_sec !== null) ago = fmtAge(d.last_msg_sec);
    else if(d.last_status_sec !== undefined && d.last_status_sec !== null) ago = fmtAge(d.last_status_sec);
    else if(d.last_snapshot_sec !== undefined && d.last_snapshot_sec !== null) ago = fmtAge(d.last_snapshot_sec);
    html += '<div class="hcard">'+
      '<div class="icon">'+it.icon+'</div>'+
      '<div class="info"><div class="name">'+it.name+'</div><div class="ago">'+(ago||label)+'</div></div>'+
      '<div class="status-dot '+cs+'"></div>'+
      '</div>';
  }
  cards.innerHTML = html;

  var dot = document.getElementById('hb-dot');
  dot.className = 'hb-dot ' + (h.overall==='healthy'?'ok':h.overall==='degraded'?'warn':'bad');

  document.getElementById('uptime-display').textContent = '运行 ' + fmtUptime(h.uptime||0);
}

function fmtAge(sec){
  if(sec === null || sec === undefined) return '--';
  if(sec < 2) return '刚刚';
  if(sec < 60) return Math.floor(sec) + '秒前';
  if(sec < 3600) return Math.floor(sec/60) + '分' + Math.floor(sec%60) + '秒前';
  return Math.floor(sec/3600) + '小时前';
}

function fmtUptime(sec){
  var d = Math.floor(sec/86400), h = Math.floor((sec%86400)/3600), m = Math.floor((sec%3600)/60), s = Math.floor(sec%60);
  var p = [];
  if(d>0) p.push(d+'天');
  if(h>0) p.push(h+'时');
  if(m>0) p.push(m+'分');
  p.push(s+'秒');
  return p.join(' ');
}

// ============ DRONE SUMMARY ============
function renderDroneSummary(s){
  var d = (s && s.drone) ? s.drone : {};
  var bat = d.battery_remaining || 0;
  document.getElementById('drone-summary').innerHTML =
    cardV('飞行模式', d.flight_mode||'UNKNOWN', d.armed?'🔴 武装':'⚪ 解除')+
    cardV('电池', bat+'%', '电压: '+(d.battery_voltage||0).toFixed(1)+'V', bat>20?'green':(bat>5?'yellow':'red'))+
    cardV('GPS', d.gps_fix>=3?'3D定位':'无定位', '卫星: '+(d.satellites||0), d.gps_fix>=3?'green':'red');
}

function renderHangarSummary(s){
  var h = (s && s.hangar) ? s.hangar : {};
  document.getElementById('hangar-summary').innerHTML =
    cardV('舱门', h.door_status||'UNKNOWN', '', h.door_status==='CLOSED'?'green':'yellow')+
    cardV('锁定', h.lock_status||'UNKNOWN', '', h.lock_status==='LOCKED'?'green':'yellow')+
    cardV('温度', h.temperature ? h.temperature.toFixed(1)+'°C' : '--',
          '湿度: '+(h.humidity ? h.humidity.toFixed(1)+'%' : '--'),
          h.temperature>50?'red':(h.temperature>35?'yellow':'green'));
}

// ============ DRONE DETAIL ============
function renderDroneDetail(s){
  var d = (s && s.drone) ? s.drone : {};
  document.getElementById('drone-detail').innerHTML =
    cardV('纬度', d.lat ? d.lat.toFixed(6) : '--')+
    cardV('经度', d.lon ? d.lon.toFixed(6) : '--')+
    cardV('高度(相对)', d.alt ? d.alt.toFixed(1)+' m' : '--')+
    cardV('航向', d.heading ? d.heading+'°' : '--')+
    cardV('地速', d.groundspeed ? d.groundspeed.toFixed(1)+' m/s' : '--')+
    cardV('爬升率', d.climb_rate ? d.climb_rate.toFixed(1)+' m/s' : '--')+
    cardV('空速', d.airspeed ? d.airspeed.toFixed(1)+' m/s' : '--')+
    cardV('姿态(R/P/Y)', d.roll!==undefined ? d.roll.toFixed(1)+'/'+d.pitch.toFixed(1)+'/'+d.yaw.toFixed(1) : '--')+
    cardV('当前航点', 'WP '+(d.wp_current||0));
  var sats = d.satellites || 0;
  var pct = Math.min(100, sats*5);
  var gps = document.getElementById('gps-gauge');
  gps.innerHTML = '<span class="gauge-label">卫星 '+sats+'</span><div class="gauge-bar"><div class="gauge-fill '+(sats>=12?'ok':(sats>=6?'warn':'bad'))+'" style="width:'+pct+'%"></div></div>';
}

// ============ HANGAR DETAIL ============
function renderHangarDetail(s){
  var h = (s && s.hangar) ? s.hangar : {};
  var alarmFlags = h.alarm_flags || 0;
  var alarmText = '无告警';
  var hasAlarm = false;
  if(alarmFlags){
    hasAlarm = true;
    var flags = [];
    if(alarmFlags & 0x0001) flags.push('烟雾');
    if(alarmFlags & 0x0002) flags.push('高温');
    if(alarmFlags & 0x0004) flags.push('门异常');
    if(alarmFlags & 0x0008) flags.push('锁异常');
    if(alarmFlags & 0x0010) flags.push('电源异常');
    alarmText = flags.join(', ');
  }
  document.getElementById('hangar-detail').innerHTML =
    cardV('舱门状态', h.door_status||'UNKNOWN', '', h.door_status==='CLOSED'?'green':(h.door_status==='OPEN'?'yellow':'red'))+
    cardV('锁定状态', h.lock_status||'UNKNOWN', '', h.lock_status==='LOCKED'?'green':'red')+
    cardV('机库温度', h.temperature ? h.temperature.toFixed(1)+'°C' : '--')+
    cardV('机库湿度', h.humidity ? h.humidity.toFixed(1)+'%' : '--')+
    cardV(hasAlarm ? '⚠️ 告警' : '✅ 正常', alarmText, 'flags=0x'+alarmFlags.toString(16).toUpperCase(), hasAlarm?'red':'green');
}

function cardV(label, value, sub, color){
  color = color || '';
  return '<div class="card"><h3>'+label+'</h3><div class="val '+color+'">'+value+'</div>'+(sub?'<div class="sub">'+sub+'</div>':'')+'</div>';
}

// ============ EVENTS ============
async function loadEvents(){
  var filterEl = document.getElementById('ev-filter');
  var filter = filterEl ? filterEl.value : 'all';
  var data = await api('/api/events?count=100');
  var logEl = document.getElementById('ev-log');
  if(!data || !data.events){logEl.innerHTML='<div class="ev-row"><span style="color:var(--dim)">加载失败</span></div>';return;}
  var events = data.events || [];
  if(filter!=='all') events = events.filter(function(e){return e.level===filter;});
  logEl.innerHTML = events.map(function(e){
    var d = new Date(e.ts*1000);
    var ts = d.toLocaleTimeString('zh-CN',{hour12:false});
    return '<div class="ev-row">'+
      '<span class="ev-ts">'+ts+'</span>'+
      '<span class="ev-src">'+esc(e.source)+'</span>'+
      '<span class="ev-lvl '+e.level+'">'+e.level.toUpperCase()+'</span>'+
      '<span class="ev-msg">'+esc(e.message)+'</span>'+
      '</div>';
  }).join('')||'<div class="ev-row"><span style="color:var(--dim)">暂无事件</span></div>';
}

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// ============ ALERT TOASTS ============
function showToast(level, title, msg){
  var id = 't'+Date.now()+Math.random();
  var el = document.createElement('div');
  el.className = 'toast ' + level;
  el.id = id;
  var bar = document.createElement('div');
  bar.className = 'toast-bar';
  el.appendChild(bar);
  var tEl = document.createElement('div');
  tEl.className = 'toast-title';
  tEl.textContent = title;
  el.appendChild(tEl);
  var mEl = document.createElement('div');
  mEl.className = 'toast-msg';
  mEl.textContent = msg;
  el.appendChild(mEl);
  var btn = document.createElement('span');
  btn.className = 'toast-close';
  btn.textContent = '✕';
  btn.onclick = function(){ dismissToast(id); };
  el.appendChild(btn);
  document.getElementById('toasts').appendChild(el);
  setTimeout(function(){dismissToast(id);}, TOAST_TIMEOUT);
}

function dismissToast(id){
  var el = document.getElementById(id);
  if(el) el.remove();
}

// ============ HEALTH POLLING + ALERT DETECTION ============
async function pollHealth(){
  var h = await api('/api/health');
  if(!h) return;
  renderHealth(h);

  var s = await api('/api/status');
  if(s){
    renderDroneSummary(s);
    renderHangarSummary(s);
    renderDroneDetail(s);
    renderHangarDetail(s);
  }

  // detect connection changes for toasts
  if(h.mavlink && !h.mavlink.connected && lastAlerts['mavlink'] !== 'off'){
    showToast('error', '🛸 无人机断联', 'MAVLink连接丢失，请检查4G模块');
    lastAlerts['mavlink'] = 'off';
  }
  if(h.mavlink && h.mavlink.connected && lastAlerts['mavlink'] === 'off'){
    showToast('info', '🛸 无人机已恢复', 'MAVLink连接已恢复');
    lastAlerts['mavlink'] = 'on';
  }
  if(h.mavlink && h.mavlink.connected) lastAlerts['mavlink'] = 'on';

  if(h.stm32 && !h.stm32.connected && lastAlerts['stm32'] !== 'off'){
    showToast('error', '🔌 STM32断联', '下位机串口通信丢失');
    lastAlerts['stm32'] = 'off';
  }
  if(h.stm32 && h.stm32.connected && lastAlerts['stm32'] === 'off'){
    showToast('info', '🔌 STM32已恢复', '下位机串口通信已恢复');
    lastAlerts['stm32'] = 'on';
  }
  if(h.stm32 && h.stm32.connected) lastAlerts['stm32'] = 'on';

  if(prevHealth && prevHealth !== h.overall){
    if(h.overall === 'critical') showToast('error', '⚠️ 系统异常', '多个模块离线，请立即检查');
    else if(h.overall === 'degraded') showToast('warn', '⚠️ 系统降级', '部分模块离线');
    else if(h.overall === 'healthy') showToast('info', '✅ 系统正常', '所有模块运行正常');
  }
  prevHealth = h.overall;
}

// ============ CONFIG ============
async function loadConfig(){
  var d = await api('/api/config');
  if(d && d.raw) document.getElementById('config-text').value = d.raw;
}
async function saveConfig(){
  var raw = document.getElementById('config-text').value;
  var r = await api('/api/config', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({raw:raw})});
  var m = document.getElementById('config-msg');
  m.className = 'msg ' + (r && r.ok ? 'success' : 'error');
  m.textContent = r ? (r.ok ? '配置已保存 (需重启生效)' : '保存失败: '+r.error) : '请求失败';
}
async function restartService(){
  await api('/api/restart', {method:'POST'});
  showToast('info', '重启', '请手动执行: sudo systemctl restart hangar');
}

// ============ COMMAND ============
async function sendCmd(cmd){
  var r = await api('/api/command', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({cmd:cmd})});
  var m = document.getElementById('cmd-msg');
  m.className = 'msg ' + (r && r.ok ? 'success' : 'error');
  m.textContent = r ? (r.ok ? '指令 '+cmd+' 已发送' : '发送失败: '+r.error) : '请求失败';
}

// ============ LOGS ============
async function loadLogs(){
  var d = await api('/api/logs');
  if(d) document.getElementById('log-content').textContent = d.lines;
}

// ============ INIT ============
setInterval(pollHealth, 2000);
pollHealth();
setInterval(loadEvents, 5000);
</script>
</body>
</html>"""


class WebUI:
    """嵌入式 HTTP 服务器，提供专业级管理仪表盘。"""

    def __init__(self, config: dict, app_state, event_bus, stm32_comm=None):
        self._host = config.get("host", "0.0.0.0")
        self._port = config.get("port", 8080)
        self._app_state = app_state
        self._event_bus = event_bus
        self._stm32 = stm32_comm
        self._server = None

    def start(self):
        handler = self._make_handler()
        self._server = HTTPServer((self._host, self._port), handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        logger.info("Web UI ready: http://%s:%d", self._host, self._port)
        self._app_state.log_event("webui", "info", "Web仪表盘已启动: http://" + self._host + ":" + str(self._port))

    def stop(self):
        if self._server:
            self._server.shutdown()
        logger.info("Web UI stopped")

    def _make_handler(self):
        ui = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                logger.debug("HTTP %s", args[0] if args else fmt)

            def _json(self, data, code=200):
                body = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json;charset=utf-8")
                self.send_header("Content-Length", len(body))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html;charset=utf-8")
                    self.end_headers()
                    self.wfile.write(DASHBOARD_HTML.encode())
                elif path == "/api/status":
                    self._json(ui._app_state.to_dict())
                elif path == "/api/health":
                    self._json(ui._app_state.health())
                elif path == "/api/events":
                    qs = parse_qs(urlparse(self.path).query)
                    count = int(qs.get("count", [50])[0])
                    self._json({"events": ui._app_state.get_events(count)})
                elif path == "/api/config":
                    try:
                        with open("config.yaml", "r", encoding="utf-8") as f:
                            raw = f.read()
                        self._json({"raw": raw})
                    except Exception as e:
                        self._json({"error": str(e)}, 500)
                elif path == "/api/logs":
                    try:
                        log_dir = "./data/logs"
                        files = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")])
                        if files:
                            with open(os.path.join(log_dir, files[-1]), "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            self._json({"lines": "".join(lines[-80:])})
                        else:
                            self._json({"lines": "(无日志)"})
                    except Exception as e:
                        self._json({"error": str(e)}, 500)
                else:
                    self._json({"error": "not found"}, 404)

            def do_POST(self):
                path = urlparse(self.path).path
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}

                if path == "/api/command":
                    cmd = body.get("cmd", "")
                    cmd_map = {"OPEN_DOOR": 0x01, "CLOSE_DOOR": 0x02, "LOCK": 0x03, "UNLOCK": 0x04}
                    code = cmd_map.get(cmd)
                    if code is not None and ui._stm32:
                        ui._stm32.send_command(code)
                        ui._app_state.log_event("webui", "info", "用户下发指令: " + cmd)
                        self._json({"ok": True, "cmd": cmd})
                    else:
                        self._json({"ok": False, "error": "unknown cmd or STM32 offline"})

                elif path == "/api/config":
                    raw = body.get("raw", "")
                    try:
                        with open("config.yaml", "w", encoding="utf-8") as f:
                            f.write(raw)
                        ui._app_state.log_event("webui", "info", "用户更新了配置文件")
                        self._json({"ok": True})
                    except Exception as e:
                        self._json({"ok": False, "error": str(e)})

                elif path == "/api/restart":
                    ui._app_state.log_event("webui", "warn", "用户请求重启服务")
                    self._json({"ok": True, "msg": "请手动执行: sudo systemctl restart hangar"})

                else:
                    self._json({"error": "not found"}, 404)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

        return Handler
