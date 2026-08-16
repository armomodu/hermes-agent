import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_decomposition_json.py")
SPEC = importlib.util.spec_from_file_location("validator", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(VALIDATOR)


class ArtifactQualityAssignmentTest(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "deliveryProfile": "artifact_delivery",
            "approvedSlices": [{"name": "maeve_quality_review"}],
        }

    def test_permits_exact_maeve_quality_execution_slice(self):
        self.assertTrue(VALIDATOR.is_artifact_delivery_maeve_quality_task({
            "title": "maeve_quality_review",
            "assignee": "Maeve",
            "taskType": "execution",
        }, self.contract))

    def test_rejects_maeve_on_other_execution_slice(self):
        self.assertFalse(VALIDATOR.is_artifact_delivery_maeve_quality_task({
            "title": "text_draft",
            "assignee": "Maeve",
            "taskType": "execution",
        }, self.contract))

    def test_software_profile_remains_strict(self):
        self.assertFalse(VALIDATOR.is_artifact_delivery_maeve_quality_task({
            "title": "maeve_quality_review",
            "assignee": "Maeve",
            "taskType": "execution",
        }, {**self.contract, "deliveryProfile": "production_component"}))

    def test_actor_identity_is_case_insensitive(self):
        allowed = {VALIDATOR.canonical_agent(value) for value in VALIDATOR.TASK_TYPE_ALLOWED_ASSIGNEES["review"]}
        self.assertIn(VALIDATOR.canonical_agent("Operator"), allowed)


if __name__ == "__main__":
    unittest.main()
