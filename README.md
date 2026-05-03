# claude-code-from-scratch

> Exploring how Claude works under the hood — rebuilding its coding-agent behaviour from scratch using the Anthropic API: prompt pipelines, context windows, and tool-driven interactions.

---

## What's inside

| File | Purpose |
|------|---------|
| `core.py` | Shared primitives: Anthropic client/config, safety checks, tool schemas, tool handlers, dispatch maps, and the reusable `stream_loop()`. |
| `e01_perception_action_loop.py` | **Episode 01** — the simplest agent loop (LLM → `bash` → repeat) with a small REPL. |
| `e02_tool_use.py` | **Episode 02** — scalable multi-tool agent via a dispatch map (bash + basic file tools) using `stream_loop()`. |
| `e03_todo_write.py` | **Episode 03** — planning + progress tracking via `todo_write`/`todo_read`/`todo_update` persisted to `.agent_todo.json`. |
| `e04_sub_agent.py` | **Episode 04** — delegate subtasks to isolated subagents via `spawn_subagent` (fresh context). |
| `e05_skill_loading.py` | **Episode 05** — discover + lazily load `skills/*/SKILL.md` via `list_skills` and `load_skill`. |
| `e06_context_compact.py` | **Episode 06** — compress history + persist long-term context to `.agent_memory.md`. |
| `e07_task_system.py` | **Episode 07** — persistent dependency-aware tasks stored in `.agent_tasks.json`. |
| `e08_background_tasks.py` | **Episode 08** — run slow shell commands in the background with notifications. |
| `e09_agents_team.py` | **Episode 09** — persistent teammates with filesystem mailboxes (`.mailboxes/`). |
| `e10_team_protocols.py` | **Episode 10** — FSM-governed teammate protocol to avoid deadlocks/talking over. |
| `e11_autonomous_agents.py` | **Episode 11** — agents self-organize by atomically claiming tasks from the shared board (`.agent_tasks.json`). |
| `e12_worktree_task_isolation.py` | **Episode 12** — isolate tasks in per-branch git worktrees to avoid interference. |
| `e13_streaming.py` | **Episode 13** — explicit real-time token streaming (TTFT improvements). |
| `e14_tools_extended.py` | **Episode 14** — safety-first tool arsenal (read/write/grep/glob/revert) with snapshots. |
| `e15_permissions.py` | **Episode 15** — YAML-driven permission governance (`config/permissions.yaml`). |
| `skills/` | Skill library (markdown SOPs) loaded on-demand in Episode 05. |
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
uv run e01

# 5. Run Episode 02
uv run e02

# 6. Run Episode 03
uv run e03

# 7. Run Episode 04
uv run e04

# 8. Run Episode 05
uv run e05

# 9. Run Episode 06
uv run e06

# 10. Run Episode 07
uv run e07

# 11. Run Episode 08
uv run e08

# 12. Run Episode 09
uv run e09

# 13. Run Episode 10
uv run e10

# 14. Run Episode 11
uv run e11

# 15. Run Episode 12
uv run e12

# 16. Run Episode 13
uv run e13

# 17. Run Episode 14
uv run e14

# 18. Run Episode 15
uv run e15

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
python e01_perception_action_loop.py
# or: python e02_tool_use.py
# or: python e03_todo_write.py
# or: python e04_sub_agent.py
# or: python e05_skill_loading.py
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
├── e01_perception_action_loop.py # Episode 01
├── e02_tool_use.py               # Episode 02
├── e03_todo_write.py             # Episode 03
├── e04_sub_agent.py              # Episode 04
├── e05_skill_loading.py          # Episode 05
├── e06_context_compact.py        # Episode 06
├── e07_task_system.py            # Episode 07
├── e08_background_tasks.py       # Episode 08
├── skills/                   # Skill library (SKILL.md files)
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
