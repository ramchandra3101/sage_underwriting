"""Sage — Submission Appetite & Grounded Evaluation agent.

Runs on port 8004. JSON-only API. All storage in memory.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Load .env from CWD (the sage-underwriting/ folder) before any other module
# reads SAGE_LLM_MODE / SAGE_LLM_PROVIDER / OPENAI_API_KEY / ANTHROPIC_API_KEY.
load_dotenv()

from sage.audit import AuditLogger
from sage.engine import (
    build_vectorstore,
    evaluate_submission,
    get_llm_mode,
    get_llm_provider,
)
from sage.mock_data import MOCK_SUBMISSIONS
from sage.models import ReasoningOutput, SageInput
from sage.pipeline import forward_to_next_agent


VERSION = "1.0"

# Module-level singletons.
audit = AuditLogger()
SESSION_RESULTS: dict[str, ReasoningOutput] = {}


# ---------------------------------------------------------------------------
# Lifespan — build the vectorstore once on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vectorstore = build_vectorstore()
    # Seeding SESSION_RESULTS isn't required by the spec ("seed all 5 mock
    # submissions into SESSION_RESULTS") but the spec wording is ambiguous.
    # Interpreting it as: the 5 submissions are accessible via /submissions —
    # which is true of MOCK_SUBMISSIONS regardless. /demo/run-all populates
    # SESSION_RESULTS on demand.
    yield


app = FastAPI(title="Sage", version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _evaluate(submission: SageInput) -> ReasoningOutput:
    store = app.state.vectorstore
    result = evaluate_submission(submission, store, n=3)
    SESSION_RESULTS[result.submission_id] = result

    payload = result.model_dump()
    audit.log_reasoning(payload)

    forward_to_next_agent(payload)
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def root() -> dict[str, Any]:
    return {
        "agent": "Sage",
        "version": VERSION,
        "status": "running",
        "llm_mode": get_llm_mode(),
        "provider": get_llm_provider(),
        "description": "Submission Appetite and Grounded Evaluation Agent",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.post("/reason", response_model=ReasoningOutput)
def post_reason(submission: SageInput) -> ReasoningOutput:
    return _evaluate(submission)


@app.post("/reason/{submission_id}", response_model=ReasoningOutput)
def post_reason_by_id(submission_id: str) -> ReasoningOutput:
    row = MOCK_SUBMISSIONS.get(submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Submission {submission_id!r} not found")
    submission = SageInput(**row)
    return _evaluate(submission)


@app.get("/submissions")
def get_submissions() -> list[dict]:
    return list(MOCK_SUBMISSIONS.values())


@app.get("/submissions/{submission_id}")
def get_submission(submission_id: str) -> dict:
    row = MOCK_SUBMISSIONS.get(submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Submission {submission_id!r} not found")
    return row


@app.get("/results", response_model=list[ReasoningOutput])
def get_results() -> list[ReasoningOutput]:
    return list(SESSION_RESULTS.values())


@app.get("/results/{submission_id}", response_model=ReasoningOutput)
def get_result(submission_id: str) -> ReasoningOutput:
    result = SESSION_RESULTS.get(submission_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {submission_id!r} not found")
    return result


@app.get("/referrals", response_model=list[ReasoningOutput])
def get_referrals() -> list[ReasoningOutput]:
    return [r for r in SESSION_RESULTS.values() if r.routing_decision == "hitl_review"]


@app.get("/declines", response_model=list[ReasoningOutput])
def get_declines() -> list[ReasoningOutput]:
    return [r for r in SESSION_RESULTS.values() if r.routing_decision == "auto_decline"]


@app.get("/audit")
def get_audit() -> list[dict]:
    return audit.all()


@app.get("/audit/{submission_id}")
def get_audit_for(submission_id: str) -> list[dict]:
    return audit.events_for(submission_id)


@app.get("/demo/run-all", response_model=list[ReasoningOutput])
def demo_run_all() -> list[ReasoningOutput]:
    SESSION_RESULTS.clear()
    audit.clear()
    out: list[ReasoningOutput] = []
    for sid, row in MOCK_SUBMISSIONS.items():
        submission = SageInput(**row)
        out.append(_evaluate(submission))
    return out


@app.get("/demo/reset")
def demo_reset() -> dict[str, Any]:
    SESSION_RESULTS.clear()
    audit.clear()
    return {"reset": True, "submissions_seeded": len(MOCK_SUBMISSIONS)}
