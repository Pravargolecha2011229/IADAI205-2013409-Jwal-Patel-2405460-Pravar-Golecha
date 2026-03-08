import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
from datetime import datetime, timedelta
import os, json, html, re, hashlib, sqlite3, uuid
import requests
import warnings
warnings.filterwarnings('ignore')
try:
    import matplotlib  # required by pandas Styler.background_gradient
    HAS_MATPLOTLIB = True
except Exception:
    HAS_MATPLOTLIB = False

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
def _secret_value(name):
    """Safely read from Streamlit secrets in local and cloud environments."""
    try:
        return st.secrets.get(name)
    except Exception:
        return None


# Secrets take precedence, then environment variables.
GEMINI_API_KEY = _secret_value("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = _secret_value("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY", "")
GEMINI_MODEL = _secret_value("GEMINI_MODEL") or os.environ.get("GEMINI_MODEL", "") or "models/gemini-2.5-pro"
GROQ_MODEL = _secret_value("GROQ_MODEL") or os.environ.get("GROQ_MODEL", "") or "llama-3.3-70b-versatile"
AI_PROVIDER = (_secret_value("AI_PROVIDER") or os.environ.get("AI_PROVIDER", "")).strip().lower()

# Auto-detect Groq keys pasted into Gemini fields.
if not GROQ_API_KEY and GEMINI_API_KEY.startswith("gsk_"):
    GROQ_API_KEY = GEMINI_API_KEY

if not AI_PROVIDER:
    AI_PROVIDER = "groq" if GROQ_API_KEY else "gemini"

if AI_PROVIDER == "groq" and not GROQ_API_KEY:
    st.warning("Groq API key not found. Add GROQ_API_KEY (or AI_PROVIDER=gemini with GEMINI_API_KEY).")
if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
    st.warning("Gemini API key not found. Add GEMINI_API_KEY (or AI_PROVIDER=groq with GROQ_API_KEY).")

st.set_page_config(
    page_title="GlobeTrek AI – Cultural Travel Planner",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
#  DARK THEME CSS  (Midnight Teal Palette)
# ─────────────────────────────────────────
st.markdown("""
<style>
/* ── Global reset ─────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── App background ──────────────────── */
.stApp {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 40%, #0a1628 70%, #061020 100%);
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* ── Sidebar ─────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #0a1628 100%) !important;
    border-right: 1px solid #1e3a5f !important;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stRadio label { color: #94a3b8 !important; }
[data-testid="stSidebar"] hr { border-color: #1e3a5f !important; }

/* ── Typography ──────────────────────── */
.main-header {
    font-size: 2.8rem;
    font-weight: 900;
    letter-spacing: 3px;
    text-align: center;
    background: linear-gradient(90deg, #00d4aa, #0099ff, #7c3aed);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin: 0.5rem 0 0.2rem;
    animation: shimmerText 4s ease infinite;
}
.sub-header {
    font-size: 1.6rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00d4aa, #0099ff);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    margin: 1.2rem 0 0.8rem;
}
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #00d4aa;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 1rem 0 0.5rem;
}

/* ── Hero Banner ─────────────────────── */
.hero-shell {
    position: relative;
    overflow: hidden;
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    background: linear-gradient(135deg, #0d3b5e 0%, #0a2640 40%, #0d3349 70%, #1a1040 100%);
    border: 1px solid #1e4d7a;
    box-shadow: 0 20px 60px rgba(0,212,170,0.1), 0 0 0 1px rgba(0,212,170,0.05);
}
.hero-shell h3 { color: #e2e8f0; font-size: 1.5rem; font-weight: 800; margin-bottom: 0.5rem; }
.hero-shell p  { color: #94a3b8; font-size: 1rem; line-height: 1.7; }
.hero-tag {
    display: inline-block;
    padding: 0.25rem 0.8rem;
    border-radius: 999px;
    background: rgba(0,212,170,0.15);
    border: 1px solid rgba(0,212,170,0.3);
    color: #00d4aa;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 0.8rem;
}
.orb {
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
    filter: blur(60px);
    opacity: 0.25;
}
.orb-1 { width:300px; height:300px; right:-80px; top:-80px; background: radial-gradient(circle, #00d4aa, transparent); }
.orb-2 { width:200px; height:200px; left:5%; bottom:-60px; background: radial-gradient(circle, #0099ff, transparent); animation-delay:2s; }
.orb-3 { width:150px; height:150px; right:25%; top:20%; background: radial-gradient(circle, #7c3aed, transparent); animation-delay:4s; }

/* ── Cards ───────────────────────────── */
.gt-card {
    background: linear-gradient(135deg, #0d1b2a, #0f2235);
    border: 1px solid #1e3a5f;
    border-left: 4px solid #00d4aa;
    border-radius: 16px;
    padding: 1.5rem;
    margin: 0.8rem 0;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.gt-card:hover {
    border-left-color: #0099ff;
    box-shadow: 0 15px 40px rgba(0,212,170,0.12);
    transform: translateY(-4px);
}
.gt-card h4 { color: #00d4aa; font-weight: 800; font-size: 1.1rem; margin-bottom: 0.6rem; }
.gt-card p  { color: #94a3b8; font-size: 0.93rem; line-height: 1.6; margin: 0.3rem 0; }
.gt-card strong { color: #64b5f6; }

/* Destination card variant */
.dest-card {
    background: linear-gradient(135deg, #0d1b2a, #0f2235);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 1.4rem;
    margin: 0.6rem 0;
    transition: all 0.3s ease;
    cursor: pointer;
}
.dest-card:hover {
    border-color: #00d4aa;
    box-shadow: 0 10px 35px rgba(0,212,170,0.15);
    transform: translateY(-3px);
}
.dest-card .dest-name { color: #e2e8f0; font-weight: 700; font-size: 1.05rem; }
.dest-card .dest-country { color: #00d4aa; font-size: 0.85rem; font-weight: 600; }
.dest-card .dest-meta { color: #64748b; font-size: 0.82rem; margin-top: 0.4rem; }

/* Review / Feedback card */
.review-card {
    background: #0d1b2a;
    border-left: 4px solid #0099ff;
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    margin: 0.6rem 0;
    transition: all 0.25s ease;
}
.review-card:hover { transform: translateX(4px); border-left-color: #00d4aa; }

.feedback-card {
    background: #0d1b2a;
    border-left: 4px solid #7c3aed;
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    margin: 0.6rem 0;
    transition: all 0.25s ease;
}
.feedback-card:hover { transform: translateX(4px); border-left-color: #00d4aa; }

/* AI response container */
.ai-response {
    background: linear-gradient(135deg, #0d1b2a, #0a1628);
    border: 1px solid #1e4d7a;
    border-left: 4px solid #00d4aa;
    border-radius: 16px;
    padding: 1.8rem;
    margin: 1rem 0;
    color: #cbd5e1;
    line-height: 1.8;
    font-size: 0.97rem;
}
.ai-response h1, .ai-response h2, .ai-response h3 { color: #00d4aa; margin: 1rem 0 0.5rem; }
.ai-response h4, .ai-response h5 { color: #0099ff; margin: 0.8rem 0 0.4rem; }
.ai-response strong { color: #64b5f6; }
.ai-response em { color: #94a3b8; }
.ai-response ul, .ai-response ol { padding-left: 1.4rem; margin: 0.5rem 0; }
.ai-response li { margin: 0.3rem 0; color: #cbd5e1; }
.ai-response table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
.ai-response th { background: #1e3a5f; color: #00d4aa; padding: 0.6rem 1rem; text-align: left; }
.ai-response td { border-bottom: 1px solid #1e3a5f; padding: 0.5rem 1rem; color: #94a3b8; }
.ai-response hr { border-color: #1e3a5f; margin: 1.2rem 0; }
.ai-response code { background: #0f2235; color: #00d4aa; padding: 0.1rem 0.4rem; border-radius: 4px; }

/* Auth container */
.auth-box {
    max-width: 460px;
    margin: 40px auto;
    padding: 2.5rem;
    background: linear-gradient(135deg, #0d1b2a, #0f2235);
    border: 1px solid #1e3a5f;
    border-radius: 20px;
    box-shadow: 0 30px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,212,170,0.08);
}
.auth-logo {
    text-align: center;
    margin-bottom: 2rem;
}
.auth-logo .brand { font-size: 2.2rem; font-weight: 900; letter-spacing: 2px; background: linear-gradient(90deg,#00d4aa,#0099ff); -webkit-background-clip: text; background-clip: text; color: transparent; }
.auth-logo .tagline { color: #64748b; font-size: 0.9rem; margin-top: 0.2rem; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00d4aa, #0099ff) !important;
    color: #0a0e1a !important;
    font-weight: 800 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 1.4rem !important;
    transition: all 0.3s ease !important;
    letter-spacing: 0.5px !important;
}
.stButton > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 12px 30px rgba(0,212,170,0.35) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stDateInput > div > div > input {
    background: #0f2235 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00d4aa !important;
    box-shadow: 0 0 0 2px rgba(0,212,170,0.2) !important;
}
.stSelectbox > div > div { color: #e2e8f0 !important; }
label { color: #94a3b8 !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0d1b2a, #0f2235) !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 14px !important;
    padding: 1.2rem !important;
}
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.82rem !important; }
[data-testid="stMetricValue"] { color: #00d4aa !important; font-weight: 800 !important; }
[data-testid="stMetricDelta"] { color: #0099ff !important; }

/* Tabs */
[role="tablist"] { border-bottom: 2px solid #1e3a5f !important; }
[role="tab"] { color: #64748b !important; font-weight: 700 !important; }
[role="tab"][aria-selected="true"] { color: #00d4aa !important; border-bottom: 2px solid #00d4aa !important; }

/* Expanders */
.streamlit-expanderHeader { background: #0d1b2a !important; color: #94a3b8 !important; border-radius: 10px !important; border: 1px solid #1e3a5f !important; }

/* Live chip */
.live-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.8rem;
    border-radius: 999px;
    background: rgba(0,212,170,0.1);
    border: 1px solid rgba(0,212,170,0.3);
    color: #00d4aa;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 0.8rem;
}
.pulse { width:8px; height:8px; border-radius:50%; background:#00d4aa; animation: pulse 1.5s ease-in-out infinite; }

/* Stars */
.stars { color: #fbbf24; font-size: 1.1rem; }

/* Badge */
.badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
}
.badge-teal   { background: rgba(0,212,170,0.15); color: #00d4aa; border: 1px solid rgba(0,212,170,0.3); }
.badge-blue   { background: rgba(0,153,255,0.15); color: #0099ff; border: 1px solid rgba(0,153,255,0.3); }
.badge-purple { background: rgba(124,58,237,0.15); color: #a78bfa; border: 1px solid rgba(124,58,237,0.3); }
.badge-amber  { background: rgba(251,191,36,0.15); color: #fbbf24; border: 1px solid rgba(251,191,36,0.3); }

/* Progress bar override */
.stProgress > div > div { background: linear-gradient(90deg, #00d4aa, #0099ff) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: linear-gradient(#00d4aa, #0099ff); border-radius: 3px; }

/* Divider */
.gt-divider { border: none; border-top: 1px solid #1e3a5f; margin: 1.5rem 0; }

/* Info / Success / Warning boxes */
.stAlert { border-radius: 12px !important; }
.stSuccess { background: rgba(0,212,170,0.1) !important; border-color: #00d4aa !important; }
.stInfo    { background: rgba(0,153,255,0.1) !important; border-color: #0099ff !important; }
.stWarning { background: rgba(251,191,36,0.1) !important; border-color: #fbbf24 !important; }
.stError   { background: rgba(239,68,68,0.1) !important; border-color: #ef4444 !important; }

/* Chatbot message */
.chat-user {
    background: rgba(0,153,255,0.12);
    border: 1px solid rgba(0,153,255,0.25);
    border-radius: 14px 14px 4px 14px;
    padding: 0.9rem 1.2rem;
    margin: 0.5rem 0;
    color: #cbd5e1;
    max-width: 80%;
    margin-left: auto;
}
.chat-bot {
    background: rgba(0,212,170,0.08);
    border: 1px solid rgba(0,212,170,0.2);
    border-radius: 14px 14px 14px 4px;
    padding: 0.9rem 1.2rem;
    margin: 0.5rem 0;
    color: #cbd5e1;
    max-width: 85%;
}

/* Weather card */
.weather-card {
    background: linear-gradient(135deg, #0d3b5e, #0a2640);
    border: 1px solid #1e4d7a;
    border-radius: 14px;
    padding: 1.2rem;
    text-align: center;
}
.weather-temp { font-size: 2.2rem; font-weight: 800; color: #00d4aa; }
.weather-cond { color: #94a3b8; font-size: 0.9rem; }

/* Tip box */
.tip-box {
    background: rgba(124,58,237,0.08);
    border: 1px solid rgba(124,58,237,0.25);
    border-radius: 12px;
    padding: 1rem 1.3rem;
    margin: 0.6rem 0;
    color: #c4b5fd;
    font-size: 0.9rem;
}
.tip-box strong { color: #a78bfa; }

/* Sidebar nav pills */
.nav-pill {
    display: block;
    padding: 0.65rem 1rem;
    border-radius: 10px;
    color: #94a3b8;
    font-weight: 600;
    margin: 0.2rem 0;
    transition: all 0.2s;
    cursor: pointer;
    text-decoration: none;
}
.nav-pill:hover, .nav-pill.active {
    background: rgba(0,212,170,0.12);
    color: #00d4aa;
    border-left: 3px solid #00d4aa;
}

/* Keyframes */
@keyframes shimmerText {
    0%,100% { filter: drop-shadow(0 0 12px rgba(0,212,170,0.4)); }
    50%      { filter: drop-shadow(0 0 20px rgba(0,153,255,0.5)); }
}
@keyframes pulse {
    0%   { transform: scale(0.8); opacity: 1; box-shadow: 0 0 0 0 rgba(0,212,170,0.4); }
    70%  { transform: scale(1); opacity: 0.7; box-shadow: 0 0 0 10px rgba(0,212,170,0); }
    100% { transform: scale(0.8); opacity: 1; box-shadow: 0 0 0 0 rgba(0,212,170,0); }
}
@keyframes fadeUp {
    from { opacity:0; transform: translateY(20px); }
    to   { opacity:1; transform: translateY(0); }
}
.fade-up { animation: fadeUp 0.7s ease-out; }

/* Hide Streamlit default elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────
DB_PATH = "globetrek.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        first_name TEXT DEFAULT '',
        last_name TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS saved_itineraries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        country TEXT NOT NULL,
        itinerary_data TEXT NOT NULL,
        start_date DATE,
        end_date DATE,
        budget REAL,
        group_size INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        site_name TEXT NOT NULL,
        country TEXT NOT NULL,
        site_type TEXT DEFAULT '',
        rating REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, site_name),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        site_name TEXT NOT NULL,
        country TEXT NOT NULL,
        rating INTEGER NOT NULL,
        review_text TEXT,
        visit_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        satisfaction_rating INTEGER NOT NULL,
        feedback_text TEXT,
        category TEXT DEFAULT 'General',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS travel_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        country TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS user_presence (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit(); conn.close()


# ─────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────
def hp(p): return hashlib.sha256(p.encode()).hexdigest()

def register_user(username, password, email, first="", last=""):
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return False, "Invalid email format."
    if len(password) < 6:
        return False, "Password must be ≥ 6 characters."
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO users(username,password,email,first_name,last_name) VALUES(?,?,?,?,?)",
                     (username.strip(), hp(password), email.strip(), first.strip(), last.strip()))
        conn.commit(); conn.close()
        return True, "Account created! Please login."
    except sqlite3.IntegrityError:
        return False, "Username or email already taken."
    except Exception as e:
        return False, str(e)

def login_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, first_name FROM users WHERE username=? AND password=?", (username.strip(), hp(password)))
        row = c.fetchone(); conn.close()
        if row: return True, row[0], row[1] or username
        return False, None, None
    except: return False, None, None

def get_user(uid):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT username,email,first_name,last_name,created_at FROM users WHERE id=?", (uid,))
        r = c.fetchone(); conn.close(); return r
    except: return None


# ─────────────────────────────────────────
#  DB OPERATIONS
# ─────────────────────────────────────────
def add_fav(uid, site, country, stype="", rating=0):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT OR IGNORE INTO favorites(user_id,site_name,country,site_type,rating) VALUES(?,?,?,?,?)",
                     (uid,site,country,stype,rating))
        conn.commit(); conn.close(); return True
    except: return False

def rm_fav(uid, site):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM favorites WHERE user_id=? AND site_name=?", (uid,site))
        conn.commit(); conn.close(); return True
    except: return False

def get_favs(uid):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT site_name,country,site_type,rating FROM favorites WHERE user_id=? ORDER BY created_at DESC", (uid,))
        r = c.fetchall(); conn.close(); return r
    except: return []

def save_itinerary(uid, title, country, data, sd, ed, budget, gs):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO saved_itineraries(user_id,title,country,itinerary_data,start_date,end_date,budget,group_size) VALUES(?,?,?,?,?,?,?,?)",
                     (uid,title,country,json.dumps(data),sd,ed,budget,gs))
        conn.commit(); conn.close(); return True
    except: return False

def get_itineraries(uid):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT id,title,country,start_date,end_date,budget,created_at FROM saved_itineraries WHERE user_id=? ORDER BY created_at DESC", (uid,))
        r = c.fetchall(); conn.close(); return r
    except: return []

def save_review(uid, site, country, rating, text, vdate=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO reviews(user_id,site_name,country,rating,review_text,visit_date) VALUES(?,?,?,?,?,?)",
                     (uid,site,country,rating,text,vdate))
        conn.commit(); conn.close(); return True, "Review submitted!"
    except Exception as e: return False, str(e)

def get_reviews(site, country):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("""SELECT u.username,r.rating,r.review_text,r.created_at
                     FROM reviews r JOIN users u ON r.user_id=u.id
                     WHERE r.site_name=? AND r.country=? ORDER BY r.created_at DESC""", (site,country))
        r = c.fetchall(); conn.close(); return r
    except: return []

def save_feedback(uid, sat, text, cat="General"):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO feedback(user_id,satisfaction_rating,feedback_text,category) VALUES(?,?,?,?)", (uid,sat,text,cat))
        conn.commit(); conn.close(); return True, "Thank you for your feedback!"
    except: return False, "Error saving."

def get_recent_feedback(limit=20):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("""SELECT u.username,f.satisfaction_rating,f.feedback_text,f.category,f.created_at
                     FROM feedback f JOIN users u ON f.user_id=u.id
                     ORDER BY f.created_at DESC LIMIT ?""", (limit,))
        r = c.fetchall(); conn.close(); return r
    except: return []

def save_note(uid, title, content, country=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO travel_notes(user_id,title,content,country) VALUES(?,?,?,?)", (uid,title,content,country))
        conn.commit(); conn.close(); return True
    except: return False

def get_notes(uid):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT id,title,content,country,created_at FROM travel_notes WHERE user_id=? ORDER BY created_at DESC", (uid,))
        r = c.fetchall(); conn.close(); return r
    except: return []

def del_note(nid, uid):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM travel_notes WHERE id=? AND user_id=?", (nid, uid))
        conn.commit(); conn.close(); return True
    except: return False

def save_chat(uid, role, msg):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO chat_history(user_id,role,message) VALUES(?,?,?)", (uid,role,msg))
        conn.commit(); conn.close()
    except: pass

def get_chat(uid, limit=20):
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        c.execute("SELECT role,message FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid,limit))
        r = c.fetchall(); conn.close(); return list(reversed(r))
    except: return []

def touch_user_presence(uid):
    try:
        if not uid:
            return
        if "session_id" not in st.session_state or not st.session_state.session_id:
            st.session_state.session_id = f"{uid}-{uuid.uuid4().hex}"
        sid = st.session_state.session_id
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO user_presence(session_id,user_id,last_seen)
            VALUES(?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
              user_id=excluded.user_id,
              last_seen=CURRENT_TIMESTAMP
        """, (sid, uid))
        conn.execute("DELETE FROM user_presence WHERE last_seen < datetime('now','-5 minutes')")
        conn.commit()
        conn.close()
    except:
        pass

def clear_user_presence():
    try:
        sid = st.session_state.get("session_id")
        if not sid:
            return
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM user_presence WHERE session_id=?", (sid,))
        conn.commit()
        conn.close()
    except:
        pass

def get_stats():
    try:
        conn = sqlite3.connect(DB_PATH); c = conn.cursor()
        stats = {}
        for key, query in [
            ('users',       "SELECT COUNT(*) FROM users"),
            ('users_online',"SELECT COUNT(DISTINCT user_id) FROM user_presence WHERE last_seen >= datetime('now','-5 minutes')"),
            ('reviews',     "SELECT COUNT(*) FROM reviews"),
            ('avg_rating',  "SELECT COALESCE(AVG(rating),0) FROM reviews"),
            ('itineraries', "SELECT COUNT(*) FROM saved_itineraries"),
            ('feedback',    "SELECT COUNT(*) FROM feedback"),
            ('avg_sat',     "SELECT COALESCE(AVG(satisfaction_rating),0) FROM feedback"),
        ]:
            c.execute(query); v = c.fetchone()[0]; stats[key] = round(v,2) if isinstance(v,float) else (v or 0)
        c.execute("SELECT site_name,country,COUNT(*) cnt,ROUND(AVG(rating),1) ar FROM reviews GROUP BY site_name ORDER BY cnt DESC LIMIT 10")
        stats['top_reviewed'] = c.fetchall()
        c.execute("SELECT country,COUNT(*) FROM saved_itineraries GROUP BY country ORDER BY 2 DESC LIMIT 8")
        stats['pop_countries'] = c.fetchall()
        conn.close(); return stats
    except: return {'users':0,'users_online':0,'reviews':0,'avg_rating':0,'itineraries':0,'feedback':0,'avg_sat':0,'top_reviewed':[],'pop_countries':[]}


# ─────────────────────────────────────────
#  DATA
# ─────────────────────────────────────────
@st.cache_data
def load_data():
    paths = ["dataset/Tourist_Destinations.csv","Tourist_Destinations.csv","data/Tourist_Destinations.csv"]
    df = None
    loaded_from = None
    
    # Try local paths first
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_csv(p)
                loaded_from = f"local: {p}"
                break
            except Exception as e:
                continue
    
    # if dataset folder contains CSV files, pick the largest one
    if df is None and os.path.isdir("dataset"):
        csv_files = [(f, os.path.getsize(os.path.join("dataset", f))) 
                     for f in os.listdir("dataset") if f.lower().endswith(".csv")]
        if csv_files:
            csv_files.sort(key=lambda x: x[1], reverse=True)  # Sort by size, largest first
            for fname, _ in csv_files:
                try:
                    full_path = os.path.join("dataset", fname)
                    df = pd.read_csv(full_path)
                    loaded_from = f"local: {full_path}"
                    break
                except Exception as e:
                    continue
    
    # Fall back to sample data if no CSV found
    if df is None:
        df = _sample_data()
        loaded_from = "sample_data (limited to 30 rows)"
    
    df.columns = df.columns.str.strip().str.lower().str.replace(' ','_')
    renames = {'destination_name':'site_name','destination':'site_name','avg_cost_(usd/day)':'budget_per_day',
               'avg_cost_usd/day':'budget_per_day','avg_rating':'rating','type':'site_type'}
    df = df.rename(columns={k:v for k,v in renames.items() if k in df.columns})
    for col,def_ in [('rating',4.0),('budget_per_day',100),('site_type','Cultural'),('best_season','Year Round')]:
        if col not in df.columns: df[col] = def_
    df['rating']         = pd.to_numeric(df['rating'],errors='coerce').fillna(4.0).clip(1,5)
    df['budget_per_day'] = pd.to_numeric(df['budget_per_day'],errors='coerce').fillna(100)
    df['reviews_count']  = np.random.randint(50,800,len(df))
    df['popularity']     = (df['rating'] / 5) * 0.6 + np.random.uniform(0,0.4,len(df))
    
    result_df = df.dropna(subset=['country','site_name']).reset_index(drop=True)
    return result_df

def _sample_data():
    rows = [
        ('Eiffel Tower','France','Monument',4.8,150,'Spring'),('Taj Mahal','India','Historical',4.9,80,'Winter'),
        ('Colosseum','Italy','Historical',4.7,120,'Spring'),('Great Wall','China','Historical',4.6,90,'Autumn'),
        ('Machu Picchu','Peru','Archaeological',4.8,110,'Dry Season'),('Angkor Wat','Cambodia','Religious',4.7,60,'Nov-Mar'),
        ('Alhambra','Spain','Historical',4.7,100,'Spring'),('Sagrada Familia','Spain','Religious',4.8,130,'Spring'),
        ('Acropolis','Greece','Historical',4.6,140,'Spring'),('Pyramids of Giza','Egypt','Archaeological',4.7,80,'Winter'),
        ('Santorini','Greece','Nature',4.8,200,'Summer'),('Kyoto Temples','Japan','Religious',4.9,100,'Spring'),
        ('Bali Rice Terraces','Indonesia','Nature',4.6,70,'Dry Season'),('Petra','Jordan','Archaeological',4.7,90,'Spring'),
        ('Statue of Liberty','USA','Monument',4.5,180,'Summer'),('Hagia Sophia','Turkey','Religious',4.8,110,'Spring'),
        ('Chichen Itza','Mexico','Archaeological',4.7,100,'Winter'),('Vatican Museums','Italy','Religious',4.9,160,'Spring'),
        ('Louvre Museum','France','Museum',4.8,140,'Year Round'),('Sydney Opera','Australia','Monument',4.7,200,'Year Round'),
        ('Mont Saint-Michel','France','Historical',4.6,130,'Summer'),('Stonehenge','UK','Archaeological',4.5,150,'Summer'),
        ('Neuschwanstein','Germany','Historical',4.7,120,'Summer'),('Cappadocia','Turkey','Nature',4.8,100,'Spring'),
        ('Serengeti','Tanzania','Nature',4.9,250,'June-Oct'),('Fjords','Norway','Nature',4.9,180,'Summer'),
        ('Reykjavik','Iceland','Cultural',4.7,200,'Winter'),('Fez Medina','Morocco','Cultural',4.6,70,'Spring'),
        ('Havana','Cuba','Cultural',4.5,90,'Nov-Apr'),('Varanasi Ghats','India','Religious',4.7,60,'Oct-Mar'),
    ]
    return pd.DataFrame(rows, columns=['site_name','country','site_type','rating','budget_per_day','best_season'])


# ─────────────────────────────────────────
#  GEMINI
# ─────────────────────────────────────────
@st.cache_resource
def get_model(provider, api_key, model_name):
    """Return a configured Gemini model instance."""
    try:
        if provider != "gemini":
            return None
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_name)
    except Exception as e:
        # initialization failure; log to console for debugging
        print(f"[GlobeTrek] get_model error: {e}")
        return None


def _is_quota_error(error_str):
    s = (error_str or "").lower()
    quota_markers = ["quota exceeded", "resource_exhausted", "429", "rate limit", "too many requests"]
    return any(marker in s for marker in quota_markers)


def _groq_generate(prompt, system_prompt="", temperature=0.7, max_tokens=3500):
    if not GROQ_API_KEY:
        raise RuntimeError("Missing GROQ_API_KEY")
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt or "You are a helpful travel planning assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=90
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"{resp.status_code} {resp.text[:500]}")
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Groq returned no choices.")
    return choices[0].get("message", {}).get("content", "").strip()


def _fallback_itinerary(country, interests, budget, group_size, start_date, end_date):
    days = (end_date - start_date).days + 1
    total = budget * group_size * days
    picks = interests if interests else ["Culture", "Food", "History"]
    lines = [
        "## Offline Itinerary (Fallback)",
        "",
        f"Gemini response is unavailable right now, so here is a practical {days}-day plan for **{country}**.",
        "",
        "### Trip Snapshot",
        f"- Dates: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}",
        f"- Group size: {group_size}",
        f"- Budget: ${budget}/person/day (estimated total: ${total:,.0f})",
        f"- Focus: {', '.join(picks)}",
        "",
        "### Day-by-Day Plan"
    ]
    for i in range(days):
        d = start_date + timedelta(days=i)
        theme = picks[i % len(picks)]
        est = max(25, int(budget * 0.9))
        lines.extend([
            f"#### Day {i+1} ({d.strftime('%a, %b %d')}): {theme}",
            "- Morning: Visit a top cultural landmark and arrive at opening time.",
            "- Afternoon: Explore a museum/local market, then have a regional lunch.",
            "- Evening: Take a neighborhood walk, local dinner, and cultural show if available.",
            f"- Estimated spend: ${est} per person",
            ""
        ])
    lines.extend([
        "### Practical Tips",
        "- Keep 10-15% of budget as contingency.",
        "- Use public transport/day passes where possible.",
        "- Pre-book major attractions for morning slots.",
        "",
        "### Next Step",
        "When Gemini quota resets (midnight UTC) or billing is enabled, regenerate for a fully AI-detailed version."
    ])
    return "\n".join(lines)

def gen_itinerary_ai(country, interests, budget, group_size, start_date, end_date):
    days = (end_date - start_date).days + 1
    prompt = f"""You are an expert cultural travel planner. Create an extremely detailed, practical {days}-day itinerary for {group_size} people visiting {country}.

TRAVELER PROFILE:
- Budget: ${budget} USD per person per day (Total trip budget: ${budget * group_size * days})
- Interests: {', '.join(interests)}
- Travel Dates: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}
- Group Size: {group_size}

Please provide a COMPLETE, DETAILED response covering ALL sections below. Use markdown formatting with clear headers:

# 🌍 {country} Cultural Travel Guide — {days} Days

## 📋 Trip Overview
- Best time to visit & why these dates are good/bad
- Visa requirements and entry details
- Currency, exchange tips, budget summary
- Safety rating and important warnings
- Climate & what to pack

## 📅 Day-by-Day Itinerary
For EACH of the {days} days, provide:
### Day [N]: [Theme for the day]
**Morning (8:00 AM – 12:00 PM)**
- Specific activities, exact location, how to get there, time needed, cost

**Afternoon (12:00 PM – 6:00 PM)**
- Specific activities, exact location, how to get there, time needed, cost
- Lunch recommendation: Restaurant name, cuisine, price range

**Evening (6:00 PM – 10:00 PM)**
- Specific activities or leisure
- Dinner recommendation: Restaurant name, cuisine, price range
- Evening entertainment options

**Day [N] Cost Estimate:** $X per person

## 🏛️ Top Cultural Sites & Attractions
For each major attraction (list at least 8-10), include:
- **Name** | Rating: ⭐⭐⭐⭐⭐ | Category
- Location & how to reach
- Opening hours & best time to visit
- Entry fee (adult/child/student)
- Why visit – cultural/historical significance
- Insider tip

## 🍽️ Food & Dining Guide
- 8 must-try dishes with description and price
- Top 5 restaurants with name, location, price range, specialty
- Best street food areas
- Dietary options (vegetarian, halal, vegan)
- Food safety tips

## 🏨 Accommodation Guide
By budget tier:
- **Budget** (under $50/night): 2 recommendations with names, areas, amenities
- **Mid-Range** ($50–$150/night): 2 recommendations
- **Luxury** ($150+/night): 2 recommendations
- Best neighborhoods to stay

## 🚇 Transportation Guide
- Getting there: Best flight routes, airports, travel time
- Getting around: Metro, bus, taxi, rental options with costs
- Day trips from the city: destinations & logistics
- Transport apps to download

## 💰 Complete Budget Breakdown (per person)
| Category | Budget | Mid-Range | Luxury |
|---|---|---|---|
| Accommodation | $X/night | $X/night | $X/night |
| Food | $X/day | $X/day | $X/day |
| Activities | $X/day | $X/day | $X/day |
| Transport | $X/day | $X/day | $X/day |
| **TOTAL {days} days** | **$X** | **$X** | **$X** |

## 🎭 Cultural Tips & Etiquette
- Dress code requirements
- Religious site rules
- Photography dos and don'ts
- Tipping customs
- Useful local phrases (at least 10 phrases with pronunciation)
- Social customs & taboos

## 💎 Hidden Gems & Off-the-Beaten-Path
List 5 lesser-known spots with descriptions and why they're special

## 🆘 Emergency & Practical Info
- Emergency numbers (police, ambulance, fire)
- Nearest hospitals
- Embassy/consulate contact
- Useful apps (maps, translation, transport)
- Tourist helpline

## 🧳 Packing Checklist
Organized by category (documents, clothing, electronics, health)

Make every section detailed, accurate, and genuinely useful. Include specific names of restaurants, hotels, and attractions. Provide real price estimates where possible."""

    try:
        if AI_PROVIDER == "groq":
            return _groq_generate(
                prompt,
                system_prompt="You are an expert cultural travel planner. Return structured markdown with clear sections.",
                temperature=0.7,
                max_tokens=6000
            )
        model = get_model(AI_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL)
        if not model:
            return _fallback_itinerary(country, interests, budget, group_size, start_date, end_date)
        # request as many tokens as the model will allow for long itineraries
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(
            temperature=0.7, max_output_tokens=32768
        ))
        text = response.text
        # if output appears truncated, try to continue
        if text.strip().endswith("...") or len(text) > 32000:
            try:
                cont = model.generate_content("Continue the itinerary from where it left off.",
                                              generation_config=genai.types.GenerationConfig(
                                                  temperature=0.7, max_output_tokens=16384
                                              ))
                text += "\n" + cont.text
            except Exception:
                pass
        return text
    except Exception as e:
        error_str = str(e).lower()
        if "api key" in error_str or "invalid" in error_str or "authentication" in error_str:
            if AI_PROVIDER == "groq":
                st.error("❌ **API Key Error**: Your Groq API key is invalid or not recognized.\n\nUpdate `GROQ_API_KEY` in `secrets.toml` and restart the app.")
            else:
                st.error("❌ **API Key Error**: Your Gemini API key is invalid or not recognized.\n\n**Steps to fix:**\n1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)\n2. Create a **new** API key\n3. Copy it carefully (no extra spaces)\n4. Replace `GEMINI_API_KEY` in `.streamlit/secrets.toml`\n5. Restart the app")
            return None
        elif _is_quota_error(error_str):
            if AI_PROVIDER == "groq":
                st.error("❌ **Quota Exceeded**: Your Groq key hit rate/quota limits. Upgrade your Groq plan or wait for reset.")
                st.warning("Showing fallback itinerary because Groq quota is currently exhausted.")
            else:
                st.error("❌ **Quota Exceeded**: Your API key's free tier limit has been reached.\n\n**To continue:**\n1. Go to [Google Cloud Console](https://console.cloud.google.com/)\n2. Enable **Billing** for your project\n3. Return to [Google AI Studio](https://makersuite.google.com/app/apikey) and verify billing is active\n4. Restart the app\n\n(Free tier resets daily at midnight UTC)")
                st.warning("Showing fallback itinerary because Gemini quota is currently exhausted.")
            return _fallback_itinerary(country, interests, budget, group_size, start_date, end_date)
        st.warning("Showing fallback itinerary because Gemini is temporarily unavailable.")
        return _fallback_itinerary(country, interests, budget, group_size, start_date, end_date)


def ask_chatbot(question, context="", history=None):
    sys_prompt = f"""You are GlobeBot, a friendly and knowledgeable cultural travel assistant for GlobeTrek AI.
Help users with travel planning, cultural insights, visa info, packing tips, safety advice, and destination recommendations.
Be concise, friendly, and use emojis appropriately. Context: {context}"""
    messages = []
    if history:
        for role, msg in history[-6:]:
            messages.append({'role': role, 'parts': [msg]})
    messages.append({'role': 'user', 'parts': [question]})
    try:
        if AI_PROVIDER == "groq":
            return _groq_generate(
                question,
                system_prompt=sys_prompt,
                temperature=0.6,
                max_tokens=1200
            )
        model = get_model(AI_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL)
        if not model:
            return "Chatbot unavailable — Gemini API not configured."
        chat = model.start_chat(history=messages[:-1])
        resp = chat.send_message(sys_prompt + "\n\n" + question)
        return resp.text
    except Exception as e:
        error_str = str(e).lower()
        if "quota exceeded" in error_str or "429" in error_str:
            if AI_PROVIDER == "groq":
                return """**Quota Exceeded Error**

Your Groq API key has reached rate/quota limits.

1. Check your Groq dashboard usage and limits.
2. Upgrade your plan or wait for the reset window.
3. Retry after a short delay for burst-rate limits."""
            return """**Quota Exceeded Error**

Your free Gemini API tier has reached its limit. To continue using AI features:

1. **Upgrade your plan**: Visit [Google AI Studio](https://makersuite.google.com/app/apikey) → Billing → Enable paid usage.
2. **Wait for reset**: Free limits reset daily (around midnight UTC).
3. **Check usage**: Monitor at [Google AI Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits).

Once upgraded, you can generate unlimited itineraries! 🚀"""
        return f"Sorry, I encountered an error: {str(e)}"

def gen_destination_insight(site, country, site_type):
    prompt = f"""Give a rich, engaging cultural insight about {site} in {country} (type: {site_type}).
Include: historical background (2-3 sentences), what makes it unique, best photo spots, insider tips, and nearby attractions.
Keep it under 250 words. Use emojis and markdown."""
    try:
        if AI_PROVIDER == "groq":
            return _groq_generate(
                prompt,
                system_prompt="You are a concise, engaging travel expert.",
                temperature=0.7,
                max_tokens=450
            )
        model = get_model(AI_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL)
        if not model:
            return "AI insights unavailable."
        resp = model.generate_content(prompt)
        return resp.text
    except: 
        return "AI insights unavailable due to API quota limits. Please upgrade your Gemini plan or wait for reset."


# ─────────────────────────────────────────
#  WEATHER
# ─────────────────────────────────────────
def weather_sim(country, date):
    month = date.month
    # rough climate zones
    hot = ['India','Egypt','Thailand','Mexico','Peru','Cuba','Morocco','Tanzania','Indonesia','Cambodia']
    cold = ['Norway','Iceland','Canada','Russia','Finland','Sweden']
    base = 28 if country in hot else (5 if country in cold else 18)
    seasonal = [0,-1,-1,2,5,8,10,10,7,3,-1,-2]
    t = base + seasonal[month-1] + np.random.randint(-3,3)
    icons = {(0,5):"❄️",(5,12):"🌨️",(12,18):"🌥️",(18,24):"⛅",(24,30):"🌤️",(30,50):"☀️"}
    icon = next((v for (lo,hi),v in icons.items() if lo<=t<hi), "🌡️")
    conditions = {(0,12):"Cold & Crisp",(12,18):"Cool & Pleasant",(18,24):"Mild & Comfortable",(24,30):"Warm & Sunny",(30,50):"Hot & Humid"}
    cond = next((v for (lo,hi),v in conditions.items() if lo<=t<hi), "Warm")
    return {'temp':t,'icon':icon,'cond':cond,'humidity':np.random.randint(40,75),'wind':np.random.randint(5,25),'uv':np.random.randint(2,10)}


# ─────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────
for k,v in [('uid',None),('uname',None),('fname',None),('page','login'),('chat_history',[])]:
    if k not in st.session_state: st.session_state[k] = v

init_db()


# ─────────────────────────────────────────
#  AUTH PAGES
# ─────────────────────────────────────────
def show_login():
    c1,c2,c3 = st.columns([1,1.1,1])
    with c2:
        st.markdown('<div class="auth-box fade-up">', unsafe_allow_html=True)
        st.markdown("""
        <div class="auth-logo">
            <div style="font-size:2.5rem">🌍</div>
            <div class="brand">GlobeTrek AI</div>
            <div class="tagline">Intelligent Cultural Travel Planning</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("#### 🔐 Sign In")
        username = st.text_input("Username", key="li_u", placeholder="Enter your username")
        password = st.text_input("Password", type="password", key="li_p", placeholder="Enter your password")
        c_a,c_b = st.columns(2)
        with c_a:
            if st.button("🚀 Login", use_container_width=True, type="primary"):
                if username and password:
                    ok, uid, fn = login_user(username, password)
                    if ok:
                        st.session_state.uid = uid; st.session_state.uname = username
                        st.session_state.fname = fn; st.session_state.page = 'app'
                        st.rerun()
                    else: st.error("❌ Invalid credentials.")
                else: st.warning("Fill in both fields.")
        with c_b:
            if st.button("📝 Register", use_container_width=True):
                st.session_state.page = 'register'; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def show_register():
    c1,c2,c3 = st.columns([1,1.1,1])
    with c2:
        st.markdown('<div class="auth-box fade-up">', unsafe_allow_html=True)
        st.markdown("""
        <div class="auth-logo">
            <div style="font-size:2.5rem">🌍</div>
            <div class="brand">GlobeTrek AI</div>
            <div class="tagline">Create your account</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("#### 📝 Create Account")
        c_a,c_b = st.columns(2)
        with c_a: fn = st.text_input("First Name", key="rg_fn")
        with c_b: ln = st.text_input("Last Name",  key="rg_ln")
        un  = st.text_input("Username", key="rg_u")
        em  = st.text_input("Email",    key="rg_e")
        pw  = st.text_input("Password", type="password", key="rg_p", help="Min 6 characters")
        pw2 = st.text_input("Confirm Password", type="password", key="rg_p2")
        ca,cb = st.columns(2)
        with ca:
            if st.button("✅ Create Account", use_container_width=True, type="primary"):
                if not all([un,em,pw,pw2]): st.warning("All fields required.")
                elif pw != pw2: st.error("Passwords don't match.")
                else:
                    ok,msg = register_user(un,pw,em,fn,ln)
                    if ok: st.success(msg); st.session_state.page='login'; st.rerun()
                    else: st.error(msg)
        with cb:
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.page='login'; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────
def show_app():
    df = load_data()
    touch_user_presence(st.session_state.uid)

    # ── Sidebar ──────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:1rem;background:linear-gradient(135deg,#0d3b5e,#0a2640);border-radius:14px;
                    border:1px solid #1e4d7a;margin-bottom:1rem;">
            <div style="color:#00d4aa;font-size:0.78rem;font-weight:700;letter-spacing:1px;">WELCOME BACK</div>
            <div style="color:#e2e8f0;font-size:1.1rem;font-weight:800;margin-top:0.2rem;">
                👋 {st.session_state.fname or st.session_state.uname}
            </div>
        </div>
        """, unsafe_allow_html=True)

        pages = [
            ("🏠","Dashboard"),("✈️","Plan Trip"),("🤖","AI Chatbot"),
            ("❤️","Favorites"),("⭐","Reviews"),
            ("💬","Feedback"),("📝","Travel Notes"),("👤","Profile"),("📋","History")
        ]
        nav = st.radio("", [f"{ic} {pg}" for ic,pg in pages], label_visibility="collapsed")

        st.markdown("<hr style='border-color:#1e3a5f;margin:1rem 0'>", unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1: st.metric("🌍 Sites",  len(df))
        with c2: st.metric("🗺️ Ctrs",  df['country'].nunique())
        st.markdown("<hr style='border-color:#1e3a5f;margin:1rem 0'>", unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            clear_user_presence()
            for k in ['uid','uname','fname']: st.session_state[k] = None
            st.session_state.page = 'login'; st.rerun()

    # ── Header ───────────────────────────
    st.markdown('<h1 class="main-header">🌍 GlobeTrek AI</h1>', unsafe_allow_html=True)
    st.markdown("""
    <div class="hero-shell fade-up">
        <div class="orb orb-1"></div><div class="orb orb-2"></div><div class="orb orb-3"></div>
        <span class="hero-tag">✨ AI-Powered Cultural Travel</span>
        <h3>Discover the World's Greatest Cultural Wonders</h3>
        <p>Personalised AI itineraries • Real-time community insights • Multilingual support • Smart recommendations</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Route ────────────────────────────
    page = nav.split(" ",1)[1]
    if   page == "Dashboard":    page_home(df)
    elif page == "Plan Trip":    page_plan(df)
    elif page == "AI Chatbot":   page_chatbot()
    elif page == "Favorites":    page_favorites()
    elif page == "Reviews":      page_reviews(df)
    elif page == "Feedback":     page_feedback()
    elif page == "Travel Notes": page_notes()
    elif page == "Profile":      page_profile()
    elif page == "History":      page_history()


# ─────────────────────────────────────────
#  HOME
# ─────────────────────────────────────────
def page_home(df):
    st.markdown('<h2 class="sub-header">🌟 Featured Destinations</h2>', unsafe_allow_html=True)
    if HAS_AUTOREFRESH: st_autorefresh(interval=10000, key="home_refresh")

    top3 = df.nlargest(3,'rating')
    cols = st.columns(3)
    for i,(col,(_,r)) in enumerate(zip(cols, top3.iterrows())):
        with col:
            stars = "★"*int(r['rating']) + "☆"*(5-int(r['rating']))
            st.markdown(f"""
            <div class="dest-card fade-up">
                <div class="dest-name">{r['site_name']}</div>
                <div class="dest-country">📍 {r['country']}</div>
                <div style="color:#fbbf24;font-size:1rem;margin:0.5rem 0;">{stars}</div>
                <div class="dest-meta">
                    <span class="badge badge-teal">{r.get('site_type','Cultural')}</span>&nbsp;
                    <span class="badge badge-blue">${r['budget_per_day']:.0f}/day</span>&nbsp;
                    <span class="badge badge-amber">{r.get('best_season','Year Round')}</span>
                </div>
                <div style="color:#64748b;font-size:0.8rem;margin-top:0.5rem;">
                    ⭐ {r['rating']}/5.0 · {r.get('reviews_count',0)} reviews
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"❤️ Save to Favourites", key=f"hfav{i}"):
                add_fav(st.session_state.uid, r['site_name'], r['country'], r.get('site_type',''), r['rating'])
                st.success("Added!")

    st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">📈 Live Platform Stats</h2>', unsafe_allow_html=True)
    if HAS_AUTOREFRESH:
        st.markdown("<div class='live-chip'><span class='pulse'></span>&nbsp;Live – auto-refreshes</div>", unsafe_allow_html=True)

    stats = get_stats()
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("👥 Users Online", stats.get('users_online', 0))
    c2.metric("📝 Reviews",    stats['reviews'])
    c3.metric("✈️ Trips",      stats['itineraries'])
    c4.metric("💬 Feedback",   stats['feedback'])
    c5.metric("⭐ Avg Rating", f"{stats['avg_rating']:.1f}/5" if stats['avg_rating'] else "—")

    st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">👨‍👩‍👧‍👦 Age-Wise Travel Suggestions</h2>', unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    with a1:
        st.markdown("""
        <div class="gt-card">
            <h4>🧒 Kids & Teens (8-17)</h4>
            <p><strong>Best picks:</strong> Theme culture parks, interactive museums, easy nature trails.</p>
            <p><strong>Why:</strong> Short attention spans need high-energy, visual, activity-based experiences.</p>
        </div>
        """, unsafe_allow_html=True)
    with a2:
        st.markdown("""
        <div class="gt-card">
            <h4>🧑 Young Adults (18-35)</h4>
            <p><strong>Best picks:</strong> Food trails, heritage walks, nightlife districts, photo hotspots.</p>
            <p><strong>Why:</strong> Flexible schedules and social travel style fit mixed culture + adventure plans.</p>
        </div>
        """, unsafe_allow_html=True)
    with a3:
        st.markdown("""
        <div class="gt-card">
            <h4>👴 Adults & Seniors (36+)</h4>
            <p><strong>Best picks:</strong> Relaxed cultural circuits, comfort stays, guided tours, spiritual sites.</p>
            <p><strong>Why:</strong> Prioritizes pace, safety, comfort, and deeper context over rushed checklists.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<h2 class="sub-header">✨ Why Choose GlobeTrek AI?</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="gt-card">
        <p>GlobeTrek AI transforms the way you explore the world by combining artificial intelligence with cultural discovery. Instead of generic travel plans, the platform creates personalized journeys tailored to your interests, budget, and travel style. With real-time insights, curated destinations, and smart recommendations, GlobeTrek AI helps travelers uncover hidden gems and authentic cultural experiences around the globe.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="gt-card">
        <h4>What You Get</h4>
        <p><strong>AI-Powered Trip Planning</strong> – Instantly generate personalized travel itineraries based on your preferences.</p>
        <p><strong>Cultural Discovery</strong> – Explore destinations rich in history, traditions, and local experiences.</p>
        <p><strong>Smart Recommendations</strong> – Get suggestions for places, seasons, and activities that match your travel style.</p>
        <p><strong>Community Insights</strong> – Read reviews and feedback from other travelers to make informed decisions.</p>
        <p><strong>Travel Organization Tools</strong> – Save favorites, write travel notes, and track your journey in one place.</p>
        <p><strong>Multilingual Support</strong> – Easily plan trips across countries without language barriers.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="gt-card">
        <h4>What Makes Us Unique</h4>
        <p><strong>AI-Driven Personalization</strong> – Every recommendation adapts to your interests and past activity.</p>
        <p><strong>Focus on Cultural Exploration</strong> – Not just tourist spots, but meaningful cultural experiences.</p>
        <p><strong>Integrated Travel Hub</strong> – Planning, recommendations, notes, reviews, and favorites all in one platform.</p>
        <p><strong>Hidden Gem Discovery</strong> – Discover lesser-known destinations that typical travel platforms miss.</p>
        <p><strong>User-Centered Design</strong> – A simple, intuitive dashboard designed to make trip planning effortless.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🌍 Popular Countries Snapshot")
    country_counts = df['country'].value_counts().head(10).reset_index()
    country_counts.columns = ['Country', 'Destinations']
    fig_country = px.bar(
        country_counts.sort_values('Destinations'),
        x='Destinations',
        y='Country',
        orientation='h',
        color='Destinations',
        color_continuous_scale='Tealgrn'
    )
    fig_country.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
    st.plotly_chart(fig_country, use_container_width=True)

    st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">🔍 Destination Explorer</h2>', unsafe_allow_html=True)

    c1,c2,c3 = st.columns(3)
    with c1: country_f = st.selectbox("Filter by Country",  ["All"] + sorted(df['country'].unique()))
    with c2: type_f    = st.selectbox("Filter by Type",     ["All"] + sorted(df['site_type'].unique()))
    with c3: budget_f  = st.slider("Max Budget ($/day)", 30, 300, 300, 10)

    filt = df.copy()
    if country_f != "All": filt = filt[filt['country']==country_f]
    if type_f    != "All": filt = filt[filt['site_type']==type_f]
    filt = filt[filt['budget_per_day'] <= budget_f].sort_values('rating', ascending=False)

    st.markdown(f"<p style='color:#64748b;font-size:0.9rem;'>Showing {len(filt)} destinations</p>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i,(_,r) in enumerate(filt.head(9).iterrows()):
        with cols[i%3]:
            stars = "★"*int(r['rating']) + "☆"*(5-int(r['rating']))
            st.markdown(f"""
            <div class="dest-card">
                <div class="dest-name">{r['site_name']}</div>
                <div class="dest-country">📍 {r['country']}</div>
                <div style="color:#fbbf24;font-size:0.9rem;margin:0.3rem 0;">{stars} {r['rating']:.1f}</div>
                <div class="dest-meta">
                    <span class="badge badge-teal">{r.get('site_type','Cultural')}</span>&nbsp;
                    <span class="badge badge-blue">${r['budget_per_day']:.0f}/day</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            ca,cb = st.columns(2)
            with ca:
                if st.button("❤️", key=f"fav_e_{i}"):
                    add_fav(st.session_state.uid, r['site_name'], r['country'], r.get('site_type',''), r['rating'])
                    st.toast(f"Saved {r['site_name']}!")
            with cb:
                if st.button("🔍", key=f"ins_e_{i}"):
                    with st.expander(f"AI Insight: {r['site_name']}", expanded=True):
                        with st.spinner("Generating..."):
                            insight = gen_destination_insight(r['site_name'], r['country'], r.get('site_type',''))
                        st.markdown(f"<div class='ai-response'>{insight}</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────
#  PLAN TRIP
# ─────────────────────────────────────────
def page_plan(df):
    st.markdown('<h2 class="sub-header">✈️ AI Cultural Trip Planner</h2>', unsafe_allow_html=True)

    with st.form("trip_form"):
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### 📍 Destination & Preferences")
            country   = st.selectbox("Country", sorted(df['country'].unique()))
            interests = st.multiselect("Cultural Interests",
                ['Architecture','Food & Cuisine','History','Religious Sites','Art & Museums',
                 'Nature & Landscapes','Adventure','Local Festivals','Traditional Crafts','Nightlife'],
                default=['Architecture','History'])
            accessibility = st.checkbox("♿ Accessibility-friendly options")

        with c2:
            st.markdown("#### 📅 Travel Details")
            start = st.date_input("Departure Date", datetime.now()+timedelta(days=30))
            end   = st.date_input("Return Date",    datetime.now()+timedelta(days=37))
            budget = st.number_input("Budget per Person per Day (USD $)", 20, 2000, 100, 10)
            gs     = st.number_input("Group Size", 1, 100, 2)

            st.markdown("#### ⚙️ Extra Options")
            c_a,c_b = st.columns(2)
            with c_a:
                include_hidden = st.checkbox("🔮 Include Hidden Gems", True)
                include_food   = st.checkbox("🍽️ Detailed Food Guide", True)
            with c_b:
                include_budget = st.checkbox("💰 Budget Breakdown", True)
                include_tips   = st.checkbox("🎭 Cultural Etiquette", True)

        submitted = st.form_submit_button("🚀 Generate AI Itinerary", type="primary", use_container_width=True)

    if submitted:
        if start >= end:
            st.error("Return date must be after departure date.")
            return
        days = (end-start).days+1
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("📅 Duration",    f"{days} days")
        c2.metric("👥 Group",       gs)
        c3.metric("💰 Total Budget", f"${budget*gs*days:,.0f}")
        c4.metric("💵 Per Person",   f"${budget:.0f}/day")

        # Weather preview
        st.markdown("#### 🌤️ Weather Preview")
        wc = st.columns(min(days,7))
        for i in range(min(days,7)):
            d = start + timedelta(days=i)
            w = weather_sim(country, d)
            with wc[i]:
                st.markdown(f"""
                <div class="weather-card">
                    <div style="color:#64748b;font-size:0.75rem;">{d.strftime('%a %d')}</div>
                    <div style="font-size:1.5rem">{w['icon']}</div>
                    <div class="weather-temp">{w['temp']}°C</div>
                    <div class="weather-cond">{w['cond']}</div>
                    <div style="color:#475569;font-size:0.75rem;">💧{w['humidity']}% 💨{w['wind']}km/h</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)

        # Cost estimate
        st.markdown("#### 💰 Estimated Cost Breakdown")
        total = budget * gs * days
        breakdown = {'🏨 Accommodation': total*0.38, '🍽️ Food & Dining': total*0.28,
                     '🎭 Activities':    total*0.20, '🚇 Transport':     total*0.10,
                     '🛍️ Shopping':     total*0.04}
        cc = st.columns(5)
        for col,(k,v) in zip(cc, breakdown.items()):
            col.metric(k, f"${v:,.0f}")

        # Cost breakdown table
        cost_data = []
        for category, amount in breakdown.items():
            percentage = (amount / total) * 100
            cost_data.append([category, f"${amount:,.2f}", f"{percentage:.1f}%"])
        
        cost_df = pd.DataFrame(cost_data, columns=['Category', 'Amount', 'Percentage'])
        cost_df.loc[len(cost_df)] = ['💵 TOTAL', f"${total:,.2f}", '100%']
        st.dataframe(cost_df, use_container_width=True, hide_index=True)

        # Recommended sites
        recs = df[df['country']==country].sort_values('rating', ascending=False).head(5)
        if not recs.empty:
            st.markdown("#### 🏛️ Top Sites for Your Trip")
            rc = st.columns(min(5, len(recs)))
            for col,(_,r) in zip(rc, recs.iterrows()):
                with col:
                    st.markdown(f"""
                    <div class="gt-card" style="padding:1rem;text-align:center;">
                        <div style="color:#00d4aa;font-weight:700;font-size:0.9rem;">{r['site_name']}</div>
                        <div style="color:#fbbf24;font-size:0.85rem;">{'⭐'*int(r['rating'])}</div>
                        <div style="color:#64748b;font-size:0.78rem;">{r.get('site_type','')}</div>
                        <div style="color:#0099ff;font-size:0.8rem;">${r['budget_per_day']:.0f}/day</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)

        # Generate AI itinerary
        st.markdown("#### 🤖 AI-Generated Itinerary")
        st.markdown("<div class='tip-box'><strong>⏳ Generating your personalised itinerary...</strong> This may take 20-40 seconds for a detailed response.</div>", unsafe_allow_html=True)

        with st.spinner("🌍 GlobeTrek AI is crafting your perfect cultural journey..."):
            ai_text = gen_itinerary_ai(country, interests, budget, gs, start, end)

        if ai_text:
            st.markdown(f'<div class="ai-response fade-up">{ai_text}</div>', unsafe_allow_html=True)

            c1,c2,c3 = st.columns(3)
            with c1:
                title = st.text_input("Save as:", f"{country} Trip {start.strftime('%b %Y')}", key="itin_title")
                if st.button("💾 Save Itinerary", use_container_width=True):
                    ok = save_itinerary(st.session_state.uid, title, country,
                                        {'ai_text': ai_text, 'start': str(start), 'end': str(end)},
                                        start, end, budget, gs)
                    st.success("✅ Itinerary saved!") if ok else st.error("Failed to save.")
            with c2:
                if st.button("📋 Copy to Clipboard", use_container_width=True):
                    st.code(ai_text, language="markdown")
            with c3:
                if st.button("🤖 Ask Follow-up Questions", use_container_width=True):
                    st.info("Head to the AI Chatbot tab to ask follow-up questions about your itinerary!")
        else:
            st.error("Could not generate itinerary. Check your Gemini API key, billing/quota status, and optional `GEMINI_MODEL` override in secrets/env.")


# ─────────────────────────────────────────
#  AI CHATBOT  (extra feature)
# ─────────────────────────────────────────
def page_chatbot():
    st.markdown('<h2 class="sub-header">🤖 GlobeBot — AI Travel Assistant</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="tip-box">
        <strong>🌍 GlobeBot</strong> can help with: visa info, packing tips, destination comparisons,
        cultural customs, budget planning, safety tips, and much more. Ask anything!
    </div>
    """, unsafe_allow_html=True)

    # Display history
    history = get_chat(st.session_state.uid)
    for role, msg in history:
        if role == 'user':
            st.markdown(f'<div class="chat-user">👤 <strong>You:</strong> {html.escape(msg)}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-bot">🤖 <strong>GlobeBot:</strong><br>{msg}</div>', unsafe_allow_html=True)

    st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)

    # Quick prompts
    st.markdown("**💡 Quick prompts:**")
    qc = st.columns(4)
    quick = ["Best time to visit Japan?","Visa for Schengen area?","Packing for Southeast Asia","Is it safe to travel solo?"]
    for col,q in zip(qc,quick):
        with col:
            if st.button(q, key=f"qp_{q[:10]}"):
                st.session_state['chat_input'] = q

    user_q = st.text_input("💬 Ask GlobeBot anything...", key="chat_in", 
                            value=st.session_state.get('chat_input',''),
                            placeholder="e.g., What should I pack for Morocco in December?")

    if st.button("📨 Send", type="primary") and user_q.strip():
        save_chat(st.session_state.uid, 'user', user_q)
        with st.spinner("🤖 GlobeBot is thinking..."):
            reply = ask_chatbot(user_q, history=history)
        save_chat(st.session_state.uid, 'assistant', reply)
        st.session_state['chat_input'] = ''
        st.rerun()

    if st.button("🗑️ Clear Chat History"):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM chat_history WHERE user_id=?", (st.session_state.uid,))
            conn.commit(); conn.close()
            st.rerun()
        except: pass


# ─────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────
def page_dashboard(df):
    st.markdown('<h2 class="sub-header">📊 Analytics Dashboard</h2>', unsafe_allow_html=True)
    if HAS_AUTOREFRESH: st_autorefresh(interval=8000, key="dash_refresh")
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()

    stats = get_stats()
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("👥 Users Online", stats.get('users_online', 0))
    c2.metric("📝 Reviews",     stats['reviews'])
    c3.metric("✈️ Itineraries", stats['itineraries'])
    c4.metric("💬 Feedback",    stats['feedback'])
    c5.metric("⭐ Avg Review",  f"{stats['avg_rating']:.1f}")
    c6.metric("😊 Satisfaction",f"{stats['avg_sat']:.1f}/5")

    st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)

    t1,t2,t3 = st.tabs(["📊 Destinations","🌡️ Season Analysis","👥 Community"])

    with t1:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("#### ⭐ Rating Distribution")
            rating_dist = pd.cut(df['rating'], bins=[0,1,2,3,4,5], labels=['1★', '2★', '3★', '4★', '5★']).value_counts().sort_index()
            rating_table = pd.DataFrame({
                'Rating Range': rating_dist.index,
                'Count': rating_dist.values,
                'Percentage': (rating_dist.values / len(df) * 100).round(1)
            }).reset_index(drop=True)
            fig_rating = px.bar(rating_table, x='Rating Range', y='Count', text='Count', color='Count', color_continuous_scale='Blues')
            fig_rating.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig_rating, use_container_width=True)

        with c2:
            st.markdown("#### 🏛️ Destination Types Breakdown")
            type_counts = df['site_type'].value_counts().reset_index()
            type_counts.columns = ['Type', 'Count']
            type_counts['Percentage'] = (type_counts['Count'] / len(df) * 100).round(1)
            fig_type = px.pie(type_counts.head(8), names='Type', values='Count', hole=0.45)
            fig_type.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_type, use_container_width=True)

        # Budget vs Rating table
        st.markdown("#### 💰 Budget vs Rating by Destination Type")
        budget_rating = df.groupby('site_type').agg({
            'budget_per_day': ['min', 'max', 'mean'],
            'rating': ['min', 'max', 'mean'],
            'site_name': 'count'
        }).round(2)
        budget_rating.columns = ['Min Budget ($)', 'Max Budget ($)', 'Avg Budget ($)', 'Min Rating', 'Max Rating', 'Avg Rating', 'Count']
        budget_rating = budget_rating.reset_index().rename(columns={'site_type': 'Type'})
        st.dataframe(budget_rating, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("#### 🌡️ Best Season Analysis")
        season_counts = df['best_season'].value_counts().reset_index().head(10)
        season_counts.columns = ['Season', 'Count']
        season_counts['Percentage'] = (season_counts['Count'] / len(df) * 100).round(1)
        season_counts = season_counts.sort_values('Count', ascending=False)
        fig_season = px.bar(season_counts, x='Season', y='Count', text='Count', color='Count', color_continuous_scale='Teal')
        fig_season.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig_season, use_container_width=True)

        # Top 10 budget destinations
        st.markdown("#### 💚 Most Budget-Friendly Destinations")
        cheap = df.nsmallest(10,'budget_per_day')[['site_name','country','site_type','budget_per_day','rating']].reset_index(drop=True)
        cheap.columns = ['Destination', 'Country', 'Type', 'Daily Budget ($)', 'Rating']
        if HAS_MATPLOTLIB:
            st.dataframe(
                cheap.style.background_gradient(cmap='YlOrRd', subset=['Daily Budget ($)']),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.dataframe(cheap, use_container_width=True, hide_index=True)
        
        st.markdown("#### ⭐ Highest Rated Destinations")
        top_rated = df.nlargest(10,'rating')[['site_name','country','site_type','rating','budget_per_day']].reset_index(drop=True)
        top_rated.columns = ['Destination', 'Country', 'Type', 'Rating', 'Daily Budget ($)']
        st.dataframe(top_rated, use_container_width=True, hide_index=True)

    with t3:
        stats2 = get_stats()
        if stats2['top_reviewed']:
            st.markdown("#### 🔥 Most Reviewed Destinations (by Users)")
            tr_df = pd.DataFrame(stats2['top_reviewed'], columns=['Site','Country','Reviews','Avg Rating'])
            tr_df = tr_df.sort_values('Reviews', ascending=False)
            st.dataframe(tr_df, use_container_width=True, hide_index=True)
        else:
            st.info("No community reviews yet. Be the first to review a destination!")

        if stats2['pop_countries']:
            st.markdown("#### 🌍 Most Planned Countries")
            pc_df = pd.DataFrame(stats2['pop_countries'], columns=['Country','Itineraries'])
            pc_df = pc_df.sort_values('Itineraries', ascending=False)
            pc_df['Percentage'] = (pc_df['Itineraries'] / pc_df['Itineraries'].sum() * 100).round(1)
            fig_pc = px.bar(pc_df, x='Country', y='Itineraries', text='Itineraries', color='Itineraries', color_continuous_scale='Viridis')
            fig_pc.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig_pc, use_container_width=True)


# ─────────────────────────────────────────
#  FAVORITES
# ─────────────────────────────────────────
def page_favorites():
    st.markdown('<h2 class="sub-header">❤️ My Favourites</h2>', unsafe_allow_html=True)
    favs = get_favs(st.session_state.uid)
    if not favs:
        st.info("💡 No favourites yet. Explore destinations on the Home page and tap ❤️ to save them!"); return

    st.markdown(f"<p style='color:#64748b;'>You have <strong style='color:#00d4aa;'>{len(favs)}</strong> saved destinations</p>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i,(site,country,stype,rating) in enumerate(favs):
        with cols[i%3]:
            stars = "★"*int(rating) + "☆"*(5-int(rating)) if rating else ""
            st.markdown(f"""
            <div class="dest-card">
                <div class="dest-name">{html.escape(site)}</div>
                <div class="dest-country">📍 {html.escape(country)}</div>
                <div style="color:#fbbf24;font-size:0.9rem;">{stars}</div>
                <div class="dest-meta">
                    <span class="badge badge-teal">{html.escape(stype or 'Cultural')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            ca,cb = st.columns(2)
            with ca:
                if st.button("🔍 Insight", key=f"fins{i}"):
                    with st.expander(f"About {site}", expanded=True):
                        with st.spinner("Loading..."):
                            insight = gen_destination_insight(site, country, stype or '')
                        st.markdown(f"<div class='ai-response'>{insight}</div>", unsafe_allow_html=True)
            with cb:
                if st.button("🗑️ Remove", key=f"frem{i}"):
                    rm_fav(st.session_state.uid, site); st.rerun()


# ─────────────────────────────────────────
#  REVIEWS
# ─────────────────────────────────────────
def page_reviews(df):
    st.markdown('<h2 class="sub-header">⭐ Community Reviews</h2>', unsafe_allow_html=True)
    if HAS_AUTOREFRESH: st_autorefresh(interval=7000, key="rev_refresh")
    if HAS_AUTOREFRESH:
        st.markdown("<div class='live-chip'><span class='pulse'></span>&nbsp;Live – new reviews appear automatically</div>", unsafe_allow_html=True)

    t1,t2 = st.tabs(["✍️ Write a Review","📖 Read Reviews"])

    with t1:
        c1,c2 = st.columns([2,1])
        with c1:
            site = st.selectbox("Choose Destination", sorted(df['site_name'].unique()), key="rv_site")
        with c2:
            country = df[df['site_name']==site]['country'].iloc[0] if not df[df['site_name']==site].empty else ""
            st.text_input("Country", value=country, disabled=True)

        with st.form("review_form", clear_on_submit=True):
            rating   = st.slider("⭐ Your Rating", 1, 5, 4)
            vdate    = st.date_input("📅 Visit Date (optional)", datetime.now())
            review_t = st.text_area("✍️ Your Review", height=130,
                                     placeholder="Describe your experience, tips for other travellers, highlights, what to avoid...")
            if st.form_submit_button("📤 Submit Review", type="primary", use_container_width=True):
                if not review_t.strip(): st.warning("Please write your review.")
                else:
                    ok, msg = save_review(st.session_state.uid, site, country, rating, review_t.strip(), vdate)
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)

    with t2:
        site2 = st.selectbox("View Reviews for", sorted(df['site_name'].unique()), key="rv_view")
        country2 = df[df['site_name']==site2]['country'].iloc[0] if not df[df['site_name']==site2].empty else ""
        reviews = get_reviews(site2, country2)

        if reviews:
            avg = round(np.mean([r[1] for r in reviews]), 2)
            c1,c2,c3 = st.columns(3)
            c1.metric("Total Reviews", len(reviews))
            c2.metric("Average Rating", f"{avg}/5")
            c3.metric("Sentiment", "🌟 Excellent" if avg>=4.5 else ("👍 Good" if avg>=3.5 else "😐 Mixed"))

            # Rating distribution
            rd = {1:0,2:0,3:0,4:0,5:0}
            for _,r,_,_ in reviews: rd[r] = rd.get(r,0)+1
            for star in range(5,0,-1):
                bar = int((rd[star]/len(reviews))*20)
                st.markdown(f"<div style='display:flex;align-items:center;gap:0.5rem;margin:0.15rem 0;'>"
                            f"<span style='color:#fbbf24;width:2rem;font-size:0.85rem;'>{'★'*star}</span>"
                            f"<div style='flex:1;background:#1e3a5f;border-radius:4px;height:8px;'>"
                            f"<div style='width:{bar*5}%;background:linear-gradient(90deg,#00d4aa,#0099ff);height:8px;border-radius:4px;'></div></div>"
                            f"<span style='color:#64748b;font-size:0.8rem;width:1.5rem;'>{rd[star]}</span></div>",
                            unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            for user,rate,text,date in reviews:
                stars_s = "★"*int(rate)+"☆"*(5-int(rate))
                st.markdown(f"""
                <div class="review-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="color:#e2e8f0;">{html.escape(str(user))}</strong>
                        <span style="color:#fbbf24;">{stars_s}</span>
                    </div>
                    <div style="color:#475569;font-size:0.78rem;margin:0.2rem 0;">{html.escape(str(date).split('.')[0])}</div>
                    <div style="color:#94a3b8;margin-top:0.4rem;line-height:1.6;">{html.escape(str(text or ''))}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No reviews yet for this destination. Be the first to share your experience!")


# ─────────────────────────────────────────
#  FEEDBACK
# ─────────────────────────────────────────
def page_feedback():
    st.markdown('<h2 class="sub-header">💬 App Feedback</h2>', unsafe_allow_html=True)
    if HAS_AUTOREFRESH: st_autorefresh(interval=8000, key="fb_refresh")

    t1,t2 = st.tabs(["📝 Submit Feedback","📊 Community Feed"])

    with t1:
        with st.form("fb_form", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1:
                sat = st.select_slider("How satisfied are you?",
                    options=['😞 Very Poor','😕 Poor','😐 Neutral','🙂 Good','😍 Excellent'])
            with c2:
                cat = st.selectbox("Category", ['General','Feature Request','Bug Report','Content','UX/Design','Other'])
            fb_text = st.text_area("Your feedback", height=120,
                                    placeholder="Tell us what you love, what could be improved, or any issues you've encountered...")
            if st.form_submit_button("📤 Submit Feedback", type="primary", use_container_width=True):
                if not fb_text.strip(): st.warning("Please enter your feedback.")
                else:
                    rmap = {'😞 Very Poor':1,'😕 Poor':2,'😐 Neutral':3,'🙂 Good':4,'😍 Excellent':5}
                    ok,msg = save_feedback(st.session_state.uid, rmap[sat], fb_text.strip(), cat)
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)

    with t2:
        if HAS_AUTOREFRESH:
            st.markdown("<div class='live-chip'><span class='pulse'></span>&nbsp;Live feed</div>", unsafe_allow_html=True)
        feed = get_recent_feedback(30)
        if not feed: st.info("No feedback yet — be the first!"); return

        cats = ["All"] + sorted({f[3] for f in feed if f[3]})
        c_f = st.selectbox("Filter by category", cats)
        shown = feed if c_f=="All" else [f for f in feed if f[3]==c_f]

        if shown:
            avg_s = round(np.mean([f[1] for f in shown]),2)
            c1,c2 = st.columns(2)
            c1.metric("Feedback Count", len(shown))
            c2.metric("Avg Satisfaction", f"{avg_s}/5")

        for user,rate,text,cat2,date in shown:
            stars_s = "★"*int(rate)+"☆"*(5-int(rate))
            cat_badge = f"<span class='badge badge-purple'>{html.escape(str(cat2))}</span>"
            st.markdown(f"""
            <div class="feedback-card">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong style="color:#e2e8f0;">{html.escape(str(user))}</strong>
                    <span style="color:#fbbf24;">{stars_s}</span>
                </div>
                <div style="color:#475569;font-size:0.78rem;margin:0.2rem 0;">{html.escape(str(date).split('.')[0])} · {cat_badge}</div>
                <div style="color:#94a3b8;margin-top:0.4rem;line-height:1.6;">{html.escape(str(text or ''))}</div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────
#  TRAVEL NOTES  (extra feature)
# ─────────────────────────────────────────
def page_notes():
    st.markdown('<h2 class="sub-header">📝 Travel Notes</h2>', unsafe_allow_html=True)
    st.markdown("""
    <div class="tip-box">
        <strong>✍️ Personal Travel Journal</strong> — jot down ideas, packing lists, important contacts,
        local phrases, or anything else you'd like to remember for your trips.
    </div>
    """, unsafe_allow_html=True)

    with st.form("note_form", clear_on_submit=True):
        c1,c2 = st.columns([2,1])
        with c1: n_title   = st.text_input("Note Title", placeholder="e.g., Packing list for Japan")
        with c2: n_country = st.text_input("Country (optional)", placeholder="e.g., Japan")
        n_text = st.text_area("Note", height=150, placeholder="Write your note here...")
        if st.form_submit_button("💾 Save Note", type="primary", use_container_width=True):
            if not n_title.strip(): st.warning("Please add a title.")
            elif save_note(st.session_state.uid, n_title.strip(), n_text.strip(), n_country.strip()):
                st.success("Note saved!"); st.rerun()

    notes = get_notes(st.session_state.uid)
    if not notes: st.info("No notes yet."); return

    st.markdown(f"<p style='color:#64748b;'>You have <strong style='color:#00d4aa;'>{len(notes)}</strong> notes</p>", unsafe_allow_html=True)
    for nid, title, content, country, created in notes:
        with st.expander(f"📝 {title}" + (f"  —  📍 {country}" if country else "")):
            st.markdown(f"<div style='color:#94a3b8;font-size:0.8rem;margin-bottom:0.5rem;'>📅 {created.split('.')[0]}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='color:#cbd5e1;line-height:1.7;white-space:pre-wrap;'>{html.escape(content or '')}</div>", unsafe_allow_html=True)
            if st.button("🗑️ Delete", key=f"delnote_{nid}"):
                del_note(nid, st.session_state.uid); st.rerun()


# ─────────────────────────────────────────
#  PROFILE
# ─────────────────────────────────────────
def page_profile():
    st.markdown('<h2 class="sub-header">👤 My Profile</h2>', unsafe_allow_html=True)
    user = get_user(st.session_state.uid)
    if not user: st.error("Could not load profile."); return

    uname, email, fn, ln, created = user
    full = f"{fn} {ln}".strip() or uname

    c1,c2 = st.columns([1,2])
    with c1:
        st.markdown(f"""
        <div class="gt-card" style="text-align:center;padding:2rem;">
            <div style="font-size:4rem;">👤</div>
            <div style="color:#e2e8f0;font-size:1.3rem;font-weight:800;margin-top:0.5rem;">{html.escape(full)}</div>
            <div style="color:#00d4aa;font-size:0.85rem;">@{html.escape(uname)}</div>
            <div style="color:#64748b;font-size:0.78rem;margin-top:0.3rem;">Member since {created[:10] if created else 'N/A'}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        trips = get_itineraries(st.session_state.uid)
        favs  = get_favs(st.session_state.uid)
        notes = get_notes(st.session_state.uid)
        c_a,c_b,c_c = st.columns(3)
        c_a.metric("✈️ Trips Saved",    len(trips))
        c_b.metric("❤️ Favourites",     len(favs))
        c_c.metric("📝 Travel Notes",   len(notes))

        st.markdown("#### 📋 Account Details")
        st.markdown(f"""
        <div class="gt-card">
            <p><strong>Email:</strong> {html.escape(email or '')}</p>
            <p><strong>Username:</strong> {html.escape(uname)}</p>
            <p><strong>Full Name:</strong> {html.escape(full)}</p>
        </div>
        """, unsafe_allow_html=True)

    if trips:
        st.markdown("#### ✈️ Saved Itineraries")
        for tid, title, country, sd, ed, budget, created in trips:
            st.markdown(f"""
            <div class="gt-card" style="padding:1rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="color:#00d4aa;font-weight:700;">{html.escape(title)}</div>
                        <div style="color:#64748b;font-size:0.82rem;">📍 {html.escape(country)} · {sd} → {ed} · ${budget:.0f}/day</div>
                    </div>
                    <span class="badge badge-teal">{html.escape(created[:10] if created else '')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────
#  HISTORY
# ─────────────────────────────────────────
def page_history():
    st.markdown('<h2 class="sub-header">📋 Your Travel History</h2>', unsafe_allow_html=True)

    t1,t2,t3,t4,t5 = st.tabs(["📝 Itineraries","⭐ Reviews","❤️ Favorites","💬 Chat","📄 Notes"])

    with t1:
        st.markdown("#### ✈️ Your Past Itineraries")
        itineraries = get_itineraries(st.session_state.uid)
        if itineraries:
            itin_list = []
            for itin_id, title, country, start_date, end_date, budget, created_at in itineraries:
                itin_list.append({
                    '📅 Date Created': created_at[:10] if created_at else 'N/A',
                    '🌍 Country': country,
                    '✈️ Trip': title,
                    '💰 Budget': f"${budget}/day" if budget else 'N/A',
                    '👥 Group': 'Saved'
                })
            if itin_list:
                df_itin = pd.DataFrame(itin_list)
                st.dataframe(df_itin, use_container_width=True, hide_index=True)
            else:
                st.info("No itineraries created yet. Start planning a trip!")
        else:
            st.info("📭 No itineraries yet. Head to **Plan Trip** to create your first AI itinerary!")

    with t2:
        st.markdown("#### ⭐ Your Reviews")
        reviews_list = []
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT site_name, country, rating, review_text, visit_date, created_at FROM reviews WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (st.session_state.uid,))
            reviews = c.fetchall()
            conn.close()
            
            if reviews:
                for site_name, country, rating, review_text, visit_date, created_at in reviews:
                    reviews_list.append({
                        '📅 Posted': created_at[:10] if created_at else 'N/A',
                        '📍 Destination': f"{site_name}, {country}",
                        '⭐ Rating': f"{'★'*int(rating)}{'☆'*(5-int(rating))}",
                        '💬 Review': review_text[:60] + '...' if review_text and len(review_text) > 60 else review_text or '(No comment)'
                    })
                df_reviews = pd.DataFrame(reviews_list)
                st.dataframe(df_reviews, use_container_width=True, hide_index=True)
            else:
                st.info("📭 No reviews yet. Share your travel experiences!")
        except:
            st.info("📭 No reviews yet.")

    with t3:
        st.markdown("#### ❤️ Your Saved Favorites")
        favs = get_favs(st.session_state.uid)
        if favs:
            fav_data = []
            for site_name, country, site_type, rating in favs:
                fav_data.append({
                    '📍 Destination': site_name,
                    '🌍 Country': country,
                    '🎭 Type': site_type or 'Cultural',
                    '⭐ Rating': f"{'★'*int(rating)}{'☆'*(5-int(rating))}" if rating else 'N/A'
                })
            df_favs = pd.DataFrame(fav_data)
            st.dataframe(df_favs, use_container_width=True, hide_index=True)
        else:
            st.info("❤️ No favorites saved yet. Explore destinations and add them to your favorites!")

    with t4:
        st.markdown("#### 💬 Chat History")
        history = get_chat(st.session_state.uid)
        if history:
            chat_data = []
            for role, msg in history[-30:]:
                chat_data.append({
                    '👤 Role': '🧑 You' if role == 'user' else '🤖 GlobeBot',
                    '💬 Message': msg[:80] + '...' if len(msg) > 80 else msg
                })
            df_chat = pd.DataFrame(chat_data)
            st.dataframe(df_chat, use_container_width=True, hide_index=True)
            
            if st.button("🗑️ Clear Chat History"):
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("DELETE FROM chat_history WHERE user_id=?", (st.session_state.uid,))
                    conn.commit()
                    conn.close()
                    st.success("Chat history cleared!")
                    st.rerun()
                except:
                    st.error("Failed to clear history.")
        else:
            st.info("💭 No chat history yet. Start chatting with GlobeBot!")

    with t5:
        st.markdown("#### 📄 Your Travel Notes")
        notes = get_notes(st.session_state.uid)
        if notes:
            notes_data = []
            for note_id, title, content, country, created_at in notes:
                notes_data.append({
                    '📅 Date': created_at[:10] if created_at else 'N/A',
                    '📍 Country': country or '(Multiple)',
                    '📝 Title': title,
                    '📋 Preview': content[:60] + '...' if content and len(content) > 60 else content or '(Empty)'
                })
            df_notes = pd.DataFrame(notes_data)
            st.dataframe(df_notes, use_container_width=True, hide_index=True)
        else:
            st.info("📝 No travel notes yet. Create notes while planning your trips!")


# ─────────────────────────────────────────
#  FOOTER
# ─────────────────────────────────────────
def show_footer():
    st.markdown("<hr class='gt-divider'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center;padding:1.5rem 0;color:#334155;">
        <div style="font-size:1.5rem;margin-bottom:0.3rem;">🌍</div>
        <div style="font-weight:800;font-size:1rem;background:linear-gradient(90deg,#00d4aa,#0099ff);
                    -webkit-background-clip:text;background-clip:text;color:transparent;">GlobeTrek AI</div>
        <div style="font-size:0.8rem;margin-top:0.3rem;color:#475569;">
            Intelligent Cultural Travel Planning · Powered by Gemini AI
        </div>
        <div style="font-size:0.75rem;margin-top:0.5rem;color:#334155;">
            © 2025 GlobeTrek AI · All rights reserved
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────
if   st.session_state.page == 'login':    show_login()
elif st.session_state.page == 'register': show_register()
else:                                      show_app()

show_footer()
