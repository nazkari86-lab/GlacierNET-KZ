# Open-source evaluation for the Event Radar

Reviewed on 2026-07-31. Repository metadata and licences must be rechecked
before any future vendoring or dependency upgrade.

| Project | Licence | Decision | Reason |
|---|---|---|---|
| [Irchel Geoparser](https://github.com/dguzh/geoparser) | MIT | adopt architecture, not dependency | Strong customizable place extraction/linking and custom-gazetteer design. The current radar needs only a small RGI gazetteer and source coordinates, so a full NLP stack would add weight without validated benefit. |
| [feedparser](https://github.com/kurtmckee/feedparser) | BSD-style | compatible future dependency | Mature RSS/Atom parser. The first implementation uses the Python standard library for the narrow configured-feed contract, avoiding another runtime dependency. Adopt feedparser when real publisher feeds demonstrate malformed formats that justify it. |
| [Ushahidi Platform](https://github.com/ushahidi/platform) | AGPL-3.0 | design reference only | Excellent event/evidence workflow and crisis-mapping concepts. No Ushahidi code is copied or linked: its full platform and copyleft obligations are unnecessary for the compact MIT service. |
| [OpenEWS](https://github.com/open-ews/open-ews) | MIT | future dissemination adapter | Useful API-driven emergency-message architecture. Dissemination remains disabled until an authority validates recipients, message templates, escalation policy, and operational responsibility. |
| [gdelt-doc-api](https://github.com/alex9smith/gdelt-doc-api) | MIT | do not depend | A useful client reference, but GDELT Cloud v2 has a small documented HTTP surface. Direct typed requests preserve timeout, cache, and evidence-boundary control with less dependency risk. |
| PetaBencana legacy SITI server | repository marked deprecated | reject | An archived/deprecated operational path is not a safe foundation for a new evidence pipeline. Community-reporting concepts remain relevant, but a maintained component must be selected if that feature is later added. |

## What was actually reused

No third-party source code was copied into GlacierNET-KZ. The implementation
uses independently written adapters and adopts four general patterns:

1. configurable gazetteer-based geolocation;
2. immutable event/source identity and evidence status;
3. small source adapters behind one normalized event contract;
4. strict separation between detection, verification, and dissemination.

## Why a custom lightweight core is preferable now

The scientific bottleneck is not feed parsing. It is labelled, timestamped,
leakage-safe evidence connecting pre-event signals to verified events and
controls. A large crisis platform or NLP pipeline would improve feature count
without improving calibration. The current core therefore spends complexity
on provenance, distance, failure handling, claim boundaries, and tests.

## Revisit criteria

- Add Irchel Geoparser when at least two real publishers omit coordinates and a
  manually checked multilingual toponym set exists.
- Add feedparser when configured official feeds fail the standard-library
  parser in a reproducible fixture.
- Add a maintained community-reporting platform only with moderation,
  consent, privacy, and misinformation controls.
- Add OpenEWS only after an authorized agency owns the warning decision and a
  separate operational validation is complete.

