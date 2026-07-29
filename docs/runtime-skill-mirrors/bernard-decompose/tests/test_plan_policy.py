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
        built_contract = {**contract, "executionPlan": built}
        self.assertEqual(
            validator.collect_task_contract_local_findings(
                built_contract,
                "gate",
                strict_plan=True,
                strict_graph=False,
                allow_read_only=True,
            ),
            [],
        )

    def test_builder_output_passes_validator_for_execution(self):
        contract = self.fixtures["validExecution"]
        built = builder.build_execution_plan(
            contract,
            {
                "outcome": "The workflow implementation matches its authority and focused proof",
                "inspect": "Inspect the live workflow authority.",
                "derive": "Derive the smallest implementation delta.",
                "apply": "Apply only the bounded workflow change.",
                "verify": "Run the focused workflow proof.",
                "operation": "modify",
                "symbols": ["runWorkflow"],
                "invariant": "Existing workflow transitions remain unchanged.",
                "completionChecks": ["The focused workflow proof passes."],
            },
            "execution",
        )
        built_contract = {**contract, "executionPlan": built}
        self.assertEqual(
            validator.collect_task_contract_local_findings(
                built_contract,
                "execution",
                strict_plan=True,
                strict_graph=False,
                allow_read_only=False,
            ),
            [],
        )

    def test_builder_rejects_authored_execution_plan(self):
        contract = {
            "executionPlan": self.fixtures["validExecution"]["executionPlan"],
        }
        with self.assertRaisesRegex(
            ValueError,
            "executionPlan is generated output",
        ):
            builder.canonical_plan_input(contract, "legacy-plan")

    def test_builder_canonicalizes_exact_proof_only_slice(self):
        contract = {
            "primaryArtifactClass": "code",
            "mutationRoot": "src/lib/example.test.ts",
            "proofRoot": "src/lib/example.test.ts",
            "writableFiles": ["src/lib/example.test.ts"],
            "proofFiles": ["src/lib/example.test.ts"],
            "createdFileGlobs": ["src/lib/example.test.ts"],
        }
        self.assertEqual(
            builder.canonical_artifact_class(contract, "proof"),
            "proof",
        )

    def test_builder_does_not_reclassify_implementation(self):
        contract = {
            "primaryArtifactClass": "code",
            "mutationRoot": "src/lib/example.ts",
            "proofRoot": "src/lib/example.test.ts",
            "writableFiles": ["src/lib/example.ts"],
            "proofFiles": [],
            "createdFileGlobs": [],
        }
        self.assertEqual(
            builder.canonical_artifact_class(contract, "implementation"),
            "code",
        )

    def test_builder_preserves_special_proof_classes(self):
        contract = {
            "primaryArtifactClass": "integration_proof",
            "mutationRoot": "src/lib/integration.test.ts",
            "proofRoot": "src/lib/integration.test.ts",
            "writableFiles": ["src/lib/integration.test.ts"],
            "proofFiles": ["src/lib/integration.test.ts"],
            "createdFileGlobs": ["src/lib/integration.test.ts"],
        }
        self.assertEqual(
            builder.canonical_artifact_class(contract, "integration"),
            "integration_proof",
        )

    def test_validator_rejects_untruthful_docs_proof_root(self):
        contract = {
            **self.fixtures["validExecution"],
            "primaryArtifactClass": "docs",
            "mutationRoot": "docs/workflow.md",
            "proofRoot": "src/docs/workflow.md",
            "writableFiles": ["docs/workflow.md"],
            "proofFiles": [],
            "createdFileGlobs": ["docs/workflow.md"],
            "verification": {"focusedTests": [], "qualityGates": []},
        }
        codes = {
            finding["code"]
            for finding in validator.collect_task_contract_local_findings(
                contract,
                "docs",
                strict_plan=True,
                strict_graph=True,
            )
        }
        self.assertIn("docs_proof_root_mismatch", codes)
        self.assertEqual(
            builder.canonical_proof_root(contract, "docs"),
            contract["mutationRoot"],
        )

    def test_builder_infers_docs_from_markdown_mutation_root(self):
        contract = {
            "mutationRoot": "apps/mission-control/docs/knowledge-plane/guide.md",
            "proofRoot": "apps/mission-control/src/lib/storage/types.ts",
            "writableFiles": ["apps/mission-control/docs/knowledge-plane/guide.md"],
            "proofFiles": [],
            "createdFileGlobs": ["apps/mission-control/docs/knowledge-plane/guide.md"],
        }
        self.assertEqual(
            builder.canonical_artifact_class(contract, "docs"),
            "docs",
        )

    def test_docs_contract_cannot_own_its_proof_file(self):
        contract = {
            **self.fixtures["validExecution"],
            "primaryArtifactClass": "docs",
            "mutationRoot": "docs/guide.md",
            "proofRoot": "docs/guide.md",
            "writableFiles": ["docs/guide.md"],
            "proofFiles": ["docs/guide.md"],
            "createdFileGlobs": ["docs/guide.md"],
        }
        codes = {
            finding["code"]
            for finding in validator.collect_task_contract_local_findings(
                contract,
                "docs",
                strict_plan=True,
                strict_graph=True,
            )
        }
        self.assertIn("implementation_owns_proof", codes)


if __name__ == "__main__":
    unittest.main()
