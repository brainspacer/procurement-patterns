# procurement-patterns

Joint pattern library for procurement-vertical agent commerce, co-maintained by Concordia Protocol and A2CN Protocol. Composes with the A2A Procurement Profile (BidAngel) per [ADR 0035](https://github.com/bidangel/a2a-procurement-spec/blob/main/adrs/0035-cross-protocol-composition-with-a2cn-and-concordia.md).

This repo is the worked-example surface where the three protocols compose against concrete procurement scenarios (RFx, BAFO, clarification rounds, HITL approval, dispute resolution). Each pattern lands as a fixture set with end-to-end signed artifacts exercising the three-protocol substrate split.

## The substrate split

Per ADR 0035, the three protocols partition cleanly:

| Protocol | Owns |
|----------|------|
| **A2CN** | Session establishment, authority chain, mandate verification, bilateral transaction record, session-state lifecycle. |
| **Concordia** | Wire envelope, negotiation receipt, cross-protocol `references[]` mechanism, base relationship verbs (`fulfills`, `approves`, `enforces`, `rejects`). |
| **A2A Procurement Profile** (BidAngel) | Canonical procurement payload fragments (`opportunity`, `requirement`, `evaluation_criterion`, `buyer`), the `procurement.*` clause namespace for RejectionRecord, procurement-specific relationship verbs (initial: `satisfies`). |

The substrate split follows the maturity gradient of each profile. A2CN's mandate-verification semantics generalise across domains. Concordia's envelope and receipt format are domain-neutral and were designed with cross-protocol composition in mind from inception. The A2A Procurement Profile's contribution is the procurement-specific payload semantics that ride inside the Concordia envelope under an A2CN-established session.

## Scope of this repo

In scope:

- **Worked-example fixtures.** End-to-end signed artifacts exercising A2CN session + Concordia envelope + procurement payload composition. First fixture: HITL pause-resume with ApprovalReceipt (per [a2aproject/A2A#1737](https://github.com/a2aproject/A2A/discussions/1737)).
- **Cross-protocol relationship-verb registry.** Procurement-specific verbs added to Concordia's `references[]` vocabulary, namespaced per ADR 0035 §2.
- **Cross-protocol ADRs** that touch the three-protocol composition surface specifically (not the per-protocol concerns each upstream owns).

Out of scope:

- A2CN session-state machine, mandate verification semantics, transaction-record format. Lives at [a2cn-protocol/A2CN](https://github.com/a2cn-protocol/A2CN).
- Concordia envelope shape, receipt format, attestation schemas (§9.6), reference-linkage shape (§11.5). Lives at [eriknewton/concordia-protocol](https://github.com/eriknewton/concordia-protocol).
- The A2A Procurement Profile's UBL/Peppol/OCDS/eForms-aligned canonical fragments, `procurement.*` clause namespace, and procurement-specific relationship verbs. Live at [bidangel/a2a-procurement-spec](https://github.com/bidangel/a2a-procurement-spec).

## Status

Scaffold. First fixture PR coming this week: `hitl-pause-resume-150k.json`, shaped as a Concordia [§9.6.4b ApprovalReceipt](https://github.com/eriknewton/concordia-protocol/blob/main/SPEC.md#964b-approvalreceipt-v05-a2a-discussion-1737) with `references[]` pointing at the A2CN session ID and the upstream mandate. The HITL example from [a2aproject/A2A#1737](https://github.com/a2aproject/A2A/discussions/1737#discussioncomment-16882987) is the canonical worked example.

Subsequent fixtures land per pattern:

- BAFO round triggering `AWAITING_HUMAN_APPROVAL` with ApprovalReceipt + OCDS opportunity ID via `references[]` (per [bidangel/a2a-procurement-spec#4](https://github.com/bidangel/a2a-procurement-spec/issues/4)).
- Typed `RejectionRecord` enumeration across the `mandate.*` (Concordia) and `procurement.*` (BidAngel) clause namespaces.
- `FulfillmentAttestation` consuming A2CN's `DELIVERY_ACKNOWLEDGED` event verbatim, mapped to Concordia's `fulfillment.status` enum.
- Three §8 ratifications from the 2026-05-18 cross-fire batch (umbrella profile single registration, resolvable `https://` URI shape, `satisfies` stays distinct from `fulfills`).

The formal A2A extension PR (umbrella Registered Vocabulary Profile registering ApprovalReceipt, RejectionRecord, and FulfillmentAttestation as entries) targets filing window 2026-05-18 plus one to two weeks.

## Repository layout

```
README.md                this file
LICENSE                  Apache-2.0
.github/CODEOWNERS       review routing
fixtures/                worked-example signed artifacts (per-pattern subdirectories)
adrs/                    cross-protocol architectural decisions
```

## Maintainers

- [Erik Newton](https://github.com/eriknewton) (Concordia Protocol)
- [Christian Magorrian](https://github.com/cmagorr1) (A2CN Protocol)

Additional committers added per scope per [a2aproject/A2A#1832](https://github.com/a2aproject/A2A/discussions/1832) (e.g., [@brainspacer](https://github.com/brainspacer) on A2A Procurement Profile payload semantics).

## License

Apache-2.0. See [LICENSE](./LICENSE).

## Citing

When citing this repo in a spec, ADR, or RFC, please reference the specific commit or tag rather than `main`. The three-protocol substrate split is canonical per ADR 0035 (BidAngel); any drift surfaces as an ADR amendment under [`adrs/`](./adrs/) in this repo.
