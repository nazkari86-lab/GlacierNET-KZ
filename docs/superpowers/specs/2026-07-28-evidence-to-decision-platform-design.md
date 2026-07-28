# GlacierNET-KZ Evidence-to-Decision Platform — design

## Objective

Evolve GlacierNET-KZ from a collection of research, map, AI, Operations, Jury and report pages into one evidence-first cryosphere product. A user must be able to select a real glacier or lake candidate and follow the same source-backed case through analysis, map, next verification action, jury evidence and export.

The platform must improve usefulness and presentation quality without widening scientific claims beyond the current one-AOI, RGI-derived-label temporal evidence. It must not claim independent gold-label accuracy, regional generalisation, event probability, inundation, impact, operational warning or engineering effectiveness unless their dedicated validation gates become complete.

## Product principle

```text
verified source → named spatial object → year-aware observation
→ explicit claim boundary → next evidence action → exportable evidence package
```

Every step preserves provenance, date, uncertainty/maturity and a visible `not allowed` statement. Missing data produces an abstention or a collection request, never a synthetic replacement.

## Delivery program

The program is deliberately split into independently shippable releases.

### Release A — Evidence-to-Decision Spine (first implementation plan)

Create a stable case identity and deep-link contract shared by Risk Twin, Operations, Jury, AI Analysis and Reports.

- `EvidenceCaseRef` has `rgi_id`, optional `lake_id`, optional `year`, `source_scope` and a non-secret canonical URL query.
- Operations candidate selection links to the matching Risk Twin map state rather than a generic page.
- Risk Twin shares selected object, year, map mode, issue and comparison state via URL.
- Jury and Reports link to the same case only when the case is backed by a returned local source; they otherwise link to the glacier context without fabricating a lake case.
- A source-aware case header appears consistently across pages: identity, evidence status, locality/time window, claim boundary and next action.
- The demo route becomes a guided five-step journey through live data, with clear degraded/offline states.

### Release B — Scientific Evidence Cockpit

Make the valid scientific evidence legible to a non-specialist without overstating it.

- Show temporal split, label tier, exact test scope, model provenance, calibration state and caveats next to every metric.
- Add glacier-level paired metric tables and bootstrap CI rendering only from measured report artefacts.
- Separate `verified`, `exploratory`, `provisional`, `blocked` and `not available` states in API, UI, exported reports and LLM prompts.
- Add a claim registry explorer that links every supported claim to its report, checksum/provenance and disallowed extension.
- The Zhetysu external evaluation remains visibly blocked until an authoritative boundary and adjudicated labels exist; its protocol can be prepared but cannot emit performance results.

### Release C — Evidence-grounded AI and reports

Make AI useful only as an interface to project evidence.

- AI receives a typed, compact case package assembled server-side, not the full uncontrolled tool catalogue.
- Supported questions generate structured answer blocks: conclusion, values, uncertainty, evidence IDs, caveats and suggested visualisation specification.
- The browser renders charts from returned numerical series; the language model never fabricates graph values or SVG paths.
- Exports include source list, claim boundaries, selected map state and generated-at time. User-entered observations retain `requires_provenance_review`.

### Release D — Product, accessibility and jury route

Make the project simple to demonstrate under ordinary internet conditions.

- Landing page offers `Explore evidence`, `Scan a year`, `Review a case`, `Jury evidence` and `Export report` as distinct tasks.
- A guided demo is keyboard-operable, bilingual/trilingual where existing translation infrastructure supports it, and says when data are unavailable.
- Every map-heavy route has a readable non-map summary, reduced-motion support and an offline/local-layer fallback.
- Jury view presents proof, limitations and reproducibility in the same order a reviewer needs to evaluate them.

### Release E — Release engineering and reproducibility

- One status command reports API health, local artefact availability, manifest/hash state, data-link state and claim-gate status.
- Strict release mode fails on unverified Drive symlinks, missing required artefacts, invalid reports or unsupported claim text.
- Presentation mode may use only hashes-verified local artefacts; it shows a source-unavailable state rather than reaching out to an untrusted remote layer.
- CI/local checks are split: focused tests may run without global coverage; release checks report the global coverage gate separately and never hide it.

## Architecture

### Canonical case contract

The web client owns browser URL state. The API owns source validity and never trusts query parameters as evidence.

```ts
interface EvidenceCaseRef {
  rgiId: string;
  lakeId?: string;
  year?: number;
  objectId?: string;
  issueId?: string;
  sourceScope: "local_inventory" | "annual_screening" | "archive_context" | "planning_context";
}
```

Case resolution is fail-closed: an unknown lake ID, mismatched glacier, unavailable year artefact or unsupported source scope resolves to the glacier context with a human-readable explanation. It never selects a nearby record by guesswork.

### Evidence package

The backend provides a single read-only package for each valid case. It contains typed source references, available visual layers, source coverage, claim limits, numerical facts, ranked evidence actions and report/export provenance. Existing source-specific endpoints remain available; the package composes their validated outputs and makes no new physics or risk calculation.

### Presentation boundaries

- Maps display source geometries and labelled spatial context.
- Charts render only API-provided numbers and intervals.
- AI returns prose and structured chart specifications constrained by the evidence package.
- Operations can record observations and reports, but labels them user/field supplied until review; it cannot promote them to scientific validation automatically.

## Failure handling

- Missing API/context: preserve local RGI/year layer and explain the missing source.
- Missing annual comparison: disable only compare mode.
- Missing OSM/GHSL: show no synthetic buildings, people or assets.
- Failed external basemap: leave local vectors and inspector active.
- Missing strict data verification: presentation/release status is incomplete, while development views show an explicit data-link limitation.
- AI/provider failure: return the verified context package for direct reading and do not replace it with generated text.

## Validation strategy

- Unit tests: case parsing/validation, source-scope restrictions, claim-status mapping, structured AI response validation and chart data guards.
- Component tests: one selected case synchronises Operations/Risk Twin/Jury/Reports links; no synthetic fallback appears on any empty state.
- Browser tests: guided demo primary path; keyboard flow; reduced motion; local layer survival after tile failure.
- API tests: package contains only source-returned values and blocks unsupported claims.
- Release checks: frontend lint/build, focused frontend/API tests, manifest/checksum validators and the existing strict claim gate.

## Explicit non-goals until external evidence exists

- Expert-adjudicated gold accuracy.
- Independent Zhetysu Alatau performance/generalisation.
- Calibrated GLOF probability, warning, inundation, casualty or infrastructure-impact estimates.
- Validated 2000–2020 regional loss rate or a 2050 regional forecast beyond the documented exploratory scope.

## First plan boundary

The next implementation plan covers **Release A only**. It delivers an end-to-end, source-aware case spine without changing model science or downloading new data. Releases B–E then build on its contract and can be validated separately.
