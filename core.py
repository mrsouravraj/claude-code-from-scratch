#!/usr/bin/env python3
"""
core.py — Shared foundation for the claude-code-from-scratch agent series.

This module is a pure library — it defines configuration, safety rules,
tool schemas, tool handlers, and the dispatch helper. It contains no REPL
and no agent loop; those live in each episode's script (e.g.
perception_action_loop.py) so every lesson can evolve independently.

Exports used by other scripts:
    client, MODEL, DEFAULT_SYSTEM          — Anthropic API setup
    BASIC_TOOLS, BASIC_DISPATCH            — minimal bash-only toolset
    EXTENDED_TOOLS, EXTENDED_DISPATCH      — richer toolset (read, grep, …)
    dispatch_tools()                       — execute tool_use blocks
"""

# ──────────────────────────────────────────────
# 1. Imports
# ──────────────────────────────────────────────
import os
import subprocess
from typing import List, Dict, Any

from anthropic import Anthropic
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# 2. Configuration
# ──────────────────────────────────────────────
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")   # https://console.anthropic.com/
MODEL_ID          = os.getenv("MODEL_ID")

client = Anthropic(base_url="https://api.anthropic.com", api_key=ANTHROPIC_API_KEY)
MODEL  = MODEL_ID

DEFAULT_SYSTEM = (
    f"You are a coding agent at {os.getcwd()}. "
    "Use tools to solve tasks. Act, don't explain."
)

# ──────────────────────────────────────────────
# 3. Safety — blocked command patterns
# ──────────────────────────────────────────────
_ALWAYS_BLOCK: List[str] = [
    "rm -rf /",         # Prevent root filesystem deletion
    "sudo",             # Prevent privilege escalation
    "shutdown",         # Prevent system termination
    "reboot",           # Prevent system restart
    "> /dev/",          # Prevent direct hardware / device writing
    ":(){ :|:& };:",    # Prevent fork bombs
]

# ──────────────────────────────────────────────
# 4. Tool handlers
# ──────────────────────────────────────────────

def run_bash(command: str) -> str:
    """Run a shell command and return its output (stdout + stderr)."""
    if any(blocked in command for blocked in _ALWAYS_BLOCK):
        return "Error: dangerous command blocked"
    try:
        result = subprocess.run(
            command, shell=True, cwd=os.getcwd(),
            capture_output=True, text=True, timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, start_line: int = None, end_line: int = None) -> str:
    """Read a file and return numbered lines, optionally sliced."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        s = (start_line or 1) - 1
        e = end_line or len(lines)
        numbered = "".join(f"{s + 1 + i:4d}\t{l}" for i, l in enumerate(lines[s:e]))
        return numbered[:50000] or "(empty file)"
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error reading {path}: {e}"


def run_grep(pattern: str, path: str = ".", recursive: bool = True) -> str:
    """Search for a regex pattern across files."""
    try:
        flags = ["-r"] if recursive else []
        r = subprocess.run(
            ["grep", "-n", *flags, pattern, path],
            capture_output=True, text=True, timeout=30,
        )
        return ((r.stdout + r.stderr).strip() or "(no matches)")[:10000]
    except Exception as e:
        return f"Error: {e}"

# ──────────────────────────────────────────────
# 5. Tool schemas & dispatch maps
# ──────────────────────────────────────────────

# --- Minimal toolset: bash only ---
BASIC_TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
]

BASIC_DISPATCH: dict = {
    "bash": lambda inp: run_bash(inp["command"]),
}

# --- Extended toolset: bash + read + grep (write/glob/revert coming soon) ---
EXTENDED_TOOLS = BASIC_TOOLS + [
    {
        "name": "read",
        "description": (
            "Read a file and return numbered lines. Use start_line/end_line "
            "for large files. Returns up to 50,000 characters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path":       {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line":   {"type": "integer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "grep",
        "description": "Search for a regex pattern across files. Returns file paths and line numbers of matches.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern":   {"type": "string"},
                "path":      {"type": "string"},
                "recursive": {"type": "boolean"},
            },
            "required": ["pattern"],
        },
    },
]

EXTENDED_DISPATCH: dict = {
    "bash": lambda inp: run_bash(inp["command"]),
    "read": lambda inp: run_read(inp["path"], inp.get("start_line"), inp.get("end_line")),
    "grep": lambda inp: run_grep(inp["pattern"], inp.get("path", "."), inp.get("recursive", True)),
}

# ──────────────────────────────────────────────
# 6. Dispatch helper
# ──────────────────────────────────────────────

def dispatch_tools(response_content: list, dispatch: dict) -> List[Dict[str, Any]]:
    """
    Execute all tool_use blocks from a model response and collect results.

    Args:
        response_content: The `content` list from an Anthropic Message object.
        dispatch:         Map of tool names → handler callables.

    Returns:
        List of `tool_result` dicts ready to be sent back to the model.
    """
    results = []

    for block in response_content:
        if block.type != "tool_use":
            continue

        tool_name   = block.name
        tool_input  = block.input
        tool_use_id = block.id
        handler     = dispatch.get(tool_name)

        # Log the tool call for user visibility (yellow text).
        first_val = str(list(tool_input.values())[0])[:80] if tool_input else ""
        print(f"\033[33m[{tool_name}] {first_val}...\033[0m")

        if handler:
            try:
                output = handler(tool_input)
            except Exception as e:
                output = f"Error during tool execution: {e}"
        else:
            output = f"Error: Unknown tool '{tool_name}'"

        print(str(output)[:300])  # preview for the user

        results.append({
            "type":        "tool_result",
            "tool_use_id": tool_use_id,
            "content":     str(output),
        })

    return results


def stream_loop(
    messages: List[Dict[str, Any]],
    tools: list,
    dispatch: dict,
) -> None:
    """
    A generalized streaming agent loop.

    Streams LLM text to the terminal in real-time, then executes any
    tool calls requested by the model. Repeats until the model stops
    requesting tools (stop_reason == 'end_turn').

    Args:
        messages: Conversation history — mutated in place.
        tools:    Tool schema list to pass to the API.
        dispatch: Map of tool names → handler callables.
    """
    while True:
        print("\n\033[36m> Thinking...\033[0m")
        full_content = []
        stop_reason  = None

        with client.messages.stream(
            model=MODEL,
            system=DEFAULT_SYSTEM,
            messages=messages,
            tools=tools,
            max_tokens=8000,
        ) as stream:
            for event in stream:
                event_type = type(event).__name__

                # Stream text deltas to the terminal as they arrive.
                if event_type == "RawContentBlockDeltaEvent":
                    delta = event.delta
                    if hasattr(delta, "text"):
                        print(delta.text, end="", flush=True)

                # Capture the final message once the stream is complete.
                elif event_type == "MessageStopEvent":
                    final = stream.get_final_message()
                    full_content = final.content
                    stop_reason  = final.stop_reason

        print()  # newline after streamed text

        # Record the full assistant response in history.
        messages.append({"role": "assistant", "content": full_content})

        if stop_reason != "tool_use":
            break

        # Execute requested tools and feed results back.
        results = dispatch_tools(full_content, dispatch)
        messages.append({"role": "user", "content": results})