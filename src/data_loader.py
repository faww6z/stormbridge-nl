from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def load_csv(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    return pd.read_csv(path)

def load_all_data() -> dict:
    return {
        "weather_alerts":          load_csv("weather_alerts.csv"),
        "sites":                   load_csv("sites.csv"),
        "crews":                   load_csv("crews.csv"),
        "equipment":               load_csv("equipment.csv"),
        "tasks":                   load_csv("tasks.csv"),
        "risk_rules":              load_csv("risk_rules.csv"),
        "supply_resource_delays":  load_csv("supply_resource_delays.csv"),
    }
