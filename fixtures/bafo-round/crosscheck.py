#!/usr/bin/env python3
"""Run the bafo-round fixture through both reference implementations.

verify.py checks the fixture against the specifications with no reference code.
This script is the other half: it feeds the same files to the Concordia and
A2CN Python reference implementations and reports what each one does.

  python crosscheck.py --concordia PATH --a2cn PATH

PATH is a checkout of eriknewton/concordia-protocol and of a2cn-protocol/A2CN.
README.md records the commits this was last run against and the results.

Exit 0 when every outcome matches the one recorded below. That includes the
known divergences: each is pinned to the behaviour observed today, so the day
one is resolved upstream this script exits 1 and the fixture gets updated.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

outcomes: list[tuple[bool, str, str]] = []


def record(label: str, got: str, expect: str) -> None:
    outcomes.append((got == expect, label, f"got {got}, expected {expect}"))


def load(path: str):
    return json.loads((HERE / path).read_text())


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def did_document(did: str, jwks: dict) -> dict:
    methods = [
        {
            "id": jwk["kid"],
            "type": "JsonWebKey2020",
            "controller": did,
            "publicKeyJwk": {k: jwk[k] for k in ("kty", "crv", "x")},
        }
        for jwk in jwks["keys"]
        if jwk["kid"].startswith(did + "#")
    ]
    ids = [m["id"] for m in methods]
    return {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": did,
        "verificationMethod": methods,
        "authentication": ids,
        "assertionMethod": ids,
    }


def run_concordia(expected: dict, jwks: dict) -> None:
    from concordia.approval_receipt import verify_approval_receipt

    receipt = load("concordia/approval_receipt.json")
    offer_act = load("a2cn/bafo_offer_protocol_act.json")
    now = datetime.fromisoformat(expected["evaluation_time"].replace("Z", "+00:00"))
    jwk = next(k for k in jwks["keys"] if k["kid"] == receipt["approver"]["identity"])

    result = verify_approval_receipt(
        receipt, offer_act, now=now, issuer_public_key=b64url_decode(jwk["x"])
    )
    record(
        "Concordia verify_approval_receipt accepts the receipt",
        "valid" if result.valid else f"invalid:{result.failure_reason}",
        "valid",
    )

    tampered = copy.deepcopy(offer_act)
    tampered["terms"]["total_value"] = 9_900_000
    result = verify_approval_receipt(
        receipt, tampered, now=now, issuer_public_key=b64url_decode(jwk["x"])
    )
    record(
        "Concordia rejects the receipt against a tampered offer",
        "valid" if result.valid else str(result.failure_reason),
        "offer_hash_mismatch",
    )


def run_a2cn(expected: dict, jwks: dict) -> None:
    import a2cn.session as session_module
    from a2cn.session import A2CNError, SessionManager

    frozen = datetime.fromisoformat(expected["evaluation_time"].replace("Z", "+00:00"))

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)

    # The fixture's timestamps are fixed, so the implementation's clock is too.
    session_module.datetime = FrozenClock

    init = load("a2cn/session_init.json")
    ack = load("a2cn/session_ack.json")
    offer = load("a2cn/bafo_offer.json")
    acceptance = load("a2cn/acceptance.json")
    receipt = load("concordia/approval_receipt.json")

    def paused_session():
        manager = SessionManager()
        for did in (init["initiator"]["did"], ack["responder"]["did"]):
            manager.register_did_document(did, did_document(did, jwks))
        session = manager.create_session(
            ack["session_id"], init, ack, ack["session_created_at"]
        )
        after_offer = manager.process_message(session, copy.deepcopy(offer))
        after_acceptance = manager.process_message(session, copy.deepcopy(acceptance))
        return manager, session, after_offer, after_acceptance

    def attempt(label: str, candidate: dict, expect: str) -> None:
        manager, session, _, _ = paused_session()
        try:
            state = manager.apply_approval_receipt(session, candidate)
            got = str(getattr(state["state"], "value", state["state"]))
        except A2CNError as exc:
            got = exc.code
        record(label, got, expect)

    _, _, after_offer, after_acceptance = paused_session()
    record(
        "A2CN accepts the BAFO offer (signature rebuilt and verified)",
        str(getattr(after_offer["state"], "value", after_offer["state"])),
        "NEGOTIATING",
    )
    want = expected["a2cn"]["on_acceptance"]
    got = {key: after_acceptance.get(key) for key in want}
    got["state"] = str(getattr(got["state"], "value", got["state"]))
    record(
        "A2CN pauses the acceptance in AWAITING_HUMAN_APPROVAL, bound to the offer hash",
        json.dumps(got, sort_keys=True),
        json.dumps(want, sort_keys=True),
    )

    # Divergence 1: A2CN compares scope.offer_hash to its base64url
    # protocol_act_hash; Concordia's schema requires sha256:<hex>.
    attempt(
        "KNOWN DIVERGENCE: A2CN applies the Concordia receipt as issued",
        receipt,
        "OFFER_HASH_MISMATCH",
    )

    # Divergence 2: A2CN reads the approver from a top-level approver_did;
    # Concordia carries it at approver.identity.
    rehashed = copy.deepcopy(receipt)
    rehashed["scope"]["offer_hash"] = expected["hashes"]["a2cn_protocol_act_hash"]
    attempt(
        "KNOWN DIVERGENCE: A2CN applies the receipt with only the hash re-encoded",
        rehashed,
        "UNAUTHORIZED_APPROVER",
    )

    # Divergence 3: Concordia §11.5.7 recommends urn:a2cn:session:<id>; A2CN
    # accepts the bare id or a2cn:session:<id> only.
    urn_shaped = copy.deepcopy(rehashed)
    urn_shaped["approver_did"] = receipt["approver"]["identity"]
    urn_shaped["references"][0]["id"] = "urn:" + urn_shaped["references"][0]["id"]
    attempt(
        "KNOWN DIVERGENCE: A2CN applies a receipt whose session reference is URN-shaped",
        urn_shaped,
        "APPROVAL_RECEIPT_INVALID",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--concordia", required=True, help="concordia-protocol checkout")
    parser.add_argument("--a2cn", required=True, help="A2CN checkout")
    args = parser.parse_args()

    sys.path.insert(0, str(Path(args.concordia).resolve()))
    sys.path.insert(0, str(Path(args.a2cn).resolve() / "reference-implementation" / "python"))

    expected = load("expected.json")
    jwks = load("keys/jwks.json")
    run_concordia(expected, jwks)
    run_a2cn(expected, jwks)

    for ok, label, detail in outcomes:
        print(("PASS  " if ok else "FAIL  ") + label + ("" if ok else f" ({detail})"))
    failed = sum(1 for ok, _, _ in outcomes if not ok)
    print(f"\n{len(outcomes) - failed} of {len(outcomes)} outcomes as expected")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
