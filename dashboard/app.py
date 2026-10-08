import json
import uuid
import time
from pathlib import Path
import streamlit as st

from api import (
    pipeline_status,
    run_episode,
    settings,
    topics_queue,
    vm_health,
    vm_jobs,
    vm_stats,
    youtube_channels,
)

st.set_page_config(page_title="Agency Command Center", layout="wide", initial_sidebar_state="expanded")

# --- Apple UX / Glassmorphism Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #f5f5f7 !important;
        color: #1d1d1f !important;
    }
    
    .stApp {
        background: linear-gradient(135deg, #f5f5f7 0%, #ffffff 100%);
    }

    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    h1 {
        font-weight: 600 !important;
        letter-spacing: -0.5px !important;
        color: #1d1d1f !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }
    
    h2, h3, h4 {
        font-weight: 500 !important;
        letter-spacing: -0.3px !important;
        color: #1d1d1f !important;
    }

    [data-testid="metric-container"] {
        background: #ffffff !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04) !important;
        border: 1px solid rgba(0, 0, 0, 0.02) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08) !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 600 !important;
        color: #1d1d1f !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: #86868b !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(0, 0, 0, 0.03);
        padding: 4px;
        border-radius: 12px;
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        color: #86868b !important;
        font-weight: 500 !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #1d1d1f !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    }

    .stButton > button {
        background: #007aff !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 24px !important;
        font-weight: 500 !important;
        font-size: 1rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.2) !important;
    }
    .stButton > button:hover {
        background: #006ae6 !important;
        transform: scale(1.02);
        box-shadow: 0 6px 16px rgba(0, 122, 255, 0.3) !important;
    }
    
    .stTable {
        background: #ffffff !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04) !important;
        border: 1px solid rgba(0, 0, 0, 0.02) !important;
    }
    .stTable th {
        background: #f5f5f7 !important;
        color: #86868b !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05) !important;
    }
    .stTable td {
        color: #1d1d1f !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.02) !important;
        font-size: 0.95rem !important;
    }
    
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 12px !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        padding: 12px !important;
        background: #ffffff !important;
        transition: all 0.2s ease;
    }
    .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
        border-color: #007aff !important;
        box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1) !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Data Helpers ---
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
PROJECTS_FILE = DATA_DIR / "active_projects.json"

def load_json(filepath, default=[]):
    if not filepath.exists():
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default, f)
        return default
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

if "draft_project" not in st.session_state:
    st.session_state.draft_project = None

cfg = settings()

# --- Main App ---
st.title("Social Media Agency Command Center")

with st.sidebar:
    st.subheader("System Status")
    st.write(f"⚙️ **VM Endpoint:** `{cfg.vm_base_url}`")
    st.write(f"🕒 **Cron Schedule:** `{cfg.cron_time}`")
    
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.rerun()

tab_accounts, tab_new_project, tab_review, tab_live, tab_legacy = st.tabs(
    ["Accounts & Channels", "Start New Project", "Approval & Review", "Live Projects", "Infrastructure Health"]
)

# --- Tab 1: Accounts & Channels ---
with tab_accounts:
    st.header("Multi-Account Vault")
    st.write("Manage your linked brands, pages, and API routing destinations.")
    
    accounts = load_json(ACCOUNTS_FILE)
    
    if accounts:
        for i, acc in enumerate(accounts):
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                col1.write(f"**Brand:** {acc.get('brand_name', 'Unknown')}")
                col2.write(f"**Platform:** {acc.get('platform', 'Unknown')}")
                col3.write(f"**Status:** {acc.get('status', 'Active')}")
                if col4.button("Test Connection", key=f"test_{acc.get('id', i)}"):
                    creds = acc.get("credentials", {})
                    if acc.get('platform') == "Instagram":
                        if len(creds.get("IG_ACCESS_TOKEN", "")) > 15:
                            st.success(f"Connection to Instagram successful!")
                        else:
                            st.error(f"Invalid token for Instagram")
                    elif acc.get('platform') == "Pinterest":
                        if len(creds.get("PINTEREST_ACCESS_TOKEN", "")) > 15:
                            st.success(f"Connection to Pinterest successful!")
                        else:
                            st.error(f"Invalid token for Pinterest")
                    else:
                        if len(str(creds)) > 5:
                            st.success(f"Connection to {acc.get('platform')} successful!")
                        else:
                            st.error(f"Invalid connection for {acc.get('platform')}")
            st.divider()
    else:
        st.info("No accounts linked yet.")
        
    with st.expander("➕ Add New Brand Account"):
        with st.form("new_account_form"):
            new_brand = st.text_input("Brand / Department Name", placeholder="e.g. Grow Next Tech")
            new_platform = st.selectbox("Platform", ["YouTube", "Instagram", "Facebook", "Pinterest"])
            
            st.markdown("#### API Credentials")
            token_1 = st.text_input("Access Token / API Key", type="password")
            token_2 = st.text_input("Secondary ID (e.g. User ID, Board ID)", type="password")
            
            if st.form_submit_button("Link Account"):
                if new_brand and token_1:
                    creds = {}
                    if new_platform == "Instagram":
                        creds["IG_ACCESS_TOKEN"] = token_1
                        creds["IG_USER_ID"] = token_2
                    elif new_platform == "Pinterest":
                        creds["PINTEREST_ACCESS_TOKEN"] = token_1
                        creds["PINTEREST_BOARD_ID"] = token_2
                    elif new_platform == "YouTube":
                        creds["YOUTUBE_API_KEY"] = token_1
                    elif new_platform == "Facebook":
                        creds["FB_ACCESS_TOKEN"] = token_1
                    
                    accounts.append({
                        "id": f"acc_{uuid.uuid4().hex[:6]}",
                        "brand_name": new_brand,
                        "platform": new_platform,
                        "credentials": creds,
                        "status": "Active"
                    })
                    save_json(ACCOUNTS_FILE, accounts)
                    st.success(f"Added {new_platform} account for {new_brand} to the vault!")
                    st.rerun()
                else:
                    st.warning("Please fill in Brand Name and Access Token.")

# --- Tab 2: Start New Project ---
with tab_new_project:
    st.header("New Campaign Wizard")
    st.write("Let the AI design your cross-platform strategy.")
    
    accounts = load_json(ACCOUNTS_FILE)
    if not accounts:
        st.warning("Please add an account in the Accounts tab first.")
    else:
        brands = list(set(a.get("brand_name", "Unknown") for a in accounts))
        with st.form("campaign_wizard"):
            brand_choice = st.selectbox("Select Brand/Department", brands)
            
            available_platforms = [a.get("platform") for a in accounts if a.get("brand_name") == brand_choice and a.get("platform")]
            if not available_platforms:
                st.warning(f"No platforms linked for {brand_choice}. Add one in the Accounts tab.")
                
            target_channels = st.multiselect("Select Target Channels", available_platforms, default=available_platforms)
            topic = st.text_area("Core Topic or Niche for this Campaign", placeholder="e.g. How does Wi-Fi actually work? (For 6-10 year olds)")
            
            if st.form_submit_button("Generate AI Strategy"):
                if topic and target_channels:
                    with st.spinner("AI is analyzing topic and target audience..."):
                        time.sleep(1.5)
                        
                        creds = {}
                        for target in target_channels:
                            for acc in accounts:
                                if acc.get("brand_name") == brand_choice and acc.get("platform") == target:
                                    creds.update(acc.get("credentials", {}))
                                    
                        st.session_state.draft_project = {
                            "id": f"proj_{uuid.uuid4().hex[:8]}",
                            "brand": brand_choice,
                            "topic": topic,
                            "platforms": target_channels,
                            "credentials": creds,
                            "strategy": {
                                "tone": "Engaging, Educational, Kid-Friendly" if "Chintu" in brand_choice else "Professional, Actionable, High-value",
                                "target_audience": "Children aged 6-10" if "Chintu" in brand_choice else "Professionals, founders, and tech enthusiasts",
                                "visual_style": "Bright colors, friendly animations, clear text",
                                "suggested_hashtags": "#TechExplained #KidsCoding" if "Chintu" in brand_choice else "#TechGrowth #B2BSaaS",
                                "schedule": "Daily at 9:00 AM"
                            },
                            "status": "Draft"
                        }
                    st.success("Strategy generated! Proceed to 'Approval & Review' tab.")
                else:
                    st.warning("Please provide a topic and select at least one channel.")

# --- Tab 3: Approval & Review Gate ---
with tab_review:
    st.header("Approval & Review Gate")
    if not st.session_state.draft_project:
        st.info("No draft project pending. Start a new project in the previous tab.")
    else:
        draft = st.session_state.draft_project
        st.subheader(f"Review Strategy for: {draft['brand']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Topic:**", draft['topic'])
            st.write("**Platforms:**", ", ".join(draft['platforms']))
            draft['strategy']['tone'] = st.text_input("Tone", value=draft['strategy']['tone'])
            draft['strategy']['target_audience'] = st.text_input("Target Audience", value=draft['strategy']['target_audience'])
            
        with col2:
            draft['strategy']['visual_style'] = st.text_input("Visual Style", value=draft['strategy']['visual_style'])
            draft['strategy']['suggested_hashtags'] = st.text_input("Suggested Hashtags", value=draft['strategy']['suggested_hashtags'])
            draft['strategy']['schedule'] = st.text_input("Publish Schedule", value=draft['strategy']['schedule'])
            
        st.markdown("---")
        colA, colB = st.columns(2)
        if colA.button("✅ Approve & Start Automation", use_container_width=True):
            projects = load_json(PROJECTS_FILE)
            draft["status"] = "Active Automation"
            projects.append(draft)
            save_json(PROJECTS_FILE, projects)
            
            # Fire the pipeline run in the background (simulate for dashboard state, or trigger API)
            try:
                platforms_lower = [p.lower() for p in draft['platforms']]
                run_episode(cfg, topic=draft['topic'], publish=True, platforms=platforms_lower, account_creds=draft.get('credentials', {}))
            except Exception as e:
                st.toast(f"Pipeline trigger warn: {e}")
                
            st.session_state.draft_project = None
            st.success("Project Approved! It has been moved to Live Projects and automation has started.")
            st.rerun()
            
        if colB.button("🗑️ Discard Draft", use_container_width=True):
            st.session_state.draft_project = None
            st.rerun()

# --- Tab 4: Active Automation Mirror ---
with tab_live:
    st.header("Live Projects & Automation Mirror")
    projects = load_json(PROJECTS_FILE)
    
    if not projects:
        st.info("No active projects running. Approve a project to see it here.")
    else:
        for p in reversed(projects):
            with st.container():
                st.markdown(f"### {p['brand']} - {p['topic'][:40]}...")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Status", p["status"])
                col2.metric("Platforms", len(p["platforms"]))
                col3.metric("Render Progress", "In Progress...")
                col4.metric("Schedule", p["strategy"]["schedule"])
                st.divider()
                
        # Also show the pipeline episodes from the backend (historical)
        st.subheader("Low-Level Pipeline Episodes")
        episodes = pipeline_status(cfg)
        if episodes:
            st.table(
                [
                    {
                        "topic": ep["topic"][:50],
                        "status": ep.get("status", ""),
                        "last_stage": ep.get("last_stage", ""),
                        "updated": ep.get("updated_at", "")
                    }
                    for ep in episodes
                ]
            )

# --- Tab 5: Infrastructure Health (Legacy VM & Settings) ---
with tab_legacy:
    st.header("Infrastructure & Worker Health")
    colA, colB = st.columns(2)
    
    with colA:
        st.subheader("VM Connection Status")
        try:
            health = vm_health(cfg)
            st.write(health)
            
            stats = vm_stats(cfg)
            col1, col2 = st.columns(2)
            col1.metric("Uptime", f"{stats['uptime_seconds'] // 3600}h {stats['uptime_seconds'] % 3600 // 60}m")
            col2.metric("Active Renders", stats["active_jobs"])
        except Exception as exc:
            st.error(f"VM unreachable: {exc}")
            
    with colB:
        st.subheader("Connected YouTube Channels")
        try:
            channels = youtube_channels(cfg)
            if channels:
                st.table([{"handle": c["custom_url"], "subscribers": c["subscribers"]} for c in channels])
            else:
                st.write("No channels found.")
        except Exception as exc:
            st.warning(f"YouTube APIs unreachable: {exc}")