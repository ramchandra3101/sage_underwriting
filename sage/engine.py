"""Sage's reasoning engine.

Three components:

1. ``build_vectorstore``      Splits the appetite memo into 15 paragraphs and
                              indexes them in an in-memory ChromaDB collection
                              using the local sentence-transformers model
                              ``all-MiniLM-L6-v2``. Falls back to a plain
                              keyword scorer if Chroma or the model can't load.

2. ``retrieve_passages``      Builds a query string from the submission and
                              returns the top-N CitedPassage objects.

3. ``reason``                 Either returns the canned MOCK_REASONING entry
                              or calls the LLM with the retrieved passages as
                              the only context. Output is grounding-checked
                              against the retrieved passage IDs.

4. ``evaluate_submission``    Orchestrator: retrieve -> reason -> grounding
                              -> apply confidence routing thresholds.

Modes
-----
``SAGE_LLM_MODE`` env var:
    "mock"   — return canned reasoning (default; no API key required)
    "real"   — call the LLM with retrieved context
    "hybrid" — same as "real"; retrieval was always live anyway

Provider
--------
``SAGE_LLM_PROVIDER`` env var: "openai" (default) or "anthropic".

If anything in the LLM path fails — missing key, network error, malformed
JSON — Sage silently falls back to mock and emits a warning log.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from sage.mock_data import (
    APPETITE_MEMO,
    MOCK_REASONING,
    SIC_DESCRIPTIONS,
)
from sage.models import CitedPassage, ReasoningOutput, SageInput


logger = logging.getLogger("sage.engine")


# ---------------------------------------------------------------------------
# Mode + provider lookups (read on every call so env changes pick up cleanly)
# ---------------------------------------------------------------------------

def get_llm_mode() -> str:
    return os.environ.get("SAGE_LLM_MODE", "mock").lower()


def get_llm_provider() -> str:
    return os.environ.get("SAGE_LLM_PROVIDER", "openai").lower()


# ---------------------------------------------------------------------------
# Memo split — passages keyed by id "p01"…"p15"
# ---------------------------------------------------------------------------

_PASSAGE_RE = re.compile(r"(p\d{2}):\s*(.+?)(?=\np\d{2}:|\Z)", re.DOTALL)


def _split_memo(text: str) -> list[tuple[str, str]]:
    """Return list of (id, body) tuples in document order."""
    out: list[tuple[str, str]] = []
    for match in _PASSAGE_RE.finditer(text):
        pid = match.group(1).strip()
        body = " ".join(match.group(2).split())  # collapse whitespace
        out.append((pid, body))
    return out


_PASSAGES: list[tuple[str, str]] = _split_memo(APPETITE_MEMO)
_PASSAGE_BY_ID: dict[str, str] = dict(_PASSAGES)


# ---------------------------------------------------------------------------
# Vectorstore — built once at startup, falls back gracefully
# ---------------------------------------------------------------------------

class _KeywordFallbackStore:
    """Pure-Python substring/keyword ranker — no external deps.

    Used when ChromaDB or sentence-transformers can't be loaded. Scores
    each passage by counting overlapping lowercase tokens with the query.
    """

    def __init__(self, passages: list[tuple[str, str]]) -> None:
        self._passages = passages

    def query_top_n(self, query: str, n: int) -> list[tuple[str, str, float]]:
        q_tokens = {tok for tok in re.findall(r"\w+", query.lower()) if len(tok) > 2}
        scored: list[tuple[float, str, str]] = []
        for pid, body in self._passages:
            body_tokens = re.findall(r"\w+", body.lower())
            hits = sum(1 for t in body_tokens if t in q_tokens)
            scored.append((hits, pid, body))
        scored.sort(key=lambda x: (-x[0], x[1]))
        # Return n highest-scoring entries; floats are 1/(rank+1) for downstream.
        return [(pid, body, 1.0 / (rank + 1)) for rank, (_, pid, body) in enumerate(scored[:n])]


class _ChromaStore:
    def __init__(self, collection: Any) -> None:
        self._coll = collection

    def query_top_n(self, query: str, n: int) -> list[tuple[str, str, float]]:
        result = self._coll.query(query_texts=[query], n_results=n)
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        dists = (result.get("distances") or [[]])[0] or [0.0] * len(ids)
        out: list[tuple[str, str, float]] = []
        for pid, doc, dist in zip(ids, docs, dists):
            out.append((pid, doc, float(dist)))
        return out


def build_vectorstore() -> Any:
    """Return a store object exposing ``.query_top_n(query, n)``.

    Always returns *something* — falls back to keyword matching if the
    Chroma or sentence-transformers imports/loads fail.
    """
    try:
        import chromadb
        from chromadb.utils import embedding_functions

        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
        )
        client = chromadb.Client()
        # Collections are global per client — drop & re-create for idempotency.
        try:
            client.delete_collection("sage_appetite_memo")
        except Exception:
            pass
        coll = client.create_collection(
            name="sage_appetite_memo",
            embedding_function=ef,
        )
        ids = [pid for pid, _ in _PASSAGES]
        docs = [body for _, body in _PASSAGES]
        coll.add(ids=ids, documents=docs)
        logger.info("Sage vectorstore built — %d passages indexed in ChromaDB", len(ids))
        return _ChromaStore(coll)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ChromaDB / sentence-transformers unavailable (%s); using keyword fallback", exc
        )
        return _KeywordFallbackStore(_PASSAGES)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def _build_query(submission: SageInput) -> str:
    sic_desc = SIC_DESCRIPTIONS.get(submission.sic_code, submission.sic_code)
    market = (submission.jura_result or {}).get("market", "")
    aria_routing = (submission.aria_result or {}).get("routing_decision", "")
    return (
        f"{sic_desc} {submission.state} TIV {submission.tiv:.0f} "
        f"{market} {aria_routing}"
    ).strip()


def _relevance_note(query: str, passage_text: str) -> str:
    q_tokens = {t for t in re.findall(r"\w+", query.lower()) if len(t) > 2}
    p_tokens = re.findall(r"\w+", passage_text.lower())
    matched = sorted({t for t in p_tokens if t in q_tokens})[:5]
    if not matched:
        return "Top semantic match for the submission's profile."
    return "Matches query terms: " + ", ".join(matched)


def retrieve_passages(
    submission: SageInput,
    store: Any,
    n: int = 3,
) -> list[CitedPassage]:
    query = _build_query(submission)
    hits = store.query_top_n(query, n)
    return [
        CitedPassage(
            passage_id=pid,
            text=body,
            relevance_note=_relevance_note(query, body),
        )
        for pid, body, _score in hits
    ]


# ---------------------------------------------------------------------------
# LLM call — provider-agnostic, fail-safe
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a commercial insurance underwriter at a carrier that writes "
    "small commercial P&C business. You must reason ONLY from the provided "
    "appetite memo passages. Do not use outside knowledge. Respond ONLY with "
    "valid JSON matching this exact schema:\n"
    "{\n"
    "  \"recommendation\": \"pass\" | \"decline\" | \"refer\",\n"
    "  \"confidence\": float 0.0-1.0,\n"
    "  \"rationale\": string (1-2 paragraphs),\n"
    "  \"cited_passage_ids\": list of passage IDs from context,\n"
    "  \"risk_factors\": list of strings,\n"
    "  \"questions_for_uw\": list of strings (empty if not refer)\n"
    "}\n"
    "Do not include any text outside the JSON object."
)


def _build_user_prompt(
    submission: SageInput,
    passages: list[CitedPassage],
) -> str:
    passage_lines = "\n".join(
        f"[{p.passage_id}] {p.text}" for p in passages
    )
    sub_lines = (
        f"submission_id: {submission.submission_id}\n"
        f"insured_name: {submission.insured_name}\n"
        f"state: {submission.state}\n"
        f"zip_code: {submission.zip_code}\n"
        f"sic_code: {submission.sic_code} ({SIC_DESCRIPTIONS.get(submission.sic_code, '')})\n"
        f"tiv: ${submission.tiv:,.0f}\n"
        f"credit_score_used: {submission.credit_score_used}\n"
        f"new_business: {submission.new_business}\n"
    )
    jura_dump = json.dumps(submission.jura_result or {}, indent=2)
    aria_dump = json.dumps(submission.aria_result or {}, indent=2)
    return (
        f"Appetite memo passages:\n{passage_lines}\n\n"
        f"Submission:\n{sub_lines}\n"
        f"Jura jurisdiction result:\n{jura_dump}\n\n"
        f"Aria appetite score:\n{aria_dump}\n\n"
        "Provide your underwriting recommendation."
    )


def _call_openai(system: str, user: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("SAGE_LLM_MODEL", "gpt-4o")
    resp = client.chat.completions.create(
        model=model,
        temperature=0.0,
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(system: str, user: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("SAGE_LLM_MODEL", "claude-sonnet-4-20250514")
    resp = client.messages.create(
        model=model,
        temperature=0.0,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # Concatenate all text blocks (Anthropic can return multiple blocks).
    parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "".join(parts) if parts else (resp.content[0].text if resp.content else "")


def _call_llm(system: str, user: str) -> str:
    provider = get_llm_provider()
    if provider == "anthropic":
        return _call_anthropic(system, user)
    return _call_openai(system, user)


# ---------------------------------------------------------------------------
# Grounding check
# ---------------------------------------------------------------------------

def grounding_check(
    cited_ids: list[str],
    retrieved_ids: list[str],
) -> bool:
    retrieved = set(retrieved_ids)
    for cid in cited_ids:
        if cid not in retrieved:
            logger.warning(
                "grounding_check failed: cited %r not in retrieved %s",
                cid, sorted(retrieved),
            )
            return False
    return True


# ---------------------------------------------------------------------------
# reason()
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mock_reasoning(
    submission: SageInput,
    passages: list[CitedPassage],
) -> dict:
    """Build a reasoning dict from MOCK_REASONING + the live retrieval."""
    fixture = MOCK_REASONING.get(submission.submission_id)
    if fixture is None:
        # Generic fallback — should not happen for any of the 5 seeded ids.
        return {
            "submission_id": submission.submission_id,
            "insured_name": submission.insured_name,
            "recommendation": "refer",
            "confidence": 0.5,
            "rationale": (
                "No mock reasoning fixture for this submission_id; "
                "defaulting to a HITL referral pending live LLM evaluation."
            ),
            "cited_passages": [p.model_dump() for p in passages],
            "risk_factors": ["No fixture available"],
            "questions_for_uw": ["Why was this submission routed to Sage?"],
            "grounding_check_passed": True,
        }
    return {
        "submission_id": submission.submission_id,
        "insured_name": submission.insured_name,
        "recommendation": fixture["recommendation"],
        "confidence": fixture["confidence"],
        "rationale": fixture["rationale"],
        "cited_passages": [p.model_dump() for p in passages],
        "risk_factors": list(fixture["risk_factors"]),
        "questions_for_uw": list(fixture["questions_for_uw"]),
        "grounding_check_passed": True,
    }


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE)


def _strip_json_fence(s: str) -> str:
    """Strip ``` / ```json markdown fences. Anthropic often wraps JSON in them.

    Also tries to recover by extracting the first ``{...}`` blob if neither a
    plain JSON nor a fenced JSON parses cleanly.
    """
    s = (s or "").strip()
    m = _FENCE_RE.match(s)
    if m:
        return m.group(1).strip()
    # If the response starts mid-prose, grab the outermost {...} blob.
    if s and s[0] != "{":
        a = s.find("{")
        b = s.rfind("}")
        if a != -1 and b != -1 and b > a:
            return s[a : b + 1]
    return s


def _real_reasoning(
    submission: SageInput,
    passages: list[CitedPassage],
) -> dict:
    """Call the LLM, parse JSON, run grounding. Falls back to mock on error."""
    system = _SYSTEM_PROMPT
    user = _build_user_prompt(submission, passages)
    raw = ""
    try:
        raw = _call_llm(system, user)
        parsed = json.loads(_strip_json_fence(raw))
    except Exception as exc:  # noqa: BLE001
        snippet = (raw or "").strip().replace("\n", " ")[:160]
        logger.warning(
            "LLM call failed (%s); raw=%r; falling back to mock reasoning",
            exc, snippet,
        )
        return _mock_reasoning(submission, passages)

    cited_ids = [str(c) for c in parsed.get("cited_passage_ids", [])]
    retrieved_ids = [p.passage_id for p in passages]
    grounded = grounding_check(cited_ids, retrieved_ids)

    # Build cited_passages list out of the *retrieved* passage objects,
    # preserving the LLM's ordering when it cited valid ids.
    by_id = {p.passage_id: p for p in passages}
    cited_passages: list[dict] = []
    for cid in cited_ids:
        if cid in by_id:
            cited_passages.append(by_id[cid].model_dump())
    if not cited_passages:
        cited_passages = [p.model_dump() for p in passages]

    return {
        "submission_id": submission.submission_id,
        "insured_name": submission.insured_name,
        "recommendation": parsed.get("recommendation", "refer"),
        "confidence": float(parsed.get("confidence", 0.5)),
        "rationale": parsed.get("rationale", ""),
        "cited_passages": cited_passages,
        "risk_factors": list(parsed.get("risk_factors", [])),
        "questions_for_uw": list(parsed.get("questions_for_uw", [])),
        "grounding_check_passed": grounded,
    }


def reason(
    submission: SageInput,
    passages: list[CitedPassage],
) -> dict:
    mode = get_llm_mode()
    if mode in ("real", "hybrid"):
        return _real_reasoning(submission, passages)
    return _mock_reasoning(submission, passages)


# ---------------------------------------------------------------------------
# evaluate_submission — orchestrator
# ---------------------------------------------------------------------------

def _route(recommendation: str, confidence: float, grounded: bool) -> str:
    if grounded and recommendation == "pass" and confidence >= 0.90:
        return "auto_pass"
    if grounded and recommendation == "decline" and confidence >= 0.85:
        return "auto_decline"
    return "hitl_review"


def evaluate_submission(
    submission: SageInput,
    store: Any,
    n: int = 3,
) -> ReasoningOutput:
    passages = retrieve_passages(submission, store, n=n)
    body = reason(submission, passages)
    routing = _route(
        body["recommendation"],
        body["confidence"],
        body["grounding_check_passed"],
    )
    body["routing_decision"] = routing
    body["timestamp"] = _now()
    # cited_passages came back as list[dict] — ReasoningOutput expects models.
    return ReasoningOutput(**body)
