"""CPU-only arithmetic, provenance and document-contract regression checks."""
import json
import unittest

import build_hy4_flops as report


class HY4LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((report.OUT / "hy4-config.json").read_text())
        cls.ledger = report.build_ledger(cls.config)
        cls.ops = {op["key"]: op for op in cls.ledger["ops"]}

    def test_pairs_against_brute_force(self):
        for n in [1, 5, 2047, 2048, 2049, 100000]:
            self.assertEqual(report.selected_pairs(n, 2048), sum(min(t, 2048) for t in range(1, n + 1)))

    def test_original_glm_reconciliation(self):
        self.assertEqual(self.ledger["totals"]["glm"] + 46_080_000_000, report.PUBLISHED_GLM)

    def test_common_backbone(self):
        for key in ["qa", "qb", "absorb", "vexpand", "outproj", "idxq", "idxk", "idxw", "idxscore", "qk", "pv"]:
            self.assertEqual(self.ops[key]["hy_total"], self.ops[key]["glm_total"], key)

    def test_gate_independent_calculation(self):
        self.assertEqual(self.ops["gate"]["hy_total"], 1_570_347_417_600_000)
        self.assertEqual(self.ops["gate"]["hy"], self.ops["outproj"]["hy"])

    def test_hy_total_regression(self):
        self.assertEqual(self.ledger["totals"]["hy"], 12_593_012_513_084_960)

    def test_tree_unique_complete_ownership(self):
        keys = [k for node in report.TREE for k in report.keys(node)]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), set(self.ops))

    def test_layer_and_component_sums(self):
        for m in ["hy", "glm"]:
            total = self.ledger["totals"][m]
            self.assertEqual(sum(v[m] for v in self.ledger["categories"].values()), total)
            global_ops = sum(op[m] for op in self.ops.values() if op["scope"] == "global")
            self.assertEqual(sum(row[m] for row in self.ledger["layers"]) + global_ops, total)

    def test_counts_and_index_placement(self):
        self.assertEqual(self.ops["idxscore"]["hy_count"], 21)
        self.assertEqual(self.ops["idxscore"]["glm_count"], 21)
        self.assertEqual(self.ops["router"]["hy_count"], 77)
        self.assertEqual(self.ops["densegu"]["hy_count"], 1)
        self.assertNotIn(2, self.ops["idxscore"]["hy_layers"])
        self.assertIn(5, self.ops["idxscore"]["hy_layers"])
        self.assertEqual(self.ops["reuseids"]["hy_count"], 57)
        self.assertIn(2, self.ops["reuseids"]["hy_layers"])

    def test_config_drift_is_not_silent(self):
        changed = dict(self.config, hidden_size=8192)
        with self.assertRaises(AssertionError):
            report.build_ledger(changed)

    def test_sources_exist_and_are_pinned(self):
        evidence = json.loads((report.OUT / "source-audit.json").read_text())
        self.assertEqual(evidence["revision"], report.REV)
        for op in self.ops.values():
            self.assertIn(report.REV, report.source_link(evidence, op["source"], op["anchor"]))

    def test_html_contract(self):
        page = (report.OUT / "index.html").read_text()
        for section in ["overview", "scope", "execution-tree", "ihc", "comparison", "layer-map", "runtime", "sources"]:
            self.assertIn(f'id="{section}"', page)
        self.assertNotIn("@@", page)
        self.assertIn('data-maas-annotator', page)
        self.assertIn('max-width:1560px', page)


if __name__ == "__main__":
    unittest.main()
