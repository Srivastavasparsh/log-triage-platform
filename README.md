# Autonomous On-Call DevOps & Log Triage Agent

An event-driven, self-healing incident remediation pipeline built with **Python, Watchdog, LangGraph, Gemini API (`v1beta`), Docker, SQLite, and GitHub REST API**.

When a service writes an unhandled exception traceback to `logs/`, the ingestion daemon parses the stack trace in real time, triggers a stateful **Diagnose → Patch → Verify** agent loop, validates the generated fix against the service's test suite, and opens a **Draft Pull Request** with a root-cause report.

## System Architecture

1. **Real-Time Log Ingestion (`src/ingester.py`):** Uses `watchdog` with byte-offset tracking and multi-line traceback grouping to detect `ERROR` events without duplicate reads or test-log feedback loops.
2. **Telemetry & Audit Persistence (`src/db.py`):** Stores raw structured logs (`logs` table) and agent remediation outcomes/PR URLs (`remediations` table) in SQLite (`telemetry.db`).
3. **Stateful Remediation Loop (`src/agent/graph.py`):**
   - **Diagnose & Patch:** Sends stack trace, source code, and existing unit tests to Gemini (`gemini-2.5-flash`) using structured Pydantic outputs (`DiagnosisPlan`).
   - **AST & Sandbox Verification (`src/agent/sandbox.py`):** Validates syntax via `ast.parse()` and executes `pytest` inside an isolated Docker container (with local `venv` fallback) before accepting any change.
   - **Retry & Escalation Guardrails:** Automatically retries failed patches with test-failure feedback up to `MAX_RETRIES`, escalating to human review if verification fails.
4. **Automated GitHub PR (`src/agent/github_pr.py`):** Creates an isolated `fix/<service>-<error>` branch, commits the verified patch, and opens a Draft Pull Request via the GitHub REST API.

## Quick Start

```bash
git clone [https://github.com/Srivastavasparsh/log-triage-platform.git](https://github.com/Srivastavasparsh/log-triage-platform.git)
cd log-triage-platform
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Configure .env:
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_pat
GITHUB_REPO=Srivastavasparsh/log-triage-platform
LOGS_DIR=logs

Run the Live Demo

Start the ingestion daemon:
python3 src/ingester.py

Trigger a production crash in target_app/billing.py:
python3 -c "from target_app.billing import calculate_unit_price; calculate_unit_price(100.0, 0)"
## 2. LinkedIn Post & Resume Bullets

**LinkedIn Post (pair with your 45-second screen recording):**
> Most "AI coding" demos stop at pasting a stack trace into a chat box. I wanted to build an end-to-end pipeline that actually handles the on-call workflow safely.
>
> I upgraded my log-triage platform into an **Autonomous On-Call DevOps Agent**:
> 1️⃣ A `watchdog` daemon tails production logs in real time and groups multi-line Python stack traces.
> 2️⃣ A **LangGraph** state machine reads the failing code + existing unit tests and generates a structured patch via the Gemini API.
> 3️⃣ Before any code is touched on GitHub, an AST parser and isolated `pytest` sandbox verify the fix (retrying automatically if tests fail, or escalating to a human).
> 4️⃣ Once verified, it cuts a `fix/` branch and opens a **Draft Pull Request** with the root-cause analysis.
>
> Building this taught me how critical guardrails are in agentic systems—specifically preventing test-log feedback loops, handling Git branch race conditions, and enforcing deterministic test verification before PR creation.
>
> Code & architecture: [https://github.com/Srivastavasparsh/log-triage-platform](https://github.com/Srivastavasparsh/log-triage-platform)
>
> #SoftwareEngineering #AIAgents #DevOps #Python #LangGraph #BackendDevelopment

**ATS Resume Bullets (for Backend / AI Engineer roles):**
* Engineered an event-driven autonomous DevOps agent using **Python, Watchdog, LangGraph, and Gemini API** that detects live stack traces, diagnoses root causes, and opens verified **Draft Pull Requests** via the GitHub REST API.
* Implemented multi-stage verification guardrails (**AST syntax validation**, isolated **Docker/pytest sandboxing**, and thread-safe log offset tracking) with SQLite audit persistence, preventing unverified patches and test-log feedback loops.

---

Once you commit `README.md` and merge your PR on GitHub into `main`, are you ready to move on to upgrading **`collab-space`** into a **Live Multi-Agent Co-Editor**?