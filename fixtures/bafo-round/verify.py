#!/usr/bin/env python3
"""Verifier for the bafo-round fixture.

Reads the files in this directory and checks them against expected.json. It
shares no code with generate.py and imports neither reference implementation.

  python verify.py     exit 0 when every check passes, 1 otherwise

Dependencies: cryptography, rfc8785.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HERE = Path(__file__).resolve().parent
CONTEXTS = HERE.parent.parent / "procurement-profile" / "contexts" / "v0.1"

# A2CN §7.3.1: the fields a signed act's signature covers, per act type.
ACT_HEADER = (
    "protocol_version",
    "session_id",
    "round_number",
    "sequence_number",
    "message_type",
    "sender_did",
    "timestamp",
)
ACT_PAYLOAD = {
    "offer": ("expires_at", "terms"),
    "acceptance": ("accepted_offer_id", "accepted_protocol_act_hash"),
}

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> bool:
    results.append((bool(ok), label))
    return bool(ok)


def load(path: str) -> Any:
    return json.loads((HERE / path).read_text())


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def minor_units(amount: str) -> tuple[int, str]:
    """'150000.00 USD' -> (15000000, 'USD')."""
    number, currency = amount.split(" ")
    whole, _, fraction = number.partition(".")
    return int(whole) * 100 + int((fraction + "00")[:2]), currency


def key_for(jwks: dict, kid: str) -> Ed25519PublicKey | None:
    for jwk in jwks["keys"]:
        if jwk["kid"] == kid and jwk["kty"] == "OKP" and jwk["crv"] == "Ed25519":
            return Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))
    return None


def rebuild_act(message: dict, protocol_version: str) -> dict:
    fields = ACT_HEADER + ACT_PAYLOAD[message["message_type"]]
    return {
        name: message.get(name, protocol_version) if name == "protocol_version" else message[name]
        for name in fields
    }


def act_hash(act: dict) -> str:
    return b64url(hashlib.sha256(rfc8785.dumps(act)).digest())


def verify_jws(token: str, jwks: dict) -> str | None:
    """Return the JWS payload string when the signature verifies, else None."""
    try:
        protected, payload, signature = token.split(".")
        header = json.loads(b64url_decode(protected))
        key = key_for(jwks, header.get("kid", ""))
        if header.get("alg") != "EdDSA" or key is None:
            return None
        key.verify(b64url_decode(signature), f"{protected}.{payload}".encode("ascii"))
        return b64url_decode(payload).decode("ascii")
    except (InvalidSignature, ValueError, KeyError):
        return None


def verify_receipt(
    receipt: dict, offer_act: dict, mandate: dict, jwks: dict, now: datetime
) -> str:
    """Return 'valid' or the first failure, in the order a verifier would hit it."""
    signable = {k: v for k, v in receipt.items() if k != "signature"}
    key = key_for(jwks, receipt["approver"]["identity"])
    if key is None or receipt["signature"]["alg"] != "Ed25519":
        return "signature_invalid"
    try:
        key.verify(
            base64.urlsafe_b64decode(receipt["signature"]["value"]), rfc8785.dumps(signable)
        )
    except (InvalidSignature, ValueError):
        return "signature_invalid"
    if not parse_time(receipt["issued_at"]) <= now <= parse_time(receipt["expires_at"]):
        return "expired"
    if receipt["approver"]["identity"] not in mandate.get("approval_operator_dids", []):
        return "unauthorized_approver"
    expected = "sha256:" + hashlib.sha256(rfc8785.dumps(offer_act)).hexdigest()
    if receipt["scope"]["offer_hash"] != expected:
        return "offer_hash_mismatch"
    return "valid"


def context_terms(name: str) -> set[str]:
    context = json.loads((CONTEXTS / name).read_text())["@context"]
    return {term for term in context if not term.startswith("@")}


def main() -> int:
    expected = load("expected.json")
    jwks = load("keys/jwks.json")
    session_init = load("a2cn/session_init.json")
    session_ack = load("a2cn/session_ack.json")
    offer = load("a2cn/bafo_offer.json")
    offer_act = load("a2cn/bafo_offer_protocol_act.json")
    acceptance = load("a2cn/acceptance.json")
    receipt = load("concordia/approval_receipt.json")
    opportunity = load("procurement/opportunity.json")
    requirement = load("procurement/requirement.json")

    now = parse_time(expected["evaluation_time"])
    version = session_ack["protocol_version"]
    session_id = session_ack["session_id"]
    mandate = session_ack["responder_mandate"]
    hashes = expected["hashes"]

    # 1. Offer hash: one digest, two encodings.
    digest = hashlib.sha256(rfc8785.dumps(offer_act)).digest()
    check(digest.hex() == hashes["offer_protocol_act_sha256_hex"], "offer act digest matches expected.json")
    check(b64url(digest) == hashes["a2cn_protocol_act_hash"], "A2CN protocol_act_hash is base64url of that digest")
    check("sha256:" + digest.hex() == hashes["concordia_offer_hash"], "Concordia offer_hash is sha256:hex of that digest")

    # 2. A2CN offer: rebuilt from its own fields, signed by the supplier.
    rebuilt = rebuild_act(offer, version)
    check(rebuilt == offer_act, "offer rebuilds to the stored protocol act")
    check(act_hash(rebuilt) == offer["protocol_act_hash"], "offer states the hash of its rebuilt act")
    check(verify_jws(offer["protocol_act_signature"], jwks) == offer["protocol_act_hash"], "offer signature verifies over its act hash")
    check(offer["sender_did"] == session_init["initiator"]["did"], "offer is sent by the session initiator")

    # 3. A2CN acceptance: bound to the offer, signed by the buyer agent.
    check(acceptance["accepted_protocol_act_hash"] == offer["protocol_act_hash"], "acceptance names the offer's act hash")
    check(acceptance["accepted_offer_id"] == offer["message_id"], "acceptance names the offer's message id")
    check(verify_jws(acceptance["acceptance_signature"], jwks) == act_hash(rebuild_act(acceptance, version)), "acceptance signature verifies over its act hash")
    check(acceptance["sender_did"] == session_ack["responder"]["did"], "acceptance is sent by the session responder")

    # 4. Threshold crossing on the accepting party's mandate.
    total = offer["terms"]["total_value"]
    check(total > mandate["requires_human_approval_above"], "offer total exceeds the buyer mandate's approval threshold")
    check(total <= mandate["max_commitment_value"], "offer total is within the buyer mandate's commitment ceiling")
    paused = expected["a2cn"]["on_acceptance"]
    check(paused["approval_pending_offer_hash"] == offer["protocol_act_hash"], "expected pause is bound to the offer's act hash")

    # 5. Concordia ApprovalReceipt.
    scope = receipt["scope"]
    check(verify_receipt(receipt, offer_act, mandate, jwks, now) == "valid", "receipt verifies: signature, validity window, approver, offer hash")
    check(scope["decision"] == expected["concordia"]["decision"], "receipt decision matches expected.json")
    check(minor_units(scope["amount"]) == (total, offer["terms"]["currency"]), "receipt amount equals the offer total")
    check(minor_units(scope["threshold_crossed"])[0] == mandate["requires_human_approval_above"], "receipt threshold equals the mandate threshold")
    check(receipt["id"] == expected["a2cn"]["on_approval_receipt"]["approval_receipt_id"], "receipt id is the one A2CN records")

    # 6. references[]: every entry resolves inside the fixture.
    targets = {
        "negotiation_session": {session_id, f"a2cn:session:{session_id}"},
        "mandate": {mandate["mandate_id"]},
        "opportunity": {opportunity["externalId"]},
    }
    relationships = {"negotiation_session": "approves", "mandate": "fulfills", "opportunity": "satisfies"}
    check(len(receipt["references"]) == len(expected["references"]), "receipt carries the expected number of references")
    for ref in receipt["references"]:
        kind = ref["type"]
        check(ref["id"] in targets.get(kind, set()), f"reference {kind} resolves ({ref['id']})")
        check(ref["relationship"] == relationships.get(kind), f"reference {kind} uses '{relationships.get(kind)}'")

    # 7. Procurement payload.
    carried = offer["terms"]["custom_terms"]["a2a_procurement_profile"]
    check(carried["requirement"] == requirement, "offer carries the requirement fragment unchanged")
    check(carried["opportunity_external_id"] == opportunity["externalId"], "offer names the opportunity the receipt satisfies")
    for name, fragment in (("requirement", requirement), ("opportunity", opportunity)):
        terms = context_terms(f"{name}.context.jsonld")
        unknown = [key for key in fragment if not key.startswith("@") and key not in terms]
        check(not unknown, f"{name} fragment uses only terms from its v0.1 context" + (f" (unknown: {unknown})" if unknown else ""))
        check(fragment["@type"] in terms, f"{name} fragment @type is the context's class term")

    # 8. Negative cases: each must fail for the stated reason.
    def tampered_offer() -> str:
        act = copy.deepcopy(offer_act)
        act["terms"]["total_value"] = 9_900_000
        return verify_receipt(receipt, act, mandate, jwks, now)

    def tampered_signature() -> str:
        bad = copy.deepcopy(receipt)
        bad["scope"]["amount"] = "15000.00 USD"
        return verify_receipt(bad, offer_act, mandate, jwks, now)

    def after_expiry() -> str:
        return verify_receipt(receipt, offer_act, mandate, jwks, parse_time("2026-05-12T15:22:09Z"))

    def approver_removed() -> str:
        other = dict(mandate, approval_operator_dids=["did:web:acme.example#someone-else"])
        return verify_receipt(receipt, offer_act, other, jwks, now)

    cases = {
        "offer_amount_tampered": tampered_offer,
        "receipt_signature_tampered": tampered_signature,
        "evaluated_after_expiry": after_expiry,
        "approver_not_in_mandate": approver_removed,
    }
    for case in expected["negative_cases"]:
        outcome = cases[case["name"]]()
        check(outcome == case["expect"], f"negative case {case['name']} fails with {case['expect']} (got {outcome})")

    failed = [label for ok, label in results if not ok]
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    print(f"\n{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
