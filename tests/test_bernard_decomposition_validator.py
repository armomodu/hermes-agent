import copy
import json
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    REPO_ROOT
    / "docs/runtime-skill-mirrors/bernard-decompose/scripts/validate_decomposition_json.py"
)


def task_contract(root: str) -> dict:
    return {
        "version": "task-contract.v1",
        "semanticHinge": "Update one bounded contract surface",
        "workflowFamily": "contracts",
        "mutationRoot": root,
        "authorityRoot": "apps/mission-control/src/lib/release",
        "proofRoot": "apps/mission-control/src/lib/knowledge-plane/__tests__",
        "acceptanceHinge": "The bounded contract matches release authority",
        "writableFiles": [f"{root}/release.ts"],
        "createdFileGlobs": [
            "apps/mission-control/src/lib/knowledge-plane/__tests__/release.test.ts"
        ],
        "proofFiles": ["apps/mission-control/src/lib/knowledge-plane/__tests__/release.test.ts"],
        "readOnlyAnchors": ["apps/mission-control/src/lib/release/objective-release-service.ts"],
        "outputArtifacts": [],
        "provides": [],
        "consumes": [],
        "verification": {},
        "executionPlan": {
            "version": "task-execution-plan.v1",
            "outcome": "Project release authority into the bounded release contract",
            "steps": [
                {
                    "kind": "inspect_authority",
                    "instruction": "Read the live release authority.",
                    "references": ["authorityRoot"],
                },
                {
                    "kind": "derive_delta",
                    "instruction": "Derive only the missing contract delta.",
                    "references": ["authorityRoot", "mutationRoot"],
                },
                {
                    "kind": "apply_change",
                    "instruction": "Apply the bounded contract change.",
                    "references": ["mutationRoot"],
                },
                {
                    "kind": "verify",
                    "instruction": "Run the focused contract proof.",
                    "references": ["proofRoot"],
                },
            ],
            "expectedChanges": [
                {
                    "target": "mutationRoot",
                    "operation": "modify",
                    "symbols": ["releaseContract"],
                    "invariant": "Do not widen outside the release contract root.",
                }
            ],
            "completionChecks": ["Focused release contract proof passes"],
        },
    }


def repair_payload() -> dict:
    return {
        "kind": "task_repair_result",
        "sourceTaskId": str(uuid.uuid4()),
        "sourceAttemptNumber": 2,
        "taskContract": task_contract("apps/mission-control/src/lib/knowledge-plane/contracts"),
        "title": "Repair release workflow contract",
        "nextAction": "Execute the validated bounded plan",
    }


class BernardDecompositionValidatorTest(unittest.TestCase):
    def run_validator(self, payload: dict, *args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "payload.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), *args, str(path)],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

    def test_valid_repair_passes(self) -> None:
        result = self.run_validator(repair_payload(), "--repair")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "repair")

    def test_repair_without_plan_fails(self) -> None:
        payload = repair_payload()
        payload["taskContract"].pop("executionPlan")
        result = self.run_validator(payload, "--repair")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("executionPlan is required", result.stderr)

    def test_repair_with_out_of_order_plan_fails(self) -> None:
        payload = repair_payload()
        steps = payload["taskContract"]["executionPlan"]["steps"]
        steps[0], steps[2] = steps[2], steps[0]
        result = self.run_validator(payload, "--repair")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("steps are out of order", result.stderr)

    def test_repair_with_unbounded_reference_fails(self) -> None:
        payload = repair_payload()
        payload["taskContract"]["executionPlan"]["steps"][0]["references"] = [
            "siblingRoot"
        ]
        result = self.run_validator(payload, "--repair")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved reference", result.stderr)

    def test_repair_with_created_path_outside_contract_roots_fails(self) -> None:
        payload = repair_payload()
        payload["taskContract"]["createdFileGlobs"] = ["apps/mission-control/src/app/api/unrelated.ts"]
        result = self.run_validator(payload, "--repair")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes mutationRoot and proofRoot", result.stderr)

    def test_full_decomposition_still_passes(self) -> None:
        execution_id = str(uuid.uuid4())
        review_id = str(uuid.uuid4())
        execution_contract = task_contract(
            "apps/mission-control/src/lib/knowledge-plane/contracts"
        )
        review_contract = copy.deepcopy(execution_contract)
        review_contract["mutationRoot"] = "apps/mission-control/src/lib/knowledge-plane/__tests__"
        review_contract["writableFiles"] = [
            "apps/mission-control/src/lib/knowledge-plane/__tests__/gate.test.ts"
        ]
        payload = {
            "kind": "decomposition_result",
            "actor": "Bernard",
            "requestReview": True,
            "tasks": [
                {
                    "id": execution_id,
                    "title": "Author bounded release contract",
                    "assignee": "William",
                    "taskType": "execution",
                    "priority": "P1",
                    "nextAction": "Execute the validated plan",
                    "taskContract": execution_contract,
                },
                {
                    "id": review_id,
                    "title": "Review bounded release contract",
                    "assignee": "Bernard",
                    "taskType": "review",
                    "reviewMode": "gate_review",
                    "priority": "P1",
                    "nextAction": "Review the completed graph",
                    "dependsOn": [execution_id],
                    "taskContract": review_contract,
                },
            ],
        }
        result = self.run_validator(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["taskCount"], 2)


if __name__ == "__main__":
    unittest.main()
