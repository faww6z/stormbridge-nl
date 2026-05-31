# StormBridge watsonx Orchestrate Tool Package

This package exposes StormBridge NL as read-only watsonx Orchestrate ADK tools.

The tools draft workflow payloads, manager briefs, dispatch packets, and stakeholder updates. They do not dispatch crews, send messages, or write to external systems.

## Tools

- `get_stormbridge_risk_queue`
- `get_stormbridge_top_priority`
- `draft_stormbridge_manager_brief`
- `draft_stormbridge_dispatch_packet`
- `draft_stormbridge_stakeholder_update`
- `prepare_stormbridge_orchestrate_handoff`

## Import

From the repository root:

```bash
orchestrate tools import \
  -k python \
  -f orchestrate_tools/stormbridge_response/source/stormbridge_tools.py \
  -p orchestrate_tools/stormbridge_response \
  -r orchestrate_tools/stormbridge_response/requirements.txt
```

## Create Agent

```bash
orchestrate agents create \
  --name stormbridge_response_coordinator \
  --kind native \
  --description "Coordinates human-approved StormBridge NL storm response workflows." \
  --llm watsonx/ibm/granite-3-8b-instruct \
  --style react \
  --tools get_stormbridge_risk_queue \
  --tools get_stormbridge_top_priority \
  --tools draft_stormbridge_manager_brief \
  --tools draft_stormbridge_dispatch_packet \
  --tools draft_stormbridge_stakeholder_update \
  --tools prepare_stormbridge_orchestrate_handoff
```

## Refresh Package Data

If you change `src/` or `data/`, refresh the package copy before importing:

```bash
cp src/*.py orchestrate_tools/stormbridge_response/src/
cp data/*.csv orchestrate_tools/stormbridge_response/data/
```
