from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
import unittest
from pathlib import Path


def _load_script_module(path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("validate_plugin_specs_script", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load script module.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestValidatePluginSpecsScript(unittest.TestCase):
    def test_script_passes_on_defaults(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_plugin_specs.py"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_script_fails_on_malformed_registry(self) -> None:
        module = _load_script_module(Path("scripts/validate_plugin_specs.py"))

        class _BadRegistry:
            def list_plugin_specs(self):
                return [{"plugin_key": "", "intent": "", "execution_spec": {}}]

        class _BadWorkflowRegistry:
            def list_workflow_plugin_specs(self):
                return [{"workflow_key": "", "tool_keys": []}]

        module.build_default_agent_tool_registry = lambda: _BadRegistry()
        module.build_default_agent_workflow_registry = lambda: _BadWorkflowRegistry()
        result = module.main()
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
