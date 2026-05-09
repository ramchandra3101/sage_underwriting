"""In-memory tamper-evident audit log for Sage."""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone


_lock = threading.Lock()
AUDIT_LOG: list[dict] = []


def _hash_payload(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _append(event_type: str, submission_id: str, payload: dict) -> dict:
    body = {
        "event_id": str(uuid.uuid4()),
        "submission_id": submission_id,
        "event_type": event_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body["sha256_hash"] = _hash_payload(body)
    with _lock:
        AUDIT_LOG.append(body)
    return body


class AuditLogger:
    """Thin handle over the module-level ``AUDIT_LOG``."""

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def log_reasoning(self, output: dict) -> None:
        _append("REASONED", output["submission_id"], output)
        outcome_map = {
            "auto_pass":    "AUTO_PASSED",
            "auto_decline": "AUTO_DECLINED",
            "hitl_review":  "HITL_TRIGGERED",
        }
        outcome = outcome_map.get(output.get("routing_decision"))
        if outcome:
            _append(outcome, output["submission_id"], output)

    def log_event(self, event_type: str, submission_id: str, payload: dict) -> None:
        _append(event_type, submission_id, payload)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def all(self) -> list[dict]:
        with _lock:
            return list(AUDIT_LOG)

    def events_for(self, submission_id: str) -> list[dict]:
        with _lock:
            return [e for e in AUDIT_LOG if e.get("submission_id") == submission_id]

    def clear(self) -> None:
        with _lock:
            AUDIT_LOG.clear()

    def verify_integrity(self) -> dict:
        with _lock:
            entries = list(AUDIT_LOG)
        if not entries:
            return {"status": "no_log", "total": 0, "valid": 0, "invalid": 0, "errors": []}
        total = valid = invalid = 0
        errors: list[dict] = []
        for i, raw in enumerate(entries, 1):
            total += 1
            entry = dict(raw)
            stored = entry.pop("sha256_hash", None)
            if _hash_payload(entry) == stored:
                valid += 1
            else:
                invalid += 1
                errors.append({
                    "line": i,
                    "submission_id": entry.get("submission_id"),
                    "error": "hash_mismatch",
                })
        return {
            "status": "ok" if invalid == 0 else "integrity_errors",
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "errors": errors,
        }
