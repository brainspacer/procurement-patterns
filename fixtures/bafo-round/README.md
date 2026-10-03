# bafo-round

A best-and-final-offer round in which a human approves an acceptance that crosses a mandate threshold. One scenario, three protocols:

- **A2CN** carries the session, the signed offer and acceptance, and the `AWAITING_HUMAN_APPROVAL` pause.
- **Concordia** carries the signed `ApprovalReceipt` and its `references[]`.
- **A2A Procurement Profile** carries the procurement payload inside the offer, and the `satisfies` relationship verb.

Proposed in [bidangel/a2a-procurement-spec#4](https://github.com/bidangel/a2a-procurement-spec/issues/4). The scenario differs from that proposal in one respect, explained under [Changes from the proposal](#changes-from-the-proposal).

## Scenario

1. A supplier agent (`did:web:supplier.example`) opens an A2CN session with a buyer agent (`did:web:acme.example`).
2. The supplier sends its BAFO as an A2CN `offer` for USD 150,000.00. The offer's `terms.custom_terms` carries a Procurement Profile `Requirement` fragment and names the opportunity it answers.
3. The buyer agent moves to accept. Its mandate allows commitments up to USD 200,000.00 but requires human approval above USD 100,000.00, so A2CN holds the acceptance and the session enters `AWAITING_HUMAN_APPROVAL`, bound to the offer's act hash.
4. The buyer's procurement lead (`did:web:acme.example#procurement-lead`) signs a Concordia `ApprovalReceipt` over that offer.
5. A2CN consumes the receipt, releases the held acceptance, and the session reaches `COMPLETED`.

## Files

| Path | Protocol | What it is |
| --- | --- | --- |
| `procurement/opportunity.json` | Procurement Profile | The opportunity, as an `Opportunity` fragment |
| `procurement/requirement.json` | Procurement Profile | The BAFO clarification, as a `Requirement` fragment |
| `a2cn/session_init.json`, `a2cn/session_ack.json` | A2CN | Session establishment, with both mandates |
| `a2cn/bafo_offer.json` | A2CN | The signed offer, carrying the requirement fragment |
| `a2cn/bafo_offer_protocol_act.json` | A2CN | The object the offer's signature covers; the hash preimage |
| `a2cn/acceptance.json` | A2CN | The signed acceptance that A2CN holds until approval |
| `concordia/approval_receipt.json` | Concordia | The signed `ApprovalReceipt` |
| `keys/jwks.json` | | Public keys for the three signers |
| `expected.json` | | Evaluation time, hashes, expected outcomes, negative cases |

## How the three protocols bind

**One digest, two encodings.** The receipt's `scope.offer_hash` and A2CN's `protocol_act_hash` are the same SHA-256 digest of the same bytes: the RFC 8785 canonical form of `a2cn/bafo_offer_protocol_act.json`. Concordia writes it as `sha256:<hex>`; A2CN writes it as base64url. Because the procurement payload sits inside `terms`, the digest covers it: changing a word of the requirement invalidates the supplier's signature and the approval.

**`references[]`.** The receipt carries three, and each resolves inside this fixture:

| Reference | Relationship | Owner of the verb | Resolves to |
| --- | --- | --- | --- |
| `a2cn:session:bafo-2026-05-12-001` | `approves` | Concordia | `a2cn/session_ack.json` `session_id` |
| `a2cn:mandate:m-2026-05-12-0042` | `fulfills` | Concordia | `a2cn/session_ack.json` `responder_mandate.mandate_id` |
| `ocds-bidangel-0001-bafo-fixture` | `satisfies` | Procurement Profile | `procurement/opportunity.json` `externalId` |

**Approver authority.** The receipt's `approver.identity` is listed in the buyer mandate's `approval_operator_dids`, and its key is in `keys/jwks.json`.

## Running it

```sh
pip install cryptography rfc8785==0.1.4

python generate.py   # rewrites every artifact; output is byte-stable
python verify.py     # 36 checks, exit 0 on success
```

`verify.py` shares no code with `generate.py` and imports neither reference implementation. It checks the fixture against the specifications: JCS canonicalization, both hash encodings, the A2CN act signatures, the threshold crossing, the receipt's signature, validity window, approver and offer binding, each reference, and that the fragments use only terms from their [v0.1 contexts](../../procurement-profile/contexts/v0.1/). It also runs four negative cases, each of which must fail for the stated reason.

Timestamps are fixed. `expected.json` gives the `evaluation_time` at which the receipt is inside its validity window.

The Ed25519 seeds in `generate.py` are test keys, published so the fixture can be regenerated. Do not reuse them.

## Against the reference implementations

`crosscheck.py` feeds the same files to both Python reference implementations:

```sh
pip install jsonschema jcs==0.2.1 PyJWT==2.9.0 httpx==0.27.0
python crosscheck.py --concordia <concordia-protocol checkout> --a2cn <A2CN checkout>
```

Last run against `eriknewton/concordia-protocol@847729c` and `a2cn-protocol/A2CN@c7ff3f1`:

| Check | Result |
| --- | --- |
| Concordia `verify_approval_receipt` accepts the receipt | passes |
| Concordia rejects the receipt against a tampered offer | passes (`offer_hash_mismatch`) |
| A2CN accepts the offer, rebuilding and verifying its signature | passes |
| A2CN holds the acceptance in `AWAITING_HUMAN_APPROVAL`, bound to the offer hash | passes |

### Divergences found

The receipt is a valid Concordia artifact, and A2CN pauses correctly, but the A2CN reference implementation does not accept the Concordia receipt as issued, so the cross-check stops at the pause. `expected.json` records the outcome the composition should reach once it does. The cross-check pins today's behaviour for each of these, so it fails the day one is resolved and the fixture can be updated.

1. **Offer hash encoding.** A2CN compares `scope.offer_hash` to its base64url `protocol_act_hash` as a string. Concordia's schema requires `sha256:<hex>`. Same digest, different spelling: A2CN returns `OFFER_HASH_MISMATCH`.
2. **Approver field.** A2CN reads the approver from a top-level `approver_did` (or `operator_did`, `signed_by`). Concordia carries it at `approver.identity`. With only the hash re-encoded, A2CN returns `UNAUTHORIZED_APPROVER`.
3. **Session reference shape.** Concordia §11.5.7 recommends `urn:a2cn:session:<id>`. A2CN accepts the bare id or `a2cn:session:<id>` and rejects the URN form with `APPROVAL_RECEIPT_INVALID`. This fixture uses `a2cn:session:<id>`, which Concordia's schema example also uses.

Each is a small change on one side or the other. Which side is for the A2CN and Concordia maintainers to decide; this fixture records the gap and does not pick.

## Changes from the proposal

Issue #4 had the buyer's procurement lead approve the *supplier's offer*. In A2CN the pause belongs to the party whose mandate carries the threshold, and it triggers on that party's own act (§14.2). So here the supplier's offer is transmitted normally, and the pause is on the *buyer agent's acceptance*, which is the act the buyer's mandate constrains. The approver, the amounts, the receipt shape and the `satisfies` reference are as proposed.

The receipt also gained a `fulfills` reference to the mandate, which A2CN §14.1 requires and Concordia §9.6.4b recommends.

## Not covered

- **UBL round-trip of the requirement payload** (acceptance criterion 1 of issue #4). It needs a UBL adapter and projection that do not exist yet.
- **A Concordia wire envelope.** The receipt is a standalone signed artifact, which is how §9.6.4b defines it.
- **DID resolution.** Keys come from `keys/jwks.json`; nothing is fetched.
- **A `deny` receipt, receipt expiry and re-approval, and `RejectionRecord`.** Each is a separate fixture.
