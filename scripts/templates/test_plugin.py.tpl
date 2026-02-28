from __future__ import annotations

import unittest

from main_app.services.agent_dashboard.plugin_sdk import validate_tool_plugin_spec
from main_app.services.agent_dashboard.executor_plugins.${tool_key}_plugin import build_${tool_key}_plugin_spec


class Test${class_name}PluginSpec(unittest.TestCase):
    def test_spec_validates(self) -> None:
        spec = build_${tool_key}_plugin_spec()
        result = validate_tool_plugin_spec(spec)
        self.assertTrue(result.ok)


if __name__ == "__main__":
    unittest.main()
