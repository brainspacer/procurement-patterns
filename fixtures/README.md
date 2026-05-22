# fixtures/

Worked-example signed artifacts exercising the three-protocol substrate split per [ADR 0035](https://github.com/bidangel/a2a-procurement-spec/blob/main/adrs/0035-cross-protocol-composition-with-a2cn-and-concordia.md).

## Layout

Each pattern gets a subdirectory. Each fixture is self-contained: input, signed artifacts (Concordia envelope, A2CN session record, procurement payload), expected verification outcomes.

```
fixtures/
  hitl-pause-resume/        ApprovalReceipt threshold-crossing pattern
  bafo-round/               Best-and-Final-Offer with OCDS opportunity reference
  rejection-record/         Typed RejectionRecord across mandate.* and procurement.* clauses
  fulfillment-attestation/  Concordia FulfillmentAttestation consuming A2CN DELIVERY_ACKNOWLEDGED
```

## Conformance bar

Every fixture verifies against:

- RFC 8785 JCS canonicalization (`rfc8785@0.1.4` Python; equivalents in JS, Go, Java, Rust per [A2A #1734](https://github.com/a2aproject/A2A/discussions/1734) substrate gate).
- Lowercase-hex SHA-256 over canonical pre-image.
- Ed25519 signature verification against the issuer's published JWKS.
- Cross-protocol `references[]` resolution per Concordia v0.5.1 §11.5.

Pending arrival of the first fixture this week.
