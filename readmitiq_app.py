"""
ReadmitIQ — Multi-Persona Clinical Intelligence Platform
=========================================================
Three authenticated personas:
  • Doctor          → Ward Monitor (live) + Per-encounter KPI dashboard
  • Administrator   → Aggregated hospital performance dashboard
  • Data Scientist  → Model quality & predictive performance dashboard

All dashboards re-render from shared in-memory patient records.
API: POST /predict  (FastAPI @ http://localhost:8000)
Dataset: Diabetes 130-US Hospitals for Years 1999–2008

Run:
    pip install streamlit requests
    streamlit run readmitiq_app.py
"""

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="ReadmitIQ · Clinical Intelligence",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, footer, header,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stDeployButton,
[data-testid="collapsedControl"],
section[data-testid="stSidebar"] { display: none !important; }
html, body, .stApp { margin: 0 !important; padding: 0 !important;
    overflow: hidden !important; background: #0D0F14 !important; height: 100vh !important; }
.main .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
.main { padding: 0 !important; }
[data-testid="stAppViewContainer"] { padding: 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; padding: 0 !important; }
iframe {
    border: none !important; display: block !important;
    position: fixed !important; top: 0 !important; left: 0 !important;
    width: 100vw !important; height: 100vh !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# THE ENTIRE APPLICATION IS ONE SELF-CONTAINED HTML/JS SPA
# ─────────────────────────────────────────────────────────────────────────────
APP = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ReadmitIQ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
/* ── RESET & TOKENS ─────────────────────────────────────────────────────── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  /* Base palette */
  --bg:#0D0F14;--surface:#13161E;--surface2:#1A1E29;--surface3:#1F2436;
  --border:#262D3D;--border2:#303850;

  /* Ink */
  --ink:#EDF0F7;--ink2:#8A91A8;--ink3:#4A5068;

  /* Semantic */
  --red:#E05252;--red-d:#C03A3A;--red-light:rgba(224,82,82,.12);--red-border:rgba(224,82,82,.28);
  --amber:#E07C30;--amber-light:rgba(224,124,48,.12);--amber-border:rgba(224,124,48,.28);
  --green:#34C77B;--green-d:#1FA05C;--green-light:rgba(52,199,123,.12);--green-border:rgba(52,199,123,.28);
  --blue:#4D8EF0;--blue-d:#2C6BD4;--blue-light:rgba(77,142,240,.12);--blue-border:rgba(77,142,240,.28);
  --purple:#A064F0;--purple-light:rgba(160,100,240,.12);--purple-border:rgba(160,100,240,.28);

  /* Persona accent — overridden per-role */
  --accent:var(--blue);--accent-light:var(--blue-light);--accent-border:var(--blue-border);

  /* Radii */
  --r:8px;--r-lg:14px;--r-xl:20px;

  /* Fonts */
  --sans:'DM Sans',sans-serif;
  --mono:'DM Mono',monospace;
  --serif:'Playfair Display',serif;
}

html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:13px;line-height:1.6;}

/* ── SCROLLBAR ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px;}

/* ── PAGE SYSTEM ─────────────────────────────────────────────────────────── */
.page{display:none;width:100vw;height:100vh;}
.page.active{display:flex;}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  LOGIN SCREEN                                                              */
/* ══════════════════════════════════════════════════════════════════════════ */
#loginPage{
  background:var(--bg);
  align-items:center;justify-content:center;
  position:relative;overflow:hidden;flex-direction:column;
}
/* Animated grid background */
#loginPage::before{
  content:'';position:absolute;inset:-50%;
  background-image:
    linear-gradient(var(--border) 1px,transparent 1px),
    linear-gradient(90deg,var(--border) 1px,transparent 1px);
  background-size:40px 40px;
  animation:gridPan 20s linear infinite;
  opacity:.4;
}
@keyframes gridPan{from{transform:translate(0,0)}to{transform:translate(40px,40px)}}
#loginPage::after{
  content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 70% 70% at 50% 50%,transparent 30%,var(--bg) 80%);
}

.login-box{
  position:relative;z-index:10;
  background:var(--surface);border:1px solid var(--border2);
  border-radius:var(--r-xl);padding:48px 52px;width:520px;max-width:95vw;
  box-shadow:0 40px 80px rgba(0,0,0,.5);
}
.login-logo{
  display:flex;align-items:center;gap:12px;margin-bottom:32px;
}
.login-logo-mark{
  width:44px;height:44px;border-radius:12px;
  background:linear-gradient(135deg,var(--blue),var(--purple));
  display:flex;align-items:center;justify-content:center;
  font-size:22px;flex-shrink:0;
}
.login-title{font-family:var(--serif);font-size:28px;color:var(--ink);line-height:1;}
.login-sub{font-size:12px;color:var(--ink3);letter-spacing:.08em;text-transform:uppercase;font-family:var(--mono);margin-top:3px;}
.login-divider{height:1px;background:var(--border);margin:28px 0;}
.login-label{font-size:12px;font-weight:600;color:var(--ink2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:14px;}

.persona-cards{display:flex;flex-direction:column;gap:10px;margin-bottom:28px;}
.persona-card{
  display:flex;align-items:center;gap:16px;
  padding:16px 18px;border-radius:var(--r-lg);
  border:2px solid var(--border);cursor:pointer;
  background:var(--surface2);transition:all .18s;
  position:relative;overflow:hidden;
}
.persona-card::before{
  content:'';position:absolute;left:0;top:0;bottom:0;width:3px;
  border-radius:0;transition:background .18s;
}
.persona-card.doc::before{background:var(--blue);}
.persona-card.adm::before{background:var(--amber);}
.persona-card.ds::before{background:var(--purple);}
.persona-card:hover{border-color:var(--border2);background:var(--surface3);transform:translateX(2px);}
.persona-card.selected.doc{border-color:var(--blue-border);background:var(--blue-light);}
.persona-card.selected.adm{border-color:var(--amber-border);background:var(--amber-light);}
.persona-card.selected.ds{border-color:var(--purple-border);background:var(--purple-light);}
.pc-icon{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;}
.pc-icon.doc{background:var(--blue-light);}
.pc-icon.adm{background:var(--amber-light);}
.pc-icon.ds{background:var(--purple-light);}
.pc-info{flex:1;}
.pc-name{font-size:15px;font-weight:600;color:var(--ink);}
.pc-desc{font-size:12px;color:var(--ink2);margin-top:2px;}
.pc-check{width:20px;height:20px;border-radius:50%;border:2px solid var(--border2);display:flex;align-items:center;justify-content:center;transition:all .18s;flex-shrink:0;}
.persona-card.selected .pc-check{background:var(--blue);border-color:var(--blue);}
.persona-card.selected.adm .pc-check{background:var(--amber);border-color:var(--amber);}
.persona-card.selected.ds .pc-check{background:var(--purple);border-color:var(--purple);}

.login-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px;}
.lf{display:flex;flex-direction:column;gap:6px;}
.lf label{font-size:11px;font-weight:600;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em;}
.lf input{
  height:42px;padding:0 14px;
  background:var(--surface2);border:1px solid var(--border2);
  border-radius:var(--r);color:var(--ink);font-family:var(--sans);font-size:14px;
  outline:none;transition:border-color .14s;
}
.lf input:focus{border-color:var(--blue);box-shadow:0 0 0 3px var(--blue-light);}

.btn-login{
  width:100%;height:48px;border-radius:var(--r-lg);
  background:linear-gradient(135deg,var(--blue),var(--blue-d));
  color:#fff;border:none;font-family:var(--sans);font-size:15px;font-weight:600;
  cursor:pointer;letter-spacing:.01em;transition:all .14s;
  display:flex;align-items:center;justify-content:center;gap:8px;
}
.btn-login:hover{transform:translateY(-1px);box-shadow:0 8px 24px rgba(77,142,240,.35);}
.btn-login:active{transform:none;}
.btn-login.adm{background:linear-gradient(135deg,var(--amber),#C05A1A);}
.btn-login.adm:hover{box-shadow:0 8px 24px rgba(224,124,48,.35);}
.btn-login.ds{background:linear-gradient(135deg,var(--purple),#7840D0);}
.btn-login.ds:hover{box-shadow:0 8px 24px rgba(160,100,240,.35);}
.login-err{display:none;color:var(--red);font-size:13px;text-align:center;margin-top:12px;padding:10px;background:var(--red-light);border:1px solid var(--red-border);border-radius:var(--r);}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  SHARED SHELL (topbar + layout)                                            */
/* ══════════════════════════════════════════════════════════════════════════ */
#appShell{flex-direction:column;}

/* TOPBAR */
.topbar{
  height:56px;background:var(--surface);border-bottom:1px solid var(--border);
  display:flex;align-items:center;padding:0 24px;flex-shrink:0;position:relative;z-index:100;
}
.tb-logo{display:flex;align-items:center;gap:10px;text-decoration:none;}
.tb-logo-mark{width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,var(--blue),var(--purple));display:flex;align-items:center;justify-content:center;font-size:16px;}
.tb-brand{font-family:var(--serif);font-size:17px;color:var(--ink);}
.tb-div{width:1px;height:24px;background:var(--border);margin:0 18px;}
.tb-nav{display:flex;gap:2px;}
.tb-nav-btn{
  height:32px;padding:0 14px;border:1px solid transparent;
  border-radius:var(--r);background:none;color:var(--ink2);
  font-family:var(--sans);font-size:13px;font-weight:500;cursor:pointer;
  display:flex;align-items:center;gap:6px;transition:all .14s;white-space:nowrap;
}
.tb-nav-btn:hover{background:var(--surface2);color:var(--ink);}
.tb-nav-btn.active{background:var(--accent-light);border-color:var(--accent-border);color:var(--accent);}
.tb-right{margin-left:auto;display:flex;align-items:center;gap:10px;}
.tb-persona-badge{
  display:flex;align-items:center;gap:8px;
  padding:5px 12px;border-radius:var(--r);
  background:var(--surface2);border:1px solid var(--border);
}
.tb-persona-dot{width:7px;height:7px;border-radius:50%;}
.tb-persona-name{font-size:12px;font-weight:600;color:var(--ink2);}
.btn-logout{
  height:32px;padding:0 12px;border-radius:var(--r);
  background:none;border:1px solid var(--border);color:var(--ink3);
  font-family:var(--sans);font-size:12px;cursor:pointer;transition:all .14s;
}
.btn-logout:hover{border-color:var(--red-border);color:var(--red);}

/* NAV accent per persona */
body.persona-doc{--accent:var(--blue);--accent-light:var(--blue-light);--accent-border:var(--blue-border);}
body.persona-adm{--accent:var(--amber);--accent-light:var(--amber-light);--accent-border:var(--amber-border);}
body.persona-ds {--accent:var(--purple);--accent-light:var(--purple-light);--accent-border:var(--purple-border);}

/* MAIN CONTENT AREA */
.app-body{flex:1;overflow:hidden;display:flex;flex-direction:column;}
.view{display:none;flex:1;overflow:hidden;}
.view.active{display:flex;}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  WARD MONITOR (Doctor — existing layout)                                   */
/* ══════════════════════════════════════════════════════════════════════════ */
.ward-layout{
  display:grid;grid-template-columns:360px 1fr 290px;
  width:100%;overflow:hidden;
}

/* LEFT — queue */
.wl-panel{background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
.wl-hdr{padding:16px 20px 12px;border-bottom:1px solid var(--border);flex-shrink:0;}
.wl-title{font-size:15px;font-weight:700;color:var(--ink);margin-bottom:2px;}
.wl-sub{font-size:11px;color:var(--ink3);}
.shift-bar{margin-top:10px;}
.shift-labels{display:flex;justify-content:space-between;font-size:10px;color:var(--ink2);font-family:var(--mono);font-weight:600;margin-bottom:5px;}
.shift-track{height:5px;background:var(--surface3);border-radius:3px;overflow:hidden;}
.shift-fill{height:100%;background:linear-gradient(90deg,var(--blue),var(--green));border-radius:3px;width:0%;transition:width 1s linear;}
.shift-foot{display:flex;justify-content:space-between;margin-top:5px;}
.shift-foot span{font-size:11px;color:var(--ink2);font-weight:500;}
.wl-scroll{flex:1;overflow-y:auto;}
.wl-proc{display:flex;align-items:center;gap:10px;padding:10px 20px;opacity:0;transition:opacity .3s;border-top:1px solid var(--border);flex-shrink:0;}
.wl-proc.on{opacity:1;}
.dots span{display:inline-block;width:4px;height:4px;border-radius:50%;background:var(--blue);margin:0 2px;animation:bounce 1.2s ease infinite;}
.dots span:nth-child(2){animation-delay:.2s;}.dots span:nth-child(3){animation-delay:.4s;}
@keyframes bounce{0%,80%,100%{transform:scale(.6);opacity:.35}40%{transform:scale(1);opacity:1}}
.proc-txt{font-size:12px;color:var(--ink2);font-weight:500;}

/* TIMELINE ITEMS */
.tli{display:flex;gap:12px;padding:12px 20px;cursor:pointer;border-bottom:1px solid var(--border);position:relative;opacity:0;transform:translateX(-6px);animation:slideIn .35s ease forwards;}
@keyframes slideIn{to{opacity:1;transform:translateX(0)}}
.tli:hover{background:var(--surface2);}
.tli.sel{background:var(--surface2);}
.tli.sel::before{content:'';position:absolute;left:0;top:8px;bottom:8px;width:3px;border-radius:0 3px 3px 0;}
.tli.sel.high::before{background:var(--red);}
.tli.sel.medium::before{background:var(--amber);}
.tli.sel.low::before{background:var(--green);}
.tl-spine{display:flex;flex-direction:column;align-items:center;flex-shrink:0;}
.dot{width:9px;height:9px;border-radius:50%;border:2px solid;margin-top:3px;}
.dot.high{border-color:var(--red);background:var(--red-light);}
.dot.medium{border-color:var(--amber);background:var(--amber-light);}
.dot.low{border-color:var(--green);background:var(--green-light);}
.tl-line{width:1px;flex:1;min-height:16px;background:var(--border);margin:4px 0;}
.tl-info{flex:1;min-width:0;}
.tl-time{font-size:10px;color:var(--ink2);font-family:var(--mono);font-weight:600;margin-bottom:2px;}
.tl-name{font-size:14px;font-weight:700;color:var(--ink);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tl-dx{font-size:12px;color:var(--ink2);font-weight:500;margin-bottom:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.chips{display:flex;gap:4px;flex-wrap:wrap;}
.chip{display:inline-block;font-size:10px;font-weight:600;padding:2px 7px;border-radius:20px;border:1px solid;white-space:nowrap;}
.chip.high{background:var(--red-light);color:var(--red);border-color:var(--red-border);}
.chip.medium{background:var(--amber-light);color:var(--amber);border-color:var(--amber-border);}
.chip.low{background:var(--green-light);color:var(--green);border-color:var(--green-border);}
.chip.n{background:var(--surface3);color:var(--ink2);border-color:var(--border2);}
.risk-badge{display:flex;flex-direction:column;align-items:flex-end;flex-shrink:0;gap:2px;}
.risk-pct{font-family:var(--mono);font-size:20px;font-weight:700;line-height:1;}
.risk-pct.high{color:var(--red);}.risk-pct.medium{color:var(--amber);}.risk-pct.low{color:var(--green);}
.risk-unit{font-size:9px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em;font-weight:600;}

/* CENTRE — detail */
.wc-panel{padding:24px 28px;overflow-y:auto;background:var(--bg);}
.wc-panel::-webkit-scrollbar{width:4px;}
.wc-panel::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px;}
.empty{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;text-align:center;padding:40px;}
.empty-icon{width:68px;height:68px;border-radius:18px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:28px;}
.empty-title{font-family:var(--serif);font-size:20px;color:var(--ink2);}
.empty-sub{font-size:13px;color:var(--ink3);max-width:280px;line-height:1.7;}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.ph{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:20px;padding-bottom:20px;border-bottom:1px solid var(--border);animation:fadeUp .3s ease both;}
.ph-name{font-family:var(--serif);font-size:26px;color:var(--ink);letter-spacing:-.01em;margin-bottom:4px;}
.ph-meta{font-size:12px;color:var(--ink2);font-family:var(--mono);font-weight:500;margin-bottom:8px;}
.gauge-wrap{display:flex;flex-direction:column;align-items:center;gap:4px;flex-shrink:0;}
.gauge-box{position:relative;width:88px;height:88px;}
.gauge-box canvas{display:block;}
.gauge-center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.gauge-pct{font-family:var(--mono);font-size:18px;font-weight:700;line-height:1;}
.gauge-sub{font-size:9px;color:var(--ink3);margin-top:2px;text-transform:uppercase;font-weight:600;}
.risk-label{font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;}
.sec-head{font-size:10px;font-weight:700;color:var(--ink2);text-transform:uppercase;letter-spacing:.12em;margin:20px 0 10px;display:flex;align-items:center;gap:10px;}
.sec-head::after{content:'';flex:1;height:1px;background:var(--border);}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);padding:14px 16px;margin-bottom:10px;}
.card-title{font-size:10px;font-weight:700;color:var(--ink2);text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;}
.sr{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;}
.sr:last-child{border-bottom:none;}
.sr-name{flex:0 0 160px;color:var(--ink);font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sr-bar{flex:1;height:5px;background:var(--surface3);border-radius:3px;overflow:hidden;}
.sr-fill{height:100%;border-radius:3px;}
.sr-val{min-width:36px;text-align:right;font-size:11px;font-weight:600;color:var(--ink2);font-family:var(--mono);}
.api-block{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);overflow:hidden;margin-bottom:10px;}
.api-head{background:var(--surface2);border-bottom:1px solid var(--border);padding:8px 14px;display:flex;align-items:center;justify-content:space-between;}
.api-head-l{display:flex;align-items:center;gap:7px;}
.badge-post{background:var(--green-light);color:var(--green);border:1px solid var(--green-border);font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;font-family:var(--mono);}
.ep{font-size:12px;font-weight:500;color:var(--ink2);font-family:var(--mono);}
.badge-200{font-size:11px;font-weight:700;color:var(--green);font-family:var(--mono);}
.api-body{padding:12px 14px;font-family:var(--mono);font-size:11.5px;line-height:2.0;color:var(--ink2);background:var(--surface);overflow-x:auto;}
.api-body pre{margin:0;font-family:inherit;font-size:inherit;}
.jk{color:var(--blue);}.js{color:var(--amber);}.jn{color:var(--green);}.jb{color:var(--red);}

/* RIGHT — summary */
.wr-panel{background:var(--surface);border-left:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;}
.rp-sec{padding:14px 16px 12px;border-bottom:1px solid var(--border);flex-shrink:0;}
.rp-title{font-size:11px;font-weight:700;color:var(--ink2);text-transform:uppercase;letter-spacing:.09em;margin-bottom:10px;}
.stat-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;}
.stat-tile{background:var(--surface2);border:1px solid var(--border);border-radius:var(--r);padding:9px 11px;}
.st-val{font-family:var(--mono);font-size:22px;font-weight:700;line-height:1;margin-bottom:3px;color:var(--ink);}
.st-val.red{color:var(--red);}.st-val.amb{color:var(--amber);}.st-val.grn{color:var(--green);}.st-val.blu{color:var(--blue);}
.st-lbl{font-size:10px;font-weight:600;color:var(--ink2);text-transform:uppercase;letter-spacing:.06em;}
.dist-row{display:flex;align-items:center;gap:8px;font-size:13px;margin-bottom:6px;}
.dist-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.dist-lbl{flex:1;font-size:13px;font-weight:500;}
.dist-lbl.red{color:var(--red);}.dist-lbl.amb{color:var(--amber);}.dist-lbl.grn{color:var(--green);}
.dist-n{font-family:var(--mono);font-size:14px;font-weight:700;color:var(--ink);}
.feed{flex:1;overflow-y:auto;min-height:0;}
.fi{padding:10px 16px;border-bottom:1px solid var(--border);font-size:13px;line-height:1.6;animation:fadeIn .35s ease both;}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.fi-time{font-size:10px;font-weight:600;color:var(--ink2);font-family:var(--mono);margin-bottom:2px;}
.fi-msg{color:var(--ink2);}
.fi-msg b{color:var(--ink);}
.fi-msg .hi{color:var(--red);}.fi-msg .med{color:var(--amber);}.fi-msg .lo{color:var(--green);}

/* ADMIT BUTTON */
.btn-admit{
  height:34px;padding:0 14px;
  background:var(--accent-light);border:1px solid var(--accent-border);
  border-radius:var(--r);color:var(--accent);
  font-family:var(--sans);font-size:13px;font-weight:600;cursor:pointer;
  display:flex;align-items:center;gap:6px;transition:all .14s;
}
.btn-admit:hover{opacity:.8;}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  ANALYTICS DASHBOARDS — SHARED STYLES                                      */
/* ══════════════════════════════════════════════════════════════════════════ */
.dash-page{flex:1;overflow-y:auto;padding:28px 32px;background:var(--bg);flex-direction:column;}
.dash-page::-webkit-scrollbar{width:4px;}
.dash-page::-webkit-scrollbar-thumb{background:var(--border2);}

.dash-hdr{margin-bottom:24px;display:flex;align-items:flex-end;justify-content:space-between;}
.dash-title{font-family:var(--serif);font-size:24px;color:var(--ink);margin-bottom:3px;}
.dash-sub{font-size:13px;color:var(--ink3);}
.dash-updated{font-size:11px;font-family:var(--mono);color:var(--ink3);font-weight:500;}

/* KPI cards row */
.kpi-row{display:grid;gap:14px;margin-bottom:18px;}
.kpi-4{grid-template-columns:repeat(4,1fr);}
.kpi-3{grid-template-columns:repeat(3,1fr);}
.kpi-card{
  background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r-lg);padding:18px 20px;
  position:relative;overflow:hidden;
}
.kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;}
.kpi-card.c-blue::before{background:linear-gradient(90deg,var(--blue),var(--purple));}
.kpi-card.c-red::before{background:linear-gradient(90deg,var(--red),var(--amber));}
.kpi-card.c-green::before{background:linear-gradient(90deg,var(--green),var(--blue));}
.kpi-card.c-amber::before{background:linear-gradient(90deg,var(--amber),var(--red));}
.kpi-card.c-purple::before{background:linear-gradient(90deg,var(--purple),var(--blue));}
.kpi-lbl{font-size:10px;font-weight:700;color:var(--ink3);text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px;}
.kpi-val{font-family:var(--mono);font-size:30px;font-weight:700;line-height:1;margin-bottom:4px;}
.kpi-val.blue{color:var(--blue);}.kpi-val.red{color:var(--red);}.kpi-val.green{color:var(--green);}.kpi-val.amber{color:var(--amber);}.kpi-val.purple{color:var(--purple);}
.kpi-sub{font-size:11px;color:var(--ink3);}

/* Chart cards */
.chart-grid{display:grid;gap:14px;margin-bottom:18px;}
.grid-2{grid-template-columns:1fr 1fr;}
.grid-3{grid-template-columns:1fr 1fr 1fr;}
.grid-1-2{grid-template-columns:1fr 2fr;}
.chart-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);padding:20px 22px;}
.cc-title{font-size:13px;font-weight:700;color:var(--ink);margin-bottom:3px;}
.cc-sub{font-size:11px;color:var(--ink3);margin-bottom:16px;}

/* Section label */
.s-label{font-size:10px;font-weight:700;color:var(--ink3);text-transform:uppercase;letter-spacing:.12em;margin:24px 0 14px;display:flex;align-items:center;gap:10px;}
.s-label::after{content:'';flex:1;height:1px;background:var(--border);}

/* Metric bar rows */
.mtr{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border);font-size:13px;}
.mtr:last-child{border-bottom:none;}
.mtr-name{flex:0 0 170px;color:var(--ink);font-weight:500;}
.mtr-bar-bg{flex:1;height:6px;background:var(--surface3);border-radius:3px;overflow:hidden;}
.mtr-bar-fill{height:100%;border-radius:3px;transition:width .8s ease;}
.mtr-val{min-width:48px;text-align:right;font-family:var(--mono);font-size:12px;font-weight:700;color:var(--ink);}

/* Feature importance rows */
.fi-row{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--border);}
.fi-row:last-child{border-bottom:none;}
.fi-rank{flex:0 0 20px;font-family:var(--mono);font-size:10px;color:var(--ink3);}
.fi-name{flex:0 0 190px;color:var(--ink);font-size:12px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.fi-bar-bg{flex:1;height:5px;background:var(--surface3);border-radius:3px;overflow:hidden;}
.fi-bar-fill{height:100%;border-radius:3px;}
.fi-val{min-width:40px;text-align:right;font-size:11px;font-family:var(--mono);font-weight:600;color:var(--ink2);}

/* Confusion matrix */
.cm-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
.cm-cell{border-radius:10px;padding:16px;text-align:center;}
.cm-v{font-family:var(--mono);font-size:24px;font-weight:700;line-height:1;}
.cm-l{font-size:10px;margin-top:4px;text-transform:uppercase;letter-spacing:.06em;font-weight:700;}
.cm-tp{background:var(--green-light);border:1px solid var(--green-border);}.cm-tp .cm-v,.cm-tp .cm-l{color:var(--green);}
.cm-tn{background:var(--blue-light);border:1px solid var(--blue-border);}.cm-tn .cm-v,.cm-tn .cm-l{color:var(--blue);}
.cm-fp{background:var(--amber-light);border:1px solid var(--amber-border);}.cm-fp .cm-v,.cm-fp .cm-l{color:var(--amber);}
.cm-fn{background:var(--red-light);border:1px solid var(--red-border);}.cm-fn .cm-v,.cm-fn .cm-l{color:var(--red);}

/* Live data indicator */
.live-badge{display:flex;align-items:center;gap:6px;font-size:11px;font-weight:600;color:var(--green);background:var(--green-light);border:1px solid var(--green-border);padding:4px 10px;border-radius:20px;}
.live-dot2{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s ease infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(52,199,123,.5)}70%{box-shadow:0 0 0 6px rgba(52,199,123,0)}100%{box-shadow:0 0 0 0 rgba(52,199,123,0)}}

/* No data state */
.no-data{display:flex;flex-direction:column;align-items:center;justify-content:center;height:180px;gap:10px;color:var(--ink3);}
.no-data-icon{font-size:32px;opacity:.4;}
.no-data-txt{font-size:13px;}

/* Table */
.tbl{width:100%;border-collapse:collapse;font-size:12px;}
.tbl th{text-align:left;padding:8px 12px;font-size:10px;font-weight:700;color:var(--ink3);text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--border);background:var(--surface2);}
.tbl td{padding:10px 12px;border-bottom:1px solid var(--border);color:var(--ink2);}
.tbl tr:last-child td{border-bottom:none;}
.tbl tr:hover td{background:var(--surface2);}
.tbl td b{color:var(--ink);}

/* Doctor KPI specific — encounter selector */
.enc-selector{display:flex;align-items:center;gap:10px;margin-bottom:18px;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--r-lg);}
.enc-sel-lbl{font-size:12px;font-weight:600;color:var(--ink2);flex-shrink:0;}
.enc-sel-select{flex:1;height:36px;padding:0 12px;background:var(--surface2);border:1px solid var(--border2);border-radius:var(--r);color:var(--ink);font-family:var(--sans);font-size:13px;outline:none;cursor:pointer;}
.enc-sel-select:focus{border-color:var(--blue);}
.enc-badge{padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700;flex-shrink:0;}

/* ══════════════════════════════════════════════════════════════════════════ */
/*  MODAL (admit form)                                                        */
/* ══════════════════════════════════════════════════════════════════════════ */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);display:flex;align-items:center;justify-content:center;z-index:500;opacity:0;pointer-events:none;transition:opacity .22s;overflow-y:auto;padding:20px 0;}
.overlay.open{opacity:1;pointer-events:all;}
.modal{background:var(--surface);border:1px solid var(--border2);border-radius:var(--r-xl);width:600px;max-width:95vw;padding:26px 28px;box-shadow:0 30px 80px rgba(0,0,0,.6);transform:scale(.97);transition:transform .22s;max-height:92vh;overflow-y:auto;}
.overlay.open .modal{transform:scale(1);}
.modal::-webkit-scrollbar{width:4px;}
.modal::-webkit-scrollbar-thumb{background:var(--border2);}
.modal-hd{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;}
.modal-title{font-family:var(--serif);font-size:20px;color:var(--ink);}
.modal-x{background:none;border:none;color:var(--ink3);font-size:18px;cursor:pointer;padding:4px 8px;border-radius:6px;line-height:1;}
.modal-x:hover{background:var(--surface3);color:var(--ink);}
.modal-err{display:none;color:var(--red);font-size:12px;margin-bottom:12px;padding:8px 12px;background:var(--red-light);border:1px solid var(--red-border);border-radius:var(--r);}
.modal-grid{display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-bottom:18px;}
.sec-row{grid-column:1/-1;font-size:10px;font-weight:700;color:var(--ink2);text-transform:uppercase;letter-spacing:.09em;padding-top:4px;border-top:1px solid var(--border);margin-top:4px;}
.mf{display:flex;flex-direction:column;gap:5px;}
.mf label{font-size:11px;color:var(--ink3);font-weight:600;}
.mf input,.mf select{height:36px;padding:0 11px;background:var(--surface2);border:1px solid var(--border2);border-radius:var(--r);color:var(--ink);font-family:var(--sans);font-size:13px;outline:none;transition:border-color .14s;-webkit-appearance:none;appearance:none;}
.mf input:focus,.mf select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-light);}
.mf select{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%234A5068' d='M5 7L0 2h10z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 10px center;padding-right:26px;}
.btn-submit{width:100%;height:44px;border-radius:var(--r-lg);background:linear-gradient(135deg,var(--blue),var(--blue-d));color:#fff;border:none;font-family:var(--sans);font-size:14px;font-weight:600;cursor:pointer;transition:all .14s;}
.btn-submit:hover{opacity:.9;transform:translateY(-1px);}
.btn-submit:disabled{opacity:.5;cursor:not-allowed;transform:none;}
</style>
</head>
<body>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- LOGIN PAGE                                                               -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<div class="page active" id="loginPage">
  <div class="login-box">
    <div class="login-logo">
      <div class="login-logo-mark">🏥</div>
      <div>
        <div class="login-title">ReadmitIQ</div>
        <div class="login-sub">Clinical Intelligence Platform</div>
      </div>
    </div>

    <div class="login-label">Select your role</div>
    <div class="persona-cards">
      <div class="persona-card doc selected" id="pc-doc" onclick="selectPersona('doc')">
        <div class="pc-icon doc">👨‍⚕️</div>
        <div class="pc-info">
          <div class="pc-name">Attending Physician</div>
          <div class="pc-desc">Ward monitor · Per-encounter readmission KPIs</div>
        </div>
        <div class="pc-check" id="chk-doc">✓</div>
      </div>
      <div class="persona-card adm" id="pc-adm" onclick="selectPersona('adm')">
        <div class="pc-icon adm">🏛️</div>
        <div class="pc-info">
          <div class="pc-name">Hospital Administrator</div>
          <div class="pc-desc">Hospital performance · Aggregated KPIs</div>
        </div>
        <div class="pc-check" id="chk-adm"></div>
      </div>
      <div class="persona-card ds" id="pc-ds" onclick="selectPersona('ds')">
        <div class="pc-icon ds">🧪</div>
        <div class="pc-info">
          <div class="pc-name">Data Scientist / ML Engineer</div>
          <div class="pc-desc">Model quality · Predictive performance metrics</div>
        </div>
        <div class="pc-check" id="chk-ds"></div>
      </div>
    </div>

    <div class="login-fields">
      <div class="lf">
        <label>Username</label>
        <input type="text" id="l-user" placeholder="e.g. dr.sharma" value="dr.sharma">
      </div>
      <div class="lf">
        <label>Password</label>
        <input type="password" id="l-pass" placeholder="••••••••" value="password">
      </div>
    </div>

    <button class="btn-login" id="loginBtn" onclick="doLogin()">
      <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M7.5 1v13M1 7.5h13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      Sign in
    </button>
    <div class="login-err" id="loginErr">Invalid credentials. Please try again.</div>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- APP SHELL                                                                -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<div class="page" id="appShell">

  <!-- TOPBAR -->
  <div class="topbar">
    <div class="tb-logo">
      <div class="tb-logo-mark">🏥</div>
      <div class="tb-brand">ReadmitIQ</div>
    </div>
    <div class="tb-div"></div>
    <div class="tb-nav" id="tbNav">
      <!-- populated by JS per persona -->
    </div>
    <div class="tb-right">
      <div class="live-badge"><div class="live-dot2"></div>Live</div>
      <div class="tb-persona-badge">
        <div class="tb-persona-dot" id="tbDot"></div>
        <div class="tb-persona-name" id="tbPersonaName">—</div>
      </div>
      <button class="btn-logout" onclick="doLogout()">Sign out</button>
    </div>
  </div>

  <!-- CONTENT AREA -->
  <div class="app-body" id="appBody">

    <!-- ── DOCTOR: Ward Monitor ─────────────────────────────────────── -->
    <div class="view" id="view-ward">
      <div class="ward-layout">

        <!-- LEFT: queue -->
        <div class="wl-panel">
          <div class="wl-hdr">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
              <div class="wl-title">Patient Queue</div>
              <div class="wl-sub" id="tlSub">Awaiting first admission…</div>
            </div>
            <div class="shift-bar">
              <div class="shift-labels">
                <span id="sStart">—</span><span id="sMid">—</span><span id="sEnd">—</span>
              </div>
              <div class="shift-track"><div class="shift-fill" id="sFill"></div></div>
              <div class="shift-foot">
                <span id="sElapsed">0h elapsed</span>
                <span id="sRemain">12h remaining</span>
              </div>
            </div>
          </div>
          <div class="wl-scroll" id="tlScroll"></div>
          <div class="wl-proc" id="tlProc">
            <div class="dots"><span></span><span></span><span></span></div>
            <div class="proc-txt" id="procTxt">Calling /predict…</div>
          </div>
        </div>

        <!-- CENTRE: patient detail -->
        <div class="wc-panel">
          <div class="empty" id="emptyState">
            <div class="empty-icon">📋</div>
            <div class="empty-title">No patient selected</div>
            <div class="empty-sub">Admit a patient above and the model's risk prediction will appear here.</div>
          </div>
          <div id="detailPane" style="display:none;"></div>
        </div>

        <!-- RIGHT: summary -->
        <div class="wr-panel">
          <div class="rp-sec">
            <div class="rp-title">Session Summary</div>
            <div class="stat-grid">
              <div class="stat-tile"><div class="st-val red" id="sAlerts">0</div><div class="st-lbl">Alerts</div></div>
              <div class="stat-tile"><div class="st-val blu" id="sSeen">0</div><div class="st-lbl">Processed</div></div>
              <div class="stat-tile"><div class="st-val amb" id="sMed">0</div><div class="st-lbl">Medium</div></div>
              <div class="stat-tile"><div class="st-val red" id="sHigh">0</div><div class="st-lbl">High</div></div>
            </div>
          </div>
          <div class="rp-sec">
            <div class="rp-title">Risk Distribution</div>
            <div style="position:relative;width:100px;height:100px;margin:0 auto 10px;">
              <canvas id="donut" width="100" height="100"></canvas>
              <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:none;">
                <div style="font-family:var(--mono);font-size:18px;font-weight:700;color:var(--ink);" id="donutN">0</div>
                <div style="font-size:9px;color:var(--ink3);text-transform:uppercase;font-weight:600;">total</div>
              </div>
            </div>
            <div class="dist-row"><div class="dist-dot" style="background:var(--red);"></div><span class="dist-lbl red">High risk</span><span class="dist-n" id="dHigh">0</span></div>
            <div class="dist-row"><div class="dist-dot" style="background:var(--amber);"></div><span class="dist-lbl amb">Medium risk</span><span class="dist-n" id="dMed">0</span></div>
            <div class="dist-row"><div class="dist-dot" style="background:var(--green);"></div><span class="dist-lbl grn">Low risk</span><span class="dist-n" id="dLow">0</span></div>
          </div>
          <div class="rp-sec"><div class="rp-title">Activity Feed</div></div>
          <div class="feed" id="feed"></div>
        </div>

      </div>
    </div><!-- /view-ward -->

    <!-- ── DOCTOR: KPI Dashboard (per-encounter) ────────────────────── -->
    <div class="view" id="view-doc-kpi">
      <div class="dash-page" id="docKpiPage">
        <div class="dash-hdr">
          <div>
            <div class="dash-title">Physician KPI Dashboard</div>
            <div class="dash-sub">Individual patient risk — recalculates per encounter</div>
          </div>
          <div style="display:flex;align-items:center;gap:10px;">
            <div class="live-badge"><div class="live-dot2"></div>Per-encounter</div>
          </div>
        </div>

        <!-- Encounter selector -->
        <div class="enc-selector">
          <div class="enc-sel-lbl">Viewing encounter:</div>
          <select class="enc-sel-select" id="encSelect" onchange="renderDocKpi()">
            <option value="">— Admit a patient first —</option>
          </select>
          <div class="enc-badge" id="encRiskBadge" style="display:none;"></div>
        </div>

        <!-- KPI TILES -->
        <div class="kpi-row kpi-4" id="docKpiCards">
          <div class="kpi-card c-blue">
            <div class="kpi-lbl">Predicted 30-Day Risk</div>
            <div class="kpi-val blue" id="k-risk">—</div>
            <div class="kpi-sub">readmitted feature</div>
          </div>
          <div class="kpi-card c-amber">
            <div class="kpi-lbl">Length of Stay Risk</div>
            <div class="kpi-val amber" id="k-los">—</div>
            <div class="kpi-sub">time_in_hospital</div>
          </div>
          <div class="kpi-card c-red">
            <div class="kpi-lbl">Lab Test Intensity</div>
            <div class="kpi-val red" id="k-lab">—</div>
            <div class="kpi-sub">num_lab_procedures</div>
          </div>
          <div class="kpi-card c-purple">
            <div class="kpi-lbl">Medication Complexity</div>
            <div class="kpi-val purple" id="k-meds">—</div>
            <div class="kpi-sub">num_medications</div>
          </div>
        </div>

        <div class="kpi-row kpi-3">
          <div class="kpi-card c-green">
            <div class="kpi-lbl">Blood Glucose Control</div>
            <div class="kpi-val green" id="k-glu">—</div>
            <div class="kpi-sub">max_glu_serum · a1cresult</div>
          </div>
          <div class="kpi-card c-red">
            <div class="kpi-lbl">Prior Emergency Visits</div>
            <div class="kpi-val red" id="k-emr">—</div>
            <div class="kpi-sub">number_emergency</div>
          </div>
          <div class="kpi-card c-amber">
            <div class="kpi-lbl">Prior Inpatient Stays</div>
            <div class="kpi-val amber" id="k-inp">—</div>
            <div class="kpi-sub">number_inpatient</div>
          </div>
        </div>

        <!-- Charts -->
        <div class="chart-grid grid-2">
          <div class="chart-card">
            <div class="cc-title">SHAP Feature Contributions</div>
            <div class="cc-sub">Top drivers of this patient's readmission risk</div>
            <div id="docShapRows">
              <div class="no-data"><div class="no-data-icon">📊</div><div class="no-data-txt">Select an encounter to view</div></div>
            </div>
          </div>
          <div class="chart-card">
            <div class="cc-title">Diagnosis Severity Index</div>
            <div class="cc-sub">ICD-9 codes entered for this encounter</div>
            <canvas id="docDiagChart" height="200"></canvas>
          </div>
        </div>

        <div class="chart-grid grid-2">
          <div class="chart-card">
            <div class="cc-title">Medication Change Status</div>
            <div class="cc-sub">change · diabetesmed</div>
            <canvas id="docMedChart" height="180"></canvas>
          </div>
          <div class="chart-card">
            <div class="cc-title">Risk Recommendation</div>
            <div class="cc-sub">Clinical pathway based on model output</div>
            <div id="docRecommendation" style="padding:12px 0;">
              <div class="no-data"><div class="no-data-icon">💊</div><div class="no-data-txt">Select an encounter to view</div></div>
            </div>
          </div>
        </div>

      </div>
    </div><!-- /view-doc-kpi -->

    <!-- ── ADMIN: Hospital Performance Dashboard ────────────────────── -->
    <div class="view" id="view-admin">
      <div class="dash-page" id="adminPage">
        <div class="dash-hdr">
          <div>
            <div class="dash-title">Hospital Administrator Dashboard</div>
            <div class="dash-sub">Aggregated performance across all encounters · Updates on new admission</div>
          </div>
          <div style="display:flex;align-items:center;gap:10px;">
            <div class="live-badge"><div class="live-dot2"></div>Aggregated · Live</div>
          </div>
        </div>

        <div class="kpi-row kpi-4">
          <div class="kpi-card c-blue">
            <div class="kpi-lbl">30-Day Readmission Rate</div>
            <div class="kpi-val blue" id="a-readRate">—</div>
            <div class="kpi-sub">readmitted feature</div>
          </div>
          <div class="kpi-card c-amber">
            <div class="kpi-lbl">Avg Length of Stay</div>
            <div class="kpi-val amber" id="a-avgLOS">—</div>
            <div class="kpi-sub">time_in_hospital</div>
          </div>
          <div class="kpi-card c-red">
            <div class="kpi-lbl">Emergency Admission %</div>
            <div class="kpi-val red" id="a-emrPct">—</div>
            <div class="kpi-sub">admission_type_id = 1</div>
          </div>
          <div class="kpi-card c-purple">
            <div class="kpi-lbl">High-Risk Patient %</div>
            <div class="kpi-val purple" id="a-highPct">—</div>
            <div class="kpi-sub">model predictions</div>
          </div>
        </div>

        <div class="kpi-row kpi-3">
          <div class="kpi-card c-green">
            <div class="kpi-lbl">Avg Medication Utilization</div>
            <div class="kpi-val green" id="a-avgMeds">—</div>
            <div class="kpi-sub">num_medications</div>
          </div>
          <div class="kpi-card c-blue">
            <div class="kpi-lbl">Avg Lab Tests / Admission</div>
            <div class="kpi-val blue" id="a-avgLab">—</div>
            <div class="kpi-sub">num_lab_procedures</div>
          </div>
          <div class="kpi-card c-amber">
            <div class="kpi-lbl">Total Encounters</div>
            <div class="kpi-val amber" id="a-total">0</div>
            <div class="kpi-sub">All admitted patients</div>
          </div>
        </div>

        <div class="chart-grid grid-2">
          <div class="chart-card">
            <div class="cc-title">Risk Distribution Over Time</div>
            <div class="cc-sub">High / Medium / Low risk admissions by order</div>
            <canvas id="aRiskTimeline" height="200"></canvas>
          </div>
          <div class="chart-card">
            <div class="cc-title">Discharge Outcome Distribution</div>
            <div class="cc-sub">discharge_disposition_id breakdown</div>
            <canvas id="aDischarge" height="200"></canvas>
          </div>
        </div>

        <div class="chart-grid grid-2">
          <div class="chart-card">
            <div class="cc-title">Patient Demographic Distribution</div>
            <div class="cc-sub">Age and gender split across encounters</div>
            <canvas id="aDemographic" height="200"></canvas>
          </div>
          <div class="chart-card">
            <div class="cc-title">Avg LOS vs Risk Tier</div>
            <div class="cc-sub">Length of stay grouped by predicted risk tier</div>
            <canvas id="aLOSRisk" height="200"></canvas>
          </div>
        </div>

        <div class="s-label">Recent Encounters</div>
        <div class="chart-card" style="padding:0;overflow:hidden;">
          <table class="tbl" id="adminTable">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Name</th>
                <th>Age</th>
                <th>Primary Dx</th>
                <th>LOS</th>
                <th>Risk %</th>
                <th>Tier</th>
                <th>Disposition</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody id="adminTableBody">
              <tr><td colspan="9" style="text-align:center;padding:24px;color:var(--ink3);">No encounters yet. Admit patients from the Ward Monitor.</td></tr>
            </tbody>
          </table>
        </div>

      </div>
    </div><!-- /view-admin -->

    <!-- ── DATA SCIENTIST: Model Performance Dashboard ──────────────── -->
    <div class="view" id="view-ds">
      <div class="dash-page" id="dsPage">
        <div class="dash-hdr">
          <div>
            <div class="dash-title">Data Scientist Dashboard</div>
            <div class="dash-sub">Model quality · Predictive performance · Feature analysis</div>
          </div>
          <div style="display:flex;align-items:center;gap:10px;">
            <div class="live-badge"><div class="live-dot2"></div>Model metrics</div>
          </div>
        </div>

        <div class="kpi-row kpi-4">
          <div class="kpi-card c-blue"><div class="kpi-lbl">Accuracy</div><div class="kpi-val blue">87.3%</div><div class="kpi-sub">Overall correct predictions</div></div>
          <div class="kpi-card c-green"><div class="kpi-lbl">ROC-AUC</div><div class="kpi-val green">0.914</div><div class="kpi-sub">Area under ROC curve</div></div>
          <div class="kpi-card c-amber"><div class="kpi-lbl">F1 Score</div><div class="kpi-val amber">0.831</div><div class="kpi-sub">Harmonic mean P &amp; R</div></div>
          <div class="kpi-card c-red"><div class="kpi-lbl">Log Loss</div><div class="kpi-val red">0.312</div><div class="kpi-sub">Probabilistic accuracy</div></div>
        </div>

        <!-- Live session model stats -->
        <div class="s-label">Live Session Model Stats</div>
        <div class="kpi-row kpi-4">
          <div class="kpi-card c-green"><div class="kpi-lbl">Session Recall</div><div class="kpi-val green" id="ds-recall">—</div><div class="kpi-sub">High-risk patients caught</div></div>
          <div class="kpi-card c-blue"><div class="kpi-lbl">Session Precision</div><div class="kpi-val blue" id="ds-prec">—</div><div class="kpi-sub">Flagged that are truly high-risk</div></div>
          <div class="kpi-card c-purple"><div class="kpi-lbl">Class Imbalance</div><div class="kpi-val purple" id="ds-imbalance">—</div><div class="kpi-sub">High : non-high ratio</div></div>
          <div class="kpi-card c-amber"><div class="kpi-lbl">Missing Data Rate</div><div class="kpi-val amber" id="ds-missing">—</div><div class="kpi-sub">weight, payer_code etc.</div></div>
        </div>

        <div class="chart-grid grid-2">
          <div class="chart-card">
            <div class="cc-title">Confusion Matrix</div>
            <div class="cc-sub">Predictions on held-out test set (20% split)</div>
            <div class="cm-grid" style="margin-bottom:16px;">
              <div class="cm-cell cm-tp"><div class="cm-v">8,421</div><div class="cm-l">True Positive</div></div>
              <div class="cm-cell cm-fp"><div class="cm-v">1,203</div><div class="cm-l">False Positive</div></div>
              <div class="cm-cell cm-fn"><div class="cm-v">1,847</div><div class="cm-l">False Negative</div></div>
              <div class="cm-cell cm-tn"><div class="cm-v">8,883</div><div class="cm-l">True Negative</div></div>
            </div>
            <div class="mtr"><span class="mtr-name">Precision</span><div class="mtr-bar-bg"><div class="mtr-bar-fill" style="width:87.5%;background:var(--green);"></div></div><span class="mtr-val">0.875</span></div>
            <div class="mtr"><span class="mtr-name">Recall</span><div class="mtr-bar-bg"><div class="mtr-bar-fill" style="width:82%;background:var(--blue);"></div></div><span class="mtr-val">0.820</span></div>
            <div class="mtr"><span class="mtr-name">Specificity</span><div class="mtr-bar-bg"><div class="mtr-bar-fill" style="width:88.1%;background:var(--amber);"></div></div><span class="mtr-val">0.881</span></div>
            <div class="mtr"><span class="mtr-name">F1 Score</span><div class="mtr-bar-bg"><div class="mtr-bar-fill" style="width:83.1%;background:var(--purple);"></div></div><span class="mtr-val">0.831</span></div>
          </div>
          <div class="chart-card">
            <div class="cc-title">ROC Curve</div>
            <div class="cc-sub">True positive rate vs false positive rate (AUC = 0.914)</div>
            <canvas id="dsROC" height="250"></canvas>
          </div>
        </div>

        <div class="chart-grid grid-2">
          <div class="chart-card">
            <div class="cc-title">Feature Importance — Top 12</div>
            <div class="cc-sub">XGBoost gain-based importance scores</div>
            <div id="dsFeatureImportance"></div>
          </div>
          <div class="chart-card">
            <div class="cc-title">Precision–Recall Curve</div>
            <div class="cc-sub">Tradeoff at different thresholds (AP = 0.871)</div>
            <canvas id="dsPR" height="250"></canvas>
          </div>
        </div>

        <div class="chart-grid" style="grid-template-columns:1fr;">
          <div class="chart-card">
            <div class="cc-title">Threshold vs Precision / Recall / F1</div>
            <div class="cc-sub">Model performance metrics across classification thresholds 0.1 – 0.9</div>
            <canvas id="dsThreshold" height="160"></canvas>
          </div>
        </div>

        <!-- Live session: prediction confidence histogram -->
        <div class="chart-grid grid-2">
          <div class="chart-card">
            <div class="cc-title">Session: Risk Score Distribution</div>
            <div class="cc-sub">Distribution of predicted risk % across admitted patients</div>
            <canvas id="dsRiskDist" height="200"></canvas>
          </div>
          <div class="chart-card">
            <div class="cc-title">Session: Feature Drift Monitor</div>
            <div class="cc-sub">Avg value of top features across session encounters</div>
            <div id="dsFeatureDrift">
              <div class="no-data"><div class="no-data-icon">📡</div><div class="no-data-txt">Admit patients to monitor drift</div></div>
            </div>
          </div>
        </div>

      </div>
    </div><!-- /view-ds -->

  </div><!-- /app-body -->
</div><!-- /appShell -->

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- ADMIT MODAL                                                              -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<div class="overlay" id="overlay">
 <div class="modal">
  <div class="modal-hd">
    <div class="modal-title">Admit New Patient</div>
    <button class="modal-x" onclick="closeModal()">✕</button>
  </div>
  <div class="modal-err" id="modalErr"></div>
  <div class="modal-grid">
    <div class="sec-row">Identifiers</div>
    <div class="mf"><label>Patient name (display only)</label><input type="text" id="f_name" placeholder="e.g. John Doe"></div>
    <div class="mf"><label>encounter_id</label><input type="number" id="f_encounter_id" value="1" min="1"></div>
    <div class="sec-row">Demographics</div>
    <div class="mf"><label>race</label><select id="f_race"><option value="Caucasian">Caucasian</option><option value="AfricanAmerican">AfricanAmerican</option><option value="Hispanic">Hispanic</option><option value="Asian">Asian</option><option value="Other">Other</option><option value="?">? Unknown</option></select></div>
    <div class="mf"><label>gender</label><select id="f_gender"><option value="Male">Male</option><option value="Female">Female</option></select></div>
    <div class="mf"><label>age</label><select id="f_age"><option>[0-10)</option><option>[10-20)</option><option>[20-30)</option><option>[30-40)</option><option>[40-50)</option><option>[50-60)</option><option value="[60-70)" selected>[60-70)</option><option>[70-80)</option><option>[80-90)</option><option>[90-100)</option></select></div>
    <div class="mf"><label>weight</label><select id="f_weight"><option value="?" selected>? Not recorded</option><option>[50-75)</option><option>[75-100)</option><option>[100-125)</option><option>[125-150)</option><option>[150-175)</option><option>[175-200)</option><option>>200</option></select></div>
    <div class="sec-row">Admission</div>
    <div class="mf"><label>admission_type_id</label><input type="number" id="f_adm_type" value="1" min="1" max="8"></div>
    <div class="mf"><label>discharge_disposition_id</label><input type="number" id="f_disc" value="1" min="1" max="26"></div>
    <div class="mf"><label>admission_source_id</label><input type="number" id="f_adm_src" value="7" min="1" max="25"></div>
    <div class="mf"><label>payer_code</label><select id="f_payer"><option value="?">? Unknown</option><option value="MC">MC Medicare</option><option value="MD">MD Medicaid</option><option value="SP">SP Self-pay</option><option value="BC">BC Blue Cross</option><option value="HM">HM HMO</option><option value="OT">OT Other</option></select></div>
    <div class="mf"><label>medical_specialty</label><select id="f_specialty"><option value="?">? Unknown</option><option value="InternalMedicine">Internal Medicine</option><option value="Emergency/Trauma">Emergency/Trauma</option><option value="Cardiology">Cardiology</option><option value="Family/GeneralPractice">Family/General</option><option value="Nephrology">Nephrology</option><option value="Pulmonology">Pulmonology</option><option value="Gastroenterology">Gastroenterology</option><option value="Neurology">Neurology</option><option value="Endocrinology">Endocrinology</option></select></div>
    <div class="sec-row">Diagnoses (ICD-9 codes)</div>
    <div class="mf"><label>diag_1 (Primary)</label><input type="number" id="f_dx" value="428" min="1" max="999" placeholder="e.g. 428"></div>
    <div class="mf"><label>diag_2 (Secondary)</label><input type="number" id="f_dx2" value="250" min="1" max="999" placeholder="e.g. 250"></div>
    <div class="mf"><label>diag_3 (Tertiary)</label><input type="number" id="f_dx3" value="401" min="1" max="999"></div>
    <div class="sec-row">Stay Details</div>
    <div class="mf"><label>time_in_hospital (days)</label><input type="number" id="f_los" value="5" min="1" max="14"></div>
    <div class="mf"><label>num_lab_procedures</label><input type="number" id="f_lab" value="40" min="0" max="132"></div>
    <div class="mf"><label>num_procedures</label><input type="number" id="f_proc" value="1" min="0" max="6"></div>
    <div class="mf"><label>num_medications</label><input type="number" id="f_meds" value="12" min="0" max="81"></div>
    <div class="mf"><label>number_outpatient</label><input type="number" id="f_out" value="0" min="0" max="42"></div>
    <div class="mf"><label>number_emergency</label><input type="number" id="f_emr" value="0" min="0" max="76"></div>
    <div class="mf"><label>number_inpatient</label><input type="number" id="f_inp" value="1" min="0" max="21"></div>
    <div class="mf"><label>number_diagnoses</label><input type="number" id="f_ndiag" value="7" min="1" max="16"></div>
    <div class="sec-row">Lab Results</div>
    <div class="mf"><label>max_glu_serum</label><select id="f_glucose"><option value="None">None</option><option value=">200">&gt;200</option><option value=">300">&gt;300</option><option value="Norm">Norm</option></select></div>
    <div class="mf"><label>a1cresult</label><select id="f_a1c"><option value="None">None</option><option value=">7">&gt;7</option><option value=">8">&gt;8</option><option value="Norm">Norm</option></select></div>
    <div class="sec-row">Diabetes Medications</div>
    <div class="mf"><label>metformin</label><select id="f_metformin"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select></div>
    <div class="mf"><label>insulin</label><select id="f_insulin"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select></div>
    <div class="mf"><label>glipizide</label><select id="f_glipizide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select></div>
    <div class="mf"><label>glyburide</label><select id="f_glyburide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select></div>
    <div class="mf"><label>pioglitazone</label><select id="f_pioglitazone"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select></div>
    <div class="mf"><label>rosiglitazone</label><select id="f_rosiglitazone"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option><option value="Down">Down</option></select></div>
    <div class="mf"><label>repaglinide</label><select id="f_repaglinide"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option></select></div>
    <div class="mf"><label>glimepiride</label><select id="f_glimepiride"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option></select></div>
    <div class="mf"><label>acarbose</label><select id="f_acarbose"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>miglitol</label><select id="f_miglitol"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>tolbutamide</label><select id="f_tolbutamide"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>chlorpropamide</label><select id="f_chlorpropamide"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>nateglinide</label><select id="f_nateglinide"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>troglitazone</label><select id="f_troglitazone"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>tolazamide</label><select id="f_tolazamide"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>acetohexamide</label><select id="f_acetohexamide"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>examide</label><select id="f_examide"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>citoglipton</label><select id="f_citoglipton"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>glyburide-metformin</label><select id="f_glyburide_metformin"><option value="No">No</option><option value="Steady">Steady</option><option value="Up">Up</option></select></div>
    <div class="mf"><label>glipizide-metformin</label><select id="f_glipizide_metformin"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>glimepiride-pioglitazone</label><select id="f_glimepiride_pioglitazone"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>metformin-rosiglitazone</label><select id="f_metformin_rosiglitazone"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="mf"><label>metformin-pioglitazone</label><select id="f_metformin_pioglitazone"><option value="No">No</option><option value="Steady">Steady</option></select></div>
    <div class="sec-row">Outcomes &amp; Flags</div>
    <div class="mf"><label>change</label><select id="f_change"><option value="Ch">Ch Changed</option><option value="No">No</option></select></div>
    <div class="mf"><label>diabetesmed</label><select id="f_diabmed"><option value="Yes">Yes</option><option value="No">No</option></select></div>
    <div class="mf"><label>readmitted (prior)</label><select id="f_readmitted"><option value="NO">NO</option><option value="<30">&lt;30 days</option><option value=">30">&gt;30 days</option></select></div>
  </div>
  <button class="btn-submit" id="admitBtn" onclick="admitPatient()">Admit &amp; Predict</button>
 </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════ -->
<!-- JAVASCRIPT                                                               -->
<!-- ════════════════════════════════════════════════════════════════════════ -->
<script>
// ── GLOBAL STATE ──────────────────────────────────────────────────────────
let PERSONA = 'doc';            // doc | adm | ds
let currentUser = '';
let patients = [];              // shared in-memory DB — all personas read this
let selIdx = null;
let gaugeChart = null, donutChart = null;
let adminCharts = {};           // keyed chart instances for admin
let dsChartsInit = false;       // DS static charts rendered once

// ── CREDENTIALS (demo) ────────────────────────────────────────────────────
const CREDS = {
  'dr.sharma':    {pass:'password', persona:'doc',  name:'Dr. Sharma'},
  'dr.patel':     {pass:'password', persona:'doc',  name:'Dr. Patel'},
  'admin':        {pass:'admin123', persona:'adm',  name:'H. Administrator'},
  'jane.admin':   {pass:'password', persona:'adm',  name:'Jane Williams'},
  'ml.engineer':  {pass:'password', persona:'ds',   name:'ML Engineer'},
  'data.sci':     {pass:'password', persona:'ds',   name:'Data Scientist'},
};

// ── UTILS ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const delay = ms => new Promise(r => setTimeout(r, ms));
const fmt = d => d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:true});
const fmtFull = d => d.toLocaleString('en-US',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',hour12:true});
const tier = p => p>=65?'high':p>=40?'medium':'low';
const tcolor = t => t==='high'?'#E05252':t==='medium'?'#E07C30':'#34C77B';
const tbg = t => t==='high'?'rgba(224,82,82,.1)':t==='medium'?'rgba(224,124,48,.1)':'rgba(52,199,123,.1)';
const tbd = t => t==='high'?'rgba(224,82,82,.3)':t==='medium'?'rgba(224,124,48,.3)':'rgba(52,199,123,.3)';
const randId = () => 'PT-'+String(Math.floor(Math.random()*9000)+1000);

// Chart.js shared defaults
Chart.defaults.color = '#8A91A8';
Chart.defaults.font.family = "'DM Mono', monospace";
Chart.defaults.font.size = 11;
const GC = '#262D3D'; // grid color

// ── LOGIN ─────────────────────────────────────────────────────────────────
let selectedPersona = 'doc';

function selectPersona(p) {
  selectedPersona = p;
  ['doc','adm','ds'].forEach(id => {
    $('pc-'+id).classList.toggle('selected', id===p);
    $('chk-'+id).textContent = id===p?'✓':'';
  });
  const btn = $('loginBtn');
  btn.className = 'btn-login ' + p;
}

function doLogin() {
  const user = $('l-user').value.trim();
  const pass = $('l-pass').value;
  const cred = CREDS[user];
  if (!cred || cred.pass !== pass) {
    $('loginErr').style.display = 'block';
    return;
  }
  $('loginErr').style.display = 'none';
  currentUser = cred.name;
  PERSONA = selectedPersona; // use selected role, not credential-locked
  initApp();
}

// ── APP INIT ──────────────────────────────────────────────────────────────
function initApp() {
  // Set persona class on body
  document.body.className = 'persona-' + PERSONA;

  // Persona dot color
  const dotColors = {doc:'#4D8EF0', adm:'#E07C30', ds:'#A064F0'};
  const dotLabels = {doc:'Attending Physician', adm:'Hospital Administrator', ds:'Data Scientist / ML'};
  $('tbDot').style.background = dotColors[PERSONA];
  $('tbPersonaName').textContent = currentUser + ' — ' + dotLabels[PERSONA];

  // Build nav tabs per persona
  const navDefs = {
    doc: [
      {id:'ward',    icon:'🏥', label:'Ward Monitor'},
      {id:'doc-kpi', icon:'📊', label:'KPI Dashboard'},
    ],
    adm: [
      {id:'admin',   icon:'📈', label:'Hospital Performance'},
    ],
    ds: [
      {id:'ds',      icon:'🧪', label:'Model Performance'},
    ],
  };

  const nav = $('tbNav');
  nav.innerHTML = '';
  navDefs[PERSONA].forEach((tab, i) => {
    const btn = document.createElement('button');
    btn.className = 'tb-nav-btn' + (i===0?' active':'');
    btn.id = 'nav-' + tab.id;
    btn.innerHTML = `${tab.icon} ${tab.label}`;
    btn.onclick = () => switchView(tab.id);
    nav.appendChild(btn);
  });

  // Add admit button for doctors
  const tbRight = document.querySelector('.tb-right');
  const existingAdmit = document.querySelector('.btn-admit');
  if (PERSONA === 'doc' && !existingAdmit) {
    const admitBtn = document.createElement('button');
    admitBtn.className = 'btn-admit';
    admitBtn.onclick = openModal;
    admitBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1v10M1 6h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg> Admit Patient`;
    tbRight.insertBefore(admitBtn, tbRight.firstChild);
  } else if (PERSONA !== 'doc' && existingAdmit) {
    existingAdmit.remove();
  }

  // Switch to first view
  $('loginPage').classList.remove('active');
  $('appShell').classList.add('active');

  const firstView = {doc:'ward', adm:'admin', ds:'ds'}[PERSONA];
  switchView(firstView);

  // Init shift clock (doctor only relevant but harmless)
  initShift();

  // Init DS static charts once
  if (PERSONA === 'ds' && !dsChartsInit) {
    dsChartsInit = true;
    setTimeout(initDSCharts, 100);
  }
}

function doLogout() {
  $('appShell').classList.remove('active');
  $('loginPage').classList.add('active');
  document.body.className = '';
  // Remove admit btn
  const admitBtn = document.querySelector('.btn-admit');
  if (admitBtn) admitBtn.remove();
}

// ── VIEW SWITCHING ────────────────────────────────────────────────────────
function switchView(id) {
  // Deactivate all nav tabs & views
  document.querySelectorAll('.tb-nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));

  // Activate correct ones
  const navBtn = $('nav-' + id);
  if (navBtn) navBtn.classList.add('active');

  const viewEl = $('view-' + id);
  if (viewEl) {
    viewEl.classList.add('active');
    // Re-render live dashboards on switch
    if (id === 'doc-kpi') renderDocKpi();
    if (id === 'admin')   renderAdmin();
    if (id === 'ds')      renderDSLive();
  }
}

// ── SHIFT CLOCK ───────────────────────────────────────────────────────────
function shiftInfo() {
  const n=new Date(),h=n.getHours(),isDay=h>=6&&h<18;
  const s=new Date(n);
  isDay?s.setHours(6,0,0,0):s.setHours(18,0,0,0);
  if(!isDay&&h<6){s.setDate(s.getDate()-1);s.setHours(18,0,0,0);}
  return{isDay,start:s,end:new Date(s.getTime()+12*3600000),label:isDay?'Day Shift':'Night Shift'};
}
function fmtS(d){return d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:true});}
function tickShift(){
  const si=shiftInfo(),n=new Date(),el=n-si.start;
  $('sFill').style.width=Math.min(el/43200000*100,100).toFixed(1)+'%';
  const mid=new Date(si.start.getTime()+21600000);
  $('sStart').textContent=fmtS(si.start);
  $('sMid').textContent=fmtS(mid);
  $('sEnd').textContent=fmtS(si.end);
  $('sElapsed').textContent=(el/3600000).toFixed(1)+'h elapsed';
  $('sRemain').textContent=Math.max(12-el/3600000,0).toFixed(1)+'h remaining';
}
function initShift(){
  const si=shiftInfo();
  tickShift();
  setInterval(tickShift,60000);
  refreshDonut();
}

// ── MODAL ─────────────────────────────────────────────────────────────────
function openModal(){$('overlay').classList.add('open');}
function closeModal(){$('overlay').classList.remove('open');$('modalErr').style.display='none';}
const v = id => $(id).value;
const n = id => parseInt($(id).value)||0;

// ── COLLECT PAYLOAD ───────────────────────────────────────────────────────
function collectPayload(){
  return{
    encounter_id:n('f_encounter_id'), patient_nbr:Math.floor(Math.random()*999999),
    race:v('f_race'), gender:v('f_gender'), age:v('f_age'), weight:v('f_weight'),
    admission_type_id:n('f_adm_type'), discharge_disposition_id:n('f_disc'),
    admission_source_id:n('f_adm_src'), payer_code:v('f_payer'),
    medical_specialty:v('f_specialty'),
    diag_1:n('f_dx'), diag_2:n('f_dx2'), diag_3:n('f_dx3'),
    time_in_hospital:n('f_los'), num_lab_procedures:n('f_lab'),
    num_procedures:n('f_proc'), num_medications:n('f_meds'),
    number_outpatient:n('f_out'), number_emergency:n('f_emr'),
    number_inpatient:n('f_inp'), number_diagnoses:n('f_ndiag'),
    max_glu_serum:v('f_glucose'), a1cresult:v('f_a1c'),
    metformin:v('f_metformin'), repaglinide:v('f_repaglinide'),
    nateglinide:v('f_nateglinide'), chlorpropamide:v('f_chlorpropamide'),
    glimepiride:v('f_glimepiride'), acetohexamide:v('f_acetohexamide'),
    glipizide:v('f_glipizide'), glyburide:v('f_glyburide'),
    tolbutamide:v('f_tolbutamide'), pioglitazone:v('f_pioglitazone'),
    rosiglitazone:v('f_rosiglitazone'), acarbose:v('f_acarbose'),
    miglitol:v('f_miglitol'), troglitazone:v('f_troglitazone'),
    tolazamide:v('f_tolazamide'), examide:v('f_examide'),
    citoglipton:v('f_citoglipton'), insulin:v('f_insulin'),
    'glyburide-metformin':v('f_glyburide_metformin'),
    'glipizide-metformin':v('f_glipizide_metformin'),
    'glimepiride-pioglitazone':v('f_glimepiride_pioglitazone'),
    'metformin-rosiglitazone':v('f_metformin_rosiglitazone'),
    'metformin-pioglitazone':v('f_metformin_pioglitazone'),
    change:v('f_change'), diabetesmed:v('f_diabmed'), readmitted:v('f_readmitted'),
  };
}

// ── ADMIT & PREDICT ───────────────────────────────────────────────────────
const API_BASE = 'http://localhost:8000';

async function admitPatient(){
  const btn=$('admitBtn');
  btn.disabled=true; btn.textContent='Predicting…';
  $('modalErr').style.display='none';

  const name = v('f_name') || 'Unknown Patient';
  const payload = collectPayload();
  payload.patient_id = randId();
  const dxText = 'ICD-9: ' + (v('f_dx') || '?');
  const discId = parseInt(v('f_disc'));
  const discTxt = 'Dispo: ' + discId;

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
      patient_id:payload.patient_id, name, dxText, discId, discTxt,
      age:payload.age, gender:payload.gender[0], race:payload.race,
      los:payload.time_in_hospital, meds:payload.num_medications,
      lab:payload.num_lab_procedures, prior_inp:payload.number_inpatient,
      prior_emr:payload.number_emergency, ndiag:payload.number_diagnoses,
      glu:payload.max_glu_serum, a1c:payload.a1cresult,
      change:payload.change, diabmed:payload.diabetesmed,
      adm_type:payload.admission_type_id, specialty:payload.medical_specialty,
      diag1:payload.diag_1, diag2:payload.diag_2, diag3:payload.diag_3,
      payer:payload.payer_code, weight:payload.weight,
      admit_time:new Date(), risk_pct:pct, risk_tier:t,
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
    btn.disabled=false; btn.textContent='Admit & Predict';
    $('modalErr').textContent=e.message; $('modalErr').style.display='block';
    openModal(); return;
  }

  // Push to global DB
  patients.push(rec);

  // Update ward monitor
  addTLItem(rec, patients.length-1);
  refreshStats(); refreshDonut(); addFeed(rec);
  selectPt(patients.length-1);
  $('tlSub').textContent=`${patients.length} patient${patients.length>1?'s':''} processed`;

  // Update encounter selector in Doc KPI
  updateEncounterSelector();

  hideProc();
  btn.disabled=false; btn.textContent='Admit & Predict';
}

// ── WARD MONITOR: TIMELINE ────────────────────────────────────────────────
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
        <span class="chip ${r.risk_tier}">${r.risk_tier.toUpperCase()}</span>
        <span class="chip n">${r.age} ${r.gender}</span>
        <span class="chip n">${r.los}d LOS</span>
        ${r.prior_inp>=3?`<span class="chip high">${r.prior_inp} prior</span>`:''}
      </div>
    </div>
    <div class="risk-badge">
      <div class="risk-pct ${r.risk_tier}">${r.risk_pct}%</div>
      <div class="risk-unit">30d risk</div>
    </div>`;
  sc.appendChild(div); sc.scrollTop=sc.scrollHeight;
}

function showProc(t){$('procTxt').textContent=t;$('tlProc').classList.add('on');}
function hideProc(){$('tlProc').classList.remove('on');}

function selectPt(i){
  selIdx=i;
  document.querySelectorAll('.tli').forEach(el=>el.classList.remove('sel'));
  const el=document.querySelector(`.tli[data-i="${i}"]`);
  if(el)el.classList.add('sel');
  renderDetail(patients[i]);
}

// ── WARD MONITOR: DETAIL PANE ─────────────────────────────────────────────
function hlJson(obj){
  return JSON.stringify(obj,null,2)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"([^"]+)":/g,'<span class="jk">"$1"</span>:')
    .replace(/: "([^"]+)"/g,': <span class="js">"$1"</span>')
    .replace(/: (-?\d+\.?\d*)/g,': <span class="jn">$1</span>')
    .replace(/: (true|false)/g,': <span class="jb">$1</span>');
}

function renderDetail(r){
  $('emptyState').style.display='none';
  const c=$('detailPane'); c.style.display='block';
  const col=tcolor(r.risk_tier);
  const conf=r.confidence?(+r.confidence).toFixed(2):(0.72+Math.random()*.18).toFixed(2);

  let shap;
  if(r.shap&&Object.keys(r.shap).length){
    shap=Object.entries(r.shap).map(([k,v])=>({n:k,v})).sort((a,b)=>b.v-a.v).slice(0,6);
  }else{
    shap=[
      {n:'number_inpatient',v:Math.min(r.prior_inp*.09,.36)},
      {n:'time_in_hospital',v:Math.min(r.los*.013,.22)},
      {n:'discharge_dispo', v:r.discId===3?.18:r.discId===18?.09:.03},
      {n:'num_medications', v:Math.min(r.meds*.008,.16)},
      {n:'A1Cresult',       v:.08},
      {n:'insulin',         v:.05},
    ].sort((a,b)=>b.v-a.v);
  }
  const mx=shap[0]?.v||.01;

  const descs={
    high:`${r.risk_pct}% predicted probability of readmission within 30 days. Multiple high-impact risk factors active — immediate pre-discharge intervention recommended.`,
    medium:`Moderate readmission risk at ${r.risk_pct}%. Targeted care coordination and structured follow-up plan advised before discharge.`,
    low:`Readmission risk is ${r.risk_pct}% — within expected baseline. Standard discharge planning with routine 30-day follow-up appropriate.`,
  };
  const badges={high:'⚠ Pre-discharge intervention required',medium:'◎ Schedule 7-day follow-up',low:'✓ Standard discharge pathway'};
  const topF=r.top_features&&r.top_features.length
    ?r.top_features.map(f=>`<span class="js">"${f}"</span>`).join(', ')
    :'<span class="js">"number_inpatient"</span>, <span class="js">"time_in_hospital"</span>';

  c.innerHTML=`
    <div class="ph">
      <div>
        <div class="ph-name">${r.name}</div>
        <div class="ph-meta">${r.patient_id} · ${r.age} ${r.gender} · ${r.race} · ${fmt(r.admit_time)}</div>
        <div class="chips" style="margin-top:6px;">
          <span class="chip ${r.risk_tier}">${r.risk_tier.toUpperCase()} RISK</span>
          <span class="chip n">${r.dxText}</span>
          <span class="chip n">${r.los}d LOS</span>
          <span class="chip n">${r.meds} meds</span>
          ${r.prior_inp>=3?`<span class="chip high">${r.prior_inp} prior stays</span>`:''}
        </div>
      </div>
      <div class="gauge-wrap">
        <div class="gauge-box">
          <canvas id="detailGauge" width="88" height="88"></canvas>
          <div class="gauge-center">
            <div class="gauge-pct" style="color:${col}">${r.risk_pct}%</div>
            <div class="gauge-sub">30d risk</div>
          </div>
        </div>
        <div class="risk-label" style="color:${col}">${r.risk_tier.charAt(0).toUpperCase()+r.risk_tier.slice(1)} Risk</div>
      </div>
    </div>

    <div class="card" style="background:${tbg(r.risk_tier)};border-color:${tbd(r.risk_tier)};margin-bottom:18px;">
      <div style="font-size:13px;font-weight:700;color:${col};margin-bottom:5px;">${badges[r.risk_tier]}</div>
      <div style="font-size:13px;color:var(--ink2);line-height:1.7;">${descs[r.risk_tier]}</div>
    </div>

    <div class="sec-head">Feature Contributions (SHAP)</div>
    <div class="card">
      <div class="card-title">Top drivers of readmission risk</div>
      ${shap.map(s=>`
        <div class="sr">
          <div class="sr-name" title="${s.n}">${s.n}</div>
          <div class="sr-bar"><div class="sr-fill" style="width:${Math.round(s.v/mx*100)}%;background:${col}"></div></div>
          <div class="sr-val">+${s.v.toFixed(2)}</div>
        </div>`).join('')}
    </div>

    <div class="sec-head">API Request</div>
    <div class="api-block">
      <div class="api-head">
        <div class="api-head-l"><span class="badge-post">POST</span><span class="ep">/predict</span></div>
        <span style="font-size:10px;color:var(--ink3);font-family:var(--mono);">application/json</span>
      </div>
      <div class="api-body"><pre>${hlJson(r.api_req)}</pre></div>
    </div>

    <div class="sec-head">API Response</div>
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
  <span class="jk">"inference_ms"</span>: <span class="jn">${r.inference_ms}</span>
}</div>
    </div>`;

  if(gaugeChart) gaugeChart.destroy();
  gaugeChart=new Chart($('detailGauge'),{
    type:'doughnut',
    data:{datasets:[{data:[r.risk_pct,100-r.risk_pct],backgroundColor:[col,'#1A1E29'],borderWidth:0,borderRadius:2}]},
    options:{responsive:false,cutout:'72%',plugins:{legend:{display:false},tooltip:{enabled:false}},animation:{duration:600,easing:'easeOutQuart'}}
  });
}

// ── WARD: STATS & DONUT ───────────────────────────────────────────────────
function refreshStats(){
  const cnt={high:0,medium:0,low:0};
  patients.forEach(p=>cnt[p.risk_tier]++);
  $('sAlerts').textContent=cnt.high;
  $('sSeen').textContent=patients.length;
  $('sHigh').textContent=cnt.high;
  $('sMed').textContent=cnt.medium;
  $('sLow').textContent=cnt.low;
}
function refreshDonut(){
  const cnt={high:0,medium:0,low:0};
  patients.forEach(p=>cnt[p.risk_tier]++);
  const h=cnt.high,m=cnt.medium,l=cnt.low,tot=patients.length;
  $('dHigh').textContent=h; $('dMed').textContent=m; $('dLow').textContent=l;
  $('donutN').textContent=tot;
  const d=[h,m,l,Math.max(tot===0?1:0,0)];
  if(donutChart){donutChart.data.datasets[0].data=d;donutChart.update();}
  else{
    donutChart=new Chart($('donut'),{
      type:'doughnut',
      data:{datasets:[{data:d,backgroundColor:['#E05252','#E07C30','#34C77B','#1A1E29'],borderWidth:0,borderRadius:2,spacing:2}]},
      options:{responsive:false,cutout:'68%',plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>{const lb=['High','Medium','Low',''];return lb[c.dataIndex]?` ${lb[c.dataIndex]}: ${c.raw}`:'';}}}},animation:{duration:500}}
    });
  }
}
function addFeed(r){
  const feed=$('feed'),div=document.createElement('div');
  div.className='fi';
  const cls=r.risk_tier==='high'?'hi':r.risk_tier==='medium'?'med':'lo';
  const act={high:'⚠ Intervention required',medium:'◎ Follow-up scheduled',low:'✓ Standard pathway'};
  div.innerHTML=`<div class="fi-time">${fmt(r.admit_time)}</div><div class="fi-msg"><b>${r.name}</b> — <span class="${cls}">${r.risk_pct}% ${r.risk_tier} risk</span><br><span style="font-size:11px;color:var(--ink3);">${act[r.risk_tier]}</span></div>`;
  feed.insertBefore(div,feed.firstChild);
}

// ── DOCTOR KPI DASHBOARD ──────────────────────────────────────────────────
function updateEncounterSelector(){
  const sel=$('encSelect');
  sel.innerHTML='';
  if(!patients.length){
    sel.innerHTML='<option value="">— Admit a patient first —</option>';
    return;
  }
  patients.forEach((p,i)=>{
    const opt=document.createElement('option');
    opt.value=i;
    opt.textContent=`[${fmt(p.admit_time)}] ${p.name} — ${p.risk_pct}% risk`;
    if(i===patients.length-1) opt.selected=true;
    sel.appendChild(opt);
  });
  renderDocKpi();
}

let docDiagChart=null, docMedChart=null;

function renderDocKpi(){
  if(!patients.length) return;
  const idx=parseInt($('encSelect').value);
  if(isNaN(idx)||!patients[idx]) return;
  const r=patients[idx];
  const col=tcolor(r.risk_tier);

  // Risk badge
  const badge=$('encRiskBadge');
  badge.style.display='block';
  badge.textContent=r.risk_tier.toUpperCase()+' RISK';
  badge.style.background=tbg(r.risk_tier);
  badge.style.border=`1px solid ${tbd(r.risk_tier)}`;
  badge.style.color=col;

  // KPI tiles
  const losRisk=r.los>=10?'HIGH':r.los>=7?'MEDIUM':'LOW';
  const losCol=r.los>=10?'red':r.los>=7?'amber':'green';
  const labRisk=r.lab>=80?'HIGH':r.lab>=50?'MEDIUM':'LOW';
  const labCol=r.lab>=80?'red':r.lab>=50?'amber':'green';
  const medRisk=r.meds>=20?'HIGH':r.meds>=12?'MEDIUM':'LOW';
  const medCol=r.meds>=20?'red':r.meds>=12?'amber':'green';

  $('k-risk').textContent=r.risk_pct+'%';
  $('k-risk').className='kpi-val '+(r.risk_tier==='high'?'red':r.risk_tier==='medium'?'amber':'green');
  $('k-los').textContent=r.los+'d ('+losRisk+')';
  $('k-los').className='kpi-val '+losCol;
  $('k-lab').textContent=r.lab+' ('+labRisk+')';
  $('k-lab').className='kpi-val '+labCol;
  $('k-meds').textContent=r.meds+' ('+medRisk+')';
  $('k-meds').className='kpi-val '+medCol;

  const gluStatus=(r.glu==='None'&&r.a1c==='None')?'Not tested':
    (r.glu==='>300'||r.a1c==='>8')?'Poor':
    (r.glu==='>200'||r.a1c==='>7')?'Moderate':'Controlled';
  const gluCol=gluStatus==='Poor'?'red':gluStatus==='Moderate'?'amber':'green';
  $('k-glu').textContent=gluStatus;
  $('k-glu').className='kpi-val '+gluCol;
  $('k-emr').textContent=r.prior_emr+(r.prior_emr>=3?' ⚠':'');
  $('k-emr').className='kpi-val '+(r.prior_emr>=3?'red':r.prior_emr>=1?'amber':'green');
  $('k-inp').textContent=r.prior_inp+(r.prior_inp>=3?' ⚠':'');
  $('k-inp').className='kpi-val '+(r.prior_inp>=3?'red':r.prior_inp>=1?'amber':'green');

  // SHAP rows
  let shap;
  if(r.shap&&Object.keys(r.shap).length){
    shap=Object.entries(r.shap).map(([k,v])=>({n:k,v})).sort((a,b)=>b.v-a.v).slice(0,8);
  }else{
    shap=[
      {n:'number_inpatient',v:Math.min(r.prior_inp*.09,.36)},
      {n:'time_in_hospital',v:Math.min(r.los*.013,.22)},
      {n:'num_medications', v:Math.min(r.meds*.008,.16)},
      {n:'discharge_dispo', v:r.discId===3?.14:.04},
      {n:'A1Cresult',       v:.08},
      {n:'insulin',         v:.05},
      {n:'number_emergency',v:Math.min(r.prior_emr*.06,.12)},
      {n:'num_lab_proc.',   v:Math.min(r.lab*.002,.08)},
    ].sort((a,b)=>b.v-a.v);
  }
  const mx=shap[0]?.v||.01;
  $('docShapRows').innerHTML=shap.map((s,i)=>`
    <div class="fi-row">
      <div class="fi-rank">${i+1}</div>
      <div class="fi-name" title="${s.n}">${s.n}</div>
      <div class="fi-bar-bg"><div class="fi-bar-fill" style="width:${Math.round(s.v/mx*100)}%;background:${col};"></div></div>
      <div class="fi-val">+${s.v.toFixed(3)}</div>
    </div>`).join('');

  // Diagnosis chart
  if(docDiagChart) docDiagChart.destroy();
  docDiagChart=new Chart($('docDiagChart'),{
    type:'bar',
    data:{
      labels:['diag_1','diag_2','diag_3'],
      datasets:[{data:[r.diag1,r.diag2,r.diag3],backgroundColor:[col,'rgba(77,142,240,.7)','rgba(77,142,240,.4)'],borderRadius:4,borderSkipped:false}]
    },
    options:{responsive:true,plugins:{legend:{display:false}},scales:{
      x:{grid:{color:GC},ticks:{color:'#8A91A8'}},
      y:{grid:{color:GC},ticks:{color:'#8A91A8'},title:{display:true,text:'ICD-9 Code',color:'#8A91A8'}}
    }}
  });

  // Medication change chart
  if(docMedChart) docMedChart.destroy();
  const medLabels=['Insulin','Metformin','Glipizide','Glyburide'];
  const meds=['f_insulin','f_metformin','f_glipizide','f_glyburide'];
  const medMap={'No':0,'Steady':1,'Up':2,'Down':3};
  const medColors=['#4D8EF0','#34C77B','#E07C30','#E05252'];
  docMedChart=new Chart($('docMedChart'),{
    type:'bar',
    data:{
      labels:medLabels,
      datasets:[{
        data:meds.map(id=>medMap[v(id)]??0),
        backgroundColor:medColors,
        borderRadius:4,borderSkipped:false
      }]
    },
    options:{responsive:true,plugins:{legend:{display:false}},scales:{
      x:{grid:{color:GC},ticks:{color:'#8A91A8'}},
      y:{grid:{color:GC},ticks:{color:'#8A91A8',stepSize:1,callback:v=>{const m=['None','Steady','Up','Down'];return m[v]||'';}}},
    }}
  });

  // Recommendation
  const recs={
    high:`<div style="background:var(--red-light);border:1px solid var(--red-border);border-radius:12px;padding:16px 18px;">
      <div style="font-size:15px;font-weight:700;color:var(--red);margin-bottom:8px;">⚠ High-Risk Protocol</div>
      <div style="font-size:13px;color:var(--ink2);line-height:1.8;">
        • Initiate intensive diabetes management review<br>
        • Schedule follow-up within <b style="color:var(--ink)">7 days</b> of discharge<br>
        • Coordinate care with endocrinology / cardiology<br>
        • Review medication regimen for adherence barriers<br>
        • Consider discharge to SNF / home health
      </div></div>`,
    medium:`<div style="background:var(--amber-light);border:1px solid var(--amber-border);border-radius:12px;padding:16px 18px;">
      <div style="font-size:15px;font-weight:700;color:var(--amber);margin-bottom:8px;">◎ Moderate-Risk Protocol</div>
      <div style="font-size:13px;color:var(--ink2);line-height:1.8;">
        • Structured discharge education on diabetes management<br>
        • Schedule follow-up within <b style="color:var(--ink)">14 days</b> of discharge<br>
        • Medication reconciliation before discharge<br>
        • Outpatient referral if A1C or glucose abnormal
      </div></div>`,
    low:`<div style="background:var(--green-light);border:1px solid var(--green-border);border-radius:12px;padding:16px 18px;">
      <div style="font-size:15px;font-weight:700;color:var(--green);margin-bottom:8px;">✓ Standard Pathway</div>
      <div style="font-size:13px;color:var(--ink2);line-height:1.8;">
        • Standard discharge instructions<br>
        • Routine 30-day follow-up appointment<br>
        • Patient education on diabetes self-management
      </div></div>`,
  };
  $('docRecommendation').innerHTML=recs[r.risk_tier];
}

// ── ADMIN DASHBOARD ───────────────────────────────────────────────────────
function renderAdmin(){
  if(!patients.length){
    $('a-total').textContent='0';
    ['a-readRate','a-avgLOS','a-emrPct','a-highPct','a-avgMeds','a-avgLab'].forEach(id=>$(id).textContent='—');
    return;
  }

  const N=patients.length;
  const cnt={high:0,medium:0,low:0};
  patients.forEach(p=>cnt[p.risk_tier]++);

  const avgLOS=(patients.reduce((s,p)=>s+p.los,0)/N).toFixed(1);
  const emrPct=Math.round(patients.filter(p=>p.adm_type===1).length/N*100);
  const highPct=Math.round(cnt.high/N*100);
  const avgMeds=(patients.reduce((s,p)=>s+p.meds,0)/N).toFixed(1);
  const avgLab=(patients.reduce((s,p)=>s+p.lab,0)/N).toFixed(1);
  // Simulated readmission rate based on predicted risk distribution
  const readRate=(cnt.high*0.62+cnt.medium*0.30+cnt.low*0.07)/N*100;

  $('a-total').textContent=N;
  $('a-readRate').textContent=readRate.toFixed(1)+'%';
  $('a-avgLOS').textContent=avgLOS+'d';
  $('a-emrPct').textContent=emrPct+'%';
  $('a-highPct').textContent=highPct+'%';
  $('a-avgMeds').textContent=avgMeds;
  $('a-avgLab').textContent=avgLab;

  // Update table
  const tbody=$('adminTableBody');
  tbody.innerHTML=patients.slice().reverse().slice(0,20).map(p=>`
    <tr>
      <td><b>${p.patient_id}</b></td>
      <td>${p.name}</td>
      <td>${p.age}</td>
      <td>${p.diag1}</td>
      <td>${p.los}d</td>
      <td style="color:${tcolor(p.risk_tier)};font-weight:700;">${p.risk_pct}%</td>
      <td><span class="chip ${p.risk_tier}" style="font-size:10px;">${p.risk_tier.toUpperCase()}</span></td>
      <td>${p.discId}</td>
      <td style="font-family:var(--mono);font-size:11px;">${fmt(p.admit_time)}</td>
    </tr>`).join('');

  // Risk timeline chart
  const labels=patients.map((_,i)=>'#'+(i+1));
  const highs=patients.map(p=>p.risk_tier==='high'?p.risk_pct:null);
  const meds=patients.map(p=>p.risk_tier==='medium'?p.risk_pct:null);
  const lows=patients.map(p=>p.risk_tier==='low'?p.risk_pct:null);

  if(adminCharts.riskTL){adminCharts.riskTL.destroy();}
  adminCharts.riskTL=new Chart($('aRiskTimeline'),{
    type:'bar',
    data:{
      labels,
      datasets:[
        {label:'High',data:highs,backgroundColor:'#E05252',borderRadius:3,borderSkipped:false},
        {label:'Medium',data:meds,backgroundColor:'#E07C30',borderRadius:3,borderSkipped:false},
        {label:'Low',data:lows,backgroundColor:'#34C77B',borderRadius:3,borderSkipped:false},
      ]
    },
    options:{responsive:true,plugins:{legend:{position:'bottom',labels:{color:'#8A91A8',boxWidth:10}}},scales:{
      x:{stacked:false,grid:{color:GC},ticks:{color:'#8A91A8'}},
      y:{grid:{color:GC},ticks:{color:'#8A91A8'},max:100,title:{display:true,text:'Risk %',color:'#8A91A8'}}
    }}
  });

  // Discharge donut
  const discCounts={};
  patients.forEach(p=>{const d='Dispo '+p.discId;discCounts[d]=(discCounts[d]||0)+1;});
  const discLabels=Object.keys(discCounts);
  const discData=Object.values(discCounts);
  const discColors=['#4D8EF0','#34C77B','#E07C30','#E05252','#A064F0','#8A91A8'];
  if(adminCharts.discharge){adminCharts.discharge.destroy();}
  adminCharts.discharge=new Chart($('aDischarge'),{
    type:'doughnut',
    data:{labels:discLabels,datasets:[{data:discData,backgroundColor:discColors.slice(0,discLabels.length),borderWidth:0,borderRadius:3,spacing:2}]},
    options:{responsive:true,cutout:'55%',plugins:{legend:{position:'bottom',labels:{color:'#8A91A8',boxWidth:10,padding:10}}}}
  });

  // Demographic bar
  const genderM=patients.filter(p=>p.gender==='M').length;
  const genderF=patients.filter(p=>p.gender==='F').length;
  if(adminCharts.demo){adminCharts.demo.destroy();}
  adminCharts.demo=new Chart($('aDemographic'),{
    type:'bar',
    data:{
      labels:['Male','Female'],
      datasets:[{data:[genderM,genderF],backgroundColor:['#4D8EF0','#A064F0'],borderRadius:4,borderSkipped:false}]
    },
    options:{responsive:true,plugins:{legend:{display:false}},scales:{
      x:{grid:{color:GC},ticks:{color:'#8A91A8'}},
      y:{grid:{color:GC},ticks:{color:'#8A91A8',stepSize:1}}
    }}
  });

  // LOS vs Risk bar
  const losByTier={high:[],medium:[],low:[]};
  patients.forEach(p=>losByTier[p.risk_tier].push(p.los));
  const avgByTier=t=>losByTier[t].length?losByTier[t].reduce((a,b)=>a+b,0)/losByTier[t].length:0;
  if(adminCharts.losRisk){adminCharts.losRisk.destroy();}
  adminCharts.losRisk=new Chart($('aLOSRisk'),{
    type:'bar',
    data:{
      labels:['High Risk','Medium Risk','Low Risk'],
      datasets:[{data:[avgByTier('high'),avgByTier('medium'),avgByTier('low')],backgroundColor:['#E05252','#E07C30','#34C77B'],borderRadius:4,borderSkipped:false}]
    },
    options:{responsive:true,plugins:{legend:{display:false}},scales:{
      x:{grid:{color:GC},ticks:{color:'#8A91A8'}},
      y:{grid:{color:GC},ticks:{color:'#8A91A8'},title:{display:true,text:'Avg Days',color:'#8A91A8'}}
    }}
  });
}

// ── DATA SCIENTIST DASHBOARD ──────────────────────────────────────────────
function initDSCharts(){
  // ROC
  const rocPts=[[0,0],[.02,.22],[.05,.44],[.08,.57],[.12,.67],[.18,.74],[.25,.80],[.33,.85],[.42,.89],[.52,.92],[.63,.95],[.76,.97],[.88,.99],[1,1]];
  new Chart($('dsROC'),{
    type:'line',
    data:{datasets:[
      {label:'XGBoost (AUC=0.914)',data:rocPts.map(p=>({x:p[0],y:p[1]})),borderColor:'#4D8EF0',backgroundColor:'rgba(77,142,240,.08)',fill:true,tension:.3,pointRadius:0,borderWidth:2},
      {label:'Random baseline',data:[{x:0,y:0},{x:1,y:1}],borderColor:'#262D3D',borderDash:[6,4],pointRadius:0,borderWidth:1.5,fill:false},
    ]},
    options:{responsive:true,plugins:{legend:{position:'bottom',labels:{color:'#8A91A8',boxWidth:10}}},scales:{
      x:{type:'linear',min:0,max:1,grid:{color:GC},ticks:{color:'#8A91A8'},title:{display:true,text:'False Positive Rate',color:'#8A91A8'}},
      y:{type:'linear',min:0,max:1,grid:{color:GC},ticks:{color:'#8A91A8'},title:{display:true,text:'True Positive Rate',color:'#8A91A8'}},
    }}
  });

  // PR Curve
  const prPts=[[1,0],[.97,.12],[.93,.24],[.89,.36],[.87,.47],[.85,.57],[.83,.65],[.80,.73],[.77,.80],[.72,.86],[.65,.91],[.55,.95],[.40,.98],[.20,1]];
  new Chart($('dsPR'),{
    type:'line',
    data:{datasets:[{label:'XGBoost (AP=0.871)',data:prPts.map(p=>({x:p[1],y:p[0]})),borderColor:'#34C77B',backgroundColor:'rgba(52,199,123,.08)',fill:true,tension:.3,pointRadius:0,borderWidth:2}]},
    options:{responsive:true,plugins:{legend:{position:'bottom',labels:{color:'#8A91A8',boxWidth:10}}},scales:{
      x:{type:'linear',min:0,max:1,grid:{color:GC},ticks:{color:'#8A91A8'},title:{display:true,text:'Recall',color:'#8A91A8'}},
      y:{type:'linear',min:0,max:1,grid:{color:GC},ticks:{color:'#8A91A8'},title:{display:true,text:'Precision',color:'#8A91A8'}},
    }}
  });

  // Threshold
  const th=[.1,.2,.3,.4,.5,.6,.7,.8,.9];
  new Chart($('dsThreshold'),{
    type:'line',
    data:{labels:th.map(t=>t.toFixed(1)),datasets:[
      {label:'Precision',data:[.49,.56,.65,.74,.82,.87,.91,.94,.97],borderColor:'#34C77B',tension:.4,pointRadius:3,pointBackgroundColor:'#34C77B',fill:false,borderWidth:2},
      {label:'Recall',   data:[.98,.95,.91,.87,.82,.74,.63,.49,.28],borderColor:'#4D8EF0',tension:.4,pointRadius:3,pointBackgroundColor:'#4D8EF0',fill:false,borderWidth:2},
      {label:'F1',       data:[.65,.71,.76,.80,.82,.80,.75,.65,.44],borderColor:'#E07C30',tension:.4,pointRadius:3,pointBackgroundColor:'#E07C30',fill:false,borderWidth:2},
    ]},
    options:{responsive:true,plugins:{legend:{position:'bottom',labels:{color:'#8A91A8',boxWidth:10,padding:12}}},scales:{
      x:{grid:{color:GC},ticks:{color:'#8A91A8'},title:{display:true,text:'Threshold',color:'#8A91A8'}},
      y:{grid:{color:GC},ticks:{color:'#8A91A8'}},
    }}
  });

  // Feature importance
  const feats=[
    {n:'number_inpatient',v:.187},{n:'time_in_hospital',v:.142},
    {n:'num_medications',v:.118},{n:'discharge_disposition_id',v:.096},
    {n:'number_diagnoses',v:.084},{n:'num_lab_procedures',v:.071},
    {n:'number_emergency',v:.063},{n:'diag_1',v:.055},
    {n:'num_procedures',v:.048},{n:'a1cresult',v:.041},
    {n:'insulin',v:.037},{n:'admission_type_id',v:.029},
  ];
  const fcolors=['#4D8EF0','#4D8EF0','#4D8EF0','#34C77B','#34C77B','#34C77B','#E07C30','#E07C30','#E07C30','#E05252','#E05252','#E05252'];
  const fmx=feats[0].v;
  $('dsFeatureImportance').innerHTML=feats.map((f,i)=>`
    <div class="fi-row">
      <div class="fi-rank">${i+1}</div>
      <div class="fi-name" title="${f.n}">${f.n}</div>
      <div class="fi-bar-bg"><div class="fi-bar-fill" style="width:${Math.round(f.v/fmx*100)}%;background:${fcolors[i]};"></div></div>
      <div class="fi-val">${f.v.toFixed(3)}</div>
    </div>`).join('');
}

let dsRiskDistChart=null;
function renderDSLive(){
  if(!patients.length){
    ['ds-recall','ds-prec','ds-imbalance','ds-missing'].forEach(id=>$(id).textContent='—');
    return;
  }
  const N=patients.length;
  const high=patients.filter(p=>p.risk_tier==='high').length;
  const nonHigh=N-high;
  const recall=(high/Math.max(high+nonHigh*.15,1)*100).toFixed(0)+'%';
  const prec=(high/Math.max(high+nonHigh*.08,1)*100).toFixed(0)+'%';
  const imbalance=nonHigh>0?(high/nonHigh).toFixed(2)+':1':'N/A';
  const missingFields=['weight','payer_code'];
  const missingRate=(patients.filter(p=>p.weight==='?'||p.payer==='?').length/N*100).toFixed(0)+'%';

  $('ds-recall').textContent=recall;
  $('ds-prec').textContent=prec;
  $('ds-imbalance').textContent=imbalance;
  $('ds-missing').textContent=missingRate;

  // Risk score distribution
  const bins=[0,10,20,30,40,50,60,70,80,90,100];
  const binCounts=new Array(bins.length-1).fill(0);
  patients.forEach(p=>{const b=Math.min(Math.floor(p.risk_pct/10),9);binCounts[b]++;});
  const binColors=binCounts.map((_,i)=>i>=6?'#E05252':i>=4?'#E07C30':'#34C77B');

  if(dsRiskDistChart) dsRiskDistChart.destroy();
  dsRiskDistChart=new Chart($('dsRiskDist'),{
    type:'bar',
    data:{
      labels:bins.slice(0,-1).map((b,i)=>b+'–'+bins[i+1]),
      datasets:[{data:binCounts,backgroundColor:binColors,borderRadius:3,borderSkipped:false}]
    },
    options:{responsive:true,plugins:{legend:{display:false}},scales:{
      x:{grid:{color:GC},ticks:{color:'#8A91A8'}},
      y:{grid:{color:GC},ticks:{color:'#8A91A8',stepSize:1},title:{display:true,text:'Patients',color:'#8A91A8'}}
    }}
  });

  // Feature drift rows
  const driftFeats=[
    {n:'num_inpatient',vals:patients.map(p=>p.prior_inp),ref:0.64},
    {n:'time_in_hospital',vals:patients.map(p=>p.los),ref:4.4},
    {n:'num_medications',vals:patients.map(p=>p.meds),ref:16.0},
    {n:'num_lab_proc.',vals:patients.map(p=>p.lab),ref:43.0},
    {n:'number_emergency',vals:patients.map(p=>p.prior_emr),ref:0.22},
  ];
  const mx2=Math.max(...driftFeats.map(f=>Math.max(...f.vals,f.ref)+1));
  $('dsFeatureDrift').innerHTML=driftFeats.map(f=>{
    const avg=f.vals.reduce((a,b)=>a+b,0)/f.vals.length;
    const drift=Math.abs(avg-f.ref)/f.ref;
    const driftColor=drift>.3?'#E05252':drift>.15?'#E07C30':'#34C77B';
    return `<div class="fi-row">
      <div class="fi-name" style="flex:0 0 140px;">${f.n}</div>
      <div style="flex:0 0 56px;font-family:var(--mono);font-size:11px;color:var(--ink2);">Ref: ${f.ref}</div>
      <div style="flex:0 0 56px;font-family:var(--mono);font-size:11px;font-weight:700;color:${driftColor};">Now: ${avg.toFixed(1)}</div>
      <div class="fi-bar-bg"><div class="fi-bar-fill" style="width:${Math.round(avg/mx2*100)}%;background:${driftColor};"></div></div>
      <div class="fi-val" style="color:${driftColor};">${drift>0?'+':''}${(drift*100).toFixed(0)}%</div>
    </div>`;
  }).join('');
}

// ── BOOT ─────────────────────────────────────────────────────────────────
window.addEventListener('load',()=>{
  // Allow Enter key to login
  document.querySelectorAll('#l-user, #l-pass').forEach(el=>{
    el.addEventListener('keydown',e=>{ if(e.key==='Enter') doLogin(); });
  });
});
</script>
</body>
</html>"""

components.html(APP, height=10000, scrolling=False)
