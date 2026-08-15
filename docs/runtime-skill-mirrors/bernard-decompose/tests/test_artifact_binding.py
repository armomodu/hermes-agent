import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = load_module("build_contract_decomposition", SCRIPTS / "build_contract_decomposition.py")
validator = load_module("validate_decomposition_json", SCRIPTS / "validate_decomposition_json.py")
checkpoint = load_module("decomposition_checkpoint", SCRIPTS / "decomposition_checkpoint.py")
complete = load_module("complete_decomposition", SCRIPTS / "complete_decomposition.py")


def objective() -> dict:
    return {
        "id": "915a1c8c-332f-4a63-afd5-a5dddc274818",
        "decompositionContract": {"approvedSlices": []},
    }


def manifest() -> dict:
    return {
        "kind": "contract-decomposition-manifest.v1",
        "objectiveId": objective()["id"],
        "statusNote": "Bound artifact test",
        "tasks": [{
            "key": "slice",
            "requirements": [],
            "title": "Bound slice",
            "assignee": "William",
            "taskType": "execution",
            "priority": "P1",
            "nextAction": "Implement the bounded slice.",
            "dependsOn": [],
            "contract": {
                "semanticHinge": "One bounded change",
                "workflowFamily": "test",
                "mutationRoot": "apps/example.ts",
                "authorityRoot": "apps/source.ts",
                "proofRoot": "apps/proof.test.ts",
                "acceptanceHinge": "The change is proven",
                "writableFiles": ["apps/example.ts"],
                "createdFileGlobs": ["apps/example.ts"],
                "proofFiles": [],
                "readOnlyAnchors": ["apps/source.ts", "apps/proof.test.ts"],
                "outputArtifacts": [],
                "provides": [],
                "consumes": [],
                "verification": {"focusedTests": [], "qualityGates": ["software_lint"]},
                "productionEvidence": [],
                "primaryArtifactClass": "code",
                "plan": {
                    "outcome": "Implement one bounded change",
                    "inspect": "Inspect the authority source",
                    "derive": "Derive the required delta",
                    "apply": "Apply the bounded change",
                    "verify": "Verify the proof surface",
                    "operation": "modify",
                    "symbols": ["example"],
                    "invariant": "Only the mutation root changes",
                    "completionChecks": ["Lint passes"],
                },
            },
        }],
    }


class ArtifactBindingTest(unittest.TestCase):
    def test_executable_proof_matches_mission_control_vitest_discovery(self):
        self.assertTrue(validator._is_executable_software_test_proof(
            "apps/mission-control/src/lib/decomposition/__tests__/contract.test.ts"
        ))
        self.assertFalse(validator._is_executable_software_test_proof(
            "apps/mission-control/src/lib/production-control/__tests__/store-only-canary.test.ts"
        ))

    def test_validator_rejects_task_count_that_differs_from_approved_slices(self):
        source_objective = objective()
        source_objective["decompositionContract"]["approvedSlices"] = [
            {"name": "first"},
            {"name": "second"},
        ]
        source_manifest = manifest()
        payload = builder.expand_manifest(source_manifest, source_objective)
        with tempfile.TemporaryDirectory() as raw:
            report_path = Path(raw) / "report.json"
            result = validator.emit_contract_required_report(
                payload,
                max_tasks=10,
                objective=source_objective,
                manifest=source_manifest,
                amend_baseline=None,
                report_path=report_path,
                workspace=Path(raw),
            )
            self.assertEqual(result, 1)
            codes = {finding["code"] for finding in json.loads(report_path.read_text())["findings"]}
            self.assertIn("task_count_mismatch_contract", codes)

    def test_validator_rejects_payload_not_generated_from_current_manifest(self):
        source_manifest = manifest()
        payload = builder.expand_manifest(source_manifest, objective())
        payload["tasks"][0]["title"] = "Stale generated title"
        with tempfile.TemporaryDirectory() as raw:
            report_path = Path(raw) / "report.json"
            result = validator.emit_contract_required_report(
                payload,
                max_tasks=10,
                objective=objective(),
                manifest=source_manifest,
                amend_baseline=None,
                report_path=report_path,
                workspace=Path(raw),
            )
            self.assertEqual(result, 1)
            codes = {finding["code"] for finding in json.loads(report_path.read_text())["findings"]}
            self.assertIn("manifest_payload_mismatch", codes)

    def test_atomic_finalizer_submits_once_and_reuses_accepted_checkpoint(self):
        payload = builder.expand_manifest(manifest(), objective())
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            manifest_path = workspace / "manifest.json"
            result_path = workspace / "decomposition.json"
            objective_path = workspace / "objective.json"
            response_path = workspace / "response.json"
            manifest_path.write_text(json.dumps(manifest()))
            result_path.write_text(json.dumps(payload))
            objective_path.write_text(json.dumps(objective()))
            checkpoint.record_build(
                objective_id=payload["objectiveId"],
                manifest_path=manifest_path,
                decomposition_path=result_path,
                objective_path=objective_path,
                workspace=workspace,
            )
            checkpoint.record_validation(
                report={"ok": True, "findingCount": 0, "findings": []},
                workspace=workspace,
            )
            (workspace / "decomposition-validator-report.json").write_text(
                json.dumps({"ok": True, "findingCount": 0, "findings": []})
            )
            with mock.patch.object(complete, "submit", return_value=(200, {"ok": True})) as submit:
                complete.ensure_submitted(
                    payload,
                    workspace / ".mc-decomposition-checkpoint.json",
                    response_path,
                    api_base="https://example.test/api",
                    token="test-token",
                    timeout=1,
                )
                complete.ensure_submitted(
                    payload,
                    workspace / ".mc-decomposition-checkpoint.json",
                    response_path,
                    api_base="https://example.test/api",
                    token="test-token",
                    timeout=1,
                )
            submit.assert_called_once()
            self.assertEqual(
                json.loads((workspace / ".mc-decomposition-checkpoint.json").read_text())["checkpointStatus"],
                "accepted",
            )

    def test_ambiguous_timeout_reconciles_matching_live_graph(self):
        payload = builder.expand_manifest(manifest(), objective())
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            manifest_path = workspace / "manifest.json"
            result_path = workspace / "decomposition.json"
            objective_path = workspace / "objective.json"
            manifest_path.write_text(json.dumps(manifest()))
            result_path.write_text(json.dumps(payload))
            objective_path.write_text(json.dumps(objective()))
            checkpoint.record_build(
                objective_id=payload["objectiveId"],
                manifest_path=manifest_path,
                decomposition_path=result_path,
                objective_path=objective_path,
                workspace=workspace,
            )
            checkpoint.record_validation(
                report={"ok": True, "findingCount": 0, "findings": []},
                workspace=workspace,
            )
            (workspace / "decomposition-validator-report.json").write_text(
                json.dumps({"ok": True, "findingCount": 0, "findings": []})
            )
            with mock.patch.object(complete, "submit", side_effect=TimeoutError()), mock.patch.object(
                complete, "persisted_graph_matches", return_value=True
            ):
                complete.ensure_submitted(
                    payload,
                    workspace / ".mc-decomposition-checkpoint.json",
                    workspace / "response.json",
                    api_base="https://example.test/api",
                    token="test-token",
                    timeout=1,
                )
            self.assertEqual(
                json.loads((workspace / ".mc-decomposition-checkpoint.json").read_text())["checkpointStatus"],
                "accepted",
            )


if __name__ == "__main__":
    unittest.main()
