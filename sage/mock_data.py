"""All Sage reference data as Python constants.

The appetite memo is a Python string here so runtime code reads no files.
The repo also contains ``appetite_memo.txt`` for human reference only.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Appetite memo — 15 paragraphs, p01 through p15.
# Engine.py splits on "\np\d{2}: " so keep that format intact.
# ---------------------------------------------------------------------------

APPETITE_MEMO: str = """\
p01: This carrier writes small commercial Property and Casualty business with a
focus on Tier A and Tier B classes. Preferred segments include professional
services, technology, finance, and selected light retail. Standard appetite
applies to the small commercial book; specialty lines and surplus pathways
require separate authority. The objective of this memo is to give underwriters
clear written guidance on classes, geographies, TIV bands, and authority
levels so that submissions can be triaged consistently.

p02: Tier A classes are the carrier's preferred risks. This includes the SIC
range 7000 through 7999 covering professional services, technology, computer
services, and management consulting. Finance and accounting offices are also
Tier A. Pricing is favorable, terms are standard, and underwriting authority
extends to the full small commercial limit without referral when no other
flags are present. New business and renewals in Tier A are treated equally.

p03: Tier B classes carry standard appetite with standard terms. Restaurants
under SIC 5812, grocery stores under SIC 5411, bars and taverns under SIC
5813, light manufacturing, and electrical contractors under SIC 1731 all sit
in this tier. Submissions in Tier B require complete ACORD applications and
loss runs but no senior referral when score is at or above the auto-pass
threshold. Pricing follows the standard Tier B factor table.

p04: Tier C classes warrant elevated scrutiny. Higher-hazard exposures live
here. Bars with on-premises entertainment under SIC 5813 are flagged for
liquor liability review even though the base SIC sits in Tier B. Auto
dealers, fuel stations, and similar exposures default to Tier C. Appetite is
limited and pricing is loaded; declination is the default unless the
underwriter documents a specific reason to accept.

p05: Tier X represents hard-decline classes. The carrier does not write adult
entertainment, cannabis-related operations, fireworks manufacturing or sales,
or demolition contractors. There are no exceptions to Tier X declines.
Submissions identified as Tier X must be returned to the broker with a
written decline notice citing this paragraph.

p06: Geographic restrictions follow state and ZIP-level guidance. Florida
coastal moratorium ZIPs are excluded from new business until the moratorium
lifts. California wildfire ZIPs require a FAIR Plan overlap check before any
admitted-market admission. New York applies Part 86 credit-score
restrictions; submissions where the credit score was used for pricing in NY
must be blocked at jurisdiction unless re-priced without credit data.

p07: Total Insured Value guidelines drive band selection. Micro accounts
under 250 thousand dollars are accepted with standard terms. The small band
covers 250 thousand to 1 million and is the carrier's sweet spot. The medium
band 1 to 3 million uses the same factor table with no adjustment. Large
accounts of 3 to 5 million attract a TIV load. Jumbo accounts above 5 million
require senior underwriter sign-off and frequently route to surplus lines if
the state is licensed.

p08: Liquor liability is treated as a separate gating factor. Any SIC where
on-premises consumption of alcohol is a meaningful part of the operation —
including bars under SIC 5813 and full-service restaurants that derive more
than thirty percent of receipts from alcohol — must carry a liquor liability
endorsement. The endorsement requires a separate review and is not bundled
into the base General Liability submission.

p09: New business is held to a stricter appetite standard than renewal in
Tier C classes. Where a renewal account scoring 60 might pass with documented
loss history, a new submission scoring 60 in the same class will be declined.
Renewal accounts are granted ten percent latitude on the composite score in
recognition of incumbency, prior loss data, and broker familiarity.

p10: Multi-location submissions are evaluated location by location. Each
location is scored independently for SIC tier, geography, and TIV. Combined
TIV across all locations triggers jumbo review when aggregate exceeds 5
million dollars even when no single location is jumbo on its own. Common
ownership and common operations are assumed unless the broker indicates
otherwise.

p11: Loss history requirements gate the auto-pass routing. A clean three-year
loss history is required for an automated approval. Any single loss greater
than 100 thousand dollars in the prior five years requires a full
underwriter review regardless of the composite score. Frequency-driven loss
patterns of three or more incidents per year are referred even when severity
is low.

p12: Contractor guidelines apply to SIC 1731 electrical work, SIC 1711
plumbing and HVAC, and adjacent trades. A current general liability
certificate must be on file before any quote is bound. Residential-only
contractors are preferred over commercial because residential exposures are
typically lower severity. Any contractor whose work involves fire suppression
testing or hot work routes for senior review.

p13: Restaurant guidelines apply to SIC 5812. Full-service dining is
preferred. Fast-food operations with drive-through service are downgraded one
tier due to elevated GL frequency. A fire suppression system inspection
record is required for any restaurant with TIV greater than 500 thousand.
Restaurants with on-premises liquor sales are subject to the liquor liability
guidance in paragraph 08.

p14: The Excess and Surplus pathway handles risks that fall outside the
admitted appetite. Surplus-eligible submissions route to the compliance
queue for diligent search. The diligent search requirement is three written
admitted-carrier declinations on file before binding. An Excess and Surplus
notice is sent to the broker within forty-eight hours of routing. The
carrier's E&S division writes the policy on surplus-lines paper.

p15: Underwriter authority is calibrated to the TIV. Auto-pass decisions up
to 2 million dollars sit within standard underwriter authority. Above 2
million, or whenever the submission falls in any Tier C class, senior
underwriter sign-off is required regardless of composite score. Sign-off
must be documented with a reason code in the audit trail prior to binding.
"""


# ---------------------------------------------------------------------------
# SIC code → human-readable description (used to enrich the retrieval query).
# Only the codes that appear in our 5 seed submissions are needed.
# ---------------------------------------------------------------------------

SIC_DESCRIPTIONS: dict[str, str] = {
    "5812": "restaurants eating places",
    "5411": "grocery stores",
    "5813": "bars taverns drinking places",
    "7374": "computer services data processing",
    "1731": "electrical contractors",
}


# ---------------------------------------------------------------------------
# Pre-built jura_result and aria_result dicts that mirror what the upstream
# agents actually return for each submission. Used when the pipeline calls
# Sage with the merged payload, AND when /reason/{id} is hit directly.
# ---------------------------------------------------------------------------

_JURA_BASE_TS = "2026-05-08T08:00:00+00:00"


_JURA_SUB_001 = {
    "submission_id": "SUB-001",
    "insured_name": "Rossi's Italian Kitchen",
    "market": "admitted",
    "doi_flags": [],
    "rationale": (
        "Submission cleared for admitted market in IL. No DOI flags triggered. "
        "Forwarding to appetite scoring."
    ),
    "routed_to": "aria",
    "blocked_reason": None,
    "timestamp": _JURA_BASE_TS,
    "has_block": False,
    "has_disclose": False,
    "eligible": True,
}

_JURA_SUB_002 = {
    "submission_id": "SUB-002",
    "insured_name": "Patel Food Markets",
    "market": "blocked",
    "doi_flags": [
        {
            "rule_id": "fl_moratorium",
            "rule_name": "Coastal moratorium",
            "level": "block",
            "state": "FL",
            "statutory_ref": "FL Ins Code §627.351",
            "description": "FL coastal moratorium applies to ZIP 33139",
        }
    ],
    "rationale": "Submission blocked. FL Ins Code §627.351. Statutory hold issued.",
    "routed_to": "blocked",
    "blocked_reason": "FL Ins Code §627.351",
    "timestamp": _JURA_BASE_TS,
    "has_block": True,
    "has_disclose": False,
    "eligible": False,
}

_JURA_SUB_003 = {
    "submission_id": "SUB-003",
    "insured_name": "Harbor View Lounge",
    "market": "admitted",
    "doi_flags": [
        {
            "rule_id": "ca_ab2414",
            "rule_name": "Credit score disclosure",
            "level": "disclose",
            "state": "CA",
            "statutory_ref": "CA Ins Code §1861.05",
            "description": "Credit score disclosure: rule triggered (CA Ins Code §1861.05)",
        },
        {
            "rule_id": "ca_fair_plan",
            "rule_name": "FAIR Plan overlap check",
            "level": "clear",
            "state": "CA",
            "statutory_ref": "CA Ins Code §10091",
            "description": "FAIR Plan overlap check: not triggered",
        },
    ],
    "rationale": (
        "Submission cleared for admitted market in CA. 1 disclosure flag(s) "
        "require compliance review before forwarding to appetite scoring."
    ),
    "routed_to": "aria",
    "blocked_reason": None,
    "timestamp": _JURA_BASE_TS,
    "has_block": False,
    "has_disclose": True,
    "eligible": True,
}

_JURA_SUB_004 = {
    "submission_id": "SUB-004",
    "insured_name": "Apex Business Services",
    "market": "blocked",
    "doi_flags": [
        {
            "rule_id": "ny_part86",
            "rule_name": "Credit-based pricing prohibition",
            "level": "block",
            "state": "NY",
            "statutory_ref": "NY 11 NYCRR Part 86",
            "description": "Credit-based pricing prohibition: rule triggered (NY 11 NYCRR Part 86)",
        },
        {
            "rule_id": "ny_free_look",
            "rule_name": "Free-look period notice",
            "level": "disclose",
            "state": "NY",
            "statutory_ref": "NY Ins Law §3209",
            "description": "Free-look period notice: rule triggered (NY Ins Law §3209)",
        },
    ],
    "rationale": "Submission blocked. NY 11 NYCRR Part 86. Statutory hold issued.",
    "routed_to": "blocked",
    "blocked_reason": "NY 11 NYCRR Part 86",
    "timestamp": _JURA_BASE_TS,
    "has_block": True,
    "has_disclose": True,
    "eligible": False,
}

_JURA_SUB_005 = {
    "submission_id": "SUB-005",
    "insured_name": "Greenberg Builders",
    "market": "es",
    "doi_flags": [
        {
            "rule_id": "tx_surplus_threshold",
            "rule_name": "Surplus lines eligibility",
            "level": "warn",
            "state": "TX",
            "statutory_ref": "TX Ins Code §981.004",
            "description": "Surplus lines eligibility: rule triggered (TX Ins Code §981.004)",
        }
    ],
    "rationale": (
        "Submission routed to E&S market. TIV of $6,200,000 exceeds surplus "
        "threshold for TX."
    ),
    "routed_to": "compliance_queue",
    "blocked_reason": None,
    "timestamp": _JURA_BASE_TS,
    "has_block": False,
    "has_disclose": False,
    "eligible": True,
}


_ARIA_SUB_001 = {
    "submission_id": "SUB-001",
    "insured_name": "Rossi's Italian Kitchen",
    "sic_base_score": 70,
    "sic_tier": "B",
    "state_modifier": 0,
    "tiv_band": "Small",
    "tiv_modifier": 5,
    "composite_score": 75,
    "routing_decision": "auto_pass",
    "routing_reason": (
        "SIC tier B (base 70) + state IL modifier +0 + TIV band 'Small' "
        "modifier +5 -> composite 75 ≥ 65 — clean auto-pass"
    ),
    "timestamp": _JURA_BASE_TS,
}

_ARIA_SUB_003 = {
    "submission_id": "SUB-003",
    "insured_name": "Harbor View Lounge",
    "sic_base_score": 40,
    "sic_tier": "C",
    "state_modifier": -20,
    "tiv_band": "Small",
    "tiv_modifier": 5,
    "composite_score": 25,
    "routing_decision": "auto_decline",
    "routing_reason": (
        "SIC tier C (base 40) + state CA modifier -20 + TIV band 'Small' "
        "modifier +5 -> composite 25 < 35 — auto-decline"
    ),
    "timestamp": _JURA_BASE_TS,
}


# ---------------------------------------------------------------------------
# Five named-insured submissions, fully populated with jura_result and
# (where applicable) aria_result. SUB-002, SUB-004, SUB-005 have aria=None
# because Aria is never called on those paths in normal flow.
# ---------------------------------------------------------------------------

MOCK_SUBMISSIONS: dict[str, dict] = {
    "SUB-001": {
        "submission_id": "SUB-001",
        "insured_name": "Rossi's Italian Kitchen",
        "state": "IL",
        "zip_code": "60601",
        "sic_code": "5812",
        "tiv": 450000.0,
        "credit_score_used": False,
        "new_business": True,
        "jura_result": _JURA_SUB_001,
        "aria_result": _ARIA_SUB_001,
    },
    "SUB-002": {
        "submission_id": "SUB-002",
        "insured_name": "Patel Food Markets",
        "state": "FL",
        "zip_code": "33139",
        "sic_code": "5411",
        "tiv": 820000.0,
        "credit_score_used": False,
        "new_business": True,
        "jura_result": _JURA_SUB_002,
        "aria_result": None,
    },
    "SUB-003": {
        "submission_id": "SUB-003",
        "insured_name": "Harbor View Lounge",
        "state": "CA",
        "zip_code": "90210",
        "sic_code": "5813",
        "tiv": 620000.0,
        "credit_score_used": True,
        "new_business": False,
        "jura_result": _JURA_SUB_003,
        "aria_result": _ARIA_SUB_003,
    },
    "SUB-004": {
        "submission_id": "SUB-004",
        "insured_name": "Apex Business Services",
        "state": "NY",
        "zip_code": "10001",
        "sic_code": "7374",
        "tiv": 310000.0,
        "credit_score_used": True,
        "new_business": True,
        "jura_result": _JURA_SUB_004,
        "aria_result": None,
    },
    "SUB-005": {
        "submission_id": "SUB-005",
        "insured_name": "Greenberg Builders",
        "state": "TX",
        "zip_code": "75001",
        "sic_code": "1731",
        "tiv": 6200000.0,
        "credit_score_used": False,
        "new_business": True,
        "jura_result": _JURA_SUB_005,
        "aria_result": None,
    },
}


# ---------------------------------------------------------------------------
# Mock reasoning fixtures. ``cited_passages`` here is just the list of
# passage IDs the LLM "would" cite — engine.py replaces this with the live
# ChromaDB results before returning.
# ---------------------------------------------------------------------------

MOCK_REASONING: dict[str, dict] = {
    "SUB-001": {
        "recommendation": "pass",
        "confidence": 0.92,
        "rationale": (
            "Rossi's Italian Kitchen is a Tier B restaurant (SIC 5812) in IL "
            "with TIV $450K and an Aria composite score of 75. Per the "
            "appetite memo, Tier B restaurants are within standard appetite "
            "with standard terms, and the TIV is below the $500K fire "
            "suppression inspection trigger. No DOI flags from Jura. "
            "Recommend a clean auto-pass."
        ),
        "cited_passage_ids": ["p03", "p13"],
        "risk_factors": [
            "Fire suppression system inspection required for TIV > $500K — "
            "not triggered at $450K TIV",
            "Standard Tier B restaurant risk — no aggravating factors",
        ],
        "questions_for_uw": [],
    },
    "SUB-002": {
        "recommendation": "decline",
        "confidence": 0.99,
        "rationale": (
            "Patel Food Markets is in a Florida coastal moratorium ZIP. "
            "Jurisdiction was blocked by Jura under FL Ins Code §627.351. "
            "The appetite memo excludes Florida coastal moratorium ZIPs from "
            "new business. There is no underwriting path that overrides a "
            "statutory hold; recommend decline."
        ),
        "cited_passage_ids": ["p06"],
        "risk_factors": [
            "FL coastal moratorium ZIP — statutory block at jurisdiction",
        ],
        "questions_for_uw": [],
    },
    "SUB-003": {
        "recommendation": "decline",
        "confidence": 0.88,
        "rationale": (
            "Harbor View Lounge is a Tier C bar (SIC 5813) in California "
            "with credit-score-used pricing and a low Aria composite of 25. "
            "Tier C bars require liquor liability review, CA wildfire ZIPs "
            "require FAIR Plan overlap, and the composite is well below the "
            "auto-decline threshold. Multiple aggravating factors align with "
            "the carrier's decline guidance for Tier C drinking places."
        ),
        "cited_passage_ids": ["p04", "p06", "p08"],
        "risk_factors": [
            "Tier C class — bars with on-premises alcohol (SIC 5813)",
            "CA wildfire ZIP disclosure required",
            "Liquor liability endorsement review required",
            "Aria composite score 25 — below auto-decline threshold",
        ],
        "questions_for_uw": [
            "Is a liquor liability endorsement in place?",
            "Has CA FAIR Plan overlap been confirmed?",
        ],
    },
    "SUB-004": {
        "recommendation": "decline",
        "confidence": 0.99,
        "rationale": (
            "Apex Business Services was blocked by Jura under NY 11 NYCRR "
            "Part 86 because credit score was used in pricing. The appetite "
            "memo prohibits NY submissions where credit score is used unless "
            "re-priced without credit data. No underwriting override exists; "
            "recommend decline pending re-submission."
        ),
        "cited_passage_ids": ["p06"],
        "risk_factors": [
            "NY Part 86 credit score ban — blocked at jurisdiction",
        ],
        "questions_for_uw": [],
    },
    "SUB-005": {
        "recommendation": "refer",
        "confidence": 0.75,
        "rationale": (
            "Greenberg Builders is an electrical contractor (SIC 1731) in "
            "Texas with TIV $6.2M which exceeds the $5M jumbo threshold. "
            "Jura routed to E&S surplus-lines pathway. Per the memo, jumbo "
            "accounts require senior UW sign-off, contractors require a "
            "current GL certificate, and the E&S diligent search needs three "
            "admitted-carrier declinations. Refer to senior underwriter."
        ),
        "cited_passage_ids": ["p07", "p12", "p14"],
        "risk_factors": [
            "TIV $6.2M exceeds jumbo threshold — senior UW sign-off required",
            "E&S routing — surplus lines pathway",
            "Contractor risk requires valid GL certificate on file",
        ],
        "questions_for_uw": [
            "Is a current general liability certificate available?",
            "Is this residential or commercial electrical work?",
            "Have 3 admitted carrier declinations been obtained for E&S "
            "diligent search?",
        ],
    },
}
