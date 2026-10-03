#!/usr/bin/env python3
"""Deterministic generator for the bafo-round fixture.

Writes every artifact in this directory from fixed inputs and fixed Ed25519
seeds, so a rerun produces byte-identical files.

  python generate.py     regenerate every file in place
  python verify.py       check the files (does not import this module)

Dependencies: cryptography, rfc8785. Neither reference implementation is
imported here; crosscheck.py runs the artifacts through both.

The seeds below are TEST KEYS. They are published on purpose so the fixture
can be regenerated. Never reuse them.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import rfc8785
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent

PROFILE_URI = "https://spec.bidangelai.com/v0.1/"
CONTEXT_BASE = "https://spec.bidangelai.com/contexts/v0.1/"

SUPPLIER_DID = "did:web:supplier.example"
BUYER_DID = "did:web:acme.example"
SUPPLIER_KID = f"{SUPPLIER_DID}#key-1"
BUYER_KID = f"{BUYER_DID}#key-1"
APPROVER_KID = f"{BUYER_DID}#procurement-lead"

# 32-byte Ed25519 seeds (ASCII). Test keys only.
SEEDS = {
    SUPPLIER_KID: b"bafo-fixture-supplier-agent-0001",
    BUYER_KID: b"bafo-fixture-buyer-agent-0000001",
    APPROVER_KID: b"bafo-fixture-procurement-lead-01",
}

SESSION_ID = "bafo-2026-05-12-001"
MANDATE_ID = "a2cn:mandate:m-2026-05-12-0042"
OPPORTUNITY_ID = "ocds-bidangel-0001-bafo-fixture"
RECEIPT_ID = "urn:concordia:receipt:bafo-fixture-001"
PROTOCOL_VERSION = "0.3"

# Amounts in minor units (US cents), as A2CN carries them.
OFFER_TOTAL = 15_000_000
APPROVAL_THRESHOLD = 10_000_000
COMMITMENT_CEILING = 20_000_000


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def jcs(obj: Any) -> bytes:
    return rfc8785.dumps(obj)


def private_key(kid: str) -> Ed25519PrivateKey:
    seed = SEEDS[kid]
    assert len(seed) == 32, kid
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_jwk(kid: str) -> dict:
    raw = private_key(kid).public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {"kty": "OKP", "crv": "Ed25519", "x": b64url(raw), "kid": kid, "use": "sig"}


def a2cn_act_hash(act: dict) -> str:
    """A2CN §7.3.2: base64url(SHA-256(JCS(act)))."""
    return b64url(hashlib.sha256(jcs(act)).digest())


def a2cn_jws(payload: str, kid: str) -> str:
    """A2CN §7.3.2: attached JWS compact over the ASCII act hash, EdDSA."""
    header = json.dumps({"alg": "EdDSA", "kid": kid}, separators=(",", ":"), sort_keys=True)
    signing_input = f"{b64url(header.encode())}.{b64url(payload.encode())}"
    signature = private_key(kid).sign(signing_input.encode("ascii"))
    return f"{signing_input}.{b64url(signature)}"


def concordia_sign(artifact: dict, kid: str) -> str:
    """Concordia §9.2: Ed25519 over JCS of the artifact minus top-level signature."""
    signable = {k: v for k, v in artifact.items() if k != "signature"}
    return base64.urlsafe_b64encode(private_key(kid).sign(jcs(signable))).decode("ascii")


def write(path: str, obj: Any) -> None:
    target = HERE / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> None:
    # -- Procurement payload (A2A Procurement Profile) ------------------------
    opportunity = {
        "@context": CONTEXT_BASE + "opportunity.context.jsonld",
        "@type": "Opportunity",
        "perRowKey": "BAFO-FIXTURE-OPP-0001",
        "externalId": OPPORTUNITY_ID,
        "canonicalTitle": "Facility systems maintenance, base year plus four option years",
        "summary": "On-site maintenance of facility control systems. Best-and-final-offer round open.",
        "buyerRef": {
            "canonicalName": "Acme Contracting Authority",
            "countryCode": "US",
            "parentName": None,
            "legalIdentifier": None,
            "legalIdentifierScheme": None,
        },
        "opportunityType": "services",
        "opportunityTypeCode": None,
        "contractVehicle": None,
        "status": "active",
        "publishAt": "2026-04-14T13:00:00Z",
        "dueAt": "2026-05-13T17:00:00Z",
        "estimatedValueLow": 100000,
        "estimatedValueHigh": 200000,
        "currency": "USD",
        "geography": "US",
        "noticeId": "BAFO-FIXTURE-NOTICE-0001",
        "lotRef": None,
        "primaryCategoryCode": "541513",
        "primaryCategoryScheme": "naics",
    }
    requirement = {
        "@context": CONTEXT_BASE + "requirement.context.jsonld",
        "@type": "Requirement",
        "perRowKey": "BAFO-2026-05-12-SCOPE",
        "externalId": "BAFO-SOW-CLARIFICATION-3.2",
        "title": "BAFO clarification: extended maintenance window",
        "body": (
            "Supplier confirms 24x7 on-site coverage for the optional Y3 / Y4 "
            "extension years, contingent on the maintenance-window adjustment "
            "described in the original solicitation section C.5.2."
        ),
        "sectionRef": "C.5.2 / BAFO Round 1",
        "requirementType": "technical",
        "requirementTypeCode": "FAR-52.246-4",
        "subType": "narrative",
        "mandatoryFlag": True,
        "dueAt": "2026-05-13T17:00:00Z",
        "standardSchema": None,
        "valueConstraints": None,
        "evidenceNeededSummary": "Signed staffing plan and a sample on-call rotation for Y3.",
    }
    write("procurement/opportunity.json", opportunity)
    write("procurement/requirement.json", requirement)

    # -- A2CN session ---------------------------------------------------------
    session_params = {
        "deal_type": "services_procurement",
        "currency": "USD",
        "subject": f"BAFO round for {OPPORTUNITY_ID}",
        "max_rounds": 4,
        "session_timeout_seconds": 86400,
        "round_timeout_seconds": 14400,
    }
    session_init = {
        "message_type": "session_init",
        "message_id": "bafo-init-0001",
        "protocol_version": PROTOCOL_VERSION,
        "session_params": session_params,
        "initiator": {
            "organization_name": "Supplier Example LLC",
            "did": SUPPLIER_DID,
            "verification_method": SUPPLIER_KID,
            "agent_id": "supplier-bid-agent",
            "endpoint": "https://supplier.example/api/a2cn",
        },
        "initiator_mandate": {
            "mandate_type": "declared",
            "agent_id": "supplier-bid-agent",
            "principal_organization": "Supplier Example LLC",
            "principal_did": SUPPLIER_DID,
            "authorized_deal_types": ["services_procurement"],
            "max_commitment_value": COMMITMENT_CEILING,
            "max_commitment_currency": "USD",
            "valid_from": "2026-05-01T00:00:00Z",
            "valid_until": "2026-05-31T23:59:59Z",
            "scope_description": "Bid and BAFO submission for " + OPPORTUNITY_ID,
        },
    }
    buyer_mandate = {
        "mandate_type": "declared",
        "mandate_id": MANDATE_ID,
        "agent_id": "acme-sourcing-agent",
        "principal_organization": "Acme Contracting Authority",
        "principal_did": BUYER_DID,
        "authorized_deal_types": ["services_procurement"],
        "max_commitment_value": COMMITMENT_CEILING,
        "max_commitment_currency": "USD",
        "requires_human_approval_above": APPROVAL_THRESHOLD,
        "approval_operator_dids": [APPROVER_KID],
        "valid_from": "2026-05-12T00:00:00Z",
        "valid_until": "2026-05-12T23:59:59Z",
        "scope_description": "Evaluate and accept BAFO offers for " + OPPORTUNITY_ID,
    }
    session_ack = {
        "message_type": "session_ack",
        "message_id": "bafo-ack-0001",
        "session_id": SESSION_ID,
        "in_reply_to": session_init["message_id"],
        "protocol_version": PROTOCOL_VERSION,
        "session_params_accepted": {k: v for k, v in session_params.items() if k != "subject"},
        "responder": {
            "organization_name": "Acme Contracting Authority",
            "did": BUYER_DID,
            "verification_method": BUYER_KID,
            "agent_id": "acme-sourcing-agent",
            "endpoint": "https://acme.example/api/a2cn",
        },
        "responder_mandate": buyer_mandate,
        "session_created_at": "2026-05-12T14:00:00Z",
        "current_turn": "initiator",
    }
    write("a2cn/session_init.json", session_init)
    write("a2cn/session_ack.json", session_ack)

    # -- BAFO offer (supplier -> buyer) --------------------------------------
    # The procurement payload rides in terms.custom_terms, so the A2CN act hash
    # covers it.
    terms = {
        "total_value": OFFER_TOTAL,
        "currency": "USD",
        "custom_terms": {
            "a2a_procurement_profile": {
                "extension_uri": PROFILE_URI,
                "opportunity_external_id": OPPORTUNITY_ID,
                "requirement": requirement,
            }
        },
    }
    offer_act = {
        "protocol_version": PROTOCOL_VERSION,
        "session_id": SESSION_ID,
        "round_number": 1,
        "sequence_number": 1,
        "message_type": "offer",
        "sender_did": SUPPLIER_DID,
        "timestamp": "2026-05-12T14:05:00Z",
        "expires_at": "2026-05-13T17:00:00Z",
        "terms": terms,
    }
    offer_hash_a2cn = a2cn_act_hash(offer_act)
    offer = {
        "message_type": "offer",
        "message_id": "bafo-offer-0001",
        "session_id": SESSION_ID,
        "round_number": 1,
        "sequence_number": 1,
        "sender_did": SUPPLIER_DID,
        "sender_agent_id": "supplier-bid-agent",
        "sender_verification_method": SUPPLIER_KID,
        "timestamp": offer_act["timestamp"],
        "expires_at": offer_act["expires_at"],
        "terms": terms,
        "protocol_act_hash": offer_hash_a2cn,
        "protocol_act_signature": a2cn_jws(offer_hash_a2cn, SUPPLIER_KID),
    }
    write("a2cn/bafo_offer_protocol_act.json", offer_act)
    write("a2cn/bafo_offer.json", offer)

    # -- Acceptance (buyer -> supplier), held until a human approves ----------
    acceptance = {
        "message_type": "acceptance",
        "message_id": "bafo-acceptance-0001",
        "session_id": SESSION_ID,
        "in_reply_to": offer["message_id"],
        "round_number": 1,
        "sequence_number": 2,
        "accepted_offer_id": offer["message_id"],
        "accepted_protocol_act_hash": offer_hash_a2cn,
        "sender_did": BUYER_DID,
        "sender_agent_id": "acme-sourcing-agent",
        "sender_verification_method": BUYER_KID,
        "timestamp": "2026-05-12T14:20:00Z",
    }
    acceptance_act = {
        "protocol_version": PROTOCOL_VERSION,
        "session_id": SESSION_ID,
        "round_number": 1,
        "sequence_number": 2,
        "message_type": "acceptance",
        "sender_did": BUYER_DID,
        "timestamp": acceptance["timestamp"],
        "accepted_offer_id": acceptance["accepted_offer_id"],
        "accepted_protocol_act_hash": acceptance["accepted_protocol_act_hash"],
    }
    acceptance["acceptance_signature"] = a2cn_jws(a2cn_act_hash(acceptance_act), BUYER_KID)
    write("a2cn/acceptance.json", acceptance)

    # -- Concordia ApprovalReceipt -------------------------------------------
    # The offer the approver evaluated is the A2CN protocol act, canonicalized
    # whole (Concordia §9.6.4b). Same digest as A2CN's protocol_act_hash, in
    # Concordia's encoding.
    offer_digest_hex = hashlib.sha256(jcs(offer_act)).hexdigest()
    receipt = {
        "artifact_type": "ApprovalReceipt",
        "id": RECEIPT_ID,
        "issued_at": "2026-05-12T14:22:08Z",
        "expires_at": "2026-05-12T15:22:08Z",
        "approver": {"identity": APPROVER_KID, "role": "procurement_authority"},
        "scope": {
            "decision": "approve",
            "offer_hash": "sha256:" + offer_digest_hex,
            "amount": "150000.00 USD",
            "threshold_crossed": "100000.00 USD",
        },
        "references": [
            {
                "type": "negotiation_session",
                "id": f"a2cn:session:{SESSION_ID}",
                "relationship": "approves",
            },
            {"type": "mandate", "id": MANDATE_ID, "relationship": "fulfills"},
            {"type": "opportunity", "id": OPPORTUNITY_ID, "relationship": "satisfies"},
        ],
    }
    receipt["signature"] = {"alg": "Ed25519", "value": concordia_sign(receipt, APPROVER_KID)}
    write("concordia/approval_receipt.json", receipt)

    # -- Keys and expectations ------------------------------------------------
    write("keys/jwks.json", {"keys": [public_jwk(kid) for kid in SEEDS]})
    write(
        "expected.json",
        {
            "evaluation_time": "2026-05-12T14:30:00Z",
            "hashes": {
                "offer_protocol_act_sha256_hex": offer_digest_hex,
                "a2cn_protocol_act_hash": offer_hash_a2cn,
                "concordia_offer_hash": "sha256:" + offer_digest_hex,
            },
            "a2cn": {
                "on_acceptance": {
                    "state": "AWAITING_HUMAN_APPROVAL",
                    "current_turn": "responder",
                    "approval_pending_offer_id": offer["message_id"],
                    "approval_pending_offer_hash": offer_hash_a2cn,
                },
                "on_approval_receipt": {
                    "state": "COMPLETED",
                    "current_turn": "none",
                    "approval_receipt_id": RECEIPT_ID,
                },
            },
            "concordia": {"valid": True, "decision": "approve", "approver": APPROVER_KID},
            "references": [
                {
                    "id": f"a2cn:session:{SESSION_ID}",
                    "relationship": "approves",
                    "resolves_to": "a2cn/session_ack.json#/session_id",
                },
                {
                    "id": MANDATE_ID,
                    "relationship": "fulfills",
                    "resolves_to": "a2cn/session_ack.json#/responder_mandate/mandate_id",
                },
                {
                    "id": OPPORTUNITY_ID,
                    "relationship": "satisfies",
                    "resolves_to": "procurement/opportunity.json#/externalId",
                },
            ],
            "negative_cases": [
                {"name": "offer_amount_tampered", "expect": "offer_hash_mismatch"},
                {"name": "receipt_signature_tampered", "expect": "signature_invalid"},
                {"name": "evaluated_after_expiry", "expect": "expired"},
                {"name": "approver_not_in_mandate", "expect": "unauthorized_approver"},
            ],
        },
    )


if __name__ == "__main__":
    main()
