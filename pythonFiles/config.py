import json
from pathlib import Path

def load_config():
    with (Path(__file__).resolve().parent / 'config.json').open('r') as config_file:
        config = json.load(config_file)
        return config
        
config = load_config()

grid_rows = config["rows"]
grid_cols = config["cols"]
fruit_count = config["fruit_count"]
agent_count = config["agent_count"]
health_min = config.get("health_min", 0)
health_max = config.get("health_max", 100)
base_disease_transmission = config.get("base_disease_transmission", 0.20)
disease_health_impact = config.get("disease_health_impact", 20)
