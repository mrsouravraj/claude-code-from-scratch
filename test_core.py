"""
test_core.py: Comprehensive unit tests for the refactored run_bash and async_bash functions.

This module tests the configurable timeout and output truncation features
added to the run_bash and async_bash functions.
"""

import unittest
import asyncio
import time
from unittest.mock import patch, MagicMock
from core import (
    run_bash,
    async_bash,
    _DEFAULT_TIMEOUT,
    _DEFAULT_MAX_OUTPUT_CHARS,
)


class TestRunBashBasic(unittest.TestCase):
    """Test basic functionality of run_bash."""

    def test_simple_echo_command(self):
        """Test a simple echo command."""
        result = run_bash("echo 'hello world'")
        self.assertEqual(result, "hello world")

    def test_no_output(self):
        """Test command with no output returns placeholder."""
        result = run_bash("true")
        self.assertEqual(result, "(no output)")

    def test_error_capture(self):
        """Test that stderr is captured."""
        result = run_bash("ls /nonexistent_directory_12345")
        # The actual error message varies by OS, but should contain 'file' or 'directory'
        self.assertIn("No such file or directory", result)

    def test_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked."""
        result = run_bash("rm -rf /")
        self.assertEqual(result, "Error: dangerous command blocked")

    def test_sudo_blocked(self):
        """Test that sudo commands are blocked."""
        result = run_bash("sudo ls")
        self.assertEqual(result, "Error: dangerous command blocked")

    def test_reboot_blocked(self):
        """Test that reboot commands are blocked."""
        result = run_bash("reboot")
        self.assertEqual(result, "Error: dangerous command blocked")


class TestRunBashTimeout(unittest.TestCase):
    """Test timeout functionality in run_bash."""

    def test_default_timeout_value(self):
        """Test that default timeout is 120 seconds."""
        self.assertEqual(_DEFAULT_TIMEOUT, 120)

    def test_timeout_with_custom_value(self):
        """Test timeout with a custom value (1 second)."""
        result = run_bash("sleep 10", timeout=1)
        self.assertIn("Error: timeout", result)
        self.assertIn("1s", result)

    def test_timeout_error_message_format(self):
        """Test that timeout error includes the timeout value."""
        result = run_bash("sleep 5", timeout=2)
        self.assertEqual(result, "Error: timeout (2s)")

    def test_command_completes_within_timeout(self):
        """Test that commands completing within timeout work fine."""
        result = run_bash("echo 'test'", timeout=10)
        self.assertEqual(result, "test")


class TestRunBashOutputTruncation(unittest.TestCase):
    """Test output truncation functionality in run_bash."""

    def test_default_max_output_value(self):
        """Test that default max output is 50000 characters."""
        self.assertEqual(_DEFAULT_MAX_OUTPUT_CHARS, 50000)

    def test_output_truncation_with_custom_limit(self):
        """Test output is truncated when exceeding max_output_chars."""
        # Generate a large output
        large_output = "a" * 1000
        result = run_bash(f"echo '{large_output}'", max_output_chars=100)
        self.assertEqual(len(result), 100)
        self.assertTrue(result.startswith("a"))

    def test_output_truncation_exact_limit(self):
        """Test output at exact truncation limit."""
        result = run_bash("echo 'hello'", max_output_chars=5)
        self.assertEqual(result, "hello")

    def test_output_truncation_below_limit(self):
        """Test output shorter than max_output_chars."""
        result = run_bash("echo 'hi'", max_output_chars=100)
        self.assertEqual(result, "hi")

    def test_zero_max_output_chars(self):
        """Test with max_output_chars set to 0."""
        result = run_bash("echo 'test'", max_output_chars=0)
        self.assertEqual(result, "")

    def test_large_output_truncation(self):
        """Test truncation with a large output."""
        # Create a large output with a Python one-liner
        result = run_bash(
            "python3 -c \"print('x' * 10000)\"",
            max_output_chars=1000
        )
        self.assertEqual(len(result), 1000)


class TestRunBashCombined(unittest.TestCase):
    """Test run_bash with both timeout and max_output_chars."""

    def test_timeout_and_truncation_together(self):
        """Test using both timeout and max_output_chars parameters."""
        result = run_bash(
            "echo 'hello world'",
            timeout=5,
            max_output_chars=5
        )
        self.assertEqual(result, "hello")

    def test_both_none_uses_defaults(self):
        """Test that passing None uses default values."""
        result = run_bash("echo 'test'", timeout=None, max_output_chars=None)
        self.assertEqual(result, "test")

    def test_backward_compatibility_no_args(self):
        """Test backward compatibility: calling with only command."""
        result = run_bash("echo 'test'")
        self.assertEqual(result, "test")


class TestAsyncBashBasic(unittest.TestCase):
    """Test basic functionality of async_bash."""

    def test_simple_async_echo_command(self):
        """Test async execution of simple echo command."""
        async def test():
            result = await async_bash("echo 'hello world'")
            return result
        
        result = asyncio.run(test())
        self.assertEqual(result, "hello world")

    def test_async_no_output(self):
        """Test async command with no output returns placeholder."""
        async def test():
            result = await async_bash("true")
            return result
        
        result = asyncio.run(test())
        self.assertEqual(result, "(no output)")

    def test_async_dangerous_command_blocked(self):
        """Test that dangerous commands are blocked in async version."""
        async def test():
            result = await async_bash("rm -rf /")
            return result
        
        result = asyncio.run(test())
        self.assertEqual(result, "Error: dangerous command blocked")


class TestAsyncBashTimeout(unittest.TestCase):
    """Test timeout functionality in async_bash."""

    def test_async_timeout_with_custom_value(self):
        """Test async timeout with a custom value."""
        async def test():
            result = await async_bash("sleep 10", timeout=1)
            return result
        
        result = asyncio.run(test())
        self.assertIn("Error: timeout", result)
        self.assertIn("1s", result)

    def test_async_command_completes_within_timeout(self):
        """Test that async commands completing within timeout work fine."""
        async def test():
            result = await async_bash("echo 'test'", timeout=10)
            return result
        
        result = asyncio.run(test())
        self.assertEqual(result, "test")


class TestAsyncBashOutputTruncation(unittest.TestCase):
    """Test output truncation functionality in async_bash."""

    def test_async_output_truncation_with_custom_limit(self):
        """Test async output is truncated when exceeding max_output_chars."""
        async def test():
            large_output = "a" * 1000
            result = await async_bash(
                f"echo '{large_output}'",
                max_output_chars=100
            )
            return result
        
        result = asyncio.run(test())
        self.assertEqual(len(result), 100)
        self.assertTrue(result.startswith("a"))

    def test_async_output_truncation_exact_limit(self):
        """Test async output at exact truncation limit."""
        async def test():
            result = await async_bash("echo 'hello'", max_output_chars=5)
            return result
        
        result = asyncio.run(test())
        self.assertEqual(result, "hello")


class TestAsyncBashCombined(unittest.TestCase):
    """Test async_bash with both timeout and max_output_chars."""

    def test_async_timeout_and_truncation_together(self):
        """Test async using both timeout and max_output_chars parameters."""
        async def test():
            result = await async_bash(
                "echo 'hello world'",
                timeout=5,
                max_output_chars=5
            )
            return result
        
        result = asyncio.run(test())
        self.assertEqual(result, "hello")

    def test_async_backward_compatibility_no_args(self):
        """Test async backward compatibility: calling with only command."""
        async def test():
            result = await async_bash("echo 'test'")
            return result
        
        result = asyncio.run(test())
        self.assertEqual(result, "test")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and special scenarios."""

    def test_command_with_special_characters(self):
        """Test commands with special shell characters."""
        result = run_bash("echo 'hello | grep hello'")
        self.assertIn("hello", result)

    def test_command_with_pipes(self):
        """Test command with piped output."""
        result = run_bash("echo 'hello world' | wc -w")
        self.assertEqual(result.strip(), "2")

    def test_multiline_output(self):
        """Test command producing multiline output."""
        result = run_bash("echo -e 'line1\\nline2\\nline3'")
        self.assertIn("line1", result)
        self.assertIn("line2", result)
        self.assertIn("line3", result)

    def test_stderr_to_stdout_merge(self):
        """Test that stderr is merged with stdout."""
        result = run_bash("ls /nonexistent_dir 2>&1")
        self.assertIn("No such file", result)

    def test_empty_command_output(self):
        """Test command with whitespace-only output."""
        result = run_bash("echo '   ' | tr -d ' '")
        self.assertEqual(result, "(no output)")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with old function signatures."""

    def test_old_dispatch_still_works(self):
        """Test that existing dispatch maps still work."""
        # Simulating how BASIC_DISPATCH and EXTENDED_DISPATCH call run_bash
        dispatch_fn = lambda inp: run_bash(inp["command"])
        result = dispatch_fn({"command": "echo 'test'"})
        self.assertEqual(result, "test")

    def test_timeout_parameter_optional(self):
        """Test that timeout parameter is fully optional."""
        result = run_bash("echo 'test'")  # No timeout parameter
        self.assertEqual(result, "test")

    def test_max_output_chars_parameter_optional(self):
        """Test that max_output_chars parameter is fully optional."""
        result = run_bash("echo 'test'")  # No max_output_chars parameter
        self.assertEqual(result, "test")


if __name__ == "__main__":
    unittest.main()
