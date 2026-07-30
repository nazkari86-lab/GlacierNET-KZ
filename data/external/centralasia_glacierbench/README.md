# CentralAsia-GlacierBench local source cache

This directory contains real third-party datasets and external model artifacts
used by CentralAsia-GlacierBench. Large files are intentionally excluded from
Git. Recreate the compact cache with:

```bash
python scripts/sync_centralasia_glacierbench.py
```

The command is resumable. It writes `sync_manifest.json` with local SHA-256
digests. Upstream checksums are enforced where the publisher provides them.
Dataset presence is not treated as evaluation success; the generated benchmark
report keeps data readiness and measured performance separate.

`GLID.tar.gz` and `GSDD.tar.gz` are intentionally outside the compact profile.
Use `--include-large` only when at least the runner-reported free-space
requirement is available. The sync refuses the request before download when the
safety margin is not met.
