import json
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRADER = (
    ROOT
    / "docs/runtime-skill-mirrors/grade-mission-control-decomposition/scripts/grade_decomposition.py"
)


def plan(read_only: bool = False) -> dict:
    kinds = ["inspect_authority", "derive_delta"]
    if not read_only:
        kinds.append("apply_change")
    kinds.append("verify")
    return {
        "version": "task-execution-plan.v1",
        "steps": [{"kind": kind, "instruction": kind, "references": ["authorityRoot"]} for kind in kinds],
        "expectedChanges": [] if read_only else [{"target": "mutationRoot"}],
    }


def graph(proof_class: str) -> tuple[dict, list[dict]]:
    proof_id, integration_id, review_id = [str(uuid.uuid4()) for _ in range(3)]
    proof_path = "apps/mission-control/src/lib/example/__tests__/focused.test.ts"
    integration_path = "apps/mission-control/src/lib/example/__tests__/integration.test.ts"
    proof = {
        "id": proof_id,
        "title": "Focused proof",
        "taskType": "execution",
        "status": "pending",
        "dependsOn": [],
        "taskContract": {
            "version": "task-contract.v1",
            "primaryArtifactClass": proof_class,
            "mutationRoot": proof_path,
            "authorityRoot": "apps/mission-control/src/lib/example/source.ts",
            "proofRoot": proof_path,
            "acceptanceHinge": "Focused proof passes",
            "writableFiles": [proof_path],
            "createdFileGlobs": [proof_path],
            "proofFiles": [proof_path],
            "readOnlyAnchors": [],
            "provides": ["focused-proof-v1"],
            "consumes": [],
            "verification": {"qualityGates": ["software_test"]},
            "executionPlan": plan(),
        },
    }
    integration = {
        "id": integration_id,
        "title": "Integration proof",
        "taskType": "execution",
        "status": "pending",
        "dependsOn": [proof_id],
        "taskContract": {
            **proof["taskContract"],
            "primaryArtifactClass": "integration_proof",
            "mutationRoot": integration_path,
            "proofRoot": integration_path,
            "writableFiles": [integration_path],
            "createdFileGlobs": [integration_path],
            "proofFiles": [integration_path],
            "provides": ["integration-proof-v1"],
            "consumes": ["focused-proof-v1"],
            "verification": {"qualityGates": ["software_test", "software_build"]},
        },
    }
    review = {
        "id": review_id,
        "title": "Gate review",
        "taskType": "review",
        "status": "pending",
        "dependsOn": [proof_id, integration_id],
        "taskContract": {
            "version": "task-contract.v1",
            "primaryArtifactClass": "review_gate",
            "writableFiles": [],
            "createdFileGlobs": [],
            "provides": [],
            "consumes": ["integration-proof-v1"],
            "executionPlan": plan(read_only=True),
        },
    }
    objective = {
        "id": str(uuid.uuid4()),
        "reviewReady": True,
        "approved": False,
        "childTaskIds": [proof_id, integration_id, review_id],
    }
    return objective, [proof, integration, review]


class DecompositionGraderTest(unittest.TestCase):
    def run_grader(self, proof_class: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        objective, tasks = graph(proof_class)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            objective_path = root / "objective.json"
            tasks_path = root / "tasks.json"
            report_path = root / "report.json"
            objective_path.write_text(json.dumps(objective), encoding="utf-8")
            tasks_path.write_text(json.dumps(tasks), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(GRADER),
                    "--objective",
                    str(objective_path),
                    "--tasks",
                    str(tasks_path),
                    "--report",
                    str(report_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            return result, json.loads(report_path.read_text(encoding="utf-8"))

    def test_focused_proof_graph_is_a_grade(self) -> None:
        result, report = self.run_grader("focused_proof")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(report["grade"], "A")

    def test_legacy_proof_requires_bounded_amendment(self) -> None:
        result, report = self.run_grader("proof")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            [finding["code"] for finding in report["findings"]],
            ["legacy_primary_artifact_class"],
        )

    def test_staged_candidate_requires_exact_invocation_chain_owner(self) -> None:
        objective, tasks = graph("focused_proof")
        routing_path = "apps/mission-control/src/lib/workers/release-job-routing.ts"
        objective["decompositionContract"] = {"sourceAnchors": [routing_path]}
        candidate = {
            "decompositionTaskId": "decompose-1",
            "candidateDigest": "digest-1",
            "correctionRound": 0,
            "tasks": tasks,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            objective_path = root / "objective.json"
            candidate_path = root / "candidate.json"
            objective_path.write_text(json.dumps(objective), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(GRADER), "--objective", str(objective_path), "--candidate", str(candidate_path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invocation_chain_incomplete", [finding["code"] for finding in report["findings"]])

        tasks[0]["taskContract"]["readOnlyAnchors"] = [routing_path]
        candidate["tasks"] = tasks
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            objective_path = root / "objective.json"
            candidate_path = root / "candidate.json"
            objective_path.write_text(json.dumps(objective), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(GRADER), "--objective", str(objective_path), "--candidate", str(candidate_path)],
                cwd=ROOT, capture_output=True, text=True,
            )
            report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(report["grade"], "A")
        self.assertEqual(report["candidateDigest"], "digest-1")


if __name__ == "__main__":
    unittest.main()
