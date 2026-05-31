"""
risk_engine.py — StormBridge NL
Calculates the risk-ranked action queue from v3 scenario datasets.
"""

import pandas as pd

# ── Lookup tables ──────────────────────────────────────────────────────────

SEVERITY_TO_NUM: dict = {
    "LOW":      2.0,
    "MODERATE": 5.0,
    "HIGH":     7.0,
    "EXTREME":  9.0,
}

CRITICALITY_TO_NUM: dict = {
    "LOW":      3.0,
    "MODERATE": 5.0,
    "HIGH":     7.0,
    "CRITICAL": 10.0,
}

SCENARIO_CREW_COL: dict = {
    "SCENARIO-A": "availability_scenario_a",
    "SCENARIO-B": "availability_scenario_b",
    "SCENARIO-C": "availability_scenario_c",
}

SCENARIO_EQUIP_COL: dict = {
    "SCENARIO-A": "status_scenario_a",
    "SCENARIO-B": "status_scenario_b",
    "SCENARIO-C": "status_scenario_c",
}

# Crew status values that count as "deployable" for this scenario
CREW_ACTIVE_STATUSES = frozenset({
    "AVAILABLE", "ON-SHIFT", "DISPATCHED", "STANDBY",
})

# Equipment status keywords that mean "not usable right now"
EQUIP_BLOCKED_KEYWORDS = (
    "SECURED", "SUSPENDED", "INSPECTION PENDING",
    "BREACHED", "FAILED", "ISOLATED",
    "CRITICAL LOAD", "REMOVED", "PARKED",
)

# Composite risk score weights — must sum to 1.0
WEIGHTS = {
    "weather_severity": 0.30,
    "site_criticality": 0.25,
    "exposure_level":   0.15,
    "task_priority":    0.25,   # priority_score/10; replaces separate urgency + safety_impact
    "resource_gap":     0.05,
}

# Priority thresholds
PRIORITY_THRESHOLDS = [
    (8.5, "Critical"),
    (7.0, "High"),
    (5.5, "Medium"),
    (0.0, "Low"),
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _severity_num(text) -> float:
    return SEVERITY_TO_NUM.get(str(text).upper().strip(), 5.0)


def _criticality_num(text) -> float:
    return CRITICALITY_TO_NUM.get(str(text).upper().strip(), 5.0)


def _derive_exposure(road_routes, helicopter_pad) -> float:
    """
    1–10 exposure score from accessibility data.
    More routes + helicopter access = lower exposure (easier to respond).
    """
    try:
        routes = int(road_routes)
    except (ValueError, TypeError):
        routes = 2
    base = max(1.0, 10.0 - routes * 2.0)
    if str(helicopter_pad).upper().strip() == "YES":
        base = max(1.0, base - 1.0)
    return min(10.0, base)


def _crew_deployable(status: str) -> bool:
    return str(status).upper().strip() in CREW_ACTIVE_STATUSES


def _equip_operational(status: str) -> bool:
    s = str(status).upper().strip()
    return not any(kw in s for kw in EQUIP_BLOCKED_KEYWORDS)


def _resource_gap(site_id: str, scenario: str,
                  crews: pd.DataFrame, equipment: pd.DataFrame) -> int:
    """
    Returns 0–10 gap score for a site/scenario.
    +5 if no deployable crew at this site, +5 if no operational equipment.
    """
    crew_col  = SCENARIO_CREW_COL.get(scenario, "availability_scenario_b")
    equip_col = SCENARIO_EQUIP_COL.get(scenario, "status_scenario_b")

    site_crews = crews[crews["site_id"] == site_id]
    avail_crew = site_crews[site_crews[crew_col].apply(_crew_deployable)]

    site_equip = equipment[equipment["site_id"] == site_id]
    avail_equip = site_equip[site_equip[equip_col].apply(_equip_operational)]

    gap = 0
    if avail_crew.empty:
        gap += 5
    if avail_equip.empty:
        gap += 5
    return gap


def _priority_label(score: float) -> str:
    for threshold, label in PRIORITY_THRESHOLDS:
        if score >= threshold:
            return label
    return "Low"


# ── Main calculation ───────────────────────────────────────────────────────

def calculate_action_queue(data: dict, scenario: str = "SCENARIO-B") -> pd.DataFrame:
    """
    Build the risk-ranked action queue for a given scenario.

    Args:
        data:     Dict of DataFrames from data_loader.load_all_data().
        scenario: One of "SCENARIO-A", "SCENARIO-B", "SCENARIO-C".

    Returns:
        DataFrame sorted by risk_score descending.
        Returns an empty DataFrame if no tasks match the scenario.
    """
    weather_all = data["weather_alerts"]
    sites       = data["sites"]
    tasks       = data["tasks"]
    crews       = data["crews"]
    equipment   = data["equipment"]

    # Tasks for this scenario only; skip cross-sector comms tasks (site_id = "ALL")
    scenario_tasks = tasks[
        (tasks["scenario"] == scenario) &
        (tasks["site_id"] != "ALL")
    ].copy()

    if scenario_tasks.empty:
        return pd.DataFrame()

    rows = []

    for _, task in scenario_tasks.iterrows():

        # ── Site ──────────────────────────────────────────────────────────
        site_match = sites[sites["site_id"] == task["site_id"]]
        if site_match.empty:
            continue
        site = site_match.iloc[0]

        # ── Sector-specific weather for this scenario ──────────────────────
        weather_match = weather_all[
            (weather_all["scenario"] == scenario) &
            (weather_all["sector"]   == site["sector"])
        ]
        if weather_match.empty:
            weather_match = weather_all[weather_all["scenario"] == scenario]
        if weather_match.empty:
            continue
        weather = weather_match.iloc[0]

        # ── Numeric factor values ──────────────────────────────────────────
        severity_num    = _severity_num(weather["severity"])
        criticality_num = _criticality_num(site["criticality"])
        exposure_num    = _derive_exposure(site["road_access_routes"], site["helicopter_pad"])

        ps = task.get("priority_score", 50)
        if pd.isna(ps):
            ps = 50
        task_priority = float(ps) / 10.0

        gap = _resource_gap(task["site_id"], scenario, crews, equipment)

        # ── Per-factor contributions ───────────────────────────────────────
        contrib_weather      = round(severity_num    * WEIGHTS["weather_severity"], 2)
        contrib_criticality  = round(criticality_num * WEIGHTS["site_criticality"], 2)
        contrib_exposure     = round(exposure_num    * WEIGHTS["exposure_level"],   2)
        contrib_priority     = round(task_priority   * WEIGHTS["task_priority"],    2)
        contrib_resource_gap = round(float(gap)      * WEIGHTS["resource_gap"],     2)

        score = (
            contrib_weather
            + contrib_criticality
            + contrib_exposure
            + contrib_priority
            + contrib_resource_gap
        )

        # Confidence: prefer watsonx_confidence from task data if present
        confidence = max(65, min(95, 100 - gap * 3))
        raw_conf = task.get("watsonx_confidence") if hasattr(task, "get") else None
        if raw_conf is not None and pd.notna(raw_conf):
            try:
                confidence = int(float(raw_conf) * 100)
            except (ValueError, TypeError):
                pass

        rows.append({
            "site_id":           str(task["site_id"]),
            "task_id":           str(task["task_id"]),
            "site_name":         str(site["site_name"]),
            "sector":            str(site["sector"]),
            "zone":              str(site.get("zone", "")),
            "task_name":         str(task["task_name"]),
            "task_status":       str(task.get("task_status", "")).strip(),
            "trigger_condition": str(task.get("trigger_condition", "")).strip(),
            "business_impact":   str(task.get("business_impact_if_delayed", "")).strip(),
            "human_approved":    str(task.get("human_approved", "")).upper().strip(),
            "risk_score":        round(score, 2),
            "priority":          _priority_label(score),
            "resource_gap":      gap,
            "confidence_score":  confidence,
            "recommended_action": str(task["task_name"]),
            "headcount_at_risk": int(site.get("headcount_on_site", 0)),
            "revenue_impact_hr": int(site.get("revenue_impact_per_hr_cad", 0)),
            # Explainability breakdown
            "contrib_weather":      contrib_weather,
            "contrib_criticality":  contrib_criticality,
            "contrib_exposure":     contrib_exposure,
            "contrib_priority":     contrib_priority,
            "contrib_resource_gap": contrib_resource_gap,
        })

    if not rows:
        return pd.DataFrame()

    aq = pd.DataFrame(rows)
    return aq.sort_values("risk_score", ascending=False).reset_index(drop=True)
