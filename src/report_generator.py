from src.watsonx_client import generate_text


def build_local_manager_brief(weather, action_queue) -> str:
    top_action = action_queue.iloc[0]
    top_three = action_queue.head(3)

    action_lines = []
    for _, row in top_three.iterrows():
        action_lines.append(
            f"- **{row['site_name']}** ({row['sector']}): {row['task_name']} "
            f"| Risk: {row['risk_score']}/10 | Priority: {row['priority']} | Confidence: {row['confidence_score']}%"
        )

    return f"""
## 1. Situation Summary

A **{weather['alert_type']}** is active in **{weather['affected_region']}** with a severity level of **{weather['severity']}/10**, wind speeds of **{weather['wind_kmh']} km/h**, and expected precipitation of **{weather['precipitation_mm']} mm**.

## 2. Top Priority

The highest-priority operation is **{top_action['site_name']}** in the **{top_action['sector']}** sector.

**Recommended action:** {top_action['recommended_action']}

## 3. Risk-Ranked Action Plan

{chr(10).join(action_lines)}

## 4. Resource Concerns

The top resource gap score is **{top_action['resource_gap']}**. Sites with higher resource gaps may require manual review before dispatching crews or equipment.

## 5. Human Approval Note

StormBridge supports decision-making but does not automatically dispatch crews or send stakeholder communications. Human approval is required before any operational action is taken.
"""


def build_watsonx_manager_brief(weather, action_queue) -> str:
    top_rows = action_queue.head(3)

    risk_items = []
    for _, row in top_rows.iterrows():
        risk_items.append(
            f"""
Site: {row['site_name']}
Sector: {row['sector']}
Priority: {row['priority']}
Risk score: {row['risk_score']}/10
Confidence score: {row['confidence_score']}%
Task: {row['task_name']}
Resource gap score: {row['resource_gap']}
Recommended action: {row['recommended_action']}
"""
        )

    prompt = f"""
You are StormBridge NL, an operations coordination assistant for Newfoundland and Labrador organizations.

Generate a concise manager brief using ONLY the information provided below.

Rules:
- Do not invent names, people, approvals, phone numbers, or facts.
- Do not say an action has been approved.
- Make it clear that human approval is required before dispatch or communication.
- Keep the tone professional and operational.
- Use headings and short bullets.
- Focus on what is at risk, what should be prioritized, and what needs review.

Storm alert:
Alert type: {weather['alert_type']}
Severity: {weather['severity']}/10
Wind speed: {weather['wind_kmh']} km/h
Precipitation: {weather['precipitation_mm']} mm
Affected region: {weather['affected_region']}
Start time: {weather['start_time']}
End time: {weather['end_time']}

Top risk-ranked operations:
{chr(10).join(risk_items)}

Output format:
1. Situation Summary
2. Top Priority
3. Risk-Ranked Action Plan
4. Resource Concerns
5. Human Approval Note
"""

    return generate_text(prompt, max_new_tokens=600)


def build_manager_brief(weather, action_queue, use_watsonx: bool = False) -> str:
    if use_watsonx:
        return build_watsonx_manager_brief(weather, action_queue)

    return build_local_manager_brief(weather, action_queue)
