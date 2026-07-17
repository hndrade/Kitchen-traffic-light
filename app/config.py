"""Persistence for the weekly kitchen schedule and app settings."""
import json
import os

DAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".kitchen_traffic_light")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_BLOCKS = [
    {"start": "09:30", "end": "10:30"},
    {"start": "14:00", "end": "15:00"},
]

DEFAULT_CONFIG = {
    "schedule": {
        day: {
            "enabled": day not in ("Sábado", "Domingo"),
            "blocks": [dict(b) for b in DEFAULT_BLOCKS],
        }
        for day in DAYS
    },
    "start_with_windows": False,
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update({k: v for k, v in data.items() if k != "schedule"})
    merged["schedule"].update(data.get("schedule", {}))
    return merged


def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
