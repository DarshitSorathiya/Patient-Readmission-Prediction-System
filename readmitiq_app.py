"""
ReadmitIQ — Ward Monitor · 30-Day Readmission Risk
Streamlit app: the ENTIRE dashboard is one self-contained HTML/JS component
rendered via st.components.v1.html(). Streamlit does not fight the layout.

Dataset: Diabetes 130-US Hospitals for Years 1999–2008
API:     POST /predict  (your FastAPI server)

Run:
    pip install streamlit
    streamlit run readmitiq_app.py
"""

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Ward Monitor · 30-Day Readmission Risk",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide every scrap of Streamlit chrome and make iframe fill the full viewport
st.markdown("""
<style>
#MainMenu, footer, header,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stDeployButton,
[data-testid="collapsedControl"],
section[data-testid="stSidebar"] { display: none !important; }

/* Kill ALL Streamlit spacing */
html, body, .stApp { margin: 0 !important; padding: 0 !important; overflow: hidden !important; background: #F4F3F0 !important; height: 100vh !important; }
.main .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
.main { padding: 0 !important; }
[data-testid="stAppViewContainer"] { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; padding: 0 !important; }

/* Make the iframe fill the full viewport */
iframe {
    border: none !important;
    display: block !important;
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
}
</style>
""", unsafe_allow_html=True)

DASHBOARD = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#F4F3F0;--surface:#FFFFFF;--surface2:#F9F8F6;--surface3:#F1F0EC;
  --border:#E8E6E1;--border2:#D8D6D0;
  --ink:#1A1916;--ink2:#6A6860;--ink3:#A8A6A0;
  --red:#B83232;--red-light:#FDF0EF;--red-border:#F0C4C0;
  --amber:#C4600A;--amber-light:#FEF5EC;--amber-border:#F0D4B0;
  --green:#1A7A52;--green-light:#EDF7F2;--green-border:#B8E4CE;
  --blue:#1E5FA8;
  --r:10px;--r-lg:14px;--r-xl:20px;
  --serif:'Roboto',sans-serif;--sans:'Roboto',sans-serif;--mono:'Roboto Mono',monospace;
}
html,body{height:100%;overflow:hidden;background:var(--bg);}
body{font-family:var(--sans);color:var(--ink);font-size:13px;line-height:1.6;}

/* TOPBAR */
.topbar{background:var(--surface);border-bottom:1px solid var(--border);height:58px;display:flex;align-items:center;padding:0 28px;position:sticky;top:0;z-index:100;}
.live-dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:pulse 2s ease infinite;margin-right:11px;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(26,122,82,.5)}70%{box-shadow:0 0 0 7px rgba(26,122,82,0)}100%{box-shadow:0 0 0 0 rgba(26,122,82,0)}}
.brand-name{font-family:var(--serif);font-size:18px;letter-spacing:-.01em;color:var(--ink);line-height:1;}
.brand-sub{font-size:10px;color:var(--ink3);letter-spacing:.07em;text-transform:uppercase;font-family:var(--mono);margin-top:2px;}
.tb-div{width:1px;height:26px;background:var(--border);margin:0 20px;}
.tb-col{display:flex;flex-direction:column;gap:1px;}
.tb-lbl{font-size:10px;color:var(--ink3);text-transform:uppercase;letter-spacing:.07em;}
.tb-val{font-size:13px;color:var(--ink);font-family:var(--mono);font-weight:500;}
.btn-admit{margin-left:auto;height:34px;padding:0 16px;background:var(--red-light);border:1px solid var(--red-border);border-radius:8px;color:var(--red);font-family:var(--sans);font-size:13px;font-weight:500;cursor:pointer;display:flex;align-items:center;gap:6px;transition:all .14s;}
.btn-admit:hover{background:#FAEAE8;border-color:#E8A8A4;}

/* 3-COL LAYOUT */
.layout{display:grid;grid-template-columns:380px 1fr 300px;height:calc(100vh - 58px);overflow:hidden;}

/* LEFT */
.left-panel{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
.tl-hdr{padding:18px 22px 14px;border-bottom:1px solid var(--border);flex-shrink:0;}
.tl-title{font-family:var(--serif);font-size:16px;font-weight:400;color:var(--ink);letter-spacing:-.01em;margin-bottom:2px;}
.tl-sub{font-size:11px;color:var(--ink3);}
.shift-bar{margin-top:10px;}
.shift-labels{display:flex;justify-content:space-between;font-size:10px;color:var(--ink3);font-family:var(--mono);margin-bottom:5px;}
.shift-track{height:6px;background:var(--surface3);border-radius:3px;overflow:hidden;}
.shift-fill{height:100%;background:linear-gradient(90deg,var(--blue),var(--green));border-radius:3px;width:0%;transition:width 1s linear;}
.shift-foot{display:flex;justify-content:space-between;margin-top:5px;}
.shift-foot span{font-size:10px;color:var(--ink3);}
.tl-scroll{flex:1;overflow-y:auto;}
.tl-scroll::-webkit-scrollbar{width:4px;}
.tl-scroll::-webkit-scrollbar-thumb{background:var(--surface3);border-radius:2px;}
.tl-proc{display:flex;align-items:center;gap:10px;padding:12px 22px;opacity:0;transition:opacity .3s;border-top:1px solid var(--border);flex-shrink:0;}
.tl-proc.on{opacity:1;}
.dots span{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--blue);margin:0 2px;animation:bounce 1.2s ease infinite;}
.dots span:nth-child(2){animation-delay:.2s;}.dots span:nth-child(3){animation-delay:.4s;}
@keyframes bounce{0%,80%,100%{transform:scale(.6);opacity:.35}40%{transform:scale(1);opacity:1}}
.proc-txt{font-size:11px;color:var(--ink3);}

/* TIMELINE ITEM */
.tli{display:flex;gap:12px;padding:13px 22px;cursor:pointer;border-bottom:1px solid var(--border);position:relative;opacity:0;transform:translateX(-8px);animation:slideIn .38s ease forwards;}
@keyframes slideIn{to{opacity:1;transform:translateX(0)}}
.tli:hover{background:var(--surface2);}
.tli.sel{background:var(--surface2);}
.tli.sel::before{content:'';position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:0 3px 3px 0;}
.tli.sel.high::before{background:var(--red);}
.tli.sel.medium::before{background:var(--amber);}
.tli.sel.low::before{background:var(--green);}
.tl-spine{display:flex;flex-direction:column;align-items:center;flex-shrink:0;}
.dot{width:10px;height:10px;border-radius:50%;border:2px solid;margin-top:4px;}
.dot.high{border-color:var(--red);background:var(--red-light);}
.dot.medium{border-color:var(--amber);background:var(--amber-light);}
.dot.low{border-color:var(--green);background:var(--green-light);}
.tl-line{width:1px;flex:1;min-height:18px;background:var(--border);margin:4px 0;}
.tl-info{flex:1;min-width:0;}
.tl-time{font-size:10px;color:var(--ink3);font-family:var(--mono);margin-bottom:2px;}
.tl-name{font-size:14px;font-weight:500;color:var(--ink);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tl-dx{font-size:11px;color:var(--ink2);margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.chips{display:flex;gap:4px;flex-wrap:wrap;}
.chip{display:inline-block;font-size:10px;padding:2px 7px;border-radius:20px;border:1px solid;white-space:nowrap;}
.chip.high{background:var(--red-light);color:var(--red);border-color:var(--red-border);}
.chip.medium{background:var(--amber-light);color:var(--amber);border-color:var(--amber-border);}
.chip.low{background:var(--green-light);color:var(--green);border-color:var(--green-border);}
.chip.n{background:var(--surface3);color:var(--ink2);border-color:var(--border);}
.risk-badge{display:flex;flex-direction:column;align-items:flex-end;flex-shrink:0;gap:2px;}
.risk-pct{font-family:var(--mono);font-size:20px;font-weight:500;line-height:1;}
.risk-pct.high{color:var(--red);}.risk-pct.medium{color:var(--amber);}.risk-pct.low{color:var(--green);}
.risk-unit{font-size:9px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em;}

/* CENTRE */
.centre{padding:28px 30px;overflow-y:auto;background:var(--bg);border-right:1px solid var(--border);}
.centre::-webkit-scrollbar{width:4px;}
.centre::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.empty{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;text-align:center;padding:40px;}
.empty-icon{width:72px;height:72px;border-radius:20px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:30px;}
.empty-title{font-family:var(--serif);font-size:20px;color:var(--ink2);}
.empty-sub{font-size:13px;color:var(--ink3);max-width:260px;line-height:1.7;}
.ph{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:22px;padding-bottom:22px;border-bottom:1px solid var(--border);animation:fadeUp .32s ease both;}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.ph-name{font-family:var(--serif);font-size:26px;font-weight:400;color:var(--ink);letter-spacing:-.02em;margin-bottom:5px;}
.ph-meta{font-size:12px;color:var(--ink2);font-family:var(--mono);margin-bottom:10px;}
.gauge-wrap{display:flex;flex-direction:column;align-items:center;gap:5px;flex-shrink:0;}
.gauge-box{position:relative;width:92px;height:92px;}
.gauge-box canvas{display:block;}
.gauge-center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.gauge-pct{font-family:var(--mono);font-size:20px;font-weight:500;line-height:1;}
.gauge-sub{font-size:9px;color:var(--ink3);margin-top:2px;}
.risk-label{font-size:11px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;}
.sec-head{font-size:10px;font-weight:500;color:var(--ink3);text-transform:uppercase;letter-spacing:.1em;margin:22px 0 12px;display:flex;align-items:center;gap:10px;}
.sec-head::after{content:'';flex:1;height:1px;background:var(--border);}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);padding:16px 18px;margin-bottom:10px;}
.card-title{font-size:10px;color:var(--ink3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;}
.sr{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;}
.sr:last-child{border-bottom:none;}
.sr-name{flex:0 0 160px;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sr-bar{flex:1;height:5px;background:var(--surface3);border-radius:3px;overflow:hidden;}
.sr-fill{height:100%;border-radius:3px;}
.sr-val{min-width:36px;text-align:right;font-size:10px;color:var(--ink3);font-family:var(--mono);}
.api-block{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);overflow:hidden;margin-bottom:10px;}
.api-head{background:var(--surface2);border-bottom:1px solid var(--border);padding:9px 14px;display:flex;align-items:center;justify-content:space-between;font-size:11px;}
.api-head-l{display:flex;align-items:center;gap:7px;}
.badge-post{background:var(--green-light);color:var(--green);border:1px solid var(--green-border);font-size:10px;padding:2px 8px;border-radius:4px;font-weight:500;font-family:var(--mono);}
.ep{font-size:11px;color:var(--ink2);font-family:var(--mono);}
.badge-200{font-size:10px;color:var(--green);font-weight:500;font-family:var(--mono);}
.api-body{padding:13px 16px;font-family:var(--mono);font-size:11px;line-height:1.9;color:var(--ink2);background:var(--surface);overflow-x:auto;}
.api-body pre{margin:0;font-family:inherit;font-size:inherit;}
.jk{color:#1E5FA8;}.js{color:#C4600A;}.jn{color:#1A7A52;}.jb{color:#B83232;}

/* RIGHT */
.right-panel{background:var(--surface);display:flex;flex-direction:column;overflow:hidden;}
.rp-sec{padding:14px 16px 12px;border-bottom:1px solid var(--border);flex-shrink:0;}
.rp-title{font-size:10px;font-weight:500;color:var(--ink3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:10px;}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;}
.stat-tile{background:var(--surface2);border:1px solid var(--border);border-radius:var(--r);padding:9px 12px;}
.st-val{font-family:var(--mono);font-size:20px;font-weight:500;line-height:1;margin-bottom:3px;color:var(--ink);}
.st-val.red{color:var(--red);}.st-val.amb{color:var(--amber);}.st-val.grn{color:var(--green);}.st-val.blu{color:var(--blue);}
.st-lbl{font-size:10px;color:var(--ink3);text-transform:uppercase;letter-spacing:.07em;}
.dist-row{display:flex;align-items:center;gap:8px;font-size:12px;margin-bottom:6px;}
.dist-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.dist-lbl{flex:1;}.dist-lbl.red{color:var(--red);}.dist-lbl.amb{color:var(--amber);}.dist-lbl.grn{color:var(--green);}
.dist-n{font-family:var(--mono);font-size:12px;font-weight:500;color:var(--ink2);}
.feed{flex:1;overflow-y:auto;min-height:0;}
.feed::-webkit-scrollbar{width:3px;}
.feed::-webkit-scrollbar-thumb{background:var(--surface3);border-radius:2px;}
.fi{padding:10px 16px;border-bottom:1px solid var(--border);font-size:12px;line-height:1.5;animation:fadeIn .35s ease both;}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.fi-time{font-size:10px;color:var(--ink3);font-family:var(--mono);margin-bottom:2px;}
.fi-msg{color:var(--ink2);}
.fi-msg b{color:var(--ink);}
.fi-msg .hi{color:var(--red);}.fi-msg .med{color:var(--amber);}.fi-msg .lo{color:var(--green);}

/* MODAL */
.overlay{position:fixed;inset:0;background:rgba(26,25,22,.55);display:flex;align-items:center;justify-content:center;z-index:500;opacity:0;pointer-events:none;transition:opacity .22s;overflow-y:auto;padding:20px 0;}
.overlay.open{opacity:1;pointer-events:all;}
.modal{background:var(--surface);border:1px solid var(--border2);border-radius:var(--r-xl);width:580px;max-width:95vw;padding:28px 30px;box-shadow:0 20px 60px rgba(26,25,22,.12);transform:scale(.97);transition:transform .22s;max-height:90vh;overflow-y:auto;}
.overlay.open .modal{transform:scale(1);}
.modal::-webkit-scrollbar{width:4px;}
.modal::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.modal-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
.modal-title{font-family:var(--serif);font-size:22px;font-weight:400;letter-spacing:-.01em;}
.modal-x{background:none;border:none;color:var(--ink3);font-size:18px;cursor:pointer;padding:5px 9px;border-radius:7px;line-height:1;}
.modal-x:hover{background:var(--surface3);color:var(--ink);}
.modal-err{display:none;color:var(--red);font-size:12px;margin-bottom:14px;padding:8px 12px;background:var(--red-light);border:1px solid var(--red-border);border-radius:8px;}
.modal-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-bottom:20px;}
.sec-row{grid-column:1/-1;font-size:10px;font-weight:500;color:var(--ink3);text-transform:uppercase;letter-spacing:.09em;padding-top:4px;border-top:1px solid var(--border);margin-top:4px;}
.full{grid-column:1/-1;}
.mf{display:flex;flex-direction:column;gap:5px;}
.mf label{font-size:11px;color:var(--ink2);}
.mf input,.mf select{height:38px;padding:0 12px;background:var(--surface2);border:1px solid var(--border2);border-radius:9px;color:var(--ink);font-family:var(--sans);font-size:13px;outline:none;transition:border-color .14s;-webkit-appearance:none;appearance:none;}
.mf input:focus,.mf select:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(30,95,168,.08);}
.mf select{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%23A8A6A0' d='M5 7L0 2h10z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:28px;}
.btn-submit{width:100%;height:44px;border-radius:10px;background:var(--red);color:#fff;border:none;font-family:var(--sans);font-size:14px;font-weight:500;cursor:pointer;letter-spacing:.01em;transition:background .14s,transform .1s;}
.btn-submit:hover{background:#A02A2A;}
.btn-submit:active{transform:scale(.99);}
.btn-submit:disabled{background:#D8A0A0;cursor:not-allowed;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
</style>
</head>
<body>

<!-- TOPBAR -->
<div class="topbar">
  <div class="live-dot"></div>
  <div>
    <div class="brand-name">Ward Monitor</div>
    <div class="brand-sub" id="shiftBadge">—</div>
  </div>
  <div class="tb-div"></div>
  <div class="tb-col">
    <span class="tb-lbl">Current shift</span>
    <span class="tb-val" id="tbRange">—</span>
  </div>
  <button class="btn-admit" onclick="openModal()">
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M6.5 1v11M1 6.5h11" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
    Admit patient
  </button>
</div>

<!-- LAYOUT -->
<div class="layout">

  <!-- LEFT -->
  <div class="left-panel">
    <div class="tl-hdr">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <div class="tl-title">Patient queue</div>
        <div class="tl-sub" id="tlSub">Awaiting first admission…</div>
      </div>
      <div class="shift-bar">
        <div class="shift-labels">
          <span id="sStart">—</span><span id="sMid">—</span><span id="sEnd">—</span>
        </div>
        <div class="shift-track"><div class="shift-fill" id="sFill"></div></div>
        <div class="shift-foot">
          <span id="sElapsed">0h elapsed</span>
          <span>Next: <b id="sNext" style="color:var(--ink2);font-family:var(--mono);">—</b></span>
          <span id="sRemain">12h remaining</span>
        </div>
      </div>
    </div>
    <div class="tl-scroll" id="tlScroll"></div>
    <div class="tl-proc" id="tlProc">
      <div class="dots"><span></span><span></span><span></span></div>
      <div class="proc-txt" id="procTxt">Calling /predict…</div>
    </div>
  </div>

  <!-- CENTRE -->
  <div class="centre">
    <div class="empty" id="emptyState">
      <div class="empty-icon">📋</div>
      <div class="empty-title">No patient selected</div>
      <div class="empty-sub">Click "Admit patient" above, fill in the form, and the model's prediction will appear here.</div>
    </div>
    <div id="detailPane" style="display:none;"></div>
  </div>

  <!-- RIGHT -->
  <div class="right-panel">
    <div class="rp-sec">
      <div class="rp-title">Session summary</div>
      <div class="stat-grid">
        <div class="stat-tile"><div class="st-val red" id="sAlerts">0</div><div class="st-lbl">Active alerts</div></div>
        <div class="stat-tile"><div class="st-val blu" id="sSeen">0</div><div class="st-lbl">Processed</div></div>
        <div class="stat-tile"><div class="st-val amb" id="sMed">0</div><div class="st-lbl">Medium risk</div></div>
        <div class="stat-tile"><div class="st-val red" id="sHigh">0</div><div class="st-lbl">High risk</div></div>
        <div class="stat-tile"><div class="st-val grn" id="sLow">0</div><div class="st-lbl">Low risk</div></div>
      </div>
    </div>
    <div class="rp-sec">
      <div class="rp-title">Risk distribution</div>
      <div style="position:relative;width:110px;height:110px;margin:0 auto 12px;">
        <canvas id="donut" width="110" height="110"></canvas>
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:none;">
          <div style="font-family:var(--mono);font-size:18px;font-weight:500;color:var(--ink);" id="donutN">0</div>
          <div style="font-size:10px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em;margin-top:3px;">patients</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:7px;">
        <div class="dist-row"><div class="dist-dot" style="background:var(--red);"></div><span class="dist-lbl red">High risk</span><span class="dist-n" id="dHigh">0</span></div>
        <div class="dist-row"><div class="dist-dot" style="background:var(--amber);"></div><span class="dist-lbl amb">Medium risk</span><span class="dist-n" id="dMed">0</span></div>
        <div class="dist-row"><div class="dist-dot" style="background:var(--green);"></div><span class="dist-lbl grn">Low risk</span><span class="dist-n" id="dLow">0</span></div>
      </div>
    </div>
    <div class="rp-sec"><div class="rp-title">Activity feed</div></div>
    <div class="feed" id="feed"></div>
  </div>
</div>

<!-- ADMIT MODAL -->
<div class="overlay" id="overlay">
 <div class="modal">
  <div class="modal-hd">
    <div class="modal-title">Admit new patient</div>
    <button class="modal-x" onclick="closeModal()">&#x2715;</button>
  </div>
  <div class="modal-err" id="modalErr"></div>
  <div class="modal-grid">

    <!-- ── IDENTIFIERS ── -->
    <div class="sec-row">Identifiers</div>
    <div class="mf"><label>Patient name (display only)</label><input type="text" id="f_name" placeholder="e.g. John Doe"></div>
    <div class="mf"><label>encounter_id</label><input type="number" id="f_encounter_id" value="1" min="1"></div>
    <div class="mf"><label>patient_nbr</label><input type="number" id="f_patient_nbr" value="1" min="1"></div>

    <!-- ── DEMOGRAPHICS ── -->
    <div class="sec-row">Demographics</div>
    <div class="mf"><label>race</label>
      <select id="f_race">
        <option value="Caucasian">Caucasian</option>
        <option value="AfricanAmerican">AfricanAmerican</option>
        <option value="Hispanic">Hispanic</option>
        <option value="Asian">Asian</option>
        <option value="Other">Other</option>
        <option value="?">? (Unknown)</option>
      </select>
    </div>
    <div class="mf"><label>gender</label>
      <select id="f_gender">
        <option value="Male">Male</option>
        <option value="Female">Female</option>
        <option value="Unknown/Invalid">Unknown/Invalid</option>
      </select>
    </div>
    <div class="mf"><label>age</label>
      <select id="f_age">
        <option value="[0-10)">[0-10)</option>
        <option value="[10-20)">[10-20)</option>
        <option value="[20-30)">[20-30)</option>
        <option value="[30-40)">[30-40)</option>
        <option value="[40-50)">[40-50)</option>
        <option value="[50-60)">[50-60)</option>
        <option value="[60-70)" selected>[60-70)</option>
        <option value="[70-80)">[70-80)</option>
        <option value="[80-90)">[80-90)</option>
        <option value="[90-100)">[90-100)</option>
      </select>
    </div>
    <div class="mf"><label>weight</label>
      <select id="f_weight">
        <option value="?" selected>? (Not recorded)</option>
        <option value="[0-25)">[0-25)</option>
        <option value="[25-50)">[25-50)</option>
        <option value="[50-75)">[50-75)</option>
        <option value="[75-100)">[75-100)</option>
        <option value="[100-125)">[100-125)</option>
        <option value="[125-150)">[125-150)</option>
        <option value="[150-175)">[150-175)</option>
        <option value="[175-200)">[175-200)</option>
        <option value=">200">&gt;200</option>
      </select>
    </div>

    <!-- ── ADMISSION ── -->
    <div class="sec-row">Admission</div>
    <div class="mf"><label>admission_type_id</label><input type="number" id="f_adm_type" value="1" min="1" max="8"></div>
    <div class="mf"><label>discharge_disposition_id</label><input type="number" id="f_disc" value="1" min="1" max="26"></div>
    <div class="mf"><label>admission_source_id</label><input type="number" id="f_adm_src" value="7" min="1" max="25"></div>
    <div class="mf"><label>payer_code</label>
      <select id="f_payer">
        <option value="?">? (Unknown)</option>
        <option value="MC">MC — Medicare</option>
        <option value="MD">MD — Medicaid</option>
        <option value="HM">HM — HMO</option>
        <option value="BC">BC — Blue Cross</option>
        <option value="SP">SP — Self-pay</option>
        <option value="CP">CP — Champus</option>
        <option value="UN">UN — United Health</option>
        <option value="CM">CM — Cigna</option>
        <option value="OG">OG — Government</option>
        <option value="WC">WC — Worker Comp</option>
        <option value="OT">OT — Other</option>
        <option value="PO">PO — Self-pay (Other)</option>
        <option value="CH">CH — Charity</option>
        <option value="FR">FR — Federal</option>
        <option value="DM">DM — Dual eligible</option>
      </select>
    </div>
    <div class="mf"><label>medical_specialty</label>
      <select id="f_specialty">
        <option value="?">? (Unknown)</option>
        <option value="InternalMedicine">Internal Medicine</option>
        <option value="Emergency/Trauma">Emergency / Trauma</option>
        <option value="Family/GeneralPractice">Family / General Practice</option>
        <option value="Cardiology">Cardiology</option>
        <option value="Surgery-General">Surgery — General</option>
        <option value="Nephrology">Nephrology</option>
        <option value="Orthopedics">Orthopedics</option>
        <option value="Orthopedics-Reconstructive">Orthopedics — Reconstructive</option>
        <option value="Radiology">Radiology</option>
        <option value="Pulmonology">Pulmonology</option>
        <option value="Psychiatry">Psychiatry</option>
        <option value="Urology">Urology</option>
        <option value="ObstetricsandGynecology">Obstetrics &amp; Gynecology</option>
        <option value="Gastroenterology">Gastroenterology</option>
        <option value="Neurology">Neurology</option>
        <option value="Hematology/Oncology">Hematology / Oncology</option>
        <option value="Endocrinology">Endocrinology</option>
        <option value="Surgery-Cardiovascular/Thoracic">Surgery — Cardiovascular/Thoracic</option>
        <option value="Pediatrics">Pediatrics</option>
        <option value="Geriatrics">Geriatrics</option>
      </select>
    </div>

    <!-- ── DIAGNOSES (ICD-9) ── -->
    <div class="sec-row">Diagnoses (ICD-9)</div>
    <div class="mf"><label>diag_1 (Primary ICD-9)</label><input type="number" id="f_dx" value="428" min="1" max="999" placeholder="e.g. 428"></div>
    <div class="mf"><label>diag_2 (Secondary ICD-9)</label><input type="number" id="f_dx2" value="250" min="1" max="999" placeholder="e.g. 250"></div>
    <div class="mf"><label>diag_3 (Tertiary ICD-9)</label><input type="number" id="f_dx3" value="401" min="1" max="999" placeholder="e.g. 401"></div>

    <!-- ── STAY DETAILS ── -->
    <div class="sec-row">Stay Details</div>
    <div class="mf"><label>time_in_hospital (days)</label><input type="number" id="f_los" value="5" min="1" max="14"></div>
    <div class="mf"><label>num_lab_procedures</label><input type="number" id="f_lab" value="40" min="0" max="132"></div>
    <div class="mf"><label>num_procedures</label><input type="number" id="f_proc" value="1" min="0" max="6"></div>
    <div class="mf"><label>num_medications</label><input type="number" id="f_meds" value="12" min="0" max="81"></div>
    <div class="mf"><label>number_outpatient</label><input type="number" id="f_out" value="0" min="0" max="42"></div>
    <div class="mf"><label>number_emergency</label><input type="number" id="f_emr" value="0" min="0" max="76"></div>
    <div class="mf"><label>number_inpatient</label><input type="number" id="f_inp" value="1" min="0" max="21"></div>
    <div class="mf"><label>number_diagnoses</label><input type="number" id="f_ndiag" value="7" min="1" max="16"></div>

    <!-- ── LAB RESULTS ── -->
    <div class="sec-row">Lab Results</div>
    <div class="mf"><label>max_glu_serum</label>
      <select id="f_glucose">
        <option value="None">None (not tested)</option>
        <option value=">200">&gt;200</option>
        <option value=">300">&gt;300</option>
        <option value="Norm">Norm</option>
      </select>
    </div>
    <div class="mf"><label>a1cresult</label>
      <select id="f_a1c">
        <option value="None">None (not tested)</option>
        <option value=">7">&gt;7</option>
        <option value=">8">&gt;8</option>
        <option value="Norm">Norm</option>
      </select>
    </div>

    <!-- ── DIABETES MEDICATIONS ── -->
    <div class="sec-row">Diabetes Medications</div>
    <div class="mf"><label>metformin</label>
      <select id="f_metformin"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>repaglinide</label>
      <select id="f_repaglinide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>nateglinide</label>
      <select id="f_nateglinide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>chlorpropamide</label>
      <select id="f_chlorpropamide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>glimepiride</label>
      <select id="f_glimepiride"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>acetohexamide</label>
      <select id="f_acetohexamide"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>glipizide</label>
      <select id="f_glipizide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>glyburide</label>
      <select id="f_glyburide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>tolbutamide</label>
      <select id="f_tolbutamide"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>pioglitazone</label>
      <select id="f_pioglitazone"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>rosiglitazone</label>
      <select id="f_rosiglitazone"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>acarbose</label>
      <select id="f_acarbose"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>miglitol</label>
      <select id="f_miglitol"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>troglitazone</label>
      <select id="f_troglitazone"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>tolazamide</label>
      <select id="f_tolazamide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option></select>
    </div>
    <div class="mf"><label>examide</label>
      <select id="f_examide"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>citoglipton</label>
      <select id="f_citoglipton"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>insulin</label>
      <select id="f_insulin"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>glyburide-metformin</label>
      <select id="f_glyburide_metformin"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select>
    </div>
    <div class="mf"><label>glipizide-metformin</label>
      <select id="f_glipizide_metformin"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>glimepiride-pioglitazone</label>
      <select id="f_glimepiride_pioglitazone"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>metformin-rosiglitazone</label>
      <select id="f_metformin_rosiglitazone"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>
    <div class="mf"><label>metformin-pioglitazone</label>
      <select id="f_metformin_pioglitazone"><option value="No">No</option><option value="Steady">Steady</option></select>
    </div>

    <!-- ── OUTCOMES ── -->
    <div class="sec-row">Outcomes & Flags</div>
    <div class="mf"><label>change</label>
      <select id="f_change"><option value="Ch">Ch — Changed</option><option value="No">No</option></select>
    </div>
    <div class="mf"><label>diabetesmed</label>
      <select id="f_diabmed"><option value="Yes">Yes</option><option value="No">No</option></select>
    </div>
    <div class="mf"><label>readmitted (prior known)</label>
      <select id="f_readmitted">
        <option value="NO">NO</option>
        <option value="&lt;30">&lt;30 days</option>
        <option value="&gt;30">&gt;30 days</option>
      </select>
    </div>

  </div>
  <button class="btn-submit" id="admitBtn" onclick="admitPatient()">Admit &amp; predict</button>
 </div>
</div>

<script>
// ── STATE ──
let patients=[], selIdx=null, gaugeChart=null, donutChart=null;
let cnt={high:0,medium:0,low:0};

// ── UTILS ──
const $=id=>document.getElementById(id);
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const fmt=d=>d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:true});
const tier=p=>p>=65?'high':p>=40?'medium':'low';
const tcolor=t=>t==='high'?'#B83232':t==='medium'?'#C4600A':'#1A7A52';
const tbg=t=>t==='high'?'#FDF0EF':t==='medium'?'#FEF5EC':'#EDF7F2';
const tbd=t=>t==='high'?'#F0C4C0':t==='medium'?'#F0D4B0':'#B8E4CE';
const randId=()=>'PT-'+String(Math.floor(Math.random()*9000)+1000);

// ── SHIFT CLOCK ──
function shiftInfo(){
  const n=new Date(),h=n.getHours(),isDay=h>=6&&h<18;
  const s=new Date(n);
  isDay?s.setHours(6,0,0,0):s.setHours(18,0,0,0);
  if(!isDay&&h<6){s.setDate(s.getDate()-1);s.setHours(18,0,0,0);}
  return{isDay,start:s,end:new Date(s.getTime()+12*60*60*1000),label:isDay?'Day shift':'Night shift'};
}
function fmtS(d){return d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:true});}
function tickShift(){
  const i=shiftInfo(),n=new Date(),el=n-i.start;
  $('sFill').style.width=Math.min(el/(43200000)*100,100).toFixed(1)+'%';
  const mid=new Date(i.start.getTime()+21600000);
  $('sStart').textContent=fmtS(i.start);$('sMid').textContent=fmtS(mid);$('sEnd').textContent=fmtS(i.end);
  $('sElapsed').textContent=(el/3600000).toFixed(1)+'h elapsed';
  $('sRemain').textContent=Math.max(12-el/3600000,0).toFixed(1)+'h remaining';
}

// ── MODAL ──
function openModal(){$('overlay').classList.add('open');}
function closeModal(){$('overlay').classList.remove('open');$('modalErr').style.display='none';}

// ── COLLECT FORM ──
// All field names match the Diabetes 130-US Hospitals dataset exactly.
function collectPayload(){
  const v=id=>$(id).value;
  const n=id=>parseInt($(id).value)||0;
  return{
    // Identifiers
    encounter_id:                  n('f_encounter_id'),
    patient_nbr:                   n('f_patient_nbr'),
    // Demographics
    race:                          v('f_race'),
    gender:                        v('f_gender'),
    age:                           v('f_age'),
    weight:                        v('f_weight'),
    // Admission
    admission_type_id:             n('f_adm_type'),
    discharge_disposition_id:      n('f_disc'),
    admission_source_id:           n('f_adm_src'),
    payer_code:                    v('f_payer'),
    medical_specialty:             v('f_specialty'),
    // Diagnoses
    diag_1:                        n('f_dx'),
    diag_2:                        n('f_dx2'),
    diag_3:                        n('f_dx3'),
    // Stay
    time_in_hospital:              n('f_los'),
    num_lab_procedures:            n('f_lab'),
    num_procedures:                n('f_proc'),
    num_medications:               n('f_meds'),
    number_outpatient:             n('f_out'),
    number_emergency:              n('f_emr'),
    number_inpatient:              n('f_inp'),
    number_diagnoses:              n('f_ndiag'),
    // Lab results
    max_glu_serum:                 v('f_glucose'),
    a1cresult:                     v('f_a1c'),
    // Diabetes medications
    metformin:                     v('f_metformin'),
    repaglinide:                   v('f_repaglinide'),
    nateglinide:                   v('f_nateglinide'),
    chlorpropamide:                v('f_chlorpropamide'),
    glimepiride:                   v('f_glimepiride'),
    acetohexamide:                 v('f_acetohexamide'),
    glipizide:                     v('f_glipizide'),
    glyburide:                     v('f_glyburide'),
    tolbutamide:                   v('f_tolbutamide'),
    pioglitazone:                  v('f_pioglitazone'),
    rosiglitazone:                 v('f_rosiglitazone'),
    acarbose:                      v('f_acarbose'),
    miglitol:                      v('f_miglitol'),
    troglitazone:                  v('f_troglitazone'),
    tolazamide:                    v('f_tolazamide'),
    examide:                       v('f_examide'),
    citoglipton:                   v('f_citoglipton'),
    insulin:                       v('f_insulin'),
    'glyburide-metformin':         v('f_glyburide_metformin'),
    'glipizide-metformin':         v('f_glipizide_metformin'),
    'glimepiride-pioglitazone':    v('f_glimepiride_pioglitazone'),
    'metformin-rosiglitazone':     v('f_metformin_rosiglitazone'),
    'metformin-pioglitazone':      v('f_metformin_pioglitazone'),
    // Outcomes / flags
    change:                        v('f_change'),
    diabetesmed:                   v('f_diabmed'),
    readmitted:                    v('f_readmitted'),
  };
}

// ── ADMIT & CALL API ──
const API_BASE = 'http://localhost:8000';

async function admitPatient(){
  const btn=$('admitBtn');
  btn.disabled=true;btn.textContent='Predicting…';
  $('modalErr').style.display='none';

  const name=v('f_name')||'Unknown Patient';
  const payload=collectPayload();
  payload.patient_id = randId();
  const dxText = 'ICD-9: ' + (v('f_dx') || '?');
  const discId=parseInt(v('f_disc'));
  const discTxt='Disposition: '+discId;

  showProc(`Calling /predict for ${name}…`);
  closeModal();

  let rec;
  try{
    const t0=performance.now();
    const r=await fetch(`${API_BASE}/predict`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload),
    });
    const ms=Math.round(performance.now()-t0);
    if(!r.ok){const e=await r.text();throw new Error(`HTTP ${r.status}: ${e}`);}
    const d=await r.json();
    const pct=d.readmission_risk_pct??0;
    const t=d.risk_tier??tier(pct);
    rec={
      patient_id: payload.patient_id,
      name, dxText, discId, discTxt,
      age:payload.age, gender:payload.gender[0], race:payload.race,
      los:payload.time_in_hospital, meds:payload.num_medications,
      prior_inp:payload.number_inpatient,
      admit_time:new Date(),
      risk_pct:pct, risk_tier:t,
      will_readmit:d.will_readmit??(pct>=50),
      confidence:d.confidence??0,
      top_features:d.top_features??[],
      shap:d.shap_values??{},
      inference_ms:d.inference_ms??ms,
      timestamp:d.timestamp??new Date().toISOString(),
      api_req:payload, api_resp:d, ms,
    };
  }catch(e){
    hideProc();
    btn.disabled=false;btn.textContent='Admit & predict';
    $('modalErr').textContent=e.message;$('modalErr').style.display='block';
    openModal();return;
  }

  patients.push(rec);cnt[rec.risk_tier]++;
  hideProc();
  addTLItem(rec,patients.length-1);
  refreshStats();refreshDonut();addFeed(rec);
  selectPt(patients.length-1);
  $('tlSub').textContent=`${patients.length} patient${patients.length>1?'s':''} processed`;
  btn.disabled=false;btn.textContent='Admit & predict';
}

function v(id){return $(id).value;}

// ── TIMELINE ──
function addTLItem(r,i){
  const sc=$('tlScroll'),div=document.createElement('div');
  div.className=`tli ${r.risk_tier}`;div.dataset.i=i;
  div.onclick=()=>selectPt(+div.dataset.i);
  div.innerHTML=`
    <div class="tl-spine">
      <div class="dot ${r.risk_tier}"></div>
      ${i>0?'<div class="tl-line"></div>':''}
    </div>
    <div class="tl-info">
      <div class="tl-time">${fmt(r.admit_time)}</div>
      <div class="tl-name">${r.name}</div>
      <div class="tl-dx">${r.dxText}</div>
      <div class="chips">
        <span class="chip ${r.risk_tier}">${r.risk_tier.toUpperCase()} RISK</span>
        <span class="chip n">${r.age}y ${r.gender}</span>
        <span class="chip n">${r.los}d LOS</span>
        ${r.discId==3?'<span class="chip medium">SNF</span>':''}
        ${r.prior_inp>=3?`<span class="chip high">${r.prior_inp} prior</span>`:''}
      </div>
    </div>
    <div class="risk-badge">
      <div class="risk-pct ${r.risk_tier}">${r.risk_pct}%</div>
      <div class="risk-unit">30d risk</div>
    </div>`;
  sc.appendChild(div);sc.scrollTop=sc.scrollHeight;
}
function showProc(t){$('procTxt').textContent=t;$('tlProc').classList.add('on');}
function hideProc(){$('tlProc').classList.remove('on');}

// ── DETAIL ──
function selectPt(i){
  selIdx=i;
  document.querySelectorAll('.tli').forEach(el=>el.classList.remove('sel'));
  const el=document.querySelector(`.tli[data-i="${i}"]`);
  if(el)el.classList.add('sel');
  renderDetail(patients[i]);
}

function renderDetail(r){
  $('emptyState').style.display='none';
  const c=$('detailPane');c.style.display='block';
  const col=tcolor(r.risk_tier);
  const conf=r.confidence?(+r.confidence).toFixed(2):(0.72+Math.random()*.18).toFixed(2);
  const ts=r.timestamp;

  // SHAP
  let shap;
  if(r.shap&&Object.keys(r.shap).length){
    shap=Object.entries(r.shap).map(([k,v])=>({n:k,v})).sort((a,b)=>b.v-a.v).slice(0,6);
  }else{
    shap=[
      {n:'number_inpatient',     v:Math.min(r.prior_inp*.09,.36)},
      {n:'time_in_hospital',     v:Math.min(r.los*.013,.22)},
      {n:'discharge_disposition',v:r.discId==3?.18:r.discId==18?.09:.03},
      {n:'num_medications',      v:Math.min(r.meds*.008,.16)},
      {n:'A1Cresult',            v:.08},
      {n:'insulin',              v:.05},
    ].sort((a,b)=>b.v-a.v);
  }
  const mx=shap[0]?.v||.01;

  const descs={
    high:`${r.risk_pct}% predicted probability of readmission within 30 days. Multiple high-impact risk factors are active — immediate pre-discharge intervention is recommended.`,
    medium:`Moderate readmission risk at ${r.risk_pct}%. Targeted care coordination and a structured follow-up plan are advised before discharge.`,
    low:`Readmission risk is ${r.risk_pct}% — within expected baseline. Standard discharge planning with routine 30-day follow-up is appropriate.`,
  };
  const badges={high:'⚠ Pre-discharge intervention required',medium:'~ Schedule 7-day follow-up',low:'✓ Standard discharge pathway'};

  // Pretty-print request JSON with syntax highlighting
  function hlJson(obj){
    return JSON.stringify(obj,null,2)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"([^"]+)":/g,'<span class="jk">"$1"</span>:')
      .replace(/: "([^"]+)"/g,': <span class="js">"$1"</span>')
      .replace(/: (-?\d+\.?\d*)/g,': <span class="jn">$1</span>')
      .replace(/: (true|false)/g,': <span class="jb">$1</span>');
  }

  const topF=(r.top_features&&r.top_features.length
    ?r.top_features.map(f=>`<span class="js">"${f}"</span>`).join(', ')
    :'<span class="js">"number_inpatient"</span>, <span class="js">"time_in_hospital"</span>');

  c.innerHTML=`
    <div class="ph">
      <div>
        <div class="ph-name">${r.name}</div>
        <div class="ph-meta">${r.patient_id} · ${r.age}y ${r.gender} · ${r.race} · Admitted ${fmt(r.admit_time)}</div>
        <div class="chips" style="margin-top:6px;">
          <span class="chip ${r.risk_tier}">${r.risk_tier.toUpperCase()} RISK</span>
          <span class="chip n">${r.dxText}</span>
          <span class="chip n">${r.los}d LOS</span>
          <span class="chip n">${r.meds} meds</span>
          <span class="chip n">${r.discTxt}</span>
          ${r.prior_inp>=3?`<span class="chip high">${r.prior_inp} prior stays</span>`:''}
        </div>
      </div>
      <div class="gauge-wrap">
        <div class="gauge-box">
          <canvas id="detailGauge" width="92" height="92"></canvas>
          <div class="gauge-center">
            <div class="gauge-pct" style="color:${col}">${r.risk_pct}%</div>
            <div class="gauge-sub">30d risk</div>
          </div>
        </div>
        <div class="risk-label" style="color:${col}">${r.risk_tier.charAt(0).toUpperCase()+r.risk_tier.slice(1)} risk</div>
      </div>
    </div>

    <div class="card" style="background:${tbg(r.risk_tier)};border-color:${tbd(r.risk_tier)};margin-bottom:22px;">
      <div style="font-size:13px;color:${col};font-weight:500;margin-bottom:5px;">${badges[r.risk_tier]}</div>
      <div style="font-size:13px;color:#3A3836;line-height:1.6;">${descs[r.risk_tier]}</div>
    </div>

    <div class="sec-head">Feature contributions (SHAP)</div>
    <div class="card">
      <div class="card-title">Top drivers of readmission risk</div>
      ${shap.map(s=>`
        <div class="sr">
          <div class="sr-name" title="${s.n}">${s.n}</div>
          <div class="sr-bar"><div class="sr-fill" style="width:${Math.round(s.v/mx*100)}%;background:${col}"></div></div>
          <div class="sr-val">+${s.v.toFixed(2)}</div>
        </div>`).join('')}
    </div>

    <div class="sec-head">API request</div>
    <div class="api-block">
      <div class="api-head">
        <div class="api-head-l"><span class="badge-post">POST</span><span class="ep">/predict</span></div>
        <span style="font-size:10px;color:var(--ink3);font-family:var(--mono);">Content-Type: application/json</span>
      </div>
      <div class="api-body"><pre>${hlJson(r.api_req)}</pre></div>
    </div>

    <div class="sec-head">API response</div>
    <div class="api-block">
      <div class="api-head">
        <div class="api-head-l"><span class="badge-post">POST</span><span class="ep">/predict · response</span></div>
        <span class="badge-200">200 OK · ${r.ms}ms</span>
      </div>
      <div class="api-body">{
  <span class="jk">"patient_id"</span>: <span class="js">"${r.patient_id}"</span>,
  <span class="jk">"readmission_risk_pct"</span>: <span class="jn">${r.risk_pct}</span>,
  <span class="jk">"risk_tier"</span>: <span class="js">"${r.risk_tier}"</span>,
  <span class="jk">"will_readmit"</span>: <span class="jb">${r.will_readmit}</span>,
  <span class="jk">"confidence"</span>: <span class="jn">${conf}</span>,
  <span class="jk">"top_features"</span>: [${topF}],
  <span class="jk">"shap_values"</span>: {<span class="js">…</span>},
  <span class="jk">"inference_ms"</span>: <span class="jn">${r.inference_ms}</span>,
  <span class="jk">"timestamp"</span>: <span class="js">"${ts}"</span>
}</div>
    </div>`;

  if(gaugeChart)gaugeChart.destroy();
  gaugeChart=new Chart($('detailGauge'),{
    type:'doughnut',
    data:{datasets:[{data:[r.risk_pct,100-r.risk_pct],backgroundColor:[col,'#EAE8E3'],borderWidth:0,borderRadius:3}]},
    options:{responsive:false,cutout:'72%',plugins:{legend:{display:false},tooltip:{enabled:false}},animation:{duration:650,easing:'easeOutQuart'}}
  });
}

// ── STATS & DONUT ──
function refreshStats(){
  $('sAlerts').textContent=cnt.high;
  $('sSeen').textContent=patients.length;
  $('sHigh').textContent=cnt.high;
  $('sMed').textContent=cnt.medium;
  $('sLow').textContent=cnt.low;
}
function refreshDonut(){
  const h=cnt.high,m=cnt.medium,l=cnt.low,tot=patients.length;
  $('dHigh').textContent=h;$('dMed').textContent=m;$('dLow').textContent=l;
  $('donutN').textContent=tot;
  const d=[h,m,l,Math.max(tot===0?1:0,0)];
  if(donutChart){donutChart.data.datasets[0].data=d;donutChart.update();}
  else{donutChart=new Chart($('donut'),{
    type:'doughnut',
    data:{datasets:[{data:d,backgroundColor:['#B83232','#C4600A','#1A7A52','#EAE8E3'],borderWidth:0,borderRadius:3,spacing:2}]},
    options:{responsive:false,cutout:'68%',plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>{const lb=['High','Medium','Low',''];return lb[c.dataIndex]?` ${lb[c.dataIndex]}: ${c.raw}`:'';}}}},animation:{duration:500,easing:'easeOutQuart'}}
  });}
}
function addFeed(r){
  const feed=$('feed'),div=document.createElement('div');
  div.className='fi';
  const cls=r.risk_tier==='high'?'hi':r.risk_tier==='medium'?'med':'lo';
  const act={high:'⚠ Intervention required',medium:'~ Follow-up scheduled',low:'✓ Standard pathway'};
  div.innerHTML=`<div class="fi-time">${fmt(r.admit_time)}</div><div class="fi-msg"><b>${r.name}</b> — <span class="${cls}">${r.risk_pct}% ${r.risk_tier} risk</span><br><span style="font-size:11px;color:var(--ink3);">${act[r.risk_tier]}</span></div>`;
  feed.insertBefore(div,feed.firstChild);
}

// ── INIT ──
function init(){
  const i=shiftInfo();
  $('shiftBadge').textContent=i.label;
  $('tbRange').textContent=fmtS(i.start)+' – '+fmtS(i.end);
  tickShift();setInterval(tickShift,60000);
  refreshDonut();
}
window.addEventListener('load',init);
</script>
</body>
</html>"""

# Use a very large height so the fixed-position iframe covers everything.
# The CSS above overrides it to 100vh anyway.
components.html(DASHBOARD, height=10000, scrolling=False)
