import json
from pathlib import Path

def load_config():
    with (Path(__file__).resolve().parent / 'configs' / 'default.json').open('r') as config_file:
        config = json.load(config_file)
        return config
        
config = load_config()

grid_rows = config["World Settings"]["rows"]
grid_cols = config["World Settings"]["cols"]
_legacy_building_count = config.get("building_count", config.get("fruit_count", 4))
_default_building_counts = {
    "type_1_workplace": 2,
    "type_2_workplace": 2,
    "type_3_workplace": 1,
    "type_4_workplace": 1,
    "type_5_workplace": 1,
    "apartment_building": 2,
    "hotel": 2,
    "school": 1,
    "grocery_store": 1,
    "hospital": 1,
    "budget_house": 2,
    "premium_house": 1,
}
_building_count_keys = tuple(_default_building_counts)
if "building_counts" in config:
    building_counts = {
        name: config["building_counts"].get(name, 0)
        for name in _building_count_keys
    }
else:
    # Backwards compatibility for older configs that only set building_count.
    building_counts = {name: 0 for name in _building_count_keys}
    for index in range(_legacy_building_count):
        name = _building_count_keys[index % len(_building_count_keys)]
        building_counts[name] += 1

for _name, _count in building_counts.items():
    if not isinstance(_count, int) or isinstance(_count, bool) or _count < 0:
        raise ValueError("building_counts.{} must be a nonnegative integer".format(_name))
building_count = sum(building_counts.values())
agent_count = config["Agent & Population"]["agent_count"]
health_min = config.get("health_min", 0)
health_max = config.get("health_max", 100)
starting_health_min = config.get("starting_health_min", 50)
disease_config = config.get("Health & Disease", {})
disease_chance_per_turn = disease_config.get(
    "community_case_chance_per_turn",
    config.get("disease_chance_per_turn", 0.5),
)
hunger_drain_per_step = config.get("hunger_drain_per_step", 5)
hunger_damage_per_step = config.get("hunger_damage_per_step", 10)
starting_wealth = config.get("starting_wealth", 0)
_days_per_year = 365.25
type_1_income_per_year = config.get(
    "type_1_income_per_year", config.get("type_1_income_per_turn", 100) * _days_per_year
)
type_2_income_per_year = config.get(
    "type_2_income_per_year", config.get("type_2_income_per_turn", 250) * _days_per_year
)
low_wealth_threshold = config.get("low_wealth_threshold", 1000)
low_wealth_stress_turns = config.get("low_wealth_stress_turns", 10)
grocery_hunger_threshold = config.get("grocery_hunger_threshold", 25)
grocery_food_cost = config.get("grocery_food_cost", 500)
grocery_food_health_restore = config.get("grocery_food_health_restore", 25)
grocery_food_mental_restore = config.get("grocery_food_mental_restore", 25)
mental_health_recovery_per_turn = config.get("mental_health_recovery_per_turn", 1)
stress_mental_health_initial_drain = config.get("stress_mental_health_initial_drain", 5)
stress_mental_health_sustained_drain = config.get("stress_mental_health_sustained_drain", 2)
building_names = {
    1: "Type 1 Workplace",
    2: "Type 2 Workplace",
    3: "School",
    4: "Grocery Store",
    5: "Hospital",
    6: "Budget House",
    7: "Premium House",
    8: "Type 3 Workplace",
    9: "Type 4 Workplace",
    10: "Type 5 Workplace",
    11: "Apartment Building",
    12: "Hotel",
}

job_names = {
    1: "Type 1 job",
    2: "Type 2 job",
    4: "Grocery Store job",
    5: "Hospital job",
    8: "Type 3 job",
    9: "Type 4 job",
    10: "Type 5 job",
}
job_income_per_year = {
    1: type_1_income_per_year,
    2: type_2_income_per_year,
    4: config.get("Economy & Jobs", {}).get("grocery_store_income_per_year", 32000),
    5: config.get("Economy & Jobs", {}).get("hospital_income_per_year", 110000),
    8: config.get("Economy & Jobs", {}).get("type_3_income_per_year", 50000),
    9: config.get("Economy & Jobs", {}).get("type_4_income_per_year", 25000),
    10: config.get("Economy & Jobs", {}).get("type_5_income_per_year", 70000),
}
