import copy
import json
import os
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
CONTRACT_BUILDER = (
    REPO_ROOT
    / "docs/runtime-skill-mirrors/bernard-decompose/scripts/build_contract_decomposition.py"
)
CHECKPOINT = (
    REPO_ROOT
    / "docs/runtime-skill-mirrors/bernard-decompose/scripts/decomposition_checkpoint.py"
)
SKILL = REPO_ROOT / "docs/runtime-skill-mirrors/bernard-decompose/SKILL.md"


def task_contract(root: str) -> dict:
    return {
        "version": "task-contract.v1",
        "semanticHinge": "Update one bounded contract surface",
        "workflowFamily": "contracts",
        "mutationRoot": root,
        "authorityRoot": "apps/mission-control/src/lib/release",
        "proofRoot": "apps/mission-control/src/lib/knowledge-plane/__tests__/release.test.ts",
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
        "verification": {
            "focusedTests": ["apps/mission-control/src/lib/knowledge-plane/__tests__/release.test.ts"],
            "qualityGates": ["software_test"],
        },
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


def contract_required_payload() -> dict:
    implementation_id = str(uuid.uuid4())
    proof_id = str(uuid.uuid4())
    integration_id = str(uuid.uuid4())
    review_id = str(uuid.uuid4())
    implementation = task_contract("apps/mission-control/src/lib/knowledge-plane/contracts")
    implementation["mutationRoot"] = implementation["writableFiles"][0]
    implementation["createdFileGlobs"] = []
    implementation["proofFiles"] = []
    implementation["verification"] = {"focusedTests": [], "qualityGates": []}
    implementation["provides"] = ["release-contract-v1"]

    proof = task_contract("apps/mission-control/src/lib/knowledge-plane/__tests__")
    proof_file = "apps/mission-control/src/lib/knowledge-plane/__tests__/release-proof.test.ts"
    proof["mutationRoot"] = proof_file
    proof["proofRoot"] = proof_file
    proof["writableFiles"] = [proof_file]
    proof["proofFiles"] = [proof_file]
    proof["createdFileGlobs"] = [proof_file]
    proof["verification"] = {
        "focusedTests": [proof_file],
        "qualityGates": ["software_test"],
    }
    proof["consumes"] = ["release-contract-v1"]
    proof["provides"] = ["release-proof-v1"]

    integration = copy.deepcopy(proof)
    integration_file = "apps/mission-control/src/lib/knowledge-plane/__tests__/release-integration.test.ts"
    integration["primaryArtifactClass"] = "integration_proof"
    integration["mutationRoot"] = integration_file
    integration["proofRoot"] = integration_file
    integration["writableFiles"] = [integration_file]
    integration["proofFiles"] = [integration_file]
    integration["createdFileGlobs"] = [integration_file]
    integration["verification"] = {
        "focusedTests": [integration_file],
        "qualityGates": ["software_test"],
    }
    integration["consumes"] = ["release-contract-v1", "release-proof-v1"]

    review = copy.deepcopy(integration)
    review["writableFiles"] = []
    review["createdFileGlobs"] = []
    review["proofFiles"] = [integration_file]
    review["primaryArtifactClass"] = "review_gate"
    review["consumes"] = []

    return {
        "kind": "decomposition_result",
        "actor": "Bernard",
        "requestReview": True,
        "tasks": [
            {
                "id": implementation_id,
                "title": "Author release contract",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Execute",
                "taskContract": implementation,
            },
            {
                "id": proof_id,
                "title": "Prove release contract",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Prove",
                "dependsOn": [implementation_id],
                "taskContract": proof,
            },
            {
                "id": integration_id,
                "title": "Run final integration proof",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Integrate",
                "dependsOn": [implementation_id, proof_id],
                "taskContract": integration,
            },
            {
                "id": review_id,
                "title": "Gate review",
                "assignee": "Bernard",
                "taskType": "review",
                "reviewMode": "gate_review",
                "priority": "P1",
                "nextAction": "Review",
                "dependsOn": [implementation_id, proof_id, integration_id],
                "taskContract": review,
            },
        ],
    }


def compact_manifest() -> dict:
    objective_id = str(uuid.uuid4())

    def contract(root: str, proof: str, *, provides=None, consumes=None) -> dict:
        return {
            "semanticHinge": f"Own {root}",
            "workflowFamily": "artifact-registry",
            "mutationRoot": root,
            "authorityRoot": "apps/mission-control/src/lib/storage/storage-adapter-interface.ts",
            "proofRoot": proof,
            "acceptanceHinge": f"{root} remains bounded and verifiable",
            "writableFiles": [root],
            "createdFileGlobs": [],
            "proofFiles": [],
            "readOnlyAnchors": ["apps/mission-control/src/lib/storage/storage-adapter-interface.ts"],
            "outputArtifacts": [],
            "provides": provides or [],
            "consumes": consumes or [],
            "verification": {"focusedTests": [], "qualityGates": []},
            "plan": {
                "outcome": f"Implement the bounded owner at {root}",
                "inspect": "Inspect the declared storage authority.",
                "derive": "Derive the exact missing ownership delta.",
                "apply": "Apply only the bounded owner change.",
                "verify": "Verify against the declared focused proof.",
                "operation": "modify",
                "symbols": ["artifactRegistryOwner"],
                "invariant": "No sibling mutation root is changed.",
                "completionChecks": ["The bounded owner is represented exactly once"],
            },
        }

    first_root = "apps/mission-control/src/lib/storage/types.ts"
    second_root = "apps/mission-control/src/lib/storage/file-storage-adapter.ts"
    proof = "apps/mission-control/src/lib/knowledge-plane/__tests__/artifact-registry.test.ts"
    return {
        "kind": "contract-decomposition-manifest.v1",
        "objectiveId": objective_id,
        "statusNote": "Bounded artifact registry graph ready for review",
        "tasks": [
            {
                "key": "types-owner",
                "title": "Own artifact registry storage types",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Execute the bounded plan",
                "dependsOn": [],
                "contract": contract(first_root, proof, provides=["artifact-registry-types-v1"]),
            },
            {
                "key": "file-owner",
                "title": "Own artifact registry file persistence",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Execute after types authority exists",
                "dependsOn": ["types-owner"],
                "contract": contract(
                    second_root,
                    proof,
                    consumes=["artifact-registry-types-v1"],
                ),
            },
        ],
    }


def convergence_manifest() -> tuple[dict, dict]:
    objective_id = str(uuid.uuid4())
    implementation_file = "apps/mission-control/src/lib/knowledge-plane/contracts/release.ts"
    proof_file = "apps/mission-control/src/lib/knowledge-plane/__tests__/release-proof.test.ts"
    integration_file = "apps/mission-control/src/lib/knowledge-plane/__tests__/release-integration.test.ts"
    authority_file = "apps/mission-control/src/lib/release/objective-release-service.ts"

    def contract(
        *,
        mutation: str,
        proof: str,
        writable: list[str],
        proof_files: list[str],
        created: list[str],
        provides: list[str],
        consumes: list[str],
        artifact_class: str | None = None,
    ) -> dict:
        value = {
            "semanticHinge": f"Own the bounded change at {mutation}",
            "workflowFamily": "release-contract",
            "mutationRoot": mutation,
            "authorityRoot": authority_file,
            "proofRoot": proof,
            "acceptanceHinge": f"The bounded change at {mutation} is authority-derived",
            "writableFiles": writable,
            "createdFileGlobs": created,
            "proofFiles": proof_files,
            "readOnlyAnchors": [authority_file],
            "outputArtifacts": [],
            "provides": provides,
            "consumes": consumes,
            "verification": {
                "focusedTests": proof_files,
                "qualityGates": ["software_test"] if proof_files else [],
            },
            "plan": {
                "outcome": f"Produce the authority-derived bounded output at {mutation}",
                "inspect": "Inspect the declared release authority.",
                "derive": "Derive the exact missing bounded delta.",
                "apply": "Apply only the declared mutation.",
                "verify": "Run the declared focused proof.",
                "operation": "modify",
                "symbols": ["releaseContract"],
                "invariant": "No sibling mutation root changes.",
                "completionChecks": ["The declared bounded proof passes"],
            },
        }
        if artifact_class:
            value["primaryArtifactClass"] = artifact_class
        return value

    manifest = {
        "kind": "contract-decomposition-manifest.v1",
        "objectiveId": objective_id,
        "statusNote": "Release contract decomposition is ready for review",
        "tasks": [
            {
                "key": "release-contract",
                "requirements": [f"ownership:{implementation_file}"],
                "title": "Author bounded release contract",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Implement the bounded contract",
                "dependsOn": [],
                "contract": contract(
                    mutation=implementation_file,
                    proof=proof_file,
                    writable=[implementation_file],
                    proof_files=[],
                    created=[],
                    provides=["release-contract-v1"],
                    consumes=[],
                ),
            },
            {
                "key": "release-proof",
                "requirements": ["proof:0"],
                "title": "Prove bounded release contract",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Create the focused proof",
                "dependsOn": ["release-contract"],
                "contract": contract(
                    mutation=proof_file,
                    proof=proof_file,
                    writable=[proof_file],
                    proof_files=[proof_file],
                    created=[proof_file],
                    provides=["release-proof-v1"],
                    consumes=["release-contract-v1"],
                ),
            },
            {
                "key": "integration-proof",
                "requirements": [],
                "title": "Run final integration proof",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Run the complete proof",
                "dependsOn": ["release-contract", "release-proof"],
                "contract": contract(
                    mutation=integration_file,
                    proof=integration_file,
                    writable=[integration_file],
                    proof_files=[integration_file],
                    created=[integration_file],
                    provides=["release-integration-v1"],
                    consumes=["release-contract-v1", "release-proof-v1"],
                    artifact_class="integration_proof",
                ),
            },
            {
                "key": "gate-review",
                "requirements": [],
                "title": "Review the complete release graph",
                "assignee": "Bernard",
                "taskType": "review",
                "reviewMode": "gate_review",
                "priority": "P1",
                "nextAction": "Review the integrated graph",
                "dependsOn": ["release-contract", "release-proof", "integration-proof"],
                "contract": contract(
                    mutation=integration_file,
                    proof=integration_file,
                    writable=[],
                    proof_files=[integration_file],
                    created=[],
                    provides=[],
                    consumes=[],
                    artifact_class="review_gate",
                ),
            },
        ],
    }
    objective = {
        "id": objective_id,
        "decompositionContract": {
            "taskContractRequired": True,
            "maxTaskCount": 8,
            "requiredOwnershipPaths": [implementation_file],
            "proofExpected": ["The bounded release proof passes"],
        },
    }
    return manifest, objective


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

    def test_operational_skill_is_concise_and_manifest_first(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        self.assertLess(len(skill.splitlines()), 250)
        self.assertIn("Canonical Manifest Workflow", skill)
        self.assertIn("decomposition_checkpoint.py resume", skill)
        self.assertIn("Never change a key during correction", skill)
        self.assertIn("read the complete report once", skill)
        self.assertIn("Every listed path must have exactly one explicit writable owner", skill)
        self.assertIn("One final `integration_proof`", skill)

    def test_compact_manifest_expands_deterministically_with_ordered_plan(self) -> None:
        manifest = compact_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "manifest.json"
            first_output = Path(temp_dir) / "first.json"
            second_output = Path(temp_dir) / "second.json"
            source.write_text(json.dumps(manifest), encoding="utf-8")
            first = subprocess.run(
                ["python3", str(CONTRACT_BUILDER), str(source), str(first_output)],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            second = subprocess.run(
                ["python3", str(CONTRACT_BUILDER), str(source), str(second_output)],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_output.read_text(), second_output.read_text())
            payload = json.loads(first_output.read_text())
            self.assertEqual(payload["kind"], "decomposition_result")
            self.assertEqual(payload["tasks"][1]["dependsOn"], [payload["tasks"][0]["id"]])
            plan = payload["tasks"][1]["taskContract"]["executionPlan"]
            self.assertEqual(
                [step["kind"] for step in plan["steps"]],
                ["inspect_authority", "derive_delta", "apply_change", "verify"],
            )
            self.assertIn(
                "consumedToken:artifact-registry-types-v1",
                plan["steps"][1]["references"],
            )

    def test_compact_manifest_rejects_unknown_dependency_key(self) -> None:
        manifest = compact_manifest()
        manifest["tasks"][1]["dependsOn"] = ["missing-owner"]
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "manifest.json"
            output = Path(temp_dir) / "decomposition.json"
            source.write_text(json.dumps(manifest), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(CONTRACT_BUILDER), str(source), str(output)],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown dependsOn keys", result.stderr)

    def test_manifest_checkpoint_survives_retry_and_counts_only_real_corrections(self) -> None:
        manifest = compact_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            source = workspace / "manifest.json"
            output = workspace / "decomposition.json"
            objective = workspace / "objective.json"
            source.write_text(json.dumps(manifest), encoding="utf-8")
            objective.write_text(
                json.dumps({"id": manifest["objectiveId"], "decompositionContract": {}}),
                encoding="utf-8",
            )
            command = [
                "python3",
                str(CONTRACT_BUILDER),
                str(source),
                str(output),
                "--objective",
                str(objective),
            ]
            first = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
            retry = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(retry.returncode, 0, retry.stderr)
            self.assertEqual(json.loads(first.stdout)["correctionRound"], 0)
            self.assertEqual(json.loads(retry.stdout)["correctionRound"], 0)

            manifest["statusNote"] = "Corrected bounded artifact registry graph"
            source.write_text(json.dumps(manifest), encoding="utf-8")
            corrected = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
            self.assertEqual(corrected.returncode, 0, corrected.stderr)
            self.assertEqual(json.loads(corrected.stdout)["correctionRound"], 1)
            status = subprocess.run(
                ["python3", str(CHECKPOINT), "status", "--workspace", str(workspace)],
                cwd=workspace,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            checkpoint = json.loads(status.stdout)
            self.assertEqual(checkpoint["correctionRound"], 1)
            self.assertEqual(checkpoint["checkpointStatus"], "drafted")

    def test_autonomous_convergence_reuses_manifest_across_correction_and_retry(self) -> None:
        manifest, objective = convergence_manifest()
        manifest["tasks"][0]["contract"]["authorityRoot"] = "apps/mission-control"
        manifest["tasks"][2]["dependsOn"] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            manifest_path = workspace / "manifest.json"
            objective_path = workspace / "objective.json"
            decomposition_path = workspace / "decomposition.json"
            report_path = workspace / "decomposition-validator-report.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            objective_path.write_text(json.dumps(objective), encoding="utf-8")
            build = [
                "python3",
                str(CONTRACT_BUILDER),
                str(manifest_path),
                str(decomposition_path),
                "--objective",
                str(objective_path),
            ]
            validate = [
                "python3",
                str(VALIDATOR),
                "--contract-required",
                str(decomposition_path),
                "8",
                "--objective",
                str(objective_path),
                "--manifest",
                str(manifest_path),
                "--report",
                str(report_path),
            ]

            first_build = subprocess.run(build, cwd=workspace, capture_output=True, text=True)
            first_validate = subprocess.run(validate, cwd=workspace, capture_output=True, text=True)
            self.assertEqual(first_build.returncode, 0, first_build.stderr)
            self.assertNotEqual(first_validate.returncode, 0)
            first_payload = json.loads(decomposition_path.read_text())
            first_ids = [task["id"] for task in first_payload["tasks"]]
            first_report = json.loads(report_path.read_text())
            first_codes = {item["code"] for item in first_report["findings"]}
            self.assertIn("authority_root_too_broad", first_codes)
            self.assertIn("integration_proof_dependencies_missing", first_codes)

            manifest["tasks"][0]["contract"]["authorityRoot"] = (
                "apps/mission-control/src/lib/release/objective-release-service.ts"
            )
            manifest["tasks"][2]["dependsOn"] = ["release-contract", "release-proof"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            corrected_build = subprocess.run(build, cwd=workspace, capture_output=True, text=True)
            corrected_validate = subprocess.run(validate, cwd=workspace, capture_output=True, text=True)
            self.assertEqual(corrected_build.returncode, 0, corrected_build.stderr)
            self.assertEqual(corrected_validate.returncode, 0, corrected_validate.stderr)
            corrected_output = decomposition_path.read_text()
            corrected_payload = json.loads(corrected_output)
            self.assertEqual([task["id"] for task in corrected_payload["tasks"]], first_ids)
            self.assertEqual(json.loads(corrected_build.stdout)["correctionRound"], 1)
            self.assertEqual(json.loads(report_path.read_text())["findingCount"], 0)

            resumed = subprocess.run(
                ["python3", str(CHECKPOINT), "resume"],
                cwd=workspace,
                capture_output=True,
                text=True,
            )
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            retry_build = subprocess.run(build, cwd=workspace, capture_output=True, text=True)
            retry_validate = subprocess.run(validate, cwd=workspace, capture_output=True, text=True)
            self.assertEqual(retry_build.returncode, 0, retry_build.stderr)
            self.assertEqual(retry_validate.returncode, 0, retry_validate.stderr)
            self.assertEqual(decomposition_path.read_text(), corrected_output)
            self.assertEqual(json.loads(retry_build.stdout)["correctionRound"], 1)

            accepted = subprocess.run(
                ["python3", str(CHECKPOINT), "mark", "accepted"],
                cwd=workspace,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "BERNARD_DECOMPOSITION_ARCHIVE_ROOT": str(workspace / "archive"),
                },
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            accepted_checkpoint = json.loads(accepted.stdout)
            self.assertEqual(accepted_checkpoint["checkpointStatus"], "accepted")
            archive = Path(accepted_checkpoint["archivePath"])
            self.assertEqual(
                json.loads((archive / "canonical-manifest.json").read_text()),
                json.loads(manifest_path.read_text()),
            )
            self.assertEqual(
                json.loads((archive / "accepted-decomposition.json").read_text()),
                json.loads(decomposition_path.read_text()),
            )
            self.assertEqual(
                json.loads((archive / "validator-report.json").read_text()),
                json.loads(report_path.read_text()),
            )
            self.assertEqual(
                json.loads((archive / "checkpoint.json").read_text())["checkpointStatus"],
                "accepted",
            )
            metrics = subprocess.run(
                ["python3", str(CHECKPOINT), "metrics"],
                cwd=workspace,
                capture_output=True,
                text=True,
            )
            self.assertEqual(metrics.returncode, 0, metrics.stderr)
            metric_payload = json.loads(metrics.stdout)
            self.assertFalse(metric_payload["firstPassValidatorSuccess"])
            self.assertEqual(metric_payload["terminalCorrectionRound"], 1)
            self.assertEqual(metric_payload["firstPassValidatorSuccessRate"], 0.0)
            self.assertEqual(metric_payload["terminalConvergenceRate"], 1.0)
            self.assertEqual(metric_payload["averageCorrectionRounds"], 1.0)
            self.assertEqual(metric_payload["workspaceResumeSuccessRate"], 1.0)
            self.assertEqual(metric_payload["fullRegenerationCount"], 0)

    def test_checkpoint_rejects_non_improving_correction_with_new_defect(self) -> None:
        manifest, objective = convergence_manifest()
        manifest["tasks"][0]["contract"]["authorityRoot"] = "apps/mission-control"
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            manifest_path = workspace / "manifest.json"
            objective_path = workspace / "objective.json"
            decomposition_path = workspace / "decomposition.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            objective_path.write_text(json.dumps(objective), encoding="utf-8")
            build = [
                "python3",
                str(CONTRACT_BUILDER),
                str(manifest_path),
                str(decomposition_path),
                "--objective",
                str(objective_path),
            ]
            validate = [
                "python3",
                str(VALIDATOR),
                "--contract-required",
                str(decomposition_path),
                "8",
                "--objective",
                str(objective_path),
                "--manifest",
                str(manifest_path),
            ]

            self.assertEqual(
                subprocess.run(build, cwd=workspace, capture_output=True, text=True).returncode,
                0,
            )
            self.assertNotEqual(
                subprocess.run(validate, cwd=workspace, capture_output=True, text=True).returncode,
                0,
            )

            manifest["tasks"][0]["contract"]["authorityRoot"] = (
                "apps/mission-control/src/lib/release/objective-release-service.ts"
            )
            manifest["tasks"][1]["contract"]["authorityRoot"] = "apps/mission-control"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(
                subprocess.run(build, cwd=workspace, capture_output=True, text=True).returncode,
                0,
            )
            self.assertNotEqual(
                subprocess.run(validate, cwd=workspace, capture_output=True, text=True).returncode,
                0,
            )

            checkpoint = json.loads((workspace / ".mc-decomposition-checkpoint.json").read_text())
            self.assertEqual(checkpoint["checkpointStatus"], "correction_rejected")
            self.assertFalse(checkpoint["metrics"]["lastCorrectionAccepted"])
            self.assertFalse(checkpoint["metrics"]["lastCorrectionReducedFindings"])
            self.assertGreater(checkpoint["metrics"]["defectsIntroducedDuringCorrection"], 0)
            self.assertEqual(
                checkpoint["retryContext"]["lastFindingCount"],
                checkpoint["findingCount"],
            )

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
        self.assertIn("escapes mutationRoot", result.stderr)

    def test_repair_with_markdown_only_software_test_fails(self) -> None:
        payload = repair_payload()
        payload["taskContract"]["proofRoot"] = "apps/mission-control/docs/proof.md"
        payload["taskContract"]["proofFiles"] = ["apps/mission-control/docs/proof.md"]
        payload["taskContract"]["createdFileGlobs"] = ["apps/mission-control/docs/proof.md"]
        result = self.run_validator(payload, "--repair")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("software_test proof scope is not executable", result.stderr)

    def test_repair_with_markdown_evidence_without_software_test_passes(self) -> None:
        payload = repair_payload()
        payload["taskContract"]["proofRoot"] = "apps/mission-control/docs/proof.md"
        payload["taskContract"]["proofFiles"] = ["apps/mission-control/docs/proof.md"]
        payload["taskContract"]["createdFileGlobs"] = ["apps/mission-control/docs/proof.md"]
        payload["taskContract"]["verification"] = {"focusedTests": [], "qualityGates": []}
        result = self.run_validator(payload, "--repair")
        self.assertEqual(result.returncode, 0, result.stderr)

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

    def test_contract_required_rejects_legacy_task(self) -> None:
        payload = {
            "kind": "decomposition_result",
            "actor": "Bernard",
            "requestReview": True,
            "tasks": [{
                "id": str(uuid.uuid4()),
                "title": "Legacy task",
                "assignee": "William",
                "taskType": "execution",
                "priority": "P1",
                "nextAction": "Start",
                "summary": "Legacy",
                "acceptanceCriteria": "Legacy",
                "constraints": "Legacy",
                "relatedFiles": ["apps/mission-control/src/legacy.ts"],
            }],
        }
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task_contract_missing", result.stderr)

    def test_contract_required_enforces_strict_execution_plan_references(self) -> None:
        execution_id = str(uuid.uuid4())
        review_id = str(uuid.uuid4())
        execution_contract = task_contract("apps/mission-control/src/lib/knowledge-plane/contracts")
        execution_contract["mutationRoot"] = execution_contract["writableFiles"][0]
        execution_contract["executionPlan"]["steps"][0]["references"] = ["siblingRoot"]
        review_contract = task_contract("apps/mission-control/src/lib/knowledge-plane/__tests__")
        payload = {
            "kind": "decomposition_result",
            "actor": "Bernard",
            "requestReview": True,
            "tasks": [
                {
                    "id": execution_id,
                    "title": "Contract slice",
                    "assignee": "William",
                    "taskType": "execution",
                    "priority": "P1",
                    "nextAction": "Execute",
                    "taskContract": execution_contract,
                },
                {
                    "id": review_id,
                    "title": "Gate review",
                    "assignee": "Bernard",
                    "taskType": "review",
                    "reviewMode": "gate_review",
                    "priority": "P1",
                    "nextAction": "Review",
                    "dependsOn": [execution_id],
                    "taskContract": review_contract,
                },
            ],
        }
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unresolved reference", result.stderr)

    def test_contract_required_accepts_bounded_proof_integration_and_read_only_gate(self) -> None:
        result = self.run_validator(contract_required_payload(), "--contract-required")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_contract_required_rejects_proof_creation_in_normal_slice(self) -> None:
        payload = contract_required_payload()
        payload["tasks"][0]["taskContract"]["createdFileGlobs"] = [
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**"
        ]
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("escapes mutationRoot", result.stderr)

    def test_contract_required_rejects_docs_file_as_its_own_proof(self) -> None:
        payload = contract_required_payload()
        contract = payload["tasks"][0]["taskContract"]
        docs_path = "apps/mission-control/docs/knowledge-plane/artifact-registry.md"
        contract["primaryArtifactClass"] = "docs"
        contract["mutationRoot"] = docs_path
        contract["authorityRoot"] = docs_path
        contract["proofRoot"] = docs_path
        contract["writableFiles"] = [docs_path]
        contract["proofFiles"] = [docs_path]
        contract["readOnlyAnchors"] = []
        contract["verification"] = {
            "focusedTests": [],
            "qualityGates": ["docs_scope_review"],
        }
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("implementation_owns_proof", result.stderr)

    def test_contract_required_rejects_multiple_objective_storage_clusters(self) -> None:
        payload = contract_required_payload()
        contract = payload["tasks"][0]["taskContract"]
        storage_paths = [
            "apps/mission-control/src/lib/storage/types.ts",
            "apps/mission-control/src/lib/storage/storage-adapter-interface.ts",
        ]
        contract["mutationRoot"] = "apps/mission-control/src/lib/storage"
        contract["authorityRoot"] = storage_paths[0]
        contract["proofRoot"] = storage_paths[0]
        contract["writableFiles"] = storage_paths
        contract["readOnlyAnchors"] = []
        objective = {
            "id": str(uuid.uuid4()),
            "decompositionContract": {
                "taskContractRequired": True,
                "maxTaskCount": 8,
                "allowedExpansionZone": storage_paths,
                "sourceAnchors": storage_paths,
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            payload_path = Path(temp_dir) / "payload.json"
            objective_path = Path(temp_dir) / "objective.json"
            report_path = Path(temp_dir) / "report.json"
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            objective_path.write_text(json.dumps(objective), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--contract-required",
                    str(payload_path),
                    "--objective",
                    str(objective_path),
                    "--report",
                    str(report_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple_mutation_clusters", result.stderr)

    def test_contract_required_rejects_read_only_writable_overlap(self) -> None:
        payload = contract_required_payload()
        contract = payload["tasks"][0]["taskContract"]
        contract["readOnlyAnchors"] = [contract["writableFiles"][0]]
        contract["authorityRoot"] = contract["mutationRoot"]
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("readOnlyAnchors overlaps writable scope", result.stderr)

    def test_contract_required_rejects_missing_integration_proof(self) -> None:
        payload = contract_required_payload()
        payload["tasks"][2]["taskContract"]["primaryArtifactClass"] = "proof"
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one integration_proof", result.stderr)

    def test_contract_required_rejects_generic_authority_root(self) -> None:
        payload = contract_required_payload()
        payload["tasks"][0]["taskContract"]["authorityRoot"] = "apps/mission-control"
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authorityRoot is too broad", result.stderr)

    def test_contract_required_rejects_broad_root_for_one_exact_writable_file(self) -> None:
        payload = contract_required_payload()
        contract = payload["tasks"][0]["taskContract"]
        contract["mutationRoot"] = "apps/mission-control/src/lib/knowledge-plane"
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must equal its one exact writable file", result.stderr)

    def test_contract_required_rejects_broad_proof_root(self) -> None:
        payload = contract_required_payload()
        payload["tasks"][0]["taskContract"]["proofRoot"] = (
            "apps/mission-control/src/lib/knowledge-plane/__tests__"
        )
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be one exact proof path", result.stderr)

    def test_contract_required_rejects_recursive_existing_writable_scope(self) -> None:
        payload = contract_required_payload()
        contract = payload["tasks"][0]["taskContract"]
        contract["mutationRoot"] = "apps/mission-control/src/lib/knowledge-plane/contracts"
        contract["writableFiles"] = [
            "apps/mission-control/src/lib/knowledge-plane/contracts/**"
        ]
        contract["createdFileGlobs"] = []
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("recursive writable scope over existing files is forbidden", result.stderr)

    def test_contract_required_generic_proof_does_not_require_json_authority_artifact(self) -> None:
        payload = contract_required_payload()
        proof_contract = payload["tasks"][1]["taskContract"]
        proof_contract["outputArtifacts"] = ["Focused release proof"]
        result = self.run_validator(payload, "--contract-required")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_contract_required_rejects_proof_files_on_normal_implementation(self) -> None:
        payload = contract_required_payload()
        contract = payload["tasks"][0]["taskContract"]
        contract["proofFiles"] = [contract["proofRoot"]]
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("implementation_owns_proof", result.stderr)

    def test_contract_required_rejects_software_test_without_proof_files(self) -> None:
        payload = contract_required_payload()
        contract = payload["tasks"][0]["taskContract"]
        contract["proofFiles"] = []
        contract["verification"] = {
            "focusedTests": [],
            "qualityGates": ["software_test"],
        }
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("software_test_proof_missing", result.stderr)

    def test_contract_required_rejects_focused_test_outside_proof_files(self) -> None:
        payload = contract_required_payload()
        proof_contract = payload["tasks"][1]["taskContract"]
        proof_contract["verification"]["focusedTests"] = [
            "apps/mission-control/src/lib/knowledge-plane/__tests__/other.test.ts"
        ]
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("focused_test_outside_proof_scope", result.stderr)

    def test_contract_required_rejects_dependency_cycles(self) -> None:
        payload = contract_required_payload()
        payload["tasks"][0]["dependsOn"] = [payload["tasks"][1]["id"]]
        payload["tasks"][1]["dependsOn"] = [payload["tasks"][0]["id"]]
        result = self.run_validator(payload, "--contract-required")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dependency_cycle", result.stderr)

    def test_contract_required_reports_all_task_graph_and_coverage_findings_together(self) -> None:
        payload = contract_required_payload()
        payload["tasks"][0]["taskContract"]["authorityRoot"] = "apps/mission-control"
        payload["tasks"][0]["taskContract"]["proofRoot"] = "apps/mission-control/src/lib/knowledge-plane/__tests__"
        payload["tasks"][1]["dependsOn"] = ["missing-provider"]
        payload["tasks"][2]["dependsOn"] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "decomposition.json"
            report_path = Path(temp_dir) / "report.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(VALIDATOR),
                    "--contract-required",
                    str(path),
                    "--report",
                    str(report_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(report_path.read_text())
            codes = {finding["code"] for finding in report["findings"]}
            self.assertIn("authority_root_too_broad", codes)
            self.assertIn("proof_root_not_exact", codes)
            self.assertIn("dependency_not_found", codes)
            self.assertIn("integration_proof_dependencies_missing", codes)
            self.assertGreaterEqual(report["findingCount"], 4)


if __name__ == "__main__":
    unittest.main()
