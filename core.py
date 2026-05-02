#!/usr/bin/env python3
"""
core.py — A minimal coding agent powered by the Anthropic API.

Implements a perception-action loop: the LLM thinks, optionally calls tools
(currently just bash), observes the results, and repeats until it has a
final answer.
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
# 4. Tool definitions & dispatch map
# ──────────────────────────────────────────────
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

# ──────────────────────────────────────────────
# 5. Tool handlers
# ──────────────────────────────────────────────

def run_bash(command: str) -> str:
    """
    Executes a shell command synchronously and returns the output.

    Args:
        command (str): The raw shell command string to execute.

    Returns:
        str: Combined stdout and stderr output, truncated if necessary.
    """
    # Security check: verify the command doesn't contain blacklisted patterns
    if any(blocked in command for blocked in _ALWAYS_BLOCK):
        return "Error: dangerous command blocked"

    try:
        # Execute command in the current working directory using the system shell
        result = subprocess.run(
            command, shell=True, cwd=os.getcwd(),
            capture_output=True, text=True, timeout=120,
        )
        # Combine standard output and error output, then strip whitespace
        output = (result.stdout + result.stderr).strip()
        # Return output or a placeholder, capped at 50k chars to protect context window
        return output[:50000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: timeout (120s)"
    except Exception as e:
        return f"Error: {e}"

# ──────────────────────────────────────────────
# 6. Agent loop logic
# ──────────────────────────────────────────────

def dispatch_tools(response_content: list, dispatch: dict) -> List[Dict[str, Any]]:
    """
    Executes all tool_use blocks from a model's response and collects the results.

    Args:
        response_content (list): The `content` list from an Anthropic Message object.
        dispatch (dict): The dispatch map to use for routing tool calls.

    Returns:
        list: A list of `tool_result` dictionaries ready to be sent back to the model.
    """
    results = []

    for block in response_content:
        if block.type != "tool_use":
            continue

        tool_name   = block.name
        tool_input  = block.input
        tool_use_id = block.id
        handler     = dispatch.get(tool_name)

        # Log the tool call for user visibility.
        first_val = str(list(tool_input.values())[0])[:80] if tool_input else ""
        print(f"\033[33m[{tool_name}] {first_val}...\033[0m")  # Yellow text

        if handler:
            try:
                output = handler(tool_input)
            except Exception as e:
                output = f"Error during tool execution: {e}"
        else:
            output = f"Error: Unknown tool '{tool_name}'"

        print(str(output)[:300])  # Print a preview of the output.

        results.append({
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": str(output),
        })

    return results


def agent_loop(messages: List[Dict[str, Any]], dispatch: dict) -> None:
    """
    Runs the core agent interaction loop until the model provides a final answer.

    This function mutates the `messages` list in place, appending each new
    assistant response and the results of any tool calls.

    Args:
        messages (list): The conversation history, which will be updated.
        dispatch (dict): A map of tool names to their handler functions.
    """
    while True:
        # 1. Call the LLM with the current conversation history and available tools.
        print("\n\033[36m> Thinking...\033[0m")
        response = client.messages.create(
            model=MODEL,
            system=DEFAULT_SYSTEM,
            messages=messages,
            tools=BASIC_TOOLS,
            max_tokens=8000,
        )

        # Append the assistant's entire response (including any tool calls) to the history.
        messages.append({"role": "assistant", "content": response.content})

        # 2. Check if the loop should terminate.
        # If the stop reason is not 'tool_use', the model has provided its final answer.
        if response.stop_reason != "tool_use":
            break

        # 3. If the model wants to use tools, execute them.
        results = dispatch_tools(response.content, dispatch)

        # Append the tool results to the history as a new "user" message.
        messages.append({"role": "user", "content": results})

# ──────────────────────────────────────────────
# 7. Main entry-point (REPL)
# ──────────────────────────────────────────────

def main() -> None:
    """Interactive REPL — accepts user queries and runs the agent loop."""
    history: List[Dict[str, Any]] = []

    while True:
        try:
            query = input("\033[36ms01 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if query.strip().lower() in ("q", "exit", ""):
            break

        # Add the user's query to the conversation history.
        history.append({"role": "user", "content": query})

        # Run the agent loop (may involve multiple model ↔ tool turns).
        agent_loop(history, BASIC_DISPATCH)

        # Print the final text response from the assistant.
        last_message = history[-1]
        print("\n\033[32mFinal Answer:\033[0m")
        for block in last_message.get("content", []):
            if block.type == "text":
                print(block.text)
        print()


if __name__ == "__main__":
    main()