# claude-code-from-scratch

> Exploring how Claude works under the hood — rebuilding its coding-agent behaviour from scratch using the Anthropic API: prompt pipelines, context windows, and tool-driven interactions.

---

## What's inside

| File | Purpose |
|------|---------|
| `core.py` | Shared primitives: Anthropic client/config, safety checks, tool schemas, tool handlers, dispatch maps, and the reusable `stream_loop()`. |
| `perception_action_loop.py` | **Episode 01** — the simplest agent loop (LLM → `bash` → repeat) with a small REPL. |
| `tool_use.py` | **Episode 02** — scalable multi-tool agent via a dispatch map (bash + basic file tools) using `stream_loop()`. |
| `pyproject.toml` / `uv.lock` | Dependencies and reproducible installs via `uv`. |

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
# then edit .env and fill in ANTHROPIC_API_KEY (MODEL_ID is optional)

# 4. Run Episode 01
uv run s01

# 5. Run Episode 02
uv run s02

# (Optional) Run the "latest" episode
uv run agent
```

---

## Quickstart (classic — pip)

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .

cp .env.example .env            # fill in your keys
python perception_action_loop.py
# or: python tool_use.py
```

---

## Environment variables

Create a `.env` file (or export the vars) before running:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...   # Required — get yours at console.anthropic.com
MODEL_ID=claude-sonnet-4-6     # Optional — defaults to this if unset
ANTHROPIC_BASE_URL=...         # Optional — for proxies / gateways
```

---

## Project structure

```
claude-code-from-scratch/
├── core.py                   # Shared primitives (tools, dispatch, stream loop)
├── perception_action_loop.py # Episode 01
├── tool_use.py               # Episode 02
├── pyproject.toml            # Project config (PEP 621)
├── uv.lock                   # Locked dependencies (uv)
├── .env                      # Your secrets (git-ignored)
├── .env.example              # Template — safe to commit
├── .python-version           # Pins Python version for uv
├── .venv/                    # Created by uv sync (git-ignored)
└── README.md
```

---

## How the agent works

```
User input
    │
    ▼
Episode 01: agent_loop()
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
