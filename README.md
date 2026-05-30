I pushed the StormBridge NL prototype to GitHub. Clone the repo, create your own virtual environment, install the requirements, and run the app locally.

Do not create or push a real .env file. Use .env.example as the template.

Commands:
git clone <repo-link>
cd stormbridge-nl
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
