# CL-AI: Master Development Plan and Technical Specifications

**Document status:** Approved scope / implementation planning  
**Revision:** Qwen Cloud API architecture update  
**Date:** October 11, 2026  
**Project:** CL-AI (Command Line AI)  
**Primary use case:** FailSafe E-Commerce DevOps/SRE learning and operations  
**Primary platform:** Windows + Git Bash, including the VS Code integrated terminal  
**Application type:** Terminal-first conversational CLI (no website, desktop GUI, or VS Code extension)

---

## 1. Project Summary

CL-AI is a personal, conversational, AI-assisted DevOps/SRE terminal tool. It helps the user discover commands, remember useful commands, document errors and failed fixes, understand Terraform changes, and eventually investigate problems using authorized tools and historical evidence.

**Core goal:** Build a reliable engineering memory and troubleshooting companion, not just a chatbot that invents shell commands.

### 1.1 Confirmed design decisions

- **Primary AI backend:** The user's authorized **Qwen Cloud API** account. Exact endpoint, model ID, rate limits, and pricing must be confirmed from the user's API provider account before implementation.
- **AI portability:** The code remains provider-independent so a different API can be configured without rewriting feature modules.
- **Optional future local AI:** Ollama with a suitable Qwen/open-weight model. The RTX 3050 Laptop GPU (4 GB dedicated VRAM) and 24 GB RAM are adequate for experimenting with some small quantized models, but local inference is **not required** for the first release.
- **Where data lives:** SQLite and log/runbook files on the user's computer by default.
- **Where CL-AI runs:** Existing Git Bash terminal, either as a one-shot command or a conversational session.
- **Web search:** `-helpme` uses an actual online search/documentation retrieval service. The Qwen API alone must **not** be assumed to provide live web search.
- **Command safety:** AI-generated commands are suggestions, not automatically executed actions. Explicitly requested command capture or approved diagnostics have separate safeguards.
- **Future ML:** Troubleshooting records are structured to support retrieval, evaluation, recommendation ranking, and later model-training experiments. Saving records does **not** automatically retrain Qwen.

### 1.2 Version roadmap

| Version | Feature set | Primary result |
|---|---|---|
| **v0.1** | Command Vault + Online `-helpme` + Git Bash Command Awareness | Discover, explain, save, and retrieve commands. |
| **v0.2** | Smart Runbook Generator + Error Log and Troubleshooting Tracker | Save real error evidence, every meaningful attempt, failed fixes, confirmed resolutions, and recurring-error history. |
| **v0.3** | Terraform Plan Explainer + Verified Apply History | Explain planned infrastructure changes and compare them with credible deployment records. |
| **v0.4** | Interactive Troubleshooting Agent | Investigate issues with approved tools and the knowledge accumulated in v0.1-v0.3. |
| **v1.0** | Stable Integrated Release | Harden, test, document, package, and release one usable CLI. |
| **Future** | AIOps/MLOps experiments | Use sanitized troubleshooting datasets for evaluation, ranking, and possibly fine-tuning. |

**Scope rule:** Do not add a web application, VS Code sidebar extension, always-on monitoring service, or autonomous infrastructure modification as part of these versions.

---

## 2. How the User Interacts with CL-AI

### 2.1 One-shot mode: continue working in ordinary Git Bash

```bash
terraform -chdir=terraform/environments/dev show tfplan
cl-ai save the command

cl-ai save-last
cl-ai find "the command for viewing my Terraform plan"
cl-ai -helpme "How do I create an Azure Linux VM with Terraform?"
```

The `cl-ai save the command` phrase is a proposed custom shortcut, not a built-in Bash feature. It requires an opt-in Bash wrapper/function that can retrieve the previous shell command reliably enough to show a preview.

### 2.2 Conversational mode: chat within the terminal

```text
$ cl-ai

CL-AI v0.1
Project: failsafe-ecommerce
Provider: Qwen Cloud

You: I forgot how to inspect my Docker Compose services.
CL-AI: I found a saved command: docker compose ps
       It shows the status of the services in your Compose project.

You: Can you save another command?
CL-AI: Yes. Paste it, or ask me to retrieve the previous Git Bash command.

You: exit
$
```

### 2.3 Three sources of information must be labeled

| Source label | Meaning | Example |
|---|---|---|
| **Saved** | Retrieved from the user's SQLite Vault or incident history. | A command saved last week. |
| **Online documentation** | Retrieved from a real current documentation page, with URL. | Terraform Registry example. |
| **AI-generated / inferred** | Produced by Qwen from supplied context; requires verification. | A proposed troubleshooting explanation. |

**Never label an AI-generated guess as a verified command, successful fix, deployment, or observed error.**

### 2.4 Core manual-versus-automatic principle

The user supplies intent, confirms important outcomes, and grants diagnostic permissions. Python handles data capture, timestamps, storage, parsing, counting, search, and safeguards. Qwen explains, categorizes, summarizes, and proposes solutions based on supplied evidence.

---

## 3. Technical Architecture

### 3.1 System overview

```text
Git Bash / VS Code Integrated Terminal
                 |
      +----------+----------+
      |                     |
  One-shot CLI          Chat Mode
      |                     |
      +----------+----------+
                 |
          CL-AI Python Core
                 |
     Intent Router / Session State
                 |
      +----------+------------------+-----------------+
      |          |                  |                 |
 v0.1 Vault   v0.1 -helpme     v0.2 Runbooks     v0.3 Terraform
      |          |                  |                 |
 SQLite FTS5  Web Retrieval    Logs + Incidents   Plan JSON Parser
      |          |                  |                 |
      +----------+------------------+-----------------+
                 |
       v0.4 Troubleshooting Agent
                 |
     Restricted, approved diagnostic tools
                 |
       Shared services and safeguards
           - AI model adapter
           - Qwen Cloud (primary)
           - Ollama (optional later)
           - SQLite and local files
           - Secret redaction
           - Structured validation
           - Audit/provenance records
```

### 3.2 Technology decisions

| Layer | Recommended technology | Purpose |
|---|---|---|
| CLI commands | Python 3.11+ and Typer | Define launch, save, find, incident, and other commands. |
| Conversational terminal | Prompt Toolkit | Text interaction and history inside CL-AI. |
| Terminal output | Rich | Explanations, tables, warnings, readable formatting. |
| Primary model | Qwen Cloud API | Generate language-based outputs and reason over retrieved evidence. |
| AI abstraction | Provider adapter with LangChain where helpful | Keep Qwen specifics separate from core modules. |
| Structured responses | Pydantic | Validate titles, labels, suggested commands, risk explanations, and runbook sections. |
| Data | SQLite and FTS5 | Persist commands/incidents and search them. |
| Raw-ish log artifacts | Redacted local files | Preserve relevant captured stdout/stderr and traces. |
| Online help | Real search/document retrieval client | Search official online references and return source URLs. |
| Shell awareness | Opt-in Git Bash function/hook | Retrieve recent command text from the invoking Bash session. |
| Terraform analysis | Terraform `show -json` plus Python parser | Read planned changes deterministically. |
| Testing | Pytest, mocks, fixtures | Validate behavior without using billable cloud resources. |

### 3.3 Qwen Cloud configuration

Do **not** hardcode the Qwen model name or API endpoint until those details are verified from the user's particular API account. Some Qwen providers expose OpenAI-compatible APIs; others may differ. Use a configurable adapter.

Illustrative `.env` configuration (placeholders only):

```dotenv
AI_PROVIDER=qwen
QWEN_API_KEY=replace_with_your_private_key
QWEN_BASE_URL=replace_with_your_provider_endpoint
QWEN_MODEL=replace_with_your_available_model_id

WEB_SEARCH_PROVIDER=replace_with_chosen_provider
WEB_SEARCH_API_KEY=optional_if_provider_requires_it

CLAI_DATA_DIR=~/.cl-ai
CLAI_LOG_CAPTURE=off
CLAI_CLOUD_LOG_SHARING=off
CLAI_MAX_AI_REQUESTS_PER_SESSION=30
```

The specific variable names are part of the proposed CL-AI configuration, not an assertion about a Qwen SDK's required names. Load them into the matching adapter after checking your provider's documentation.

**Security:** Never commit `.env`, API tokens, Terraform plan files, state snapshots, or locally captured error logs. The example `.env` must be documented as a template; commit only `.env.example` with empty placeholder values.

### 3.4 How Qwen Cloud is used by each version

| Version | Qwen handles | Python/local services handle |
|---|---|---|
| v0.1 | Titles, command explanations, categorization, natural-language intent, researched-command summaries. | Command capture, web retrieval, Vault storage, provenance, retrieval indexes, validation. |
| v0.2 | Error explanations, incident summaries, pattern descriptions, runbook drafting. | Log capture, event/incident counts, deduplication, attempt timelines, solution evidence. |
| v0.3 | Plain-English change reports and risk explanations. | Terraform JSON parsing, action counts, deployment proof, history comparisons, secret filtering. |
| v0.4 | Diagnostic planning and synthesis of evidence. | Permission checks, tool allowlists, bounded execution, access controls, audit logs. |

**If Qwen Cloud is unavailable:** Existing local Vault searches, stored runbooks, incident history, and deterministic Terraform summaries should still work where feasible; new AI explanations may be unavailable until connectivity returns.

---

## 4. v0.1: Command Vault + Online Help + Terminal Awareness

### 4.1 Objective

A daily-use terminal assistant that can save a command with AI-generated documentation, recover the previous Git Bash command, search saved commands in natural language, and research unfamiliar commands online.

### 4.2 Module A: Command Vault

**Feature requirements**

- [ ] Accept pasted commands and commands retrieved from the invoking Git Bash session.
- [ ] Generate a meaningful title automatically.
- [ ] Generate technology category and subcategory (Terraform/Planning, Docker/Logs, Git/History, etc.).
- [ ] Generate a short explanation in simple English.
- [ ] Explain important subcommands, flags, arguments, paths, and placeholders.
- [ ] Generate relevant search tags.
- [ ] Assess possible risks, including deletion, resource changes, exposed secrets, and cloud charges.
- [ ] Record project, working directory, shell, and Git context when actually available.
- [ ] Distinguish whether the command was pasted, captured, or researched.
- [ ] Detect obvious duplicates; let the user keep or merge intentional variants.
- [ ] Show a full preview and allow Save, Edit, or Cancel.
- [ ] Persist approved entries to SQLite across sessions.
- [ ] Provide natural-language search, category filters, and edit/delete features.
- [ ] Record `saved`, `user-reported worked`, and `execution-verified` as distinct states.

**Proposed command entry fields**

| Field | Generated / captured by |
|---|---|
| Command ID, created/updated timestamps | SQLite/Python |
| Exact command text | User input or shell integration |
| Title, category, subcategory, description, flag breakdown, tags | Qwen, validated by Pydantic |
| Risk notes | Deterministic checks plus AI explanation |
| Project/directory/shell/Git branch/commit | Local context, if available |
| Source and documentation URLs | Import/research metadata |
| Execution and verification state | Explicit evidence or user confirmation |

**Example**

```text
$ terraform -chdir=terraform/environments/dev plan -out=tfplan
$ cl-ai save the command

CL-AI: Previous command found.

Title: Generate Development Terraform Plan
Category: Terraform / Planning
Explanation: Preview the changes in your dev Terraform directory and
             save the execution plan to a local file called tfplan.
Breakdown:
  -chdir=...  Use the specified Terraform working directory.
  plan        Preview proposed changes.
  -out=tfplan Save the resulting plan file.
Risk: Does not apply cloud changes; the saved plan can contain secrets.
Project: failsafe-ecommerce (detected locally)

Save? [Y] Save / [E] Edit / [N] Cancel
```

**Manual input:** Provide/paste the command, or explicitly ask CL-AI to retrieve the last Git Bash command. Review/edit the generated entry and confirm saving. If a previous command did not work, report that separately rather than allowing CL-AI to assume success.

**Automatic behavior:** Generate documentation, tags, and category; collect permitted context; detect duplicates; write approved records to SQLite.

### 4.3 Module B: Git Bash Command Awareness

The user specifically wants this workflow in their ordinary terminal:

```bash
terraform -chdir=terraform/environments/dev show tfplan
cl-ai save the command
```

**Technical plan**

1. Install an optional `cl-ai` Bash wrapper/function in the user's Git Bash startup configuration.
2. When the user calls `cl-ai save the command` or `cl-ai save-last`, the wrapper retrieves the previous relevant command from the **current** shell's history or maintained shell metadata.
3. Exclude the CL-AI invocation itself and clearly display the candidate before saving.
4. Pass captured text to Python via a safer channel such as standard input, not by constructing `eval` or executing captured text.
5. Send the sanitized candidate through the Command Vault documentation flow.
6. Provide a manual-paste fallback when history is disabled, unavailable, altered by shell settings, or ambiguous.

**Limitations and safeguards**

- Normal Python child processes cannot directly read another Bash session's live in-memory history.
- Git Bash history settings and multiline commands may affect what can be retrieved; test with real session fixtures.
- Shell history alone cannot prove exit status or capture what the command printed.
- Do not continuously record every command in v0.1.
- Never save credentials embedded in command arguments without redaction or explicit rejection.
- Never execute the retrieved command just to save it.

### 4.4 Module C: Command Vault retrieval

**Examples**

```bash
cl-ai find "What did I use to inspect Terraform plans?"
cl-ai find "Find my Docker logs command"
cl-ai list
cl-ai list --category terraform
```

Start with SQLite FTS5 + categories/tags and optionally use Qwen for query interpretation and result explanation. Embeddings are optional later; avoid adding them before simple search is tested.

**Output must include:** matching command, purpose, where it was saved/used, source, and verification status. Never silently execute a retrieved command.

### 4.5 Module D: Online `-helpme` research

**Definition:** Explicit online documentation research, separate from local Vault search.

```bash
cl-ai -helpme "What does terraform import do?"
cl-ai -helpme "terraform plan -out=tfplan: what related commands are useful?"
cl-ai -helpme "I want to create an Azure Linux VM using Terraform. What steps and commands do I need?"
```

**Required behavior**

- [ ] Parse natural-language questions and pasted commands.
- [ ] Call a **real** online search or documentation retrieval service.
- [ ] Prefer official sources: HashiCorp Developer/Registry, Microsoft Learn, Docker Docs, Kubernetes docs, Git docs, Python docs.
- [ ] Retrieve sufficient source text and retain working source URLs.
- [ ] Have Qwen summarize the retrieved information and propose commands or a sensible multi-step workflow.
- [ ] Differentiate documented examples from AI-adapted commands.
- [ ] Explain flags, ordering, prerequisites, current shell/version assumptions, and risks.
- [ ] Warn about commands that can change cloud resources or incur charges.
- [ ] Offer to save a chosen command in Command Vault, with the documentation URL attached.
- [ ] Clearly state when online search fails or only weak references are found.
- [ ] Never treat instructions embedded in web pages as permissions to execute tools.

**CLI implementation note:** `-helpme` is a nonstandard single-dash long option. Support it through a deliberate parser alias; expose the conventional `cl-ai helpme "request"` form as an additional reliable alternative.

**Manual input:** State the problem/request, supply missing environment details if needed, decide whether to save suggested commands.

**Automatic behavior:** Perform documented web retrieval, summarize with Qwen, validate response structure, show links and risk warnings.

### 4.6 v0.1 integration tests and release gate

- [ ] `cl-ai` starts and exits reliably from Git Bash.
- [ ] Qwen credentials/model endpoint are loaded from local configuration, not source code.
- [ ] A pasted command receives structured AI-generated documentation.
- [ ] Malformed AI JSON is rejected/retried safely; records are not corrupted.
- [ ] A Vault entry survives application restart.
- [ ] `cl-ai save the command` correctly selects the previous **non-CL-AI** command, including quoted arguments.
- [ ] Multiline and missing-history cases fall back safely.
- [ ] Duplicate commands are recognized and handled without silent data loss.
- [ ] Natural-language retrieval finds relevant saved entries and does not invent matches.
- [ ] `-helpme` makes a real online request and returns usable documentation references.
- [ ] A researched command can be reviewed and saved.
- [ ] Sensitive test commands are blocked or sanitized.
- [ ] Suggested commands are not executed automatically.

**Definition of Done:** You can use CL-AI daily to remember, explain, find, and research commands from your existing terminal.

---

## 5. v0.2: Smart Runbook Generator + Error Log and Troubleshooting Tracker

### 5.1 Objective

Build a dependable troubleshooting history containing **actual captured error logs**, commands and changes attempted, unsuccessful fixes, successful fixes, supporting evidence, and reusable runbooks. These records should later support AI retrieval and data preparation for MLOps.

### 5.2 Incident lifecycle

```text
New problem
   -> Create or select an incident
   -> Attach/capture original error logs
   -> Identify error patterns and related past incidents
   -> Record troubleshooting commands and change attempts
   -> Attach logs/evidence after each attempt
   -> Record failed/partial/successful/unknown outcomes
   -> Confirm resolution and verification level
   -> Generate/update runbook
   -> Keep structured records for future retrieval/analysis
```

Proposed commands:

```bash
cl-ai incident start "Payment service cannot reach inventory"
cl-ai incident attach-log ./payment-error.log
cl-ai incident show INC-0042
cl-ai incident attempts INC-0042
cl-ai incident resolve INC-0042
cl-ai run -- docker compose ps
```

The exact CLI syntax can be refined during implementation; it is not currently installed.

### 5.3 Capture actual error logs, not just AI summaries

**Required metadata per log artifact**

- Incident ID, optional attempt ID, log artifact ID.
- Original capture time (if available) and ingestion time.
- Producing command, process/service, source and project/environment.
- Captured stdout and stderr as separate streams when feasible.
- Exit code when execution was observed.
- Sanitized log text that preserves ordering, stack traces, and error context.
- Content hash, source identifier, redaction/truncation flags, size, and retention rules.

**Supported collection modes**

| Mode | User action | What gets collected |
|---|---|---|
| Manual paste | Paste an error or trace in CL-AI. | User-submitted content and metadata. |
| File import | `cl-ai incident attach-log ./error.log` | Sanitized file content and source/reference. |
| Explicit tracked command | `cl-ai run -- <user-supplied command>` | Approved execution plus captured stdout/stderr/exit code. |
| Future shell capture | Enable supported opt-in shell hooks. | Only the explicitly selected metadata/output classes. |

**Execution boundary:** `cl-ai run --` intentionally executes the user's supplied command as a tracking wrapper. It is not a permission for the model to choose arbitrary commands. Make risks clear, refuse automatic unsafe operations, and obtain explicit approval for commands with side effects. For initial v0.2, prioritize allowlisted diagnostic commands.

**Limitation:** CL-AI cannot recover output printed earlier in an ordinary terminal unless it was captured or the user provides a file/paste. Last-command text from v0.1 does not automatically include stdout/stderr.

### 5.4 Mandatory error deduplication and counting rule

> **Repeated error log lines must not be counted as separate incidents.**

CL-AI tracks three different levels:

| Level | Definition | Example |
|---|---|---|
| **Error event** | An observed occurrence in log output. One event may span multiple lines (for example, a traceback). | Twenty connection-refused events during one startup. |
| **Error pattern** | A recognizable type/signature used to compare events or incidents. | Payment connection refused to a particular service. |
| **Incident** | A distinct troubleshooting episode or problem being investigated. | One payment-service outage. |

**Example:** If the payment service prints the same error 20 times during one outage, record **20 error events, 1 matching error pattern, and 1 incident**. If that problem happens on three separate days and is tracked as three separate outages, there are **3 incidents** connected to the same pattern (with however many underlying events were captured).

**Implementation rules**

1. Create a stable incident ID for each distinct troubleshooting episode.
2. Parse logged events; do not assume one line equals one event. Group multiline stack traces appropriately.
3. Derive normalized error fingerprints from source, error type, message, and meaningful context, excluding volatile timestamps where appropriate.
4. Associate matching events with an existing open incident when they belong to the same ongoing failure.
5. Maintain separate counters for events, patterns, and incidents.
6. Detect reimports using a log-file content hash plus source/capture information. Do not double count duplicated imports.
7. Reopening a saved runbook or reanalyzing a log must not create new incidents.
8. Create a new incident only for a genuinely new troubleshooting episode; do not infer one from every repeated line.
9. Permit the user to split/merge incident groupings and record that correction.
10. Preserve event-to-incident relationships so future analysis can distinguish noisy logs from repeated outages.

### 5.5 Troubleshooting attempt and recommendation tracking

For each attempt, preserve:

| Field | Description |
|---|---|
| Attempt ID / Incident ID | Stable linkage. |
| Attempt time and sequence | Where the step occurs in the incident timeline. |
| Proposed change / command | Exact or sanitized operation attempted. |
| Source | User idea, Qwen suggestion, online docs, saved runbook, teammate, etc. |
| Rationale | Why this action was considered relevant. |
| Before evidence | Log/diagnostic references before the attempt. |
| After evidence | Log/diagnostic references after the attempt. |
| Execution outcome | Command succeeded, failed, or not observed. |
| Troubleshooting outcome | Fixed issue, failed to fix, partially helped, or unknown. |
| Verification status | Self-reported, user-confirmed, or supported by collected tests/logs. |
| Notes | Side effects, context, follow-up action. |

**Keep failed attempts.** They are useful evidence about what did *not* work under that environment and should influence future recommendations without becoming absolute rules.

**Example conversation**

```text
You: Track this error: payment connection refused.
CL-AI: Created INC-0042. You can attach logs or use tracked diagnostics.

You: I changed the external URL to port 8005. It still failed.
CL-AI: Attempt 1 saved. Outcome: not resolved (user report).

You: I corrected the internal service port and checkout passes now.
CL-AI: Attempt 2 saved. Reported outcome: successful.
       Do you want to attach a passing test/log and confirm resolution?

You: Yes.
CL-AI: Resolution recorded, linked to evidence, and ready for a runbook.
```

### 5.6 Smart Runbook Generator

Generate a Markdown runbook from the incident evidence, not from guesses. Recommended sections:

1. Problem title and affected technology/service.
2. Environment and symptoms.
3. Original error log references and relevant excerpts.
4. Error-event counts and related historical incidents (clearly distinguished).
5. Investigation timeline.
6. Commands tried and their execution results.
7. Failed/partial attempts, with context.
8. Confirmed working fix and verification evidence.
9. Root cause, only if supported; otherwise mark **unconfirmed**.
10. Preventive checks and related Vault commands.
11. Sources, incident ID, dates, and last update.

Runbooks should live locally by default; optionally export a reviewed/sanitized copy to the FailSafe repository's `docs/runbooks/` folder. Never commit private logs or API credentials accidentally.

### 5.7 Retrieval and learning behavior in v0.2

When a new log resembles historical incidents, CL-AI can retrieve:

- Frequency across **distinct incidents** and within-event counts.
- Relevant previously attempted fixes and their observed outcomes.
- Verified resolutions in comparable environments.
- Related saved commands from v0.1.
- Log excerpts that actually support the recommendation.

**This is retrieval-based improvement, not automatic model training.** A solution that worked once is a clue, not a universal rule.

### 5.8 Manual input vs. automatic behavior in v0.2

| Manual user action | Automatic CL-AI behavior |
|---|---|
| Start/select a case; describe issue if needed. | Create incident ID, time, context. |
| Paste logs, attach files, or opt in to tracked diagnostics. | Store redacted logs, link artifacts, parse events. |
| Explain changes made outside CL-AI. | Record them as timeline attempts. |
| Report whether a fix worked and provide verification where possible. | Separate execution result from actual resolution outcome. |
| Correct incorrectly grouped incidents. | Recompute linked event/pattern/incident counts. |
| Confirm a fix and request a runbook. | Generate evidence-based Markdown runbook. |
| Approve dataset export. | Sanitize, structure, and export approved records. |

### 5.9 v0.2 release gate

- [ ] Store and retrieve redacted original error logs with provenance.
- [ ] Capture stdout/stderr and exit codes for explicitly tracked commands where supported.
- [ ] Import existing logs without duplication on reimport.
- [ ] Distinguish error **events**, error **patterns**, and **incidents**.
- [ ] Demonstrate that 20 repeated events from one outage do **not** create 20 incidents.
- [ ] Preserve failed, partial, successful, and unknown attempts.
- [ ] Link commands and log artifacts to each troubleshooting attempt.
- [ ] Distinguish user-reported fixes from evidence-verified resolutions.
- [ ] Generate accurate, editable Markdown runbooks.
- [ ] Retrieve past incidents for similar future errors.
- [ ] Export a sanitized structured dataset without leaking credentials.

---

## 6. v0.3: Terraform Plan Explainer + Apply History

### 6.1 Objective

Interpret real Terraform plans, maintain verified apply history, and explain the differences and potential consequences of future changes to Azure infrastructure.

### 6.2 Plan capture and parsing

Example commands from FailSafe's development layout:

```bash
terraform -chdir=terraform/environments/dev plan -out=tfplan
terraform -chdir=terraform/environments/dev show -json tfplan
```

CL-AI should accept an existing plan path or explicitly ask permission before invoking safe analysis commands. Saved plan artifacts are sensitive and should not be committed to Git.

**Deterministic parser responsibilities**

- Read `terraform show -json` output.
- Enumerate resource changes and Terraform action arrays.
- Count creates, updates, deletes, and replacements accurately (including replacement actions involving both delete and create).
- Extract relevant resource names, addresses, changed attributes, and known-unknown status where safe.
- Identify proposed changes affecting networking, identity, AKS node pools, storage, or other dependencies.
- Redact sensitive attributes **before** any Qwen Cloud request.
- Produce a structured summary that Qwen explains in simple language.

### 6.3 Sample report (illustration only)

```text
CL-AI Terraform Report / dev
  Create: 1  |  Update: 2  |  Delete: 0  |  Replace: 1

Observed planned action:
  AKS node pool replacement

Possible impact:
  Running workloads may be disrupted; check rollout/availability requirements.

Observed planned action:
  NSG rule source range widened

Possible impact:
  Network exposure may increase, depending on other access controls.

Status: Analysis only; no Terraform apply performed.
```

**Separate facts and predictions.** Qwen may describe likely security, cost, or availability effects but must identify them as possible impacts rather than guaranteed outcomes. Exact Azure billing requires separate cost data/estimators and cannot be inferred reliably from a generic plan alone.

### 6.4 Verified Terraform apply history

Store records with:

- Apply record ID, timestamp, Terraform environment/workspace/state reference.
- Git commit and source/configuration revision, if available.
- Intended saved plan reference and sanitized change summary.
- Actual apply command/result, completion evidence, and verification level.
- Relevant resulting state/plan references (not raw state contents in the ordinary database).
- Changed resource addresses and actions.

**Verification labels**

- `planned`: A plan exists; not applied.
- `apply_observed_success`: CL-AI or a trusted integration observed a successful apply.
- `ci_verified_success`: Verified by an accessible deployment record.
- `user_reported_success`: User says it succeeded; independent evidence unavailable.
- `failed` or `unknown`: Apply unsuccessful or evidence incomplete.

A saved Terraform state snapshot is **not** by itself a history of successful applies. If the user runs Terraform outside CL-AI, a verified history requires trustworthy CI/job evidence or an explicit recorded execution flow.

### 6.5 Historical comparison

Example request:

```text
You: Compare my new dev plan with my last confirmed apply.
```

CL-AI should:

1. Find the relevant environment's most recent confirmed apply record.
2. Identify what that record says was deployed and what the new plan proposes now.
3. Compare available resource changes, configuration metadata, and significant attributes.
4. Highlight infrastructure drift or unknown history rather than guessing.
5. Explain potentially affected systems using only supported dependency evidence.
6. Suggest manual checks before an apply.

**Important limit:** A current plan is based on current configuration/state and may include drift or external changes. Comparing history does not prove that an earlier apply caused a later difference.

### 6.6 Manual input vs. automatic behavior in v0.3

| Manual user action | Automatic CL-AI behavior |
|---|---|
| Choose plan path or authorize plan inspection. | Parse plan JSON and count changes. |
| Request a risk explanation. | Produce evidence-based Qwen summary from sanitized fields. |
| Choose environment if not determinable. | Filter correct deployment records. |
| Provide or authorize retrieval of successful apply evidence. | Create a history record with verification label. |
| Ask to compare last apply and new plan. | Compute and explain grounded differences. |
| Decide whether and how to deploy. | No automatic `apply` or `destroy`. |

### 6.7 v0.3 release gate

- [ ] Parse saved Terraform plans without sending raw plans to Qwen Cloud.
- [ ] Count create/update/delete/replace correctly, including replacement semantics.
- [ ] Identify resource change facts without hallucination.
- [ ] Provide meaningful but qualified risk descriptions.
- [ ] Record actual apply evidence and verification labels.
- [ ] Compare current proposals against relevant historical records.
- [ ] Gracefully handle absent/stale history and unknown state.
- [ ] Never silently apply changes or expose sensitive plan values.

---

## 7. v0.4: Interactive Troubleshooting Agent

### 7.1 Objective

Allow CL-AI to investigate a problem through **approved and bounded** diagnostic tools, drawing on the Command Vault, runbooks, error logs, Terraform history, and local project configurations.

### 7.2 Agent capabilities

- [ ] Interpret a natural-language problem report.
- [ ] Identify which evidence and tool categories might help.
- [ ] Ask permission before accessing project files or running diagnostic tools.
- [ ] Inspect approved Docker status, logs, ports, and connectivity data.
- [ ] Inspect approved Git status/diffs and relevant configuration files.
- [ ] Inspect relevant Terraform summaries and verified apply history.
- [ ] Build a **limited** dependency view from actual Compose files, service URLs, module references, and relevant configuration (not guessed relationships).
- [ ] Retrieve matching Vault commands and incident/runbook records.
- [ ] Recognize when an earlier proposed fix failed in a comparable environment.
- [ ] Provide probable causes **with cited evidence from inspected files/logs**.
- [ ] Suggest safe next steps and distinguish unknowns from facts.
- [ ] Record user-confirmed successful resolution back into the incident history and runbook.

### 7.3 Tool design: no unrestricted shell agent

Provide typed, approved diagnostic functions such as:

- `get_docker_compose_status(project_path)`
- `read_service_logs(service, max_lines)`
- `inspect_config_file(approved_path)`
- `get_git_status(repository_path)`
- `get_recent_git_diff(repository_path, allowed_range)`
- `get_terraform_plan_summary(environment)`
- `search_command_vault(query)`
- `search_incident_history(error_signature)`

The names are illustrative. Each tool must validate inputs, limit file paths and output volume, redact secrets, and maintain an audit trail. Prefer subprocess argument arrays over shell string execution; never use AI-supplied `eval`.

No automatic service restarts, deletion, `terraform apply`, `terraform destroy`, or configuration modifications in this release.

### 7.4 Example investigation

```text
You: My order service cannot reach payment. Can you investigate?
CL-AI: I can read Docker status, selected service logs, and the relevant
       Compose configuration. May I perform these read-only checks?
You: Yes.
CL-AI: The order service configuration points to a payment port that
       differs from the configured payment endpoint. I also found a
       related historical incident whose first fix failed.
       Here are the matching config lines and log references...
You: I corrected the port and checkout now passes.
CL-AI: Record this as user-confirmed and attach a passing test result?
You: Yes.
CL-AI: Incident and runbook updated.
```

### 7.5 Manual input vs. automatic behavior in v0.4

| Manual user action | Automatic CL-AI behavior |
|---|---|
| Describe the problem. | Select relevant evidence categories. |
| Approve limited diagnostic access. | Run allowlisted read-only tools and record provenance. |
| Give missing context or correct wrong assumptions. | Refine the investigation and confidence level. |
| Choose whether to make suggested changes. | Do not perform modifications automatically. |
| Verify and confirm resolution. | Record linked attempt, evidence, and runbook update. |

### 7.6 v0.4 release gate

- [ ] Agent can conduct a controlled end-to-end investigation in a test project.
- [ ] All tool calls require a user-authorized scope.
- [ ] No arbitrary-shell execution from the LLM is possible.
- [ ] Logs/configuration/previous records are used as evidence rather than guesses.
- [ ] Tool failures and missing context are surfaced honestly.
- [ ] User-confirmed outcomes flow back to v0.2.
- [ ] Security tests cover path traversal, prompt injection from logs/web pages, and secret leakage.

---

## 8. v1.0: Stable, Integrated CLI Release

Focus on quality and reliability rather than adding more major modules.

- [ ] Integrate v0.1-v0.4 into the same terminal workflow.
- [ ] Document installation, environment configuration, and Bash integration.
- [ ] Provide `.env.example` without actual credentials.
- [ ] Add database migrations and recovery/backup procedures.
- [ ] Add import/export and deletion of command, incident, and log records.
- [ ] Add configurable log retention, storage quotas, and AI request limits.
- [ ] Document what is sent to Qwen Cloud and require opt-in for external log sharing.
- [ ] Add deterministic tests with fixture logs, saved Terraform plan samples, and mocked Qwen/search responses.
- [ ] Test Qwen outage, web search outage, missing Bash hook, unrecognized command, and corrupted/missing logs.
- [ ] Check Git Bash, VS Code terminal, and packaging/install behavior.
- [ ] Provide practical demonstrations from the FailSafe E-Commerce lab.
- [ ] Publish an installable Python package/release with a clear README and limitations.

---

## 9. Manual Input and Automatic Work: Master Matrix

| Module / task | What you manually input or approve | What CL-AI automatically performs |
|---|---|---|
| CLI session | Run `cl-ai`, type questions, choose `exit`. | Conversation routing and readable output. |
| Save command | Paste command or call `save the command`; review confirmation. | Capture candidate, generate docs, categorize, deduplicate, store. |
| Retrieve command | Describe desired task. | Search SQLite and explain actual stored matches. |
| Online `-helpme` | Ask question, specify missing environment details, optionally save result. | Live web retrieval, Qwen explanation, source links and risk notes. |
| Open incident | Describe failure or start tracking. | Assign ID, timestamps, local context. |
| Capture error | Paste/import log or authorize tracked execution. | Save sanitized log artifact, metadata, event identifiers. |
| Track attempts | Report external changes and whether fix worked. | Build timeline; link commands, AI suggestions, and before/after evidence. |
| Recurrence analysis | Correct a wrongly grouped incident when necessary. | Count events, patterns, and distinct incidents without double counting. |
| Generate runbook | Confirm outcomes and request documentation. | Draft evidence-backed Markdown guide. |
| Terraform analysis | Select plan; approve file inspection. | Parse JSON, summarize changes and risks. |
| Terraform history | Supply/authorize successful apply evidence. | Label verification and store metadata. |
| Compare deployments | Ask for comparison, choose environment if needed. | Compare grounded records and report uncertainties. |
| Troubleshoot with agent | Describe problem, approve tools, verify fix. | Collect permitted diagnostics and synthesize grounded advice. |
| Future MLOps export | Review and authorize sanitized dataset. | Prepare labeled, structured export and provenance records. |

### 9.1 What CL-AI must never assume

- A saved command was executed successfully.
- A successful exit code means the incident is resolved.
- A user-provided log was captured from the current machine.
- Twenty repeated log events equal twenty separate incidents.
- A Terraform plan was successfully applied.
- A previously working fix will work under different versions/configurations.
- An AI-generated command is documented, current, safe, or correct unless checked.
- A Qwen Cloud API account includes free unlimited requests or built-in browsing.

---

## 10. Persistent Storage and Data Model

### 10.1 Local storage layout

```text
~/.cl-ai/
|-- cl_ai.db
|-- config/
|   `-- settings.toml
|-- logs/
|   |-- INC-0001/
|   |   |-- execution-001.stdout.log
|   |   |-- execution-001.stderr.log
|   |   `-- attempt-002.log
|   `-- INC-0002/
|-- runbooks/
|   |-- terraform-provider-error.md
|   `-- payment-connectivity.md
|-- exports/
|   `-- troubleshooting_dataset.jsonl
`-- backups/
```

Store database and sensitive log files outside the public Git repository by default. Directory paths are illustrative; make Windows path resolution robust.

### 10.2 Suggested SQLite tables

| Table | Starting version | Purpose |
|---|---|---|
| `commands` | v0.1 | Original commands and generated documentation. |
| `command_sources` | v0.1 | Official URLs/source provenance. |
| `command_contexts` (optional) | v0.1 | Project, shell, paths, usage/verification observations. |
| `incidents` | v0.2 | Distinct troubleshooting episodes. |
| `error_patterns` | v0.2 | Normalized error signatures. |
| `error_events` | v0.2 | Observed error occurrences, potentially multiline. |
| `log_artifacts` | v0.2 | Redacted log files, sources, hashes, and retention metadata. |
| `command_executions` | v0.2 | Explicitly tracked command executions and exit codes. |
| `troubleshooting_attempts` | v0.2 | Actions and outcomes within each incident. |
| `recommendations` | v0.2 | AI/online/user recommendations and their sources. |
| `resolutions` | v0.2 | Resolution claims, labels, verification references. |
| `runbooks` | v0.2 | Generated documentation and its incident linkage. |
| `terraform_applies` | v0.3 | Deployment outcomes and verification evidence. |
| `terraform_changes` | v0.3 | Sanitized planned/applied resource change metadata. |
| `agent_sessions` / `tool_calls` | v0.4 | Permissions, tool requests, results, and audits. |

### 10.3 Data-quality rules

- Use stable IDs, timestamps, and foreign-key relationships.
- Separate observed execution outcomes, user-reported outcomes, and independently verified resolutions.
- Do not overwrite failed attempts when a later attempt succeeds.
- Avoid double counting when the same file is reimported.
- Record truncation, redaction, and missing data explicitly.
- Keep versioned schemas and migrations as the project evolves.
- Never treat Qwen-generated summaries as substitutes for original captured evidence.

---

## 11. Privacy, Security, and Cost Controls

### 11.1 Data leaving the laptop

Qwen Cloud is the primary inference service, meaning text sent to it leaves the local computer. The user has permission to use their API, but that does not automatically authorize uploading every log, state file, token, or project secret.

Default behavior:

- Command Vault can send **sanitized command text** for explanations after secret checks.
- v0.2 should send only selected, sanitized error excerpts or derived incident summaries; sending full logs requires explicit consent/configuration.
- v0.3 should send only locally parsed, sanitized change summaries, not raw Terraform plan/state files.
- v0.4 should limit prompt content to required, bounded, sanitized diagnostic evidence.
- Verify the particular Qwen service provider's data-retention, training-use, pricing, and permission terms independently.

### 11.2 Core safety requirements

- Keep API keys in local environment variables or a protected secret store, not Git.
- Detect and redact tokens, credentials, private keys, and sensitive connection strings.
- Do not send raw state files or entire plan JSON to a hosted model.
- Never execute online-documentation instructions simply because a web page suggests them.
- Treat web content, logs, and repository comments as untrusted data (prompt injection protection).
- Restrict diagnostic tools to typed, allowlisted operations and approved paths.
- Confirm any write or destructive action; v0.4 remains read-only by design.
- Enforce maximum log size, retention policies, and deletion/export controls.
- Track approximate API request and search usage when the provider exposes consumption data; use configurable soft limits to avoid unexpected charges.

### 11.3 Cost assumptions

Local Python/SQLite and local storage do not need an additional cloud server. **Qwen Cloud inference may incur usage charges** depending on the user's authorized account, model, and quota. Real web search may likewise have a quota or cost. Azure infrastructure used by FailSafe is separate and may incur charges independently.

Recommended first configuration: local data, bounded Qwen requests, a real free/low-cost docs retrieval option, no new Azure resources for CL-AI, and no automatic cloud fallback that could spend money unexpectedly.

---

## 12. Future MLOps: Use the Data, Do Not Pretend the Model Retrains Itself

### 12.1 Three stages of improving CL-AI

1. **Retrieval (available from v0.2):** Search relevant historical incidents and pass a small, sanitized evidence bundle to Qwen. No model training required.
2. **Feedback-aware ranking (later):** Rank suggested actions using outcomes and context from prior attempts. This can be rule-based or use small classifiers before any LLM fine-tuning.
3. **Model training/fine-tuning (future experiment):** Curate reviewed, consented, sanitized records, select a compatible model, and build training/evaluation pipelines. Fine-tuning is not guaranteed to improve performance.

### 12.2 Suggested dataset unit

Use **one troubleshooting episode** as a core sample containing structured references to events, attempts, and outcomes, rather than treating every repeated error line as an independent training sample.

Example illustrative JSONL record:

```json
{"incident_id":"INC-0042","project":"failsafe-ecommerce","category":"docker-networking","error_pattern":"connection_refused","event_count":20,"attempts":[{"action":"change_external_port","source":"ai","outcome":"failed"},{"action":"correct_internal_service_port","source":"user","outcome":"user_confirmed_success"}],"verification":"checkout_test_passed","redacted":true}
```

This is a simplified sample. Real exports also need timestamps, tool versions, incident context, evidence references, provenance, and licensing/privacy review.

### 12.3 Evaluation and data governance

- Review and remove secrets, sensitive company data, and personally identifying log content before export/training.
- Split training and evaluation by **incident and time**, not randomly by repeated log lines (avoid leakage of nearly identical events).
- Track dataset version and label provenance.
- Measure retrieval accuracy, verified fix usefulness, unsafe suggestion rate, hallucination rate, and explanation quality.
- Compare against a baseline that uses retrieval without fine-tuning.
- Only claim a trained model is better when it improves performance on **unseen** incidents.

Potential later tools: dataset versioning, experiment tracking, model registry, inference evaluation, and automated regression checks. These are intentionally outside the initial v0.1-v1.0 release scope.

---

## 13. Proposed Repository Structure

Place CL-AI in the FailSafe repository but keep it installable and reusable independently.

```text
failsafe-ecommerce/
|-- services/
|-- terraform/
|-- kubernetes/
|-- monitoring/
|-- docs/
`-- tools/
    `-- cl-ai/
        |-- README.md
        |-- pyproject.toml
        |-- .env.example
        |-- src/
        |   `-- cl_ai/
        |       |-- __init__.py
        |       |-- cli.py
        |       |-- chat.py
        |       |-- router.py
        |       |-- config.py
        |       |-- ai/
        |       |   |-- provider.py
        |       |   |-- qwen_adapter.py
        |       |   |-- schemas.py
        |       |   `-- prompts.py
        |       |-- vault/
        |       |-- helpme/
        |       |-- shell/
        |       |-- runbooks/            # add in v0.2
        |       |-- terraform/           # add in v0.3
        |       |-- agent/               # add in v0.4
        |       |-- storage/
        |       `-- security/
        `-- tests/
```

**Do not create all future modules on day one.** Add directories when their version begins. The real personal database and captured logs belong in the local data directory, not this source tree.

---

## 14. Development Sequence and Estimated Effort

Estimates assume focused sessions of approximately 1-2 hours and may expand with testing and unfamiliar APIs.

| Order | Milestone | Estimated sessions | Proof of completion |
|---|---|---:|---|
| 1 | CLI + Qwen adapter | 2-3 | Stable `cl-ai` chat; model connection configurable. |
| 2 | SQLite Command Vault | 2-3 | Save/read/edit/delete records. |
| 3 | AI-generated command documentation | 2-3 | Structured, reviewable command record. |
| 4 | Git Bash previous-command integration | 2-4 | Correct `save the command` behavior and fallback. |
| 5 | Natural-language Vault search | 2-3 | Relevant retrieval with clear source labels. |
| 6 | Online `-helpme` research | 3-5 | Real official source URLs and useful explanations. |
| 7 | v0.1 hardening/tests | 2-3 | All v0.1 release gates pass. |
| 8 | v0.2 incident and log capture | 4-6 | Real log artifacts and incident associations. |
| 9 | v0.2 attempts, counting, deduplication | 4-6 | Correct separate event/pattern/incident counts. |
| 10 | v0.2 runbooks and dataset export | 3-5 | Evidence-backed runbook and sanitized export. |
| 11 | v0.3 Terraform plan parsing | 4-7 | Accurate action extraction and explanation. |
| 12 | v0.3 apply history and comparison | 4-7 | Verified records and useful comparisons. |
| 13 | v0.4 diagnostic agent | 10-20 | Approved, grounded troubleshooting demonstration. |
| 14 | v1.0 hardening and packaging | 5-8 | Tested, installable CLI release. |

Do not spend extra Azure money just to prove CL-AI works. Prefer local fixtures, mocked API responses, and existing FailSafe development scenarios.

---

## 15. First Development Session (1-2 Hours)

**Focus:** Only the CLI foundation with Qwen Cloud. No full Vault, database, or incident tracking yet.

- [ ] Create `tools/cl-ai/` and initialize an installable Python project.
- [ ] Create and activate a virtual environment.
- [ ] Install core packages (CLI, terminal formatting, model client, tests).
- [ ] Verify the Qwen Cloud provider's **actual base URL, available model name, authentication method, quotas, and terms**.
- [ ] Add `.env.example`, `.gitignore`, and protected local configuration loading.
- [ ] Create the `cl-ai` entry point and basic interactive chat loop.
- [ ] Implement a small Qwen adapter with timeouts, meaningful errors, and no key logging.
- [ ] Test a simple command explanation such as `terraform init`.
- [ ] Add an exit command and a test that the program fails gracefully without an API key.
- [ ] Commit the working foundation without secrets.

**Expected result**

```text
$ cl-ai
CL-AI v0.1 | Provider: Qwen Cloud
You: Explain terraform plan in simple terms.
CL-AI: Terraform plan previews the infrastructure changes it would make,
       but does not apply them.
You: exit
$
```

### Immediate next session

Build the initial SQLite `commands` table and a manual `cl-ai save "command"` workflow. **Only after manual saving works** should you add AI documentation, Git Bash `save-last`, then natural-language retrieval and real online `-helpme`.

---

## 16. Final Scope and Acceptance Summary

**v0.1 - Discover and remember commands**  
Qwen generates command descriptions; Bash integration retrieves recent command text with permission; SQLite persists the Vault; `-helpme` performs real online documentation research.

**v0.2 - Remember the entire troubleshooting journey**  
CL-AI stores redacted error logs, commands, failed attempts, attempted fixes, outcomes, supporting evidence, and runbooks. It counts **error events**, **patterns**, and **incidents** separately. Repeated log lines from one outage must **never** become separate incidents just because they repeat.

**v0.3 - Understand and remember Terraform changes**  
Local JSON parsing supplies exact planned actions. Qwen explains them. Verified applies are tracked separately from plans and user reports; sensitive Terraform data stays protected.

**v0.4 - Investigate with evidence and permission**  
A bounded, read-only agent inspects authorized diagnostics and retrieves Vault/runbook/Terraform history to suggest supported next steps; confirmed resolutions update historical records.

**v1.0 - A reliable daily-use terminal tool**  
One installable CLI, clear documentation, tests, private local storage, safe cloud-data boundaries, and working FailSafe demonstrations.

**Future - MLOps experiments**  
Use curated, sanitized historical incidents for retrieval evaluations, ranking and, if justified, model-training experiments. Qwen Cloud remains the initial inference backend; Ollama can be introduced later without rewriting all modules.

**Guiding principle:** Let Python capture, count, store, parse, and enforce permissions. Let Qwen explain, classify, summarize, and propose. Let the user approve consequential actions and confirm what actually worked.
