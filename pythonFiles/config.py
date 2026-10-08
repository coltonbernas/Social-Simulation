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
