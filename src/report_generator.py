"""
report_generator.py — StormBridge NL
Generates manager briefs and stakeholder communications.

Two paths:
  use_watsonx=False  → deterministic template (always works, no credentials needed)
  use_watsonx=True   → calls watsonx.ai via watsonx_client; silently falls back to
                       the template on any error so the live demo never crashes.

Ownership:
  build_manager_brief / _fallback_brief  → Tahmid (plumbing + fallback)
  _build_prompt                          → Tonye (wording), Tahmid (data binding)
  generate_text call                     → Fawwaz (credentials + watsonx_client.py)

Schema note:
  Uses .get() with fallbacks so it works with both the old v1 schema and new v3 schema.
  v3 renames: storm_type (was alert_type), wind_kph_sustained (was wind_kmh),
               rainfall_mm_6hr (was precipitation_mm), zone (was affected_region),
               issued_at/expires_at (was start_time/end_time).
"""


def build_manager_brief(weather, top_action, use_watsonx: bool = False) -> str:
    """
    Generate a storm response manager brief.

    Args:
        weather:     Row from weather_alerts DataFrame (pandas Series or dict).
        top_action:  Top row from action_queue DataFrame (pandas Series or dict).
        use_watsonx: If True, attempt IBM Granite generation via watsonx_client.
                     Falls back to the template brief on any error.

    Returns:
        Formatted plain-text brief string.
    """
    if use_watsonx:
        try:
            from src.watsonx_client import generate_text
            return generate_text(_build_prompt(weather, top_action))
        except Exception:
            pass  # Fall through to template — never crash the live demo
    return _fallback_brief(weather, top_action)


def _fallback_brief(weather, top_action) -> str:
    """Deterministic template brief — no AI or credentials required."""

    # Column name compat: v3 renames several fields; fall back to v1 names
    storm_type  = weather.get("storm_type",        weather.get("alert_type",       "Storm Warning"))
    wind        = weather.get("wind_kph_sustained", weather.get("wind_kmh",         "N/A"))
    precip      = weather.get("rainfall_mm_6hr",   weather.get("precipitation_mm", "N/A"))
    region      = weather.get("zone",              weather.get("affected_region",  "N/A"))
    severity    = weather.get("severity",          "N/A")
    issued_at   = weather.get("issued_at",         weather.get("start_time",       "N/A"))
    expires_at  = weather.get("expires_at",        weather.get("end_time",         "N/A"))
    storm_name  = weather.get("storm_name",        "")

    site_name   = top_action.get("site_name",      "N/A")
    sector      = top_action.get("sector",         "N/A")
    zone        = top_action.get("zone",           top_action.get("region", "N/A"))
    risk_score  = top_action.get("risk_score",     "N/A")
    confidence  = top_action.get("confidence_score", "N/A")
    task_name   = top_action.get("task_name",      top_action.get("recommended_action", "N/A"))
    biz_impact  = top_action.get("business_impact", "")
    headcount   = top_action.get("headcount_at_risk", "")
    revenue_hr  = top_action.get("revenue_impact_hr", "")
    task_status = top_action.get("task_status",   "")

    headline = f"{storm_name} — {storm_type}".strip(" —") if storm_name else storm_type
    divider  = "─" * 52

    brief = (
        f"STORM RESPONSE BRIEF — {headline.upper()}\n"
        f"{divider}\n"
        f"Region:        {region}\n"
        f"Severity:      {severity}\n"
        f"Wind speed:    {wind} km/h\n"
        f"Precipitation: {precip} mm\n"
        f"Active window: {issued_at}  →  {expires_at}\n"
        f"\n"
        f"HIGHEST PRIORITY SITE\n"
        f"{divider}\n"
        f"Site:        {site_name}  ({sector})\n"
        f"Zone:        {zone}\n"
        f"Risk score:  {risk_score}/10  (confidence: {confidence}%)\n"
        f"Task:        {task_name}\n"
    )

    if task_status:
        brief += f"Status:      {task_status}\n"
    if headcount:
        brief += f"Personnel:   {headcount} on site\n"
    if revenue_hr:
        brief += f"Cost of delay: ${int(revenue_hr):,}/hr\n"
    if biz_impact:
        brief += f"\nBUSINESS RISK\n{divider}\n{biz_impact}\n"

    brief += (
        f"\n"
        f"NEXT STEPS\n"
        f"{divider}\n"
        f"All recommended actions require human approval before crew dispatch\n"
        f"or external stakeholder communication. Operations managers should\n"
        f"review the full ranked action queue and confirm resource availability\n"
        f"before issuing any response instructions.\n"
        f"\n"
        f"[Template brief — connect watsonx.ai credentials to enable AI generation\n"
        f" via IBM Granite through StormBridge NL.]"
    )
    return brief


def _build_prompt(weather, top_action) -> str:
    """
    Prompt sent to watsonx.ai.

    Tonye: refine the instruction wording in lines marked [PROMPT].
    Tahmid: owns the data binding (f-string variables) — do not change those.
    """
    storm_type  = weather.get("storm_type",        weather.get("alert_type",       "Storm"))
    wind        = weather.get("wind_kph_sustained", weather.get("wind_kmh",         "N/A"))
    precip      = weather.get("rainfall_mm_6hr",   weather.get("precipitation_mm", "N/A"))
    region      = weather.get("zone",              weather.get("affected_region",  "N/A"))
    severity    = weather.get("severity",          "N/A")
    issued_at   = weather.get("issued_at",         weather.get("start_time",       "N/A"))
    expires_at  = weather.get("expires_at",        weather.get("end_time",         "N/A"))

    site_name   = top_action.get("site_name",      "N/A")
    sector      = top_action.get("sector",         "N/A")
    risk_score  = top_action.get("risk_score",     "N/A")
    confidence  = top_action.get("confidence_score", "N/A")
    task_name   = top_action.get("task_name",      "N/A")
    biz_impact  = top_action.get("business_impact", "Not specified")

    return (
        # [PROMPT] System instruction
        "You are StormBridge NL, an operations coordination assistant for "
        "Newfoundland and Labrador industries.\n\n"
        "Write a concise, professional storm response brief for operations managers. "
        "Be specific, factual, and action-oriented. "
        "Do not invent any data beyond what is provided below.\n\n"
        # Data binding
        f"CURRENT ALERT\n"
        f"- Type: {storm_type}\n"
        f"- Severity: {severity}\n"
        f"- Wind speed: {wind} km/h\n"
        f"- Precipitation: {precip} mm\n"
        f"- Region: {region}\n"
        f"- Active: {issued_at} to {expires_at}\n\n"
        f"HIGHEST PRIORITY SITE\n"
        f"- Site: {site_name}\n"
        f"- Sector: {sector}\n"
        f"- Risk score: {risk_score}/10\n"
        f"- Confidence: {confidence}%\n"
        f"- Required action: {task_name}\n"
        f"- Business risk if delayed: {biz_impact}\n\n"
        # [PROMPT] Output format instruction
        "Write the brief in 3 short paragraphs: "
        "(1) situation summary with storm conditions and affected sectors, "
        "(2) the highest-priority action and why it is ranked first, "
        "(3) next steps and a reminder that human approval is required before any dispatch."
    )
