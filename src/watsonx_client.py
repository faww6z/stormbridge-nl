import os
from pathlib import Path
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)

IBM_API_KEY = os.getenv("IBM_API_KEY")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID")
IBM_WATSONX_URL = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
IBM_MODEL_ID = os.getenv("IBM_MODEL_ID", "meta-llama/llama-3-3-70b-instruct")


def check_env():
    print(f"Looking for .env at: {ENV_PATH}")
    print(f".env exists: {ENV_PATH.exists()}")
    print(f"IBM_PROJECT_ID loaded: {bool(IBM_PROJECT_ID)}")
    print(f"IBM_API_KEY loaded: {bool(IBM_API_KEY)}")
    print(f"IBM_MODEL_ID: {IBM_MODEL_ID}")


def get_iam_token() -> str:
    if not IBM_API_KEY:
        raise ValueError("IBM_API_KEY is missing from .env")

    response = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": IBM_API_KEY,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(f"Failed to get IAM token: {response.status_code} - {response.text}")

    return response.json()["access_token"]


def generate_text(prompt: str, max_new_tokens: int = 500) -> str:
    if not IBM_PROJECT_ID:
        raise ValueError("IBM_PROJECT_ID is missing from .env")

    token = get_iam_token()

    url = f"{IBM_WATSONX_URL}/ml/v1/text/chat?version=2023-05-29"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model_id": IBM_MODEL_ID,
        "project_id": IBM_PROJECT_ID,
        "messages": [
            {
                "role": "system",
                "content": "You are StormBridge NL, an operations coordination assistant for Newfoundland and Labrador organizations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "parameters": {
            "max_tokens": max_new_tokens,
            "temperature": 0.2,
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(f"watsonx.ai chat failed: {response.status_code} - {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    check_env()

    test_prompt = """
    Write a short manager brief for a severe storm affecting:
    - St. John's Port Operations
    - Avalon Energy Feeder 12
    - Labrador Remote Mine Site

    Include top priority, operational risk, and a human approval note.
    Keep it concise and professional.
    """

    print("\n--- watsonx.ai test output ---\n")
    print(generate_text(test_prompt))
