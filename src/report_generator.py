from src.watsonx_client import generate_text


def build_manager_brief(weather, action_queue) -> str:
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
