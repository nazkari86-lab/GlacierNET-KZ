# Risk Twin Evidence-to-Action Map — design

## Decision

Build the Risk Twin around a **hybrid scientific map**: a clean vector-first map with optional satellite imagery and optional hillshade/terrain context. The default view prioritizes named objects, the evidence route between them, and explicit uncertainty. Satellite imagery is a comparison tool, not the default visual surface.

This is the first implementation unit of the broader project upgrade because it makes the existing real data, the model limits, and the next useful action understandable in one screen. It does not add an operational warning system or claim that an object is endangered.

## Why this approach

Three viable visual directions were considered.

1. **Hybrid scientific map — selected.** A high-contrast vector map keeps glacier, lake, river, asset, and evidence-gap labels readable. Hillshade and satellite imagery are optional evidence layers. It performs well, works offline when local tiles/layers are available, and is suitable for a projector.
2. **Satellite-first map.** It is visually dramatic but labels, routes, and uncertainty are hard to read. It also depends on tile availability and can imply more precision than the data support.
3. **Dashboard-first page.** It is easy to build but separates the map from the decision, making the project look like a collection of cards rather than a spatial research system.

## User outcome

A presenter selects a glacier and year, then can immediately answer:

1. Which named real objects are in the locally verified context?
2. What is observed, spatially proximate, missing, or only hypothetical?
3. Which data gap most changes the next decision?
4. Which nearby assets or population planning context require further verification?
5. What must not be claimed from the current data?

## Visual composition

The desktop workspace has one dominant map and two narrow decision rails.

```text
header: project status | glacier search | year timeline | map mode

left rail              map canvas                              right rail
context / layers       named evidence objects                   ranked issue queue
source status          selected-object spotlight                evidence inspector
legend                 animated evidence route                 next best action
                        cascade ribbon

footer: claim boundary and source freshness
```

### Map canvas

- At least 65 percent of desktop width is map.
- The map starts on local RGI geometry, not a generic national overview.
- The base is muted dark terrain/vector styling. Bright colours are reserved for evidence layers.
- Satellite imagery and hillshade are explicit toggles. A tile failure never hides local vectors or causes the page to fail.
- A compact top toolbar provides year, compare-year, map mode, and layer visibility without requiring Leaflet's default layer dialog.

### Named evidence objects

Every rendered object has a stable identity, display name, source, date or coverage period, confidence/maturity, and a precise claim boundary. The UI never invents a person, building purpose, lake volume, downstream route, or hazard label.

| Object | Visual treatment | Required popup/inspector fields |
| --- | --- | --- |
| RGI glacier geometry | cyan outline + translucent fill | RGI ID, name, inventory area, inventory caveat |
| Annual segmentation | indigo outline/overlay | local year, method, artefact availability, comparability warning |
| Lake inventory polygon | blue water fill | lake ID, inventory period, area if supplied, linkage caveat |
| HydroRIVERS reach | directional blue line | reach ID, length/order if supplied, proximity-only statement |
| HydroBASINS polygon | dashed violet outline | basin ID, coverage statement |
| Historical event record | red archive marker | record ID/date/source state, not a forecast |
| OSM planning asset | violet icon/footprint | source object type/name, no assumed occupancy or vulnerability |
| GHSL planning cell | amber grid/hex cell | reference year and planning-context limitation |
| Evidence gap | amber/red ring or dashed callout | missing variable, decision blocked, next way to verify |

### Modes

1. **Evidence mode (default).** Shows all selected verified layers and object maturity.
2. **Route mode.** Shows only spatially valid connections. An animated dotted trace can run along a displayed hydrographic segment, but it is captioned `spatial route for review — not an inundation model`.
3. **People and infrastructure mode.** Emphasizes OSM and GHSL planning context. It never displays a casualty count or calls any asset affected without a validated exposure/impact model.
4. **Year compare mode.** The user picks two available local years. The current and reference segmentations have distinct outlines, a slider/crossfade, and a comparability badge.

### Issue queue

The right rail contains no generic `risk score`. It ranks 3–5 evidence gaps from the existing Value-of-Information/evaluation response. Each card has:

- a severity defined as `decision impact`, not danger;
- the named object or variable;
- why this information changes an admissible pathway;
- source/maturity label;
- one concrete next action;
- map focus behaviour.

Selecting a card flies the map to the object, applies a pulse outline, opens the evidence inspector, and updates the `next best action` card. The selection is reflected in the URL query so a presenter can share a precise screen state.

### Evidence inspector

The inspector is a stable component with four fields: `What is visible`, `What may be inferred`, `What is unknown`, and `What would resolve it`. It must remain visible instead of relying solely on popups.

### Cascade ribbon

A bottom overlay turns the selected local context into an inspectable sequence:

`glacier inventory / annual observation → lake context → outlet or geometry gap → river/basin context → asset/population planning context`.

Each edge is tagged `observed`, `spatial proximity`, `requires verification`, or `blocked`. A route never implies causality merely because two objects are near each other.

## Motion and presentation quality

- Object selection: 180–250 ms focus/pulse, not a perpetual animation.
- Layer transition and year comparison: 300–500 ms crossfade.
- Route mode: sparse particles travel only on an already displayed river segment; motion pauses when the tab is inactive.
- Results that change after a scan appear with a single, readable highlight rather than counters that constantly animate.
- Respect `prefers-reduced-motion`; in that mode every state change is instant and no particles run.
- Keyboard focus, popup text, legend symbols, and colour contrast must work without colour alone.

## Data and API contract

Existing endpoints remain the primary source of truth:

- `GET /api/risk-twin/context/{rgi_id}` for RGI, lakes, rivers, basins, historical records, assets, population and source limitations.
- `GET /api/years/{year}/map-layer` for the local annual segmentation artefact.
- `GET /api/risk-twin/regional-scan` for observation candidates.
- `POST /api/risk-twin/evaluate` for typed observations, abstention, and next-observation ranking.

The implementation will introduce a frontend-only normalized `EvidenceMapObject` view model first. It maps every API feature to:

```ts
id, kind, name, geometry, source, temporalCoverage,
maturity, allowedClaim, prohibitedClaim, issue?, nextAction?
```

No calculated probability, impact amount, destination route, lake volume, structural efficacy, or population-at-risk count may be added to this view model unless an API source explicitly provides it with provenance and validation status.

## Component boundaries

The current `RiskTwinMap` is refactored into focused components without changing its public page-level inputs in the first pass.

- `RiskTwinMapShell`: Leaflet lifecycle, basemap fallback, viewport, keyboard map controls.
- `EvidenceLayerRegistry`: deterministic mapping from `EvidenceMapObject.kind` to Leaflet layer rendering and legend.
- `EvidenceObjectInspector`: selected-object data and claim boundary.
- `EvidenceIssueQueue`: ranking, focus requests, empty and loading states.
- `EvidenceRouteOverlay`: cascade ribbon and clearly typed map-route animation.
- `YearComparisonControl`: available years, compare state, artefact mismatch warning.
- `RiskTwinPage`: loads API data, owns query-state and evaluation workflow; no Leaflet rendering logic.

## Error handling and fail-closed behaviour

- If a scientific context endpoint fails, preserve RGI geometry and render a clear missing-source panel.
- If a map base tile fails, retain all local vector layers and show a small non-blocking notice.
- If an annual layer is unavailable, disable only year comparison and explain why.
- If no OSM/GHSL object is locally available, do not render synthetic examples; show `No local planning context loaded` with the source requirement.
- If an item has no authoritative name, show its source identifier and `unnamed source record`; never fabricate a place name.

## Acceptance criteria

1. Selecting any map object or issue card changes the same inspector and map focus.
2. All visible markers have a source/maturity/claim-boundary path available in the inspector.
3. The map works with local layers when external basemap tiles fail.
4. A user can compare two locally available years and see an explicit comparability state.
5. No screen contains a synthetic lake, building, event, probability, impact estimate, or warning styled as local evidence.
6. `prefers-reduced-motion`, keyboard navigation, focus visibility, and non-colour labels pass the project's accessibility checks.
7. Frontend unit tests cover view-model normalization, issue selection, no-data states, and safety-language rendering; browser tests cover the primary selection and year-compare route.
8. `npm run lint`, affected frontend tests, API tests, and production build pass before handoff.

## Delivery sequence

1. Implement the normalized evidence view model and focused map components.
2. Add named objects, inspector, issue queue, year comparison, and source-aware layer controls.
3. Add optional terrain/satellite styling, motion, accessibility and offline failure states.
4. Test with actual local context, then update Operations, Jury, and Reports to link to the same selected evidence state rather than duplicating claims.
5. Only after this map is verified, advance the broader project work: evidence package, repeatable regional scans, adjudication workflow, external-region evaluation, and expert-reviewed operational pathways.

## Out of scope for this design

- Operational GLOF warning, emergency dispatch, or an official alert.
- Calibrated event probability, inundation depth, impact/casualty estimate, or engineering recommendation.
- Invented examples used as a substitute for missing local data.
- A requirement to obtain third-party basemap imagery during a presentation.
