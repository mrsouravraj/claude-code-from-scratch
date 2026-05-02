"""
test_integration.py: Integration tests to verify backward compatibility.

This module tests that the refactored run_bash function integrates properly
with existing code in perception_action_loop.py, tool_use.py, and todo_write.py.
"""

import unittest
from unittest.mock import patch, MagicMock
from core import (
    BASIC_TOOLS,
    BASIC_DISPATCH,
    EXTENDED_TOOLS,
    EXTENDED_DISPATCH,
    run_bash,
    _DEFAULT_TIMEOUT,
    _DEFAULT_MAX_OUTPUT_CHARS,
)


class TestBasicDispatchIntegration(unittest.TestCase):
    """Test backward compatibility with BASIC_DISPATCH from perception_action_loop.py."""

    def test_basic_dispatch_bash_exists(self):
        """Test that BASIC_DISPATCH contains bash tool handler."""
        self.assertIn("bash", BASIC_DISPATCH)

    def test_basic_dispatch_calls_run_bash(self):
        """Test that BASIC_DISPATCH['bash'] correctly calls run_bash."""
        handler = BASIC_DISPATCH["bash"]
        result = handler({"command": "echo 'test'"})
        self.assertEqual(result, "test")

    def test_basic_dispatch_with_multiple_inputs(self):
        """Test BASIC_DISPATCH with various commands."""
        handler = BASIC_DISPATCH["bash"]
        
        # Test 1: Simple echo
        result1 = handler({"command": "echo 'hello'"})
        self.assertEqual(result1, "hello")
        
        # Test 2: No output
        result2 = handler({"command": "true"})
        self.assertEqual(result2, "(no output)")
        
        # Test 3: Multiple arguments in dict
        result3 = handler({"command": "echo 'world'"})
        self.assertEqual(result3, "world")


class TestExtendedDispatchIntegration(unittest.TestCase):
    """Test backward compatibility with EXTENDED_DISPATCH from tool_use.py."""

    def test_extended_dispatch_has_all_tools(self):
        """Test that EXTENDED_DISPATCH contains all expected tools."""
        expected_tools = ["bash", "read", "write", "grep", "glob", "revert"]
        for tool in expected_tools:
            self.assertIn(tool, EXTENDED_DISPATCH)

    def test_extended_dispatch_bash_works(self):
        """Test that EXTENDED_DISPATCH['bash'] still works."""
        handler = EXTENDED_DISPATCH["bash"]
        result = handler({"command": "echo 'extended'"})
        self.assertEqual(result, "extended")

    def test_extended_dispatch_preserves_functionality(self):
        """Test that other tools in EXTENDED_DISPATCH are not broken."""
        # We can't easily test read/write/grep/glob without complex setup,
        # but we can verify they exist and are callable
        for tool_name, handler in EXTENDED_DISPATCH.items():
            self.assertIsNotNone(handler)
            self.assertTrue(callable(handler))


class TestToolSchemaCompatibility(unittest.TestCase):
    """Test that tool schemas match the dispatch maps."""

    def test_basic_tools_schema_valid(self):
        """Test BASIC_TOOLS schema is valid and complete."""
        self.assertEqual(len(BASIC_TOOLS), 1)
        self.assertEqual(BASIC_TOOLS[0]["name"], "bash")
        self.assertIn("input_schema", BASIC_TOOLS[0])
        self.assertIn("command", BASIC_TOOLS[0]["input_schema"]["properties"])

    def test_extended_tools_schema_valid(self):
        """Test EXTENDED_TOOLS schema includes all expected tools."""
        tool_names = [tool["name"] for tool in EXTENDED_TOOLS]
        expected_tools = ["bash", "read", "write", "grep", "glob", "revert"]
        for tool in expected_tools:
            self.assertIn(tool, tool_names)


class TestRun_BashParameterForwarding(unittest.TestCase):
    """Test that new parameters don't break dispatch maps."""

    def test_dispatch_without_timeout_param(self):
        """Test that dispatch calls work without specifying timeout."""
        # This is how EXTENDED_DISPATCH currently calls run_bash
        handler = EXTENDED_DISPATCH["bash"]
        result = handler({"command": "echo 'test'"})
        self.assertEqual(result, "test")

    def test_dispatch_without_max_output_chars_param(self):
        """Test that dispatch calls work without specifying max_output_chars."""
        handler = BASIC_DISPATCH["bash"]
        result = handler({"command": "echo 'test'"})
        self.assertEqual(result, "test")

    def test_run_bash_direct_call_backward_compat(self):
        """Test that run_bash can be called as before (only command arg)."""
        # Old code that calls run_bash directly should still work
        result = run_bash("echo 'old_code'")
        self.assertEqual(result, "old_code")


class TestDefaultValues(unittest.TestCase):
    """Test that default values are correctly applied."""

    def test_default_timeout_is_120(self):
        """Test that _DEFAULT_TIMEOUT is 120 seconds."""
        self.assertEqual(_DEFAULT_TIMEOUT, 120)

    def test_default_max_output_is_50000(self):
        """Test that _DEFAULT_MAX_OUTPUT_CHARS is 50000."""
        self.assertEqual(_DEFAULT_MAX_OUTPUT_CHARS, 50000)

    def test_run_bash_respects_default_timeout(self):
        """Test that run_bash uses default timeout when not specified."""
        # Should complete successfully with default timeout (120s)
        result = run_bash("echo 'test'")
        self.assertEqual(result, "test")

    def test_run_bash_respects_default_truncation(self):
        """Test that run_bash uses default truncation when not specified."""
        # Should use 50000 char limit by default
        result = run_bash("echo 'hello'")
        self.assertEqual(result, "hello")


class TestSecurityBlocksUnchanged(unittest.TestCase):
    """Test that security blocks still function correctly."""

    def test_dangerous_commands_still_blocked(self):
        """Test that dangerous command patterns are still blocked."""
        dangerous_commands = [
            "rm -rf /",
            "sudo ls",
            "shutdown now",
            "reboot",
        ]
        for cmd in dangerous_commands:
            result = run_bash(cmd)
            self.assertEqual(
                result, 
                "Error: dangerous command blocked",
                f"Failed to block: {cmd}"
            )

    def test_blocked_commands_in_dispatch(self):
        """Test that blocked commands work through dispatch too."""
        handler = BASIC_DISPATCH["bash"]
        result = handler({"command": "rm -rf /"})
        self.assertEqual(result, "Error: dangerous command blocked")


class TestOutputHandling(unittest.TestCase):
    """Test output handling in dispatched commands."""

    def test_empty_output_returns_placeholder(self):
        """Test that empty output returns placeholder."""
        handler = BASIC_DISPATCH["bash"]
        result = handler({"command": "true"})
        self.assertEqual(result, "(no output)")

    def test_stderr_captured_in_dispatch(self):
        """Test that stderr is captured through dispatch."""
        handler = EXTENDED_DISPATCH["bash"]
        result = handler({"command": "ls /nonexistent_dir"})
        self.assertIn("No such file", result)

    def test_large_output_through_dispatch(self):
        """Test large output through dispatch (should use default truncation)."""
        handler = BASIC_DISPATCH["bash"]
        # Generate large output
        result = handler({
            "command": "python3 -c \"print('x' * 100000)\""
        })
        # Should be truncated to 50000 chars
        self.assertLessEqual(len(result), 50000)


class TestMixedParameterCalls(unittest.TestCase):
    """Test various ways of calling run_bash."""

    def test_only_command(self):
        """Test calling with only command."""
        result = run_bash("echo 'only_cmd'")
        self.assertEqual(result, "only_cmd")

    def test_command_and_timeout(self):
        """Test calling with command and timeout."""
        result = run_bash("echo 'cmd_timeout'", timeout=10)
        self.assertEqual(result, "cmd_timeout")

    def test_command_and_max_output(self):
        """Test calling with command and max_output_chars."""
        result = run_bash("echo 'cmd_output'", max_output_chars=3)
        self.assertEqual(result, "cmd")

    def test_command_and_both_params(self):
        """Test calling with all parameters."""
        result = run_bash("echo 'all_params'", timeout=10, max_output_chars=3)
        self.assertEqual(result, "all")

    def test_none_values_use_defaults(self):
        """Test that None values trigger default behavior."""
        result = run_bash("echo 'test'", timeout=None, max_output_chars=None)
        self.assertEqual(result, "test")


if __name__ == "__main__":
    unittest.main()
