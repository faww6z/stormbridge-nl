# StormBridge NL

StormBridge NL is an AI-powered coordination prototype for Newfoundland and Labrador organizations facing storm-driven operational disruption.

The app helps teams turn scattered operational data into a clear risk-ranked action queue, manager brief, and human-approved response plan.

## Prototype Focus

For the hackathon prototype, we are focusing on three sectors:

- Ocean / Port Operations
- Energy / Utilities
- Mining / Remote Industrial Sites

Manufacturing can be treated as a future expansion.

## What the App Does

StormBridge NL currently:

- Loads synthetic CSV datasets
- Supports three demo scenarios: Moderate Storm, Severe Storm, and Recovery
- Displays sector-specific storm alerts
- Calculates explainable risk scores for affected sites
- Ranks operational tasks by priority
- Shows crew, equipment, and supply/resource delay status
- Generates a manager brief
- Includes a human approval step before action is taken
- Supports both Local mode and watsonx.ai mode
- Prepares a watsonx Orchestrate workflow handoff payload after approval

## Tech Stack

- Python
- Streamlit
- pandas
- IBM watsonx.ai
- IBM watsonx Orchestrate
- Synthetic CSV datasets

## Project Structure

```text
stormbridge-nl/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── data/
├── orchestrate_tools/
│   └── stormbridge_response/
├── src/
│   ├── data_loader.py
│   ├── orchestrate_workflow.py
│   ├── risk_engine.py
│   ├── report_generator.py
│   └── watsonx_client.py
├── outputs/
└── tests/
```

## Setup Instructions

Clone the repo:

```bash
git clone <repo-link>
cd stormbridge-nl
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Environment Variables

Do not create or push a real `.env` file unless you are working on the IBM watsonx integration.

Use `.env.example` as the template:

```env
IBM_API_KEY=your_api_key_here
IBM_PROJECT_ID=your_project_id_here
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
IBM_MODEL_ID=your_model_id_here
ORCHESTRATE_AGENT_NAME=stormbridge_response_coordinator
ORCHESTRATE_SERVICE_URL=your_orchestrate_service_url_here
```

The `.env` file is ignored by Git and should never be committed.

## Local Mode vs watsonx.ai Mode

The app has two manager brief modes:

### Local Mode

Works without IBM credentials.

Use this mode if you are working on the app UI, datasets, risk scoring, or demo flow.

### watsonx.ai Mode

Uses IBM watsonx.ai to generate the manager brief from the structured risk queue.

Only team members with IBM Cloud access need to use this mode.

## watsonx Orchestrate Integration

StormBridge treats watsonx Orchestrate as the controlled workflow layer after human approval.

The flow is:

```text
Risk queue -> Manager brief -> Human approval -> Orchestrate handoff
```

The Streamlit app includes an **Orchestrate Workflow** tab that previews the exact payload, dispatch packet, stakeholder update, and workflow steps that an Orchestrate agent would receive. This preview is side-effect free. It does not dispatch crews or send messages.

The repo also includes a self-contained ADK tool package:

```text
orchestrate_tools/stormbridge_response/
├── README.md
├── requirements.txt
├── data/
├── src/
└── source/
    └── stormbridge_tools.py
```

The package exposes these read-only tools:

- `get_stormbridge_risk_queue`
- `get_stormbridge_top_priority`
- `draft_stormbridge_manager_brief`
- `draft_stormbridge_dispatch_packet`
- `draft_stormbridge_stakeholder_update`
- `prepare_stormbridge_orchestrate_handoff`

### Setup Orchestrate ADK

Create and activate a Python 3.11 environment for the Orchestrate ADK:

```bash
python3.11 -m venv .venv-orchestrate
source .venv-orchestrate/bin/activate
```

Install the ADK:

```bash
pip install --upgrade ibm-watsonx-orchestrate
```

Add and activate your Orchestrate environment:

```bash
orchestrate env add -n stormbridge -u <your-orchestrate-service-url>
orchestrate env activate stormbridge
```

If you do not activate `.venv-orchestrate`, use the full local command path:

```bash
.venv-orchestrate/bin/orchestrate env activate stormbridge
```

Import the StormBridge tools:

```bash
orchestrate tools import \
  -k python \
  -f orchestrate_tools/stormbridge_response/source/stormbridge_tools.py \
  -p orchestrate_tools/stormbridge_response \
  -r orchestrate_tools/stormbridge_response/requirements.txt
```

Create the response coordinator agent:

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

Generate the draft webchat embed snippet:

```bash
orchestrate channels webchat embed \
  --agent-name stormbridge_response_coordinator \
  --env draft
```

For the local Streamlit demo, save the generated HTML/JavaScript snippet to:

```text
outputs/orchestrate_webchat_embed.html
```

The `outputs/` folder is ignored by Git, so your IBM instance IDs are not committed. The **Orchestrate Workflow** tab automatically embeds that file when it exists.

Alternatively, place the generated values in `.env`:

```env
ORCHESTRATE_WEBCHAT_ORCHESTRATION_ID=your_orchestration_id_here
ORCHESTRATE_WEBCHAT_HOST_URL=https://your-orchestrate-host-url
ORCHESTRATE_WEBCHAT_CRN=your_orchestrate_crn_here
ORCHESTRATE_WEBCHAT_AGENT_ID=your_orchestrate_agent_id_here
ORCHESTRATE_WEBCHAT_SHOW_LAUNCHER=true
```

If you change the app's `src/` or `data/` files, refresh the tool package before importing:

```bash
cp src/*.py orchestrate_tools/stormbridge_response/src/
cp data/*.csv orchestrate_tools/stormbridge_response/data/
```

## Current Development Priorities

- Keep the README and demo script aligned with the v3 dashboard
- Add automated tests for scenario ranking and manager brief generation
- Replace deprecated Streamlit `use_container_width` calls with `width="stretch"`
- Build stronger manager brief and stakeholder update outputs
- Import and test the watsonx Orchestrate ADK tool package
- Finalize the presentation/demo story

## Responsible AI Notes

StormBridge NL is designed to support decision-making, not replace human operators.

The prototype includes:

- Confidence scores
- Transparent rule-based risk scoring
- Human approval before dispatch or communication
- Synthetic data only
- No automatic emergency decisions

## Team Notes

For teammates without IBM Cloud access, use **Local mode**.

For teammates working on IBM integration, create your own `.env` file locally using `.env.example` as the template. Never commit your `.env` file or API keys to GitHub.
