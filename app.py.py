import streamlit as st
import pandas as pd
import numpy as np
import joblib
import requests
from datetime import datetime, timedelta
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Menawar PV Intelligence",
    layout="wide",
    page_icon="☀️",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
#  LOGO SVG
# ─────────────────────────────────────────
def logo_svg(w=110, h=75, uid="x"):
    return f"""<svg width="{w}" height="{h}" viewBox="0 0 340 210" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="gS{uid}" cx="42%" cy="30%" r="60%"><stop offset="0%" stop-color="#fffce0"/><stop offset="30%" stop-color="#f5d050"/><stop offset="65%" stop-color="#c8940a"/><stop offset="100%" stop-color="#7a5008"/></radialGradient>
    <radialGradient id="gD{uid}" cx="38%" cy="28%" r="65%"><stop offset="0%" stop-color="#fffff0"/><stop offset="20%" stop-color="#fce870"/><stop offset="60%" stop-color="#d4a020"/><stop offset="100%" stop-color="#885f10"/></radialGradient>
    <radialGradient id="gSt{uid}" cx="35%" cy="22%" r="68%"><stop offset="0%" stop-color="#6a8faf"/><stop offset="50%" stop-color="#274768"/><stop offset="100%" stop-color="#0c1c2e"/></radialGradient>
    <radialGradient id="gJG{uid}" cx="33%" cy="25%" r="62%"><stop offset="0%" stop-color="#f5d860"/><stop offset="45%" stop-color="#c8940a"/><stop offset="100%" stop-color="#7a5008"/></radialGradient>
    <linearGradient id="gA{uid}" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#5a7a9a"/><stop offset="40%" stop-color="#263f5a"/><stop offset="100%" stop-color="#14283c"/></linearGradient>
    <linearGradient id="gAG{uid}" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#c8a030"/><stop offset="50%" stop-color="#8a6010"/><stop offset="100%" stop-color="#5a3a08"/></linearGradient>
    <linearGradient id="gTG{uid}" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#e8b828"/><stop offset="50%" stop-color="#a87010"/><stop offset="100%" stop-color="#6a4208"/></linearGradient>
  </defs>
  <circle cx="134" cy="90" r="38" fill="none" stroke="url(#gSt{uid})" stroke-width="11"/>
  <circle cx="134" cy="90" r="21" fill="#090f1b"/>
  <circle cx="206" cy="90" r="38" fill="none" stroke="url(#gSt{uid})" stroke-width="11"/>
  <circle cx="206" cy="90" r="21" fill="#090f1b"/>
  <circle cx="170" cy="38" r="38" fill="none" stroke="url(#gSt{uid})" stroke-width="11"/>
  <circle cx="170" cy="38" r="21" fill="#090f1b"/>
  <polygon points="170,1 167,31 170,29 173,31" fill="url(#gS{uid})"/>
  <polygon points="187,9 174,33 176,35 189,16" fill="url(#gS{uid})"/>
  <polygon points="153,9 166,33 164,35 151,16" fill="url(#gS{uid})"/>
  <polygon points="170,26 182,30 186,39 182,48 170,52 158,48 154,39 158,30" fill="url(#gD{uid})" stroke="#c09018" stroke-width="0.8"/>
  <circle cx="170" cy="39" r="9" fill="url(#gD{uid})"/>
  <polygon points="170,66 160,112 180,112" fill="url(#gTG{uid})" opacity="0.85"/>
  <line x1="160" y1="66" x2="170" y2="111" stroke="url(#gA{uid})" stroke-width="5" stroke-linecap="round"/>
  <line x1="180" y1="66" x2="170" y2="111" stroke="url(#gA{uid})" stroke-width="5" stroke-linecap="round"/>
  <circle cx="160" cy="66" r="4" fill="url(#gJG{uid})"/>
  <circle cx="180" cy="66" r="4" fill="url(#gJG{uid})"/>
  <circle cx="170" cy="112" r="6" fill="url(#gJG{uid})"/>
  <rect x="167" y="120" width="6" height="18" rx="2" fill="url(#gA{uid})"/>
  <rect x="148" y="137" width="44" height="6" rx="2.5" fill="url(#gA{uid})"/>
</svg>"""

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def is_night_time(t):
    if isinstance(t, datetime): t = t.time()
    return (t.hour > 19) or (t.hour == 19 and t.minute >= 30) or (t.hour < 6)

def is_production_period(t):
    if isinstance(t, datetime): t = t.time()
    return ((t.hour > 6) or (t.hour == 6 and t.minute >= 0)) and \
           ((t.hour < 19) or (t.hour == 19 and t.minute <= 30))

def fmt_seconds(sec):
    sec = int(sec)
    if sec < 60: return f"{sec}s"
    m, s = divmod(sec, 60); return f"{m}m {s:02d}s"

_OCV = [(11.00,0),(11.50,10),(11.75,20),(12.00,30),(12.25,45),(12.50,60),
        (12.65,70),(12.80,80),(13.00,90),(13.20,95),(13.50,100)]

def voltage_to_soc(v, charging=False):
    v = v - 0.30 if charging else v
    v = max(_OCV[0][0], min(_OCV[-1][0], v))
    for i in range(len(_OCV)-1):
        v0,s0=_OCV[i]; v1,s1=_OCV[i+1]
        if v0<=v<=v1: return round(s0+(s1-s0)*(v-v0)/(v1-v0),1)
    return 100.0

def soc_color(s):
    if s>=80: return "#059669"
    if s>=50: return "#0369a1"
    if s>=30: return "#d97706"
    return "#dc2626"

def fault_color(status):
    s=status.lower()
    if "normal" in s: return "#059669"
    if "night"  in s: return "#7c3aed"
    if "shading"  in s: return "#d97706"
    if "soiling"  in s: return "#ea580c"
    if "disconnect" in s: return "#dc2626"
    if "short"    in s: return "#991b1b"
    if "sensor"   in s: return "#ca8a04"
    if "critical" in s: return "#dc2626"
    return "#64748b"

def fault_loss(status):
    s=status.lower()
    if "normal" in s:            return 0
    if "night"  in s:            return 0
    if "short"  in s:            return 100
    if "disconnect" in s:        return 100
    if "critical shading" in s:  return 85
    if "shading" in s:           return 50
    if "soiling" in s:           return 30
    if "sensor"  in s:           return 10
    return 20

@st.cache_resource
def load_ml():
    try:
        rf  = joblib.load('rf_model.pkl')
        le  = joblib.load('label_encoder.pkl')
        return rf, le
    except Exception as e:
        st.error(f"⚠️ Model files not found: {e}. Ensure rf_model.pkl and label_encoder.pkl are present.")
        st.stop()

# ─────────────────────────────────────────
#  LIGHT THEME CSS
# ─────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg-primary:   #f0f4f9;
  --bg-secondary: #e8eef5;
  --bg-card:      #ffffff;
  --bg-card2:     #f7f9fc;
  --accent-navy:  #1e3a5f;
  --accent-blue:  #1d6fa4;
  --accent-sky:   #0ea5e9;
  --accent-green: #059669;
  --accent-amber: #d97706;
  --accent-red:   #dc2626;
  --accent-gold:  #b45309;
  --text-primary: #1e293b;
  --text-secondary: #475569;
  --text-muted:   #94a3b8;
  --border:       rgba(30,58,95,0.12);
  --border-bright:rgba(14,165,233,0.35);
  --shadow:       0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
  --shadow-md:    0 4px 12px rgba(0,0,0,0.10), 0 8px 32px rgba(0,0,0,0.06);
}

html,body,[data-testid="stAppViewContainer"]{
    background:var(--bg-primary) !important;
    font-family:'Plus Jakarta Sans',sans-serif;
    color:var(--text-primary);
}
[data-testid="stAppViewContainer"] > .main{
    background:var(--bg-primary) !important;
}
[data-testid="stSidebar"]{
    background:var(--bg-card) !important;
    border-right:1px solid var(--border) !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.06) !important;
}
[data-testid="stSidebar"] *{color:var(--text-primary) !important;}
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{
    color:var(--accent-navy) !important;
    font-family:'Space Grotesk',sans-serif !important;
    font-size:0.72rem !important; letter-spacing:1.5px; text-transform:uppercase;
}

[data-testid="stMetric"]{
    background:var(--bg-card) !important;
    border:1px solid var(--border) !important;
    border-radius:14px !important;
    padding:16px 18px !important;
    box-shadow:var(--shadow) !important;
    transition:transform .2s, box-shadow .2s;
}
[data-testid="stMetric"]:hover{
    transform:translateY(-2px);
    box-shadow:var(--shadow-md) !important;
}
[data-testid="stMetric"]::before{
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg,var(--accent-blue),var(--accent-sky));
    border-radius:14px 14px 0 0;
}
[data-testid="stMetricLabel"]>div{
    color:var(--text-secondary) !important;
    font-size:0.65rem !important; font-weight:600 !important;
    letter-spacing:1px; text-transform:uppercase;
}
[data-testid="stMetricValue"]{
    color:var(--accent-navy) !important;
    font-family:'Space Grotesk',sans-serif !important;
    font-size:1.45rem !important; font-weight:700 !important;
}
[data-testid="stMetricDelta"]{font-size:0.7rem !important; color:var(--text-secondary) !important;}

[data-testid="stTabs"] [role="tab"]{
    font-family:'Space Grotesk',sans-serif !important;
    font-size:0.68rem !important; letter-spacing:1px;
    text-transform:uppercase; color:var(--text-secondary) !important;
    padding:10px 18px !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{
    color:var(--accent-blue) !important;
    border-bottom:2px solid var(--accent-blue) !important;
    font-weight:700 !important;
}
[data-testid="stTabsContent"]{
    background:transparent !important;
}

.stButton button{
    background:var(--bg-card) !important;
    border:1.5px solid var(--border-bright) !important;
    color:var(--accent-blue) !important;
    font-family:'Space Grotesk',sans-serif !important;
    font-size:0.65rem !important; letter-spacing:1px; font-weight:600 !important;
    border-radius:10px !important;
    transition:all .2s !important;
    box-shadow:var(--shadow) !important;
}
.stButton button:hover{
    background:rgba(14,165,233,0.08) !important;
    border-color:var(--accent-sky) !important;
    color:var(--accent-navy) !important;
    transform:translateY(-1px) !important;
}
.stButton button[kind="primary"]{
    background:linear-gradient(135deg,var(--accent-navy),var(--accent-blue)) !important;
    color:#ffffff !important;
    border:none !important;
}
.stButton button[kind="primary"]:hover{
    background:linear-gradient(135deg,#162d4a,var(--accent-blue)) !important;
    color:#ffffff !important;
}

.mn-card{
    background:var(--bg-card);
    border:1px solid var(--border);
    border-radius:16px; padding:20px 24px;
    position:relative; overflow:hidden;
    box-shadow:var(--shadow);
    transition:transform .2s, box-shadow .2s;
    margin-bottom:10px;
}
.mn-card:hover{
    transform:translateY(-2px);
    box-shadow:var(--shadow-md);
}
.mn-card::before{
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:linear-gradient(90deg,var(--accent-blue),var(--accent-sky),var(--accent-green));
    border-radius:16px 16px 0 0;
}

.mn-section{
    display:flex; align-items:center; gap:10px;
    margin:20px 0 16px 0; padding-bottom:10px;
    border-bottom:1.5px solid var(--border);
}
.mn-section-title{
    font-family:'Space Grotesk',sans-serif; font-weight:700;
    font-size:0.78rem; color:var(--accent-navy);
    letter-spacing:2px; text-transform:uppercase;
}

.hr-row{
    display:flex; align-items:center; gap:10px;
    padding:10px 14px; border-radius:10px;
    margin-bottom:4px;
    background:var(--bg-card2);
    border:1px solid var(--border);
    transition:background .15s, box-shadow .15s;
}
.hr-row:hover{
    background:rgba(14,165,233,0.05);
    box-shadow:var(--shadow);
}

/* Sidebar input fields */
[data-testid="stTextInput"] input{
    background:var(--bg-card2) !important;
    border:1.5px solid var(--border) !important;
    color:var(--text-primary) !important;
    border-radius:8px !important;
    font-size:0.8rem !important;
}
[data-testid="stTextInput"] input:focus{
    border-color:var(--accent-sky) !important;
    box-shadow:0 0 0 3px rgba(14,165,233,0.15) !important;
}

::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:var(--bg-secondary);}
::-webkit-scrollbar-thumb{background:rgba(14,165,233,0.4);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--accent-blue);}

@keyframes mnGlow{
    0%{filter:drop-shadow(0 0 4px rgba(245,166,35,0.5));}
    50%{filter:drop-shadow(0 0 14px rgba(245,166,35,0.9));}
    100%{filter:drop-shadow(0 0 4px rgba(245,166,35,0.5));}
}
@keyframes pulse{
    0%,100%{opacity:1;} 50%{opacity:0.45;}
}
.mn-logo-anim{animation:mnGlow 3s ease-in-out infinite;}
.online-dot{
    display:inline-block; width:8px; height:8px;
    background:var(--accent-green); border-radius:50%;
    animation:pulse 2s infinite;
    box-shadow:0 0 6px var(--accent-green);
}

[data-testid="stAlert"]{
    border-radius:12px !important;
}
[data-testid="stRadio"] label{font-size:0.8rem !important; color:var(--text-primary) !important;}
[data-testid="stToggle"] label{font-size:0.8rem !important; color:var(--text-primary) !important;}
</style>""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  PLOTLY LIGHT THEME DEFAULTS
# ─────────────────────────────────────────
PLOT_BG    = "rgba(255,255,255,0.0)"
PAPER_BG   = "rgba(255,255,255,0.0)"
GRID_COLOR = "rgba(30,58,95,0.08)"
FONT_COLOR = "#334155"
FONT_FAMILY= "Plus Jakarta Sans"

def light_layout(**kwargs):
    base = dict(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(family=FONT_FAMILY, color=FONT_COLOR, size=10),
        xaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR,
                   tickfont=dict(color=FONT_COLOR), title_font=dict(color=FONT_COLOR)),
        yaxis=dict(gridcolor=GRID_COLOR, linecolor=GRID_COLOR,
                   tickfont=dict(color=FONT_COLOR), title_font=dict(color=FONT_COLOR)),
        legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor=GRID_COLOR,
                    borderwidth=1, font=dict(color=FONT_COLOR, size=9)),
        margin=dict(l=12, r=12, t=44, b=28),
    )
    base.update(kwargs)
    return base


# ─────────────────────────────────────────
#  DASHBOARD CLASS
# ─────────────────────────────────────────
class PVDashboard:

    def __init__(self):
        self.rf, self.le = load_ml()

    # ── ThingSpeak credentials from session state ──
    @property
    def channel_id(self):
        return st.session_state.get("ts_channel_id", "").strip()

    @property
    def read_api_key(self):
        return st.session_state.get("ts_read_key", "").strip()

    @property
    def write_api_key(self):
        return st.session_state.get("ts_write_key", "").strip()

    # ── Data fetch ────────────────────────
    def fetch_live(self):
        if not self.channel_id or not self.read_api_key:
            st.sidebar.warning("⚠️ Enter Channel ID and Read API Key to connect.")
            return 0.0,0.0,0.0,0.0,0.0,0.0,20.0,datetime.now().time(),False,False,0.0
        url = f"https://api.thingspeak.com/channels/{self.channel_id}/feeds.json?api_key={self.read_api_key}&results=1"
        try:
            res = requests.get(url, timeout=8); res.raise_for_status()
            feeds = res.json().get('feeds', [])
            if not feeds:
                st.sidebar.warning("📭 ThingSpeak channel returned no data yet.")
                return 0.0,0.0,0.0,0.0,0.0,0.0,20.0,datetime.now().time(),False,False,0.0
            f = feeds[0]
            v_pv  = float(f.get('field1') or 0)
            v_batt= float(f.get('field2') or 0)
            amp   = float(f.get('field3') or 0)
            pwr   = float(f.get('field4') or 0)
            ideal = float(f.get('field5') or 20.0)
            uv    = float(f.get('field7') or 0)
            dust  = float(f.get('field6') or 0)
            lu = pd.to_datetime(f.get('created_at'))
            if lu.tzinfo is None: lu = lu.tz_localize('UTC')
            diff = abs((pd.Timestamp.utcnow()-lu).total_seconds())
            return v_pv,v_batt,amp,uv,dust,pwr,ideal,datetime.now().time(),True,diff<300,diff
        except requests.exceptions.Timeout:
            st.sidebar.error("⏱ ThingSpeak request timed out. Check your connection.")
            return 17.5,12.4,1.1,8.0,5.0,19.25,20.0,datetime.now().time(),False,False,0.0
        except requests.exceptions.HTTPError as e:
            st.sidebar.error(f"🔒 HTTP Error {e.response.status_code} — Check your API Key or Channel ID.")
            return 17.5,12.4,1.1,8.0,5.0,19.25,20.0,datetime.now().time(),False,False,0.0
        except Exception as e:
            st.sidebar.error(f"🔥 Connection error: {e}")
            return 17.5,12.4,1.1,8.0,5.0,19.25,20.0,datetime.now().time(),False,False,0.0

    def fetch_history(self):
        if not self.channel_id or not self.read_api_key:
            return None
        now_c = datetime.now()
        su = now_c.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(hours=3)
        eu = su+timedelta(hours=27)
        urls = [
            f"https://api.thingspeak.com/channels/{self.channel_id}/feeds.json?api_key={self.read_api_key}"
            f"&start={su.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={eu.strftime('%Y-%m-%dT%H:%M:%SZ')}&results=8000",
            f"https://api.thingspeak.com/channels/{self.channel_id}/feeds.json?api_key={self.read_api_key}&results=800"
        ]
        def _parse(feeds):
            rows=[]
            for f in feeds:
                ts=pd.to_datetime(f.get('created_at'))
                if ts.tzinfo is None: ts=ts.tz_localize('UTC')
                tc=ts.tz_convert('Africa/Cairo')
                ch=6<=tc.hour<20
                soc=voltage_to_soc(float(f.get('field2') or 0),charging=ch)
                vpv=float(f.get('field1') or 0); amp=float(f.get('field3') or 0)
                pwr=float(f.get('field4') or 0) or vpv*amp
                rows.append({'time':tc,'V_PV':vpv,'V_Batt':float(f.get('field2') or 0),
                    'Amp':amp,'Power_W':pwr,'Ideal_Power_W':float(f.get('field5') or 20.0),
                    'UV':float(f.get('field7') or 0),'Dust':float(f.get('field6') or 0),'SOC':soc})
            if not rows: return None
            df=pd.DataFrame(rows).sort_values('time').reset_index(drop=True)
            td=now_c.strftime('%Y-%m-%d')
            df=df[df['time'].dt.strftime('%Y-%m-%d')==td]
            return df if not df.empty else None
        for url in urls:
            try:
                r=requests.get(url,timeout=15); r.raise_for_status()
                feeds=r.json().get('feeds',[])
                if feeds:
                    df=_parse(feeds)
                    if df is not None: return df
            except Exception:
                pass
        return None

    def classify(self, df):
        out=[]
        for _,row in df.iterrows():
            h=row['time'].hour; night=(h>19 or h<6)
            v,a,uv,dust,soc=row['V_PV'],row['Amp'],row['UV'],row['Dust'],row['SOC']
            if night: s="Critical Battery" if soc<=30 else ("Night — Low Battery" if soc<=40 else "Night — Normal")
            elif v<2.0 and uv>3.0: s="Disconnected"
            elif v<5.5 and a<0.15 and uv>3.0: s="Short Circuit"
            elif v>22.0 or a<-0.1: s="Sensor Fault"
            elif uv<1.0: s="Critical Shading"
            elif dust>40: s="Soiling Detected"
            else: s="Normal"
            out.append(s)
        df=df.copy(); df['Status']=out; return df

    def process_telemetry(self, v_pv, v_batt, amp, uv, dust, t, pwr=None, ideal=20.0):
        h=t.hour; m=t.minute; tf=h+m/60.0
        if pwr is None or pwr==0: pwr=v_pv*amp
        ch=(6<=h<20) and v_pv>10.0
        soc=voltage_to_soc(v_batt,charging=ch)
        vd=v_pv-v_batt; dr=dust/100.0 if dust>1.0 else dust
        ts=np.sin(2*np.pi*tf/24.0); tc2=np.cos(2*np.pi*tf/24.0)
        ip=1 if 7<=h<=17 else 0; euv=max(0,ts*10); uvd=euv-uv
        v2u=v_pv/(uv+0.5); sun=uv*ip; ideal=ideal if ideal and ideal>0 else 20.0
        data={'V_PV':[v_pv],'V_Batt':[v_batt],'Amp':[amp],'Power_W':[pwr],
              'Ideal_Power_W':[ideal],'V_Diff':[vd],'SOC_Percentage':[soc],
              'Dust_Ratio':[dr],'time_sin':[ts],'time_cos':[tc2],
              'V_to_UV_Ratio':[v2u],'Sun_Intensity_Index':[sun],
              'is_production_time':[ip],'UV_Deviation':[uvd]}
        return pd.DataFrame(data),pwr,soc,ip

    def rule_override(self, v_pv, v_batt, amp, uv, dust, soc, vd, is_night, connected, mode, status):
        fd=None
        if is_night:
            if soc<=30.0:
                fd="🔴 <b>Critical Battery</b> — Disconnect Greenhouse load immediately."
                return "Critical Battery","crit",st.error,f"🛑 **CRITICAL: Battery {soc:.1f}%** — Disconnect load now.",fd
            elif soc<=40.0:
                return "Night — Battery Low","warn",st.warning,f"🌙 Night · SOC {soc:.1f}% · Approaching 30%",None
            else:
                return "Night — Normal","ok",st.info,f"🌙 Night Normal · SOC {soc:.1f}%",None
        if not connected and mode=="📡 Live ThingSpeak":
            return status,"warn",st.warning,f"⚠️ Stale data — Last known: **{status}**",None
        if v_pv<5.5 and amp<0.15 and uv>3.0:
            fd="🔴 <b>Short Circuit</b> — PV collapsed. Disconnect & inspect wiring."
            return "Short Circuit","crit",st.error,"🚨 **Short Circuit** detected.",fd
        if v_pv<2.0 and uv>3.0:
            fd="🔴 <b>Disconnection</b> — PV near-zero in daylight. Check MC4 connectors."
            return "Disconnected","crit",st.error,"🔌 **Disconnected** — Panel not feeding.",fd
        if v_pv>22.0 or amp<-0.1:
            fd="🟡 <b>Sensor Fault</b> — Readings out of range. Verify wiring."
            return "Sensor Fault","warn",st.warning,"⚙️ **Sensor Fault** detected.",fd
        if uv<1.0:
            return "Critical Shading","crit",st.error,"🚨 **Critical Shading** — UV near zero.",None
        if dust>40 and "Normal" in status:
            return "Soiling Detected","warn",st.warning,"⚠️ **Soiling** — Cleaning recommended.",None
        if "Normal" in status:
            return status,"ok",st.success,f"✅ **{status}** — System optimal.",None
        return status,"crit",st.error,f"⚠️ **{status}**",None

    # ─────────────────────────────────────
    #  PANEL: HOME
    # ─────────────────────────────────────
    def panel_home(self, v_pv, v_batt, amp, pwr_out, soc, uv, dust,
                   is_night, is_prod, final_status, css_class,
                   diff_sec, connected, mode, confidence, alert_fn, alert_text,
                   features_df, fault_detail, hist_df):

        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🏠</span><span class='mn-section-title'>Home — Complete System Dashboard</span></div>", unsafe_allow_html=True)
        c1,c2,c3,c4,c5,c6=st.columns(6)
        c1.metric("⚡ Power Output",  f"{pwr_out:.1f} W",  "Ideal: 20W")
        c2.metric("🔋 Battery SOC",   f"{soc:.1f}%",       f"{v_batt:.2f} V")
        c3.metric("🔌 Current",        f"{amp:.2f} A",      "Live")
        c4.metric("☀️ PV Voltage",    f"{v_pv:.1f} V",     "Panel")
        c5.metric("🌫 Dust Level",     f"{dust:.0f}%",      "Soiling")
        c6.metric("🌞 UV Index",       f"{uv:.1f}",         "Irradiance")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        col_status, col_gauge = st.columns([3,1])
        with col_status:
            conf_pct = int(confidence*100)
            status_color = {"ok":"#059669","warn":"#d97706","crit":"#dc2626"}.get(css_class,"#64748b")
            st.markdown(f"""
            <div class='mn-card'>
              <div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>AI Fault Diagnosis — Confidence {conf_pct}%</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:1.7rem;font-weight:700;color:{status_color};margin-bottom:12px;letter-spacing:1px;'>{final_status}</div>
              <div style='display:flex;align-items:center;gap:10px;'>
                <div style='flex:1;background:rgba(30,58,95,0.08);border-radius:6px;height:7px;overflow:hidden;'>
                  <div style='height:100%;width:{conf_pct}%;background:linear-gradient(90deg,var(--accent-blue),var(--accent-sky));border-radius:6px;'></div>
                </div>
                <span style='font-size:0.78rem;color:var(--accent-blue);font-weight:700;'>{conf_pct}%</span>
              </div>
            </div>""", unsafe_allow_html=True)
            alert_fn(alert_text)
            if not connected and mode=="📡 Live ThingSpeak" and diff_sec>300:
                st.error(f"🔌 CONNECTION LOST — No data for {fmt_seconds(diff_sec)}")
        with col_gauge:
            self._soc_gauge(soc, key="gauge_home")

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            self._battery_compact(soc, v_batt, is_prod, is_night, mode, hist_df)
        with col_b:
            self._prediction_compact(v_pv, v_batt, amp, uv, dust, soc, features_df, final_status)

    def _soc_gauge(self, soc, key="gauge"):
        sc = soc_color(soc)
        fig_g=go.Figure(go.Indicator(mode="gauge+number",value=soc,
            number={'suffix':"%",'font':{'size':22,'family':'Space Grotesk','color':sc}},
            gauge={'axis':{'range':[0,100],'tickcolor':FONT_COLOR,'tickfont':{'color':FONT_COLOR,'size':9}},
                   'bar':{'color':sc,'thickness':0.28},
                   'bgcolor':'rgba(240,244,249,0.9)','bordercolor':GRID_COLOR,
                   'steps':[{'range':[0,30],'color':'rgba(220,38,38,0.08)'},
                             {'range':[30,80],'color':'rgba(217,119,6,0.06)'},
                             {'range':[80,100],'color':'rgba(5,150,105,0.08)'}],
                   'threshold':{'line':{'color':'#dc2626','width':2},'thickness':0.75,'value':30}}))
        fig_g.update_layout(paper_bgcolor='rgba(0,0,0,0)',margin=dict(l=10,r=10,t=20,b=10),height=145)
        st.plotly_chart(fig_g,use_container_width=True,key=key)

    def _battery_compact(self, soc, v_batt, is_prod, is_night, mode, hist_df):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🔋</span><span class='mn-section-title'>Battery SOC</span></div>", unsafe_allow_html=True)
        if hist_df is not None and not hist_df.empty:
            times=hist_df['time'].dt.strftime('%H:%M').tolist()
            socs=hist_df['SOC'].tolist(); vbats=hist_df['V_Batt'].tolist()
        else:
            hours=[i*0.5 for i in range(49)]
            base=max(30,soc-60)
            socs=[round(min(100,base+(soc-base)*(1-np.exp(-3*(h)/24))),1) for h in hours]
            vbats=[round(11.0+(s/100)*3.5,2) for s in socs]
            times=[f"{int(h):02d}:{int((h%1)*60):02d}" for h in hours]
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=times,y=socs,mode='lines',name='SOC %',
            line=dict(color='#0369a1',width=2),fill='tozeroy',fillcolor='rgba(3,105,161,0.07)',
            hovertemplate='<b>%{x}</b><br>SOC: %{y:.1f}%<extra></extra>'))
        fig.add_trace(go.Scatter(x=times,y=vbats,mode='lines',name='V_Batt',
            line=dict(color='#d97706',width=1.5,dash='dot'),yaxis='y2',
            hovertemplate='<b>%{x}</b><br>V: %{y:.2f} V<extra></extra>'))
        fig.add_hline(y=30,line=dict(color='#dc2626',width=1,dash='dash'))
        fig.update_layout(**light_layout(height=230,
            yaxis=dict(title='SOC (%)',range=[0,105],gridcolor=GRID_COLOR,tickfont=dict(color='#0369a1'),title_font=dict(color='#0369a1')),
            yaxis2=dict(title='V Batt',overlaying='y',side='right',range=[10.5,16],gridcolor='rgba(0,0,0,0)',tickfont=dict(color='#d97706'),title_font=dict(color='#d97706')),
            legend=dict(orientation='h',y=1.1,x=0,bgcolor='rgba(0,0,0,0)',font=dict(color=FONT_COLOR,size=9)),
            margin=dict(l=12,r=12,t=30,b=30)))
        st.plotly_chart(fig,use_container_width=True,key="batt_home")
        if soc>=100: st.success("✅ Battery Fully Charged — Feeding Greenhouse.")
        elif soc<=30 and is_night: st.error(f"🛑 CRITICAL — Battery {soc:.1f}%")
        elif is_night: st.info(f"🌙 Night discharge — SOC {soc:.1f}% · {v_batt:.2f} V")

    def _prediction_compact(self, v_pv, v_batt, amp, uv, dust, soc, features_df, final_status):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🔭</span><span class='mn-section-title'>Predictive Health</span></div>", unsafe_allow_html=True)
        risks=[]; score=0
        if dust>60:   risks.append(("🌫 Severe Soiling",f"Dust {dust:.0f}%","crit")); score+=30
        elif dust>30: risks.append(("🌫 Moderate Soiling",f"Dust {dust:.0f}%","warn")); score+=15
        if soc<40 and soc>30: risks.append(("🔋 Battery Risk",f"SOC {soc:.1f}%","warn")); score+=25
        if amp<0.1 and uv>4.0: risks.append(("🔌 Low Current",f"UV={uv:.1f} I={amp:.2f}A","warn")); score+=30
        if "Short" in final_status or "Disconnected" in final_status: score=100
        score=min(score,100)
        if score==0:   rl,rc="✅ All Nominal","#059669"
        elif score<30: rl,rc="🟡 Low Risk","#d97706"
        elif score<70: rl,rc="🟠 Moderate Risk","#ea580c"
        else:          rl,rc="🔴 High Risk","#dc2626"
        st.markdown(f"""<div class='mn-card' style='padding:18px 20px;'>
          <div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>Overall Risk Score</div>
          <div style='display:flex;align-items:center;gap:12px;margin-bottom:10px;'>
            <div style='width:14px;height:14px;background:{rc};border-radius:50%;box-shadow:0 0 8px {rc}60;'></div>
            <div style='font-family:"Space Grotesk",sans-serif;font-size:1.1rem;font-weight:700;color:{rc};'>{rl}</div>
          </div>
          <div style='background:rgba(30,58,95,0.08);border-radius:4px;height:6px;overflow:hidden;'>
            <div style='height:100%;width:{score}%;background:linear-gradient(90deg,#059669,{rc});border-radius:4px;'></div>
          </div>
        </div>""", unsafe_allow_html=True)
        for title,detail,level in risks[:3]:
            if level=="crit": st.error(f"**{title}** — {detail}")
            else: st.warning(f"**{title}** — {detail}")
        if not risks: st.success("🔭 System expected to remain healthy.")
        now=datetime.now()
        next_h=[(now+timedelta(hours=i)).strftime('%H:%M') for i in range(1,4)]
        soc_p=[soc]; pwr_p=[]
        for i in range(3):
            hn=(now+timedelta(hours=i+1)).hour; inp=6<=hn<20
            soc_p.append(min(100,max(0,soc_p[-1]+(2.0 if inp else -1.5))))
            df2=(1-dust/100*0.4); pwr_p.append(round(v_pv*amp*df2 if inp else 0,1))
        cols=st.columns(3)
        for i,(hr,pw,sv) in enumerate(zip(next_h,pwr_p,soc_p[1:])):
            hv=int(hr.split(':')[0]); inp=6<=hv<20; icon="☀️" if inp else "🌙"
            sc2=soc_color(sv)
            with cols[i]:
                st.markdown(f"""<div style='background:var(--bg-card2);border:1px solid var(--border);border-radius:12px;padding:12px 8px;text-align:center;box-shadow:var(--shadow);'>
                  <div style='font-size:1.1rem;'>{icon}</div>
                  <div style='font-family:"Space Grotesk",sans-serif;font-size:0.68rem;color:var(--accent-blue);margin:4px 0 2px 0;font-weight:600;'>{hr}</div>
                  <div style='font-size:0.72rem;color:var(--text-secondary);'>{pw}W</div>
                  <div style='font-family:"Space Grotesk",sans-serif;font-size:0.78rem;color:{sc2};font-weight:700;'>{sv:.0f}%</div>
                </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: OVERVIEW
    # ─────────────────────────────────────
    def panel_overview(self, v_pv, v_batt, amp, pwr_out, soc, uv, dust,
                       is_night, is_prod, final_status, css_class,
                       diff_sec, connected, mode, confidence, alert_fn, alert_text):

        st.markdown("<div class='mn-section'><span style='font-size:1rem'>⚡</span><span class='mn-section-title'>Live System Overview</span></div>", unsafe_allow_html=True)
        c1,c2,c3,c4,c5,c6=st.columns(6)
        c1.metric("⚡ Power Output",  f"{pwr_out:.1f} W",  "Ideal: 20W")
        c2.metric("🔋 Battery SOC",   f"{soc:.1f}%",       f"{v_batt:.2f} V")
        c3.metric("🔌 Current",        f"{amp:.2f} A",      "Live")
        c4.metric("☀️ PV Voltage",    f"{v_pv:.1f} V",     "Panel")
        c5.metric("🌫 Dust Level",     f"{dust:.0f}%",      "Soiling")
        c6.metric("🌞 UV Index",       f"{uv:.1f}",         "Irradiance")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        col_status, col_gauge = st.columns([3,1])
        with col_status:
            conf_pct = int(confidence*100)
            status_color = {"ok":"#059669","warn":"#d97706","crit":"#dc2626"}.get(css_class,"#64748b")
            st.markdown(f"""
            <div class='mn-card'>
              <div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>AI Fault Diagnosis — Confidence {conf_pct}%</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:1.7rem;font-weight:700;color:{status_color};margin-bottom:12px;'>{final_status}</div>
              <div style='display:flex;align-items:center;gap:10px;'>
                <div style='flex:1;background:rgba(30,58,95,0.08);border-radius:6px;height:7px;overflow:hidden;'>
                  <div style='height:100%;width:{conf_pct}%;background:linear-gradient(90deg,var(--accent-blue),var(--accent-sky));border-radius:6px;'></div>
                </div>
                <span style='font-size:0.78rem;color:var(--accent-blue);font-weight:700;'>{conf_pct}%</span>
              </div>
            </div>""", unsafe_allow_html=True)
            alert_fn(alert_text)
            if not connected and mode=="📡 Live ThingSpeak" and diff_sec>300:
                st.error(f"🔌 CONNECTION LOST — No data for {fmt_seconds(diff_sec)}")
        with col_gauge:
            self._soc_gauge(soc, key="gauge_overview")

    # ─────────────────────────────────────
    #  PANEL: AI DIAGNOSIS
    # ─────────────────────────────────────
    def panel_diagnosis(self, v_pv, v_batt, amp, uv, dust, soc, features_df,
                        final_status, css_class, alert_fn, alert_text, fault_detail, confidence):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🤖</span><span class='mn-section-title'>AI Fault Diagnosis Engine</span></div>", unsafe_allow_html=True)
        c1,c2=st.columns([2,1])
        with c1:
            conf_pct=int(confidence*100)
            sc={"ok":"#059669","warn":"#d97706","crit":"#dc2626"}.get(css_class,"#64748b")
            st.markdown(f"""
            <div class='mn-card'>
              <div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>Detected Fault Status</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:1.8rem;font-weight:700;color:{sc};margin-bottom:16px;'>{final_status}</div>
              <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>
                <span style='font-size:0.78rem;color:var(--text-secondary);'>Model Confidence</span>
                <span style='font-family:"Space Grotesk",sans-serif;font-weight:700;color:var(--accent-blue);font-size:1rem;'>{conf_pct}%</span>
              </div>
              <div style='background:rgba(30,58,95,0.08);border-radius:4px;height:8px;overflow:hidden;'>
                <div style='height:100%;width:{conf_pct}%;background:linear-gradient(90deg,var(--accent-blue),var(--accent-sky));border-radius:4px;'></div>
              </div>
              <div style='margin-top:10px;font-size:0.65rem;color:var(--text-muted);'>Random Forest · 14 Features · {len(self.le.classes_)} Classes</div>
            </div>""", unsafe_allow_html=True)
            alert_fn(alert_text)
            if fault_detail:
                st.markdown(f"""<div style='background:rgba(220,38,38,0.05);border:1px solid rgba(220,38,38,0.2);border-radius:12px;padding:14px 18px;font-size:0.82rem;color:#991b1b;line-height:1.8;margin-top:8px;'>{fault_detail}</div>""", unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px;'>Feature Snapshot</div>", unsafe_allow_html=True)
            feats={"V_PV":f"{v_pv:.2f} V","V_Batt":f"{v_batt:.2f} V","V_Diff":f"{v_pv-v_batt:.2f} V",
                   "SOC":f"{soc:.1f}%","Dust":f"{dust:.0f}%","UV Index":f"{uv:.1f}",
                   "Sun Index":f"{features_df['Sun_Intensity_Index'].values[0]:.1f}"}
            for k,v in feats.items():
                st.markdown(f"""<div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);'>
                  <span style='font-size:0.78rem;color:var(--accent-blue);font-weight:600;'>{k}</span>
                  <span style='font-family:"Space Grotesk",sans-serif;font-weight:700;color:var(--text-primary);font-size:0.84rem;'>{v}</span>
                </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: DAY REPORT
    # ─────────────────────────────────────
    def panel_day_report(self, hist_df):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>📅</span><span class='mn-section-title'>Day Report — Today's Full History</span></div>", unsafe_allow_html=True)
        if hist_df is None or hist_df.empty:
            st.info("📡 Day report is available in Live ThingSpeak mode only. Please connect your channel.")
            return
        hist_df=self.classify(hist_df)
        tab1,tab2,tab3=st.tabs(["📊  Power & SOC Timeline","🕐  Hourly Status Summary","📉  Loss Breakdown"])

        # Full 24h x-axis range
        x_range=["06:00","20:00"]

        with tab1:
            times=hist_df['time'].dt.strftime('%H:%M').tolist()
            hist_df['fault']=~hist_df['Status'].str.contains('Normal|Night',na=False)
            statuses = hist_df['Status'].unique()
            fig_gantt = go.Figure()
            for sv in statuses:
                sub = hist_df[hist_df['Status']==sv]
                fig_gantt.add_trace(go.Scatter(
                    x=sub['time'].dt.strftime('%H:%M'), y=[1]*len(sub),
                    mode='markers', marker=dict(color=fault_color(sv), size=16, symbol='square',
                        line=dict(color='rgba(0,0,0,0)', width=0)),
                    name=sv, hovertemplate=f'<b>%{{x}}</b><br>{sv}<extra></extra>'))
            fig_gantt.update_layout(**light_layout(height=100,
                yaxis=dict(visible=False),
                xaxis=dict(gridcolor=GRID_COLOR,tickfont=dict(size=9,color=FONT_COLOR),range=x_range),
                legend=dict(orientation='h',y=1.7,x=0,font=dict(size=9,color=FONT_COLOR),bgcolor='rgba(255,255,255,0.85)'),
                margin=dict(l=10,r=10,t=50,b=10), hovermode='x unified'))
            st.plotly_chart(fig_gantt, use_container_width=True, key="gantt")

            fig=make_subplots(rows=3,cols=1,shared_xaxes=True,
                              row_heights=[0.45,0.3,0.25],vertical_spacing=0.04,
                              subplot_titles=("Output Power (W)","Battery SOC (%)","PV Voltage (V)"))
            shapes=[]
            in_f=False; fs=None
            for _,row in hist_df.iterrows():
                t_str=row['time'].strftime('%H:%M')
                if row['fault'] and not in_f: in_f=True; fs=t_str
                elif not row['fault'] and in_f:
                    in_f=False
                    shapes.append(dict(type='rect',xref='x',yref='paper',x0=fs,x1=t_str,y0=0,y1=1,
                        fillcolor='rgba(220,38,38,0.04)',line_width=0,layer='below'))
            fig.add_trace(go.Scatter(x=times,y=hist_df['Power_W'],mode='lines',name='Output Power',
                line=dict(color='#1d6fa4',width=2),fill='tozeroy',fillcolor='rgba(29,111,164,0.07)',
                hovertemplate='<b>%{x}</b><br>Power: %{y:.1f} W<extra></extra>'),row=1,col=1)
            fig.add_trace(go.Scatter(x=times,y=hist_df['Ideal_Power_W'],mode='lines',name='Ideal Power',
                line=dict(color='#059669',width=1.2,dash='dash'),
                hovertemplate='<b>%{x}</b><br>Ideal: %{y:.1f} W<extra></extra>'),row=1,col=1)
            fig.add_trace(go.Scatter(x=times,y=hist_df['SOC'],mode='lines',name='SOC %',
                line=dict(color='#d97706',width=2),fill='tozeroy',fillcolor='rgba(217,119,6,0.07)',
                hovertemplate='<b>%{x}</b><br>SOC: %{y:.1f}%<extra></extra>'),row=2,col=1)
            fig.add_hline(y=30,line=dict(color='#dc2626',width=1,dash='dash'),row=2,col=1)
            fig.add_trace(go.Scatter(x=times,y=hist_df['V_PV'],mode='lines',name='V_PV',
                line=dict(color='#7c3aed',width=1.5),
                hovertemplate='<b>%{x}</b><br>V_PV: %{y:.2f} V<extra></extra>'),row=3,col=1)
            fig.update_layout(**light_layout(shapes=shapes,height=500,
                legend=dict(orientation='h',y=1.03,x=0,font=dict(size=9,color=FONT_COLOR),bgcolor='rgba(255,255,255,0.85)'),
                margin=dict(l=12,r=12,t=50,b=20),hovermode='x unified'))
            for i in range(1,4):
                fig.update_xaxes(gridcolor=GRID_COLOR,tickfont=dict(color=FONT_COLOR),range=x_range,row=i,col=1)
                fig.update_yaxes(gridcolor=GRID_COLOR,tickfont=dict(color=FONT_COLOR),row=i,col=1)
            # Subplot title colors
            for ann in fig.layout.annotations:
                ann.font.color = FONT_COLOR
            st.plotly_chart(fig,use_container_width=True,key="timeline_chart")

        with tab2:
            hist_df['hour']=hist_df['time'].dt.hour
            hourly=hist_df.groupby('hour').agg(
                Status=('Status',lambda x:x.mode()[0]),
                Avg_Power=('Power_W','mean'),Avg_SOC=('SOC','mean')).reset_index()
            st.markdown(f"""<div style='display:flex;align-items:center;gap:10px;padding:10px 14px;margin-bottom:6px;border-radius:10px;background:var(--bg-card2);border:1px solid var(--border);'>
              <div style='min-width:72px;font-size:0.62rem;color:var(--accent-blue);letter-spacing:1px;text-transform:uppercase;font-weight:700;'>HOUR</div>
              <div style='flex:1;font-size:0.62rem;color:var(--accent-blue);letter-spacing:1px;text-transform:uppercase;font-weight:700;'>STATUS</div>
              <div style='min-width:80px;font-size:0.62rem;color:var(--accent-blue);letter-spacing:1px;text-transform:uppercase;font-weight:700;'>AVG POWER</div>
              <div style='min-width:70px;font-size:0.62rem;color:var(--accent-blue);letter-spacing:1px;text-transform:uppercase;font-weight:700;'>AVG SOC</div>
              <div style='min-width:80px;font-size:0.62rem;color:var(--accent-blue);letter-spacing:1px;text-transform:uppercase;font-weight:700;'>PERIOD</div>
              <div style='min-width:90px;font-size:0.62rem;color:#dc2626;letter-spacing:1px;text-transform:uppercase;font-weight:700;text-align:right;'>POWER LOSS</div>
            </div>""", unsafe_allow_html=True)
            for _,row in hourly.iterrows():
                h=int(row['hour']); s=row['Status']
                c=fault_color(s); loss=fault_loss(s)
                is_night_h=(h<6 or h>=20)
                period="🌙 Night" if is_night_h else "⚡ Production"
                pwr_txt=f"{row['Avg_Power']:.1f} W" if not is_night_h else "0.0 W"
                st.markdown(f"""<div class='hr-row'>
                  <div style='min-width:72px;font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:0.84rem;color:var(--accent-navy);'>{h:02d}:00</div>
                  <div style='flex:1;'><span style='background:{c}15;color:{c};padding:3px 12px;border-radius:6px;font-size:0.72rem;font-weight:700;border:1px solid {c}40;'>{s}</span></div>
                  <div style='min-width:80px;font-size:0.78rem;color:var(--accent-blue);font-weight:600;'>{pwr_txt}</div>
                  <div style='min-width:70px;font-size:0.78rem;color:#d97706;font-weight:700;'>{row['Avg_SOC']:.0f}%</div>
                  <div style='min-width:80px;font-size:0.72rem;color:var(--text-secondary);'>{period}</div>
                  <div style='min-width:90px;text-align:right;font-family:"Space Grotesk",sans-serif;font-size:0.72rem;color:#dc2626;font-weight:700;'>-{loss}%</div>
                </div>""", unsafe_allow_html=True)

        with tab3:
            sc=hist_df.groupby('Status').size().reset_index(name='count')
            sc['loss']=sc['Status'].apply(fault_loss)
            sc['color']=sc['Status'].apply(fault_color)
            tot=sc['count'].sum(); sc['time_pct']=(sc['count']/tot*100).round(1)
            sc['contrib']=(sc['time_pct']*sc['loss']/100).round(2)
            total_loss=sc['contrib'].sum()
            normal_p=sc[sc['Status'].str.contains('Normal',na=False)]['time_pct'].sum()
            night_p =sc[sc['Status'].str.contains('Night',na=False)]['time_pct'].sum()
            fault_p=100-normal_p-night_p
            avg_p=hist_df['Power_W'].mean(); ideal_a=hist_df['Ideal_Power_W'].mean()
            eff=(avg_p/ideal_a*100) if ideal_a>0 else 0
            k1,k2,k3,k4,k5=st.columns(5)
            k1.metric("✅ Normal Time",f"{normal_p:.1f}%","of production")
            k2.metric("⚠️ Fault Time",f"{fault_p:.1f}%","of production")
            k3.metric("🌙 Night Time",f"{night_p:.1f}%","of day")
            k4.metric("📉 Total Power Lost",f"{total_loss:.1f}%","weighted")
            k5.metric("⚡ System Efficiency",f"{eff:.1f}%","actual/ideal")
            cp,cb=st.columns(2)
            with cp:
                fig3=go.Figure(go.Pie(labels=sc['Status'],values=sc['time_pct'],hole=0.55,
                    marker=dict(colors=sc['color'].tolist(),line=dict(color='#ffffff',width=2)),
                    textinfo='label+percent',textfont=dict(size=9,family=FONT_FAMILY,color='#1e293b'),
                    hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>'))
                fig3.update_layout(**light_layout(showlegend=False,height=300,
                    margin=dict(l=10,r=10,t=40,b=10),
                    title=dict(text='⏱ Time Spent per Status (%)',font=dict(size=11,color=FONT_COLOR))))
                st.plotly_chart(fig3,use_container_width=True,key="pie_chart")
            with cb:
                fo=sc[~sc['Status'].str.contains('Night',na=False)]
                fig4=go.Figure()
                fig4.add_trace(go.Bar(name='Time Spent (%)',x=fo['Status'],y=fo['time_pct'],
                    marker_color=fo['color'].tolist(),opacity=0.80,
                    text=[f"{v:.1f}%" for v in fo['time_pct']],textposition='outside',
                    textfont=dict(size=9,color=FONT_COLOR)))
                fig4.add_trace(go.Bar(name='Power Loss Contribution (%)',x=fo['Status'],y=fo['contrib'],
                    marker_color='rgba(220,38,38,0.65)',
                    text=[f"{v:.1f}%" for v in fo['contrib']],textposition='outside',
                    textfont=dict(size=9,color='#991b1b')))
                fig4.update_layout(**light_layout(barmode='group',height=300,
                    margin=dict(l=10,r=10,t=50,b=70),
                    xaxis=dict(tickangle=-25,gridcolor=GRID_COLOR,tickfont=dict(color=FONT_COLOR)),
                    yaxis=dict(gridcolor=GRID_COLOR,tickfont=dict(color=FONT_COLOR)),
                    legend=dict(orientation='h',y=1.15,bgcolor='rgba(255,255,255,0.85)',font=dict(size=9,color=FONT_COLOR)),
                    title=dict(text='📊 Time vs Power Loss per Fault Cause',font=dict(size=11,color=FONT_COLOR))))
                st.plotly_chart(fig4,use_container_width=True,key="bar_chart")
            st.markdown("<div style='font-size:0.65rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin:16px 0 10px 0;'>🔍 Per-Fault Power Loss Detail</div>", unsafe_allow_html=True)
            for _,row in sc.sort_values('contrib',ascending=False).iterrows():
                c=row['color']; bar_w=int(min(row['contrib']*6,100))
                st.markdown(f"""<div class='hr-row'>
                  <div style='min-width:180px;'><span style='background:{c}15;color:{c};padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:700;border:1px solid {c}40;'>{row['Status']}</span></div>
                  <div style='min-width:90px;font-size:0.78rem;color:var(--text-secondary);'>{row['time_pct']:.1f}%</div>
                  <div style='min-width:90px;font-size:0.78rem;color:#dc2626;font-weight:600;'>{row['loss']:.0f}%</div>
                  <div style='flex:1;'><div style='background:rgba(30,58,95,0.08);border-radius:4px;height:8px;overflow:hidden;'><div style='height:100%;width:{bar_w}%;background:{c};border-radius:4px;'></div></div></div>
                  <div style='min-width:90px;text-align:right;font-family:"Space Grotesk",sans-serif;font-size:0.75rem;color:{c};font-weight:700;'>{row['contrib']:.2f}%</div>
                </div>""", unsafe_allow_html=True)
            st.markdown(f"""<div style='text-align:right;font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:1rem;margin-top:14px;padding:12px 16px;background:rgba(220,38,38,0.05);border:1px solid rgba(220,38,38,0.18);border-radius:12px;color:#1e293b;'>
              TOTAL DAY POWER LOSS — <span style='color:#dc2626;'>{total_loss:.2f}%</span>
            </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: BATTERY
    # ─────────────────────────────────────
    def panel_battery(self, soc, v_batt, is_prod, is_night, mode, hist_df):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🔋</span><span class='mn-section-title'>Battery SOC — Night Discharge Monitor</span></div>", unsafe_allow_html=True)
        b1,b2,b3=st.columns(3)
        b1.metric("🔋 Battery SOC", f"{soc:.1f}%", f"{'Charging' if is_prod else 'Discharging'}")
        b2.metric("🔌 Battery Voltage", f"{v_batt:.2f} V", "Current")
        b3.metric("⚡ Status", "Night" if is_night else "Day", f"{'🌙' if is_night else '☀️'} Mode")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        if hist_df is not None and not hist_df.empty:
            pf=hist_df.copy()
            times=pf['time'].dt.strftime('%H:%M').tolist()
            socs=pf['SOC'].tolist(); vbats=pf['V_Batt'].tolist()
        else:
            hours=[i*0.5 for i in range(49)]
            base=max(30,soc-60)
            socs=[round(min(100,base+(soc-base)*(1-np.exp(-3*(h)/24))),1) for h in hours]
            vbats=[round(11.0+(s/100)*3.5,2) for s in socs]
            times=[f"{int(h):02d}:{int((h%1)*60):02d}" for h in hours]

        fig=go.Figure()
        fig.add_trace(go.Scatter(x=times,y=socs,mode='lines',name='SOC %',
            line=dict(color='#0369a1',width=2.5),fill='tozeroy',fillcolor='rgba(3,105,161,0.07)',
            hovertemplate='<b>%{x}</b><br>SOC: %{y:.1f}%<extra></extra>'))
        fig.add_trace(go.Scatter(x=times,y=vbats,mode='lines',name='V_Batt (V)',
            line=dict(color='#d97706',width=1.8,dash='dot'),yaxis='y2',
            hovertemplate='<b>%{x}</b><br>V: %{y:.2f} V<extra></extra>'))
        fig.add_hline(y=30,line=dict(color='#dc2626',width=1.2,dash='dash'),
                      annotation_text="Critical 30%",annotation_font=dict(color='#dc2626',size=10))
        fig.add_hline(y=100,line=dict(color='#059669',width=1,dash='dot'),
                      annotation_text="Full 100%",annotation_font=dict(color='#059669',size=10))
        fig.update_layout(**light_layout(height=320,
            xaxis=dict(gridcolor=GRID_COLOR,title='Time',title_font=dict(color=FONT_COLOR),
                       range=["06:00","20:00"],tickfont=dict(color=FONT_COLOR)),
            yaxis=dict(title='SOC (%)',range=[0,105],gridcolor=GRID_COLOR,
                       title_font=dict(color='#0369a1'),tickfont=dict(color='#0369a1')),
            yaxis2=dict(title='Battery Voltage (V)',overlaying='y',side='right',
                        range=[10.5,16],gridcolor='rgba(0,0,0,0)',
                        title_font=dict(color='#d97706'),tickfont=dict(color='#d97706')),
            legend=dict(orientation='h',y=1.08,x=0,bgcolor='rgba(255,255,255,0.85)',font=dict(color=FONT_COLOR,size=9)),
            margin=dict(l=12,r=12,t=40,b=40)))
        st.plotly_chart(fig,use_container_width=True,key="battery_chart")

        if hist_df is not None and not hist_df.empty and is_night:
            st.markdown("<div style='font-size:0.65rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin:16px 0 10px 0;'>🔋 Night Discharge Log — Last 30 Readings</div>", unsafe_allow_html=True)
            night_df = hist_df[hist_df['time'].apply(lambda t: t.hour>=20 or t.hour<6)].tail(30)
            if not night_df.empty:
                st.markdown(f"""<div style='display:flex;padding:8px 14px;background:var(--bg-card2);border:1px solid var(--border);border-radius:10px;margin-bottom:4px;'>
                  <div style='flex:1;font-size:0.62rem;color:var(--accent-blue);letter-spacing:1px;text-transform:uppercase;font-weight:700;'>TIME</div>
                  <div style='min-width:100px;text-align:center;font-size:0.62rem;color:#d97706;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>V_BATT</div>
                  <div style='min-width:100px;text-align:right;font-size:0.62rem;color:var(--accent-blue);letter-spacing:1px;text-transform:uppercase;font-weight:700;'>SOC</div>
                </div>""", unsafe_allow_html=True)
                for _,row in night_df.sort_values('time',ascending=False).iterrows():
                    sc2=soc_color(row['SOC'])
                    st.markdown(f"""<div class='hr-row'>
                      <div style='flex:1;font-size:0.8rem;color:var(--text-primary);'>{row['time'].strftime('%H:%M')}</div>
                      <div style='min-width:100px;text-align:center;font-family:"Space Grotesk",sans-serif;font-size:0.78rem;color:#d97706;font-weight:700;'>{row['V_Batt']:.1f} V</div>
                      <div style='min-width:100px;text-align:right;'><span style='background:{sc2}18;color:{sc2};padding:3px 12px;border-radius:6px;font-family:"Space Grotesk",sans-serif;font-size:0.75rem;font-weight:700;border:1px solid {sc2}40;'>{row['SOC']:.1f}%</span></div>
                    </div>""", unsafe_allow_html=True)

        if soc>=100: st.success("✅ Battery Fully Charged (100%) — Controller feeding Greenhouse load.")
        elif soc<=30 and is_night: st.error(f"🛑 CRITICAL — Battery {soc:.1f}% at night. Disconnect load immediately.")
        elif soc<=40 and is_night: st.warning(f"⚠️ Night — Battery {soc:.1f}% — approaching critical 30%.")
        elif is_night: st.info(f"🌙 Night discharge — SOC {soc:.1f}% · {v_batt:.2f} V")
        elif is_prod: st.info(f"⚡ Charging in progress — SOC {soc:.1f}% · {v_batt:.2f} V")

    # ─────────────────────────────────────
    #  PANEL: PREDICTIVE
    # ─────────────────────────────────────
    def panel_prediction(self, v_pv, v_batt, amp, uv, dust, soc, features_df, final_status, hist_df):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🔭</span><span class='mn-section-title'>Predictive Health Forecast</span></div>", unsafe_allow_html=True)
        p1,p2,p3=st.columns(3)
        p1.metric("🌫 Dust Level", f"{dust:.0f}%", "Soiling Factor")
        p2.metric("🌞 UV Index", f"{uv:.1f}", "Irradiance")
        p3.metric("⚡ PV Voltage", f"{v_pv:.1f} V", "Panel Output")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        risks=[]; score=0
        if dust>60:   risks.append(("🌫 Severe Soiling",f"Dust {dust:.0f}% — clean urgently","crit")); score+=30
        elif dust>30: risks.append(("🌫 Moderate Soiling",f"Dust {dust:.0f}% — clean within 24h","warn")); score+=15
        if soc<40 and soc>30: risks.append(("🔋 Battery Risk",f"SOC {soc:.1f}% near critical 30%","warn")); score+=25
        vr=v_pv/(v_batt+0.01)
        if vr<1.02 and v_pv>5:
            risks.append(("⚡ Charging Efficiency Drop",f"PV-to-Battery ratio low ({vr:.2f}).","warn")); score+=20
        if amp<0.1 and uv>4.0: risks.append(("🔌 Low Current",f"UV={uv:.1f} I={amp:.2f}A","warn")); score+=30
        if "Short" in final_status or "Disconnected" in final_status: score=100
        score=min(score,100)
        if score==0:   rl,rc,rt="✅ All Nominal","#059669","No faults detected. System is healthy."
        elif score<30: rl,rc,rt="🟡 Low Risk","#d97706","Minor conditions present. Monitor but no immediate action needed."
        elif score<70: rl,rc,rt="🟠 Moderate Risk","#ea580c","Elevated risk — monitor closely."
        else:          rl,rc,rt="🔴 High Risk","#dc2626","Fault active — act now."

        st.markdown(f"""<div class='mn-card' style='padding:22px 26px;'>
          <div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>OVERALL RISK SCORE</div>
          <div style='display:flex;align-items:center;gap:14px;margin-bottom:14px;'>
            <div style='width:18px;height:18px;background:{rc};border-radius:50%;box-shadow:0 0 12px {rc}80;'></div>
            <div style='font-family:"Space Grotesk",sans-serif;font-size:1.4rem;font-weight:700;color:{rc};'>{rl}</div>
          </div>
          <div style='background:rgba(30,58,95,0.08);border-radius:6px;height:8px;overflow:hidden;margin-bottom:10px;'>
            <div style='height:100%;width:{score}%;background:linear-gradient(90deg,#059669,{rc});border-radius:6px;'></div>
          </div>
          <div style='font-size:0.82rem;color:var(--text-secondary);'>{rt}</div>
        </div>""", unsafe_allow_html=True)

        for title,detail,level in risks:
            if level=="crit": st.error(f"**{title}** — {detail}")
            elif level=="warn": st.warning(f"**{title}** — {detail}")
            else: st.info(f"**{title}** — {detail}")
        if not risks: st.success("🔭 No risk indicators — system expected to remain healthy.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        now=datetime.now()
        next_h=[(now+timedelta(hours=i)).strftime('%H:%M') for i in range(1,7)]
        soc_p=[soc]; pwr_p=[]
        for i in range(6):
            hn=(now+timedelta(hours=i+1)).hour; inp=6<=hn<20
            soc_p.append(min(100,max(0,soc_p[-1]+(2.0 if inp and soc_p[-1]<100 else -1.5))))
            df2=(1-dust/100*0.4); pwr_p.append(round(v_pv*amp*df2 if inp else 0,1))

        st.markdown("<div style='font-size:0.65rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>⏱ Next 6 Hours Forecast</div>", unsafe_allow_html=True)
        cols=st.columns(6)
        for i,(hr,pw,sv) in enumerate(zip(next_h,pwr_p,soc_p[1:])):
            hv=int(hr.split(':')[0]); inp=6<=hv<20; icon="☀️" if inp else "🌙"
            sc2=soc_color(sv)
            with cols[i]:
                st.markdown(f"""<div style='background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:14px 8px;text-align:center;box-shadow:var(--shadow);'>
                  <div style='font-size:1.3rem;'>{icon}</div>
                  <div style='font-family:"Space Grotesk",sans-serif;font-size:0.72rem;color:var(--accent-blue);margin:6px 0 2px 0;font-weight:600;'>{hr}</div>
                  <div style='font-size:0.75rem;color:var(--text-secondary);margin-bottom:4px;'>{pw}W</div>
                  <div style='font-family:"Space Grotesk",sans-serif;font-size:0.82rem;color:{sc2};font-weight:700;'>{sv:.0f}%</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        hours_tmr=list(range(6,20)); pwr_clean=[]; pwr_dust=[]
        for h in hours_tmr:
            peak=20*(np.sin(np.pi*(h-6)/13)**1.5) if 6<=h<19 else 0
            peak=max(0,peak)
            pwr_clean.append(round(peak,1))
            pwr_dust.append(round(peak*(1-dust/100*0.4),1))
        hour_labels=[f"{h:02d}:00" for h in hours_tmr]
        exp_energy=sum(pwr_clean)/60; proj_energy=sum(pwr_dust)/60
        energy_loss=exp_energy-proj_energy
        action="Clean Now" if dust>40 else ("Monitor" if dust>20 else "All Good")

        fig_tmr=go.Figure()
        fig_tmr.add_trace(go.Bar(name='Expected (Clean)',x=hour_labels,y=pwr_clean,
            marker_color='rgba(29,111,164,0.35)',marker_line=dict(color='#1d6fa4',width=1),
            hovertemplate='<b>%{x}</b><br>Expected: %{y:.1f}W<extra></extra>'))
        fig_tmr.add_trace(go.Bar(name=f'Projected (Dust {dust:.0f}%)',x=hour_labels,y=pwr_dust,
            marker_color='rgba(217,119,6,0.65)',marker_line=dict(color='#d97706',width=1),
            hovertemplate='<b>%{x}</b><br>Projected: %{y:.1f}W<extra></extra>'))
        fig_tmr.update_layout(**light_layout(barmode='overlay',height=270,
            xaxis=dict(gridcolor=GRID_COLOR,tickfont=dict(color=FONT_COLOR)),
            yaxis=dict(gridcolor=GRID_COLOR,title='Power (W)',tickfont=dict(color=FONT_COLOR)),
            legend=dict(orientation='h',y=1.1,x=0,bgcolor='rgba(255,255,255,0.85)',font=dict(size=9,color=FONT_COLOR)),
            margin=dict(l=12,r=12,t=50,b=40),
            title=dict(text="📅 Tomorrow's System Projection",font=dict(size=11,color=FONT_COLOR))))
        st.plotly_chart(fig_tmr,use_container_width=True,key="tomorrow_chart")

        e1,e2,e3=st.columns(3)
        with e1:
            st.markdown(f"""<div class='mn-card' style='text-align:center;padding:18px;'>
              <div style='font-size:0.6rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'>☀️ EXPECTED ENERGY</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:1.7rem;font-weight:700;color:var(--accent-navy);'>{exp_energy:.1f} Wh</div>
              <div style='margin-top:6px;'><span style='background:rgba(5,150,105,0.1);color:#059669;padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;'>↑ if clean</span></div>
            </div>""", unsafe_allow_html=True)
        with e2:
            loss_color="#dc2626" if energy_loss>2 else "#d97706"
            st.markdown(f"""<div class='mn-card' style='text-align:center;padding:18px;'>
              <div style='font-size:0.6rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'>📉 PROJECTED ENERGY</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:1.7rem;font-weight:700;color:var(--accent-navy);'>{proj_energy:.1f} Wh</div>
              <div style='margin-top:6px;'><span style='background:rgba(220,38,38,0.08);color:{loss_color};padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;'>↓ -{energy_loss:.1f} Wh from dust</span></div>
            </div>""", unsafe_allow_html=True)
        with e3:
            a_color="#059669" if action=="All Good" else ("#d97706" if action=="Monitor" else "#dc2626")
            st.markdown(f"""<div class='mn-card' style='text-align:center;padding:18px;'>
              <div style='font-size:0.6rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'>⚡ RECOMMENDED ACTION</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:1.4rem;font-weight:700;color:{a_color};'>{action}</div>
              <div style='margin-top:6px;'><span style='background:{a_color}15;color:{a_color};padding:3px 10px;border-radius:6px;font-size:0.72rem;font-weight:600;'>Dust: {dust:.0f}%</span></div>
            </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: CLEANING (IoT Cloud-Based)
    # ─────────────────────────────────────
    def panel_cleaning(self, dust_in):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🧹</span><span class='mn-section-title'>Panel Cleaning Control</span></div>", unsafe_allow_html=True)

        cl1,cl2,cl3=st.columns(3)
        cl1.metric("🌫 Dust Level", f"{dust_in:.0f}%", "Current Soiling")
        cl2.metric("📉 Power Loss", f"{min(dust_in*0.4,40):.1f}%", "From Dust")
        cl3.metric("🧹 Clean Status", "Needed" if dust_in>30 else "OK", "Panel Health")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        dust_c="#059669" if dust_in<20 else "#d97706" if dust_in<50 else "#dc2626"
        loss_est=min(dust_in*0.4,40)
        c1,c2,c3=st.columns([1,1,2])
        with c1:
            st.markdown(f"""<div class='mn-card' style='text-align:center;padding:22px 16px;'>
              <div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>Current Dust Level</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:2.6rem;font-weight:700;color:{dust_c};'>{dust_in:.0f}%</div>
              <div style='background:rgba(30,58,95,0.08);border-radius:4px;height:10px;overflow:hidden;margin-top:12px;'>
                <div style='height:100%;width:{min(dust_in,100):.0f}%;background:{dust_c};border-radius:4px;'></div>
              </div>
              <div style='font-size:0.75rem;color:var(--text-secondary);margin-top:10px;'>{"⚠️ Clean Needed" if dust_in>30 else "✅ Panel Clean"}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class='mn-card' style='text-align:center;padding:22px 16px;'>
              <div style='font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>Power Loss from Dust</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-size:2.6rem;font-weight:700;color:#dc2626;'>{loss_est:.1f}%</div>
              <div style='font-size:0.75rem;color:var(--text-secondary);margin-top:10px;'>Estimated reduction</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown("""<div class='mn-card' style='padding:20px 22px;'>
              <div style='font-size:0.75rem;color:var(--accent-navy);font-weight:700;margin-bottom:6px;letter-spacing:0.5px;'>🌐 ESP32 Cloud Cleaning Control</div>
              <div style='font-size:0.72rem;color:var(--text-secondary);margin-bottom:16px;line-height:1.6;'>Commands are dispatched via ThingSpeak (Field 8). Your ESP32 polls the channel and executes the action globally from anywhere in the world.</div>""", unsafe_allow_html=True)

            if 'cleaning_log' not in st.session_state:
                st.session_state.cleaning_log=[]

            write_key = self.write_api_key
            if not write_key:
                st.warning("⚠️ Enter your **Write API Key** in the sidebar to enable cloud cleaning control.")
            else:
                b1,b2=st.columns(2)
                with b1:
                    if st.button("🧹 Trigger Cleaning", use_container_width=True, type="primary"):
                        try:
                            url = f"https://api.thingspeak.com/update?api_key={write_key}&field8=1"
                            r = requests.get(url, timeout=8)
                            if r.status_code == 200 and r.text.strip() != "0":
                                st.success("✅ Cleaning command sent! ESP32 will start shortly.")
                                st.session_state.cleaning_log.append(f"✅ Triggered — {datetime.now().strftime('%H:%M:%S')}")
                            elif r.text.strip() == "0":
                                st.error("❌ ThingSpeak rejected the update. Check your Write API Key or rate limits (15s interval).")
                            else:
                                st.error(f"❌ Unexpected response: HTTP {r.status_code}")
                        except requests.exceptions.Timeout:
                            st.error("⏱ Request timed out. Check your internet connection.")
                            st.session_state.cleaning_log.append(f"❌ Timeout — {datetime.now().strftime('%H:%M:%S')}")
                        except Exception as e:
                            st.error(f"🔥 Failed to reach ThingSpeak: {e}")
                            st.session_state.cleaning_log.append(f"❌ Error — {datetime.now().strftime('%H:%M:%S')}")
                with b2:
                    if st.button("⏹ Stop Cleaning", use_container_width=True):
                        try:
                            url = f"https://api.thingspeak.com/update?api_key={write_key}&field8=0"
                            r = requests.get(url, timeout=8)
                            if r.status_code == 200 and r.text.strip() != "0":
                                st.success("⏹ Stop command sent successfully.")
                                st.session_state.cleaning_log.append(f"⏹ Stopped — {datetime.now().strftime('%H:%M:%S')}")
                            elif r.text.strip() == "0":
                                st.warning("⚠️ ThingSpeak update rate limit reached (min 15s between updates).")
                            else:
                                st.error(f"❌ HTTP {r.status_code}")
                        except requests.exceptions.Timeout:
                            st.error("⏱ Request timed out.")
                        except Exception as e:
                            st.error(f"🔥 Error: {e}")

            if st.session_state.cleaning_log:
                st.markdown("<div style='margin-top:14px;font-size:0.62rem;color:var(--text-secondary);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;font-weight:600;'>Activity Log</div>", unsafe_allow_html=True)
                for log in reversed(st.session_state.cleaning_log[-5:]):
                    st.markdown(f"<div style='font-size:0.78rem;color:var(--accent-navy);padding:4px 0;border-bottom:1px solid var(--border);'>{log}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: ABOUT US
    # ─────────────────────────────────────
    def panel_about_us(self):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>🌟</span><span class='mn-section-title'>About Menawar — Technology &amp; Renewable Energy</span></div>", unsafe_allow_html=True)

        hdr_logo = logo_svg(w=100, h=68, uid="about")
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:32px;padding:32px 40px;background:var(--bg-card);
                    border:1px solid var(--border);border-radius:20px;margin-bottom:28px;
                    position:relative;overflow:hidden;box-shadow:var(--shadow-md);'>
          <div style='position:absolute;top:0;left:0;right:0;height:4px;
                      background:linear-gradient(90deg,#1d6fa4,#0ea5e9,#059669,#d97706);border-radius:20px 20px 0 0;'></div>
          <div class='mn-logo-anim'>{hdr_logo}</div>
          <div style='flex:1;'>
            <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:2.2rem;
                        color:var(--accent-navy);letter-spacing:4px;'>MENAWAR</div>
            <div style='font-family:"Space Grotesk",sans-serif;font-size:0.9rem;color:var(--accent-blue);
                        letter-spacing:2px;margin-top:4px;font-weight:600;'>Technology &amp; Renewable Energy</div>
            <div style='font-size:0.88rem;color:var(--text-secondary);margin-top:14px;max-width:640px;line-height:1.8;'>
              Menawar is a graduation project dedicated to AI-powered monitoring and diagnostics of photovoltaic solar systems.
              By integrating machine learning with real-time IoT infrastructure, Menawar enables proactive maintenance,
              automated panel cleaning, and intelligent fault detection — maximizing solar energy efficiency.
            </div>
            <div style='margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;'>
              <span style='background:rgba(29,111,164,0.1);color:var(--accent-blue);padding:5px 14px;border-radius:20px;font-size:0.72rem;font-weight:700;border:1px solid rgba(29,111,164,0.25);'>AI / Machine Learning</span>
              <span style='background:rgba(5,150,105,0.1);color:#059669;padding:5px 14px;border-radius:20px;font-size:0.72rem;font-weight:700;border:1px solid rgba(5,150,105,0.25);'>IoT &amp; ESP32</span>
              <span style='background:rgba(217,119,6,0.1);color:#d97706;padding:5px 14px;border-radius:20px;font-size:0.72rem;font-weight:700;border:1px solid rgba(217,119,6,0.25);'>ThingSpeak Cloud</span>
              <span style='background:rgba(124,58,237,0.1);color:#7c3aed;padding:5px 14px;border-radius:20px;font-size:0.72rem;font-weight:700;border:1px solid rgba(124,58,237,0.25);'>Renewable Energy</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='font-size:0.72rem;color:var(--text-secondary);letter-spacing:2px;text-transform:uppercase;margin:24px 0 16px 0;font-weight:700;'>🚀 Core Capabilities</div>", unsafe_allow_html=True)

        services = [
            {"icon":"🤖","title":"AI Fault Detection","desc":"Advanced Random Forest model trained on 14 electrical indicators for real-time PV fault detection — short circuits, disconnections, shading, and sensor faults.","color":"#0ea5e9"},
            {"icon":"📡","title":"Live IoT Monitoring","desc":"Direct ThingSpeak integration for continuous voltage, current, UV, and dust data streaming with instant anomaly alerts.","color":"#d97706"},
            {"icon":"🔋","title":"Battery Health Monitor","desc":"Precision SOC estimation using OCV curve analysis with charge/discharge cycle tracking and critical threshold alerts.","color":"#0369a1"},
            {"icon":"🧹","title":"Cloud-Triggered Panel Cleaning","desc":"Global remote cleaning control via ThingSpeak Field 8. The ESP32 polls the cloud and executes commands from anywhere in the world.","color":"#059669"},
            {"icon":"🔭","title":"Predictive Health Forecasting","desc":"6-hour energy production forecasts with risk scoring to drive timely maintenance decisions before faults develop.","color":"#7c3aed"},
            {"icon":"📅","title":"Daily Performance Reports","desc":"Comprehensive daily analysis including fault-cause loss breakdown, system efficiency, and hourly status tracking.","color":"#ea580c"},
        ]
        col1, col2 = st.columns(2)
        for i, srv in enumerate(services):
            col = col1 if i % 2 == 0 else col2
            with col:
                st.markdown(f"""
                <div class='mn-card' style='padding:20px 22px;margin-bottom:12px;'>
                  <div style='display:flex;align-items:flex-start;gap:16px;'>
                    <div style='font-size:1.9rem;min-width:44px;text-align:center;padding-top:2px;'>{srv['icon']}</div>
                    <div style='flex:1;'>
                      <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:0.88rem;color:{srv['color']};'>{srv['title']}</div>
                      <div style='font-size:0.78rem;color:var(--text-secondary);margin-top:6px;line-height:1.7;'>{srv['desc']}</div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='font-size:0.72rem;color:var(--text-secondary);letter-spacing:2px;text-transform:uppercase;margin:28px 0 16px 0;font-weight:700;'>⚙️ Technology Stack</div>", unsafe_allow_html=True)
        techs = [
            ("🐍","Python & Streamlit","Backend & Dashboard"),
            ("🤖","Scikit-learn RF","ML Fault Detection"),
            ("📡","ThingSpeak API","IoT Data Platform"),
            ("⚡","ESP32","Hardware Control"),
            ("📊","Plotly","Interactive Charts"),
            ("🔋","OCV Model","SOC Estimation"),
        ]
        tc = st.columns(6)
        for col, (icon, name, sub) in zip(tc, techs):
            with col:
                st.markdown(f"""<div style='background:var(--bg-card);border:1px solid var(--border);border-radius:14px;
                                            padding:16px 8px;text-align:center;box-shadow:var(--shadow);'>
                  <div style='font-size:1.5rem;'>{icon}</div>
                  <div style='font-family:"Space Grotesk",sans-serif;font-size:0.65rem;color:var(--accent-navy);
                              margin:8px 0 4px 0;letter-spacing:0.5px;font-weight:700;'>{name}</div>
                  <div style='font-size:0.62rem;color:var(--text-muted);'>{sub}</div>
                </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: CONTACT US
    # ─────────────────────────────────────
    def panel_contact_us(self):
        st.markdown("<div class='mn-section'><span style='font-size:1rem'>📞</span><span class='mn-section-title'>Contact Us — Project Team</span></div>", unsafe_allow_html=True)

        # Official project email banner
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,rgba(29,111,164,0.08),rgba(14,165,233,0.05));
                    border:1.5px solid rgba(29,111,164,0.25);border-radius:18px;padding:28px 36px;
                    margin-bottom:28px;position:relative;overflow:hidden;box-shadow:var(--shadow);'>
          <div style='position:absolute;top:0;left:0;right:0;height:4px;
                      background:linear-gradient(90deg,#d97706,#0ea5e9,#1d6fa4);border-radius:18px 18px 0 0;'></div>
          <div style='display:flex;align-items:center;gap:16px;margin-bottom:12px;'>
            <span style='font-size:2rem;'>📧</span>
            <div>
              <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:0.7rem;
                          color:var(--text-secondary);letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;'>Official Project Email — Primary Contact Channel</div>
              <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:1.4rem;color:var(--accent-blue);'>
                menawar030@gmail.com</div>
            </div>
          </div>
          <div style='font-size:0.82rem;color:var(--text-secondary);line-height:1.8;max-width:700px;'>
            For all project inquiries, demonstrations, collaborations, and technical questions,
            please reach us at the address above. Our team typically responds within 24–48 hours.
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Academic Advisor
        st.markdown("<div style='font-size:0.72rem;color:var(--text-secondary);letter-spacing:2px;text-transform:uppercase;margin:8px 0 16px 0;font-weight:700;'>🎓 Academic Advisor</div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background:var(--bg-card);border:1px solid rgba(29,111,164,0.25);border-radius:16px;
                    padding:22px 28px;margin-bottom:24px;box-shadow:var(--shadow);position:relative;overflow:hidden;'>
          <div style='position:absolute;top:0;left:0;bottom:0;width:4px;background:linear-gradient(180deg,#1d6fa4,#0ea5e9);border-radius:16px 0 0 16px;'></div>
          <div style='margin-left:10px;'>
            <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:1.05rem;color:var(--accent-navy);margin-bottom:4px;'>Dr. Asmaa Gamal Seliem</div>
            <div style='font-size:0.78rem;color:var(--accent-blue);font-weight:600;margin-bottom:14px;'>Faculty Academic Supervisor &amp; Project Advisor</div>
            <div style='display:flex;gap:28px;flex-wrap:wrap;'>
              <div style='display:flex;align-items:center;gap:8px;'>
                <span style='font-size:1rem;'>📧</span>
                <span style='font-size:0.82rem;color:var(--text-primary);font-weight:500;'>Asmaseliem90@gmail.com</span>
              </div>
              <div style='display:flex;align-items:center;gap:8px;'>
                <span style='font-size:1rem;'>📱</span>
                <span style='font-family:"Space Grotesk",sans-serif;font-size:0.82rem;color:var(--text-primary);font-weight:500;'>+201096687807</span>
              </div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        # Team Members
        st.markdown("<div style='font-size:0.72rem;color:var(--text-secondary);letter-spacing:2px;text-transform:uppercase;margin:8px 0 16px 0;font-weight:700;'>👥 Project Team Members</div>", unsafe_allow_html=True)

        team = [
            {
                "name": "Mohammed Osama Mohammed",
                "role": "IoT Implementation",
                "desc": "Responsible for the end-to-end IoT integration: ESP32 hardware programming, ThingSpeak cloud connectivity, sensor wiring, and real-time data acquisition pipeline.",
                "email": "mohamnedosama2030@gmail.com",
                "phone": "+201129427374",
                "color": "#0ea5e9",
                "icon": "📡"
            },
            {
                "name": "Sherif Alaa Eldin Ahmed",
                "role": "Mechanical & Cleaning System",
                "desc": "Designed and built the mechanical structure of the automated panel cleaning system, including actuator integration and cleaning mechanism validation.",
                "email": "sherifalaa2001@gmail.com",
                "phone": "+201020645697",
                "color": "#059669",
                "icon": "🔧"
            },
            {
                "name": "Mustafa Emad Rifai",
                "role": "Artificial Intelligence",
                "desc": "Developed the machine learning fault detection engine — data preprocessing, feature engineering, Random Forest model training, and classification pipeline.",
                "email": "mustafaemad2065@gmail.com",
                "phone": "+201012245407",
                "color": "#7c3aed",
                "icon": "🤖"
            },
            {
                "name": "Youssef Mustafa Sayed",
                "role": "Cloud & Communications",
                "desc": "Architected the cloud data flow between ThingSpeak and the Streamlit dashboard, managing API integrations, multi-tenant configuration, and deployment infrastructure.",
                "email": "Yousefmustafa446@gmail.com",
                "phone": "+201150546317",
                "color": "#d97706",
                "icon": "☁️"
            },
            {
                "name": "Omar Abdallah Noaman",
                "role": "Artificial Intelligence",
                "desc": "Contributed to AI model evaluation, dataset curation, rule-based override logic, and predictive health forecasting algorithms.",
                "email": "omara.noaman58@gmail.com",
                "phone": "+201551380331",
                "color": "#1d6fa4",
                "icon": "🧠"
            },
        ]

        col1, col2 = st.columns(2)
        for i, member in enumerate(team):
            col = col1 if i % 2 == 0 else col2
            with col:
                st.markdown(f"""
                <div class='mn-card' style='padding:22px 24px;margin-bottom:14px;'>
                  <div style='display:flex;align-items:flex-start;gap:16px;'>
                    <div style='min-width:52px;height:52px;background:{member["color"]}15;border:2px solid {member["color"]}40;
                                border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0;'>
                      {member["icon"]}
                    </div>
                    <div style='flex:1;'>
                      <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:0.92rem;color:var(--accent-navy);'>{member["name"]}</div>
                      <div style='display:inline-block;background:{member["color"]}12;color:{member["color"]};
                                  padding:2px 12px;border-radius:20px;font-size:0.68rem;font-weight:700;
                                  border:1px solid {member["color"]}30;margin:5px 0 10px 0;letter-spacing:0.5px;'>{member["role"]}</div>
                      <div style='font-size:0.77rem;color:var(--text-secondary);line-height:1.7;margin-bottom:12px;'>{member["desc"]}</div>
                      <div style='display:flex;flex-direction:column;gap:6px;'>
                        <div style='display:flex;align-items:center;gap:8px;background:var(--bg-card2);
                                    border-radius:8px;padding:7px 10px;border:1px solid var(--border);'>
                          <span style='font-size:0.85rem;'>📧</span>
                          <span style='font-size:0.76rem;color:var(--accent-blue);font-weight:500;'>{member["email"]}</span>
                        </div>
                        <div style='display:flex;align-items:center;gap:8px;background:var(--bg-card2);
                                    border-radius:8px;padding:7px 10px;border:1px solid var(--border);'>
                          <span style='font-size:0.85rem;'>📱</span>
                          <span style='font-family:"Space Grotesk",sans-serif;font-size:0.76rem;color:var(--text-primary);font-weight:500;'>{member["phone"]}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # ThingSpeak link
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background:var(--bg-card2);border:1px solid var(--border);border-radius:14px;
                    padding:20px 28px;text-align:center;box-shadow:var(--shadow);'>
          <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:0.7rem;
                      color:var(--text-secondary);letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;'>Project Data Channel</div>
          <div style='font-size:0.85rem;color:var(--accent-blue);font-weight:600;'>
            📊 ThingSpeak Channel — <span style='color:var(--accent-navy);'>Configure via sidebar to connect your own channel</span>
          </div>
          <div style='font-size:0.78rem;color:var(--text-muted);margin-top:6px;'>
            Menawar PV Intelligence · Graduation Project 2024–2025
          </div>
        </div>""", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  MAIN RENDER
    # ─────────────────────────────────────
    def render(self):
        now       = datetime.now()
        night_now = is_night_time(now.time())
        prod_now  = is_production_period(now.time())
        inject_css()

        # ── SIDEBAR ──────────────────────
        sb_logo = logo_svg(w=70, h=48, uid="sb")
        st.sidebar.markdown(f"""
        <div style='text-align:center;padding:16px 0 14px 0;border-bottom:1.5px solid var(--border);margin-bottom:16px;'>
          <div class='mn-logo-anim' style='display:inline-block;'>{sb_logo}</div>
          <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:1.15rem;
                      color:var(--accent-navy);letter-spacing:4px;margin-top:10px;'>MENAWAR</div>
          <div style='font-size:0.56rem;color:var(--text-muted);letter-spacing:2px;text-transform:uppercase;margin-top:3px;'>Technology &amp; Renewable Energy</div>
        </div>""", unsafe_allow_html=True)

        # ── DYNAMIC THINGSPEAK SETTINGS ──
        st.sidebar.markdown("## 🔗 THINGSPEAK CHANNEL")
        st.sidebar.text_input(
            "Channel ID",
            key="ts_channel_id",
            placeholder="e.g. 3274646",
            help="Your ThingSpeak Channel ID (numeric)"
        )
        st.sidebar.text_input(
            "Read API Key",
            key="ts_read_key",
            placeholder="e.g. ZGH7UMZPP8KWY4N3",
            type="password",
            help="ThingSpeak Read API Key for fetching data"
        )
        st.sidebar.text_input(
            "Write API Key",
            key="ts_write_key",
            placeholder="e.g. XXXXXXXXXXXXX",
            type="password",
            help="ThingSpeak Write API Key — required for cloud cleaning control"
        )
        if st.sidebar.button("🔌 Connect to Channel", use_container_width=True, type="primary"):
            st.cache_data.clear()
            st.sidebar.success("✅ Cache cleared. Fetching fresh channel data...")
            st.rerun()

        st.sidebar.markdown("---")

        # ── NAVIGATION ──
        st.sidebar.markdown("## 📌 NAVIGATION")
        if 'active_panel' not in st.session_state:
            st.session_state.active_panel = "home"

        sidebar_nav = [
            ("🏠", "Home",       "home",       "Full dashboard overview"),
            ("📞", "Contact Us", "contact_us", "Get in touch with the team"),
            ("🌟", "About Us",   "about_us",   "Our project & capabilities"),
        ]
        for icon, label, key, hint in sidebar_nav:
            active = st.session_state.active_panel == key
            active_style = ("background:rgba(29,111,164,0.08);border:1.5px solid rgba(29,111,164,0.4);"
                            "box-shadow:0 2px 8px rgba(29,111,164,0.12);" if active
                            else "background:var(--bg-card2);border:1px solid var(--border);")
            label_color = "var(--accent-blue)" if active else "var(--text-primary)"
            st.sidebar.markdown(f"""
            <div style='{active_style}display:flex;align-items:center;gap:12px;padding:11px 14px;border-radius:12px;margin-bottom:5px;'>
              <span style='font-size:1.1rem;'>{icon}</span>
              <div>
                <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:0.74rem;color:{label_color};letter-spacing:0.5px;'>{label}</div>
                <div style='font-size:0.62rem;color:var(--text-muted);'>{hint}</div>
              </div>
            </div>""", unsafe_allow_html=True)
            if st.sidebar.button(f"Go to {label}", key=f"sb_{key}", use_container_width=True, help=hint):
                st.session_state.active_panel = key
                st.rerun()

        st.sidebar.markdown("---")

        # ── OPERATION MODE ──
        auto_refresh=False; is_connected=True; diff_sec=0
        st.sidebar.markdown("## ⚙ OPERATION MODE")
        mode = st.sidebar.radio("", ["📡 Live ThingSpeak","🎛 Manual Simulation"])

        if mode=="📡 Live ThingSpeak":
            auto_refresh=st.sidebar.toggle("🔄 Auto-Refresh (16s)", value=True)
            v_pv,v_batt,amp,uv_in,dust_in,pwr,ideal_pwr,t_in,success,is_connected,diff_sec=self.fetch_live()
            if success:
                st.sidebar.markdown(f"""<div style='background:rgba(5,150,105,0.07);border:1px solid rgba(5,150,105,0.28);
                  border-radius:10px;padding:10px 12px;margin:8px 0;display:flex;align-items:center;gap:8px;'>
                  <span class='online-dot'></span>
                  <span style='font-size:0.78rem;color:#059669;font-weight:600;'>Connected · {now.strftime('%H:%M:%S')}</span>
                </div>""", unsafe_allow_html=True)
            else:
                if self.channel_id and self.read_api_key:
                    st.sidebar.error("⚠️ Connection failed. Using fallback values.")
                v_pv,v_batt,amp,uv_in,dust_in,pwr,ideal_pwr,t_in = 17.5,12.4,1.1,8.0,5.0,19.25,20.0,now.time()
        else:
            if 'ui_time' not in st.session_state: st.session_state.ui_time=now.time()
            t_in    =st.sidebar.time_input("Time",value=st.session_state.ui_time)
            uv_in   =st.sidebar.slider("UV Index",0.0,12.0,8.0)
            dust_in =st.sidebar.slider("Dust (%)",0.0,100.0,5.0)
            v_pv    =st.sidebar.number_input("PV Voltage (V)",value=17.5)
            v_batt  =st.sidebar.number_input("Battery Voltage (V)",value=12.4)
            amp     =st.sidebar.number_input("Current (A)",value=1.1)
            ideal_pwr=20.0; pwr=None; is_connected=True

        st.sidebar.markdown("---")
        nl  = "🌙 NIGHT MODE" if night_now else ("⚡ PRODUCTION" if prod_now else "— STANDBY")
        nc  = "#7c3aed" if night_now else ("#059669" if prod_now else "#64748b")
        st.sidebar.markdown(f"""<div style='text-align:center;padding:9px;background:{nc}10;border-radius:10px;
          border:1.5px solid {nc}40;font-family:"Space Grotesk",sans-serif;font-weight:700;color:{nc};
          letter-spacing:2px;font-size:0.72rem;'>{nl}</div>""", unsafe_allow_html=True)

        # ── PROCESS TELEMETRY ──
        features_df,pwr_out,soc,is_prod=self.process_telemetry(v_pv,v_batt,amp,uv_in,dust_in,t_in,pwr,ideal_pwr)
        is_night =is_night_time(t_in); is_prod_p=is_production_period(t_in)

        try:
            pred_idx=self.rf.predict(features_df)[0]; ai_status=self.le.inverse_transform([pred_idx])[0]
            probs=self.rf.predict_proba(features_df)[0]; confidence=float(np.max(probs))
            vd=features_df['V_Diff'].values[0]
            final_status,css_class,alert_fn,alert_text,fault_detail=self.rule_override(
                v_pv,v_batt,amp,uv_in,dust_in,soc,vd,is_night,is_connected,mode,ai_status)
        except Exception as e:
            final_status="Unknown"; css_class="warn"; alert_fn=st.warning
            alert_text=f"Diagnosis error: {e}"; fault_detail=None; confidence=0.0

        # ── HEADER ──
        hdr_logo = logo_svg(w=90, h=62, uid="hdr")
        st.markdown(f"""
        <div style='display:flex;align-items:center;gap:20px;margin-bottom:8px;'>
          <div class='mn-logo-anim'>{hdr_logo}</div>
          <div>
            <div style='font-size:0.58rem;color:var(--accent-blue);letter-spacing:3px;text-transform:uppercase;margin-bottom:4px;font-weight:600;'>Technology &amp; Renewable Energy</div>
            <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:2rem;
                        color:var(--accent-navy);letter-spacing:4px;'>MENAWAR</div>
            <div style='font-family:"Space Grotesk",sans-serif;font-size:0.82rem;font-weight:700;
                        color:var(--accent-blue);letter-spacing:2px;text-transform:uppercase;margin-top:2px;'>PV Diagnostic Intelligence</div>
            <div style='font-size:0.65rem;color:var(--text-muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:3px;'>AI-Powered Solar Panel Health Monitoring &middot; {now.strftime('%A, %d %B %Y &middot; %H:%M')}</div>
          </div>
        </div>
        <div style='height:2px;background:linear-gradient(90deg,transparent,var(--accent-blue),var(--accent-sky),var(--accent-green),transparent);margin-bottom:18px;border-radius:2px;'></div>
        """, unsafe_allow_html=True)

        # ── TOP NAV BUTTONS ──
        nav_items=[
            ("⚡","Overview","Live metrics & status","overview"),
            ("🤖","AI Diagnosis","Fault detection engine","diagnosis"),
            ("📅","Day Report","Today's full history","day_report"),
            ("🔋","Battery","SOC & discharge log","battery"),
            ("🔭","Predictive","Forecast & risk score","prediction"),
            ("🧹","Cleaning","Panel cleaning control","cleaning"),
        ]
        nav_cols=st.columns(6)
        for col,(icon,title,sub,key) in zip(nav_cols,nav_items):
            active=st.session_state.active_panel==key
            border_style=f"2px solid var(--accent-blue)" if active else "1.5px solid var(--border)"
            bg_style="rgba(29,111,164,0.07)" if active else "var(--bg-card)"
            shadow_style="0 2px 12px rgba(29,111,164,0.15)" if active else "var(--shadow)"
            with col:
                st.markdown(f"""<div style='background:{bg_style};border:{border_style};border-radius:14px;
                    padding:12px 8px;text-align:center;margin-bottom:4px;box-shadow:{shadow_style};'>
                  <div style='font-size:1.4rem;'>{icon}</div>
                  <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:0.65rem;
                              color:{"var(--accent-blue)" if active else "var(--text-secondary)"};
                              letter-spacing:1px;text-transform:uppercase;margin-top:5px;'>{title}</div>
                  <div style='font-size:0.58rem;color:var(--text-muted);margin-top:2px;'>{sub}</div>
                </div>""", unsafe_allow_html=True)
                if st.button(f"Open {title}", key=f"btn_{key}", use_container_width=True, help=sub):
                    st.session_state.active_panel=key
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── PANEL ROUTING ──
        panel = st.session_state.active_panel

        if panel == "home":
            hist_df = None
            if mode == "📡 Live ThingSpeak":
                with st.spinner("📡 Loading today's data..."):
                    hist_df = self.fetch_history()
            self.panel_home(v_pv, v_batt, amp, pwr_out, soc, uv_in, dust_in,
                            is_night, is_prod_p, final_status, css_class,
                            diff_sec, is_connected, mode, confidence, alert_fn, alert_text,
                            features_df, fault_detail, hist_df)

        elif panel == "overview":
            self.panel_overview(v_pv, v_batt, amp, pwr_out, soc, uv_in, dust_in,
                                is_night, is_prod_p, final_status, css_class,
                                diff_sec, is_connected, mode, confidence, alert_fn, alert_text)

        elif panel == "diagnosis":
            self.panel_diagnosis(v_pv, v_batt, amp, uv_in, dust_in, soc, features_df,
                                 final_status, css_class, alert_fn, alert_text, fault_detail, confidence)

        elif panel == "day_report":
            hist_df = None
            if mode == "📡 Live ThingSpeak":
                with st.spinner("📡 Loading today's data..."):
                    hist_df = self.fetch_history()
            self.panel_day_report(hist_df)

        elif panel == "battery":
            hist_df = None
            if mode == "📡 Live ThingSpeak":
                with st.spinner("📡 Loading history..."):
                    hist_df = self.fetch_history()
            self.panel_battery(soc, v_batt, is_prod_p, is_night, mode, hist_df)

        elif panel == "prediction":
            hist_df = None
            if mode == "📡 Live ThingSpeak":
                with st.spinner("📡 Loading history..."):
                    hist_df = self.fetch_history()
            self.panel_prediction(v_pv, v_batt, amp, uv_in, dust_in, soc, features_df, final_status, hist_df)

        elif panel == "cleaning":
            self.panel_cleaning(dust_in)

        elif panel == "about_us":
            self.panel_about_us()

        elif panel == "contact_us":
            self.panel_contact_us()

        # ── AUTO REFRESH ──
        if mode == "📡 Live ThingSpeak" and auto_refresh and panel not in ("about_us", "contact_us", "home"):
            st.caption(f"🔄 Next refresh in 16s · Last update: {now.strftime('%H:%M:%S')}")
            time.sleep(16)
            st.rerun()


if __name__ == "__main__":
    app = PVDashboard()
    app.render()