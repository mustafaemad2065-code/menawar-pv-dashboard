import streamlit as st
import pandas as pd
import numpy as np
import joblib
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Cairo timezone — كل datetime.now() يمر من هنا
_CAIRO = ZoneInfo("Africa/Cairo")
def now_cairo() -> datetime:
    return datetime.now(_CAIRO)

# ─────────────────────────────────────────
#  PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Menawar PV Intelligence",
    layout="wide",
    page_icon="☀️",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════════
#  FIX 3 — LOCK LIGHT THEME: injected immediately, before anything
#  else renders.  All dark-mode CSS blocks have been removed.
# ═══════════════════════════════════════════════════════════════════
def inject_css() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

/* ══ FORCE LIGHT THEME — ALL CONTEXTS ══ */
:root,html,body,
[data-theme="light"],[data-theme="dark"],
.stApp,[data-testid="stAppViewContainer"],
[data-testid="stMain"],.main{
  background:#f4f7f2 !important;
  color:#1a2e12       !important;
  font-family:'Plus Jakarta Sans',sans-serif !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"]{
  background:#ffffff !important;
  border-right:1.5px solid rgba(58,125,30,.14) !important;
  box-shadow:2px 0 16px rgba(45,90,22,.07)    !important;
}
[data-testid="stSidebar"] *{color:#1a2e12 !important;}
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3{
  color:#2d6a2d !important;
  font-family:'Space Grotesk',sans-serif !important;
  font-size:.7rem !important;
  letter-spacing:1.5px;
  text-transform:uppercase;
}

/* ── METRICS ── */
[data-testid="stMetric"]{
  background:#ffffff !important;
  border:1px solid rgba(58,125,30,.14) !important;
  border-radius:14px !important;
  padding:16px 18px !important;
  box-shadow:0 1px 4px rgba(45,90,22,.08),0 4px 16px rgba(45,90,22,.05) !important;
  transition:transform .2s,box-shadow .2s;
  position:relative;
}
[data-testid="stMetric"]:hover{
  transform:translateY(-2px);
  box-shadow:0 4px 14px rgba(45,90,22,.12),0 8px 32px rgba(45,90,22,.07) !important;
}
[data-testid="stMetric"]::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,#3a7d1e,#d4a030);
  border-radius:14px 14px 0 0;
}
[data-testid="stMetricLabel"]>div{
  color:#4a6741 !important;
  font-size:.65rem !important;
  font-weight:600 !important;
  letter-spacing:1px;
  text-transform:uppercase;
}
[data-testid="stMetricValue"]{
  color:#2d6a2d !important;
  font-family:'Space Grotesk',sans-serif !important;
  font-size:1.45rem !important;
  font-weight:700 !important;
}
[data-testid="stMetricDelta"]{font-size:.7rem !important;color:#4a6741 !important;}

/* ── TABS ── */
[data-testid="stTabs"] [role="tab"]{
  font-family:'Space Grotesk',sans-serif !important;
  font-size:.68rem !important;
  letter-spacing:1px;text-transform:uppercase;
  color:#4a6741 !important;
  padding:10px 18px !important;
  background:transparent !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{
  color:#3a7d1e !important;
  border-bottom:2px solid #3a7d1e !important;
  font-weight:700 !important;
}
[data-testid="stTabsContent"]{background:transparent !important;}

/* ── BUTTONS ── */
.stButton button{
  background:#ffffff !important;
  border:1.5px solid rgba(58,125,30,.35) !important;
  color:#3a7d1e !important;
  font-family:'Space Grotesk',sans-serif !important;
  font-size:.65rem !important;
  letter-spacing:1px;font-weight:600 !important;
  border-radius:10px !important;
  transition:all .2s !important;
  box-shadow:0 1px 4px rgba(45,90,22,.08) !important;
}
.stButton button:hover{
  background:rgba(58,125,30,.07) !important;
  border-color:#3a7d1e !important;
  color:#2d5a16 !important;
  transform:translateY(-1px) !important;
}
.stButton button[kind="primary"]{
  background:linear-gradient(135deg,#2d6a2d,#3a7d1e) !important;
  color:#ffffff !important;border:none !important;
}
.stButton button[kind="primary"]:hover{opacity:.92 !important;color:#ffffff !important;}

/* ── CARDS ── */
.mn-card{
  background:#ffffff;
  border:1px solid rgba(58,125,30,.14);
  border-radius:16px;
  padding:20px 24px;
  position:relative;overflow:hidden;
  box-shadow:0 1px 4px rgba(45,90,22,.08),0 4px 16px rgba(45,90,22,.05);
  transition:transform .2s,box-shadow .2s;
  margin-bottom:10px;
  color:#1a2e12;
}
.mn-card:hover{
  transform:translateY(-2px);
  box-shadow:0 4px 14px rgba(45,90,22,.12),0 8px 32px rgba(45,90,22,.07);
}
.mn-card::before{
  content:'';
  position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,#3a7d1e,#d4a030,#5aad2e);
  border-radius:16px 16px 0 0;
}

/* ── CONNECTION STATUS CARDS ── */
.conn-success-card{
  background:rgba(45,138,62,.07);
  border:1.5px solid rgba(45,138,62,.30);
  border-radius:12px;padding:12px 16px;
  display:flex;align-items:center;gap:10px;margin:8px 0;
}
.conn-error-card{
  background:rgba(220,38,38,.06);
  border:1.5px solid rgba(220,38,38,.28);
  border-radius:12px;padding:12px 16px;margin:8px 0;
}

/* ── SECTION HEADERS ── */
.mn-section{
  display:flex;align-items:center;gap:10px;
  margin:20px 0 16px 0;padding-bottom:10px;
  border-bottom:1.5px solid rgba(58,125,30,.14);
}
.mn-section-title{
  font-family:'Space Grotesk',sans-serif;
  font-weight:700;font-size:.78rem;
  color:#2d6a2d;letter-spacing:2px;text-transform:uppercase;
}

/* ── LIST ROWS ── */
.hr-row{
  display:flex;align-items:center;gap:10px;
  padding:10px 14px;border-radius:10px;margin-bottom:4px;
  background:#f8faf6;border:1px solid rgba(58,125,30,.12);
  transition:background .15s,box-shadow .15s;color:#1a2e12;
}
.hr-row:hover{background:rgba(58,125,30,.05);box-shadow:0 1px 4px rgba(45,90,22,.08);}

/* ── INPUTS ── */
[data-testid="stTextInput"] input{
  background:#f8faf6 !important;
  border:1.5px solid rgba(58,125,30,.18) !important;
  color:#1a2e12 !important;border-radius:8px !important;font-size:.8rem !important;
}
[data-testid="stTextInput"] input:focus{
  border-color:#3a7d1e !important;
  box-shadow:0 0 0 3px rgba(58,125,30,.12) !important;
}
[data-testid="stTextInput"] label{color:#4a6741 !important;}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:#eaf0e6;}
::-webkit-scrollbar-thumb{background:rgba(58,125,30,.35);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:#3a7d1e;}

/* ── ANIMATIONS ── */
@keyframes mnGlow{
  0%  {filter:drop-shadow(0 0 4px rgba(58,125,30,.35)) drop-shadow(0 0 2px rgba(212,160,48,.3));}
  50% {filter:drop-shadow(0 0 14px rgba(58,125,30,.75)) drop-shadow(0 0 8px rgba(212,160,48,.65));}
  100%{filter:drop-shadow(0 0 4px rgba(58,125,30,.35)) drop-shadow(0 0 2px rgba(212,160,48,.3));}
}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:.4;}}
@keyframes slideIn{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}

.mn-logo-anim{animation:mnGlow 3s ease-in-out infinite;}
.online-dot{
  display:inline-block;width:8px;height:8px;
  background:#2d8a3e;border-radius:50%;
  animation:pulse 2s infinite;box-shadow:0 0 6px #2d8a3e;
}
.panel-content{animation:slideIn .22s ease-out;}

/* ── ALERTS ── */
[data-testid="stAlert"]{border-radius:12px !important;background:#f8faf6 !important;}

/* ── RADIO / TOGGLES ── */
[data-testid="stRadio"] label{font-size:.8rem !important;color:#1a2e12 !important;}
[data-testid="stToggle"] label{font-size:.8rem !important;color:#1a2e12 !important;}

/* ── PLOTLY CONTAINERS ── */
.stPlotlyChart{background:transparent !important;}
.js-plotly-plot .plotly .bg{fill:transparent !important;}

/* ── FORECAST HOUR CARDS ── */
.hour-card{
  background:#ffffff;border:1px solid rgba(58,125,30,.14);
  border-radius:12px;padding:14px 8px;text-align:center;
  box-shadow:0 1px 4px rgba(45,90,22,.07);color:#1a2e12;
}

/* ── NAV BUTTON LABEL FIX ── */
.stButton button p{margin:0 !important;}

/* ── SELECTBOX / DROPDOWN ── */
[data-baseweb="select"] *{color:#1a2e12 !important;background:#ffffff !important;}

/* ── HEADER GRADIENT DIVIDER ── */
.mn-divider{
  height:2.5px;
  background:linear-gradient(90deg,transparent,#3a7d1e,#d4a030,#5aad2e,transparent);
  border-radius:2px;margin-bottom:18px;
}

/* ── STATUS PERIOD BADGE ── */
.period-badge{
  text-align:center;padding:9px 14px;border-radius:10px;
  font-family:'Space Grotesk',sans-serif;font-weight:700;
  letter-spacing:2px;font-size:.7rem;
}

/* ── MAIN BLOCK CONTAINER ── */
.main .block-container{padding-top:1rem !important;}

/* ── ENSURE ALL TEXT STAYS DARK ON LIGHT BG ── */
p,span,div,label,h1,h2,h3,h4,h5,h6,li{color:#1a2e12;}
code{background:rgba(58,125,30,.08);color:#3a7d1e;}
</style>
""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────
#  PLOTLY LIGHT THEME CONSTANTS
# ─────────────────────────────────────────
PLOT_BG     = "rgba(0,0,0,0)"
PAPER_BG    = "rgba(0,0,0,0)"
GRID_COLOR  = "rgba(58,125,30,0.09)"
FONT_COLOR  = "#2d5a1a"
FONT_FAMILY = "Plus Jakarta Sans"


def light_layout(**kwargs) -> dict:
    base = dict(
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(family=FONT_FAMILY, color=FONT_COLOR, size=10),
        xaxis=dict(
            gridcolor=GRID_COLOR, linecolor=GRID_COLOR,
            tickfont=dict(color=FONT_COLOR), title_font=dict(color=FONT_COLOR),
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR, linecolor=GRID_COLOR,
            tickfont=dict(color=FONT_COLOR), title_font=dict(color=FONT_COLOR),
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)", bordercolor=GRID_COLOR,
            borderwidth=1, font=dict(color=FONT_COLOR, size=9),
        ),
        margin=dict(l=12, r=12, t=44, b=28),
    )
    base.update(kwargs)
    return base


# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def is_night_time(t) -> bool:
    if isinstance(t, datetime):
        t = t.time()
    return (t.hour > 19) or (t.hour == 19 and t.minute >= 30) or (t.hour < 6)


def is_production_period(t) -> bool:
    if isinstance(t, datetime):
        t = t.time()
    return (
        (t.hour > 6) or (t.hour == 6 and t.minute >= 0)
    ) and (
        (t.hour < 19) or (t.hour == 19 and t.minute <= 30)
    )


def fmt_seconds(sec: int) -> str:
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    m, s = divmod(sec, 60)
    return f"{m}m {s:02d}s"


_OCV = [
    (11.00, 0), (11.50, 10), (11.75, 20), (12.00, 30),
    (12.25, 45), (12.50, 60), (12.65, 70), (12.80, 80),
    (13.00, 90), (13.20, 95), (13.50, 100),
]


def voltage_to_soc(v: float, charging: bool = False) -> float:
    v = v - 0.30 if charging else v
    v = max(_OCV[0][0], min(_OCV[-1][0], v))
    for i in range(len(_OCV) - 1):
        v0, s0 = _OCV[i]
        v1, s1 = _OCV[i + 1]
        if v0 <= v <= v1:
            return round(s0 + (s1 - s0) * (v - v0) / (v1 - v0), 1)
    return 100.0


def soc_color(s: float) -> str:
    if s >= 80:
        return "#2d8a3e"
    if s >= 50:
        return "#3a7d1e"
    if s >= 30:
        return "#d4a030"
    return "#dc2626"


def fault_color(status: str) -> str:
    s = status.lower()
    if "normal"      in s: return "#2d8a3e"
    if "night"       in s: return "#5b6a3e"
    if "ramp"        in s: return "#2d8a3e"   # ramp-up is healthy
    if "industrial"  in s: return "#991b1b"   # permanent shading — critical
    if "cloud"       in s: return "#c47a1e"   # temporary shading — warn
    if "shading"     in s: return "#d4a030"   # fallback shading
    if "soiling"     in s: return "#c47a1e"
    if "disconnect"  in s: return "#dc2626"
    if "short"       in s: return "#991b1b"
    if "sensor"      in s: return "#b8860b"
    if "full"        in s: return "#2d8a3e"
    if "critical"    in s: return "#dc2626"
    return "#64748b"


def fault_loss(status: str) -> int:
    s = status.lower()
    if "normal"            in s: return 0
    if "ramp"              in s: return 0    # ramp-up is not a fault
    if "night"             in s: return 0
    if "full"              in s: return 0
    if "short"             in s: return 100
    if "disconnect"        in s: return 100
    if "industrial shading" in s: return 85
    if "cloud shading"     in s: return 40
    if "shading"           in s: return 50  # fallback
    if "soiling"           in s: return 30
    if "sensor"            in s: return 10
    return 20


@st.cache_resource
def load_ml():
    try:
        rf = joblib.load("rf_model.pkl")
        le = joblib.load("label_encoder.pkl")
        return rf, le
    except Exception as e:
        st.error(
            f"⚠️ Model files not found: {e}. "
            "Ensure rf_model.pkl and label_encoder.pkl are present."
        )
        st.stop()


# ─────────────────────────────────────────
#  FIX 2 — LOGO LOADER  (JPG/PNG or styled fallback)
# ─────────────────────────────────────────
def _logo_paths() -> list[str]:
    return ["logo.jpg", "logo.png", "logo.jpeg", "logo.JPG", "logo.PNG"]


def render_logo_sidebar() -> None:
    """Render logo in sidebar: base64 inline HTML for crisp display, else styled text card."""
    import base64 as _b64
    for path in _logo_paths():
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = _b64.b64encode(f.read()).decode()
            ext = path.rsplit(".", 1)[-1].lower().replace("jpg", "jpeg")
            st.sidebar.markdown(
                f"<div style='text-align:center;margin-bottom:8px;'>"
                f"<img src='data:image/{ext};base64,{b64}' "
                f"style='max-width:100%;height:auto;border-radius:12px;"
                f"display:block;margin:0 auto;'/></div>",
                unsafe_allow_html=True,
            )
            return
    # Fallback styled card
    st.sidebar.markdown(
        """
<div style='text-align:center;padding:16px 12px;
            background:linear-gradient(135deg,rgba(58,125,30,.08),rgba(212,160,48,.05));
            border:2px solid rgba(58,125,30,.28);border-radius:16px;margin-bottom:4px;'>
  <div style='font-size:2rem;margin-bottom:4px;'>☀️</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:1.1rem;
              color:#2d6a2d;letter-spacing:3px;'>MENAWAR</div>
  <div style='font-size:.56rem;color:#8aaa7a;letter-spacing:2px;text-transform:uppercase;margin-top:3px;'>
    PV Intelligence</div>
</div>""",
        unsafe_allow_html=True,
    )


def render_logo_header() -> None:
    """Render logo in main header: base64 inline HTML for crisp display, else emoji badge."""
    import base64 as _b64
    for path in _logo_paths():
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = _b64.b64encode(f.read()).decode()
            ext = path.rsplit(".", 1)[-1].lower().replace("jpg", "jpeg")
            col_img, col_txt = st.columns([1, 6])
            with col_img:
                st.markdown(
                    f"<img src='data:image/{ext};base64,{b64}' "
                    f"style='width:100%;max-width:110px;height:auto;"
                    f"border-radius:14px;display:block;margin-top:4px;'/>",
                    unsafe_allow_html=True,
                )
            with col_txt:
                _header_text()
            return
    # Fallback
    col_badge, col_txt = st.columns([1, 6])
    with col_badge:
        st.markdown(
            """<div style='background:linear-gradient(135deg,#2d6a2d,#3a7d1e);
                border-radius:18px;padding:16px;text-align:center;margin-top:4px;'>
              <div style='font-size:2.2rem;'>☀️</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_txt:
        _header_text()


def _header_text() -> None:
    now = now_cairo()
    st.markdown(
        f"""
<div>
  <div style='font-size:.58rem;color:#3a7d1e;letter-spacing:3px;text-transform:uppercase;
              margin-bottom:4px;font-weight:600;'>Solar Tracking &amp; IoT System</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:2rem;
              color:#2d6a2d;letter-spacing:4px;'>MENAWAR</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:.82rem;font-weight:700;
              color:#3a7d1e;letter-spacing:2px;text-transform:uppercase;margin-top:2px;'>
    PV Diagnostic Intelligence</div>
  <div style='font-size:.65rem;color:#8aaa7a;letter-spacing:1.5px;text-transform:uppercase;margin-top:3px;'>
    AI-Powered Solar Panel Health Monitoring &middot;
    {now.strftime('%A, %d %B %Y &middot; %H:%M')}</div>
</div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────
#  FIX 5 — THINGSPEAK CONNECTION VALIDATOR
# ─────────────────────────────────────────
def validate_thingspeak(channel_id: str, read_key: str) -> tuple[bool, str]:
    if not channel_id or not read_key:
        return False, "missing_credentials"
    url = (
        f"https://api.thingspeak.com/channels/{channel_id}/feeds.json"
        f"?api_key={read_key}&results=1"
    )
    try:
        r = requests.get(url, timeout=7)
        if r.status_code == 200:
            data = r.json()
            ch = data.get("channel", {})
            return (True, ch.get("name", "Connected")) if ch else (False, "empty_channel")
        if r.status_code == 401:
            return False, "invalid_api_key"
        if r.status_code == 404:
            return False, "channel_not_found"
        return False, f"http_{r.status_code}"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────
#  WEATHER FORECAST — Open-Meteo API (free, no key needed)
#  Falls back to deterministic simulation on any network error.
# ─────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_weather_forecast(lat: float = 30.0444, lon: float = 31.2357) -> dict:
    """
    Fetch tomorrow's weather from Open-Meteo for given lat/lon.
    Default coords = Cairo. Returns same dict shape as the old simulate_* helper.
    """
    try:
        tomorrow = (now_cairo() + timedelta(days=1)).strftime("%Y-%m-%d")
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=weathercode,temperature_2m_max,shortwave_radiation_sum"
            f"&timezone=Africa%2FCairo"
            f"&start_date={tomorrow}&end_date={tomorrow}"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        d = r.json().get("daily", {})
        wcode    = int(d.get("weathercode", [0])[0])
        temp_max = float(d.get("temperature_2m_max", [30])[0])
        rad_sum  = float(d.get("shortwave_radiation_sum", [20])[0])  # MJ/m²

        # WMO weather code → human label + radiation efficiency
        if wcode == 0:
            sky = "Clear Sky ☀️";      eff = 0.95
        elif wcode in (1, 2):
            sky = "Partly Cloudy 🌤";   eff = 0.75
        elif wcode == 3:
            sky = "Overcast ☁️";       eff = 0.45
        elif wcode in (45, 48):
            sky = "Foggy / Hazy 🌫";   eff = 0.55
        elif wcode in range(51, 68):
            sky = "Drizzle / Rain 🌧";  eff = 0.35
        elif wcode in range(71, 78):
            sky = "Snow ❄️";            eff = 0.25
        elif wcode in (80, 81, 82):
            sky = "Rain Showers 🌦";    eff = 0.40
        elif wcode in range(95, 100):
            sky = "Thunderstorm ⛈";    eff = 0.20
        else:
            sky = "Partly Cloudy 🌤";   eff = 0.72

        # Refine eff using actual shortwave radiation (clear-sky ≈ 25 MJ/m²/day)
        if rad_sum > 0:
            eff = min(0.97, max(0.10, rad_sum / 25.0))

        return {
            "sky":           sky,
            "atm_temp":      round(temp_max, 1),
            "radiation_eff": round(eff, 3),
            "description":   f"Tomorrow: {sky} · {temp_max:.0f}°C · Solar radiation {int(eff*100)}%",
            "source":        "Open-Meteo (Live)",
        }
    except Exception:
        # Deterministic fallback — same seed as before
        rng = np.random.default_rng(seed=int(now_cairo().strftime("%Y%m%d")))
        conditions = ["Clear Sky ☀️", "Partly Cloudy 🌤", "Overcast ☁️", "Light Haze 🌫"]
        weights    = [0.45, 0.30, 0.15, 0.10]
        idx        = rng.choice(len(conditions), p=weights)
        sky        = conditions[idx]
        eff_map = {
            "Clear Sky ☀️":    0.95,
            "Partly Cloudy 🌤": 0.72,
            "Overcast ☁️":     0.45,
            "Light Haze 🌫":   0.60,
        }
        atm_temp      = round(rng.uniform(22, 38), 1)
        radiation_eff = eff_map[sky]
        return {
            "sky":           sky,
            "atm_temp":      atm_temp,
            "radiation_eff": radiation_eff,
            "description":   f"Tomorrow: {sky} · {atm_temp}°C · Solar radiation {int(radiation_eff*100)}%",
            "source":        "Estimated (offline)",
        }


def simulate_weather_forecast() -> dict:
    """Kept for backward compatibility — now delegates to live API."""
    return fetch_weather_forecast()


# ─────────────────────────────────────────
#  FIX 4 — SEQUENCE TREND ANALYSIS
# ─────────────────────────────────────────
def analyze_sequence_trend(
    hist_df: pd.DataFrame | None,
    ideal_power: float = 20.0,
    window: int = 6,
) -> tuple[bool, float, str]:
    if hist_df is None or hist_df.empty or len(hist_df) < window:
        return False, 1.0, ""
    prod_df = hist_df[hist_df["Power_W"] > 0.5].tail(window * 2)
    if len(prod_df) < window:
        return False, 1.0, ""
    tail   = prod_df["Power_W"].tail(window).values
    diffs  = np.diff(tail)
    neg_count = int(np.sum(diffs < -0.3))
    slope  = float(np.polyfit(range(len(tail)), tail, 1)[0])
    avg_tail = float(np.mean(tail))
    pct_of_ideal  = avg_tail / max(ideal_power, 1.0)
    trend_factor  = float(max(0.5, min(1.0, pct_of_ideal)))
    if neg_count >= (window - 2) and slope < -0.4:
        msg = (
            f"⚠️ Sequence Alert: Continuous generation drop detected over the past "
            f"{window}-reading cycle (slope {slope:+.2f} W/reading, "
            f"avg {avg_tail:.1f} W vs ideal {ideal_power:.0f} W)."
        )
        return True, trend_factor, msg
    return False, 1.0, ""


# ═══════════════════════════════════════════════════════════════════
#  DASHBOARD CLASS
# ═══════════════════════════════════════════════════════════════════
class PVDashboard:

    def __init__(self) -> None:
        self.rf, self.le = load_ml()

    # ── Credentials ──────────────────────
    @property
    def channel_id(self) -> str:
        return st.session_state.get("ts_channel_id", "").strip()

    @property
    def read_api_key(self) -> str:
        return st.session_state.get("ts_read_key", "").strip()

    @property
    def write_api_key(self) -> str:
        return st.session_state.get("ts_write_key", "").strip()

    # ── Data fetch ────────────────────────
    def fetch_live(self) -> tuple:
        if not self.channel_id or not self.read_api_key:
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 20.0, now_cairo().time(), False, False, 0.0
        url = (
            f"https://api.thingspeak.com/channels/{self.channel_id}/feeds.json"
            f"?api_key={self.read_api_key}&results=1"
        )
        try:
            res = requests.get(url, timeout=8)
            res.raise_for_status()
            feeds = res.json().get("feeds", [])
            if not feeds:
                return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 20.0, now_cairo().time(), False, False, 0.0
            f        = feeds[0]
            v_pv     = float(f.get("field1") or 0)
            v_batt   = float(f.get("field2") or 0)
            amp      = float(f.get("field3") or 0)
            pwr      = float(f.get("field4") or 0)
            ideal    = float(f.get("field5") or 20.0)
            uv_ideal = float(f.get("field6") or 0)   # UV_IDEAL
            uv       = float(f.get("field7") or 0)   # UV_ACTUAL
            dust     = float(f.get("field8") or 0)   # DUST RATIO
            lu    = pd.to_datetime(f.get("created_at"))
            if lu.tzinfo is None:
                lu = lu.tz_localize("UTC")
            diff  = abs((pd.Timestamp.utcnow() - lu).total_seconds())
            return v_pv, v_batt, amp, uv, uv_ideal, dust, pwr, ideal, now_cairo().time(), True, diff < 300, diff
        except requests.exceptions.Timeout:
            return 17.5, 12.4, 1.1, 8.0, 9.0, 5.0, 19.25, 20.0, now_cairo().time(), False, False, 0.0
        except Exception:
            return 17.5, 12.4, 1.1, 8.0, 9.0, 5.0, 19.25, 20.0, now_cairo().time(), False, False, 0.0

    def fetch_history(self) -> pd.DataFrame | None:
        if not self.channel_id or not self.read_api_key:
            return None
        now_c = now_cairo()
        su = now_c.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=3)
        eu = su + timedelta(hours=27)
        urls = [
            (
                f"https://api.thingspeak.com/channels/{self.channel_id}/feeds.json"
                f"?api_key={self.read_api_key}"
                f"&start={su.strftime('%Y-%m-%dT%H:%M:%SZ')}"
                f"&end={eu.strftime('%Y-%m-%dT%H:%M:%SZ')}&results=8000"
            ),
            (
                f"https://api.thingspeak.com/channels/{self.channel_id}/feeds.json"
                f"?api_key={self.read_api_key}&results=800"
            ),
        ]

        def _parse(feeds: list) -> pd.DataFrame | None:
            rows = []
            for f in feeds:
                ts = pd.to_datetime(f.get("created_at"))
                if ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                tc  = ts.tz_convert("Africa/Cairo")
                ch  = 6 <= tc.hour < 20
                soc = voltage_to_soc(float(f.get("field2") or 0), charging=ch)
                vpv = float(f.get("field1") or 0)
                amp = float(f.get("field3") or 0)
                pwr = float(f.get("field4") or 0) or vpv * amp
                rows.append({
                    "time": tc, "V_PV": vpv,
                    "V_Batt": float(f.get("field2") or 0),
                    "Amp": amp, "Power_W": pwr,
                    "Ideal_Power_W": float(f.get("field5") or 20.0),
                    "UV_Ideal": float(f.get("field6") or 0),
                    "UV": float(f.get("field7") or 0),
                    "Dust": float(f.get("field8") or 0),
                    "SOC": soc,
                })
            if not rows:
                return None
            df = pd.DataFrame(rows).sort_values("time").reset_index(drop=True)
            td = now_c.strftime("%Y-%m-%d")
            df = df[df["time"].dt.strftime("%Y-%m-%d") == td]
            return df if not df.empty else None

        for url in urls:
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                feeds = r.json().get("feeds", [])
                if feeds:
                    df = _parse(feeds)
                    if df is not None:
                        return df
            except Exception:
                pass
        return None

    # ── Classification ─────────────────────
    def classify(self, df: pd.DataFrame) -> pd.DataFrame:
        out = []
        for _, row in df.iterrows():
            v, a, uv, uv_id, dust, soc = (
                row["V_PV"], row["Amp"], row["UV"],
                row.get("UV_Ideal", row["UV"]), row["Dust"], row["SOC"]
            )
            vd = v - row["V_Batt"]
            night = is_night_time(row["time"])
            if night:
                # Night: check Soiling + battery health only
                if dust > 60:
                    s = "Soiling Detected"
                elif soc <= 30:
                    s = "Critical Battery"
                elif soc <= 40:
                    s = "Night — Low Battery"
                else:
                    s = "Night — Normal"
            else:
                # Production: all fault types
                is_dl = uv_id > 3.0
                if v < 2.0 and is_dl:
                    s = "Disconnected"
                elif v < 5.5 and a < 0.15 and is_dl:
                    s = "Short Circuit"
                elif v > 22.0 or a < -0.1:
                    s = "Sensor Fault"
                # Shading split: industrial (permanent) vs cloud (temporary)
                elif uv < 1.0 and uv_id > 3.0:
                    s = "Industrial Shading"
                elif uv < (uv_id * 0.55) and uv_id > 2.0:
                    s = "Cloud Shading"
                elif dust > 60:
                    s = "Soiling Detected"
                elif soc >= 100:
                    s = "Battery Full"
                # Early ramp-up: V_PV close to V_Batt, current near zero
                elif vd < 1.5 and a < 0.2 and is_dl and soc < 100:
                    s = "Normal — Ramp Up"
                else:
                    s = "Normal"
            out.append(s)
        df = df.copy()
        df["Status"] = out
        return df

    # ── Telemetry processing ───────────────
    def process_telemetry(
        self,
        v_pv: float, v_batt: float, amp: float,
        uv: float, uv_ideal: float, dust: float, t,
        pwr: float | None = None,
        ideal: float = 20.0,
    ) -> tuple[pd.DataFrame, float, float, int]:
        h = t.hour; m = t.minute; tf = h + m / 60.0
        if pwr is None or pwr == 0:
            pwr = v_pv * amp
        ch  = (6 <= h < 20) and v_pv > 10.0
        soc = voltage_to_soc(v_batt, charging=ch)
        vd  = v_pv - v_batt
        dr  = dust / 100.0 if dust > 1.0 else dust
        ts  = np.sin(2 * np.pi * tf / 24.0)
        tc2 = np.cos(2 * np.pi * tf / 24.0)
        ip  = 1 if 7 <= h <= 17 else 0
        uvd = uv_ideal - uv          # UV_IDEAL (field6) - UV_ACTUAL (field7)
        v2u = v_pv / (uv + 0.5)
        sun = uv * ip
        ideal = ideal if ideal and ideal > 0 else 20.0
        data = {
            "V_PV": [v_pv], "V_Batt": [v_batt], "Amp": [amp], "Power_W": [pwr],
            "Ideal_Power_W": [ideal], "V_Diff": [vd], "SOC_Percentage": [soc],
            "Dust_Ratio": [dr], "time_sin": [ts], "time_cos": [tc2],
            "V_to_UV_Ratio": [v2u], "Sun_Intensity_Index": [sun],
            "is_production_time": [ip], "UV_Deviation": [uvd],
        }
        return pd.DataFrame(data), pwr, soc, ip

    # ── Rule override ──────────────────────
    def rule_override(
        self, v_pv, v_batt, amp, uv, uv_ideal, dust, soc, vd,
        is_night, connected, mode, status,
    ) -> tuple:

        # ══════════════════════════════════════
        #  NIGHT MODE  (after 7:30 PM — before 6 AM)
        # ══════════════════════════════════════
        if is_night:
            # Soiling can be detected at night — dust doesn't go away
            if dust > 60:
                return (
                    "Soiling Detected", "warn", st.warning,
                    f"⚠️ **Soiling Detected** — Dust ratio {dust:.0f}% (above 60% threshold). "
                    "Cleaning recommended before sunrise.", None,
                )
            # Critical battery — disconnect load immediately
            if soc <= 30.0:
                fd = (
                    "🔴 <b>Critical Battery</b> — Disconnect the greenhouse load immediately "
                    "to protect the battery from deep discharge."
                )
                return (
                    "Critical Battery", "crit", st.error,
                    f"🛑 **CRITICAL — Battery at {soc:.1f}%** — "
                    "Disconnect greenhouse load from battery NOW!", fd,
                )
            # Low battery — early warning
            if soc <= 40.0:
                return (
                    "Night — Battery Low", "warn", st.warning,
                    f"⚠️ **Night — Battery Low ({soc:.1f}%)** — "
                    "Approaching critical 30% threshold. Monitor load carefully.", None,
                )
            return (
                "Night — Normal", "ok", st.info,
                f"🌙 Night — Normal operation · SOC {soc:.1f}% · {v_batt:.2f} V", None,
            )

        # ══════════════════════════════════════
        #  PRODUCTION MODE  (6 AM — 7:30 PM)
        # ══════════════════════════════════════
        if not connected and mode == "📡 Live ThingSpeak":
            return status, "warn", st.warning, f"⚠️ Stale data — Last known status: **{status}**", None

        # Battery fully charged — ready to feed greenhouse at night
        if soc >= 100.0:
            return (
                "Battery Full", "ok", st.success,
                "✅ **Battery Fully Charged (100%)** — "
                "Solar panel is now producing excess power. "
                "You can redirect the load to another circuit or divert energy.", None,
            )

        # UV_IDEAL confirms daylight — not affected by actual shading
        is_daylight = uv_ideal > 3.0

        # ── Early-production low-current window ──
        # First ~30 min of production: V_PV ≈ V_Batt so current ≈ 0 — this is NORMAL
        is_early_production = (
            is_daylight
            and vd < 1.5          # PV voltage still close to battery voltage
            and amp < 0.2
            and soc < 100.0
        )
        if is_early_production:
            return (
                "Normal — Ramp Up", "ok", st.info,
                f"🌅 **Normal — Ramp-Up Phase** — "
                f"PV voltage ({v_pv:.1f} V) is approaching battery voltage ({v_batt:.1f} V). "
                "Current is near zero — this is expected at the start of production.", None,
            )

        if v_pv < 5.5 and amp < 0.15 and is_daylight:
            fd = "🔴 <b>Short Circuit</b> — PV voltage collapsed. Disconnect panel and inspect all wiring and fuses."
            return "Short Circuit", "crit", st.error, "🚨 **Short Circuit** detected — PV output near zero.", fd

        if v_pv < 2.0 and is_daylight:
            fd = "🔴 <b>Disconnection</b> — PV near-zero voltage in daylight. Check MC4 connectors and DC breaker."
            return "Disconnected", "crit", st.error, "🔌 **Disconnected** — Panel is not feeding the system.", fd

        if v_pv > 22.0 or amp < -0.1:
            fd = "🟡 <b>Sensor Fault</b> — Readings are out of expected range. Verify sensor wiring and calibration."
            return "Sensor Fault", "warn", st.warning, "⚙️ **Sensor Fault** — Electrical readings out of range.", fd

        # ── Shading detection — split Industrial vs Cloud ──
        if uv < 1.0 and uv_ideal > 3.0:
            # Very low UV_ACTUAL vs high UV_IDEAL → permanent obstruction (industrial shading)
            fd = (
                "🔴 <b>Industrial / Permanent Shading</b> — UV_Actual is near-zero while UV_Ideal is high. "
                "A fixed obstruction (building, tree, structure) is likely blocking the panel. "
                "Inspect panel surroundings and reposition if possible."
            )
            return (
                "Industrial Shading", "crit", st.error,
                "🚨 **Industrial Shading** — Panel blocked by a permanent obstruction.", fd,
            )
        if 1.0 <= uv < (uv_ideal * 0.55) and uv_ideal > 2.0:
            # Partial UV reduction → cloud / haze shading (temporary)
            fd = (
                "🟡 <b>Cloud / Haze Shading</b> — UV_Actual is significantly below UV_Ideal. "
                "Passing clouds or atmospheric haze are reducing irradiance. "
                "This is temporary — no physical action required."
            )
            return (
                "Cloud Shading", "warn", st.warning,
                f"⛅ **Cloud Shading** — UV {uv:.1f} vs Ideal {uv_ideal:.1f}. "
                "Temporary irradiance reduction due to clouds or haze.", fd,
            )

        # ── Soiling — dust ratio above 60 % ──
        if dust > 60:
            return (
                "Soiling Detected", "warn", st.warning,
                f"⚠️ **Soiling Detected** — Dust ratio {dust:.0f}% (above 60% threshold). "
                "Panel cleaning is recommended to restore output.", None,
            )

        if "Normal" in status:
            return status, "ok", st.success, f"✅ **{status}** — System operating optimally.", None

        return status, "crit", st.error, f"⚠️ **{status}**", None

    # ── TalkBack Command ──────────────────
    def send_talkback_command(self, command: str) -> tuple[bool, str]:
        app_id = st.session_state.get("ts_talkback_app_id", "").strip()
        tb_key = st.session_state.get("ts_talkback_key", "").strip()
        if not app_id or not tb_key:
            return False, "missing_credentials"
        url = f"https://api.thingspeak.com/talkbacks/{app_id}/commands.json"
        try:
            r = requests.post(url, data={"api_key": tb_key, "command_string": command}, timeout=8)
            if r.status_code == 201:
                return True, command
            return False, f"http_{r.status_code}"
        except requests.exceptions.Timeout:
            return False, "timeout"
        except Exception as e:
            return False, str(e)

    # ─────────────────────────────────────
    #  SHARED SOC GAUGE
    # ─────────────────────────────────────
    def _soc_gauge(self, soc: float, key: str = "gauge") -> None:
        sc = soc_color(soc)
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=soc,
            number={"suffix": "%", "font": {"size": 22, "family": "Space Grotesk", "color": sc}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": FONT_COLOR, "tickfont": {"color": FONT_COLOR, "size": 9}},
                "bar": {"color": sc, "thickness": 0.28},
                "bgcolor": "rgba(0,0,0,0)", "bordercolor": GRID_COLOR,
                "steps": [
                    {"range": [0, 30],  "color": "rgba(220,38,38,0.07)"},
                    {"range": [30, 80], "color": "rgba(212,160,48,0.06)"},
                    {"range": [80, 100],"color": "rgba(45,138,62,0.07)"},
                ],
                "threshold": {"line": {"color": "#dc2626", "width": 2}, "thickness": 0.75, "value": 30},
            },
        ))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10, r=10, t=20, b=10), height=145)
        st.plotly_chart(fig, use_container_width=True, key=key)

    # ═══════════════════════════════════════
    #  FIX 1 — STRICTLY ISOLATED PANELS
    #  Each panel uses its own st.container()
    #  and renders nothing outside it.
    # ═══════════════════════════════════════

    # ─────────────────────────────────────
    #  PANEL: HOME
    # ─────────────────────────────────────
    def panel_home(
        self, v_pv, v_batt, amp, pwr_out, soc, uv, dust,
        is_night, is_prod, final_status, css_class,
        diff_sec, connected, mode, confidence, alert_fn, alert_text,
        features_df, fault_detail, hist_df,
    ) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>🏠</span>"
                "<span class='mn-section-title'>Home — Complete System Dashboard</span></div>",
                unsafe_allow_html=True,
            )
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("⚡ Power Output",  f"{pwr_out:.1f} W", "Ideal: 20W")
            c2.metric("🔋 Battery SOC",   f"{soc:.1f}%",      f"{v_batt:.2f} V")
            c3.metric("🔌 Current",        f"{amp:.2f} A",     "Live")
            c4.metric("☀️ PV Voltage",    f"{v_pv:.1f} V",    "Panel")
            c5.metric("🌫 Dust Level",     f"{dust:.0f}%",     "Soiling")
            c6.metric("🌞 UV Index",       f"{uv:.1f}",        "Irradiance")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            col_status, col_gauge = st.columns([3, 1])
            with col_status:
                conf_pct = int(confidence * 100)
                sc = {"ok": "#2d8a3e", "warn": "#d4a030", "crit": "#dc2626"}.get(css_class, "#64748b")
                st.markdown(
                    f"""<div class='mn-card'>
  <div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>
    AI Fault Diagnosis — Confidence {conf_pct}%</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:1.7rem;font-weight:700;
              color:{sc};margin-bottom:12px;letter-spacing:1px;'>{final_status}</div>
  <div style='display:flex;align-items:center;gap:10px;'>
    <div style='flex:1;background:rgba(58,125,30,.08);border-radius:6px;height:7px;overflow:hidden;'>
      <div style='height:100%;width:{conf_pct}%;background:linear-gradient(90deg,#3a7d1e,#d4a030);border-radius:6px;'></div>
    </div>
    <span style='font-size:.78rem;color:#3a7d1e;font-weight:700;'>{conf_pct}%</span>
  </div>
</div>""",
                    unsafe_allow_html=True,
                )
                alert_fn(alert_text)
                if not connected and mode == "📡 Live ThingSpeak" and diff_sec > 300:
                    st.error(f"🔌 CONNECTION LOST — No data for {fmt_seconds(diff_sec)}")
            with col_gauge:
                self._soc_gauge(soc, key="gauge_home")

            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                self._battery_compact(soc, v_batt, is_prod, is_night, mode, hist_df)
            with col_b:
                self._prediction_compact(v_pv, v_batt, amp, uv, dust, soc, features_df, final_status)
            st.markdown("</div>", unsafe_allow_html=True)

    def _battery_compact(self, soc, v_batt, is_prod, is_night, mode, hist_df) -> None:
        st.markdown(
            "<div class='mn-section'><span style='font-size:1rem'>🔋</span>"
            "<span class='mn-section-title'>Battery SOC</span></div>",
            unsafe_allow_html=True,
        )
        if hist_df is not None and not hist_df.empty:
            times = hist_df["time"].dt.strftime("%H:%M").tolist()
            socs  = hist_df["SOC"].tolist()
            vbats = hist_df["V_Batt"].tolist()
        else:
            hours = [i * 0.5 for i in range(49)]
            base  = max(30, soc - 60)
            socs  = [round(min(100, base + (soc - base) * (1 - np.exp(-3 * (h) / 24))), 1) for h in hours]
            vbats = [round(11.0 + (s / 100) * 3.5, 2) for s in socs]
            times = [f"{int(h):02d}:{int((h % 1) * 60):02d}" for h in hours]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times, y=socs, mode="lines", name="SOC %",
            line=dict(color="#3a7d1e", width=2.5),
            fill="tozeroy", fillcolor="rgba(58,125,30,0.07)",
            hovertemplate="<b>%{x}</b><br>SOC: %{y:.1f}%<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=times, y=vbats, mode="lines", name="V_Batt (V)",
            line=dict(color="#d4a030", width=1.8, dash="dot"), yaxis="y2",
            hovertemplate="<b>%{x}</b><br>V: %{y:.2f} V<extra></extra>",
        ))
        fig.add_hline(y=30, line=dict(color="#dc2626", width=1, dash="dash"))
        fig.update_layout(**light_layout(
            height=230,
            yaxis=dict(title="SOC (%)", range=[0, 105], gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR)),
            yaxis2=dict(
                title="Voltage (V)", overlaying="y", side="right", range=[10.5, 16],
                gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#d4a030"),
            ),
            legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=9, color=FONT_COLOR)),
            margin=dict(l=12, r=12, t=30, b=28),
        ))
        st.plotly_chart(fig, use_container_width=True, key="batt_home")
        if soc >= 100:
            st.success("✅ Battery Fully Charged — Excess power available for redirection.")
        elif soc <= 30 and is_night:
            st.error(f"🛑 CRITICAL — Battery {soc:.1f}% — Disconnect load now!")
        elif is_night:
            st.info(f"🌙 Night discharge — SOC {soc:.1f}% · {v_batt:.2f} V")

    def _prediction_compact(self, v_pv, v_batt, amp, uv, dust, soc, features_df, final_status) -> None:
        st.markdown(
            "<div class='mn-section'><span style='font-size:1rem'>🔭</span>"
            "<span class='mn-section-title'>Predictive Health</span></div>",
            unsafe_allow_html=True,
        )
        risks = []; score = 0
        if dust > 60:
            risks.append(("🌫 Severe Soiling",  f"Dust {dust:.0f}%", "crit")); score += 30
        elif dust > 30:
            risks.append(("🌫 Moderate Soiling", f"Dust {dust:.0f}%", "warn")); score += 15
        if 30 < soc < 40:
            risks.append(("🔋 Battery Risk", f"SOC {soc:.1f}%", "warn")); score += 25
        if amp < 0.1 and uv > 4.0:
            risks.append(("🔌 Low Current", f"UV={uv:.1f} I={amp:.2f}A", "warn")); score += 30
        if "Short" in final_status or "Disconnected" in final_status:
            score = 100
        score = min(score, 100)
        rl, rc = (
            ("✅ All Nominal", "#2d8a3e") if score == 0
            else ("🟡 Low Risk", "#d4a030") if score < 30
            else ("🟠 Moderate Risk", "#c47a1e") if score < 70
            else ("🔴 High Risk", "#dc2626")
        )
        st.markdown(
            f"""<div class='mn-card' style='padding:18px 20px;'>
  <div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>Overall Risk Score</div>
  <div style='display:flex;align-items:center;gap:12px;margin-bottom:10px;'>
    <div style='width:14px;height:14px;background:{rc};border-radius:50%;box-shadow:0 0 8px {rc}60;'></div>
    <div style='font-family:"Space Grotesk",sans-serif;font-size:1.1rem;font-weight:700;color:{rc};'>{rl}</div>
  </div>
  <div style='background:rgba(58,125,30,.08);border-radius:4px;height:6px;overflow:hidden;'>
    <div style='height:100%;width:{score}%;background:linear-gradient(90deg,#3a7d1e,{rc});border-radius:4px;'></div>
  </div>
</div>""",
            unsafe_allow_html=True,
        )
        for title, detail, level in risks[:3]:
            (st.error if level == "crit" else st.warning)(f"**{title}** — {detail}")
        if not risks:
            st.success("🔭 System expected to remain healthy.")
        now = now_cairo()
        next_h = [(now + timedelta(hours=i)).strftime("%H:%M") for i in range(1, 4)]
        soc_p = [soc]; pwr_p = []
        for i in range(3):
            hn = (now + timedelta(hours=i + 1)).hour
            inp = 6 <= hn < 20
            soc_p.append(min(100, max(0, soc_p[-1] + (2.0 if inp else -1.5))))
            df2 = 1 - dust / 100 * 0.4
            pwr_p.append(round(v_pv * amp * df2 if inp else 0, 1))
        cols = st.columns(3)
        for i, (hr, pw, sv) in enumerate(zip(next_h, pwr_p, soc_p[1:])):
            hv = int(hr.split(":")[0])
            inp = 6 <= hv < 20
            icon = "☀️" if inp else "🌙"
            sc2 = soc_color(sv)
            with cols[i]:
                st.markdown(
                    f"""<div class='hour-card'>
  <div style='font-size:1.1rem;'>{icon}</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:.68rem;color:#3a7d1e;margin:4px 0 2px 0;font-weight:600;'>{hr}</div>
  <div style='font-size:.72rem;color:#4a6741;'>{pw}W</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:.78rem;color:{sc2};font-weight:700;'>{sv:.0f}%</div>
</div>""",
                    unsafe_allow_html=True,
                )

    # ─────────────────────────────────────
    #  PANEL: OVERVIEW
    # ─────────────────────────────────────
    def panel_overview(
        self, v_pv, v_batt, amp, pwr_out, soc, uv, dust,
        is_night, is_prod, final_status, css_class,
        diff_sec, connected, mode, confidence, alert_fn, alert_text,
    ) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>⚡</span>"
                "<span class='mn-section-title'>Live System Overview</span></div>",
                unsafe_allow_html=True,
            )
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("⚡ Power Output",  f"{pwr_out:.1f} W", "Ideal: 20W")
            c2.metric("🔋 Battery SOC",   f"{soc:.1f}%",      f"{v_batt:.2f} V")
            c3.metric("🔌 Current",        f"{amp:.2f} A",     "Live")
            c4.metric("☀️ PV Voltage",    f"{v_pv:.1f} V",    "Panel")
            c5.metric("🌫 Dust Level",     f"{dust:.0f}%",     "Soiling")
            c6.metric("🌞 UV Index",       f"{uv:.1f}",        "Irradiance")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            col_status, col_gauge = st.columns([3, 1])
            with col_status:
                conf_pct = int(confidence * 100)
                sc = {"ok": "#2d8a3e", "warn": "#d4a030", "crit": "#dc2626"}.get(css_class, "#64748b")
                st.markdown(
                    f"""<div class='mn-card'>
  <div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;'>
    AI Fault Diagnosis — Confidence {conf_pct}%</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:1.7rem;font-weight:700;color:{sc};margin-bottom:12px;'>
    {final_status}</div>
  <div style='display:flex;align-items:center;gap:10px;'>
    <div style='flex:1;background:rgba(58,125,30,.08);border-radius:6px;height:7px;overflow:hidden;'>
      <div style='height:100%;width:{conf_pct}%;background:linear-gradient(90deg,#3a7d1e,#d4a030);border-radius:6px;'></div>
    </div>
    <span style='font-size:.78rem;color:#3a7d1e;font-weight:700;'>{conf_pct}%</span>
  </div>
</div>""",
                    unsafe_allow_html=True,
                )
                alert_fn(alert_text)
                if not connected and mode == "📡 Live ThingSpeak" and diff_sec > 300:
                    st.error(f"🔌 CONNECTION LOST — No data for {fmt_seconds(diff_sec)}")
            with col_gauge:
                self._soc_gauge(soc, key="gauge_overview")
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: AI DIAGNOSIS
    # ─────────────────────────────────────
    def panel_diagnosis(
        self, v_pv, v_batt, amp, uv, dust, soc, features_df,
        final_status, css_class, alert_fn, alert_text, fault_detail, confidence,
    ) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>🤖</span>"
                "<span class='mn-section-title'>AI Fault Diagnosis Engine</span></div>",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([2, 1])
            with c1:
                conf_pct = int(confidence * 100)
                sc = {"ok": "#2d8a3e", "warn": "#d4a030", "crit": "#dc2626"}.get(css_class, "#64748b")
                st.markdown(
                    f"""<div class='mn-card'>
  <div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>Detected Fault Status</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:1.8rem;font-weight:700;color:{sc};margin-bottom:16px;'>{final_status}</div>
  <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>
    <span style='font-size:.78rem;color:#4a6741;'>Model Confidence</span>
    <span style='font-family:"Space Grotesk",sans-serif;font-weight:700;color:#3a7d1e;font-size:1rem;'>{conf_pct}%</span>
  </div>
  <div style='background:rgba(58,125,30,.08);border-radius:4px;height:8px;overflow:hidden;'>
    <div style='height:100%;width:{conf_pct}%;background:linear-gradient(90deg,#3a7d1e,#d4a030);border-radius:4px;'></div>
  </div>
  <div style='margin-top:10px;font-size:.65rem;color:#8aaa7a;'>
    Random Forest · 14 Features · {len(self.le.classes_)} Classes</div>
</div>""",
                    unsafe_allow_html=True,
                )
                alert_fn(alert_text)
                if fault_detail:
                    st.markdown(
                        f"""<div style='background:rgba(220,38,38,.05);border:1px solid rgba(220,38,38,.2);
  border-radius:12px;padding:14px 18px;font-size:.82rem;color:#dc2626;line-height:1.8;margin-top:8px;'>
  {fault_detail}</div>""",
                        unsafe_allow_html=True,
                    )
            with c2:
                st.markdown(
                    "<div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;"
                    "text-transform:uppercase;margin-bottom:12px;'>Feature Snapshot</div>",
                    unsafe_allow_html=True,
                )
                feats = {
                    "V_PV":      f"{v_pv:.2f} V",
                    "V_Batt":    f"{v_batt:.2f} V",
                    "V_Diff":    f"{v_pv - v_batt:.2f} V",
                    "SOC":       f"{soc:.1f}%",
                    "Dust":      f"{dust:.0f}%",
                    "UV Index":  f"{uv:.1f}",
                    "Sun Index": f"{features_df['Sun_Intensity_Index'].values[0]:.1f}",
                }
                for k, v in feats.items():
                    st.markdown(
                        f"""<div style='display:flex;justify-content:space-between;padding:8px 0;
  border-bottom:1px solid rgba(58,125,30,.12);'>
  <span style='font-size:.78rem;color:#3a7d1e;font-weight:600;'>{k}</span>
  <span style='font-family:"Space Grotesk",sans-serif;font-weight:700;color:#1a2e12;font-size:.84rem;'>{v}</span>
</div>""",
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: DAY REPORT
    # ─────────────────────────────────────
    def panel_day_report(self, hist_df: pd.DataFrame | None) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>📅</span>"
                "<span class='mn-section-title'>Day Report — Today's Full History</span></div>",
                unsafe_allow_html=True,
            )
            if hist_df is None or hist_df.empty:
                st.info("📡 Day report is available in Live ThingSpeak mode only. Please connect your channel.")
                st.markdown("</div>", unsafe_allow_html=True)
                return

            hist_df = self.classify(hist_df)
            tab1, tab2, tab3 = st.tabs([
                "📊  Power & SOC Timeline",
                "🕐  Hourly Status Summary",
                "📉  Loss Breakdown",
            ])
            x_range = ["06:00", "20:00"]

            with tab1:
                times = hist_df["time"].dt.strftime("%H:%M").tolist()
                hist_df["fault"] = ~hist_df["Status"].str.contains("Normal|Night", na=False)
                statuses = hist_df["Status"].unique()
                fig_gantt = go.Figure()
                for sv in statuses:
                    sub = hist_df[hist_df["Status"] == sv]
                    fig_gantt.add_trace(go.Scatter(
                        x=sub["time"].dt.strftime("%H:%M"), y=[1] * len(sub),
                        mode="markers",
                        marker=dict(color=fault_color(sv), size=16, symbol="square",
                                    line=dict(color="rgba(0,0,0,0)", width=0)),
                        name=sv, hovertemplate=f"<b>%{{x}}</b><br>{sv}<extra></extra>",
                    ))
                fig_gantt.update_layout(**light_layout(
                    height=100,
                    yaxis=dict(visible=False),
                    xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(size=9, color=FONT_COLOR), range=x_range),
                    legend=dict(orientation="h", y=1.7, x=0, font=dict(size=9, color=FONT_COLOR), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified",
                ))
                st.plotly_chart(fig_gantt, use_container_width=True, key="gantt")

                fig = make_subplots(
                    rows=3, cols=1, shared_xaxes=True,
                    row_heights=[0.45, 0.3, 0.25], vertical_spacing=0.04,
                    subplot_titles=("Output Power (W)", "Battery SOC (%)", "PV Voltage (V)"),
                )
                shapes = []
                in_f = False; fs = None
                for _, row in hist_df.iterrows():
                    t_str = row["time"].strftime("%H:%M")
                    if row["fault"] and not in_f:
                        in_f = True; fs = t_str
                    elif not row["fault"] and in_f:
                        in_f = False
                        shapes.append(dict(
                            type="rect", xref="x", yref="paper",
                            x0=fs, x1=t_str, y0=0, y1=1,
                            fillcolor="rgba(220,38,38,0.04)", line_width=0, layer="below",
                        ))
                fig.add_trace(go.Scatter(
                    x=times, y=hist_df["Power_W"], mode="lines", name="Output Power",
                    line=dict(color="#3a7d1e", width=2),
                    fill="tozeroy", fillcolor="rgba(58,125,30,0.07)",
                    hovertemplate="<b>%{x}</b><br>Power: %{y:.1f} W<extra></extra>",
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=times, y=hist_df["Ideal_Power_W"], mode="lines", name="Ideal Power",
                    line=dict(color="#d4a030", width=1.2, dash="dash"),
                    hovertemplate="<b>%{x}</b><br>Ideal: %{y:.1f} W<extra></extra>",
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=times, y=hist_df["SOC"], mode="lines", name="SOC %",
                    line=dict(color="#c47a1e", width=2),
                    fill="tozeroy", fillcolor="rgba(196,122,30,0.07)",
                    hovertemplate="<b>%{x}</b><br>SOC: %{y:.1f}%<extra></extra>",
                ), row=2, col=1)
                fig.add_hline(y=30, line=dict(color="#dc2626", width=1, dash="dash"), row=2, col=1)
                fig.add_trace(go.Scatter(
                    x=times, y=hist_df["V_PV"], mode="lines", name="V_PV",
                    line=dict(color="#5aad2e", width=1.5),
                    hovertemplate="<b>%{x}</b><br>V_PV: %{y:.2f} V<extra></extra>",
                ), row=3, col=1)
                fig.update_layout(**light_layout(
                    shapes=shapes, height=500,
                    legend=dict(orientation="h", y=1.03, x=0, font=dict(size=9, color=FONT_COLOR), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=12, r=12, t=50, b=20), hovermode="x unified",
                ))
                for i in range(1, 4):
                    fig.update_xaxes(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR), range=x_range, row=i, col=1)
                    fig.update_yaxes(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR), row=i, col=1)
                for ann in fig.layout.annotations:
                    ann.font.color = FONT_COLOR
                st.plotly_chart(fig, use_container_width=True, key="timeline_chart")

            with tab2:
                hist_df["hour"] = hist_df["time"].dt.hour
                hourly = hist_df.groupby("hour").agg(
                    Status=("Status", lambda x: x.mode()[0]),
                    Avg_Power=("Power_W", "mean"),
                    Avg_SOC=("SOC", "mean"),
                ).reset_index()
                st.markdown(
                    """<div style='display:flex;align-items:center;gap:10px;padding:10px 14px;
  margin-bottom:6px;border-radius:10px;background:#f8faf6;border:1px solid rgba(58,125,30,.12);'>
  <div style='min-width:72px;font-size:.62rem;color:#3a7d1e;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>HOUR</div>
  <div style='flex:1;font-size:.62rem;color:#3a7d1e;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>STATUS</div>
  <div style='min-width:80px;font-size:.62rem;color:#3a7d1e;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>AVG POWER</div>
  <div style='min-width:70px;font-size:.62rem;color:#3a7d1e;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>AVG SOC</div>
  <div style='min-width:80px;font-size:.62rem;color:#3a7d1e;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>PERIOD</div>
  <div style='min-width:90px;font-size:.62rem;color:#dc2626;letter-spacing:1px;text-transform:uppercase;font-weight:700;text-align:right;'>POWER LOSS</div>
</div>""",
                    unsafe_allow_html=True,
                )
                for _, row in hourly.iterrows():
                    h = int(row["hour"]); s = row["Status"]
                    c = fault_color(s); loss = fault_loss(s)
                    is_night_h = h < 6 or h >= 20
                    period  = "🌙 Night" if is_night_h else "⚡ Production"
                    pwr_txt = f"{row['Avg_Power']:.1f} W" if not is_night_h else "0.0 W"
                    st.markdown(
                        f"""<div class='hr-row'>
  <div style='min-width:72px;font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.84rem;color:#2d6a2d;'>{h:02d}:00</div>
  <div style='flex:1;'><span style='background:{c}15;color:{c};padding:3px 12px;border-radius:6px;
      font-size:.72rem;font-weight:700;border:1px solid {c}40;'>{s}</span></div>
  <div style='min-width:80px;font-size:.78rem;color:#3a7d1e;font-weight:600;'>{pwr_txt}</div>
  <div style='min-width:70px;font-size:.78rem;color:#d4a030;font-weight:700;'>{row['Avg_SOC']:.0f}%</div>
  <div style='min-width:80px;font-size:.72rem;color:#4a6741;'>{period}</div>
  <div style='min-width:90px;text-align:right;font-family:"Space Grotesk",sans-serif;
      font-size:.72rem;color:#dc2626;font-weight:700;'>-{loss}%</div>
</div>""",
                        unsafe_allow_html=True,
                    )

            with tab3:
                sc_df = hist_df.groupby("Status").size().reset_index(name="count")
                sc_df["loss"]   = sc_df["Status"].apply(fault_loss)
                sc_df["color"]  = sc_df["Status"].apply(fault_color)
                tot = sc_df["count"].sum()
                sc_df["time_pct"] = (sc_df["count"] / tot * 100).round(1)
                sc_df["contrib"]  = (sc_df["time_pct"] * sc_df["loss"] / 100).round(2)
                total_loss  = sc_df["contrib"].sum()
                normal_p = sc_df[sc_df["Status"].str.contains("Normal", na=False)]["time_pct"].sum()
                night_p  = sc_df[sc_df["Status"].str.contains("Night", na=False)]["time_pct"].sum()
                fault_p  = 100 - normal_p - night_p
                avg_p    = hist_df["Power_W"].mean()
                ideal_a  = hist_df["Ideal_Power_W"].mean()
                eff      = (avg_p / ideal_a * 100) if ideal_a > 0 else 0

                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("✅ Normal Time",      f"{normal_p:.1f}%", "of production")
                k2.metric("⚠️ Fault Time",       f"{fault_p:.1f}%",  "of production")
                k3.metric("🌙 Night Time",        f"{night_p:.1f}%",  "of day")
                k4.metric("📉 Total Power Lost",  f"{total_loss:.1f}%", "weighted")
                k5.metric("⚡ System Efficiency", f"{eff:.1f}%",       "actual/ideal")

                cp, cb = st.columns(2)
                with cp:
                    fig3 = go.Figure(go.Pie(
                        labels=sc_df["Status"], values=sc_df["time_pct"], hole=0.55,
                        marker=dict(colors=sc_df["color"].tolist(),
                                    line=dict(color="rgba(255,255,255,0.2)", width=2)),
                        textinfo="label+percent",
                        textfont=dict(size=9, family=FONT_FAMILY, color=FONT_COLOR),
                        hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>",
                    ))
                    fig3.update_layout(**light_layout(
                        showlegend=False, height=300,
                        margin=dict(l=10, r=10, t=40, b=10),
                        title=dict(text="⏱ Time Spent per Status (%)", font=dict(size=11, color=FONT_COLOR)),
                    ))
                    st.plotly_chart(fig3, use_container_width=True, key="pie_chart")
                with cb:
                    fo = sc_df[~sc_df["Status"].str.contains("Night", na=False)]
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(
                        name="Time Spent (%)", x=fo["Status"], y=fo["time_pct"],
                        marker_color=fo["color"].tolist(), opacity=0.80,
                        text=[f"{v:.1f}%" for v in fo["time_pct"]], textposition="outside",
                        textfont=dict(size=9, color=FONT_COLOR),
                    ))
                    fig4.add_trace(go.Bar(
                        name="Power Loss (%)", x=fo["Status"], y=fo["contrib"],
                        marker_color="rgba(220,38,38,0.65)",
                        text=[f"{v:.1f}%" for v in fo["contrib"]], textposition="outside",
                        textfont=dict(size=9, color="#991b1b"),
                    ))
                    fig4.update_layout(**light_layout(
                        barmode="group", height=300,
                        margin=dict(l=10, r=10, t=50, b=70),
                        xaxis=dict(tickangle=-25, gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR)),
                        legend=dict(orientation="h", y=1.15, bgcolor="rgba(0,0,0,0)", font=dict(size=9, color=FONT_COLOR)),
                        title=dict(text="📊 Time vs Power Loss per Fault Cause", font=dict(size=11, color=FONT_COLOR)),
                    ))
                    st.plotly_chart(fig4, use_container_width=True, key="bar_chart")

                st.markdown(
                    "<div style='font-size:.65rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;"
                    "margin:16px 0 10px 0;'>🔍 Per-Fault Power Loss Detail</div>",
                    unsafe_allow_html=True,
                )
                for _, row in sc_df.sort_values("contrib", ascending=False).iterrows():
                    c = row["color"]; bar_w = int(min(row["contrib"] * 6, 100))
                    st.markdown(
                        f"""<div class='hr-row'>
  <div style='min-width:180px;'><span style='background:{c}15;color:{c};padding:3px 10px;
      border-radius:6px;font-size:.72rem;font-weight:700;border:1px solid {c}40;'>{row['Status']}</span></div>
  <div style='min-width:90px;font-size:.78rem;color:#4a6741;'>{row['time_pct']:.1f}%</div>
  <div style='min-width:90px;font-size:.78rem;color:#dc2626;font-weight:600;'>{row['loss']:.0f}%</div>
  <div style='flex:1;'><div style='background:rgba(58,125,30,.08);border-radius:4px;height:8px;overflow:hidden;'>
    <div style='height:100%;width:{bar_w}%;background:{c};border-radius:4px;'></div></div></div>
  <div style='min-width:90px;text-align:right;font-family:"Space Grotesk",sans-serif;
      font-size:.75rem;color:{c};font-weight:700;'>{row['contrib']:.2f}%</div>
</div>""",
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f"""<div style='text-align:right;font-family:"Space Grotesk",sans-serif;font-weight:700;
  font-size:1rem;margin-top:14px;padding:12px 16px;background:rgba(220,38,38,.05);
  border:1px solid rgba(220,38,38,.18);border-radius:12px;color:#1a2e12;'>
  TOTAL DAY POWER LOSS — <span style='color:#dc2626;'>{total_loss:.2f}%</span>
</div>""",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: BATTERY
    # ─────────────────────────────────────
    def panel_battery(
        self, soc, v_batt, is_prod, is_night, mode, hist_df,
    ) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>🔋</span>"
                "<span class='mn-section-title'>Battery SOC — Night Discharge Monitor</span></div>",
                unsafe_allow_html=True,
            )
            b1, b2, b3 = st.columns(3)
            b1.metric("🔋 Battery SOC",     f"{soc:.1f}%",     f"{'Charging' if is_prod else 'Discharging'}")
            b2.metric("🔌 Battery Voltage",  f"{v_batt:.2f} V", "Current")
            b3.metric("⚡ Status",            "Night" if is_night else "Day", f"{'🌙' if is_night else '☀️'} Mode")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            if hist_df is not None and not hist_df.empty:
                pf    = hist_df.copy()
                times = pf["time"].dt.strftime("%H:%M").tolist()
                socs  = pf["SOC"].tolist()
                vbats = pf["V_Batt"].tolist()
            else:
                hours = [i * 0.5 for i in range(49)]
                base  = max(30, soc - 60)
                socs  = [round(min(100, base + (soc - base) * (1 - np.exp(-3 * h / 24))), 1) for h in hours]
                vbats = [round(11.0 + (s / 100) * 3.5, 2) for s in socs]
                times = [f"{int(h):02d}:{int((h % 1) * 60):02d}" for h in hours]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=times, y=socs, mode="lines", name="SOC %",
                line=dict(color="#3a7d1e", width=2.5),
                fill="tozeroy", fillcolor="rgba(58,125,30,0.07)",
                hovertemplate="<b>%{x}</b><br>SOC: %{y:.1f}%<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=times, y=vbats, mode="lines", name="V_Batt (V)",
                line=dict(color="#d4a030", width=1.8, dash="dot"), yaxis="y2",
                hovertemplate="<b>%{x}</b><br>V: %{y:.2f} V<extra></extra>",
            ))
            fig.add_hline(
                y=30, line=dict(color="#dc2626", width=1.2, dash="dash"),
                annotation_text="Critical 30%",
                annotation_font=dict(color="#dc2626", size=10),
            )
            fig.add_hline(
                y=100, line=dict(color="#2d8a3e", width=1, dash="dot"),
                annotation_text="Full 100%",
                annotation_font=dict(color="#2d8a3e", size=10),
            )
            fig.update_layout(**light_layout(
                height=320,
                xaxis=dict(gridcolor=GRID_COLOR, title="Time", range=["06:00", "20:00"], tickfont=dict(color=FONT_COLOR)),
                yaxis=dict(title="SOC (%)", range=[0, 105], gridcolor=GRID_COLOR,
                           title_font=dict(color="#3a7d1e"), tickfont=dict(color="#3a7d1e")),
                yaxis2=dict(title="Battery Voltage (V)", overlaying="y", side="right",
                            range=[10.5, 16], gridcolor="rgba(0,0,0,0)",
                            title_font=dict(color="#d4a030"), tickfont=dict(color="#d4a030")),
                legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)", font=dict(color=FONT_COLOR, size=9)),
                margin=dict(l=12, r=12, t=40, b=40),
            ))
            st.plotly_chart(fig, use_container_width=True, key="battery_chart")

            if hist_df is not None and not hist_df.empty and is_night:
                st.markdown(
                    "<div style='font-size:.65rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;"
                    "margin:16px 0 10px 0;'>🔋 Night Discharge Log — Last 30 Readings</div>",
                    unsafe_allow_html=True,
                )
                night_df = hist_df[hist_df["time"].apply(lambda t: t.hour >= 20 or t.hour < 6)].tail(30)
                if not night_df.empty:
                    st.markdown(
                        """<div style='display:flex;padding:8px 14px;background:#f8faf6;
  border:1px solid rgba(58,125,30,.12);border-radius:10px;margin-bottom:4px;'>
  <div style='flex:1;font-size:.62rem;color:#3a7d1e;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>TIME</div>
  <div style='min-width:100px;text-align:center;font-size:.62rem;color:#d4a030;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>V_BATT</div>
  <div style='min-width:100px;text-align:right;font-size:.62rem;color:#3a7d1e;letter-spacing:1px;text-transform:uppercase;font-weight:700;'>SOC</div>
</div>""",
                        unsafe_allow_html=True,
                    )
                    for _, row in night_df.sort_values("time", ascending=False).iterrows():
                        sc2 = soc_color(row["SOC"])
                        st.markdown(
                            f"""<div class='hr-row'>
  <div style='flex:1;font-size:.8rem;color:#1a2e12;'>{row['time'].strftime('%H:%M')}</div>
  <div style='min-width:100px;text-align:center;font-family:"Space Grotesk",sans-serif;
      font-size:.78rem;color:#d4a030;font-weight:700;'>{row['V_Batt']:.1f} V</div>
  <div style='min-width:100px;text-align:right;'>
    <span style='background:{sc2}18;color:{sc2};padding:3px 12px;border-radius:6px;
        font-family:"Space Grotesk",sans-serif;font-size:.75rem;font-weight:700;
        border:1px solid {sc2}40;'>{row['SOC']:.1f}%</span></div>
</div>""",
                            unsafe_allow_html=True,
                        )

            if soc >= 100:
                st.success("✅ Battery Fully Charged (100%) — Solar panel power can be redirected to another load.")
            elif soc <= 30 and is_night:
                st.error(f"🛑 CRITICAL — Battery at {soc:.1f}% during night. Disconnect greenhouse load immediately to protect the battery.")
            elif soc <= 40 and is_night:
                st.warning(f"⚠️ Night — Battery Low ({soc:.1f}%) — Approaching critical 30% threshold. Monitor load.")
            elif is_night:
                st.info(f"🌙 Night discharge in progress — SOC {soc:.1f}% · {v_batt:.2f} V")
            elif is_prod:
                st.info(f"⚡ Charging from solar panel — SOC {soc:.1f}% · {v_batt:.2f} V")
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: PREDICTIVE FORECAST (FIX 4)
    # ─────────────────────────────────────
    def panel_prediction(
        self, v_pv, v_batt, amp, uv, dust, soc,
        features_df, final_status, hist_df,
    ) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>🔭</span>"
                "<span class='mn-section-title'>Predictive Health Forecast — Multi-Factor Analysis</span></div>",
                unsafe_allow_html=True,
            )
            p1, p2, p3 = st.columns(3)
            p1.metric("🌫 Dust Level",  f"{dust:.0f}%",   "Soiling Factor")
            p2.metric("🌞 UV Index",    f"{uv:.1f}",       "Irradiance")
            p3.metric("⚡ PV Voltage",  f"{v_pv:.1f} V",  "Panel Output")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            # Risk scoring
            risks = []; score = 0
            if dust > 60:
                risks.append(("🌫 Severe Soiling",  f"Dust {dust:.0f}% — clean urgently", "crit")); score += 30
            elif dust > 30:
                risks.append(("🌫 Moderate Soiling", f"Dust {dust:.0f}% — clean within 24h", "warn")); score += 15
            if 30 < soc < 40:
                risks.append(("🔋 Battery Risk", f"SOC {soc:.1f}% near critical 30%", "warn")); score += 25
            vr = v_pv / (v_batt + 0.01)
            if vr < 1.02 and v_pv > 5:
                risks.append(("⚡ Charging Efficiency Drop", f"PV-to-Battery ratio low ({vr:.2f}).", "warn")); score += 20
            if amp < 0.1 and uv > 4.0:
                risks.append(("🔌 Low Current", f"UV={uv:.1f} I={amp:.2f}A", "warn")); score += 30
            if "Short" in final_status or "Disconnected" in final_status:
                score = 100
            score = min(score, 100)
            rl, rc, rt = (
                ("✅ All Nominal", "#2d8a3e", "No faults detected. System is healthy.") if score == 0
                else ("🟡 Low Risk", "#d4a030", "Minor conditions present. Monitor but no immediate action needed.") if score < 30
                else ("🟠 Moderate Risk", "#c47a1e", "Elevated risk — monitor closely.") if score < 70
                else ("🔴 High Risk", "#dc2626", "Fault active — act now.")
            )
            st.markdown(
                f"""<div class='mn-card' style='padding:22px 26px;'>
  <div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>OVERALL RISK SCORE</div>
  <div style='display:flex;align-items:center;gap:14px;margin-bottom:14px;'>
    <div style='width:18px;height:18px;background:{rc};border-radius:50%;box-shadow:0 0 12px {rc}80;'></div>
    <div style='font-family:"Space Grotesk",sans-serif;font-size:1.4rem;font-weight:700;color:{rc};'>{rl}</div>
  </div>
  <div style='background:rgba(58,125,30,.08);border-radius:6px;height:8px;overflow:hidden;margin-bottom:10px;'>
    <div style='height:100%;width:{score}%;background:linear-gradient(90deg,#3a7d1e,{rc});border-radius:6px;'></div>
  </div>
  <div style='font-size:.82rem;color:#4a6741;'>{rt}</div>
</div>""",
                unsafe_allow_html=True,
            )
            for title, detail, level in risks:
                (st.error if level == "crit" else st.warning if level == "warn" else st.info)(
                    f"**{title}** — {detail}"
                )
            if not risks:
                st.success("🔭 No risk indicators — system expected to remain healthy.")

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            # 6-hour near-term cards
            now = now_cairo()
            next_h = [(now + timedelta(hours=i)).strftime("%H:%M") for i in range(1, 7)]
            soc_p = [soc]; pwr_p = []
            for i in range(6):
                hn = (now + timedelta(hours=i + 1)).hour
                inp = 6 <= hn < 20
                soc_p.append(min(100, max(0, soc_p[-1] + (2.0 if inp and soc_p[-1] < 100 else -1.5))))
                df2 = 1 - dust / 100 * 0.4
                pwr_p.append(round(v_pv * amp * df2 if inp else 0, 1))
            st.markdown(
                "<div style='font-size:.65rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;"
                "margin-bottom:10px;'>⏱ Next 6 Hours Forecast</div>",
                unsafe_allow_html=True,
            )
            cols = st.columns(6)
            for i, (hr, pw, sv) in enumerate(zip(next_h, pwr_p, soc_p[1:])):
                hv = int(hr.split(":")[0]); inp = 6 <= hv < 20; icon = "☀️" if inp else "🌙"
                sc2 = soc_color(sv)
                with cols[i]:
                    st.markdown(
                        f"""<div class='hour-card'>
  <div style='font-size:1.3rem;'>{icon}</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:.72rem;color:#3a7d1e;margin:6px 0 2px 0;font-weight:600;'>{hr}</div>
  <div style='font-size:.75rem;color:#4a6741;margin-bottom:4px;'>{pw}W</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:.82rem;color:{sc2};font-weight:700;'>{sv:.0f}%</div>
</div>""",
                        unsafe_allow_html=True,
                    )

            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

            # ── FIX 4A: Sequential Trend Analysis ──
            ideal_power_val = float(features_df["Ideal_Power_W"].values[0]) if features_df is not None else 20.0
            seq_alert, trend_factor, seq_msg = analyze_sequence_trend(hist_df, ideal_power=ideal_power_val)
            if seq_alert:
                st.markdown(
                    f"""<div style='background:rgba(212,160,48,.08);border:1.5px solid rgba(212,160,48,.38);
  border-radius:14px;padding:16px 20px;margin-bottom:18px;display:flex;align-items:flex-start;gap:14px;'>
  <div style='font-size:1.5rem;flex-shrink:0;'>⚠️</div>
  <div>
    <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.78rem;
        color:#c47a1e;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;'>Sequential Trend Alert</div>
    <div style='font-size:.82rem;color:#4a6741;line-height:1.7;'>{seq_msg}</div>
  </div>
</div>""",
                    unsafe_allow_html=True,
                )

            # ── FIX 4B: Weather Forecast (Live Open-Meteo API) ──
            st.markdown(
                """<div class='mn-section'><span style='font-size:1rem'>🌤</span>
<span class='mn-section-title'>Tomorrow's Weather Forecast</span></div>""",
                unsafe_allow_html=True,
            )
            weather = fetch_weather_forecast()
            src_badge = (
                "<span style='background:rgba(45,138,62,.1);color:#2d8a3e;padding:2px 10px;"
                "border-radius:6px;font-size:.62rem;font-weight:700;border:1px solid rgba(45,138,62,.25);'>"
                f"📡 {weather.get('source','Live')}</span>"
                if "Live" in weather.get("source","")
                else
                "<span style='background:rgba(212,160,48,.1);color:#c47a1e;padding:2px 10px;"
                "border-radius:6px;font-size:.62rem;font-weight:700;border:1px solid rgba(212,160,48,.25);'>"
                f"📶 {weather.get('source','Estimated')}</span>"
            )
            st.markdown(
                f"<div style='margin-bottom:10px;'>{src_badge}</div>",
                unsafe_allow_html=True,
            )
            wc1, wc2, wc3 = st.columns(3)
            sky_icon = {
                "Clear Sky ☀️": "☀️", "Partly Cloudy 🌤": "🌤",
                "Overcast ☁️": "☁️", "Light Haze 🌫": "🌫",
            }.get(weather["sky"], "🌤")
            rad_color = "#2d8a3e" if weather["radiation_eff"] > 0.8 else "#d4a030" if weather["radiation_eff"] > 0.5 else "#dc2626"
            with wc1:
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:20px;'>
  <div style='font-size:2rem;margin-bottom:6px;'>{sky_icon}</div>
  <div style='font-size:.58rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;'>Sky Conditions</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.88rem;color:#2d6a2d;'>{weather['sky']}</div>
</div>""",
                    unsafe_allow_html=True,
                )
            with wc2:
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:20px;'>
  <div style='font-size:2rem;margin-bottom:6px;'>🌡️</div>
  <div style='font-size:.58rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;'>Atmospheric Temp</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:1.4rem;color:#d4a030;'>{weather['atm_temp']}°C</div>
</div>""",
                    unsafe_allow_html=True,
                )
            with wc3:
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:20px;'>
  <div style='font-size:2rem;margin-bottom:6px;'>☀️</div>
  <div style='font-size:.58rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;'>Solar Radiation Efficiency</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:1.4rem;color:{rad_color};'>{int(weather['radiation_eff']*100)}%</div>
</div>""",
                    unsafe_allow_html=True,
                )

            # ── FIX 4C: Integrated Forecast Chart ──
            st.markdown(
                """<div class='mn-section' style='margin-top:24px;'><span style='font-size:1rem'>📈</span>
<span class='mn-section-title'>Tomorrow's Integrated Power Forecast</span></div>""",
                unsafe_allow_html=True,
            )
            soiling_coeff  = 1.0 - (dust / 100.0 * 0.4)
            weather_factor = weather["radiation_eff"]
            hours_tmr  = list(range(6, 20))
            hour_labels = [f"{h:02d}:00" for h in hours_tmr]
            pwr_clear = []
            pwr_proj  = []
            for h in hours_tmr:
                peak      = 20 * (np.sin(np.pi * (h - 6) / 13) ** 1.5) if 6 <= h < 19 else 0
                peak      = max(0.0, float(peak))
                projected = peak * weather_factor * soiling_coeff * trend_factor
                pwr_clear.append(round(peak, 2))
                pwr_proj.append(round(projected, 2))

            exp_energy   = sum(pwr_clear) / 60
            proj_energy  = sum(pwr_proj)  / 60
            expected_peak = max(pwr_proj)

            fig_fc = make_subplots(specs=[[{"secondary_y": True}]])
            fig_fc.add_trace(go.Scatter(
                x=hour_labels, y=pwr_clear, name="Clear-Sky Limit", mode="lines",
                line=dict(color="rgba(45,138,62,0.65)", width=1.8, dash="dash"),
                fill="tozeroy", fillcolor="rgba(45,138,62,0.05)",
                hovertemplate="<b>%{x}</b><br>Clear-Sky: %{y:.1f} W<extra></extra>",
            ), secondary_y=False)
            fig_fc.add_trace(go.Scatter(
                x=hour_labels, y=pwr_proj, name="Projected (Weather×Soiling×Trend)", mode="lines",
                line=dict(color="#3a7d1e", width=2.5),
                fill="tonexty", fillcolor="rgba(58,125,30,0.10)",
                hovertemplate="<b>%{x}</b><br>Projected: %{y:.1f} W<extra></extra>",
            ), secondary_y=False)
            fig_fc.add_trace(go.Scatter(
                x=hour_labels, y=pwr_proj, name="Gold Band",
                mode="none", fill="tozeroy", fillcolor="rgba(212,160,48,0.06)",
                showlegend=False, hoverinfo="skip",
            ), secondary_y=False)
            peak_idx = int(np.argmax(pwr_proj))
            fig_fc.add_annotation(
                x=hour_labels[peak_idx], y=pwr_proj[peak_idx],
                text=f"Peak: {pwr_proj[peak_idx]:.1f}W",
                showarrow=True, arrowhead=2, arrowsize=1, arrowcolor=FONT_COLOR,
                font=dict(size=9, color=FONT_COLOR, family="Space Grotesk"),
                bgcolor="rgba(212,160,48,0.12)", bordercolor="rgba(212,160,48,0.45)",
                borderwidth=1, borderpad=4, ax=0, ay=-28,
            )
            fig_fc.update_layout(**light_layout(
                height=320,
                title=dict(text=f"📅 Tomorrow's Power Forecast — {weather['sky']}",
                           font=dict(size=11, color=FONT_COLOR, family="Space Grotesk")),
                xaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR), title="Hour of Day"),
                yaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=FONT_COLOR), title="Power (W)", range=[0, 24]),
                legend=dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=9, color=FONT_COLOR)),
                margin=dict(l=12, r=12, t=60, b=40),
            ))
            st.plotly_chart(fig_fc, use_container_width=True, key="forecast_dual_chart")

            e1, e2, e3, e4 = st.columns(4)
            with e1:
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:18px;'>
  <div style='font-size:.58rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'>☀️ CLEAR-SKY ENERGY</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:1.6rem;font-weight:700;color:#2d6a2d;'>{exp_energy:.1f} Wh</div>
  <div style='margin-top:6px;'><span style='background:rgba(45,138,62,.1);color:#2d8a3e;padding:3px 10px;
      border-radius:6px;font-size:.72rem;font-weight:600;'>Theoretical Max</span></div>
</div>""",
                    unsafe_allow_html=True,
                )
            with e2:
                loss_color = "#dc2626" if (exp_energy - proj_energy) > 3 else "#d4a030"
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:18px;'>
  <div style='font-size:.58rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'>📉 PROJECTED ENERGY</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:1.6rem;font-weight:700;color:#2d6a2d;'>{proj_energy:.1f} Wh</div>
  <div style='margin-top:6px;'><span style='background:rgba(220,38,38,.08);color:{loss_color};padding:3px 10px;
      border-radius:6px;font-size:.72rem;font-weight:600;'>↓ -{(exp_energy-proj_energy):.1f} Wh</span></div>
</div>""",
                    unsafe_allow_html=True,
                )
            with e3:
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:18px;'>
  <div style='font-size:.58rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'>⚡ EXPECTED PEAK</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:1.6rem;font-weight:700;color:#3a7d1e;'>{expected_peak:.1f} W</div>
  <div style='margin-top:6px;'><span style='background:rgba(58,125,30,.1);color:#3a7d1e;padding:3px 10px;
      border-radius:6px;font-size:.72rem;font-weight:600;'>Around Noon</span></div>
</div>""",
                    unsafe_allow_html=True,
                )
            with e4:
                eff_pct = int(weather_factor * soiling_coeff * trend_factor * 100)
                a_color = "#2d8a3e" if eff_pct > 80 else "#d4a030" if eff_pct > 55 else "#dc2626"
                action  = "All Good" if eff_pct > 80 else ("Monitor" if eff_pct > 55 else "Clean Now")
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:18px;'>
  <div style='font-size:.58rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:6px;'>⚙️ COMBINED EFFICIENCY</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:1.6rem;font-weight:700;color:{a_color};'>{eff_pct}%</div>
  <div style='margin-top:6px;'><span style='background:{a_color}15;color:{a_color};padding:3px 10px;
      border-radius:6px;font-size:.72rem;font-weight:600;'>{action}</span></div>
</div>""",
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""<div style='margin-top:16px;background:#f8faf6;border:1px solid rgba(58,125,30,.14);
  border-radius:12px;padding:16px 20px;font-size:.78rem;color:#4a6741;line-height:2;'>
  <span style='font-family:"Space Grotesk",sans-serif;font-weight:700;color:#2d6a2d;
      font-size:.72rem;letter-spacing:1px;text-transform:uppercase;'>Forecast Computation</span><br>
  <code style='background:rgba(58,125,30,.08);padding:6px 12px;border-radius:6px;font-size:.8rem;
      color:#3a7d1e;display:inline-block;margin-top:6px;'>
    P_expected = P_clear_sky × Weather({int(weather_factor*100)}%) × Soiling({int(soiling_coeff*100)}%) × Trend({int(trend_factor*100)}%)
    = {expected_peak:.1f} W peak
  </code>
</div>""",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: CLEANING
    # ─────────────────────────────────────
    def panel_cleaning(self, dust_in: float) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>🧹</span>"
                "<span class='mn-section-title'>Panel Cleaning Control</span></div>",
                unsafe_allow_html=True,
            )
            cl1, cl2, cl3 = st.columns(3)
            cl1.metric("🌫 Dust Level",   f"{dust_in:.0f}%",               "Current Soiling")
            cl2.metric("📉 Power Loss",   f"{min(dust_in*0.4,40):.1f}%",  "From Dust")
            cl3.metric("🧹 Clean Status", "Needed" if dust_in > 30 else "OK", "Panel Health")
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            dust_c   = "#2d8a3e" if dust_in < 20 else "#d4a030" if dust_in < 50 else "#dc2626"
            loss_est = min(dust_in * 0.4, 40)
            c1, c2, c3 = st.columns([1, 1, 2])

            with c1:
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:22px 16px;'>
  <div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>Current Dust Level</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:2.6rem;font-weight:700;color:{dust_c};'>{dust_in:.0f}%</div>
  <div style='background:rgba(58,125,30,.08);border-radius:4px;height:10px;overflow:hidden;margin-top:12px;'>
    <div style='height:100%;width:{min(dust_in,100):.0f}%;background:{dust_c};border-radius:4px;'></div>
  </div>
  <div style='font-size:.75rem;color:#4a6741;margin-top:10px;'>{"⚠️ Clean Needed" if dust_in>30 else "✅ Panel Clean"}</div>
</div>""",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"""<div class='mn-card' style='text-align:center;padding:22px 16px;'>
  <div style='font-size:.62rem;color:#4a6741;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;'>Power Loss from Dust</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:2.6rem;font-weight:700;color:#dc2626;'>{loss_est:.1f}%</div>
  <div style='font-size:.75rem;color:#4a6741;margin-top:10px;'>Estimated reduction</div>
</div>""",
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    """<div class='mn-card' style='padding:20px 22px;'>
  <div style='font-size:.75rem;color:#2d6a2d;font-weight:700;margin-bottom:6px;letter-spacing:.5px;'>🌐 ESP32 Cloud Cleaning Control</div>
  <div style='font-size:.72rem;color:#4a6741;margin-bottom:16px;line-height:1.6;'>Commands dispatched via ThingSpeak TalkBack API. Your ESP32 polls the TalkBack queue and executes commands globally from anywhere in the world.</div>""",
                    unsafe_allow_html=True,
                )
                if "cleaning_log" not in st.session_state:
                    st.session_state.cleaning_log = []
                app_id = st.session_state.get("ts_talkback_app_id", "").strip()
                tb_key = st.session_state.get("ts_talkback_key", "").strip()
                if not app_id or not tb_key:
                    st.warning(
                        "⚠️ Enter your **TalkBack App ID** and **TalkBack API Key** in the sidebar "
                        "under **🧹 CLEANING CONTROL** to enable remote cleaning."
                    )
                else:
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("🧹 Trigger Cleaning", use_container_width=True, type="primary"):
                            ok, msg = self.send_talkback_command("CLEAN_ON")
                            if ok:
                                st.success("✅ Cleaning command queued! ESP32 will start shortly.")
                                st.session_state.cleaning_log.append(f"✅ Triggered — {now_cairo().strftime('%H:%M:%S')}")
                            else:
                                err_map = {"timeout": "Request timed out.", "missing_credentials": "Credentials missing."}
                                st.error(f"❌ Failed: {err_map.get(msg, msg)}")
                                st.session_state.cleaning_log.append(f"❌ Error: {msg} — {now_cairo().strftime('%H:%M:%S')}")
                    with b2:
                        if st.button("⏹ Stop Cleaning", use_container_width=True):
                            ok, msg = self.send_talkback_command("CLEAN_OFF")
                            if ok:
                                st.success("⏹ Stop command queued.")
                                st.session_state.cleaning_log.append(f"⏹ Stopped — {now_cairo().strftime('%H:%M:%S')}")
                            else:
                                st.error(f"❌ Failed: {msg}")

                if st.session_state.get("cleaning_log"):
                    st.markdown(
                        "<div style='margin-top:14px;font-size:.62rem;color:#4a6741;letter-spacing:1.5px;"
                        "text-transform:uppercase;margin-bottom:6px;font-weight:600;'>Activity Log</div>",
                        unsafe_allow_html=True,
                    )
                    for log in reversed(st.session_state.cleaning_log[-5:]):
                        st.markdown(
                            f"<div style='font-size:.78rem;color:#2d6a2d;padding:4px 0;"
                            f"border-bottom:1px solid rgba(58,125,30,.12);'>{log}</div>",
                            unsafe_allow_html=True,
                        )
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: ABOUT US
    # ─────────────────────────────────────
    def panel_about_us(self) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>🌟</span>"
                "<span class='mn-section-title'>About Menawar — Solar Tracking &amp; IoT System</span></div>",
                unsafe_allow_html=True,
            )
            # Header card — use real image if available, else badge
            logo_html = ""
            for path in _logo_paths():
                if os.path.exists(path):
                    import base64
                    with open(path, "rb") as f_img:
                        b64 = base64.b64encode(f_img.read()).decode()
                    ext = path.rsplit(".", 1)[-1].lower().replace("jpg", "jpeg")
                    logo_html = f"<img src='data:image/{ext};base64,{b64}' style='width:90px;height:auto;border-radius:12px;' />"
                    break
            if not logo_html:
                logo_html = "<div style='font-size:3rem;'>☀️</div>"

            st.markdown(
                f"""<div style='display:flex;align-items:center;gap:32px;padding:32px 40px;background:#ffffff;
    border:1px solid rgba(58,125,30,.14);border-radius:20px;margin-bottom:28px;position:relative;overflow:hidden;
    box-shadow:0 4px 14px rgba(45,90,22,.10),0 8px 32px rgba(45,90,22,.06);'>
  <div style='position:absolute;top:0;left:0;right:0;height:4px;
      background:linear-gradient(90deg,#3a7d1e,#d4a030,#5aad2e,#2d6a2d);border-radius:20px 20px 0 0;'></div>
  <div class='mn-logo-anim'>{logo_html}</div>
  <div style='flex:1;'>
    <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:2.2rem;color:#2d6a2d;letter-spacing:4px;'>MENAWAR</div>
    <div style='font-family:"Space Grotesk",sans-serif;font-size:.9rem;color:#3a7d1e;letter-spacing:2px;margin-top:4px;font-weight:600;'>Solar Tracking &amp; IoT System</div>
    <div style='font-size:.88rem;color:#4a6741;margin-top:14px;max-width:640px;line-height:1.8;'>
      Menawar is a graduation project dedicated to AI-powered monitoring and diagnostics of photovoltaic solar systems.
      By integrating machine learning with real-time IoT infrastructure, Menawar enables proactive maintenance,
      automated panel cleaning, and intelligent fault detection — maximizing solar energy efficiency.
    </div>
    <div style='margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;'>
      <span style='background:rgba(58,125,30,.1);color:#3a7d1e;padding:5px 14px;border-radius:20px;font-size:.72rem;font-weight:700;border:1px solid rgba(58,125,30,.25);'>AI / Machine Learning</span>
      <span style='background:rgba(45,138,62,.1);color:#2d8a3e;padding:5px 14px;border-radius:20px;font-size:.72rem;font-weight:700;border:1px solid rgba(45,138,62,.25);'>IoT &amp; ESP32</span>
      <span style='background:rgba(212,160,48,.1);color:#b8860b;padding:5px 14px;border-radius:20px;font-size:.72rem;font-weight:700;border:1px solid rgba(212,160,48,.25);'>ThingSpeak Cloud</span>
      <span style='background:rgba(90,173,46,.1);color:#5aad2e;padding:5px 14px;border-radius:20px;font-size:.72rem;font-weight:700;border:1px solid rgba(90,173,46,.25);'>Renewable Energy</span>
    </div>
  </div>
</div>""",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<div style='font-size:.72rem;color:#4a6741;letter-spacing:2px;text-transform:uppercase;"
                "margin:24px 0 16px 0;font-weight:700;'>🚀 Core Capabilities</div>",
                unsafe_allow_html=True,
            )
            services = [
                {"icon": "🤖", "title": "AI Fault Detection",
                 "desc": "Advanced Random Forest model trained on 14 electrical indicators for real-time PV fault detection — short circuits, disconnections, shading, and sensor faults.",
                 "color": "#3a7d1e"},
                {"icon": "📡", "title": "Live IoT Monitoring",
                 "desc": "Direct ThingSpeak integration for continuous voltage, current, UV, and dust data streaming with instant anomaly alerts.",
                 "color": "#d4a030"},
                {"icon": "🔋", "title": "Battery Health Monitor",
                 "desc": "Precision SOC estimation using OCV curve analysis with charge/discharge cycle tracking and critical threshold alerts.",
                 "color": "#2d6a2d"},
                {"icon": "🧹", "title": "Cloud-Triggered Panel Cleaning",
                 "desc": "Global remote cleaning control via ThingSpeak Field 8. The ESP32 polls the cloud and executes commands from anywhere in the world.",
                 "color": "#2d8a3e"},
                {"icon": "🔭", "title": "Predictive Health Forecasting",
                 "desc": "Multi-factor forecast engine combining weather simulation, soiling coefficient, and sequential trend analysis for tomorrow's power projection.",
                 "color": "#5aad2e"},
                {"icon": "📅", "title": "Daily Performance Reports",
                 "desc": "Comprehensive daily analysis including fault-cause loss breakdown, system efficiency, and hourly status tracking.",
                 "color": "#c47a1e"},
            ]
            col1, col2 = st.columns(2)
            for i, srv in enumerate(services):
                col = col1 if i % 2 == 0 else col2
                with col:
                    st.markdown(
                        f"""<div class='mn-card' style='padding:20px 22px;margin-bottom:12px;'>
  <div style='display:flex;align-items:flex-start;gap:16px;'>
    <div style='font-size:1.9rem;min-width:44px;text-align:center;padding-top:2px;'>{srv['icon']}</div>
    <div style='flex:1;'>
      <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.88rem;color:{srv["color"]};'>{srv['title']}</div>
      <div style='font-size:.78rem;color:#4a6741;margin-top:6px;line-height:1.7;'>{srv['desc']}</div>
    </div>
  </div>
</div>""",
                        unsafe_allow_html=True,
                    )

            st.markdown(
                "<div style='font-size:.72rem;color:#4a6741;letter-spacing:2px;text-transform:uppercase;"
                "margin:28px 0 16px 0;font-weight:700;'>⚙️ Technology Stack</div>",
                unsafe_allow_html=True,
            )
            techs = [
                ("🐍", "Python & Streamlit", "Backend & Dashboard"),
                ("🤖", "Scikit-learn RF",    "ML Fault Detection"),
                ("📡", "ThingSpeak API",     "IoT Data Platform"),
                ("⚡", "ESP32",              "Hardware Control"),
                ("📊", "Plotly",             "Interactive Charts"),
                ("🔋", "OCV Model",          "SOC Estimation"),
            ]
            tc = st.columns(6)
            for col, (icon, name, sub) in zip(tc, techs):
                with col:
                    st.markdown(
                        f"""<div style='background:#ffffff;border:1px solid rgba(58,125,30,.14);border-radius:14px;
    padding:16px 8px;text-align:center;box-shadow:0 1px 4px rgba(45,90,22,.07);'>
  <div style='font-size:1.5rem;'>{icon}</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-size:.65rem;color:#2d6a2d;
      margin:8px 0 4px 0;letter-spacing:.5px;font-weight:700;'>{name}</div>
  <div style='font-size:.62rem;color:#8aaa7a;'>{sub}</div>
</div>""",
                        unsafe_allow_html=True,
                    )

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown(
                """<div style='background:#f8faf6;border:1px solid rgba(58,125,30,.14);border-radius:14px;
  padding:20px 28px;text-align:center;box-shadow:0 1px 4px rgba(45,90,22,.07);'>
  <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.7rem;
      color:#4a6741;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;'>Project Data Channel</div>
  <div style='font-size:.85rem;color:#3a7d1e;font-weight:600;'>
    📊 ThingSpeak Channel — <span style='color:#2d6a2d;'>Configure via sidebar to connect your own channel</span></div>
  <div style='font-size:.78rem;color:#8aaa7a;margin-top:6px;'>
    Menawar PV Intelligence · Solar Tracking &amp; IoT System · Graduation Project 2024–2025</div>
</div>""",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # ─────────────────────────────────────
    #  PANEL: CONTACT US
    # ─────────────────────────────────────
    def panel_contact_us(self) -> None:
        with st.container():
            st.markdown("<div class='panel-content'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='mn-section'><span style='font-size:1rem'>📞</span>"
                "<span class='mn-section-title'>Contact Us — Project Team</span></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                """<div style='background:linear-gradient(135deg,rgba(58,125,30,.07),rgba(212,160,48,.04));
  border:1.5px solid rgba(58,125,30,.22);border-radius:18px;padding:28px 36px;
  margin-bottom:28px;position:relative;overflow:hidden;
  box-shadow:0 1px 4px rgba(45,90,22,.08),0 4px 16px rgba(45,90,22,.05);'>
  <div style='position:absolute;top:0;left:0;right:0;height:4px;
      background:linear-gradient(90deg,#d4a030,#3a7d1e,#2d6a2d);border-radius:18px 18px 0 0;'></div>
  <div style='display:flex;align-items:center;gap:16px;margin-bottom:12px;'>
    <span style='font-size:2rem;'>📧</span>
    <div>
      <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.7rem;
          color:#4a6741;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;'>
        Official Project Email — Primary Contact Channel</div>
      <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:1.4rem;color:#3a7d1e;'>
        menawar030@gmail.com</div>
    </div>
  </div>
  <div style='font-size:.82rem;color:#4a6741;line-height:1.8;max-width:700px;'>
    For all project inquiries, demonstrations, collaborations, and technical questions,
    please reach us at the address above. Our team typically responds within 24–48 hours.
  </div>
</div>""",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<div style='font-size:.72rem;color:#4a6741;letter-spacing:2px;text-transform:uppercase;"
                "margin:8px 0 16px 0;font-weight:700;'>🎓 Academic Advisor</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                """<div style='background:#ffffff;border:1px solid rgba(58,125,30,.22);border-radius:16px;
  padding:22px 28px;margin-bottom:24px;box-shadow:0 1px 4px rgba(45,90,22,.08);
  position:relative;overflow:hidden;'>
  <div style='position:absolute;top:0;left:0;bottom:0;width:4px;
      background:linear-gradient(180deg,#3a7d1e,#d4a030);border-radius:16px 0 0 16px;'></div>
  <div style='margin-left:10px;'>
    <div style='font-family:"Space Grotesk",sans-serif;font-weight:800;font-size:1.05rem;color:#2d6a2d;margin-bottom:4px;'>Dr. Asmaa Gamal Seliem</div>
    <div style='font-size:.78rem;color:#3a7d1e;font-weight:600;margin-bottom:14px;'>Faculty Academic Supervisor &amp; Project Advisor</div>
    <div style='display:flex;gap:28px;flex-wrap:wrap;'>
      <div style='display:flex;align-items:center;gap:8px;'>
        <span style='font-size:1rem;'>📧</span>
        <span style='font-size:.82rem;color:#1a2e12;font-weight:500;'>Asmaseliem90@gmail.com</span>
      </div>
      <div style='display:flex;align-items:center;gap:8px;'>
        <span style='font-size:1rem;'>📱</span>
        <span style='font-family:"Space Grotesk",sans-serif;font-size:.82rem;color:#1a2e12;font-weight:500;'>+201096687807</span>
      </div>
    </div>
  </div>
</div>""",
                unsafe_allow_html=True,
            )

            st.markdown(
                "<div style='font-size:.72rem;color:#4a6741;letter-spacing:2px;text-transform:uppercase;"
                "margin:8px 0 16px 0;font-weight:700;'>👥 Project Team Members</div>",
                unsafe_allow_html=True,
            )
            team = [
                {"name": "Mohammed Osama Mohammed", "role": "IoT Implementation",
                 "desc": "Responsible for the end-to-end IoT integration: ESP32 hardware programming, ThingSpeak cloud connectivity, sensor wiring, and real-time data acquisition pipeline.",
                 "email": "mohamnedosama2030@gmail.com", "phone": "+201129427374", "color": "#3a7d1e", "icon": "📡"},
                {"name": "Sherif Alaa Eldin Ahmed", "role": "Mechanical & Cleaning System",
                 "desc": "Designed and built the mechanical structure of the automated panel cleaning system, including actuator integration and cleaning mechanism validation.",
                 "email": "sherifalaa2001@gmail.com", "phone": "+201020645697", "color": "#2d8a3e", "icon": "🔧"},
                {"name": "Mustafa Emad Rifai", "role": "Artificial Intelligence",
                 "desc": "Developed the machine learning fault detection engine — data preprocessing, feature engineering, Random Forest model training, and classification pipeline.",
                 "email": "mustafaemad2065@gmail.com", "phone": "+201012245407", "color": "#5aad2e", "icon": "🤖"},
                {"name": "Youssef Mustafa Sayed", "role": "Cloud & Communications",
                 "desc": "Architected the cloud data flow between ThingSpeak and the Streamlit dashboard, managing API integrations, multi-tenant configuration, and deployment infrastructure.",
                 "email": "Yousefmustafa446@gmail.com", "phone": "+201150546317", "color": "#d4a030", "icon": "☁️"},
                {"name": "Omar Abdallah Noaman", "role": "Artificial Intelligence",
                 "desc": "Contributed to AI model evaluation, dataset curation, rule-based override logic, and predictive health forecasting algorithms.",
                 "email": "omara.noaman58@gmail.com", "phone": "+201551380331", "color": "#2d6a2d", "icon": "🧠"},
            ]
            col1, col2 = st.columns(2)
            for i, member in enumerate(team):
                col = col1 if i % 2 == 0 else col2
                with col:
                    st.markdown(
                        f"""<div class='mn-card' style='padding:22px 24px;margin-bottom:14px;'>
  <div style='display:flex;align-items:flex-start;gap:16px;'>
    <div style='min-width:52px;height:52px;background:{member["color"]}15;
        border:2px solid {member["color"]}40;border-radius:14px;
        display:flex;align-items:center;justify-content:center;font-size:1.5rem;flex-shrink:0;'>
      {member["icon"]}
    </div>
    <div style='flex:1;'>
      <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.92rem;color:#2d6a2d;'>{member["name"]}</div>
      <div style='display:inline-block;background:{member["color"]}12;color:{member["color"]};
          padding:2px 12px;border-radius:20px;font-size:.68rem;font-weight:700;
          border:1px solid {member["color"]}30;margin:5px 0 10px 0;letter-spacing:.5px;'>{member["role"]}</div>
      <div style='font-size:.77rem;color:#4a6741;line-height:1.7;margin-bottom:12px;'>{member["desc"]}</div>
      <div style='display:flex;flex-direction:column;gap:6px;'>
        <div style='display:flex;align-items:center;gap:8px;background:#f8faf6;border-radius:8px;
            padding:7px 10px;border:1px solid rgba(58,125,30,.12);'>
          <span style='font-size:.85rem;'>📧</span>
          <span style='font-size:.76rem;color:#3a7d1e;font-weight:500;'>{member["email"]}</span>
        </div>
        <div style='display:flex;align-items:center;gap:8px;background:#f8faf6;border-radius:8px;
            padding:7px 10px;border:1px solid rgba(58,125,30,.12);'>
          <span style='font-size:.85rem;'>📱</span>
          <span style='font-family:"Space Grotesk",sans-serif;font-size:.76rem;color:#1a2e12;font-weight:500;'>{member["phone"]}</span>
        </div>
      </div>
    </div>
  </div>
</div>""",
                        unsafe_allow_html=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

    # ═══════════════════════════════════════
    #  MAIN RENDER
    # ═══════════════════════════════════════
    def render(self) -> None:
        now      = now_cairo()
        prod_now = is_production_period(now.time())

        # FIX 3: inject CSS (light-only) as very first Streamlit call
        inject_css()

        # ══════════════════════════════════
        #  SIDEBAR
        # ══════════════════════════════════
        # FIX 2: native image logo
        render_logo_sidebar()
        st.sidebar.markdown(
            "<div style='text-align:center;padding:4px 0 14px 0;"
            "border-bottom:1.5px solid rgba(58,125,30,.14);margin-bottom:16px;'>"
            "<div style='font-family:\"Space Grotesk\",sans-serif;font-weight:800;font-size:1.15rem;"
            "color:#2d6a2d;letter-spacing:4px;'>MENAWAR</div>"
            "<div style='font-size:.56rem;color:#8aaa7a;letter-spacing:2px;text-transform:uppercase;margin-top:3px;'>"
            "Solar Tracking &amp; IoT System</div></div>",
            unsafe_allow_html=True,
        )

        # ── FIX 5: Reactive ThingSpeak Auth ──
        st.sidebar.markdown("## 🔗 THINGSPEAK CHANNEL")
        st.sidebar.text_input("Channel ID", key="ts_channel_id",
            placeholder="e.g. 3274646", help="Your ThingSpeak Channel ID (numeric)")
        st.sidebar.text_input("Read API Key", key="ts_read_key",
            placeholder="e.g. ZGH7UMZPP8KWY4N3", type="password",
            help="ThingSpeak Read API Key for fetching data")
        st.sidebar.text_input("Write API Key", key="ts_write_key",
            placeholder="e.g. XXXXXXXXXXXXX", type="password",
            help="ThingSpeak Write API Key (optional)")

        st.sidebar.markdown("---")
        st.sidebar.markdown("## 🧹 CLEANING CONTROL")
        st.sidebar.markdown(
            "<div style='font-size:.62rem;color:#8aaa7a;margin:-6px 0 10px 0;line-height:1.6;'>"
            "ThingSpeak TalkBack — create a TalkBack app at thingspeak.com/talkbacks</div>",
            unsafe_allow_html=True,
        )
        st.sidebar.text_input("TalkBack App ID", key="ts_talkback_app_id",
            placeholder="e.g. 12345", help="Your ThingSpeak TalkBack App ID")
        st.sidebar.text_input("TalkBack API Key", key="ts_talkback_key",
            placeholder="TalkBack API Key", type="password",
            help="ThingSpeak TalkBack API Key for sending cleaning commands to ESP32")

        ch_id  = st.session_state.get("ts_channel_id", "").strip()
        rd_key = st.session_state.get("ts_read_key",   "").strip()
        conn_ok = False

        if ch_id and rd_key:
            cache_key = f"conn_{ch_id}_{rd_key[:8]}"
            if st.session_state.get(cache_key) is None:
                with st.sidebar:
                    with st.spinner("🔌 Verifying channel..."):
                        ok, msg = validate_thingspeak(ch_id, rd_key)
                        st.session_state[cache_key] = (ok, msg)
            ok, msg = st.session_state[cache_key]
            conn_ok = ok
            ERR_MAP = {
                "invalid_api_key":     "Invalid API Key — check your Read Key.",
                "channel_not_found":   "Channel does not exist or is private.",
                "timeout":             "Request timed out. Check your internet.",
                "missing_credentials": "Please enter Channel ID and Read API Key.",
                "empty_channel":       "Channel exists but returned no data.",
            }
            if ok:
                st.sidebar.markdown(
                    f"""<div class='conn-success-card'>
  <span class='online-dot'></span>
  <div>
    <div style='font-size:.72rem;color:#2d8a3e;font-weight:700;font-family:"Space Grotesk",sans-serif;'>✅ Connected Successfully</div>
    <div style='font-size:.62rem;color:#8aaa7a;margin-top:2px;'>
      {msg if msg != 'Connected' else 'Channel is live and reachable.'}</div>
  </div>
</div>""",
                    unsafe_allow_html=True,
                )
            else:
                err_txt = ERR_MAP.get(msg, f"Connection error: {msg}")
                st.sidebar.markdown(
                    f"""<div class='conn-error-card'>
  <div style='font-size:.72rem;color:#dc2626;font-weight:700;font-family:"Space Grotesk",sans-serif;'>❌ Connection Failed</div>
  <div style='font-size:.62rem;color:#4a6741;margin-top:4px;'>{err_txt}</div>
</div>""",
                    unsafe_allow_html=True,
                )
        elif ch_id or rd_key:
            st.sidebar.markdown(
                "<div style='background:rgba(58,125,30,.06);border:1px solid rgba(58,125,30,.18);"
                "border-radius:10px;padding:10px 14px;font-size:.7rem;color:#8aaa7a;margin:6px 0;'>"
                "ℹ️ Enter both Channel ID and Read API Key to connect.</div>",
                unsafe_allow_html=True,
            )

        if st.sidebar.button("🔌 Reconnect / Clear Cache", use_container_width=True, type="primary"):
            for k in list(st.session_state.keys()):
                if k.startswith("conn_"):
                    del st.session_state[k]
            st.cache_data.clear()
            st.rerun()

        st.sidebar.markdown("---")

        # ── Navigation ──
        st.sidebar.markdown("## 📌 NAVIGATION")
        if "active_panel" not in st.session_state:
            st.session_state.active_panel = "home"

        sidebar_nav = [
            ("🏠", "Home",       "home",       "Full dashboard overview"),
            ("📞", "Contact Us", "contact_us", "Get in touch with the team"),
            ("🌟", "About Us",   "about_us",   "Our project & capabilities"),
        ]
        for icon, label, key, hint in sidebar_nav:
            active = st.session_state.active_panel == key
            active_style = (
                "background:rgba(58,125,30,.08);border:1.5px solid rgba(58,125,30,.38);"
                "box-shadow:0 2px 8px rgba(45,90,22,.10);" if active
                else "background:#f8faf6;border:1px solid rgba(58,125,30,.12);"
            )
            label_color = "#3a7d1e" if active else "#1a2e12"
            st.sidebar.markdown(
                f"""<div style='{active_style}display:flex;align-items:center;gap:12px;padding:11px 14px;
  border-radius:12px;margin-bottom:5px;'>
  <span style='font-size:1.1rem;'>{icon}</span>
  <div>
    <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.74rem;
        color:{label_color};letter-spacing:.5px;'>{label}</div>
    <div style='font-size:.62rem;color:#8aaa7a;'>{hint}</div>
  </div>
</div>""",
                unsafe_allow_html=True,
            )
            if st.sidebar.button(f"Go to {label}", key=f"sb_{key}", use_container_width=True, help=hint):
                st.session_state.active_panel = key
                st.rerun()

        st.sidebar.markdown("---")

        # ── Operation Mode ──
        auto_refresh = False; is_connected = True; diff_sec = 0.0
        st.sidebar.markdown("## ⚙ OPERATION MODE")
        mode = st.sidebar.radio("", ["📡 Live ThingSpeak", "🎛 Manual Simulation"])

        if mode == "📡 Live ThingSpeak":
            auto_refresh = st.sidebar.toggle("🔄 Auto-Refresh (16s)", value=True)
            v_pv, v_batt, amp, uv_in, uv_ideal_in, dust_in, pwr, ideal_pwr, t_in, success, is_connected, diff_sec = self.fetch_live()
            if success:
                st.sidebar.markdown(
                    f"""<div style='background:rgba(45,138,62,.07);border:1px solid rgba(45,138,62,.28);
  border-radius:10px;padding:10px 12px;margin:8px 0;display:flex;align-items:center;gap:8px;'>
  <span class='online-dot'></span>
  <span style='font-size:.78rem;color:#2d8a3e;font-weight:600;'>Live · {now.strftime('%H:%M:%S')}</span>
</div>""",
                    unsafe_allow_html=True,
                )
            else:
                if self.channel_id and self.read_api_key:
                    st.sidebar.error("⚠️ Connection failed. Using fallback values.")
                v_pv, v_batt, amp, uv_in, uv_ideal_in, dust_in, pwr, ideal_pwr, t_in = (
                    17.5, 12.4, 1.1, 8.0, 9.0, 5.0, 19.25, 20.0, now.time()
                )
        else:
            if "ui_time" not in st.session_state:
                st.session_state.ui_time = now.time()
            t_in      = st.sidebar.time_input("Time", value=st.session_state.ui_time)
            uv_in     = st.sidebar.slider("UV Index", 0.0, 12.0, 8.0)
            dust_in   = st.sidebar.slider("Dust (%)", 0.0, 100.0, 5.0)
            v_pv      = st.sidebar.number_input("PV Voltage (V)", value=17.5)
            v_batt    = st.sidebar.number_input("Battery Voltage (V)", value=12.4)
            amp       = st.sidebar.number_input("Current (A)", value=1.1)
            uv_ideal_in = uv_in   # في السيميوليشن UV_IDEAL = UV_ACTUAL
            ideal_pwr = 20.0; pwr = None; is_connected = True

        st.sidebar.markdown("---")
        is_night_now = is_night_time(now.time())
        if is_night_now:
            nl, nc = "🌙 STANDBY — NIGHT", "#5b6a3e"
        elif prod_now:
            nl, nc = "⚡ PRODUCTION ACTIVE", "#2d8a3e"
        else:
            nl, nc = "— STANDBY", "#8aaa7a"
        st.sidebar.markdown(
            f"<div class='period-badge' style='background:{nc}10;border:1.5px solid {nc}40;color:{nc};'>{nl}</div>",
            unsafe_allow_html=True,
        )

        # ── Process Telemetry ──
        features_df, pwr_out, soc, is_prod = self.process_telemetry(
            v_pv, v_batt, amp, uv_in, uv_ideal_in, dust_in, t_in, pwr, ideal_pwr
        )
        is_night   = is_night_time(t_in)
        is_prod_p  = is_production_period(t_in)

        try:
            pred_idx     = self.rf.predict(features_df)[0]
            ai_status    = self.le.inverse_transform([pred_idx])[0]
            probs        = self.rf.predict_proba(features_df)[0]
            confidence   = float(np.max(probs))
            vd           = features_df["V_Diff"].values[0]
            final_status, css_class, alert_fn, alert_text, fault_detail = self.rule_override(
                v_pv, v_batt, amp, uv_in, uv_ideal_in, dust_in, soc, vd,
                is_night, is_connected, mode, ai_status,
            )
        except Exception as e:
            final_status = "Unknown"; css_class = "warn"; alert_fn = st.warning
            alert_text   = f"Diagnosis error: {e}"; fault_detail = None; confidence = 0.0

        # ══════════════════════════════════
        #  HEADER (FIX 2: native image)
        # ══════════════════════════════════
        render_logo_header()
        st.markdown("<div class='mn-divider'></div>", unsafe_allow_html=True)

        # ══════════════════════════════════
        #  TOP NAV BUTTONS
        # ══════════════════════════════════
        nav_items = [
            ("⚡", "Overview",   "Live metrics & status", "overview"),
            ("🤖", "AI Diagnosis","Fault detection engine", "diagnosis"),
            ("📅", "Day Report", "Today's full history",   "day_report"),
            ("🔋", "Battery",    "SOC & discharge log",    "battery"),
            ("🔭", "Predictive", "Forecast & risk score",  "prediction"),
            ("🧹", "Cleaning",   "Panel cleaning control", "cleaning"),
        ]
        nav_cols = st.columns(6)
        for col, (icon, title, sub, key) in zip(nav_cols, nav_items):
            active       = st.session_state.active_panel == key
            border_style = "2px solid #3a7d1e" if active else "1.5px solid rgba(58,125,30,.18)"
            bg_style     = "rgba(58,125,30,.07)" if active else "#ffffff"
            shadow_style = "0 2px 12px rgba(45,90,22,.14)" if active else "0 1px 4px rgba(45,90,22,.06)"
            with col:
                st.markdown(
                    f"""<div style='background:{bg_style};border:{border_style};border-radius:14px;
  padding:12px 8px;text-align:center;margin-bottom:4px;box-shadow:{shadow_style};'>
  <div style='font-size:1.4rem;'>{icon}</div>
  <div style='font-family:"Space Grotesk",sans-serif;font-weight:700;font-size:.65rem;
      color:{"#3a7d1e" if active else "#4a6741"};letter-spacing:1px;text-transform:uppercase;margin-top:5px;'>{title}</div>
  <div style='font-size:.58rem;color:#8aaa7a;margin-top:2px;'>{sub}</div>
</div>""",
                    unsafe_allow_html=True,
                )
                if st.button(f"Open {title}", key=f"btn_{key}", use_container_width=True, help=sub):
                    st.session_state.active_panel = key
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ══════════════════════════════════
        #  FIX 1 — EXECUTION FIREWALL
        #
        #  Only ONE panel renders per run.
        #  Each is inside its own container.
        #  No fallthrough, no bleed.
        # ══════════════════════════════════
        panel = st.session_state.active_panel
        _panel_slot = st.empty()

        # Helper: fetch history only when needed
        def _get_hist() -> pd.DataFrame | None:
            if mode == "📡 Live ThingSpeak":
                with st.spinner("📡 Loading today's data..."):
                    return self.fetch_history()
            return None

        with _panel_slot.container():
            if panel == "home":
                self.panel_home(
                    v_pv, v_batt, amp, pwr_out, soc, uv_in, dust_in,
                    is_night, is_prod_p, final_status, css_class,
                    diff_sec, is_connected, mode, confidence, alert_fn, alert_text,
                    features_df, fault_detail, _get_hist(),
                )

            elif panel == "overview":
                self.panel_overview(
                    v_pv, v_batt, amp, pwr_out, soc, uv_in, dust_in,
                    is_night, is_prod_p, final_status, css_class,
                    diff_sec, is_connected, mode, confidence, alert_fn, alert_text,
                )

            elif panel == "diagnosis":
                self.panel_diagnosis(
                    v_pv, v_batt, amp, uv_in, dust_in, soc, features_df,
                    final_status, css_class, alert_fn, alert_text, fault_detail, confidence,
                )

            elif panel == "day_report":
                self.panel_day_report(_get_hist())

            elif panel == "battery":
                self.panel_battery(soc, v_batt, is_prod_p, is_night, mode, _get_hist())

            elif panel == "prediction":
                self.panel_prediction(
                    v_pv, v_batt, amp, uv_in, dust_in, soc,
                    features_df, final_status, _get_hist(),
                )

            elif panel == "cleaning":
                self.panel_cleaning(dust_in)

            elif panel == "about_us":
                self.panel_about_us()

            elif panel == "contact_us":
                self.panel_contact_us()

        # ── AUTO REFRESH (1-second countdown — no monolithic sleep) ──
        _REFRESH_INTERVAL = 16
        if (
            mode == "📡 Live ThingSpeak"
            and auto_refresh
            and panel not in ("about_us", "contact_us", "home")
        ):
            if "next_refresh_at" not in st.session_state:
                st.session_state.next_refresh_at = time.time() + _REFRESH_INTERVAL
            remaining = max(0, int(st.session_state.next_refresh_at - time.time()))
            if remaining <= 0:
                st.session_state.next_refresh_at = time.time() + _REFRESH_INTERVAL
                st.rerun()
            else:
                st.caption(f"🔄 Auto-refresh in {remaining}s · Last update: {now.strftime('%H:%M:%S')}")
                time.sleep(1)
                st.rerun()


# ─────────────────────────────────────────
if __name__ == "__main__":
    app = PVDashboard()
    app.render()
