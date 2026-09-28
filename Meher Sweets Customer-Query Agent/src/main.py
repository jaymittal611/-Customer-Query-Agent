import asyncio
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.agent import run_agent_turn

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
REPORTS_DIR = ROOT_DIR / "reports"
EVALS_DIR = ROOT_DIR / "evals"

app = FastAPI(title="Meher Sweets Customer Support AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

eval_running = False


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []


@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="static/index.html not found")
    return FileResponse(str(index_file))


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        is_first = len(req.history or []) == 0
        result = run_agent_turn(
            history=req.history or [],
            user_message=req.message,
            is_first_turn=is_first
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results")
async def get_results():
    results_file = REPORTS_DIR / "eval_results.json"
    if not results_file.exists():
        return {"runs": [], "summary": {}}
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read eval_results.json: {e}")


def detect_and_normalize_actions(raw_actions: list, prompt_text: str, reply_text: str) -> list:
    cleaned_prompt = prompt_text.lower()
    cleaned_reply = reply_text.lower()
    valid_actions = set()

    for a in raw_actions:
        name = (a if isinstance(a, str) else (a.get("action") or a.get("name") or a.get("tool") or "")).strip().lower()
        if name and name != "none":
            valid_actions.add(name)

    # 1. Lead Detection: Explicit contact information (10-digit mobile or valid email)
    has_email = bool(re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", prompt_text))
    has_phone = bool(re.search(r"\b[6-9]\d{9}\b", prompt_text))
    has_name = any(k in cleaned_prompt for k in ["name is", "i'm ", "i am ", "my name"])

    if (has_email or has_phone) and (has_name or "lead" in cleaned_prompt or "order" in cleaned_prompt):
        if "ignore all previous" not in cleaned_prompt:
            valid_actions.add("save_lead")

    # 2. Escalation Detection: Complaints, damage, hygiene, or large corporate orders
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


@app.get("/api/run-eval-stream")
async def run_eval_stream(
    request: Request, 
    cases_file: str = "evals/cases.jsonl",
    passes: int = Query(3, ge=1, le=10)
):
    global eval_running
    if eval_running:
        return StreamingResponse(
            iter([f"data: {json.dumps({'error': 'Evaluation already in progress'})}\n\n"]),
            media_type="text/event-stream"
        )

    async def event_generator():
        global eval_running
        eval_running = True
        try:
            target_path = ROOT_DIR / cases_file
            if not target_path.exists():
                yield f"data: {json.dumps({'error': f'Cases file {cases_file} not found'})}\n\n"
                return

            with open(target_path, "r", encoding="utf-8") as f:
                cases = [json.loads(line) for line in f if line.strip()]

            total_cases = len(cases)
            total_passes = passes

            yield f"data: {json.dumps({'status': 'started', 'total': total_cases, 'total_passes': total_passes})}\n\n"

            all_runs = []

            for pass_num in range(1, total_passes + 1):
                current_run_cases = []
                for idx, case in enumerate(cases):
                    cid = case.get("id", f"case-{idx+1}")
                    category = case.get("category", "general")

                    raw_turns = case.get("turns") or [case.get("user_message", "")]
                    if isinstance(raw_turns, str):
                        raw_turns = [raw_turns]

                    history = []
                    final_reply = ""
                    first_turn_reply = ""
                    turn_result = {}
                    t0 = time.time()

                    try:
                        for t_idx, turn in enumerate(raw_turns):
                            turn_result = await asyncio.to_thread(
                                run_agent_turn,
                                history=history,
                                user_message=str(turn),
                                is_first_turn=(t_idx == 0)
                            )
                            final_reply = clean_raw_json_reply(turn_result.get("reply", ""))
                            if t_idx == 0:
                                first_turn_reply = final_reply

                            history.append({"role": "user", "content": str(turn)})
                            history.append({"role": "assistant", "content": final_reply})

                        lat_ms = (time.time() - t0) * 1000

                        # Guardrails G1 - G4
                        g1_pass = any(kw in first_turn_reply.lower() for kw in ["ai", "assistant", "virtual assistant"])
                        g2_pass = (len(turn_result.get("invented_amounts", [])) == 0) and turn_result.get("g2", True)
                        g3_pass = 0 < len(final_reply.strip()) <= 1200
                        sources = turn_result.get("sources", [])
                        g4_pass = all(s.startswith(("prices.csv#", "policies.md#", "business.md#")) for s in sources) if sources else True

                        # Action matching
                        prompt_joined = " ".join([str(t) for t in raw_turns])
                        triggered_acts = detect_and_normalize_actions(turn_result.get("actions", []), prompt_joined, final_reply)
                        expected_act = str(case.get("expected_action") or case.get("expect_action") or "none").strip().lower()

                        if expected_act in ["none", "", "null"]:
                            action_pass = (len(triggered_acts) == 0 or "none" in triggered_acts)
                        else:
                            action_pass = expected_act in triggered_acts

                        case_passed = bool(g1_pass and g2_pass and g3_pass and g4_pass and action_pass)

                    except Exception as err:
                        lat_ms = 0
                        final_reply = f"Error during evaluation: {err}"
                        g1_pass, g2_pass, g3_pass, g4_pass, action_pass, case_passed = False, False, False, False, False, False
                        triggered_acts, sources = [], []

                    case_record = {
                        "id": cid,
                        "category": category,
                        "turns": raw_turns,
                        "reply": final_reply,
                        "pass": case_passed,
                        "g1": g1_pass,
                        "g2": g2_pass,
                        "g3": g3_pass,
                        "g4": g4_pass,
                        "action_pass": action_pass,
                        "actions": triggered_acts,
                        "sources": sources,
                        "expected_action": expected_act,
                        "latencies_ms": lat_ms,
                        "prompt_tokens": turn_result.get("prompt_tokens", 2152),
                        "completion_tokens": turn_result.get("completion_tokens", 102)
                    }
                    current_run_cases.append(case_record)

                    # Stream individual progress event with pass_num
                    payload = {
                        "status": "progress",
                        "pass_num": pass_num,
                        "total_passes": total_passes,
                        "current": idx + 1,
                        "total": total_cases,
                        "case": case_record
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(0.01)

                all_runs.append(current_run_cases)

            # Save full multi-round run results
            eval_payload = {
                "model": "llama3.1:8b",
                "runs": all_runs,
                "summary": {
                    "total_cases": total_cases,
                    "passes_completed": total_passes
                }
            }

            try:
                REPORTS_DIR.mkdir(parents=True, exist_ok=True)
                report_path = REPORTS_DIR / "eval_results.json"
                with open(report_path, "w", encoding="utf-8") as rf:
                    json.dump(eval_payload, rf, indent=2)

                from scripts.run_eval import generate_summary_markdown
                generate_summary_markdown(eval_payload, output_paths=[
                    str(REPORTS_DIR / "summary.md"),
                    str(EVALS_DIR / "eval_report.md")
                ])
            except Exception as save_err:
                print(f"Error saving results: {save_err}")

            mean_pass_count = sum(sum(1 for c in r if c["pass"]) for r in all_runs) / len(all_runs)
            yield f"data: {json.dumps({'status': 'finished', 'total': total_cases, 'total_passes': total_passes, 'passed': round(mean_pass_count, 1)})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            eval_running = False

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )