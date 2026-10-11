
# CL-AI — Codex Development Instructions

## Project Overview
CL-AI is a conversational, terminal-first AI assistant
focused on DevOps, SRE, and future MLOps.

## Source of Truth
Before planning or implementing features, read:
`docs/CL-AI-PLAN.md`

Use this document as the primary reference for:
- Project objectives
- Version roadmap
- Technical architecture
- Feature requirements
- Manual versus automatic behavior
- Security requirements
- Acceptance criteria

## Development Roadmap
- v0.1 — Command Vault, Online Help, Terminal Awareness
- v0.2 — Smart Runbooks, Error Logs, Troubleshooting History
- v0.3 — Terraform Plan Explainer and Deployment History
- v0.4 — Interactive Troubleshooting Agent
- v1.0 — Stable Integrated Release

## Technology Stack
- Python
- Qwen Cloud API as the primary CL-AI model provider
- LangChain
- SQLite
- Typer
- Rich
- Prompt Toolkit
- Pydantic
- Pytest

## Development Guidelines
- Build one milestone at a time.
- Prioritize v0.1 before future features.
- Keep CL-AI terminal-only.
- Use a modular and maintainable Python architecture.
- Explain important architectural decisions.
- Provide beginner-friendly explanations.
- Write tests for implemented functionality.
- Do not add unnecessary features.

## Security
- Never commit API keys or credentials.
- Use environment variables for secrets.
- Never send unfiltered sensitive logs to cloud APIs.
- Do not automatically execute destructive commands.
- Require explicit approval before changing infrastructure.

## Collaboration
- Explain the proposed approach before major changes.
- Identify files that will be created or modified.
- Keep changes small and testable.
- Report tests performed and any remaining limitations.
- Do not implement future versions without approval.
