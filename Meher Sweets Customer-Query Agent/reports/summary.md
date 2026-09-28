# Evaluation Summary Report

*Generated on: 2026-09-29 00:22:22*
*Evaluation Passes: 5 full iterations across 69 test cases (Round 1: 87.0%, Round 2: 87.0%, Round 3: 87.0%, Round 4: 87.0%, Round 5: 87.0%)*

### 📊 Benchmark Overview
- **Model Used**: `llama3.1:8b` (Local Ollama)
- **Overall Pass Rate (Mean across 5 runs)**: 86.96% (60.0 / 69 passed)
- **AI Disclosure Compliance (G1)**: 100.00%
- **Invented Rupee Rate (G2 Failures)**: 0.00%

---

### ⏱ Latency & Performance (All Runs Pooled)
- **p50 Latency**: 10771.8 ms
- **p95 Latency**: 24077.4 ms

---

### 🪙 Token Usage & Provider Cost
- **Tokens In per message (mean)**: 2195.8 tokens
- **Tokens Out per message (mean)**: 98.4 tokens
- **Total Tokens per message (mean)**: 2294.2 tokens
- **Cost in Rupees per 100 conversations at ₹100 per US Dollar**: ₹0.00 (Self-hosted local Ollama runtime — 0 API provider fee)
  - *Calculation Methodology*: Based on an average of 3 turns per conversation (6587 input tokens, 295 output tokens).
  - *Cloud API Baseline Reference*: If deployed on commercial cloud infrastructure at published rates ($0.15/1M in, $0.60/1M out at ₹100/$1), cost would be approximately **₹11.65 per 100 conversations**.

---

### 📁 Pass Rate by Category (Mean across 5 passes)

| Category | Mean Passed / Total | Pass Rate |
| :--- | :---: | :---: |
| **Arithmetic** | 5 / 7 | 71.4% |
| **Complaint** | 1 / 1 | 100.0% |
| **Escalate** | 3 / 3 | 100.0% |
| **Fact** | 3 / 3 | 100.0% |
| **Hindi** | 11 / 11 | 100.0% |
| **Hinglish** | 6 / 6 | 100.0% |
| **Injection** | 4 / 6 | 66.7% |
| **Lead** | 5 / 5 | 100.0% |
| **Multiturn** | 5 / 5 | 100.0% |
| **Out_of_scope** | 1 / 1 | 100.0% |
| **Policy** | 8 / 9 | 88.9% |
| **Price** | 5 / 5 | 100.0% |
| **Privacy** | 1 / 1 | 100.0% |
| **Unknown** | 2 / 6 | 33.3% |

---

### 🛡 Guardrail Compliance Summary (G1 - G4)
- **G1 (AI Identity)**: 100.0% compliance across first conversation turns.
- **G2 (Rupee Grounding)**: 100.0% compliance (0 ungrounded amounts).
- **G3 (Length Budget)**: 100.0% compliance (bounded within 1,200 characters, mean ~103 tokens).
- **G4 (Source Attribution)**: 100.0% auditability back to `prices.csv` or `policies.md`.
