import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checkpoint = load_module(
    "decomposition_checkpoint",
    ROOT / "scripts" / "decomposition_checkpoint.py",
)


class CheckpointContinuityTest(unittest.TestCase):
    def setUp(self):
        self.archive = tempfile.TemporaryDirectory()
        self.previous_archive_root = checkpoint.os.environ.get(
            "BERNARD_DECOMPOSITION_ARCHIVE_ROOT"
        )
        checkpoint.os.environ["BERNARD_DECOMPOSITION_ARCHIVE_ROOT"] = self.archive.name

    def tearDown(self):
        if self.previous_archive_root is None:
            checkpoint.os.environ.pop("BERNARD_DECOMPOSITION_ARCHIVE_ROOT", None)
        else:
            checkpoint.os.environ[
                "BERNARD_DECOMPOSITION_ARCHIVE_ROOT"
            ] = self.previous_archive_root
        self.archive.cleanup()

    def test_rejects_full_key_regeneration_for_unchanged_objective(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            objective_path = workspace / "objective.json"
            objective_path.write_text(json.dumps({"id": "obj-1", "title": "Stable"}))
            decomposition_path = workspace / "decomposition.json"
            decomposition_path.write_text("{}")
            manifest_path = workspace / "manifest.json"
            manifest_path.write_text(json.dumps({"tasks": [{"key": "first"}]}))
            checkpoint.record_build(
                objective_id="obj-1",
                manifest_path=manifest_path,
                decomposition_path=decomposition_path,
                objective_path=objective_path,
                workspace=workspace,
            )

            manifest_path.write_text(json.dumps({"tasks": [{"key": "replacement"}]}))
            with self.assertRaisesRegex(ValueError, "replaced every stable task key"):
                checkpoint.record_build(
                    objective_id="obj-1",
                    manifest_path=manifest_path,
                    decomposition_path=decomposition_path,
                    objective_path=objective_path,
                    workspace=workspace,
                )

    def test_allows_bounded_key_correction(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            objective_path = workspace / "objective.json"
            objective_path.write_text(json.dumps({"id": "obj-1", "title": "Stable"}))
            decomposition_path = workspace / "decomposition.json"
            decomposition_path.write_text("{}")
            manifest_path = workspace / "manifest.json"
            manifest_path.write_text(json.dumps({"tasks": [{"key": "first"}]}))
            checkpoint.record_build(
                objective_id="obj-1",
                manifest_path=manifest_path,
                decomposition_path=decomposition_path,
                objective_path=objective_path,
                workspace=workspace,
            )

            manifest_path.write_text(json.dumps({"tasks": [{"key": "first"}, {"key": "split"}]}))
            result = checkpoint.record_build(
                objective_id="obj-1",
                manifest_path=manifest_path,
                decomposition_path=decomposition_path,
                objective_path=objective_path,
                workspace=workspace,
            )
            self.assertEqual(result["metrics"]["fullRegenerationCount"], 0)
            self.assertEqual(result["metrics"]["stableTaskIdentityCount"], 1)

    def test_restores_deleted_workspace_checkpoint_from_inflight_journal(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            objective_path = workspace / "objective.json"
            objective_path.write_text(json.dumps({"id": "obj-1", "title": "Stable"}))
            decomposition_path = workspace / "decomposition.json"
            decomposition_path.write_text("{}")
            manifest_path = workspace / "manifest.json"
            manifest_path.write_text(json.dumps({"tasks": [{"key": "first"}]}))
            first = checkpoint.record_build(
                objective_id="obj-1",
                manifest_path=manifest_path,
                decomposition_path=decomposition_path,
                objective_path=objective_path,
                workspace=workspace,
            )

            checkpoint.checkpoint_path(workspace).unlink()

            restored = checkpoint.load_checkpoint(workspace)
            self.assertEqual(restored, first)
            self.assertEqual(
                json.loads(checkpoint.checkpoint_path(workspace).read_text()),
                first,
            )

    def test_workspace_tampering_cannot_reset_correction_history(self):
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            objective_path = workspace / "objective.json"
            objective_path.write_text(json.dumps({"id": "obj-1", "title": "Stable"}))
            decomposition_path = workspace / "decomposition.json"
            decomposition_path.write_text("{}")
            manifest_path = workspace / "manifest.json"
            manifest_path.write_text(json.dumps({"tasks": [{"key": "first"}]}))
            checkpoint.record_build(
                objective_id="obj-1",
                manifest_path=manifest_path,
                decomposition_path=decomposition_path,
                objective_path=objective_path,
                workspace=workspace,
            )
            manifest_path.write_text(
                json.dumps({"tasks": [{"key": "first"}, {"key": "second"}]})
            )
            corrected = checkpoint.record_build(
                objective_id="obj-1",
                manifest_path=manifest_path,
                decomposition_path=decomposition_path,
                objective_path=objective_path,
                workspace=workspace,
            )
            self.assertEqual(corrected["correctionRound"], 1)

            tampered = dict(corrected)
            tampered["correctionRound"] = 0
            checkpoint.checkpoint_path(workspace).write_text(json.dumps(tampered))

            restored = checkpoint.load_checkpoint(workspace)
            self.assertEqual(restored["correctionRound"], 1)
            self.assertEqual(
                json.loads(checkpoint.checkpoint_path(workspace).read_text())[
                    "correctionRound"
                ],
                1,
            )


if __name__ == "__main__":
    unittest.main()
