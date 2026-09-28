# 🍬 Meher Sweets & Namkeen — Grounded Customer Support AI
**An enterprise-grade, deterministic customer query agent and real-time evaluation suite powered by FastAPI and local LLM inference (llama3.1:8b via Ollama). Built with strict guardrails, automated arithmetic normalization, PII sanitization, and live streaming test monitoring.**
## 📑 Table of Contents
- [📌 Overview](#-overview)
- [✨ Key Features](#-key-features)
- [📐 System Architecture](#-system-architecture)
- [🛡️ Four-Tier Guardrails (G1 – G4)](#️-four-tier-guardrails-g1--g4)
- [📊 Evaluation Benchmarks & Metrics](#-evaluation-benchmarks--metrics)
- [🛠️ Tech Stack & Dependencies](#️-tech-stack--dependencies)
- [📂 Repository Structure](#-repository-structure)
- [🚀 Quickstart & Setup Guide](#-quickstart--setup-guide)
- [🧪 Running Evaluations & Pytest Suites](#-running-evaluations--pytest-suites)
- [📡 API & Live Streaming Endpoints](#-api--live-streaming-endpoints)
- [🧩 Problem-Solving & Edge-Case Log](#-problem-solving--edge-case-log)
- [🤝 Contributing & License](#-contributing--license)
## 📌 Overview
**Meher Sweets & Namkeen** is a multi-turn customer assistance platform that automates sweet and snack inquiries, bulk pricing, store delivery validation, and customer intake. Built to operate **100% locally with zero cloud API token costs**, the agent guarantees factual consistency against store menus and operational policies through continuous verification and four explicit runtime guardrails.
### 🎯 Core Objectives
- **Zero Rupee Hallucination**: Strict verification ensuring quoted amounts originate directly from prices.csv or derived catalog arithmetic.
- **Deterministic Tool Routing**: Autonomous qualification of high-intent buyers (save_lead) and customer health/safety escalations (escalate).
- **Real-time Observability**: Server-Sent Events (SSE) streaming live benchmark traces directly to a responsive browser workbench.
## ✨ Key Features
- 🧮 **Unit-Aware Catalog Normalizer**: Converts fractional pack sizes (e.g., 500 g unit prices to 1 kg and multi-pack equivalents) directly inside retriever contexts to eliminate small-language-model calculation errors.
- 🛡️ **Autonomous Tool Execution**:
  - save_lead: Extracts customer name, validates 10-digit Indian phone numbers and email formats, timestamps leads, and writes masked entries.
  - escalate: Immediately flags spoiled sweets, hygiene incidents, insects, or urgent bulk corporate orders (>200 boxes) requiring custom branding.
- 🔒 **PII Redaction Engine**: Masks phone numbers (98765*****) and emails (u***r@example.com) in logs, traces, and UI payloads.
- 🌐 **Devanagari & Hinglish Support**: Expands phonetically mapped Hindi keywords into verified catalog SKUs and store policy sections.
- 📈 **Live Evaluation Workbench**: Runs 69 full benchmark cases directly from the browser UI with live SSE progress bars, latency percentiles, and instant metric reporting.
- 📝 **Automated Report Synchronization**: Dynamic generation of reports/summary.md and evals/eval_report.md on every evaluation run.
## 📐 System Architecture

The runtime is organized into five layers. Dependencies flow from the interface toward orchestration, knowledge and actions; the model proposes text or tool calls, but deterministic application code remains responsible for validation and final response safety.

```text
+-------------------------------------------------------------------------+
|                  Web Workbench UI (`static/index.html`)                 |
|      [Live Query Playground]      |      [Real-Time Eval Stream]        |
+-------------------------------------------------------------------------+
                  |                                           ^
            REST Chat API                               SSE Live Stream
                  v                                           |
+-------------------------------------------------------------------------+
|                       FastAPI Service (`src/main.py`)                   |
|                        Uvicorn ASGI Engine (Port 8000)                  |
+-------------------------------------------------------------------------+
     |
     |
     |
     +---> Hybrid Knowledge Base Retriever (`src/retriever.py`)
     |       |---> Product Catalog (`data/prices.csv`)
     |       |---> Store Policies (`data/policies.md`)
     |       +---> Unit Conversion Context Normalizer
     |
     +---> Local LLM Orchestrator (`src/agent.py`)
     |       |---> Ollama Runtime (`llama3.1:8b`)
     |       +---> Multi-Turn Conversation Memory Buffer
     |
     +---> Deterministic Tool Execution Router (`src/actions.py`)
     |       |---> `save_lead`: Phone Normalization & Contact Intake
     |       +---> `escalate`: Hygiene, Food Safety & Corporate Orders
     |
     +---> Runtime Guardrail Verifier & PII Masking (`src/masking.py`)
         |---> [G1 Verification] AI Disclosure
         |---> [G2 Verification] Grounded Rupee / Price Auditor
         |---> [G3 Verification] Character Budget Auditor (< 1200 chars)
         +---> [G4 Verification] Citation & Data Provenance Tracker
```

### Layer ownership

| Layer | Modules | Responsibility |
| --- | --- | --- |
| Interface | `static/index.html`, `src/main.py` | Browser UI, HTTP validation, response serialization, health and evaluation endpoints |
| Orchestration | `src/agent.py` | Scope checks, prompt construction, conversation history, model calls, tool sequencing, handoff state |
| Knowledge | `src/retriever.py`, `data/` | Catalog and policy loading, Hindi/Hinglish aliases, grounded context, source IDs |
| Actions and safety | `src/tools.py`, `src/masking.py`, `src/rupee_checker.py` | Tool validation, escalation/lead execution, PII masking, currency extraction and G2 helpers |
| Model and configuration | `src/config.py`, Ollama or another OpenAI-compatible endpoint | Model connection, credentials, temperature, step limit, and reply-length limit |
| Evaluation | `scripts/run_eval.py`, `scripts/inspect_failures.py`, `reports/` | Three-pass HTTP tests, G1-G4 checks, action assertions, metrics, and failure inspection |

### Request ownership

1. `src.main` validates `conversation_id` and `message`, retrieves the in-process history, and calls `run_agent_turn`.
2. `src.agent` rejects known out-of-scope requests or asks `src.retriever` for grounded context.
3. `src.agent` sends the system prompt, history, and grounded query to the configured model.
4. Model tool calls are validated and executed by `src.tools`; complaints also have a deterministic escalation fallback.
5. `src.agent` applies disclosure, privacy, prompt-injection, delivery-math, lead-output, and length guardrails before returning.
6. `src.main` returns `reply`, `sources`, `actions`, `handoff`, and token counts. Logs and `/leads` output use masking helpers.

### Important boundaries

- Conversation history and saved leads are process-local. A restart clears them, and multiple workers do not share them.
- Runtime retrieval is implemented in `src.retriever`; `src.data_loader` independently loads a typed knowledge base for tests and G2 allowed-price checks. These duplicate loaders should eventually be unified.
- `src.main` currently serves chat, leads, the static UI, report enrichment, and live evaluation streaming. These responsibilities can later move into separate API modules without changing the agent contract.
- `src.tools` is the authorization boundary for side effects. The model can request `save_lead` or `escalate`, but it cannot bypass validation.
## 🛡️ Four-Tier Guardrails (G1 – G4)
| Guardrail | Title | Target | Verification Mechanism |
| --- | --- | --- | --- |
| **G1** | **AI Identity Disclosure** | 100.0% | Ensures the assistant explicitly discloses that it is an AI support assistant on the first conversational turn. Guaranteed via deterministic fallback insertion. |
| **G2** | **Rupee Grounding** | 0.00% Hallucination | Extracts all currency values (₹, Rs, INR) and validates them strictly against catalog items and valid pack multiples. Ungrounded amounts trigger instant failure. |
| **G3** | **Length Budget** | < 1200 Chars | Constrains completion token length to maintain concise, mobile-friendly responses and prevent conversational drift. |
| **G4** | **Source Provenance** | 100.0% Audited | Requires factual claims, pricing, and radius policies to correlate with cited knowledge source IDs (prices.csv#SKU, policies.md#section). |
## 📊 Evaluation Benchmarks & Metrics
Benchmarked across **69 rigorous multi-turn evaluation cases** (evals/cases.jsonl) on a local llama3.1:8b model:
### 🏆 Top-Level Performance
| Metric | Score Achieved | Target Threshold | Status |
| --- | --- | --- | --- |
| **Overall Pass Rate** | **94.20% (65 / 69 passed)** | >= 85.0% | 🟢 **Surpassed** |
| **G1 (AI Identity Compliance)** | **100.00%** | 100.0% | 🟢 **Perfect** |
| **G2 (Invented Rupee Rate)** | **0.00%** | 0.00% | 🟢 **Zero Hallucination** |
| **Tool / Action Accuracy** | **100.00%** | >= 90.0% | 🟢 **Surpassed** |
| **p50 Latency** | **10,534.0 ms** | < 15,000 ms | 🟢 **Optimal (Local)** |
| **p95 Latency** | **21,221.5 ms** | < 30,000 ms | 🟢 **Optimal (Local)** |
### 🪙 Token Consumption & Cost Analysis
- **Prompt Tokens In per Message (Mean)**: 2,152.0 tokens
- **Completion Tokens Out per Message (Mean)**: 102.8 tokens
- **Total Tokens per Message (Mean)**: 2,254.8 tokens
- **Cost per 100 Conversations (Local Ollama)**: **₹0.00**
- **Theoretical Cloud Reference Cost (@ ₹100 / USD)**: ~**₹11.53 per 100 conversations** (assuming 3 turns/conversation on standard commercial endpoints at $0.15/1M prompt and $0.60/1M completion).
### 📁 Category Breakdown
| Category | Passed / Total | Pass Rate | Observed Behavior |
| --- | --- | --- | --- |
| **Policies (Delivery, Hours, Radius)** | 11 / 11 | **100.0%** | Enforces 8 km delivery ceiling and ₹999 free shipping threshold accurately. |
| **Lead Capturing (save_lead)** | 8 / 8 | **100.0%** | Accurately normalizes 10-digit phone formats, validates emails, and masks PII. |
| **Escalations (escalate)** | 7 / 7 | **100.0%** | Correctly escalates spoiled food, bad odors, insects, and large corporate inquiries. |
| **Multilingual (Hindi & Hinglish)** | 10 / 10 | **100.0%** | Accurately identifies transliterated sweet queries and Devanagari prompts. |
| **Multi-Turn Context & Memory** | 9 / 10 | **90.0%** | Retains selected sweet varieties and quantities across subsequent turns. |
| **Prompt Injections & Defenses** | 8 / 9 | **88.9%** | Defends against unauthorized discounts; ignores off-topic programming queries. |
| **Arithmetic & Unit Pricing** | 12 / 14 | **85.7%** | Accurately resolves 500 g vs 1 kg pack rates (e.g., 2 kg Dhokla = ₹640, 4 kg = ₹1,280). |
## 🛠️ Tech Stack & Dependencies
- **Language**: Python 3.11+
- **Framework**: FastAPI, Starlette, Uvicorn
- **LLM Engine**: Ollama (llama3.1:8b)
- **Testing & Quality Assurance**: Pytest (pytest-asyncio, anyio)
- **Frontend**: Vanilla HTML5, Modern CSS, JavaScript (Fetch API & Server-Sent Events EventSource)
- **Data Sources**: CSV (prices.csv), Markdown (policies.md)
## 📂 Repository Structure

Meher Sweets Customer-Query Agent/
├── data/
│   ├── prices.csv              # Sweet & snack catalog (SKUs, pack sizes, INR rates)
│   └── policies.md             # Delivery radius, thresholds, operating hours, FAQs
├── evals/
│   ├── cases.jsonl             # 69 multi-turn benchmark evaluation test scenarios
│   └── eval_report.md          # Synchronized evaluation report & failure analysis
├── reports/
│   ├── eval_results.json       # Machine-readable evaluation traces, latencies, tokens
│   └── summary.md              # Dynamically compiled benchmark summary
├── src/
│   ├── __init__.py
│   ├── actions.py              # save_lead and escalate tool execution functions
│   ├── agent.py                # LLM orchestration, system prompts, multi-turn loop
│   ├── data_loader.py          # CSV & Markdown knowledge base ingestion
│   ├── masking.py              # Regex-based PII masking (phone & email sanitization)
│   ├── main.py                 # FastAPI endpoints (REST chat + SSE eval stream)
│   └── retriever.py            # Keyword matching, Hindi mapping, unit normalization
├── static/
│   └── index.html              # Responsive workbench UI (Playground & Eval Center)
├── tests/
│   ├── test_data_loader.py     # Verifies data ingestion and section slug generation
│   ├── test_day2.py            # Verifies PII masking and lead validation
│   └── test_requirements.py    # Verifies price grounding, rupee extraction, tool errors
├── .gitignore
├── pytest.ini                  # Pytest configuration (pythonpath = .)
├── README.md                   # Complete repository documentation
└── requirements.txt            # Locked project dependencies
## 🚀 Quickstart & Setup Guide
### 1. Prerequisites
- [Python 3.11+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/) installed and running locally
- Git
### 2. Clone the Repository

git clone <repository-url>
cd "Meher Sweets Customer-Query Agent"
### 3. Create Virtual Environment & Install Dependencies

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
### 4. Pull the Local LLM Model
Ensure the Ollama service is active, then pull the target 8B weights:

ollama pull llama3.1:8b
### 5. Launch the FastAPI Application Server

uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
Open your browser and navigate to:

http://127.0.0.1:8000
## 🧪 Running Evaluations & Pytest Suites
### Running the Full Pytest Suite (12 Tests)
The test suite verifies knowledge loading, phone normalization, email validation, PII masking, and rupee extraction:

python -m pytest -v
*(Passing output: 12 passed in ~0.15s)*
### Running the Batch Evaluation CLI
Run the entire 69-case evaluation benchmark from the terminal:

python -m scripts.run_eval --cases evals/cases.jsonl
This command automatically executes all test cases, evaluates G1–G4 guardrails, writes reports/eval_results.json, and updates both reports/summary.md and evals/eval_report.md.
### Running Real-Time Evaluation via the Web UI
1. Navigate to `http://127.0.0.1:8000` in your browser.
2. Click the **Evaluation Report & Test Trace** tab.
3. Click the green **▶ Run Evaluation Now** button.
4. Observe the live progress bar, real-time pass/fail row streaming, and auto-updated latency and pass-rate metrics.
## 📡 API & Live Streaming Endpoints
### 1. Chat Turn (`POST /api/chat`)
Executes an interactive customer support turn.
**Request Body**:
{
  "message": "How much for 2 kg Khaman Dhokla?",
  "history": []
}
**Response**:
{
  "reply": "Hello! I am an AI assistant for Meher Sweets & Namkeen. The rate of Khaman Dhokla is Rs 160 per 500 g pack. For 2 kg (4 packs), the total cost is Rs 640.",
  "actions": [],
  "sources": [
    "prices.csv#DH-500"
  ],
  "invented_amounts": []
}
### 2. Live Evaluation Stream (`GET /api/run-eval-stream`)
Streams Server-Sent Events (SSE) progress chunk-by-chunk during evaluation runs.
- **Query Params**: `cases_file=evals/cases.jsonl`
- **Stream Events**:
  - `status: "started"` — Provides total case count.
  - `status: "progress"` — Delivers completed turn data, pass/fail status, and latency for each case row in real time.
  - `status: "finished"` — Final run summary with total passed cases.
## 🧩 Problem-Solving & Edge-Case Log
1. **Fractional Pack Size Multipliers**:
   - *Problem*: When asking for 2 kg or 4 kg of an item priced per 500 g (such as Khaman Dhokla at Rs 160), 8B language models often multiplied kilograms directly ($2 \times 160 = 320$).
   - *Solution*: Normalized context strings in `src/retriever.py` to explicitly present both the 500 g unit rate and the calculated 1 kg multiplier, enabling consistent calculations (2 kg = ₹640, 4 kg = ₹1,280).
2. **Pytest Module Resolution on Windows**:
   - *Problem*: Running pytest directly in PowerShell caused `ModuleNotFoundError: No module named 'src'`.
   - *Solution*: Added a project root `pytest.ini` with `pythonpath = .` and standardized test execution via `python -m pytest`.
3. **SSE Connection Lifecycles**:
   - *Problem*: Client disconnections or unhandled per-case exceptions could abort the entire batch evaluation mid-stream.
   - *Solution*: Wrapped each individual test case in an isolated `try...except` block, removed premature disconnect checks, and added `Cache-Control: no-cache` headers.
## 🏷️ Tags & Topics
`#GenerativeAI` `#LocalLLM` `#Ollama` `#Llama3` `#FastAPI` `#Guardrails` `#Python` `#SSE` `#PromptEngineering` `#SoftwareTesting` `#CustomerSupportAI` `#EnterpriseAI`
## 🤝 Contributing & License
Developed as part of the **Meher Sweets Customer-Query Agent** assignment. Released under the [MIT License](LICENSE).
