import streamlit as st
import pandas as pd

from src.data_loader import load_all_data
from src.risk_engine import calculate_action_queue

st.set_page_config(
    page_title="StormBridge NL",
    page_icon="🌩️",
    layout="wide"
)

st.title("🌩️ StormBridge NL")
st.subheader("AI Coordination Layer for Storm-Driven Operational Disruption")

st.markdown(
    """
    StormBridge NL helps organizations coordinate disruption across ports, utilities,
    mining sites, manufacturing operations, and remote crews by turning scattered
    operational data into one risk-ranked action plan.
    """
)

try:
    data = load_all_data()
    action_queue = calculate_action_queue(data)

    weather = data["weather_alerts"].iloc[0]

    st.divider()

    st.header("Active Storm Alert")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Alert Type", weather["alert_type"])
    col2.metric("Severity", f"{weather['severity']}/10")
    col3.metric("Wind Speed", f"{weather['wind_kmh']} km/h")
    col4.metric("Region", weather["affected_region"])

    st.divider()

    st.header("Risk-Ranked Action Queue")

    st.dataframe(
        action_queue[
            [
                "priority",
                "risk_score",
                "confidence_score",
                "site_name",
                "sector",
                "task_name",
                "resource_gap",
                "recommended_action",
            ]
        ],
        use_container_width=True
    )

    st.divider()

    st.header("Top Priority Response")

    top_action = action_queue.iloc[0]

    left, right = st.columns([2, 1])

    with left:
        st.markdown(f"### {top_action['site_name']}")
        st.write(f"**Sector:** {top_action['sector']}")
        st.write(f"**Priority:** {top_action['priority']}")
        st.write(f"**Risk Score:** {top_action['risk_score']}/10")
        st.write(f"**Confidence Score:** {top_action['confidence_score']}%")
        st.write(f"**Recommended Action:** {top_action['recommended_action']}")

    with right:
        st.warning("Human approval required before dispatch or external communication.")
        approve = st.button("Approve recommended action")

        if approve:
            st.success("Action approved. In the full version, this would trigger the dispatch/communication workflow.")

    st.divider()

    st.header("Available Crews")

    st.dataframe(data["crews"], use_container_width=True)

    st.header("Available Equipment")

    st.dataframe(data["equipment"], use_container_width=True)

    st.divider()

    st.header("Draft Manager Brief")

    brief = f"""
    StormBridge NL has detected a {weather['alert_type']} affecting {weather['affected_region']}.

    The highest priority issue is at {top_action['site_name']} in the {top_action['sector']} sector.
    Current risk score is {top_action['risk_score']}/10 with a confidence score of {top_action['confidence_score']}%.

    Recommended next step:
    {top_action['recommended_action']}

    Human approval is required before dispatching crews or sending stakeholder communications.
    """

    st.text_area("Manager Brief Placeholder", brief, height=220)

except Exception as e:
    st.error("Something went wrong while loading the StormBridge prototype.")
    st.exception(e)
