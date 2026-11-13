import unittest
from unittest.mock import patch

import networkx as nx

from scripts import generate_from_prompt, main_generate_loop


class GenerateForcedLoopGraphRestorationTest(unittest.TestCase):
    def setUp(self):
        self.graph = nx.MultiDiGraph()
        self.graph.add_node("start", y=0, x=0)
        self.graph.add_node("waypoint", y=1000 / 111000, x=0)
        self.graph.add_node("beginner", y=0.004, x=0.001)
        self.graph.add_node("regular", y=0.004, x=-0.001)
        self.graph.add_edge("start", "beginner", key="out-a", length=100, cost_debutant=1, cost_confirme=10, cost_expert=10)
        self.graph.add_edge("start", "beginner", key="out-a-parallel", length=250, cost_debutant=2, cost_confirme=11, cost_expert=11)
        self.graph.add_edge("beginner", "waypoint", key="in-a", length=100, cost_debutant=1, cost_confirme=10, cost_expert=10)
        self.graph.add_edge("start", "regular", key="out-b", length=300, cost_debutant=10, cost_confirme=1, cost_expert=1)
        self.graph.add_edge("regular", "waypoint", key="in-b", length=300, cost_debutant=10, cost_confirme=1, cost_expert=1)
        self.graph.add_edge("waypoint", "start", key="back", length=200, cost_debutant=1, cost_confirme=1, cost_expert=1)

    def snapshot(self):
        return sorted(
            (u, v, key, dict(data))
            for u, v, key, data in self.graph.edges(keys=True, data=True)
        )

    def test_restores_graph_after_success_and_exception(self):
        for module in (generate_from_prompt, main_generate_loop):
            with self.subTest(module=module.__name__):
                before = self.snapshot()
                result = module.generate_forced_loop(
                    self.graph, "start", 0, 0, 3000, "débutant", 0
                )
                self.assertIsNotNone(result)
                self.assertEqual(self.snapshot(), before)

                original_dijkstra = nx.single_source_dijkstra
                calls = 0

                def fail_on_return(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise RuntimeError("return calculation failed")
                    return original_dijkstra(*args, **kwargs)

                with patch.object(module.nx, "single_source_dijkstra", fail_on_return):
                    with self.assertRaisesRegex(RuntimeError, "return calculation failed"):
                        module.generate_forced_loop(
                            self.graph, "start", 0, 0, 3000, "débutant", 0
                        )
                self.assertEqual(self.snapshot(), before)

                calls = 0

                def no_return_path(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise nx.NetworkXNoPath
                    return original_dijkstra(*args, **kwargs)

                with patch.object(module.nx, "single_source_dijkstra", no_return_path):
                    self.assertIsNone(
                        module.generate_forced_loop(
                            self.graph, "start", 0, 0, 3000, "débutant", 0
                        )
                    )
                self.assertEqual(self.snapshot(), before)

    def test_prompt_profiles_use_graph_costs_and_missing_cost_fails(self):
        for module in (generate_from_prompt, main_generate_loop):
            with self.subTest(module=module.__name__):
                beginner = module.generate_forced_loop(
                    self.graph, "start", 0, 0, 3000, "débutant", 0
                )
                confirmed = module.generate_forced_loop(
                    self.graph, "start", 0, 0, 3000, "confirmé", 0
                )
                expert = module.generate_forced_loop(
                    self.graph, "start", 0, 0, 3000, "expert", 0
                )
                self.assertEqual(beginner[0], ["start", "beginner", "waypoint"])
                self.assertEqual(confirmed[0], ["start", "regular", "waypoint"])
                self.assertEqual(expert[0], ["start", "regular", "waypoint"])

                del self.graph["start"]["beginner"]["out-a"]["cost_confirme"]
                with self.assertRaisesRegex(ValueError, "cost_confirme"):
                    module.generate_forced_loop(
                        self.graph, "start", 0, 0, 3000, "confirmé", 0
                    )
                self.graph["start"]["beginner"]["out-a"]["cost_confirme"] = 10

    def test_total_distance_uses_meter_lengths_of_profile_selected_edges(self):
        path = ["start", "beginner", "waypoint"]
        self.assertEqual(
            generate_from_prompt.total_distance(self.graph, path, "cost_debutant"),
            200,
        )


if __name__ == "__main__":
    unittest.main()
