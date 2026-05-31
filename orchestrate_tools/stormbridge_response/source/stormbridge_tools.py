"""
watsonx Orchestrate ADK tools for StormBridge NL.

The tools return drafts and workflow payloads only. They do not dispatch crews,
send messages, or change operational state.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


try:
    from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
except ImportError:  # Allows local smoke tests without the ADK installed.
    class ToolPermission:
        READ_ONLY = "read_only"

    def tool(*_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from src.data_loader import load_all_data
from src.orchestrate_workflow import (
    build_dispatch_packet,
    build_orchestrate_handoff,
    build_stakeholder_update,
    get_action_queue,
    get_relevant_weather,
    get_selected_action,
    normalize_scenario,
)
from src.report_generator import build_manager_brief


def _json(data) -> str:
    return json.dumps(data, indent=2, default=str)


def _native(value):
    if hasattr(value, "item"):
        return value.item()
    return value


def _row_json(row, fields: list[str]) -> str:
    return _json({field: _native(row.get(field)) for field in fields})


@tool(
    name="get_stormbridge_risk_queue",
    description="Return the StormBridge risk-ranked action queue for a scenario.",
    permission=ToolPermission.READ_ONLY,
)
def get_stormbridge_risk_queue(scenario: str = "SCENARIO-B") -> str:
    data = load_all_data()
    scenario_key = normalize_scenario(scenario)
    queue = get_action_queue(data, scenario_key)
    fields = [
        "task_id",
        "site_name",
        "sector",
        "task_name",
        "priority",
        "risk_score",
        "confidence_score",
        "resource_gap",
        "business_impact",
    ]
    return queue[fields].head(10).to_json(orient="records", indent=2)


@tool(
    name="get_stormbridge_top_priority",
    description="Return the top priority StormBridge action for a scenario.",
    permission=ToolPermission.READ_ONLY,
)
def get_stormbridge_top_priority(scenario: str = "SCENARIO-B") -> str:
    data = load_all_data()
    action = get_selected_action(data, normalize_scenario(scenario))
    fields = [
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
    ]
    return _row_json(action, fields)


@tool(
    name="draft_stormbridge_manager_brief",
    description="Draft a manager brief for a StormBridge scenario and optional task ID.",
    permission=ToolPermission.READ_ONLY,
)
def draft_stormbridge_manager_brief(
    scenario: str = "SCENARIO-B",
    task_id: str = "",
) -> str:
    data = load_all_data()
    scenario_key = normalize_scenario(scenario)
    action = get_selected_action(data, scenario_key, task_id or None)
    weather = get_relevant_weather(data, scenario_key, action["sector"])
    return build_manager_brief(weather=weather, top_action=action, use_watsonx=False)


@tool(
    name="draft_stormbridge_dispatch_packet",
    description="Draft an internal dispatch packet for a StormBridge action.",
    permission=ToolPermission.READ_ONLY,
)
def draft_stormbridge_dispatch_packet(
    scenario: str = "SCENARIO-B",
    task_id: str = "",
) -> str:
    data = load_all_data()
    return build_dispatch_packet(
        data=data,
        scenario=normalize_scenario(scenario),
        task_id=task_id or None,
    )


@tool(
    name="draft_stormbridge_stakeholder_update",
    description="Draft an external stakeholder update for a StormBridge action.",
    permission=ToolPermission.READ_ONLY,
)
def draft_stormbridge_stakeholder_update(
    scenario: str = "SCENARIO-B",
    task_id: str = "",
) -> str:
    data = load_all_data()
    return build_stakeholder_update(
        data=data,
        scenario=normalize_scenario(scenario),
        task_id=task_id or None,
    )


@tool(
    name="prepare_stormbridge_orchestrate_handoff",
    description="Prepare the Orchestrate workflow handoff payload for an approved StormBridge action.",
    permission=ToolPermission.READ_ONLY,
)
def prepare_stormbridge_orchestrate_handoff(
    scenario: str = "SCENARIO-B",
    task_id: str = "",
    approved: bool = False,
) -> str:
    data = load_all_data()
    payload = build_orchestrate_handoff(
        data=data,
        scenario=normalize_scenario(scenario),
        task_id=task_id or None,
        approved=approved,
    )
    return _json(payload)
