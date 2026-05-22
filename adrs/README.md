# adrs/

Cross-protocol architectural decisions that touch the three-protocol composition surface specifically.

## Scope

ADRs in this directory cover decisions that span A2CN, Concordia, and the A2A Procurement Profile. Decisions that live cleanly within a single protocol's surface belong in that protocol's own repo.

In scope:

- New procurement-specific relationship verbs proposed for addition to Concordia's `references[]` vocabulary.
- New `procurement.*` clause-namespace entries proposed for Concordia's `RejectionRecord`.
- Boundary clarifications between A2CN session lifecycle and Concordia envelope state.
- Conformance-gate decisions that the three-protocol composition depends on (substrate-canonicalization version pinning, JWKS resolution discipline, cross-protocol URN resolver patterns).

Out of scope:

- A2CN-internal session, authority, or mandate decisions. Land at [a2cn-protocol/A2CN](https://github.com/a2cn-protocol/A2CN).
- Concordia-internal envelope, receipt, or attestation decisions. Land at [eriknewton/concordia-protocol](https://github.com/eriknewton/concordia-protocol).
- A2A Procurement Profile UBL/Peppol/OCDS/eForms alignment decisions. Land at [bidangel/a2a-procurement-spec](https://github.com/bidangel/a2a-procurement-spec). The canonical reference for the three-protocol split itself is [BidAngel ADR 0035](https://github.com/bidangel/a2a-procurement-spec/blob/main/adrs/0035-cross-protocol-composition-with-a2cn-and-concordia.md).

## Naming

`NNNN-short-slug.md`, four-digit zero-padded sequence starting at `0001`. Sequence is local to this repo; no relationship to per-protocol ADR sequences upstream.

## Status conventions

- `Proposed`: drafted, open for comment.
- `Accepted`: ratified by maintainers (Erik Newton + Christian Magorrian plus any scope-relevant additional committers per [a2aproject/A2A#1832](https://github.com/a2aproject/A2A/discussions/1832)).
- `Superseded by NNNN`: replaced.
- `Deprecated`: retired without replacement.

No ADRs landed yet. First batch expected after the first fixture sets ship.
