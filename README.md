# claude-code-from-scratch

> Exploring how Claude works under the hood — rebuilding its coding-agent behaviour from scratch using the Anthropic API: prompt pipelines, context windows, and tool-driven interactions.

---

## What's inside

| File | Purpose |
|------|---------|
| `core.py` | The main agent. Imports, config, safety rules, tool definitions, `run_bash`, `agent_loop`, and the interactive REPL — all in one clean file. |
| `perception_action_loop.py` | Standalone, heavily-commented walkthrough of the same perception → action cycle. Good for learning / reference. |

---

## Quickstart (recommended — uv)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that replaces `pip` + `venv` in one command.

```bash
# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create the virtual environment and install deps
uv sync

# 3. Copy the environment template and add your API key
cp .env.example .env
# then edit .env and fill in ANTHROPIC_API_KEY and MODEL_ID

# 4. Run the agent
uv run agent
# or
uv run python core.py
```

---

## Quickstart (classic — pip)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # fill in your keys
python core.py
```

---

## Environment variables

Create a `.env` file (or export the vars) before running:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...   # Required — get yours at console.anthropic.com
MODEL_ID=claude-sonnet-4-5     # Required — any Anthropic model ID
```

---

## Project structure

```
claude-code-from-scratch/
├── core.py                   # Main agent entry-point
├── perception_action_loop.py # Annotated learning reference
├── pyproject.toml            # uv / PEP 517 project config
├── requirements.txt          # pip fallback
├── .env                      # Your secrets (git-ignored)
├── .env.example              # Template — safe to commit
├── .python-version           # Pins Python version for uv
└── README.md
```

---

## How the agent works

```
User input
    │
    ▼
agent_loop()
    │
    ├─► LLM (Anthropic API)
    │        │ stop_reason == "tool_use"
    │        ▼
    │   dispatch_tools()
    │        │
    │        └─► run_bash(command)
    │                 │
    │                 └─► shell output back to LLM
    │
    └─► stop_reason == "end_turn"  →  print Final Answer
```

The loop runs until the model produces a plain-text response (no more tool calls), which is printed as the **Final Answer**.

---

## Safety

Commands are checked against a blocklist before execution:

- `rm -rf /` — filesystem wipe
- `sudo` — privilege escalation
- `shutdown` / `reboot` — system control
- `> /dev/` — raw device writes
- `:(){ :|:& };:` — fork bomb

---

## License

MIT — see [LICENSE](LICENSE).
