import json

def load_config():
    with open('config.json', 'r') as config_file:
        config = json.load(config_file)
        return config
        
config = load_config()

grid_rows = config["rows"]
grid_cols = config["cols"]
fruit_count = config["fruit_count"]
agent_count = config["agent_count"]