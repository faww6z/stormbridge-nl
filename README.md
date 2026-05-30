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
- Displays an active storm alert
- Calculates risk scores for affected sites
- Ranks operational tasks by priority
- Shows crew and equipment availability
- Generates a manager brief
- Includes a human approval step before action is taken
- Supports both Local mode and watsonx.ai mode

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
├── src/
│   ├── data_loader.py
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

## Current Development Priorities

- Improve the Streamlit dashboard layout
- Expand the synthetic datasets
- Add multiple demo scenarios
- Improve the risk scoring logic
- Build stronger manager brief and stakeholder update outputs
- Prepare the watsonx Orchestrate agent workflow
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