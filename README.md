# CL-AI

CL-AI is a conversational AI-powered terminal assistant
focused on DevOps, SRE, and future MLOps.

## Features and Roadmap

- v0.1 - Command Vault, Online Help, Terminal Awareness
- v0.2 - Smart Runbook Generator and Error Log Tracking
- v0.3 - Terraform Plan Explainer and Deployment History
- v0.4 - Interactive Troubleshooting Agent
- v1.0 - Stable Integrated Release

## Technology Stack

- Python
- Qwen Cloud API
- LangChain
- SQLite
- Typer
- Rich
- Prompt Toolkit
- Pytest

## Documentation

See [CL-AI Development Plan](docs/CL-AI-PLAN.md).

## Project Status

The v0.1 CLI, Qwen provider foundation, SQLite Command Vault, structured AI
command documentation, and opt-in Git Bash command awareness are implemented.
Natural-language search and online help are not implemented yet.

## Development Quick Start

From Git Bash on Windows:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
```

If you do not already have a local `.env`, copy `.env.example` to `.env` and
fill in your own Qwen provider values. Never commit or share `.env`.

```bash
cl-ai --version
cl-ai
```

## Command Vault

The v0.1 Vault stores its SQLite database under `~/.cl-ai/cl_ai.db` unless
`CLAI_DATA_DIR` is configured. By default, `save` sends the secret-checked
command text to Qwen for structured documentation, then shows the complete
result for Save, Edit, or Cancel review.

```bash
cl-ai save "docker compose ps"
cl-ai list
cl-ai show 1
cl-ai edit 1
cl-ai delete 1
```

Generated documentation includes a title, category, subcategory, simple
description, command-part breakdown, tags, risk level, risk notes, Qwen model
ID, and provenance. Use local-only mode when you do not want to call Qwen:

```bash
cl-ai save "docker compose ps" --no-ai
```

Saving never executes a command and does not mean it worked. CL-AI checks for
obvious embedded credentials before any Qwen request, applies deterministic
risk checks, identifies exact duplicates, validates the model's JSON response,
and asks for confirmation before writing. Delete currently has no undo, so
export and backup support will be added during a later milestone.

## Git Bash Command Awareness

Enable the wrapper for the current Git Bash session:

```bash
source <(cl-ai shell-init)
```

Then run a normal command and explicitly ask CL-AI to capture it:

```bash
docker compose ps
cl-ai save-last
```

The longer phrase is also supported:

```bash
terraform plan
cl-ai save the command
```

To enable it in future Git Bash sessions, add this line manually to `~/.bashrc`:

```bash
source <(cl-ai shell-init)
```

The wrapper checks up to 20 recent history entries, skips CL-AI commands, and
sends the selected command to Python through standard input. It does not run
the command again. CL-AI shows a preview before saving. If Bash history is not
available, `cl-ai save-last` asks you to paste the command instead. Use
`--no-ai` when you want the entire save to stay local:

```bash
cl-ai save-last --no-ai
```

Run the local tests without making cloud requests:

```bash
python -m pytest
```

## Security

CL-AI is designed to protect API credentials,
redact sensitive logs, and require permission
before running diagnostic commands.
