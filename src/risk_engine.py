import pandas as pd

def get_weight(risk_rules: pd.DataFrame, factor: str, default: float = 0.0) -> float:
    match = risk_rules[risk_rules["factor"] == factor]
    if match.empty:
        return default
    return float(match.iloc[0]["weight"])

def calculate_resource_gap(site_sector: str, site_region: str, crews: pd.DataFrame, equipment: pd.DataFrame) -> int:
    matching_crews = crews[
        (crews["sector"] == site_sector)
        & (crews["region"] == site_region)
        & (crews["available"].str.lower() == "yes")
    ]

    matching_equipment = equipment[
        (equipment["sector"] == site_sector)
        & (equipment["region"] == site_region)
        & (equipment["available"].str.lower() == "yes")
    ]

    gap = 0
    if matching_crews.empty:
        gap += 5
    if matching_equipment.empty:
        gap += 5

    return gap

def calculate_action_queue(data: dict) -> pd.DataFrame:
    weather = data["weather_alerts"].iloc[0]
    sites = data["sites"]
    tasks = data["tasks"]
    crews = data["crews"]
    equipment = data["equipment"]
    risk_rules = data["risk_rules"]

    weights = {
        "weather_severity": get_weight(risk_rules, "weather_severity"),
        "site_criticality": get_weight(risk_rules, "site_criticality"),
        "exposure_level": get_weight(risk_rules, "exposure_level"),
        "task_urgency": get_weight(risk_rules, "task_urgency"),
        "safety_impact": get_weight(risk_rules, "safety_impact"),
        "resource_gap": get_weight(risk_rules, "resource_gap"),
    }

    rows = []

    for _, task in tasks.iterrows():
        site = sites[sites["site_id"] == task["site_id"]].iloc[0]

        resource_gap = calculate_resource_gap(
            site_sector=site["sector"],
            site_region=site["region"],
            crews=crews,
            equipment=equipment,
        )

        score = (
            float(weather["severity"]) * weights["weather_severity"]
            + float(site["criticality"]) * weights["site_criticality"]
            + float(site["exposure_level"]) * weights["exposure_level"]
            + float(task["urgency"]) * weights["task_urgency"]
            + float(task["safety_impact"]) * weights["safety_impact"]
            + float(resource_gap) * weights["resource_gap"]
        )

        confidence = max(65, min(95, 100 - resource_gap * 3))

        if score >= 8:
            priority = "Critical"
        elif score >= 6.5:
            priority = "High"
        elif score >= 5:
            priority = "Medium"
        else:
            priority = "Low"

        rows.append({
            "site_id": site["site_id"],
            "site_name": site["site_name"],
            "sector": site["sector"],
            "region": site["region"],
            "task_name": task["task_name"],
            "risk_score": round(score, 2),
            "priority": priority,
            "resource_gap": resource_gap,
            "confidence_score": confidence,
            "recommended_action": f"Review {task['task_name'].lower()} and assign available response resources.",
        })

    action_queue = pd.DataFrame(rows)
    return action_queue.sort_values(by="risk_score", ascending=False).reset_index(drop=True)
