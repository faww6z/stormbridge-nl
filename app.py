import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
from pathlib import Path
from dotenv import load_dotenv

from src.data_loader import load_all_data
from src.orchestrate_workflow import build_orchestrate_handoff
from src.risk_engine import calculate_action_queue, SCENARIO_CREW_COL, SCENARIO_EQUIP_COL
from src.report_generator import build_manager_brief

# ── Page config ────────────────────────────────────────────────────────────

st.set_page_config(page_title="StormBridge NL", page_icon="🌩️", layout="wide")

st.markdown(
    """
    <style>
    /* ── Global dark command-center theme ───────────────────────────── */

    html, body, [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.18), transparent 32%),
            radial-gradient(circle at top right, rgba(239, 68, 68, 0.10), transparent 28%),
            linear-gradient(135deg, #07111f 0%, #0b1220 45%, #111827 100%);
        color: #e5e7eb;
    }

    .block-container {
        padding-top: 2.1rem;
        padding-bottom: 2rem;
        max-width: 1260px;
    }

    [data-testid="stHeader"] {
        background: rgba(7, 17, 31, 0);
    }

    [data-testid="stToolbar"] {
        right: 1rem;
    }

    /* ── Sidebar ───────────────────────────────────────────────────── */

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #08111f 0%, #0f172a 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.18);
    }

    [data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] .stCaption {
        color: #94a3b8 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(148, 163, 184, 0.18);
    }

    /* Selectbox */
    [data-baseweb="select"] > div {
        background-color: #111827;
        border: 1px solid rgba(148, 163, 184, 0.28);
        color: #e5e7eb;
        border-radius: 12px;
    }

    /* ── Hero header ───────────────────────────────────────────────── */

    .hero-card {
        padding: 1.55rem 1.75rem;
        border-radius: 20px;
        background:
            linear-gradient(135deg, rgba(30, 64, 175, 0.30), rgba(15, 23, 42, 0.96)),
            linear-gradient(135deg, #111827, #0f172a);
        border: 1px solid rgba(96, 165, 250, 0.28);
        box-shadow:
            0 18px 45px rgba(0, 0, 0, 0.28),
            inset 0 1px 0 rgba(255, 255, 255, 0.05);
        margin-bottom: 1.1rem;
    }

    .hero-title {
        font-size: 2.35rem;
        font-weight: 850;
        color: #f8fafc;
        letter-spacing: -0.04em;
        margin-bottom: 0.25rem;
        line-height: 1.1;
    }

    .hero-subtitle {
        font-size: 0.98rem;
        color: #cbd5e1;
    }

    /* ── Alert banner ──────────────────────────────────────────────── */

    .alert-card {
        padding: 0.95rem 1.1rem;
        border-radius: 16px;
        background: linear-gradient(90deg, rgba(127, 29, 29, 0.72), rgba(30, 41, 59, 0.92));
        border: 1px solid rgba(248, 113, 113, 0.35);
        color: #fecaca;
        font-weight: 650;
        margin-bottom: 1.1rem;
        box-shadow: 0 12px 26px rgba(0, 0, 0, 0.22);
    }

    .alert-card.warning {
        background: linear-gradient(90deg, rgba(120, 53, 15, 0.75), rgba(30, 41, 59, 0.92));
        border: 1px solid rgba(251, 191, 36, 0.35);
        color: #fde68a;
    }

    .alert-card.info {
        background: linear-gradient(90deg, rgba(30, 64, 175, 0.65), rgba(30, 41, 59, 0.92));
        border: 1px solid rgba(96, 165, 250, 0.35);
        color: #bfdbfe;
    }

    /* ── KPI cards ────────────────────────────────────────────────── */

    .kpi-card {
        padding: 1.05rem 1.1rem;
        border-radius: 18px;
        background:
            linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.98));
        border: 1px solid rgba(148, 163, 184, 0.20);
        box-shadow:
            0 16px 32px rgba(0, 0, 0, 0.22),
            inset 0 1px 0 rgba(255, 255, 255, 0.04);
        min-height: 118px;
    }

    .kpi-card:hover {
        border-color: rgba(96, 165, 250, 0.45);
        transform: translateY(-1px);
        transition: all 0.15s ease;
    }

    .kpi-label {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.45rem;
        font-weight: 650;
    }

    .kpi-value {
        font-size: 1.8rem;
        font-weight: 850;
        color: #f8fafc;
        letter-spacing: -0.03em;
    }

    .kpi-note {
        font-size: 0.82rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }

    /* ── Severity/status badges ───────────────────────────────────── */

    .severity-pill {
        display: inline-block;
        padding: 0.32rem 0.72rem;
        border-radius: 999px;
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(248, 113, 113, 0.36);
        color: #fecaca;
        font-weight: 800;
        font-size: 0.82rem;
        margin-bottom: 0.45rem;
        letter-spacing: 0.03em;
    }

    .section-caption {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
    }

    /* ── Streamlit containers/cards ───────────────────────────────── */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(15, 23, 42, 0.74);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 18px;
        box-shadow: 0 14px 32px rgba(0, 0, 0, 0.18);
    }

    div[data-testid="stMetric"] {
        background: rgba(2, 6, 23, 0.34);
        border: 1px solid rgba(148, 163, 184, 0.16);
        padding: 0.72rem 0.78rem;
        border-radius: 14px;
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8;
    }

    div[data-testid="stMetricValue"] {
        color: #f8fafc;
    }

    /* ── Text styling ─────────────────────────────────────────────── */

    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
        letter-spacing: -0.02em;
    }

    p, li, label, span {
        color: inherit;
    }

    .stCaption, [data-testid="stCaptionContainer"] {
        color: #94a3b8 !important;
    }

    hr {
        border-color: rgba(148, 163, 184, 0.18);
    }

    /* ── Tabs ─────────────────────────────────────────────────────── */

    button[data-baseweb="tab"] {
        color: #94a3b8;
        font-weight: 650;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #60a5fa;
    }

    [data-baseweb="tab-highlight"] {
        background-color: #3b82f6;
    }

    /* ── Dataframes / tables ──────────────────────────────────────── */

    [data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.18);
        box-shadow: 0 12px 26px rgba(0, 0, 0, 0.16);
    }

    /* ── Inputs ───────────────────────────────────────────────────── */

    textarea {
        background-color: #0f172a !important;
        color: #e5e7eb !important;
        border: 1px solid rgba(148, 163, 184, 0.28) !important;
        border-radius: 14px !important;
    }

    /* ── Buttons ──────────────────────────────────────────────────── */

    .stButton > button {
        border-radius: 12px;
        border: 1px solid rgba(96, 165, 250, 0.35);
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #ffffff;
        font-weight: 700;
        box-shadow: 0 10px 22px rgba(37, 99, 235, 0.22);
    }

    .stButton > button:hover {
        border-color: rgba(147, 197, 253, 0.80);
        background: linear-gradient(135deg, #1d4ed8, #1e40af);
        color: #ffffff;
    }

    /* ── Expander ─────────────────────────────────────────────────── */

    .streamlit-expanderHeader {
        background-color: rgba(15, 23, 42, 0.65);
        color: #e5e7eb !important;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── watsonx availability check ─────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")
WATSONX_AVAILABLE = bool(os.getenv("IBM_API_KEY")) and bool(os.getenv("IBM_PROJECT_ID"))

# ── Constants ──────────────────────────────────────────────────────────────

SCENARIO_MAP = {
    "🌧️ Severe Storm":   "SCENARIO-B",
    "⚠️ Moderate Storm": "SCENARIO-A",
    "♻️ Recovery Phase": "SCENARIO-C",
}

PRIORITY_EMOJI = {
    "Critical": "🔴 Critical",
    "High":     "🟠 High",
    "Medium":   "🟡 Medium",
    "Low":      "🟢 Low",
}

SEVERITY_BADGE = {
    "LOW":      "🟢 LOW",
    "MODERATE": "🟡 MODERATE",
    "HIGH":     "🟠 HIGH",
    "EXTREME":  "🔴 EXTREME",
}

SECTOR_ICON = {
    "Ocean / Port Operations":          "🚢",
    "Energy / Utilities":               "⚡",
    "Mining / Remote Industrial Sites": "⛏️",
}

SCENARIO_STATUS_COL = {
    "SCENARIO-A": "scenario_a_status",
    "SCENARIO-B": "scenario_b_status",
    "SCENARIO-C": "scenario_c_status",
}

FACTOR_LABELS = {
    "contrib_weather":      "Weather Severity",
    "contrib_criticality":  "Site Criticality",
    "contrib_exposure":     "Exposure Level",
    "contrib_priority":     "Task Priority",
    "contrib_resource_gap": "Resource Gap",
}
FACTOR_COLORS = ["#0062FF", "#4589FF", "#82CFFF", "#005CE6", "#0043CE"]

WEIGHTS_MD = """
| Factor | Weight | Source |
|---|---|---|
| Weather Severity | 0.30 | Sector-specific storm alert |
| Site Criticality | 0.25 | Site configuration |
| Exposure Level | 0.15 | Road routes & helicopter access |
| Task Priority | 0.25 | Task priority score (0–100 scale) |
| Resource Gap | 0.05 | Crew & equipment availability |

**Priority thresholds:** 🔴 Critical ≥ 8.5 · 🟠 High ≥ 7.0 · 🟡 Medium ≥ 5.5 · 🟢 Low < 5.5
"""

# ── Data loading (cached) ──────────────────────────────────────────────────

@st.cache_data
def get_data() -> dict:
    return load_all_data()


def get_orchestrate_webchat_html() -> str:
    embed_path = Path(__file__).resolve().parent / "outputs" / "orchestrate_webchat_embed.html"
    if embed_path.exists():
        return embed_path.read_text(encoding="utf-8")

    orchestration_id = os.getenv("ORCHESTRATE_WEBCHAT_ORCHESTRATION_ID")
    host_url = os.getenv("ORCHESTRATE_WEBCHAT_HOST_URL")
    crn = os.getenv("ORCHESTRATE_WEBCHAT_CRN")
    agent_id = os.getenv("ORCHESTRATE_WEBCHAT_AGENT_ID")

    if not all([orchestration_id, host_url, crn, agent_id]):
        return ""

    config = {
        "orchestrationID": orchestration_id,
        "hostURL": host_url,
        "rootElementID": "root",
        "showLauncher": os.getenv("ORCHESTRATE_WEBCHAT_SHOW_LAUNCHER", "true").lower() == "true",
        "crn": crn,
        "deploymentPlatform": "ibmcloud",
        "chatOptions": {
            "agentId": agent_id,
        },
    }

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          html, body, #root {{
            min-height: 620px;
            margin: 0;
            background: #0f172a;
          }}
        </style>
      </head>
      <body>
        <div id="root"></div>
        <script>
          window.wxOConfiguration = {json.dumps(config)};
          setTimeout(function () {{
            const script = document.createElement("script");
            script.src = `${{window.wxOConfiguration.hostURL}}/wxochat/wxoLoader.js?embed=true`;
            script.addEventListener("load", function () {{
              wxoLoader.init();
            }});
            document.head.appendChild(script);
          }}, 0);
        </script>
      </body>
    </html>
    """


# ── Helpers ────────────────────────────────────────────────────────────────

def render_hero_header():
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">StormBridge NL</div>
            <div class="hero-subtitle">
                Cross-sector AI coordination for storm-driven operational disruption · IBM watsonx Hackathon 2026
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(label: str, value: str, note: str):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def with_priority_badge(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["priority"] = out["priority"].map(PRIORITY_EMOJI)
    return out


def build_site_risk_summary(data: dict, aq: pd.DataFrame, scenario_key: str) -> pd.DataFrame:
    status_col = SCENARIO_STATUS_COL.get(scenario_key, "scenario_b_status")
    sites_sub = data["sites"][[
        "site_id", "site_name", "sector", "criticality",
        "headcount_on_site", "revenue_impact_per_hr_cad",
        "road_access_routes", "helicopter_pad", status_col,
    ]].copy()

    if not aq.empty:
        agg = (
            aq.groupby("site_id")
            .agg(risk_score=("risk_score", "max"), conf_mean=("confidence_score", "mean"))
            .reset_index()
        )
        merged = sites_sub.merge(agg, on="site_id", how="left")
    else:
        merged = sites_sub.copy()
        merged["risk_score"] = 0.0
        merged["conf_mean"]  = 0.0

    merged["risk_score"] = merged["risk_score"].fillna(0.0)
    merged["conf_mean"]  = merged["conf_mean"].fillna(0.0)
    merged["confidence"] = merged["conf_mean"].apply(
        lambda x: f"{x:.0f}%" if x > 0 else "N/A"
    )
    merged["priority"] = merged["risk_score"].apply(
        lambda s: "🔴 Critical" if s >= 8.5 else
                  "🟠 High"    if s >= 7.0 else
                  "🟡 Medium"  if s >= 5.5 else
                  "🟢 Low"
    )
    merged["revenue_impact_per_hr_cad"] = merged["revenue_impact_per_hr_cad"].apply(
        lambda x: f"${int(x):,}" if pd.notna(x) else "N/A"
    )
    merged = merged.rename(columns={status_col: "scenario_status", "conf_mean": "_drop"})
    return merged.sort_values("risk_score", ascending=False).reset_index(drop=True)


def fmt_crew_avail(val: str) -> str:
    s = str(val).upper().strip()
    if s in ("AVAILABLE", "ON-SHIFT", "DISPATCHED", "STANDBY", "IN TRANSIT"):
        return f"✅ {val}"
    return f"⚠️ {val}"


def fmt_equip_status(val: str) -> str:
    s = str(val).upper()
    good_kw = ("OPERATIONAL", "ACTIVE", "STANDBY", "DEPLOYED", "DISPATCHED",
               "STABLE", "DELIVERED", "MONITORED", "AVAILABLE")
    return (f"✅ {val}" if any(k in s for k in good_kw) else f"❌ {val}")


def fmt_yn(val: str) -> str:
    s = str(val).upper().strip()
    if s == "YES": return "✅"
    if s == "NO":  return "❌"
    return val


def fmt_criticality(val: str) -> str:
    s = str(val).upper()
    if "CRITICAL" in s: return "🔴 CRITICAL"
    if "HIGH" in s:     return "🟠 HIGH"
    if "MODERATE" in s: return "🟡 MODERATE"
    return "🟢 LOW"


def make_factor_chart(aq: pd.DataFrame) -> go.Figure:
    y_labels = aq["site_name"].tolist()
    fig = go.Figure()
    for i, (col, label) in enumerate(FACTOR_LABELS.items()):
        vals = aq[col].tolist()
        fig.add_trace(go.Bar(
            name=label,
            y=y_labels, x=vals,
            orientation="h",
            marker_color=FACTOR_COLORS[i % len(FACTOR_COLORS)],
            text=[f"{v:.2f}" if v >= 0.25 else "" for v in vals],
            textposition="inside", insidetextanchor="middle",
            hovertemplate=f"<b>{label}</b><br>%{{y}}<br>Contribution: %{{x:.2f}}<extra></extra>",
        ))
    fig.update_layout(
        barmode="stack",
        xaxis_title="Risk Score Contribution",
        xaxis=dict(range=[0, 10.5]),
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.45, xanchor="center", x=0.5,
                    font=dict(size=11)),
        height=300,
        margin=dict(l=0, r=10, t=10, b=140),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🌩️ StormBridge NL")
    st.caption("AI Coordination Layer for Storm-Driven Operational Disruption")
    st.divider()

    st.subheader("📡 Scenario")
    st.selectbox(
        "Active scenario",
        list(SCENARIO_MAP.keys()),
        key="scenario",
        help="Switch between the three demo scenarios. Each loads its own data.",
    )

    st.divider()
    st.subheader("🤖 watsonx.ai")
    if WATSONX_AVAILABLE:
        st.success("Credentials found — AI brief available.", icon="✅")
    else:
        st.info("No credentials — using template brief.", icon="ℹ️")

    st.divider()
    st.subheader("🧭 Demo Flow")
    st.caption("1. Select storm scenario")
    st.caption("2. Review affected sectors")
    st.caption("3. Inspect ranked action queue")
    st.caption("4. Generate manager brief")
    st.caption("5. Approve human-reviewed actions")

    st.divider()
    st.caption("v0.2 · IBM watsonx Hackathon 2026")
    st.caption("Sectors: Ocean · Energy/Utilities · Mining")


# ── Load & compute ─────────────────────────────────────────────────────────

scenario_label = st.session_state.get("scenario", "🌧️ Severe Storm")
scenario_key   = SCENARIO_MAP.get(scenario_label, "SCENARIO-B")

try:
    data   = get_data()
    aq_raw = calculate_action_queue(data, scenario=scenario_key)
except FileNotFoundError as e:
    st.error(f"**Missing data file:** `{e}`")
    st.info("Ensure all CSV files are in the `data/` folder and restart the app.")
    st.stop()
except Exception as e:
    st.error("StormBridge NL could not load its data.")
    with st.expander("Show error details"):
        st.exception(e)
    st.stop()

# Per-sector weather for this scenario
scenario_weather = data["weather_alerts"][
    data["weather_alerts"]["scenario"] == scenario_key
].copy()

# Headline weather row (highest wind speed) for banner + brief
headline_weather = scenario_weather.sort_values("wind_kph_sustained", ascending=False).iloc[0]

top_action = aq_raw.iloc[0] if not aq_raw.empty else None

# Regenerate brief when scenario changes
if st.session_state.get("_brief_scenario") != scenario_key:
    if top_action is not None:
        st.session_state.brief_text = build_manager_brief(
            weather=headline_weather, top_action=top_action, use_watsonx=False
        )
    st.session_state._brief_scenario = scenario_key

# Reset approvals when scenario changes
if st.session_state.get("_approval_scenario") != scenario_key:
    st.session_state.approvals = {}
    st.session_state._approval_scenario = scenario_key


# ── Page header ────────────────────────────────────────────────────────────

render_hero_header()

worst_sev = headline_weather["severity"]
alert_msg = (
    f"**{scenario_label}** | {headline_weather.get('storm_name', '')} "
    f"{headline_weather.get('storm_type', '')} | "
    f"Severity: {SEVERITY_BADGE.get(str(worst_sev).upper(), worst_sev)} | "
    f"Zone: {headline_weather.get('zone', 'N/A')}"
)
sev_upper = str(worst_sev).upper()

if sev_upper == "EXTREME":
    alert_class = "alert-card"
    alert_icon = "🚨"
elif sev_upper in ["HIGH", "MODERATE"]:
    alert_class = "alert-card warning"
    alert_icon = "⚠️"
else:
    alert_class = "alert-card info"
    alert_icon = "ℹ️"

st.markdown(
    f"""
    <div class="{alert_class}">
        {alert_icon} {alert_msg}
    </div>
    """,
    unsafe_allow_html=True,
)

critical_count = int((aq_raw["priority"] == "Critical").sum()) if not aq_raw.empty else 0
high_critical_count = int(aq_raw["priority"].isin(["Critical", "High"]).sum()) if not aq_raw.empty else 0
avg_confidence = int(aq_raw["confidence_score"].mean()) if not aq_raw.empty else 0

pending_approvals = len(
    data["tasks"][
        (data["tasks"]["scenario"] == scenario_key) &
        (data["tasks"]["human_approved"].str.upper() == "NO")
    ]
)

k1, k2, k3, k4 = st.columns(4)

with k1:
    render_kpi_card("Critical Actions", str(critical_count), "Require immediate review")

with k2:
    render_kpi_card("High+ Risk Tasks", str(high_critical_count), "Prioritized in queue")

with k3:
    render_kpi_card("AI Confidence", f"{avg_confidence}%", "Average confidence score")

with k4:
    render_kpi_card("Pending Approvals", str(pending_approvals), "Human sign-off required")

st.markdown("")


# ── Tabs ───────────────────────────────────────────────────────────────────

(
    tab_storm, tab_sites, tab_queue,
    tab_crews, tab_brief, tab_approval, tab_orchestrate,
) = st.tabs([
    "Storm Alert",
    "Sites at Risk",
    "Action Queue",
    "Crews & Equipment",
    "Manager Brief",
    "Human Approval",
    "Orchestrate Workflow",
])


# ── TAB 1 · Storm Alert ─────────────────────────────────────────────────────

with tab_storm:
    scenario_row = scenario_weather.iloc[0]
    st.subheader(f"{scenario_label} — {scenario_row.get('storm_name', 'Storm Event')}")
    st.caption(
        f"Issued: `{scenario_row.get('issued_at', 'N/A')}` → "
        f"Expires: `{scenario_row.get('expires_at', 'N/A')}` · "
        f"Source: {scenario_row.get('source_agency', 'N/A')}"
    )

    st.divider()
    st.markdown("**Conditions by sector**")

    sectors_in_order = [
        "Ocean / Port Operations",
        "Energy / Utilities",
        "Mining / Remote Industrial Sites",
    ]
    col_o, col_e, col_m = st.columns(3)
    cols_map = dict(zip(sectors_in_order, [col_o, col_e, col_m]))

    for sector, col in cols_map.items():
        row = scenario_weather[scenario_weather["sector"] == sector]
        if row.empty:
            continue
        row = row.iloc[0]
        icon = SECTOR_ICON.get(sector, "🏭")
        sev  = str(row.get("severity", "")).upper()
        badge = SEVERITY_BADGE.get(sev, sev)

        with col:
            with st.container(border=True):
                st.markdown(f"**{icon} {sector.split('/')[0].strip()}**")
                st.markdown(f'<span class="severity-pill">{badge}</span>', unsafe_allow_html=True)
                st.caption("Severity")
                st.metric("Wind (sustained)", f"{row.get('wind_kph_sustained', 'N/A')} km/h")
                st.metric("Gusts",     f"{row.get('wind_kph_gusts', 'N/A')} km/h")

                # Sector-specific highlights
                wave = row.get("wave_height_m", 0)
                if pd.notna(wave) and float(wave) > 0:
                    st.metric("Wave Height", f"{wave} m")

                ice = row.get("ice_accretion_mm", 0)
                if pd.notna(ice) and float(ice) > 0:
                    st.metric("Ice Accretion", f"{ice} mm")

                vis = row.get("visibility_km", "")
                if pd.notna(vis) and str(vis) not in ("", "0"):
                    st.metric("Visibility", f"{vis} km")

                temp = row.get("temperature_c", "")
                if pd.notna(temp) and str(temp) not in ("", "0"):
                    st.metric("Temperature", f"{temp} °C")

                rain = row.get("rainfall_mm_6hr", 0)
                if pd.notna(rain) and float(rain) > 0:
                    st.metric("Rainfall (6 hr)", f"{rain} mm")

                st.caption(str(row.get("notes", ""))[:180] + "…" if len(str(row.get("notes", ""))) > 180 else str(row.get("notes", "")))


# ── TAB 2 · Sites at Risk ──────────────────────────────────────────────────

with tab_sites:
    st.subheader("Sites at Risk")
    st.caption(
        "One row per site. Risk score = highest-scoring task at that site. "
        "Sites with no assigned tasks in this scenario show 0 risk."
    )

    site_summary = build_site_risk_summary(data, aq_raw, scenario_key)

    display_cols = [
        "site_name", "sector", "criticality", "headcount_on_site",
        "revenue_impact_per_hr_cad", "scenario_status",
        "risk_score", "confidence", "priority",
    ]
    st.dataframe(
        site_summary[display_cols],
        use_container_width=True, hide_index=True,
        column_config={
            "site_name":               st.column_config.TextColumn("Site"),
            "sector":                  st.column_config.TextColumn("Sector"),
            "criticality":             st.column_config.TextColumn("Criticality"),
            "headcount_on_site":       st.column_config.NumberColumn("Personnel on Site"),
            "revenue_impact_per_hr_cad": st.column_config.TextColumn("Revenue at Risk /hr"),
            "scenario_status":         st.column_config.TextColumn("Current Status"),
            "risk_score":              st.column_config.ProgressColumn(
                                           "Risk Score", min_value=0, max_value=10, format="%.2f"
                                       ),
            "confidence":              st.column_config.TextColumn("Confidence"),
            "priority":                st.column_config.TextColumn("Priority"),
        },
    )

    # Total personnel at risk
    if not aq_raw.empty:
        critical_sites = site_summary[site_summary["risk_score"] >= 7.0]
        total_personnel = critical_sites["headcount_on_site"].sum()
        if total_personnel > 0:
            st.warning(
                f"**{int(total_personnel)} personnel** are at sites with High or Critical risk "
                f"in this scenario.",
                icon="⚠️",
            )


# ── TAB 3 · Action Queue ───────────────────────────────────────────────────

with tab_queue:
    st.subheader("Risk-Ranked Action Queue")
    st.caption("Tasks for this scenario, ordered by composite risk score.")

    if aq_raw.empty:
        st.info("No tasks found for this scenario.", icon="ℹ️")
    else:
        # Add status display column
        aq_display = with_priority_badge(aq_raw).copy()

        def fmt_task_status(s: str) -> str:
            su = s.upper()
            if "PENDING" in su:   return f"🔴 {s}"
            if "IN PROGRESS" in su: return f"🟡 {s}"
            if "COMPLETED" in su: return f"✅ {s}"
            return s

        aq_display["task_status_fmt"] = aq_display["task_status"].apply(fmt_task_status)

        st.dataframe(
            aq_display[[
                "priority", "risk_score", "confidence_score",
                "site_name", "sector", "task_name",
                "task_status_fmt", "resource_gap",
            ]],
            use_container_width=True, hide_index=True,
            column_config={
                "priority":          st.column_config.TextColumn("Priority"),
                "risk_score":        st.column_config.ProgressColumn(
                                         "Risk Score", min_value=0, max_value=10, format="%.2f"
                                     ),
                "confidence_score":  st.column_config.NumberColumn("Confidence", format="%d%%"),
                "site_name":         st.column_config.TextColumn("Site"),
                "sector":            st.column_config.TextColumn("Sector"),
                "task_name":         st.column_config.TextColumn("Task", width="large"),
                "task_status_fmt":   st.column_config.TextColumn("Status"),
                "resource_gap":      st.column_config.NumberColumn("Resource Gap", format="%d /10"),
            },
        )

        st.divider()
        st.subheader("Risk Score Breakdown")
        st.caption(
            "Each bar shows how much each factor contributed to the total score. "
            "Hover for exact values."
        )
        st.plotly_chart(make_factor_chart(aq_raw), use_container_width=True)

        with st.expander("How scores are calculated"):
            st.markdown(WEIGHTS_MD)
            st.markdown(
                "**Exposure Level** is derived from the number of access routes and "
                "helicopter pad availability (fewer routes = higher exposure). "
                "**Task Priority** uses the task's 0–100 priority score, divided by 10."
            )

        # Business impact panel
        with st.expander("Business impact if actions are delayed"):
            for _, row in aq_raw.iterrows():
                if row["business_impact"]:
                    badge = PRIORITY_EMOJI.get(row["priority"], row["priority"])
                    st.markdown(
                        f"**{row['site_name']}** ({badge})\n\n"
                        f"> {row['business_impact']}"
                    )
                    st.caption(f"Task: {row['task_name']}")
                    st.divider()


# ── TAB 4 · Crews & Equipment ──────────────────────────────────────────────

with tab_crews:
    crew_col  = SCENARIO_CREW_COL.get(scenario_key, "availability_scenario_b")
    equip_col = SCENARIO_EQUIP_COL.get(scenario_key, "status_scenario_b")

    col_c, col_e = st.columns(2)

    with col_c:
        st.subheader("👷 Crews")
        crews_disp = data["crews"].copy()
        crews_disp["availability"] = crews_disp[crew_col].apply(fmt_crew_avail)
        crews_disp["storm_rated"]  = crews_disp["storm_rated"].apply(fmt_yn)
        crews_disp["fatigue_flag"] = crews_disp["fatigue_flag"].apply(
            lambda v: "⚠️ Yes" if str(v).upper() == "YES" else ""
        )
        st.dataframe(
            crews_disp[[
                "crew_id", "name", "role", "sector",
                "cert_level", "storm_rated", "availability", "fatigue_flag",
            ]],
            use_container_width=True, hide_index=True,
            column_config={
                "crew_id":    st.column_config.TextColumn("ID"),
                "name":       st.column_config.TextColumn("Name"),
                "role":       st.column_config.TextColumn("Role"),
                "sector":     st.column_config.TextColumn("Sector"),
                "cert_level": st.column_config.TextColumn("Cert"),
                "storm_rated":  st.column_config.TextColumn("Storm Rated"),
                "availability": st.column_config.TextColumn("Availability"),
                "fatigue_flag": st.column_config.TextColumn("Fatigue"),
            },
        )

    with col_e:
        st.subheader("🔧 Equipment")
        equip_disp = data["equipment"].copy()
        equip_disp["status"] = equip_disp[equip_col].apply(fmt_equip_status)
        equip_disp["fuel_pct"] = equip_disp["fuel_pct"].apply(
            lambda v: f"{v}%" if pd.notna(v) and str(v).strip() not in ("", "N/A") else "N/A"
        )
        st.dataframe(
            equip_disp[[
                "equip_id", "equip_name", "type", "sector",
                "fuel_pct", "last_inspection_result", "status", "max_wind_kph",
            ]],
            use_container_width=True, hide_index=True,
            column_config={
                "equip_id":               st.column_config.TextColumn("ID"),
                "equip_name":             st.column_config.TextColumn("Equipment"),
                "type":                   st.column_config.TextColumn("Type"),
                "sector":                 st.column_config.TextColumn("Sector"),
                "fuel_pct":               st.column_config.TextColumn("Fuel"),
                "last_inspection_result": st.column_config.TextColumn("Last Inspection"),
                "status":                 st.column_config.TextColumn("Status"),
                "max_wind_kph":           st.column_config.TextColumn("Max Wind"),
            },
        )

    # Resource warnings
    st.divider()
    n_crew_unavail = (
        data["crews"][crew_col]
        .apply(lambda v: str(v).upper().strip() not in ("AVAILABLE", "ON-SHIFT", "DISPATCHED", "STANDBY"))
        .sum()
    )
    fatigue_count = (data["crews"]["fatigue_flag"].str.upper() == "YES").sum()
    non_storm_count = (data["crews"]["storm_rated"].str.upper() == "NO").sum()

    if n_crew_unavail > 0 or fatigue_count > 0:
        parts = []
        if n_crew_unavail > 0:
            parts.append(f"**{n_crew_unavail} crew(s)** unavailable/stood-down")
        if fatigue_count > 0:
            parts.append(f"**{fatigue_count} crew(s)** flagged for fatigue")
        if non_storm_count > 0:
            parts.append(f"**{non_storm_count}** not storm-rated (restricted to safe work only)")
        st.warning(" · ".join(parts), icon="⚠️")

    # Supply & Resource Delays
    st.divider()
    st.subheader("📦 Supply & Resource Delays")
    delays = data["supply_resource_delays"][
        data["supply_resource_delays"]["scenario"] == scenario_key
    ].copy()

    if delays.empty:
        st.info("No supply or resource delays recorded for this scenario.", icon="ℹ️")
    else:
        delays["criticality"]         = delays["criticality"].apply(fmt_criticality)
        delays["workaround_available"] = delays["workaround_available"].apply(
            lambda v: "✅ Yes" if str(v).upper() == "YES"
                      else ("⚠️ Partial" if str(v).upper() == "PARTIAL" else "❌ None")
        )
        delays["cost_impact_cad"] = delays["cost_impact_cad"].apply(
            lambda v: f"${int(v):,}" if pd.notna(v) and str(v).strip() not in ("", "0", "0.0") else "—"
        )
        st.dataframe(
            delays[[
                "resource_name", "sector", "delay_hrs",
                "delay_cause_category", "criticality",
                "workaround_available", "cost_impact_cad", "status",
            ]],
            use_container_width=True, hide_index=True,
            column_config={
                "resource_name":       st.column_config.TextColumn("Resource"),
                "sector":              st.column_config.TextColumn("Sector"),
                "delay_hrs":           st.column_config.NumberColumn("Delay (hrs)", format="%d"),
                "delay_cause_category":st.column_config.TextColumn("Cause"),
                "criticality":         st.column_config.TextColumn("Criticality"),
                "workaround_available":st.column_config.TextColumn("Workaround"),
                "cost_impact_cad":     st.column_config.TextColumn("Cost Impact"),
                "status":              st.column_config.TextColumn("Status"),
            },
        )

        critical_delays = delays[delays["criticality"].str.contains("CRITICAL", na=False)]
        if not critical_delays.empty:
            st.error(
                f"**{len(critical_delays)} CRITICAL delay(s)** with no workaround available. "
                "See details above.",
                icon="🚨",
            )


# ── TAB 5 · Manager Brief ──────────────────────────────────────────────────

with tab_brief:
    st.subheader("Manager Brief")
    st.caption(
        "Operational summary for managers. "
        "Must be reviewed and approved before distribution."
    )

    if top_action is None:
        st.info("No tasks available for this scenario — brief cannot be generated.", icon="ℹ️")
    else:
        if "brief_text" not in st.session_state:
            st.session_state.brief_text = build_manager_brief(
                weather=headline_weather, top_action=top_action, use_watsonx=False
            )

        if WATSONX_AVAILABLE:
            if st.button("🤖 Generate with watsonx.ai (IBM Granite)", type="primary"):
                with st.spinner("Calling watsonx.ai…"):
                    st.session_state.brief_text = build_manager_brief(
                        weather=headline_weather, top_action=top_action, use_watsonx=True
                    )
        else:
            st.info(
                "**watsonx.ai not configured** — showing template brief. "
                "Add `IBM_API_KEY` and `IBM_PROJECT_ID` to `.env` for AI generation.",
                icon="ℹ️",
            )

        st.text_area(
            "Draft brief (editable before distribution)",
            value=st.session_state.brief_text,
            height=320,
        )

        # Show pending comms tasks for this scenario
        comms_pending = data["tasks"][
            (data["tasks"]["scenario"] == scenario_key) &
            (data["tasks"]["site_id"] == "ALL") &
            (data["tasks"]["human_approved"].str.upper() == "NO")
        ]
        if not comms_pending.empty:
            for _, ct in comms_pending.iterrows():
                st.warning(
                    f"**{ct['task_name']}** is `{ct['task_status']}` — "
                    "this brief must be approved in the Human Approval tab before dispatch.",
                    icon="🔔",
                )

        st.caption(
            "⚠️ Human review required. "
            "No brief or dispatch should be sent without operations manager sign-off."
        )


# ── TAB 6 · Human Approval Queue ──────────────────────────────────────────

with tab_approval:
    st.subheader("Human Approval Queue")
    st.caption(
        "Responsible AI: no automated dispatch or stakeholder communication is triggered "
        "without explicit human approval."
    )

    if "approvals" not in st.session_state:
        st.session_state.approvals = {}

    # ── Section A: System-tracked pending tasks (from tasks CSV) ──────────
    system_pending = data["tasks"][
        (data["tasks"]["scenario"] == scenario_key) &
        (data["tasks"]["human_approved"].str.upper() == "NO")
    ].copy()

    if not system_pending.empty:
        st.markdown("#### 🔔 Pending System Approvals")
        st.caption("These actions are tracked by StormBridge and awaiting sign-off.")
        for _, task in system_pending.iterrows():
            task_key = f"sys_{task['task_id']}"
            approved = st.session_state.approvals.get(task_key, False)
            with st.container(border=True):
                left, right = st.columns([3, 1])
                with left:
                    st.markdown(f"#### {task['task_name']}")
                    st.write(f"**Sector:** {task['sector']} | **Status:** `{task['task_status']}`")
                    if str(task.get("business_impact_if_delayed", "")).strip():
                        st.write(f"**Risk if delayed:** {task['business_impact_if_delayed']}")
                with right:
                    if approved:
                        st.success("✅ Approved")
                    else:
                        if st.button("Approve", key=f"btn_{task_key}", type="primary"):
                            st.session_state.approvals[task_key] = True
                            st.rerun()

        st.divider()

    # ── Section B: Critical / High risk-queue actions ─────────────────────
    if not aq_raw.empty:
        critical_high = aq_raw[aq_raw["priority"].isin(["Critical", "High"])].copy()

        if not critical_high.empty:
            st.markdown("#### 🎯 Critical & High Priority Actions")
            st.caption("Actions from the risk queue requiring confirmation before field deployment.")

            for _, row in critical_high.iterrows():
                task_key = f"rq_{row['task_id']}"
                badge    = PRIORITY_EMOJI.get(row["priority"], row["priority"])
                approved = st.session_state.approvals.get(task_key, False)

                with st.container(border=True):
                    left, right = st.columns([3, 1])
                    with left:
                        st.markdown(f"#### {row['site_name']}")
                        st.markdown(
                            f"**Priority:** {badge} | "
                            f"**Risk:** {row['risk_score']}/10 | "
                            f"**Confidence:** {row['confidence_score']}%"
                        )
                        st.write(f"**Sector:** {row['sector']} · **Zone:** {row['zone']}")
                        st.write(f"**Task:** {row['task_name']}")
                        st.write(f"**Status:** `{row['task_status']}`")
                        if row["headcount_at_risk"]:
                            st.write(f"**Personnel on site:** {row['headcount_at_risk']}")
                        if row.get("business_impact", "").strip():
                            with st.expander("Business impact if delayed"):
                                st.write(row["business_impact"])
                    with right:
                        if approved:
                            st.success("✅ Approved")
                        elif "COMPLETED" in str(row["task_status"]).upper():
                            st.success("✅ Pre-approved")
                        else:
                            if st.button(
                                "Approve", key=f"btn_{task_key}", type="primary"
                            ):
                                st.session_state.approvals[task_key] = True
                                st.rerun()

        elif system_pending.empty:
            st.success(
                f"No Critical or High priority actions require approval for the "
                f"**{scenario_label}** scenario.",
                icon="✅",
            )

    # ── Progress ───────────────────────────────────────────────────────────
    total_approvable = len(system_pending) + (
        len(critical_high) if not aq_raw.empty and "critical_high" in dir() else 0
    )
    approved_count = sum(1 for v in st.session_state.approvals.values() if v)

    if total_approvable > 0:
        st.divider()
        st.progress(approved_count / total_approvable)
        st.caption(f"{approved_count} of {total_approvable} actions approved.")

        if approved_count == total_approvable:
            st.success(
                "✅ All actions approved. In production, this would trigger crew dispatch "
                "and stakeholder communications via IBM watsonx Orchestrate.",
                icon="✅",
            )


# ── TAB 7 · watsonx Orchestrate Handoff ───────────────────────────────────

with tab_orchestrate:
    st.subheader("watsonx Orchestrate Handoff")
    st.caption(
        "Controlled workflow payload for the response coordinator agent. "
        "The handoff stays blocked until human approval is recorded."
    )

    if top_action is None:
        st.info("No action is available for this scenario.", icon="ℹ️")
    else:
        candidate_actions = aq_raw[aq_raw["priority"].isin(["Critical", "High"])].copy()
        if candidate_actions.empty:
            candidate_actions = aq_raw.copy()

        selected_task_id = st.selectbox(
            "Action to hand off",
            candidate_actions["task_id"].tolist(),
            format_func=lambda task_id: (
                f"{task_id} · "
                f"{candidate_actions[candidate_actions['task_id'] == task_id].iloc[0]['site_name']} · "
                f"{candidate_actions[candidate_actions['task_id'] == task_id].iloc[0]['priority']}"
            ),
        )

        selected_action = candidate_actions[
            candidate_actions["task_id"] == selected_task_id
        ].iloc[0]

        system_pending_for_scenario = data["tasks"][
            (data["tasks"]["scenario"] == scenario_key)
            & (data["tasks"]["human_approved"].str.upper() == "NO")
        ].copy()
        pending_approval_keys = [
            f"sys_{task_id}" for task_id in system_pending_for_scenario["task_id"].tolist()
        ]
        pending_system_approved = all(
            st.session_state.approvals.get(key, False) for key in pending_approval_keys
        ) if pending_approval_keys else True

        action_already_approved = (
            str(selected_action.get("human_approved", "")).upper() == "YES"
            or "COMPLETED" in str(selected_action.get("task_status", "")).upper()
            or st.session_state.approvals.get(f"rq_{selected_task_id}", False)
        )

        approved_for_handoff = bool(action_already_approved and pending_system_approved)

        payload = build_orchestrate_handoff(
            data=data,
            scenario=scenario_key,
            task_id=selected_task_id,
            approved=approved_for_handoff,
        )

        status_col, agent_col, guardrail_col = st.columns(3)
        with status_col:
            st.metric("Handoff Status", payload["handoff_status"])
        with agent_col:
            st.metric("Target Agent", os.getenv("ORCHESTRATE_AGENT_NAME", "stormbridge_response_coordinator"))
        with guardrail_col:
            st.metric("Approval Gate", "Open" if approved_for_handoff else "Blocked")

        if approved_for_handoff:
            st.success(
                "This action is ready for an Orchestrate response workflow. "
                "In production, the agent would prepare controlled dispatch and communication steps.",
                icon="✅",
            )
        else:
            st.warning(
                "The Orchestrate handoff is blocked until pending human approvals are completed.",
                icon="⚠️",
            )

        webchat_html = get_orchestrate_webchat_html()
        if webchat_html:
            with st.expander("Live Orchestrate Webchat", expanded=True):
                components.html(webchat_html, height=680, scrolling=True)
        else:
            st.info(
                "Live webchat embed is not configured locally. Generate it with "
                "`orchestrate channels webchat embed --agent-name stormbridge_response_coordinator --env draft` "
                "and save it to `outputs/orchestrate_webchat_embed.html`, or set the "
                "`ORCHESTRATE_WEBCHAT_*` variables in `.env`.",
                icon="ℹ️",
            )

        st.markdown("#### Workflow Steps")
        st.dataframe(
            pd.DataFrame(payload["workflow_steps"]),
            width="stretch",
            hide_index=True,
            column_config={
                "step": st.column_config.TextColumn("Step"),
                "owner": st.column_config.TextColumn("Owner"),
                "status": st.column_config.TextColumn("Status"),
                "description": st.column_config.TextColumn("Description", width="large"),
            },
        )

        packet_tab, update_tab, payload_tab = st.tabs([
            "Dispatch Packet",
            "Stakeholder Update",
            "Tool Payload",
        ])

        with packet_tab:
            st.text_area(
                "Dispatch packet draft",
                value=payload["dispatch_packet"],
                height=300,
            )

        with update_tab:
            st.text_area(
                "Stakeholder update draft",
                value=payload["stakeholder_update"],
                height=240,
            )

        with payload_tab:
            compact_payload = {
                "workflow_name": payload["workflow_name"],
                "scenario": payload["scenario"],
                "handoff_status": payload["handoff_status"],
                "human_approval_required": payload["human_approval_required"],
                "approved_in_stormbridge": payload["approved_in_stormbridge"],
                "storm": payload["storm"],
                "action": payload["action"],
                "critical_delays": payload["critical_delays"],
                "workflow_steps": payload["workflow_steps"],
            }
            st.code(json.dumps(compact_payload, indent=2), language="json")

        st.caption(
            "Live deployment uses the ADK tool package in `orchestrate_tools/`. "
            "The app preview is intentionally side-effect free."
        )
