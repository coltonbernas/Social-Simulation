"""In-simulation guide: explain the current run and edit config values."""

import json
import re
import time
from pathlib import Path

try:
    from .llm import ModelError, active_model, complete, using_openai
except ImportError:
    from ui.llm import ModelError, active_model, complete, using_openai

CONFIGS_DIR = Path(__file__).resolve().parent.parent / "configs"

# kind: how a value is validated.
# when: "live" applies on the next turn, "birth" applies to agents created after
# the change, "restart" is stored now and used when the world is rebuilt.
PARAMS = (
    ("World Settings", "rows", ("rows", "grid rows", "map rows", "height"),
     "count", "restart", 1, "How many rows the map has."),
    ("World Settings", "cols", ("cols", "columns", "grid columns", "map columns", "width"),
     "count", "restart", 1, "How many columns the map has."),
    ("Building Counts", "type_1_workplace",
     ("type 1 workplaces", "type 1 workplace", "workplace 1", "w1 buildings"),
     "count", "restart", 1, "How many lower-wage workplaces are placed."),
    ("Building Counts", "type_2_workplace",
     ("type 2 workplaces", "type 2 workplace", "workplace 2", "w2 buildings"),
     "count", "restart", 1, "How many higher-wage workplaces are placed."),
    ("Building Counts", "school", ("schools", "school count", "school"),
     "count", "restart", 1, "How many schools are placed."),
    ("Building Counts", "grocery_store",
     ("grocery stores", "groceries", "grocery store", "food stores"),
     "count", "restart", 1, "How many grocery stores are placed."),
    ("Building Counts", "hospital", ("hospitals", "hospital count", "hospital"),
     "count", "restart", 1, "How many hospitals are placed."),
    ("Building Counts", "budget_house",
     ("budget houses", "cheap houses", "budget housing", "budget house"),
     "count", "restart", 1, "How many budget houses are placed."),
    ("Building Counts", "premium_house",
     ("premium houses", "expensive houses", "premium housing", "premium house"),
     "count", "restart", 1, "How many premium houses are placed."),
    ("Agent & Population", "agent_count",
     ("agent count", "population size", "starting population", "number of agents", "agents"),
     "count", "restart", 1, "How many agents are created at the start."),
    ("Agent & Population", "starting_wealth",
     ("starting wealth", "start wealth", "initial wealth"),
     "money", "birth", 50, "Money a new agent begins with."),
    ("Agent & Population", "starting_health_min",
     ("starting health", "starting health min", "minimum starting health"),
     "int", "birth", 5, "Lowest health a new agent can be born with."),
    ("Agent & Population", "health_min", ("health min", "minimum health"),
     "int", "live", 5, "Health cannot fall below this."),
    ("Agent & Population", "health_max", ("health max", "maximum health"),
     "int", "live", 5, "Health cannot rise above this."),
    ("Health & Disease", "base_disease_transmission",
     ("disease transmission", "transmission", "contagion", "infection rate", "base transmission"),
     "prob", "live", 0.01, "Chance an agent catches a disease from a sick neighbor."),
    ("Health & Disease", "disease_health_impact",
     ("disease impact", "disease damage", "sickness damage", "disease health impact"),
     "int", "live", 1, "Health lost when an agent catches or keeps a disease."),
    ("Health & Disease", "disease_chance_per_turn",
     ("disease chance", "natural disease", "disease chance per turn", "spontaneous disease"),
     "prob", "live", 0.001, "Chance a healthy agent gets sick on their own each turn."),
    ("Health & Disease", "hospital_stay_duration_turns",
     ("hospital stay", "hospital duration", "time in hospital"),
     "count", "live", 1, "Turns an admitted agent spends in the hospital before they are cured."),
    ("Economy & Jobs", "type_1_income_per_turn",
     ("type 1 income", "type 1 wage", "low wage", "workplace 1 pay"),
     "money", "live", 25, "Base pay each turn for a type 1 job, before the region wage multiplier."),
    ("Economy & Jobs", "type_2_income_per_turn",
     ("type 2 income", "type 2 wage", "high wage", "workplace 2 pay"),
     "money", "live", 50, "Base pay each turn for a type 2 job, before the region wage multiplier."),
    ("Economy & Jobs", "budget_house_cost",
     ("budget house cost", "cheap rent", "budget rent"),
     "money", "live", 50, "Base price of a budget house, before regional cost of living."),
    ("Economy & Jobs", "premium_house_cost",
     ("premium house cost", "expensive rent", "premium rent"),
     "money", "live", 50, "Base price of a premium house, before regional cost of living."),
    ("Economy & Jobs", "low_wealth_threshold",
     ("low wealth threshold", "poverty line", "poor threshold"),
     "money", "live", 100, "Wealth below this starts counting as financial stress."),
    ("Economy & Jobs", "low_wealth_stress_turns",
     ("low wealth stress turns", "poverty stress turns", "turns until stress"),
     "count", "live", 1, "Turns below the poverty line before stress begins."),
    ("Grocery & Needs", "hunger_drain_per_step",
     ("hunger drain", "hunger loss", "food drain"),
     "int", "live", 1, "Hunger points lost each turn."),
    ("Grocery & Needs", "grocery_hunger_threshold",
     ("grocery threshold", "hunger threshold", "when they buy food"),
     "int", "live", 5, "Agents look for food once hunger falls below this."),
    ("Grocery & Needs", "grocery_food_cost",
     ("food cost", "grocery cost", "food price", "grocery price"),
     "money", "live", 25, "Base grocery price, before regional cost of living."),
    ("Grocery & Needs", "grocery_food_health_restore",
     ("food health restore", "food health", "health from food"),
     "int", "live", 5, "Health restored by buying food."),
    ("Grocery & Needs", "grocery_food_mental_restore",
     ("food mental restore", "food mood", "mental health from food"),
     "int", "live", 5, "Mental health restored by buying food."),
    ("Mental Health & Stress", "mental_health_recovery_per_turn",
     ("mental recovery", "mood recovery", "stress recovery"),
     "int", "live", 1, "Mental health regained each turn with no active stress."),
    ("Mental Health & Stress", "stress_mental_health_initial_drain",
     ("initial stress", "stress hit", "first stress drain"),
     "int", "live", 1, "Mental health lost the turn a new stressor starts."),
    ("Mental Health & Stress", "stress_mental_health_sustained_drain",
     ("sustained stress", "ongoing stress", "stress drain"),
     "int", "live", 1, "Mental health lost each turn a stressor continues."),
    ("Migration", "move_cost", ("move cost", "migration cost", "cost to move"),
     "money", "live", 50, "Money an agent pays to migrate."),
    ("Migration", "base_chance", ("migration chance", "base migration", "move chance"),
     "prob", "live", 0.01, "Baseline chance an agent considers moving."),
    ("Migration", "unemployed_bonus",
     ("unemployed migration", "unemployment bonus", "jobless move bonus"),
     "prob", "live", 0.02, "Extra migration chance while unemployed."),
    ("Migration", "connection_bonus",
     ("connection bonus", "family migration", "connection migration"),
     "prob", "live", 0.02, "Extra migration chance from a social connection."),
    ("Migration", "housing_price_sensitivity",
     ("housing sensitivity", "rent sensitivity", "housing price sensitivity"),
     "float", "live", 0.1, "How strongly crowded housing pushes regional rents."),
)


def _norm(text):
    text = text.lower().replace("_", " ").replace("&", " and ")
    text = re.sub(r"[^a-z0-9.%\s+-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _fmt(value):
    if isinstance(value, float):
        text = "{:.4f}".format(value).rstrip("0").rstrip(".")
        return text or "0"
    if isinstance(value, int):
        return "{:,}".format(value)
    return str(value)


class SimulationGuide:
    """Answer questions about the live run and write config changes."""

    def __init__(self, window):
        self.window = window
        self.narrating = False
        self.active_file = None
        self._seen = {}
        self._last_signature = None
        self._welcomed = False
        self._narrate_after = 0.0
        self._pending_notes = []
        self._history = []
        self._model_at = 0.0
        self._journal = {}
        self.user_name = None
        self.focus = None

    def respond(self, text):
        """Answer a message that should stay on the built-in guide."""
        raw = (text or "").strip()
        if not raw:
            return "Ask what is happening, or name a setting to change."
        command = self.try_command(raw)
        if command is not None:
            return command
        return self._one(raw)

    def try_command(self, text):
        """Handle an exact setting or file command. Return None when the model should talk."""
        raw = (text or "").strip()
        if not raw:
            return "Ask what is happening, or name a setting to change."
        clauses = self._clauses(raw)
        if len(clauses) > 1:
            answers = [self._command_clause(clause) for clause in clauses]
            if any(answer is None for answer in answers):
                return None
            reply = "\n\n".join(answers)
            self._remember(raw, reply)
            return reply
        reply = self._command_clause(raw)
        if reply is not None:
            self._remember(raw, reply)
        return reply

    def prepare_model(self, text):
        """Call the model. Returns (spoken reply, action lines)."""
        if not using_openai():
            wait = 30 - (time.monotonic() - self._model_at)
            if self._model_at and wait > 0:
                raise ModelError(
                    "The free model can answer about once every 30 seconds. "
                    "Try again in {:.0f} seconds, or name a setting directly.".format(wait)
                )
        reply = complete(self._model_messages(text))
        self._model_at = time.monotonic()
        spoken, actions = self._split_actions(reply)
        return spoken, actions

    def on_reset(self):
        self._seen = self._event_lengths()
        self._last_signature = None
        self._pending_notes = []
        self._narrate_after = 0.0
        self._journal = {}
        world = self.window.world
        if world is None:
            return None
        agents = len(self.window.population.agents) if self.window.population else 0
        if not self._welcomed:
            self._welcomed = True
            return (
                "I'm here while the simulation runs, using {model}. "
                "{source}\n\n"
                "This run started with {agents} agents on a {rows}×{cols} map. "
                "I keep a record of every turn, so you can ask what happened at turn 40, "
                "or tell me your name and what you want to watch. "
                "Exact changes such as “set food cost to 100” still happen immediately."
            ).format(
                model=active_model(),
                source=("Your OpenAI key is in use." if using_openai()
                        else "No OpenAI key is set, so this is the free model and it answers about once every 30 seconds."),
                agents=agents,
                rows=world.rows,
                cols=world.cols,
            )
        return "New run: {agents} agents on a {rows}×{cols} map. Earlier settings that need a restart are in effect now.".format(
            agents=agents, rows=world.rows, cols=world.cols)

    def on_turn(self):
        if self.window.world is None:
            return None
        self._record_turn()
        if not self.narrating:
            self._seen = self._event_lengths()
            self._pending_notes = []
            return None
        self._pending_notes.extend(self._notable_since_last())
        self._seen = self._event_lengths()
        signature = self._signature()
        now = time.monotonic()
        changed = bool(self._pending_notes) or signature != self._last_signature
        if not changed or now < self._narrate_after:
            return None
        self._narrate_after = now + 2.0
        self._last_signature = signature
        notes = self._pending_notes
        self._pending_notes = []
        return self._narration(notes)

    def _clauses(self, text):
        lowered = _norm(text)
        if " and " not in lowered:
            return [text]
        if not re.search(r"\b(set|change|update|increase|decrease|raise|lower|save|load|restart|reset)\b", lowered):
            return [text]
        parts = re.split(r"\s+and\s+", text, flags=re.IGNORECASE)
        return [part.strip() for part in parts if part.strip()]

    def _command_clause(self, text):
        """Return a reply for a direct command, or None if this is conversation."""
        norm = _norm(text)
        if not norm:
            return "Ask what is happening, or name a setting to change."
        if re.search(r"\b(help|what can you do|commands)\b", norm):
            return self._help()
        if re.search(r"\b(start narrat\w*|narrate on|keep narrat\w*|talk me through|walk me through)\b", norm):
            self.narrating = True
            return "I'll narrate as the run moves. I'll speak up when health, jobs, wealth, or the population shift, and when someone is born, dies, or gets sick. Say “stop narrating” to quiet me."
        if re.search(r"\b(stop narrat\w*|narrate off|be quiet|silence)\b", norm):
            self.narrating = False
            return "Narration is off. Ask anytime and I'll still answer."
        if re.search(r"\b(restart|reset|rebuild|new run|start over)\b", norm):
            return self._restart()
        if re.search(r"\b(save|write)\b", norm):
            return self._save(norm)
        if re.search(r"\b(load|open|use preset)\b", norm):
            return self._load(norm)
        if re.search(r"\b(list|show|settings|parameters|config)\b", norm) and not re.search(
                r"\b(set|change|to)\b", norm):
            return self._show(norm)
        change = self._parse_change(norm)
        if change is not None:
            return change
        looked = self._describe_setting(norm)
        if looked is not None:
            return looked
        return None

    def _one(self, text):
        command = self._command_clause(text)
        if command is not None:
            return command
        norm = _norm(text)
        if self.window.world is None:
            return "The simulation hasn't started yet. Once it does, ask me what you're seeing or which setting to change."
        if re.search(r"\bagents?\s+\d+\b", norm) or re.search(r"\b(this agent|selected agent|selection)\b", norm):
            return self._agent_observation(norm)
        if re.search(r"\b(regions?|migrat\w*|housing price|northwest|northeast|southwest|southeast)\b", norm):
            return self._region_observation()
        if re.search(r"\b(wealth|money|job|employ|wage|inequal|gini|econom|rent)\b", norm):
            return self._economy_observation()
        if re.search(r"\b(health|sick|disease|hunger|hospital|stress|mental)\b", norm):
            return self._health_observation()
        if re.search(r"\b(event|just happen|recent|log|died|born)\b", norm):
            return self._events_observation()
        if re.search(r"\b(map|chart|looking at|see|screen)\b", norm):
            return self._view_observation()
        if re.search(r"\b(what|how|why|status|summar|happen|going on|overview|observe|explain)\b", norm):
            return self._overview()
        return (
            "I can explain this run or change a config value. "
            "Try “what's happening”, “explain health”, or “set disease chance to 0.01”. "
            "Say “help” for more."
        )

    def _help(self):
        return (
            "Ask me about the run, or tell me to change a setting.\n\n"
            "Observations: “what's happening”, “why is health changing”, "
            "“how is wealth”, “compare regions”, “what just happened”, “explain agent 3”.\n"
            "Changes: “set food cost to 150”, “increase disease chance by 0.01”, "
            "“decrease type 1 income by 20%”. Live settings apply on the next turn. "
            "Map size, building counts, and starting population apply when you say “restart”.\n"
            "Files: “save as outbreak”, “save”, “load small”. "
            "I write JSON into the configs folder and leave default.json alone unless you name it.\n"
            "Narration: “start narrating” / “stop narrating”.\n"
            "Open questions go to {model}. Ask what happened on a turn, such as "
            "“explain turn 40”, and I'll use the record from that turn. "
            "Tell me your name or what you want to watch and I'll keep that in mind."
        ).format(active_model())

    def finish_model_reply(self, user_text, spoken, actions):
        """Apply any setting changes the model requested and remember the exchange."""
        parts = [spoken] if spoken else []
        for action in actions:
            parts.append(self._one(action))
        reply = "\n\n".join(part for part in parts if part).strip()
        if not reply:
            reply = "I didn't get a clear answer. Ask again, or name a setting directly."
        self._remember(user_text, reply)
        return reply

    def _split_actions(self, reply):
        spoken = []
        actions = []
        for line in str(reply).splitlines():
            match = re.match(r"(?i)^action\s*:\s*(.+)$", line.strip())
            if match:
                actions.append(match.group(1).strip())
            else:
                spoken.append(line)
        return "\n".join(spoken).strip(), actions

    def _remember(self, user_text, reply):
        self._history.append((user_text, reply))
        del self._history[:-8]

    def note_user(self, text):
        """Remember a name or a topic the person asked to watch."""
        name = re.search(
            r"\b(?:my name is|call me)\s+([A-Za-z][A-Za-z' -]{0,40})", text, re.I)
        if name:
            self.user_name = re.split(r"\s+and\s+", name.group(1).strip(), maxsplit=1, flags=re.I)[0].strip()
        if re.search(r"\b(care about|focus on|watch|interested in)\b", text, re.I):
            for topic in ("health", "disease", "wealth", "jobs", "migration", "regions", "housing"):
                if re.search(r"\b{}\b".format(topic), text, re.I):
                    self.focus = topic
                    break

    def _model_messages(self, text):
        if self.window.world is None:
            state = "The simulation has not started yet."
        else:
            state = self._overview()
            selected = getattr(self.window, "selected_id", None)
            if selected:
                state += "\nThe person currently has this agent selected:\n"
                state += self._agent_observation("agent {}".format(selected))
            state += "\n\n" + self._turn_context(text)
        who = self.user_name or "They have not given a name."
        focus = self.focus or "whatever is changing in the run"
        labels = ", ".join(spec["label"] for spec in self._specs()[:16])
        system = (
            "You are the guide sitting with one person while they run a social simulation. "
            "Talk to them directly, by name when you know it. Use only the records below. "
            "Do not invent events, statistics, agents, or files. "
            "When they ask about a turn, explain that turn from its record: what changed and why it matters. "
            "Keep the reply under 140 words.\n"
            "When they clearly ask to change a setting, end with one line per change, exactly like:\n"
            "ACTION: set food cost to 100\n"
            "Ordinary setting names include: {labels}.\n"
            "Do not claim a value changed unless that ACTION line is present. The app applies the line.\n\n"
            "Person: {who}\n"
            "They want you to watch: {focus}.\n\n"
            "Records:\n{state}"
        ).format(labels=labels, who=who, focus=focus, state=state)
        messages = [{"role": "system", "content": system}]
        for past_user, past_reply in self._history[-6:]:
            messages.append({"role": "user", "content": past_user})
            messages.append({"role": "assistant", "content": past_reply})
        messages.append({"role": "user", "content": text})
        return messages

    def _config(self):
        window = self.window
        if window.world is not None and isinstance(getattr(window.world, "config", None), dict):
            return window.world.config
        if isinstance(window.current_config, dict):
            return window.current_config
        return None

    def _specs(self):
        specs = []
        for section, key, aliases, kind, when, step, blurb in PARAMS:
            specs.append({
                "path": (section, key),
                "aliases": aliases,
                "kind": kind,
                "when": when,
                "step": step,
                "blurb": blurb,
                "label": aliases[0],
            })
        config = self._config() or {}
        for name, vals in config.get("Regions", {}).items():
            if not isinstance(vals, dict):
                continue
            nice = name.lower()
            specs.append({
                "path": ("Regions", name, "wage_multiplier"),
                "aliases": (
                    "{} wage".format(nice),
                    "{} wage multiplier".format(nice),
                    "{} pay multiplier".format(nice),
                ),
                "kind": "multiplier",
                "when": "live",
                "step": 0.1,
                "blurb": "Wage multiplier for the {} region.".format(name),
                "label": "{} wage multiplier".format(name),
            })
            specs.append({
                "path": ("Regions", name, "cost_of_living_multiplier"),
                "aliases": (
                    "{} cost of living".format(nice),
                    "{} cost".format(nice),
                    "{} cost multiplier".format(nice),
                ),
                "kind": "multiplier",
                "when": "live",
                "step": 0.1,
                "blurb": "Cost-of-living multiplier for the {} region.".format(name),
                "label": "{} cost of living".format(name),
            })
        return specs

    def _match_param(self, text):
        query = _norm(text)
        query = re.sub(
            r"^(what is|whats|what's|show|the value of|value of|current)\s+", "", query)
        query = re.sub(r"\b(please|now|currently)\b", "", query).strip()
        if not query:
            return None, []
        ranked = []
        for spec in self._specs():
            best = 0
            for alias in spec["aliases"]:
                alias_n = _norm(alias)
                if query == alias_n:
                    best = 1000 + len(alias_n)
                elif alias_n in query:
                    best = max(best, 500 + len(alias_n))
                elif query in alias_n and len(query) > 3:
                    best = max(best, 200 + len(query))
            if best:
                ranked.append((best, spec))
        if not ranked:
            return None, []
        ranked.sort(key=lambda item: item[0], reverse=True)
        top = ranked[0][0]
        tied = [spec for score, spec in ranked if score == top]
        # Prefer the longest alias match; drop shorter section-mates that tied only loosely.
        if len(tied) > 1 and top < 1000:
            labels = {spec["label"] for spec in tied}
            if len(labels) > 1:
                return None, tied
        return tied[0], []

    def _get(self, path):
        current = self._config()
        if current is None:
            return None
        for part in path:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _set(self, path, value):
        config = self._config()
        if config is None:
            return None
        cursor = config
        for part in path[:-1]:
            child = cursor.get(part)
            if not isinstance(child, dict):
                child = {}
                cursor[part] = child
            cursor = child
        old = cursor.get(path[-1])
        cursor[path[-1]] = value
        if self.window.current_config is None:
            self.window.current_config = config
        self._sync_regions()
        return old

    def _sync_regions(self):
        world = self.window.world
        config = self._config()
        if world is None or config is None:
            return
        configured = config.get("Regions", {})
        for region in getattr(world, "regions", []):
            vals = configured.get(region["name"])
            if not isinstance(vals, dict):
                continue
            if "wage_multiplier" in vals:
                region["wage_multiplier"] = vals["wage_multiplier"]
            if "cost_of_living_multiplier" in vals:
                region["cost_multiplier"] = vals["cost_of_living_multiplier"]

    def _coerce(self, spec, raw_value, current):
        kind = spec["kind"]
        try:
            number = float(raw_value)
        except (TypeError, ValueError):
            return None, "I need a number for {}.".format(spec["label"])
        if kind in ("count", "int", "money") and not number.is_integer():
            return None, "{} has to be a whole number.".format(spec["label"].capitalize())
        if kind in ("count", "int", "money"):
            number = int(number)
        if kind == "prob" and not 0 <= number <= 1:
            return None, "{} is a probability, so it needs to stay between 0 and 1.".format(
                spec["label"].capitalize())
        if kind == "multiplier" and number <= 0:
            return None, "{} has to be greater than 0.".format(spec["label"].capitalize())
        if kind == "count" and number < 0:
            return None, "{} can't be negative.".format(spec["label"].capitalize())
        if kind == "money" and number < 0:
            return None, "{} can't be negative.".format(spec["label"].capitalize())
        if spec["path"][-1] == "health_min":
            ceiling = self._get(("Agent & Population", "health_max"))
            if ceiling is not None and number > ceiling:
                return None, "Minimum health can't sit above maximum health ({}).".format(_fmt(ceiling))
        if spec["path"][-1] == "health_max":
            floor = self._get(("Agent & Population", "health_min"))
            if floor is not None and number < floor:
                return None, "Maximum health can't sit below minimum health ({}).".format(_fmt(floor))
        if kind == "int" and spec["path"][-1] in ("health_min", "health_max", "starting_health_min"):
            if not 0 <= number <= 100:
                return None, "Keep health settings between 0 and 100."
        return number, None

    def _parse_change(self, norm):
        multiply = re.search(r"\b(double|triple|halve)\s+(?P<name>.+)$", norm)
        if multiply:
            factor = {"double": 2, "triple": 3, "halve": 0.5}[multiply.group(1)]
            return self._apply_relative(multiply.group("name"), factor=factor)

        assigned = re.search(
            r"\b(?:set|change|update|make)\s+(?P<name>.+?)\s+(?:to|=)\s+(?P<value>-?\d+(?:\.\d+)?)\b",
            norm,
        )
        if assigned:
            return self._apply_absolute(assigned.group("name"), assigned.group("value"))

        relative = re.search(
            r"\b(?P<dir>increase|decrease|raise|lower|reduce|bump)\s+(?P<name>.+?)(?:\s+by\s+(?P<value>-?\d+(?:\.\d+)?)(?P<pct>%)?)\s*$",
            norm,
        )
        if relative:
            return self._apply_relative(
                relative.group("name"),
                direction=relative.group("dir"),
                amount=relative.group("value"),
                percent=bool(relative.group("pct")),
            )
        if re.search(r"\b(set|change|update|increase|decrease|raise|lower)\b", norm):
            return "Name the setting and the number. For example: “set food cost to 150” or “increase disease chance by 0.01”."
        return None

    def _apply_absolute(self, name, raw_value):
        spec, tied = self._match_param(name)
        if tied:
            return self._ambiguous(tied)
        if spec is None:
            return "I don't have a setting called “{}”. Say “show settings” to see the names I can change.".format(name.strip())
        current = self._get(spec["path"])
        value, error = self._coerce(spec, raw_value, current)
        if error:
            return error
        return self._commit(spec, current, value)

    def _apply_relative(self, name, direction=None, amount=None, percent=False, factor=None):
        spec, tied = self._match_param(name)
        if tied:
            return self._ambiguous(tied)
        if spec is None:
            return "I don't have a setting called “{}”.".format(name.strip())
        current = self._get(spec["path"])
        if not isinstance(current, (int, float)):
            return "I couldn't read the current {}.".format(spec["label"])
        if factor is not None:
            updated = current * factor
        elif amount is None:
            step = spec["step"]
            updated = current + step if direction in ("increase", "raise", "bump") else current - step
        elif percent:
            scale = float(amount) / 100.0
            if direction in ("decrease", "lower", "reduce"):
                scale = -scale
            updated = current * (1 + scale)
        else:
            delta = float(amount)
            if direction in ("decrease", "lower", "reduce"):
                delta = -delta
            updated = current + delta
        if spec["kind"] in ("count", "int", "money"):
            updated = int(round(updated))
        value, error = self._coerce(spec, updated, current)
        if error:
            return error
        return self._commit(spec, current, value)

    def _commit(self, spec, old, value):
        if self._config() is None:
            return "There's no active config to edit yet."
        if old == value:
            return "{} is already {}.".format(spec["label"].capitalize(), _fmt(value))
        self._set(spec["path"], value)
        saved = self._write(self.active_file.name if self.active_file else "session.json")
        timing = {
            "live": "Agents read this on the next turn.",
            "birth": "Agents already alive keep their current value. Anyone created after this uses the new one.",
            "restart": "This is stored, and it takes effect when the world is rebuilt. Say “restart” when you want that.",
        }[spec["when"]]
        return "{} is now {} (was {}). {}. {}".format(
            spec["label"].capitalize(), _fmt(value), _fmt(old), timing, saved)

    def _ambiguous(self, specs):
        names = ", ".join(spec["label"] for spec in specs[:6])
        return "That matches more than one setting: {}. Say the full name.".format(names)

    def _describe_setting(self, norm):
        if not re.search(r"\b(what is|whats|what's|explain|describe|current)\b", norm):
            return None
        spec, tied = self._match_param(norm)
        if tied:
            return self._ambiguous(tied)
        if spec is None:
            return None
        value = self._get(spec["path"])
        when = {
            "live": "Changing it affects the running simulation.",
            "birth": "Changing it affects agents created after the change.",
            "restart": "Changing it applies after a restart.",
        }[spec["when"]]
        shown = "unset" if value is None else _fmt(value)
        return "{} is {}. {} {}".format(spec["label"].capitalize(), shown, spec["blurb"], when)

    def _show(self, norm):
        config = self._config()
        if config is None:
            return "No config is loaded yet."
        wanted = None
        for section in (
            "World Settings", "Building Counts", "Agent & Population", "Health & Disease",
            "Economy & Jobs", "Grocery & Needs", "Mental Health & Stress", "Regions", "Migration",
        ):
            if _norm(section) in norm or section.split()[0].lower() in norm.split():
                wanted = section
                break
        if "region" in norm:
            wanted = "Regions"
        lines = []
        for spec in self._specs():
            section = spec["path"][0]
            if wanted and section != wanted:
                continue
            value = self._get(spec["path"])
            if value is None:
                continue
            lines.append("{}: {}".format(spec["label"], _fmt(value)))
        if not lines:
            return "I couldn't find settings for that."
        file_note = self.active_file.name if self.active_file else "session.json (written the next time you change something)"
        header = "Current {} settings".format(wanted) if wanted else "Settings I can change"
        return "{}. The working file is {}.\n{}".format(header, file_note, "\n".join(lines))

    def _file_from_text(self, norm):
        match = re.search(
            r"\b(?:save|load|open|use)\s+(?:the\s+)?(?:preset\s+|config\s+|file\s+)?"
            r"(?:as\s+|to\s+|into\s+)?([a-z0-9][a-z0-9_.-]{0,48})",
            norm,
        )
        if not match:
            match = re.search(r"\b([a-z0-9][a-z0-9_.-]{0,40}\.json)\b", norm)
        if not match:
            return None
        name = match.group(1).strip().replace(" ", "-")
        if name in ("settings", "setting", "it", "this", "that"):
            return None
        if not name.endswith(".json"):
            name += ".json"
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,48}\.json", name):
            return None
        return name

    def _write(self, name):
        config = self._config()
        if config is None:
            return "Nothing to write yet."
        CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        path = CONFIGS_DIR / name
        with path.open("w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=4)
            handle.write("\n")
        self.active_file = path
        return "Saved {}.".format(path.name)

    def _save(self, norm):
        if self._config() is None:
            return "There's no config to save yet."
        name = self._file_from_text(norm)
        if name is None:
            name = self.active_file.name if self.active_file else "session.json"
        if name == "default.json" and "default" not in norm:
            name = "session.json"
        return self._write(name) + " It includes the values from this run."

    def _load(self, norm):
        name = self._file_from_text(norm)
        if name is None:
            files = sorted(path.name for path in CONFIGS_DIR.glob("*.json"))
            if not files:
                return "The configs folder has no JSON files."
            return "Which preset should I load? I see {}.".format(", ".join(files))
        path = CONFIGS_DIR / name
        if not path.exists():
            files = sorted(item.name for item in CONFIGS_DIR.glob("*.json"))
            return "I couldn't find {}. Available files: {}.".format(
                name, ", ".join(files) or "none")
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return "I couldn't read {}: {}.".format(name, error)
        if not isinstance(loaded, dict):
            return "{} isn't a config object.".format(name)
        self._replace_config(loaded)
        self.active_file = path
        self._sync_regions()
        restart = bool(re.search(r"\b(restart|reset)\b", norm))
        message = "Loaded {}. Live values are active now. Map size, buildings, and the starting population change on restart.".format(name)
        if restart:
            message += "\n\n" + self._restart()
        return message

    def _replace_config(self, loaded):
        current = self._config()
        if isinstance(current, dict):
            current.clear()
            current.update(loaded)
            self.window.current_config = current
            if self.window.world is not None:
                self.window.world.config = current
            return
        self.window.current_config = loaded
        if self.window.world is not None:
            self.window.world.config = loaded

    def _restart(self):
        if self._config() is None:
            return "There's no config to restart from yet."
        self.window.restart_from_guide()
        world = self.window.world
        count = len(self.window.population.agents) if self.window.population else 0
        return "Rebuilt the simulation: {} agents on a {}×{} map, using the current config.".format(
            count, world.rows, world.cols)

    def _agents(self):
        population = self.window.population
        return list(population.agents) if population else []

    def _stats(self):
        agents = self._agents()
        count = len(agents)
        if hasattr(self.window, "_stats"):
            stats = dict(self.window._stats())
        else:
            stats = {
                "n": count,
                "health": sum(agent.health for agent in agents) / count if count else 0,
                "wealth": sum(agent.wealth for agent in agents) / count if count else 0,
                "sick": sum(1 for agent in agents if agent.diseases),
                "employed": sum(1 for agent in agents if agent.job),
            }
        stats["hungry"] = sum(1 for agent in agents if agent.hunger < 25)
        stats["hospital"] = sum(1 for agent in agents if agent.hospitalized_at is not None)
        stats["homeless"] = sum(1 for agent in agents if not agent.house)
        mental = [agent.mental_health for agent in agents]
        stats["mental"] = sum(mental) / len(mental) if mental else 0
        return stats

    def _trend(self, key):
        series = self.window.history.get(key, []) if getattr(self.window, "history", None) else []
        if len(series) < 2:
            return None
        window = series[-8:]
        return window[-1] - window[0], len(window) - 1

    def _trend_phrase(self, key, noun):
        change = self._trend(key)
        if not change:
            return None
        delta, turns = change
        if abs(delta) < (0.5 if key == "health" else 1):
            return "{} is holding steady over the last {} turns".format(noun, turns)
        direction = "up" if delta > 0 else "down"
        amount = abs(delta)
        if key == "wealth":
            shown = "${:,.0f}".format(amount)
        else:
            shown = "{:.0f}".format(amount)
        return "{} is {} {} over the last {} turns".format(noun, direction, shown, turns)

    def _overview(self):
        world = self.window.world
        stats = self._stats()
        ever = len(self.window.population.all_agents)
        bits = [
            "Turn {}. {} of {} agents are alive.".format(world.turnNo, stats["n"], ever),
            "Average health is {:.0f}, {} {}, and {} {}.".format(
                stats["health"],
                stats["sick"], "is sick" if stats["sick"] == 1 else "are sick",
                stats["hungry"], "is hungry" if stats["hungry"] == 1 else "are hungry"),
            "{} employed out of {} alive. {} of {} jobs are open.".format(
                stats["employed"], stats["n"], world.open_jobs, len(world.building_jobs)),
            "Average wealth is ${:,.0f}.".format(stats["wealth"]),
        ]
        for key, noun in (("health", "Health"), ("wealth", "Wealth")):
            phrase = self._trend_phrase(key, noun)
            if phrase:
                bits.append(phrase.capitalize() + ".")
        pressure = self._pressure(stats)
        if pressure:
            bits.append(pressure)
        if world.duration_days:
            bits.append("The run is set to stop after {:.0f} days; {:.0f} have elapsed.".format(
                world.duration_days, world.elapsed_days))
        return " ".join(bits)

    def _pressure(self, stats):
        if stats["n"] == 0:
            return "Everyone has died, so the run is finished."
        if stats["sick"] >= max(2, stats["n"] // 4):
            chance = self._get(("Health & Disease", "disease_chance_per_turn"))
            impact = self._get(("Health & Disease", "disease_health_impact"))
            return (
                "The clearest pressure is disease: {} people are sick. "
                "Natural infection chance is {} per turn and each bout costs {} health."
            ).format(stats["sick"], _fmt(chance), _fmt(impact))
        if stats["hungry"] >= max(2, stats["n"] // 4):
            cost = self._get(("Grocery & Needs", "grocery_food_cost"))
            return "A lot of people are hungry. Food costs ${} before regional prices, so agents who can't pay will keep losing health.".format(
                _fmt(cost))
        if stats["employed"] * 2 < stats["n"] and stats["n"] > 2:
            return "Employment is thin. Unemployed agents earn nothing, which feeds both migration and financial stress."
        gini = self.window.population.wealth_gini_coefficient()
        if gini is not None and gini >= 0.45:
            return "Wealth is uneven (Gini {:.2f}). The wealth chart shows that as a curve bending away from the diagonal.".format(gini)
        return "Nothing is dominating the run right now. Health, jobs, and hunger are all in a moderate range."

    def _health_observation(self):
        stats = self._stats()
        world = self.window.world
        causes = {}
        for event in world.death_events[-12:]:
            causes[event.get("cause", "unknown")] = causes.get(event.get("cause", "unknown"), 0) + 1
        recent_sick = len(world.disease_events[-12:])
        lines = [
            self._overview(),
            "Average mental health is {:.0f}. {} are in hospital and {} are hungry enough to be flagged.".format(
                stats["mental"], stats["hospital"], stats["hungry"]),
        ]
        if recent_sick:
            names = []
            for event in world.disease_events[-6:]:
                name = event.get("disease")
                if name and name not in names:
                    names.append(name)
            counted = "{} infection{}".format(recent_sick, "" if recent_sick == 1 else "s")
            if names:
                lines.append("The latest disease log has {}. Recent illnesses: {}.".format(
                    counted, ", ".join(names)))
            else:
                lines.append("The latest disease log has {}.".format(counted))
        if causes:
            listed = ", ".join("{} from {}".format(count, cause) for cause, count in causes.items())
            lines.append("Recent deaths: {}.".format(listed))
        lines.append(
            "Hunger drops by {} each turn, food restores {} health, and a hospital stay lasts {} turns.".format(
                _fmt(self._get(("Grocery & Needs", "hunger_drain_per_step"))),
                _fmt(self._get(("Grocery & Needs", "grocery_food_health_restore"))),
                _fmt(self._get(("Health & Disease", "hospital_stay_duration_turns"))),
            )
        )
        return " ".join(lines)

    def _economy_observation(self):
        world = self.window.world
        stats = self._stats()
        gini = self.window.population.wealth_gini_coefficient()
        gini_text = "n/a" if gini is None else "{:.3f}".format(gini)
        phrase = self._trend_phrase("wealth", "average wealth")
        regions = sorted(world.regions, key=lambda region: region.get("avg_wealth", 0), reverse=True)
        richest = regions[0]["name"] if regions else "nowhere"
        lines = [
            "Average wealth is ${:,.0f} across {} living agents. {} are employed and {} are homeless. Gini is {}.".format(
                stats["wealth"], stats["n"], stats["employed"], stats["homeless"], gini_text),
        ]
        if phrase:
            lines.append(phrase.capitalize() + ".")
        lines.append(
            "Type 1 jobs pay ${} a turn and type 2 jobs pay ${}, before regional wages. {} currently has the highest average wealth.".format(
                _fmt(self._get(("Economy & Jobs", "type_1_income_per_turn"))),
                _fmt(self._get(("Economy & Jobs", "type_2_income_per_turn"))),
                richest,
            )
        )
        lines.append("Open the wealth chart to see the Lorenz curve. A higher Gini means the curve bends farther from the straight diagonal.")
        return " ".join(lines)

    def _region_observation(self):
        world = self.window.world
        lines = ["The map is split into {} regions.".format(len(world.regions))]
        for region in world.regions:
            members = [agent for agent in self._agents() if agent.region == region["id"]]
            lines.append(
                "{name} ({country}): {pop} living here, avg wealth ${wealth:,.0f}, {jobs} open jobs, wage ×{wage}, cost of living ×{cost}, housing ×{house:.2f}.".format(
                    name=region["name"],
                    country=region.get("country", "unknown"),
                    pop=len(members),
                    wealth=region.get("avg_wealth", 0),
                    jobs=region.get("open_jobs", 0),
                    wage=_fmt(region.get("wage_multiplier", 1)),
                    cost=_fmt(region.get("cost_multiplier", 1)),
                    house=region.get("housing_price_factor", 1),
                )
            )
        moves = len(getattr(world, "migration_events", [])[-10:])
        if moves:
            lines.append("There are {} recent migration records. Move cost is ${} and the base chance is {}.".format(
                moves,
                _fmt(self._get(("Migration", "move_cost"))),
                _fmt(self._get(("Migration", "base_chance"))),
            ))
        else:
            lines.append("Nobody has a recent migration on record. Agents compare wages, jobs, and housing prices before they pay ${} to move.".format(
                _fmt(self._get(("Migration", "move_cost")))))
        return "\n".join(lines)

    def _events_observation(self):
        world = self.window.world
        items = []
        catalog = (
            ("hiring_events", lambda e: "Turn {}: agent {} was hired for {}.".format(e["turn"], e["agent_id"], e["job"])),
            ("death_events", lambda e: "Turn {}: agent {} died from {} at age {}.".format(e["turn"], e["agent_id"], e["cause"], e["age"])),
            ("birth_events", lambda e: "Turn {}: agent {} was born.".format(e["turn"], e["agent_id"])),
            ("disease_events", lambda e: "Turn {}: agent {} caught {}.".format(e["turn"], e["agent_id"], e["disease"])),
            ("house_events", lambda e: "Turn {}: agent {} {} a house.".format(e["turn"], e["agent_id"], e["event"])),
            ("grocery_events", lambda e: "Turn {}: agent {} bought food for ${:,}.".format(e["turn"], e["agent_id"], e["cost"])),
            ("migration_events", lambda e: "Turn {}: agent {} migrated.".format(e.get("turn", "?"), e.get("agent_id", "?"))),
        )
        for name, render in catalog:
            for event in getattr(world, name, [])[-4:]:
                try:
                    items.append((event.get("turn", 0), render(event)))
                except (KeyError, TypeError):
                    continue
        if not items:
            return "The event lists are still empty. Start the run and I'll have births, jobs, illness, and moves to walk through."
        items.sort(key=lambda item: item[0])
        return "Latest notable events:\n" + "\n".join(text for _, text in items[-8:])

    def _agent_observation(self, norm):
        match = re.search(r"\bagents?\s+(\d+)\b", norm)
        agent_id = int(match.group(1)) if match else getattr(self.window, "selected_id", None)
        if agent_id is None:
            return "Click an agent on the map or say “explain agent 4”."
        agent = self.window._find_agent(agent_id) if hasattr(self.window, "_find_agent") else None
        if agent is None:
            return "I can't find agent {}.".format(agent_id)
        alive = agent in self._agents()
        region = "unknown"
        if self.window.world and 0 <= agent.region < len(self.window.world.regions):
            region = self.window.world.regions[agent.region]["name"]
        status = "alive" if alive else "deceased"
        diseases = ", ".join(sorted(agent.diseases)) or "none"
        return (
            "Agent {id} is {status}. Age {age}, health {hp}/100, mental health {mental}/100, "
            "hunger {hunger}/{hunger_max}, wealth ${wealth:,}. Job: {job}. Home: {home}. "
            "Region: {region}. Diseases: {diseases}."
        ).format(
            id=agent.id,
            status=status,
            age=agent.age,
            hp=agent.health,
            mental=agent.mental_health,
            hunger=agent.hunger,
            hunger_max=agent.hunger_max,
            wealth=agent.wealth,
            job=agent.job or "unemployed",
            home="({}, {})".format(*agent.house) if agent.house else "homeless",
            region=region,
            diseases=diseases,
        )

    def _view_observation(self):
        view = getattr(self.window, "view", "map")
        if view == "wealth":
            return self._economy_observation()
        selected = getattr(self.window, "selected_id", None)
        base = self._overview() + " You're on the map. Dots are agents and squares are buildings. Regions are tinted blocks."
        if selected:
            return base + " " + self._agent_observation("agent {}".format(selected))
        return base + " Click an agent if you want me to walk through that person."

    WATCHED_EVENTS = (
        "hiring_events", "job_quit_events", "job_application_events", "death_events",
        "disease_events", "birth_events", "hospital_events", "house_events",
        "grocery_events", "school_events", "money_transfer_events",
        "relationship_events", "migration_events",
    )

    def _event_lengths(self):
        world = self.window.world
        if world is None:
            return {}
        return {name: len(getattr(world, name, [])) for name in self.WATCHED_EVENTS}

    def _record_turn(self):
        """Save this turn's stats and new events so a later question can replay it."""
        world = self.window.world
        if world is None:
            return
        turn = world.turnNo
        current = self._event_lengths()
        events = []
        for name in self.WATCHED_EVENTS:
            start = self._seen.get(name, 0)
            for event in getattr(world, name, [])[start:current.get(name, 0)]:
                line = self._format_event(name, event)
                if line:
                    events.append(line)
        stats = self._stats()
        self._journal[turn] = {
            "summary": (
                "{alive} alive, health {health:.0f}, {sick} sick, {hungry} hungry, "
                "{employed} employed, average wealth ${wealth:,.0f}"
            ).format(
                alive=stats["n"], health=stats["health"], sick=stats["sick"],
                hungry=stats["hungry"], employed=stats["employed"], wealth=stats["wealth"],
            ),
            "events": events[:40],
        }

    def _format_event(self, name, event):
        agent = event.get("agent_id", "?")
        if name == "hiring_events":
            return "Agent {} was hired for {}.".format(agent, event.get("job"))
        if name == "job_quit_events":
            return "Agent {} {}; the job reopened.".format(agent, event.get("reason"))
        if name == "job_application_events":
            if event.get("hired"):
                return None
            return "Agent {} was rejected for {}.".format(agent, event.get("job"))
        if name == "death_events":
            return "Agent {} died from {} at age {}.".format(agent, event.get("cause"), event.get("age"))
        if name == "disease_events":
            return "Agent {} caught {}.".format(agent, event.get("disease"))
        if name == "birth_events":
            return "Agent {} was born.".format(agent)
        if name == "hospital_events":
            diseases = ", ".join(event.get("diseases") or []) or "an illness"
            return "Agent {} was admitted to hospital with {}.".format(agent, diseases)
        if name == "house_events":
            return "Agent {} {} a house.".format(agent, event.get("event"))
        if name == "grocery_events":
            return "Agent {} bought food for ${:,}.".format(agent, event.get("cost", 0))
        if name == "school_events":
            return "Agent {} {}.".format(agent, "enrolled" if event.get("event") == "enrolled" else "finished school")
        if name == "money_transfer_events":
            return "{} gave ${:,} to {} ({}).".format(
                event.get("from_name"), event.get("amount", 0), event.get("to_name"), event.get("reason"))
        if name == "relationship_events":
            if not event.get("stage_changed"):
                return None
            return "{} and {} are now {}.".format(
                event.get("first_name"), event.get("second_name"), event.get("stage"))
        if name == "migration_events":
            return "Agent {} migrated.".format(agent)
        return None

    def _turns_mentioned(self, text):
        found = []
        for match in re.finditer(r"\bturns?\s+(\d+)\s*(?:to|through|-)\s*(\d+)", text, re.I):
            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                start, end = end, start
            found.extend(range(start, min(end, start + 12) + 1))
        for match in re.finditer(r"\bturn\s+(\d+)\b", text, re.I):
            found.append(int(match.group(1)))
        ordered = []
        for number in found:
            if number not in ordered:
                ordered.append(number)
        return ordered[:12]

    def _turn_context(self, text):
        world = self.window.world
        current = world.turnNo if world is not None else 0
        requested = self._turns_mentioned(text)
        if requested:
            turns = requested
        else:
            turns = sorted(self._journal)[-6:]
        if not turns:
            return "No turns have been recorded yet. The run is on turn {}.".format(current)
        lines = []
        for turn in turns:
            if turn > current or turn not in self._journal:
                lines.append("Turn {}: not recorded. The run is on turn {}.".format(turn, current))
                continue
            entry = self._journal[turn]
            lines.append("Turn {}: {}.".format(turn, entry["summary"]))
            if entry["events"]:
                lines.extend("  " + line for line in entry["events"][:20])
            else:
                lines.append("  No births, deaths, jobs, illness, or moves were recorded.")
        return "\n".join(lines)

    def _notable_since_last(self):
        current = self._event_lengths()
        notes = []
        labels = {
            "death_events": "deaths",
            "birth_events": "births",
            "disease_events": "new infections",
            "hiring_events": "hires",
            "migration_events": "moves",
        }
        for name, label in labels.items():
            delta = current.get(name, 0) - self._seen.get(name, 0)
            if delta > 0:
                notes.append((label, delta))
        return notes

    def _signature(self):
        if self.window.world is None:
            return None
        stats = self._stats()
        return (
            self.window.world.turnNo // 5,
            stats["n"],
            stats["sick"],
            stats["employed"],
            round(stats["health"]),
            round(stats["wealth"] / 100),
        )

    def _narration(self, notable):
        world = self.window.world
        stats = self._stats()
        sentence = "Turn {}. {} alive, health {:.0f}, {} sick, {} employed, avg wealth ${:,.0f}.".format(
            world.turnNo, stats["n"], stats["health"], stats["sick"], stats["employed"], stats["wealth"])
        if notable:
            totals = {}
            for label, count in notable:
                totals[label] = totals.get(label, 0) + count
            summary = ", ".join("{} {}".format(count, label) for label, count in totals.items())
            sentence += " Since I last checked: {}.".format(summary)
        trend = self._trend_phrase("health", "health")
        if trend and "steady" not in trend:
            sentence += " " + trend.capitalize() + "."
        return sentence
