"""Mock downstream-pipeline registry and forward stub.

Sage's downstream is a future W3 enrichment / quote-issuance step. No real
HTTP call here — ``forward_to_next_agent`` returns a metadata receipt only.
"""
from __future__ import annotations


PIPELINE_REGISTRY: dict[str, dict] = {
    "auto_pass": {
        "name": "W3 Enrichment",
        "port": 8005,
        "entry_route": "/enrich",
        "mock_url": "http://localhost:8005/enrich",
    },
    "auto_decline": {
        "name": "Decline Notice Service",
        "port": None,
        "entry_route": None,
        "mock_url": None,
    },
    "hitl_review": {
        "name": "Underwriter Review Queue",
        "port": 8006,
        "entry_route": "/queue",
        "mock_url": "http://localhost:8006/queue",
    },
}


def forward_to_next_agent(output: dict) -> dict:
    routing = output.get("routing_decision", "hitl_review")
    target = PIPELINE_REGISTRY.get(routing, {})
    return {
        "forwarded": routing != "auto_decline",
        "target": routing,
        "submission_id": output.get("submission_id"),
        "mock_url": target.get("mock_url"),
        "status": (
            "queued" if routing != "auto_decline" else "declined"
        ),
    }
