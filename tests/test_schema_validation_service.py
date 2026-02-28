from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main_app.services.agent_dashboard.schema_validation_service as schema_validation_service
from main_app.services.agent_dashboard.schema_validation_service import (
    schema_validation_passed,
    validate_artifact,
)


class TestSchemaValidationService(unittest.TestCase):
    def test_valid_topic_artifact_passes(self) -> None:
        summary = validate_artifact(
            intent="topic",
            artifact={
                "sections": [
                    {"key": "artifact.topic.text", "data": "This is a valid topic explanation text."}
                ]
            },
            schema_ref={"intent": "topic", "version": "v1", "id": "topic.v1"},
        )
        self.assertTrue(schema_validation_passed(summary))

    def test_invalid_topic_artifact_fails(self) -> None:
        summary = validate_artifact(
            intent="topic",
            artifact={
                "sections": [
                    {"key": "artifact.topic.text", "data": {"invalid": "shape"}}
                ]
            },
            schema_ref={"intent": "topic", "version": "v1", "id": "topic.v1"},
        )
        self.assertEqual(summary.get("status"), "failed")
        self.assertTrue(isinstance(summary.get("issues"), list))

    def test_domain_schema_candidate_is_checked_first(self) -> None:
        artifact = {
            "sections": [
                {"key": "artifact.topic.text", "data": "Valid topic markdown"}
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            first_path = Path(tmpdir) / "domain_first.json"
            fallback_path = Path(tmpdir) / "legacy_fallback.json"
            first_path.write_text(
                json.dumps(
                    {
                        "id": "topic.v1",
                        "intent": "topic",
                        "version": "v1",
                        "required_section_key": "artifact.topic.text",
                        "required_data_type": "object",
                    }
                ),
                encoding="utf-8",
            )
            fallback_path.write_text(
                json.dumps(
                    {
                        "id": "topic.v1",
                        "intent": "topic",
                        "version": "v1",
                        "required_section_key": "artifact.topic.text",
                        "required_data_type": "string",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                schema_validation_service,
                "_schema_candidate_paths",
                return_value=[first_path, fallback_path],
            ):
                summary = validate_artifact(
                    intent="topic",
                    artifact=artifact,
                    schema_ref={"intent": "topic", "version": "v1", "id": "topic.v1"},
                )
            self.assertEqual(summary.get("status"), "failed")
            issues = summary.get("issues")
            self.assertIsInstance(issues, list)
            assert isinstance(issues, list)
            self.assertTrue(any("must be object" in str(item.get("message", "")) for item in issues if isinstance(item, dict)))

    def test_legacy_schema_fallback_used_when_domain_schema_missing(self) -> None:
        artifact = {
            "sections": [
                {"key": "artifact.topic.text", "data": "Valid topic markdown"}
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_domain = Path(tmpdir) / "missing_domain.json"
            fallback_path = Path(tmpdir) / "legacy_fallback.json"
            fallback_path.write_text(
                json.dumps(
                    {
                        "id": "topic.v1",
                        "intent": "topic",
                        "version": "v1",
                        "required_section_key": "artifact.topic.text",
                        "required_data_type": "string",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                schema_validation_service,
                "_schema_candidate_paths",
                return_value=[missing_domain, fallback_path],
            ):
                summary = validate_artifact(
                    intent="topic",
                    artifact=artifact,
                    schema_ref={"intent": "topic", "version": "v1", "id": "topic.v1"},
                )
            self.assertTrue(schema_validation_passed(summary))


if __name__ == "__main__":
    unittest.main()
