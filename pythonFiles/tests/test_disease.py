import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pythonFiles.disease import (
    DISEASES,
    IMMUNE_SYSTEM_LENGTH,
    activate_pending_infections,
    combine_parent_immune_systems,
    disease_hunger_cost,
    find_best_match,
    introduce_disease,
    is_immune,
    process_disease_turn,
    random_immune_system,
)


class DiseaseModelTests(unittest.TestCase):
    def test_patterns_fit_immune_system_and_matching_slides(self):
        self.assertTrue(all(2 <= len(disease.pattern) <= 14
                            for disease in DISEASES.values()))
        self.assertTrue(all(len(disease.pattern) <= IMMUNE_SYSTEM_LENGTH
                            for disease in DISEASES.values()))
        ordered_by_contagiousness = sorted(
            DISEASES.values(), key=lambda disease: disease.contagiousness,
            reverse=True,
        )
        self.assertEqual(
            [len(disease.pattern) for disease in ordered_by_contagiousness],
            sorted(
                (len(disease.pattern) for disease in DISEASES.values()),
                reverse=True,
            ),
        )

        disease = DISEASES["common_cold"]
        immune_system = (
            "0" * 7 + disease.pattern
            + "0" * (IMMUNE_SYSTEM_LENGTH - 7 - len(disease.pattern))
        )
        self.assertTrue(is_immune(immune_system, "common_cold"))
        self.assertEqual(find_best_match("0" * 50, "10101"), (0, (0, 2, 4)))

    def test_matching_accepts_patterns_from_two_to_fourteen_bits(self):
        self.assertEqual(find_best_match("0" * 50, "01")[0], 0)
        self.assertEqual(find_best_match("0" * 50, "0" * 14)[0], 0)
        for pattern in ("0", "0" * 15):
            with self.subTest(length=len(pattern)):
                with self.assertRaises(ValueError):
                    find_best_match("0" * 50, pattern)

    def test_random_and_recombined_immune_systems_are_50_bits(self):
        self.assertEqual(len(random_immune_system()), IMMUNE_SYSTEM_LENGTH)
        first = "0" * IMMUNE_SYSTEM_LENGTH
        second = "1" * IMMUNE_SYSTEM_LENGTH
        with patch("pythonFiles.disease.random.choice", side_effect=lambda values: values[1]):
            child = combine_parent_immune_systems(first, second)
        self.assertEqual(child, second)
        self.assertEqual(len(child), IMMUNE_SYSTEM_LENGTH)

    def test_exposure_waits_until_next_turn_and_immune_neighbors_are_skipped(self):
        pattern = DISEASES["common_cold"].pattern
        source = SimpleNamespace(
            id=1, pos_x=0, pos_y=0, immune_system="0" * 50,
            diseases={"common_cold"}, pending_diseases=set(), health=100,
            hospitalized_at=None,
        )
        susceptible = SimpleNamespace(
            id=2, pos_x=0, pos_y=1, immune_system="0" * 50,
            diseases=set(), pending_diseases=set(), health=100,
            hospitalized_at=None,
        )
        immune = SimpleNamespace(
            id=3, pos_x=1, pos_y=0,
            immune_system=(
                "0" * 7 + pattern
                + "0" * (IMMUNE_SYSTEM_LENGTH - 7 - len(pattern))
            ),
            diseases=set(), pending_diseases=set(), health=100,
            hospitalized_at=None,
        )
        chain_target = SimpleNamespace(
            id=4, pos_x=0, pos_y=2, immune_system="0" * 50,
            diseases=set(), pending_diseases=set(), health=100,
            hospitalized_at=None,
        )
        world = SimpleNamespace(
            turnNo=0, config={"Health & Disease": {
                "community_case_chance_per_turn": 0,
            }}, disease_events=[],
        )

        with patch("pythonFiles.disease.random.random", return_value=0):
            process_disease_turn(
                [source, susceptible, immune, chain_target], world
            )

        self.assertEqual(susceptible.pending_diseases, {"common_cold"})
        self.assertFalse(susceptible.diseases)
        self.assertFalse(immune.pending_diseases)
        self.assertEqual(chain_target.pending_diseases, {"common_cold"})
        activate_pending_infections([susceptible])
        self.assertEqual(susceptible.diseases, {"common_cold"})

    def test_one_bit_is_repaired_per_turn_or_two_in_hospital(self):
        def sick_agent(hospitalized_at=None):
            return SimpleNamespace(
                id=1, immune_system="0" * 50, diseases={"measles"},
                pending_diseases=set(), hospitalized_at=hospitalized_at,
            )

        world = SimpleNamespace(
            turnNo=0, config={"Health & Disease": {
                "community_case_chance_per_turn": 0,
            }}, disease_events=[],
        )
        regular = sick_agent()
        hospitalized = sick_agent((0, 0))

        process_disease_turn([regular], world)
        process_disease_turn([hospitalized], world)

        self.assertEqual(
            sum(a != b for a, b in zip("0" * 50, regular.immune_system)), 1
        )
        self.assertEqual(
            sum(a != b for a, b in zip("0" * 50, hospitalized.immune_system)), 2
        )

    def test_multiple_diseases_share_one_repair_and_use_fixed_priority(self):
        agent = SimpleNamespace(
            id=1, immune_system="0" * 50,
            diseases={"common_cold", "measles"}, pending_diseases=set(),
            hospitalized_at=None,
        )
        world = SimpleNamespace(
            turnNo=0, config={"Health & Disease": {
                "community_case_chance_per_turn": 0,
            }}, disease_events=[],
        )

        process_disease_turn([agent], world)

        self.assertEqual(
            sum(a != b for a, b in zip("0" * 50, agent.immune_system)), 1
        )
        self.assertEqual(agent.diseases, {"common_cold", "measles"})

    def test_hunger_cost_scales_with_active_disease_pattern_length(self):
        agent = SimpleNamespace(diseases={"common_cold"})
        cold_cost = disease_hunger_cost(agent)
        agent.diseases = {"measles"}
        self.assertGreater(disease_hunger_cost(agent), cold_cost)
        agent.diseases.clear()
        self.assertEqual(disease_hunger_cost(agent), 0)

    def test_user_introduction_queues_infection_and_respects_immunity(self):
        agent = SimpleNamespace(
            id=5, immune_system="0" * 50,
            diseases=set(), pending_diseases=set(), health=100,
        )
        world = SimpleNamespace(turnNo=4, disease_events=[])

        self.assertTrue(introduce_disease(agent, "common_cold", world))
        self.assertEqual(agent.pending_diseases, {"common_cold"})
        self.assertFalse(agent.diseases)
        self.assertEqual(world.disease_events[0]["turn"], 5)
        self.assertEqual(world.disease_events[0]["source"], "user")
        self.assertFalse(introduce_disease(agent, "common_cold", world))

        immune_agent = SimpleNamespace(
            id=6, immune_system=(
                "0" * 7 + DISEASES["common_cold"].pattern
                + "0" * (
                    IMMUNE_SYSTEM_LENGTH - 7
                    - len(DISEASES["common_cold"].pattern)
                )
            ),
            diseases=set(), pending_diseases=set(), health=100,
        )
        self.assertFalse(introduce_disease(immune_agent, "common_cold", world))


if __name__ == "__main__":
    unittest.main()
