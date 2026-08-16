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

    def test_initializer_exposes_complete_canonical_task_template(self):
        manifest = builder.initialize_manifest(
            {
                "id": "60de1d80-3336-4fb2-83c4-fdb58cd6e76d",
                "decompositionContract": {
                    "requiredOwnershipPaths": ["src/workflow.ts"],
                    "proofExpected": ["Focused workflow proof passes."],
                },
            }
        )
        template = manifest["contractGuide"]["taskTemplate"]
        self.assertEqual(template["priority"], "P1")
        self.assertEqual(template["dependsOn"], [])
        self.assertIn("requirements", template)
        self.assertIn("reviewMode", template)
        self.assertEqual(
            set(template["contract"]["plan"]),
            {
                "outcome",
                "inspect",
                "derive",
                "apply",
                "verify",
                "operation",
                "symbols",
                "invariant",
                "completionChecks",
            },
        )
        self.assertEqual(
            manifest["contractGuide"]["unassignedRequirements"],
            ["ownership:src/workflow.ts", "proof:0"],
        )

    def test_initializer_exposes_artifact_delivery_closure(self):
        manifest = builder.initialize_manifest({
            "id": "93c604b0-8cfb-4b09-a036-f658252a877e",
            "owner": "Maeve",
            "decompositionContract": {
                "deliveryProfile": "artifact_delivery",
                "requiredOwnershipPaths": [],
                "proofExpected": [],
            },
        })
        shape = manifest["contractGuide"]["specialTaskShapes"]["artifactDelivery"]
        self.assertEqual(shape["softwareQualityGates"], [])
        self.assertEqual(shape["forbiddenArtifactClass"], "integration_proof")
        self.assertIn("operator gate_review", shape["closure"])
        self.assertTrue({"research_evidence", "content_draft", "content_package"}.issubset(
            validator.PRIMARY_ARTIFACT_CLASSES
        ))
        self.assertEqual(
            manifest["contractGuide"]["specialTaskShapes"]["integrationProof"],
            {
                "taskType": "execution",
                "primaryArtifactClass": "integration_proof",
                "qualityGates": ["software_test", "software_build"],
                "scopeRule": (
                    "Own one exact proof file: mutationRoot=proofRoot and "
                    "writableFiles=proofFiles=createdFileGlobs=[that exact file]. "
                    "Keep authorityRoot and readOnlyAnchors outside writable scope."
                ),
            },
        )
        self.assertEqual(
            manifest["contractGuide"]["specialTaskShapes"]["gateReview"][
                "reviewMode"
            ],
            "gate_review",
        )

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
            "focused_proof",
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

    def test_validator_counts_production_created_globs_in_mutation_clusters(self):
        contract = {
            **self.fixtures["validExecution"],
            "mutationRoot": "apps/mission-control/src/components/knowledge/browse/",
            "writableFiles": [
                "apps/mission-control/src/components/knowledge/browse/record-list.tsx",
            ],
            "createdFileGlobs": [
                "apps/mission-control/src/components/knowledge/browse/**",
            ],
        }
        task = {
            "id": "0d01d42e-f0b4-4d24-9ba1-ea9fb06f3038",
            "title": "Create bounded browse components",
            "nextAction": "Apply the bounded component change.",
            "summary": "Own one component mutation family.",
            "assignee": "William",
            "priority": "P1",
            "taskType": "execution",
            "reviewMode": None,
            "dependsOn": [],
            "acceptanceCriteria": ["The component contract is complete."],
            "constraints": ["Stay inside the declared mutation root."],
            "relatedFiles": contract["writableFiles"],
            "artifactPaths": [contract["authorityRoot"]],
            "taskContract": contract,
        }
        findings = validator.collect_contract_required_findings(
            {
                "actor": "Bernard",
                "kind": "decomposition_result",
                "requestReview": True,
                "tasks": [task],
            },
            max_tasks=14,
            objective={
                "decompositionContract": {
                    "allowedExpansionZone": [
                        "apps/mission-control/src/components/knowledge/browse/**",
                    ],
                },
            },
        )
        self.assertIn(
            "multiple_mutation_clusters",
            {finding["code"] for finding in findings},
        )

        exact_contract = {
            **contract,
            "createdFileGlobs": contract["writableFiles"],
        }
        exact_task = {**task, "taskContract": exact_contract}
        exact_findings = validator.collect_contract_required_findings(
            {
                "actor": "Bernard",
                "kind": "decomposition_result",
                "requestReview": True,
                "tasks": [exact_task],
            },
            max_tasks=14,
            objective={
                "decompositionContract": {
                    "allowedExpansionZone": [
                        "apps/mission-control/src/components/knowledge/browse/**",
                    ],
                },
            },
        )
        self.assertNotIn(
            "multiple_mutation_clusters",
            {finding["code"] for finding in exact_findings},
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

    def test_docs_readback_is_not_executable_proof_scope(self):
        task_id = "docs-task"
        docs_contract = {
            **self.fixtures["validExecution"],
            "primaryArtifactClass": "docs",
            "mutationRoot": "docs/guide.md",
            "proofRoot": "docs/guide.md",
            "writableFiles": ["docs/guide.md"],
            "proofFiles": [],
            "createdFileGlobs": ["docs/guide.md"],
            "verification": {"focusedTests": [], "qualityGates": []},
        }
        payload = {
            "kind": "decomposition_result",
            "actor": "Bernard",
            "requestReview": True,
            "tasks": [
                {
                    "id": task_id,
                    "title": "Write docs",
                    "assignee": "William",
                    "taskType": "execution",
                    "priority": "P1",
                    "nextAction": "Write the guide",
                    "dependsOn": [],
                    "taskContract": docs_contract,
                }
            ],
        }
        findings = validator.collect_contract_required_findings(
            payload,
            max_tasks=2,
            objective={
                "decompositionContract": {
                    "taskContractRequired": True,
                    "allowedExpansionZone": ["docs/**"],
                }
            },
        )
        self.assertFalse(
            any(
                finding["code"] == "implementation_proof_scope_leak"
                and finding.get("taskId") == task_id
                for finding in findings
            )
        )


if __name__ == "__main__":
    unittest.main()
