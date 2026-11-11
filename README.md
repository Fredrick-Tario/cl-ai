# CL-AI

CL-AI is a conversational, terminal-first AI assistant focused on DevOps, SRE,
and future MLOps.

## Project Status

CL-AI v0.1 is implemented: conversational chat, SQLite Command Vault,
structured AI command documentation, opt-in Git Bash command awareness,
natural-language Vault retrieval, and official online documentation research.

Later roadmap items are not implemented: v0.2 runbooks/error tracking, v0.3
Terraform plan/deployment history, v0.4 troubleshooting agent, and v1.0 release
hardening. CL-AI does not autonomously execute shell or infrastructure commands.

See the approved [CL-AI Development Plan](docs/CL-AI-PLAN.md) for the roadmap and
security boundaries.

## Technology

- Python 3.11+
- Configurable OpenAI-compatible endpoint (Qwen, NVIDIA NIM, or personal API)
- LangChain
- SQLite with FTS5
- Typer, Rich, and Prompt Toolkit
- Pydantic and Pytest

## Installation

From Git Bash on Windows:

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -e ".[dev]"
cl-ai --version
```

If you do not already have a local `.env`, copy `.env.example` to `.env` and
fill in your own provider values. Never overwrite an existing `.env`, and never
commit or share it.

Existing Qwen configuration remains supported:

```dotenv
AI_PROVIDER=qwen
QWEN_API_KEY=your-private-value
QWEN_BASE_URL=https://your-provider.example/v1
QWEN_MODEL=your-model-id
```

For NVIDIA NIM or another OpenAI-compatible personal endpoint, use the generic
settings. Confirm the endpoint, available model, quota, and pricing in your own
provider account; CL-AI does not assume any model API is free.

```dotenv
AI_PROVIDER=nvidia_nim
AI_API_KEY=your-private-value
AI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MODEL=your-compatible-model-id
```

Use `AI_PROVIDER=openai_compatible` and optionally `AI_PROVIDER_NAME` for a
different compatible endpoint. API keys are masked by configuration objects and
are never printed intentionally.

## Conversational Chat

Run `cl-ai` with no subcommand. The banner displays the configured provider.
If you type a terminal command such as `cl-ai list` inside chat, CL-AI tells you
to exit and run it in Git Bash; that text is not sent to the model. Chat does
not provide an unrestricted shell or execute model suggestions.

## Command Vault

The Vault database is stored under `~/.cl-ai/cl_ai.db` unless `CLAI_DATA_DIR`
is configured. Saving never executes a command or proves it worked.

```bash
cl-ai save "docker compose ps"
cl-ai save "docker compose ps" --no-ai
cl-ai list
cl-ai show 1
cl-ai edit 1
cl-ai delete 1
```

By default, `save` sends secret-checked command text to the configured AI
provider for structured documentation and shows a Save/Edit/Cancel review.
Documentation includes a title, category, description, command breakdown, tags,
risk level, model ID, and provenance. `--no-ai` keeps the save local.

CL-AI rejects obvious embedded credentials, performs deterministic risk checks,
recognizes exact duplicates, validates model JSON, and asks before writing.
Delete has no undo in v0.1; backup/import/export is future work.

## Find Saved Commands

`find` searches only real SQLite records across command text, titles,
descriptions, and tags. It never invents a replacement when there is no match.

```bash
cl-ai find "What did I use to inspect Terraform plans?"
cl-ai find "Compose service status" --category Docker
cl-ai list --category Terraform
```

Matches show the exact command, purpose, saved directory, command source,
documentation URLs when present, and verification state.

## Online Documentation Help

`helpme` performs a real online search, accepts only supported official
documentation domains, fetches the pages, and asks the configured model to
summarize that retrieved evidence. It uses free public DuckDuckGo HTML search
with a Bing HTML fallback; no paid search service or search API key is required.
Public search markup can change, so failures are reported rather than hidden.
Network access and the configured model endpoint are required.

```bash
cl-ai helpme "What does terraform import do?"
cl-ai helpme "How do I inspect Docker Compose service logs?"
cl-ai -helpme "What does git restore do?"
```

Output distinguishes documented examples from AI-adapted suggestions, includes
risk warnings, and prints retrieved source URLs. Suggested commands are never
executed. To review and save a numbered suggestion with its source URL:

```bash
cl-ai helpme "What does terraform import do?" --save 1
```

If search fails, no supported official source is found, the model API fails, or
the model cites a source that was not retrieved, CL-AI reports the failure and
does not accept or save the proposed output.

## Git Bash Command Awareness

Enable the opt-in wrapper for the current session:

```bash
source <(cl-ai shell-init)
```

Then explicitly capture the previous non-CL-AI history entry:

```bash
docker compose ps
cl-ai save-last

terraform plan
cl-ai save the command
```

The wrapper checks up to 20 history entries, sends command text through standard
input, and never reruns it. If history is unavailable, CL-AI asks for a manual
paste. Add `source <(cl-ai shell-init)` to `~/.bashrc` manually if desired.

## Tests

Automated tests mock model and online-retrieval behavior; they make no billable
cloud requests:

```bash
python -m pytest
```

## Security and Limitations

CL-AI uses environment variables for credentials, parameterized SQLite queries,
bounded inputs, literal-secret detection, and risk warnings. Online pages are
untrusted evidence, not permission to execute anything. A saved or researched
command remains unverified until separate evidence says otherwise.

v0.1 does not capture logs, generate runbooks, parse Terraform plans, track
deployments, run diagnostics, or modify infrastructure. Those capabilities are
reserved for approved later milestones.
