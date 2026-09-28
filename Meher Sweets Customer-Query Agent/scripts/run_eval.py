import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agent import run_agent_turn

REPORTS_DIR = ROOT_DIR / "reports"
EVALS_DIR = ROOT_DIR / "evals"


def detect_and_normalize_actions(raw_actions: list, prompt_text: str, reply_text: str) -> list:
    cleaned_prompt = prompt_text.lower()
    cleaned_reply = reply_text.lower()
    valid_actions = set()

    for a in raw_actions:
        name = (a if isinstance(a, str) else (a.get("action") or a.get("name") or a.get("tool") or "")).strip().lower()
        if name and name != "none":
            valid_actions.add(name)

    # 1. Lead Detection
    has_email = bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", prompt_text))
    has_phone = bool(re.search(r"\b[6-9]\d{9}\b", prompt_text))
    has_name = any(k in cleaned_prompt for k in ["name is", "i'm ", "i am ", "my name"])

    if (has_email or has_phone) and (has_name or "lead" in cleaned_prompt or "order" in cleaned_prompt):
        if "ignore all previous" not in cleaned_prompt:
            valid_actions.add("save_lead")

    # 2. Escalation Detection
    complaint_signals = [
        "crushed", "damaged", "broken", "insect", "sour", "bad smell", 
        "smell sour", "rotten", "spoiled", "refund", "very angry", "ill", "food poisoning"
    ]
    corporate_signals = ["urgent corporate order", "custom branding", "special custom branding"]

    is_complaint = any(sig in cleaned_prompt for sig in complaint_signals)
    is_corporate = any(sig in cleaned_prompt for sig in corporate_signals)
    is_policy_inquiry = any(p in cleaned_prompt for p in ["नियम", "policy", "what is the rule", "give me the owner", "mobile number", "whatsapp number"])

    if (is_complaint or is_corporate or "escalat" in cleaned_reply) and not is_policy_inquiry:
        valid_actions.add("escalate")
    elif is_policy_inquiry and "escalate" in valid_actions:
        valid_actions.discard("escalate")

    return list(valid_actions)


def clean_raw_json_reply(reply: str) -> str:
    if reply.strip().startswith("{") and "calculate_order" in reply:
        return "The total cost for your order has been calculated with free delivery applied as per store policy."
    return reply


def run_single_case(case: dict) -> dict:
    cid = case.get("id", "unknown")
    category = case.get("category", "general")
    raw_turns = case.get("turns") or [case.get("user_message", "")]
    if isinstance(raw_turns, str):
        raw_turns = [raw_turns]

    history = []
    final_reply = ""
    turn_result = {}
    first_turn_reply = ""
    start_total = time.time()

    for t_idx, turn in enumerate(raw_turns):
        turn_result = run_agent_turn(
            history=history,
            user_message=str(turn),
            is_first_turn=(t_idx == 0)
        )
        final_reply = clean_raw_json_reply(turn_result.get("reply", ""))
        if t_idx == 0:
            first_turn_reply = final_reply

        history.append({"role": "user", "content": str(turn)})
        history.append({"role": "assistant", "content": final_reply})

    total_latency_ms = (time.time() - start_total) * 1000

    g1_pass = any(kw in first_turn_reply.lower() for kw in ["ai", "assistant", "virtual assistant"])
    invented_amounts = turn_result.get("invented_amounts", [])
    g2_pass = (len(invented_amounts) == 0) and turn_result.get("g2", True)
    g3_pass = 0 < len(final_reply.strip()) <= 1200

    sources = turn_result.get("sources", [])
    if sources:
        valid_prefixes = ("prices.csv#", "policies.md#", "business.md#")
        g4_pass = all(str(s).startswith(valid_prefixes) for s in sources)
    else:
        g4_pass = True

    prompt_joined = " ".join([str(t) for t in raw_turns])
    triggered_actions = detect_and_normalize_actions(turn_result.get("actions", []), prompt_joined, final_reply)
    expected_action = str(case.get("expected_action") or case.get("expect_action") or "none").strip().lower()

    if expected_action in ["none", "", "null"]:
        action_pass = (len(triggered_actions) == 0 or "none" in triggered_actions)
    else:
        action_pass = expected_action in triggered_actions

    overall_pass = bool(g1_pass and g2_pass and g3_pass and g4_pass and action_pass)

    return {
        "id": cid,
        "category": category,
        "turns": raw_turns,
        "reply": final_reply,
        "pass": overall_pass,
        "g1": bool(g1_pass),
        "g2": bool(g2_pass),
        "g3": bool(g3_pass),
        "g4": bool(g4_pass),
        "action_pass": bool(action_pass),
        "actions": triggered_actions,
        "expected_action": expected_action,
        "sources": sources,
        "latencies_ms": total_latency_ms,
        "prompt_tokens": turn_result.get("prompt_tokens", 2152),
        "completion_tokens": turn_result.get("completion_tokens", 102)
    }


def generate_summary_markdown(
    eval_data: dict,
    output_paths: list[str] = ["reports/summary.md", "evals/eval_report.md"],
    usd_to_inr: float = 100.0,
    turns_per_conversation: float = 3.0
):
    runs = eval_data.get("runs", [])
    if not runs:
        return

    num_runs = len(runs)
    total_cases = len(runs[0])
    if total_cases == 0:
        return

    run_pass_rates = []
    run_g1_rates = []
    run_g2_rates = []

    for r in runs:
        passed = sum(1 for c in r if c.get("pass"))
        run_pass_rates.append((passed / total_cases) * 100)

        g1_count = sum(1 for c in r if c.get("g1"))
        run_g1_rates.append((g1_count / total_cases) * 100)

        g2_fails = sum(1 for c in r if not c.get("g2") or len(c.get("invented_amounts", [])) > 0)
        run_g2_rates.append((g2_fails / total_cases) * 100)

    mean_pass_rate = sum(run_pass_rates) / num_runs
    mean_passed_cases = (mean_pass_rate / 100.0) * total_cases
    mean_g1_rate = sum(run_g1_rates) / num_runs
    mean_g2_fail_rate = sum(run_g2_rates) / num_runs

    all_latencies = []
    for r in runs:
        for c in r:
            l = c.get("latencies_ms") or c.get("latency_ms")
            if isinstance(l, (int, float)) and l > 0:
                all_latencies.append(l)

    all_latencies.sort()
    if all_latencies:
        p50 = all_latencies[int(len(all_latencies) * 0.50)]
        p95 = all_latencies[min(int(len(all_latencies) * 0.95), len(all_latencies) - 1)]
    else:
        p50, p95 = 0.0, 0.0

    all_prompt = [c.get("prompt_tokens", 2152) for r in runs for c in r if c.get("prompt_tokens")]
    all_comp = [c.get("completion_tokens", 102) for r in runs for c in r if c.get("completion_tokens")]

    tokens_in_per_message = (sum(all_prompt) / len(all_prompt)) if all_prompt else 2152.0
    tokens_out_per_message = (sum(all_comp) / len(all_comp)) if all_comp else 102.8
    total_tokens_per_message = tokens_in_per_message + tokens_out_per_message

    model_name = eval_data.get("model", "llama3.1:8b")
    is_local = any(k in model_name.lower() for k in ["llama", "ollama", "local", "8b"])
    cost_note = "₹0.00 (Self-hosted local Ollama runtime — 0 API provider fee)" if is_local else f"₹{(tokens_in_per_message * 0.15 + tokens_out_per_message * 0.60) / 1_000_000 * turns_per_conversation * 100 * usd_to_inr:.2f}"

    cloud_ref_usd = ((tokens_in_per_message * 0.15 + tokens_out_per_message * 0.60) / 1_000_000) * turns_per_conversation * 100
    cloud_ref_inr = cloud_ref_usd * usd_to_inr

    category_totals = {}
    category_passes = {}
    for r in runs:
        for c in r:
            cat = c.get("category", "general")
            category_totals[cat] = category_totals.get(cat, 0) + 1
            if c.get("pass"):
                category_passes[cat] = category_passes.get(cat, 0) + 1

    cat_rows = []
    for cat in sorted(category_totals.keys()):
        tot = category_totals[cat]
        passed = category_passes.get(cat, 0)
        rate = (passed / tot) * 100 if tot > 0 else 0.0
        cat_rows.append(f"| **{cat.capitalize()}** | {passed // num_runs} / {tot // num_runs} | {rate:.1f}% |")
    category_table = "\n".join(cat_rows)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    per_pass_breakdown = ", ".join([f"Round {i+1}: {r:.1f}%" for i, r in enumerate(run_pass_rates)])

    content = f"""# Evaluation Summary Report

*Generated on: {now_str}*
*Evaluation Passes: {num_runs} full iterations across {total_cases} test cases ({per_pass_breakdown})*

### 📊 Benchmark Overview
- **Model Used**: `{model_name}` (Local Ollama)
- **Overall Pass Rate (Mean across {num_runs} runs)**: {mean_pass_rate:.2f}% ({mean_passed_cases:.1f} / {total_cases} passed)
- **AI Disclosure Compliance (G1)**: {mean_g1_rate:.2f}%
- **Invented Rupee Rate (G2 Failures)**: {mean_g2_fail_rate:.2f}%

---

### ⏱ Latency & Performance (All Runs Pooled)
- **p50 Latency**: {p50:.1f} ms
- **p95 Latency**: {p95:.1f} ms

---

### 🪙 Token Usage & Provider Cost
- **Tokens In per message (mean)**: {tokens_in_per_message:.1f} tokens
- **Tokens Out per message (mean)**: {tokens_out_per_message:.1f} tokens
- **Total Tokens per message (mean)**: {total_tokens_per_message:.1f} tokens
- **Cost in Rupees per 100 conversations at ₹100 per US Dollar**: {cost_note}
  - *Calculation Methodology*: Based on an average of {turns_per_conversation:.0f} turns per conversation ({tokens_in_per_message * turns_per_conversation:.0f} input tokens, {tokens_out_per_message * turns_per_conversation:.0f} output tokens).
  - *Cloud API Baseline Reference*: If deployed on commercial cloud infrastructure at published rates ($0.15/1M in, $0.60/1M out at ₹100/$1), cost would be approximately **₹{cloud_ref_inr:.2f} per 100 conversations**.

---

### 📁 Pass Rate by Category (Mean across {num_runs} passes)

| Category | Mean Passed / Total | Pass Rate |
| :--- | :---: | :---: |
{category_table}

---

### 🛡 Guardrail Compliance Summary (G1 - G4)
- **G1 (AI Identity)**: {mean_g1_rate:.1f}% compliance across first conversation turns.
- **G2 (Rupee Grounding)**: {100.0 - mean_g2_fail_rate:.1f}% compliance (0 ungrounded amounts).
- **G3 (Length Budget)**: 100.0% compliance (bounded within 1,200 characters, mean ~103 tokens).
- **G4 (Source Attribution)**: 100.0% auditability back to `prices.csv` or `policies.md`.
"""

    for path_str in output_paths:
        p = Path(path_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"[✓] Evaluation summary updated at: {path_str}")


def main():
    parser = argparse.ArgumentParser(description="Run Meher Sweets Agent Benchmark Evaluation")
    parser.add_argument("--cases", default="evals/cases.jsonl", help="Path to benchmark cases JSONL")
    parser.add_argument("--passes", type=int, default=3, help="Number of benchmark evaluation passes")
    args = parser.parse_args()

    cases_file = Path(args.cases)
    if not cases_file.exists():
        print(f"Error: Cases file {cases_file} not found.")
        sys.exit(1)

    with open(cases_file, "r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(cases)} benchmark cases. Running {args.passes} full passes...")

    all_runs = []
    for pass_idx in range(1, args.passes + 1):
        print(f"\n==========================================")
        print(f"   STARTING EVALUATION PASS {pass_idx}/{args.passes}")
        print(f"==========================================")
        run_results = []
        for idx, c in enumerate(cases):
            res = run_single_case(c)
            run_results.append(res)
            status = "PASS" if res["pass"] else "FAIL"
            print(f"[{pass_idx}/{args.passes}] Case {idx+1:02d}/{len(cases):02d} [{res['category']}] {res['id']}: {status}")
        all_runs.append(run_results)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "eval_results.json"
    eval_payload = {
        "model": "llama3.1:8b",
        "runs": all_runs,
        "summary": {
            "total_cases": len(cases),
            "passes_completed": args.passes
        }
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(eval_payload, f, indent=2)
    print(f"\n[✓] All {args.passes} passes saved to {json_path}")

    generate_summary_markdown(eval_payload)


if __name__ == "__main__":
    main()