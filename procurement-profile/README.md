# A2A Procurement Profile: payload fragments

The payload fragments of the A2A Procurement Profile, published here for use by the patterns and fixtures in this repository. The profile defines procurement payload semantics for agent-to-agent traffic: four canonical fragments, each layered on existing UBL 2.3 / Peppol BIS Pre-Award / OCDS 1.1.5 / EU eForms semantics.

| | |
| --- | --- |
| **Extension URI** | `https://spec.bidangelai.com/v0.1/` |
| **Version** | v0.1 (draft; breaking changes expected until v1.0) |
| **Author** | BidAngel ([@brainspacer](https://github.com/brainspacer)) |
| **Authoritative source** | [bidangel/a2a-procurement-spec](https://github.com/bidangel/a2a-procurement-spec) |
| **Discussion** | [a2aproject/A2A#1832](https://github.com/a2aproject/A2A/discussions/1832) |

The Extension URI is also the namespace IRI of the profile's vocabulary and resolves to a namespace document listing every term.

## Scope

Per the three-protocol substrate split ([ADR 0035](https://github.com/bidangel/a2a-procurement-spec/blob/main/adrs/0035-cross-protocol-composition-with-a2cn-and-concordia.md)), this profile owns procurement payload semantics and nothing else.

In scope:

- The four canonical fragments: `opportunity`, `requirement`, `evaluation_criterion`, `buyer`.
- A JSON-LD `@context` for each fragment.
- Field-by-field crosswalks from each fragment to UBL, Peppol, OCDS and eForms.

Out of scope:

- Session establishment, authority chain and mandate verification (A2CN).
- Wire envelope, receipts, the `references[]` mechanism and base relationship verbs (Concordia).
- Any change to A2A core, the AgentCard schema or the task model.

## Fragments

| Fragment | Context | Crosswalk | UBL 2.3 counterpart |
| --- | --- | --- | --- |
| `opportunity` | [`opportunity.context.jsonld`](contexts/v0.1/opportunity.context.jsonld) | [`ubl-peppol-opportunity.md`](crosswalks/ubl-peppol-opportunity.md) | `CallForTenders` (`cac:TenderingProcess`, `cac:ProcurementProject`) |
| `requirement` | [`requirement.context.jsonld`](contexts/v0.1/requirement.context.jsonld) | [`ubl-peppol-requirement.md`](crosswalks/ubl-peppol-requirement.md) | `cac:TenderingCriterionProperty` |
| `evaluation_criterion` | [`evaluation-criterion.context.jsonld`](contexts/v0.1/evaluation-criterion.context.jsonld) | [`ubl-peppol-evaluation-criterion.md`](crosswalks/ubl-peppol-evaluation-criterion.md) | `cac:TenderingCriterion` |
| `buyer` | [`buyer.context.jsonld`](contexts/v0.1/buyer.context.jsonld) | [`ubl-peppol-buyer.md`](crosswalks/ubl-peppol-buyer.md) | `cac:Party` |

Two supporting cross-maps cover the enumerations:

- [`canonical-criterion-type-eu-com-grow-map.md`](crosswalks/canonical-criterion-type-eu-com-grow-map.md): criterion type to the EU-COM-GROW `CriteriaTypeCode` codelist.
- [`canonical-opportunity-status-lifecycle-map.md`](crosswalks/canonical-opportunity-status-lifecycle-map.md): opportunity status to OCDS, UBL, SAM.gov and Ariba lifecycles.

## How the contexts map terms

Each crosswalk classes every field as exact, partial or novel against its UBL counterpart. The contexts apply one rule:

- A field keeps the UBL IRI when the crosswalk marks it exact, or partial only because the profile carries one string where UBL allows several languages, and it corresponds to a single UBL element.
- Every other field is defined under the profile namespace (`bapp:`). That covers enumerations, values flattened from a complex UBL element, fields with two candidate UBL elements, and novel fields.

Nested objects (`buyerRef`, `standardSchema`, `valueConstraints`) are opaque references at v0.1. Scoped contexts for them are planned for v0.2.

## Pinned standards

- UBL 2.3
- Peppol BIS Pre-Award, and Peppol BIS ESPD 1.0 with `CriteriaTypeCode` (`EU-COM-GROW`, list version 1.0.2)
- OCDS 1.1.5, with the Requirements extension
- EU eForms, Implementing Regulation 2019/1780

Re-pinning is event-driven: a new UBL, Peppol BIS Pre-Award, OCDS or eForms codelist release triggers a crosswalk diff.

## Declaring the profile

An agent that emits or accepts these fragments declares the profile in its AgentCard:

```json
{
  "capabilities": {
    "extensions": [
      {
        "uri": "https://spec.bidangelai.com/v0.1/",
        "description": "A2A Procurement Profile v0.1: opportunity, requirement, evaluation_criterion and buyer fragments.",
        "required": false
      }
    ]
  }
}
```

A fragment names its context:

```json
{
  "@context": "https://spec.bidangelai.com/contexts/v0.1/requirement.context.jsonld",
  "@type": "Requirement",
  "perRowKey": "caiq-v4:IAM-02.1",
  "externalId": "IAM-02.1",
  "body": "Are access rights reviewed at least annually?",
  "requirementType": "security",
  "subType": "questionnaire",
  "mandatoryFlag": true
}
```

## Not in v0.1 yet

- JSON Schema files for each fragment.
- A round-trip test (canonical fragment to UBL XML and back).
- A worked-example fixture. The BAFO fixture proposed in [bidangel/a2a-procurement-spec#4](https://github.com/bidangel/a2a-procurement-spec/issues/4) will land under `fixtures/bafo-round/` in a later PR.

## Provenance

The files under `contexts/` and `crosswalks/` are copies of the same paths in [bidangel/a2a-procurement-spec](https://github.com/bidangel/a2a-procurement-spec) at commit `a8f035c`. That repository is authoritative. Changes are made there first and copied here; please do not edit the copies in place.

## License

Apache-2.0, as the rest of this repository. That includes the copies under `crosswalks/`; the same crosswalks are published upstream under CC BY 4.0.
