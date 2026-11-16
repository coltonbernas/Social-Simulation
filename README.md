# Social-Simulation

An agent-based social simulation built for our capstone project. A population of agents lives on a grid-based world with buildings, jobs, housing, and regions, and the simulation tracks how their health, wealth, relationships, and movement change turn by turn.

## Features

- **Agents**: individual health, mental health, hunger, wealth, intelligence, jobs, and homes
- **World**: configurable grid with workplaces, schools, grocery stores, hospitals, houses, apartments, and hotels
- **Regions & economy**: four regions across two countries with their own wage and cost-of-living multipliers, job application thresholds, rent, and housing prices
- **Disease**: community cases, spread between neighbouring agents, and per-agent immune systems that are inherited from parents
- **Social life**: relationships, gifts, information sharing, marriage, births, and deaths
- **Migration**: agents can move between regions based on wages, housing prices, unemployment, and social connections
- **Reports**: end-of-run stat card and wealth Gini coefficient graph

## Requirements

- Python 3
- Standard library only (the GUI uses `tkinter`)

## Running

From the `pythonFiles` directory:

```bash
python main.py            # launches the GUI
python main.py --console  # runs in the terminal in batches of steps
```

In console mode you choose how many steps to run per batch. Press `Ctrl+C` to end the run and print the final stat card.

## Configuration

Settings live in `pythonFiles/configs/`:

- `default.json`
- `small.json`
- `large.json`

Each file sets world size, building counts, population size, starting stats, disease chance, job and income values, grocery and hunger rules, stress effects, regions, and migration settings. The GUI includes a config dialog for editing these.

## Tests

From the repository root:

```bash
python -m unittest pythonFiles.tests.test_disease
```

## Project structure

```
pythonFiles/
├── main.py         # entry point (GUI or console)
├── world.py        # grid, buildings, regions, prices
├── population.py   # agent population, relationships, births, reports
├── agent.py        # individual agent behaviour
├── disease.py      # diseases and immune systems
├── migration.py    # region-to-region movement
├── config.py       # loads and validates settings
├── configs/        # JSON presets
├── ui/             # tkinter GUI (main window, config dialog, theme)
└── tests/          # unit tests
```

## Roadmap

- More agent and environment parameters for a realistic society
- Generational inheritance of genes and conditions
- Condition / chance / decision model
- Richer agent-to-agent and agent-to-environment interactions
- More stats in the UI
