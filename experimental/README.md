# Experimental Multi-Language Stacks (Phase 9)

These components are **research prototypes** — not part of the production Docker path
(`docker-compose.yml` runs `glacierkz-api` + `glacierkz-web` only).

| Directory | Language | Purpose |
|-----------|----------|---------|
| `glacierkz-c/` | C11 | Low-level GeoTIFF raster I/O and CLI tools |
| `glacierkz-native/` | C++17 | SIMD/GDAL performance library (+ optional pybind11) |
| `glacierkz-go/` | Go 1.22 | CLI gateway (`gzcli`) proxying to FastAPI |
| `glacierkz-java/` | Java 21 | Spring Boot + Kafka batch pipeline |
| `glacierkz-dotnet/` | C# | ASP.NET Core + Blazor alternative stack |

## Status

- Individual unit tests exist per component
- **Not wired** into CI or Docker Compose
- Integration checklist: see `plans/MASTER_PLAN.md` Phase 9

## Quick start (per component)

```bash
# C library
cd experimental/glacierkz-c && cmake -B build && cmake --build build && ctest --test-dir build

# Go CLI
cd experimental/glacierkz-go && go test ./...

# .NET (requires JWT_SECRET env var, min 32 chars)
export JWT_SECRET="your-local-dev-secret-at-least-32-chars"
cd experimental/glacierkz-dotnet && dotnet test
```

Production ML inference remains in `src/` (TensorFlow/Keras) via `glacierkz-api`.
