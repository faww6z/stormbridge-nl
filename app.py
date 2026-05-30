import streamlit as st

from src.data_loader import load_all_data
from src.risk_engine import calculate_action_queue
from src.report_generator import build_manager_brief

st.set_page_config(
    page_title="StormBridge NL",
    page_icon="🌩️",
    layout="wide"
)

st.title("🌩️ StormBridge NL")
st.subheader("AI Coordination Layer for Storm-Driven Operational Disruption")

st.markdown(
    """
    StormBridge NL helps Newfoundland and Labrador organizations coordinate storm-driven disruption
    across ports, utilities, mining sites, and remote industrial operations by turning scattered
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

    st.caption(
        f"Active from {weather['start_time']} to {weather['end_time']} | "
        f"Precipitation: {weather['precipitation_mm']} mm"
    )

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
        st.write(f"**Resource Gap Score:** {top_action['resource_gap']}")
        st.write(f"**Recommended Action:** {top_action['recommended_action']}")

    with right:
        st.warning("Human approval required before dispatch or external communication.")
        approve = st.button("Approve recommended action")

        if approve:
            st.success("Action approved locally. In a full deployment, this would trigger a controlled workflow.")

    st.divider()

    st.header("Crews & Equipment")

    crew_tab, equipment_tab = st.tabs(["Crews", "Equipment"])

    with crew_tab:
        st.dataframe(data["crews"], use_container_width=True)

    with equipment_tab:
        st.dataframe(data["equipment"], use_container_width=True)

    st.divider()

    st.header("watsonx.ai Manager Brief")

    st.markdown(
        """
        This brief is generated from the structured risk queue using watsonx.ai.
        The AI does not dispatch crews or send messages automatically. A human operator must approve actions first.
        """
    )

    if "manager_brief" not in st.session_state:
        st.session_state.manager_brief = ""

    if st.button("Generate manager brief with watsonx.ai"):
        with st.spinner("Generating manager brief with watsonx.ai..."):
            st.session_state.manager_brief = build_manager_brief(weather, action_queue)

    if st.session_state.manager_brief:
        st.markdown(st.session_state.manager_brief)
    else:
        st.info("Click the button above to generate the manager brief.")

except Exception as e:
    st.error("Something went wrong while loading the StormBridge prototype.")
    st.exception(e)
