import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("grade_decomposition.py")


def execution(task_id, title, artifact_class, assignee="William", depends_on=None, consumes=None):
    path = f"content/{task_id}.md"
    return {
        "id": task_id,
        "title": title,
        "taskType": "execution",
        "status": "pending",
        "assignee": assignee,
        "dependsOn": depends_on or [],
        "taskContract": {
            "version": "task-contract.v1",
            "primaryArtifactClass": artifact_class,
            "mutationRoot": path,
            "authorityRoot": "docs/authority.md",
            "proofRoot": path,
            "acceptanceHinge": f"{title} accepted",
            "writableFiles": [path],
            "createdFileGlobs": [],
            "proofFiles": [path] if artifact_class == "integration_proof" else [],
            "readOnlyAnchors": [],
            "provides": [f"{task_id}-evidence"],
            "consumes": consumes or [],
            "outputArtifacts": [path],
            "verification": {"qualityGates": ["software_build"] if artifact_class == "integration_proof" else []},
            "executionPlan": {"steps": [
                {"kind": "inspect_authority"}, {"kind": "derive_delta"},
                {"kind": "apply_change"}, {"kind": "verify"},
            ]},
        },
    }


def review(depends_on, consumes, assignee="Operator"):
    return {
        "id": "review",
        "title": "Final gate review",
        "taskType": "review",
        "status": "pending",
        "assignee": assignee,
        "dependsOn": depends_on,
        "taskContract": {
            "version": "task-contract.v1",
            "primaryArtifactClass": "review_gate",
            "writableFiles": [], "createdFileGlobs": [], "proofFiles": [],
            "readOnlyAnchors": [], "provides": [], "consumes": consumes,
            "executionPlan": {"steps": [
                {"kind": "inspect_authority"}, {"kind": "derive_delta"}, {"kind": "verify"},
            ], "expectedChanges": []},
        },
    }


class GradeDecompositionTest(unittest.TestCase):
    def run_grade(self, objective, tasks):
        candidate = {"decompositionTaskId": "decompose-1", "candidateDigest": "digest-1", "correctionRound": 0, "tasks": tasks}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            objective_path = root / "objective.json"
            candidate_path = root / "candidate.json"
            objective_path.write_text(json.dumps(objective), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(SCRIPT), "--objective", str(objective_path), "--candidate", str(candidate_path)],
                check=False, capture_output=True, text=True,
            )
            return result, json.loads(result.stdout)

    def artifact_fixture(self, maeve_assignee="Maeve", gate_dependencies=None):
        research = execution("research", "Cited research", "research_evidence")
        package = execution("package", "Content package", "content_package", depends_on=["research"], consumes=["research-evidence"])
        quality = execution("quality", "Maeve quality review", "content_draft", assignee=maeve_assignee, depends_on=["research", "package"], consumes=["research-evidence", "package-evidence"])
        tasks = [research, package, quality]
        tasks.append(review(gate_dependencies or [task["id"] for task in tasks], ["quality-evidence"]))
        objective = {
            "id": "artifact",
            "deliveryProfile": "artifact_delivery",
            "decompositionContract": {
                "deliveryProfile": "artifact_delivery",
                "productionGateReviewer": "operator",
                "approvedSlices": [{"name": "maeve_quality_review"}],
            },
        }
        return objective, tasks

    def test_artifact_delivery_passes_without_software_integration_proof(self):
        objective, tasks = self.artifact_fixture()
        result, report = self.run_grade(objective, tasks)
        self.assertEqual(result.returncode, 0, report)
        self.assertEqual(report["grade"], "A")

    def test_artifact_delivery_requires_maeve_quality_owner(self):
        objective, tasks = self.artifact_fixture(maeve_assignee="William")
        result, report = self.run_grade(objective, tasks)
        self.assertEqual(result.returncode, 1)
        self.assertIn("artifact_quality_owner_invalid", {item["code"] for item in report["findings"]})

    def test_artifact_delivery_gate_depends_on_every_execution_slice(self):
        objective, tasks = self.artifact_fixture(gate_dependencies=["quality"])
        result, report = self.run_grade(objective, tasks)
        self.assertEqual(result.returncode, 1)
        self.assertIn("gate_review_incomplete", {item["code"] for item in report["findings"]})

    def test_software_delivery_still_requires_integration_proof(self):
        objective = {"id": "software", "deliveryProfile": "production_component", "decompositionContract": {"productionGateReviewer": "operator"}}
        implementation = execution("implementation", "Implement", "code")
        tasks = [implementation, review(["implementation"], ["implementation-evidence"])]
        result, report = self.run_grade(objective, tasks)
        self.assertEqual(result.returncode, 1)
        self.assertIn("integration_proof_incomplete", {item["code"] for item in report["findings"]})


if __name__ == "__main__":
    unittest.main()
