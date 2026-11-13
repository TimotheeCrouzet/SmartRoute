import unittest
from unittest.mock import patch

import networkx as nx

from scripts import generate_from_prompt, main_generate_loop


class GenerateForcedLoopGraphRestorationTest(unittest.TestCase):
    def setUp(self):
        self.graph = nx.MultiDiGraph()
        self.graph.add_node("start", y=0, x=0)
        self.graph.add_node("waypoint", y=1000 / 111000, x=0)
        self.graph.add_edge("start", "waypoint", key="out-a", cost_test=1, profile="a")
        self.graph.add_edge("start", "waypoint", key="out-b", cost_test=2, profile="b")
        self.graph.add_edge("waypoint", "start", key="back", cost_test=1, profile="return")

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
                    self.graph, "start", 0, 0, 3000, "test", 0
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
                            self.graph, "start", 0, 0, 3000, "test", 0
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
                            self.graph, "start", 0, 0, 3000, "test", 0
                        )
                    )
                self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
