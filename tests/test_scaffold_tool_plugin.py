from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class TestScaffoldToolPlugin(unittest.TestCase):
    def test_scaffold_generates_expected_files(self) -> None:
        intent = "tmp scaffold tool"
        tool_key = intent.replace(" ", "_")
        plugin_path = Path("main_app/services/agent_dashboard/executor_plugins") / f"{tool_key}_plugin.py"
        schema_path = Path("main_app/schemas/assets") / f"{tool_key}.v1.json"
        test_path = Path("tests") / f"test_{tool_key}_plugin.py"
        renderer_path = Path("main_app/ui/agent_dashboard/renderer_plugins") / f"{tool_key}.py"
        for path in [plugin_path, schema_path, test_path, renderer_path]:
            if path.exists():
                path.unlink()
        try:
            cmd = [
                sys.executable,
                "scripts/scaffold_tool_plugin.py",
                "--intent",
                intent,
                "--kind",
                "structured",
                "--depends-on",
                "artifact.topic.text",
                "--produces",
                "artifact.tmp_scaffold_tool.primary",
                "--with-renderer",
                "true",
                "--with-workflow-key",
                "full_asset_suite",
            ]
            completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue(plugin_path.exists())
            self.assertTrue(schema_path.exists())
            self.assertTrue(test_path.exists())
            self.assertTrue(renderer_path.exists())
        finally:
            for path in [plugin_path, schema_path, test_path, renderer_path]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
