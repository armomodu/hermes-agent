import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_module(
    "bernard_validator",
    ROOT / "scripts" / "validate_decomposition_json.py",
)
builder = load_module(
    "bernard_builder",
    ROOT / "scripts" / "build_contract_decomposition.py",
)


class PlanPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads(
            (ROOT / "tests" / "fixtures" / "plan-policy-contracts.json").read_text()
        )

    def findings(self, name: str, *, read_only: bool):
        return validator.collect_task_contract_local_findings(
            self.fixtures[name],
            name,
            strict_plan=True,
            strict_graph=False,
            allow_read_only=read_only,
        )

    def test_cross_layer_fixture(self):
        self.assertEqual(self.findings("validExecution", read_only=False), [])
        self.assertEqual(self.findings("validReadOnlyReview", read_only=True), [])
        codes = {
            finding["code"]
            for finding in self.findings("invalidReadOnlyReview", read_only=True)
        }
        self.assertIn("read_only_execution_plan_applies_change", codes)
        self.assertIn("read_only_execution_plan_expected_changes", codes)

    def test_builder_uses_the_read_only_sequence(self):
        contract = self.fixtures["validReadOnlyReview"]
        plan = {
            "outcome": "The gate independently verifies the integrated workflow result",
            "inspect": "Inspect the live workflow authority.",
            "derive": "Compare the integrated result with authority.",
            "verify": "Run the focused workflow proof.",
            "completionChecks": ["The integrated workflow satisfies the objective contract."],
        }
        built = builder.build_execution_plan(
            contract,
            plan,
            "gate",
            read_only=True,
        )

        self.assertEqual(
            [step["kind"] for step in built["steps"]],
            ["inspect_authority", "derive_delta", "verify"],
        )
        self.assertEqual(built["expectedChanges"], [])


if __name__ == "__main__":
    unittest.main()
