# GlacierNET Operations MVP

GlacierNET Operations is a shadow-mode workspace for deciding what evidence to
collect next and documenting how a human decision was made. It does not issue
official warnings and does not estimate a calibrated GLOF probability.

## Product outcome

The operational unit is an **Evidence Case**, not a segmentation mask:

```text
basin and monitored asset
        ↓
observation inbox
        ↓
change candidate + data-quality checks
        ↓
Domain Shift Detector
        ↓
Next Best Observation
        ↓
inspection task and signed field report
        ↓
evidence case and human decision
        ↓
SHA-256 audit export
```

The Science Registry and Operations Registry remain separate. Operational
records must never enter a frozen benchmark test set automatically.

## Entities

| Entity | Purpose |
| --- | --- |
| Basin | Customer or pilot deployment boundary |
| Asset | Glacier, moraine lake, sensor, slope, or infrastructure object |
| Observation | Satellite, sensor, drone, field, or inventory evidence |
| Change Candidate | A reviewable change hypothesis, not an event prediction |
| Inspection Task | A human-authorised satellite, field, drone, or sensor action |
| Field Report | Signed coordinates, checklist, measurements, notes, and attachment manifest |
| Evidence Case | Sources, changes, limitations, reviewers, and permitted use |
| Decision | Human decision, rationale, status, and eventual outcome |
| Audit Event | Append-only SHA-256-linked mutation record |

## Safety logic

`src/operations/safety.py` implements two independently named controls:

- **Domain Shift Detector** checks model compatibility and abstains outside the
  validated region, with incompatible preprocessing, high OOD score, or high
  model disagreement.
- **Next Best Observation** combines uncertainty, staleness, input-quality
  gaps, model disagreement, and expected information gain.

Neither output is a hazard probability. The current external-geography stress
result is exposed at `GET /api/operations/domain-shift/current-model`; its poor
Dice keeps external use in `abstain_local_validation_required`.

## API

Read-only endpoints:

```text
GET  /api/operations/readiness
GET  /api/operations/overview
GET  /api/operations/demo
GET  /api/operations/assets
GET  /api/operations/audit
GET  /api/operations/domain-shift/current-model
POST /api/operations/domain-shift
GET  /api/operations/evidence-cases/{case_id}/export
```

Analyst/write scope is required for persistent mutations:

```text
POST  /api/operations/basins
POST  /api/operations/assets
POST  /api/operations/observations
POST  /api/operations/change-candidates
POST  /api/operations/inspection-tasks
PATCH /api/operations/inspection-tasks/{task_id}
POST  /api/operations/field-reports
POST  /api/operations/evidence-cases
POST  /api/operations/decisions
```

Evidence exports contain the asset, related observations, candidates, tasks,
field reports, decisions, audit-chain verification, allowed and forbidden
uses, plus a bundle SHA-256.

## Web workflow

Start the stack and open:

```text
http://localhost:8080/operations
```

An empty registry automatically shows a non-persistent `synthetic_demo`
preview. It is visibly marked as shadow mode. The field form saves an offline
draft in browser storage; synchronisation is offered only for a persisted task
and an authenticated analyst.

## Production boundary

Implemented:

- persistent SQLite Operations Registry;
- role-gated writes;
- observation and inspection queues;
- domain-shift abstention;
- offline field draft;
- signed field-report schema;
- evidence cases and decisions;
- cryptographic audit chain and JSON export.

Still partner-specific:

- real sensor connectors and data contracts;
- SSO/identity-provider configuration;
- customer object inventory and permissions;
- offline map packages and attachment upload;
- institutional report templates and signatures;
- field validation and official operating procedures.
