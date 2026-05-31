"""
StormBridge NL Orchestrate workflow payload helpers.

These functions are deterministic and side-effect free. The Streamlit app uses
them to preview the handoff, and the watsonx Orchestrate ADK tools use them to
return the same operational packets to an agent.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.risk_engine import calculate_action_queue, SCENARIO_CREW_COL, SCENARIO_EQUIP_COL


SCENARIO_LABELS = {
    "SCENARIO-A": "Moderate Storm",
    "SCENARIO-B": "Severe Storm",
    "SCENARIO-C": "Recovery",
}


def normalize_scenario(scenario: str | None) -> str:
    value = str(scenario or "SCENARIO-B").upper().strip()
    aliases = {
        "A": "SCENARIO-A",
        "B": "SCENARIO-B",
        "C": "SCENARIO-C",
        "MODERATE": "SCENARIO-A",
        "SEVERE": "SCENARIO-B",
        "RECOVERY": "SCENARIO-C",
    }
    return aliases.get(value, value if value in SCENARIO_LABELS else "SCENARIO-B")


def _native(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _series_to_dict(row: pd.Series, fields: list[str]) -> dict[str, Any]:
    return {field: _native(row.get(field)) for field in fields}


def get_headline_weather(data: dict[str, pd.DataFrame], scenario: str) -> pd.Series:
    scenario_key = normalize_scenario(scenario)
    weather = data["weather_alerts"][data["weather_alerts"]["scenario"] == scenario_key].copy()
    if weather.empty:
        raise ValueError(f"No weather alert found for {scenario_key}")
    return weather.sort_values("wind_kph_sustained", ascending=False).iloc[0]


def get_relevant_weather(
    data: dict[str, pd.DataFrame],
    scenario: str,
    sector: str | None = None,
) -> pd.Series:
    scenario_key = normalize_scenario(scenario)
    weather = data["weather_alerts"][data["weather_alerts"]["scenario"] == scenario_key].copy()
    if weather.empty:
        raise ValueError(f"No weather alert found for {scenario_key}")

    if sector:
        sector_weather = weather[weather["sector"] == sector]
        if not sector_weather.empty:
            return sector_weather.iloc[0]

    return weather.sort_values("wind_kph_sustained", ascending=False).iloc[0]


def get_action_queue(data: dict[str, pd.DataFrame], scenario: str) -> pd.DataFrame:
    scenario_key = normalize_scenario(scenario)
    queue = calculate_action_queue(data, scenario=scenario_key)
    if queue.empty:
        raise ValueError(f"No actionable tasks found for {scenario_key}")
    return queue


def get_selected_action(
    data: dict[str, pd.DataFrame],
    scenario: str,
    task_id: str | None = None,
) -> pd.Series:
    queue = get_action_queue(data, scenario)
    if task_id:
        match = queue[queue["task_id"] == task_id]
        if match.empty:
            raise ValueError(f"No action found for task_id={task_id}")
        return match.iloc[0]
    return queue.iloc[0]


def _scenario_delays(data: dict[str, pd.DataFrame], scenario: str, sector: str) -> pd.DataFrame:
    delays = data.get("supply_resource_delays", pd.DataFrame())
    if delays.empty:
        return delays
    return delays[
        (delays["scenario"] == scenario)
        & ((delays["sector"] == sector) | (delays["criticality"].str.upper() == "CRITICAL"))
    ].copy()


def _resource_snapshot(
    data: dict[str, pd.DataFrame],
    scenario: str,
    site_id: str,
) -> dict[str, list[dict[str, Any]]]:
    crew_col = SCENARIO_CREW_COL.get(scenario, "availability_scenario_b")
    equip_col = SCENARIO_EQUIP_COL.get(scenario, "status_scenario_b")

    crew_fields = ["crew_id", "name", "role", "cert_level", "storm_rated", crew_col, "fatigue_flag"]
    equip_fields = ["equip_id", "equip_name", "type", "fuel_pct", "last_inspection_result", equip_col]

    crews = data["crews"][data["crews"]["site_id"] == site_id].head(4)
    equipment = data["equipment"][data["equipment"]["site_id"] == site_id].head(4)

    return {
        "crews": [_series_to_dict(row, crew_fields) for _, row in crews.iterrows()],
        "equipment": [_series_to_dict(row, equip_fields) for _, row in equipment.iterrows()],
    }


def build_dispatch_packet(
    data: dict[str, pd.DataFrame],
    scenario: str = "SCENARIO-B",
    task_id: str | None = None,
) -> str:
    scenario_key = normalize_scenario(scenario)
    action = get_selected_action(data, scenario_key, task_id)
    weather = get_relevant_weather(data, scenario_key, action["sector"])
    resources = _resource_snapshot(data, scenario_key, action["site_id"])
    delays = _scenario_delays(data, scenario_key, action["sector"])

    crew_lines = [
        f"- {crew.get('crew_id')}: {crew.get('name')} ({crew.get('role')}) - {crew.get(SCENARIO_CREW_COL[scenario_key])}"
        for crew in resources["crews"]
    ] or ["- No site crew records found."]

    equip_lines = [
        f"- {item.get('equip_id')}: {item.get('equip_name')} - {item.get(SCENARIO_EQUIP_COL[scenario_key])}"
        for item in resources["equipment"]
    ] or ["- No site equipment records found."]

    delay_lines = [
        f"- {row['resource_name']}: {row['delay_hrs']} hr delay, status {row['status']}"
        for _, row in delays.head(3).iterrows()
    ] or ["- No scenario delays linked to this sector."]

    return "\n".join([
        "STORMBRIDGE DISPATCH PACKET",
        f"Scenario: {scenario_key} - {SCENARIO_LABELS[scenario_key]}",
        f"Storm: {weather.get('storm_name', 'Storm')} / {weather.get('storm_type', 'Alert')}",
        f"Site: {action['site_name']} ({action['sector']})",
        f"Task: {action['task_name']}",
        f"Priority: {action['priority']} | Risk: {action['risk_score']}/10 | Confidence: {action['confidence_score']}%",
        f"Trigger: {action.get('trigger_condition', 'N/A')}",
        f"Business risk: {action.get('business_impact', 'N/A')}",
        "",
        "Crew snapshot:",
        *crew_lines,
        "",
        "Equipment snapshot:",
        *equip_lines,
        "",
        "Supply/resource delays:",
        *delay_lines,
        "",
        "Approval control: Human approval is required before dispatch or external communication.",
    ])


def build_stakeholder_update(
    data: dict[str, pd.DataFrame],
    scenario: str = "SCENARIO-B",
    task_id: str | None = None,
) -> str:
    scenario_key = normalize_scenario(scenario)
    action = get_selected_action(data, scenario_key, task_id)
    weather = get_relevant_weather(data, scenario_key, action["sector"])

    return "\n".join([
        "DRAFT STAKEHOLDER UPDATE",
        f"StormBridge has identified {action['site_name']} as a {action['priority']} priority during {SCENARIO_LABELS[scenario_key]}.",
        f"Current alert: {weather.get('storm_name', 'Storm')} {weather.get('storm_type', '')}, severity {weather.get('severity', 'N/A')}.",
        f"Recommended action under review: {action['task_name']}.",
        f"Operational risk if delayed: {action.get('business_impact', 'N/A')}",
        "This update is a draft. It must be approved by an operations manager before release.",
    ])


def build_orchestrate_handoff(
    data: dict[str, pd.DataFrame],
    scenario: str = "SCENARIO-B",
    task_id: str | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    scenario_key = normalize_scenario(scenario)
    action = get_selected_action(data, scenario_key, task_id)
    weather = get_relevant_weather(data, scenario_key, action["sector"])
    delays = _scenario_delays(data, scenario_key, action["sector"])

    status = "ready_for_orchestrate" if approved else "awaiting_human_approval"
    workflow_steps = [
        {
            "step": "Confirm site status",
            "owner": "Operations manager",
            "status": "ready" if approved else "blocked",
            "description": f"Confirm current status for {action['site_name']} before dispatch.",
        },
        {
            "step": "Check crew and equipment availability",
            "owner": "StormBridge tool",
            "status": "ready" if approved else "blocked",
            "description": "Use scenario-specific crew and equipment status before assigning resources.",
        },
        {
            "step": "Prepare dispatch packet",
            "owner": "watsonx Orchestrate agent",
            "status": "ready" if approved else "blocked",
            "description": "Generate a controlled packet for internal response coordination.",
        },
        {
            "step": "Draft stakeholder update",
            "owner": "watsonx Orchestrate agent",
            "status": "ready" if approved else "blocked",
            "description": "Draft an EOC/stakeholder communication for manager review.",
        },
        {
            "step": "Hold for final approval",
            "owner": "Human approver",
            "status": "required",
            "description": "No crew dispatch or external message is sent automatically.",
        },
    ]

    return {
        "workflow_name": "StormBridge response coordination",
        "scenario": scenario_key,
        "scenario_label": SCENARIO_LABELS[scenario_key],
        "handoff_status": status,
        "human_approval_required": True,
        "approved_in_stormbridge": approved,
        "storm": _series_to_dict(
            weather,
            [
                "storm_name",
                "storm_type",
                "severity",
                "wind_kph_sustained",
                "wind_kph_gusts",
                "rainfall_mm_6hr",
                "zone",
                "issued_at",
                "expires_at",
            ],
        ),
        "action": _series_to_dict(
            action,
            [
                "task_id",
                "site_id",
                "site_name",
                "sector",
                "zone",
                "task_name",
                "task_status",
                "priority",
                "risk_score",
                "confidence_score",
                "resource_gap",
                "business_impact",
                "headcount_at_risk",
                "revenue_impact_hr",
            ],
        ),
        "critical_delays": [
            _series_to_dict(
                row,
                [
                    "resource_name",
                    "resource_type",
                    "delay_hrs",
                    "delay_cause_category",
                    "criticality",
                    "workaround_available",
                    "status",
                ],
            )
            for _, row in delays.head(3).iterrows()
        ],
        "workflow_steps": workflow_steps,
        "dispatch_packet": build_dispatch_packet(data, scenario_key, task_id),
        "stakeholder_update": build_stakeholder_update(data, scenario_key, task_id),
    }
