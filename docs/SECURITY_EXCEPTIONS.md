# Dependency security exceptions

The default policy is zero unreviewed dependency findings. Temporary exceptions
are stored in `security-exceptions.json`, have a mandatory review date, and are
enforced by `scripts/audit_dependencies.py`.

## Why the exceptions exist

GlacierNET-KZ uses TensorFlow 2.15.1, the newest TensorFlow release that keeps
the Keras 2 SavedModel directory contract used by the trained, versioned model
artifacts. Keras 3 changes that persistence contract, so a direct upgrade would
make existing training, evaluation, and model artifacts incompatible.

The remaining Keras advisories concern unsafe model deserialization. Production
prediction and benchmark evaluation now reject symlinks, paths outside the
project, unregistered models, and any artifact whose SHA-256 differs from
`models/trusted_artifacts.json`. The API's unvalidated research tools are also
disabled by default.

TensorFlow 2.15 requires protobuf below version 5. GlacierNET-KZ does not accept
arbitrary protobuf payloads through its API, and the TensorFlow model artifacts
it parses are covered by the same exact-hash trust registry.

These are mitigations, not claims that the upstream defects are fixed. The
exceptions expire on **2026-08-09**. At review time, migrate to a compatible
patched TensorFlow/Keras line if one is available; otherwise renew only after a
fresh threat review.

Run:

```bash
python scripts/audit_dependencies.py
```
