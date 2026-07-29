"""Compact, evidence-only MCP catalog for GlacierNET-KZ.

Every registered tool either reads a physical local artifact or invokes the
trusted glacier-first inference workflow.  Research scaffolds, random fallback
arrays, untrained architectures, and synthetic scores are intentionally absent.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import HTTPException

logger = logging.getLogger(__name__)

ToolFunction = Callable[..., dict[str, Any]]
TOOL_REGISTRY: dict[str, dict[str, Any]] = {}


def _register(
    name: str,
    function: ToolFunction,
    description: str,
    parameters: dict[str, dict[str, Any]],
) -> None:
    TOOL_REGISTRY[name] = {
        "function": function,
        "description": description,
        "parameters": parameters,
    }


def _ok(data: Any) -> dict[str, Any]:
    return {"status": "success", "data": data}


def _error(message: str) -> dict[str, Any]:
    return {"status": "error", "error": message}


def list_models() -> dict[str, Any]:
    """List only models that can actually run in the current checkout."""
    from app.routers.models import list_models as list_available_models

    models = list_available_models()
    return _ok(
        {
            "models": models,
            "count": len(models),
            "scope": "physical model artifacts and deterministic weight-free baselines",
        }
    )


def get_model_info(model_name: str) -> dict[str, Any]:
    """Inspect one model without implying performance that was not measured."""
    from app.routers.models import list_all_models

    model = next((item for item in list_all_models() if item["name"] == model_name), None)
    if model is None:
        raise HTTPException(404, f"Unknown model: {model_name}")
    return _ok(model)


def get_ml_readiness() -> dict[str, Any]:
    """Return trusted artifacts, compatible years, and benchmark claim limits."""
    from app.services.ml_workspace_service import ml_readiness

    return _ok(ml_readiness())


def analyze_registered_glacier(
    rgi_id: str,
    year: int,
    model_name: str = "temporal_s2_terrain_s1",
    use_tta: bool = True,
    context_m: int = 400,
    refresh: bool = False,
) -> dict[str, Any]:
    """Run real multimodal inference for one RGI glacier and local year."""
    from app.config import MCP_INFERENCE_ENABLED
    from app.services.ml_workspace_service import analyze_glacier

    if not MCP_INFERENCE_ENABLED:
        return _error(
            "MCP inference is disabled. Use the dedicated /ml workflow, or set "
            "MCP_INFERENCE_ENABLED=true for a trusted local deployment."
        )
    return _ok(
        analyze_glacier(
            rgi_id,
            year=year,
            model_name=model_name,
            use_tta=use_tta,
            context_m=context_m,
            refresh=refresh,
        )
    )


def list_ml_cases(limit: int = 20) -> dict[str, Any]:
    """List persisted, reproducible glacier-level inference cases."""
    from app.services.ml_workspace_service import list_ml_cases as list_cases

    return _ok(list_cases(limit=limit))


def inspect_ml_case(case_id: str) -> dict[str, Any]:
    """Open the manifest and evidence links of one persisted ML case."""
    from app.services.ml_workspace_service import get_ml_case

    return _ok(get_ml_case(case_id))


def list_local_years(strict_only: bool = False) -> dict[str, Any]:
    """List years backed by local result tables and on-disk artifacts."""
    from app.routers.years import list_years

    return _ok(list_years(strict_only=strict_only))


def inspect_local_year(year: int) -> dict[str, Any]:
    """Inspect provenance, quality, area, and artifacts for one local year."""
    from app.routers.years import get_year

    return _ok(get_year(year))


def compare_local_years(from_year: int, to_year: int) -> dict[str, Any]:
    """Compare two local years while retaining all comparability warnings."""
    from app.routers.years import compare_years

    return _ok(compare_years(from_year=from_year, to_year=to_year))


def search_glaciers(
    search: str = "",
    named_only: bool = False,
    min_area_km2: float = 0.0,
    limit: int = 20,
) -> dict[str, Any]:
    """Search the physical RGI 7.0 study-area registry."""
    from app.services.glacier_registry_service import list_glaciers

    return _ok(
        list_glaciers(
            search=search,
            named_only=named_only,
            min_area_km2=min_area_km2,
            limit=limit,
        )
    )


def inspect_glacier_timeseries(rgi_id: str, method: str = "ndsi") -> dict[str, Any]:
    """Measure masks inside one fixed RGI polygon and preserve the caveat."""
    from app.services.glacier_registry_service import glacier_timeseries

    return _ok(glacier_timeseries(rgi_id, method))


def get_risk_twin_context(
    rgi_id: str,
    year: int = 2024,
    buffer_km: float = 10.0,
    lake_inventory_year: int = 2023,
) -> dict[str, Any]:
    """Return real glacier, lake, river, terrain, climate, and exposure context."""
    from app.services.risk_twin_context_service import risk_twin_context

    return _ok(
        risk_twin_context(
            rgi_id=rgi_id,
            year=year,
            buffer_km=buffer_km,
            lake_inventory_year=lake_inventory_year,
        )
    )


def scan_regional_lakes(inventory_year: int = 2023, buffer_km: float = 10.0) -> dict[str, Any]:
    """Rank real lake-inventory changes for follow-up, not hazard probability."""
    from app.services.risk_twin_context_service import regional_lake_screening

    return _ok(regional_lake_screening(inventory_year=inventory_year, buffer_km=buffer_km))


def list_datasets(limit: int = 100) -> dict[str, Any]:
    """List physical Sentinel/Landsat datasets registered from local files."""
    from app.routers.datasets import CORE_DIR, PREDICTIONS, RAW_LS, RAW_S2

    records: list[dict[str, Any]] = []
    for directory, prefix, sensor in (
        (RAW_S2, "sentinel2", "Sentinel-2"),
        (RAW_LS, "landsat", "Landsat"),
    ):
        for path in sorted(directory.glob(f"{prefix}_*.tif")):
            try:
                year = int(path.stem.rsplit("_", 1)[-1])
            except ValueError:
                continue
            prediction_dir = PREDICTIONS / str(year)
            records.append(
                {
                    "id": f"local-{prefix}-{year}",
                    "name": f"Ili Alatau {sensor} {year}",
                    "sensor": sensor,
                    "year": year,
                    "size_mb": round(path.stat().st_size / 1024**2, 1),
                    "source_path": str(path.relative_to(CORE_DIR)),
                    "prediction_artifacts": sorted(item.name for item in prediction_dir.glob("*_mask.tif")),
                    "scope": "physical local composite",
                }
            )
    records.sort(key=lambda item: (item["year"], item["sensor"]), reverse=True)
    return _ok(
        {
            "datasets": records[:limit],
            "total": len(records),
            "limit": limit,
            "source": "on-disk GeoTIFF inventory; independent of mutable API metadata",
        }
    )


def get_project_stats() -> dict[str, Any]:
    """Summarize the evidence-bearing project core without fabricated metrics."""
    from app.services.glacier_registry_service import list_glaciers
    from app.services.ml_workspace_service import list_ml_cases as list_cases

    years = list_local_years()["data"]
    models = list_models()["data"]
    glaciers = list_glaciers(limit=1)
    cases = list_cases(limit=100)
    return _ok(
        {
            "local_years": years["total"],
            "strict_trend_years": sum(bool(item["include_in_strict_trend"]) for item in years["years"]),
            "rgi_glaciers": glaciers["total"],
            "available_models": models["count"],
            "persisted_ml_cases": cases["total_returned"],
            "source": "physical local registries, artifacts, and result manifests",
            "claim_boundary": (
                "Counts describe available project evidence; they are not independent "
                "accuracy, operational-warning, or generalisation validation."
            ),
        }
    )


_register(
    "get_project_stats",
    get_project_stats,
    "Verified project counts from physical registries and artifacts",
    {},
)
_register("list_models", list_models, "List models that can run locally", {})
_register(
    "get_model_info",
    get_model_info,
    "Inspect one registered model and its availability",
    {"model_name": {"type": "string", "required": True}},
)
_register(
    "get_ml_readiness",
    get_ml_readiness,
    "Inspect deployable ML artifacts, compatible years, benchmarks, and claim limits",
    {},
)
_register(
    "analyze_registered_glacier",
    analyze_registered_glacier,
    "Run trusted glacier-first inference and persist an evidence case (explicit deployment opt-in required)",
    {
        "rgi_id": {"type": "string", "required": True},
        "year": {"type": "integer", "required": True},
        "model_name": {
            "type": "string",
            "default": "temporal_s2_terrain_s1",
            "enum": ["temporal_s2_terrain_s1", "temporal_s2_terrain"],
        },
        "use_tta": {"type": "boolean", "default": True},
        "context_m": {"type": "integer", "default": 400, "minimum": 0, "maximum": 2000},
        "refresh": {"type": "boolean", "default": False},
    },
)
_register(
    "list_ml_cases",
    list_ml_cases,
    "List persisted glacier-level model evidence cases",
    {"limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100}},
)
_register(
    "inspect_ml_case",
    inspect_ml_case,
    "Inspect one persisted model evidence case",
    {"case_id": {"type": "string", "required": True}},
)
_register(
    "list_local_years",
    list_local_years,
    "List locally verified analysis years",
    {"strict_only": {"type": "boolean", "default": False}},
)
_register(
    "inspect_local_year",
    inspect_local_year,
    "Inspect one local year with provenance and quality caveats",
    {"year": {"type": "integer", "required": True}},
)
_register(
    "compare_local_years",
    compare_local_years,
    "Compare two local years without discarding comparability warnings",
    {
        "from_year": {"type": "integer", "required": True},
        "to_year": {"type": "integer", "required": True},
    },
)
_register(
    "search_glaciers",
    search_glaciers,
    "Search the physical RGI 7.0 study-area registry",
    {
        "search": {"type": "string", "default": ""},
        "named_only": {"type": "boolean", "default": False},
        "min_area_km2": {"type": "number", "default": 0.0, "minimum": 0},
        "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100},
    },
)
_register(
    "inspect_glacier_timeseries",
    inspect_glacier_timeseries,
    "Inspect physical within-RGI mask measurements for one glacier",
    {
        "rgi_id": {"type": "string", "required": True},
        "method": {"type": "string", "default": "ndsi", "enum": ["ndsi", "rf", "unet"]},
    },
)
_register(
    "get_risk_twin_context",
    get_risk_twin_context,
    "Load real multi-layer spatial context for one glacier",
    {
        "rgi_id": {"type": "string", "required": True},
        "year": {"type": "integer", "default": 2024, "minimum": 2017, "maximum": 2024},
        "buffer_km": {"type": "number", "default": 10.0, "exclusiveMinimum": 0, "maximum": 30},
        "lake_inventory_year": {"type": "integer", "default": 2023},
    },
)
_register(
    "scan_regional_lakes",
    scan_regional_lakes,
    "Automatically rank real regional lake changes for observation follow-up",
    {
        "inventory_year": {"type": "integer", "default": 2023},
        "buffer_km": {"type": "number", "default": 10.0, "exclusiveMinimum": 0},
    },
)
_register(
    "list_datasets",
    list_datasets,
    "List physical local satellite datasets",
    {"limit": {"type": "integer", "default": 100, "minimum": 1, "maximum": 100}},
)


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return deterministic MCP definitions for the evidence-only catalog."""
    return [
        {
            "name": name,
            "description": meta["description"],
            "inputSchema": {
                "type": "object",
                "properties": meta["parameters"],
                "required": [key for key, value in meta["parameters"].items() if value.get("required")],
                "additionalProperties": False,
            },
        }
        for name, meta in TOOL_REGISTRY.items()
    ]


def execute_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute one known real-data tool and fail closed for every other name."""
    meta = TOOL_REGISTRY.get(tool_name)
    if meta is None:
        return _error(
            f"Unknown or removed tool '{tool_name}'. Available evidence tools: {', '.join(sorted(TOOL_REGISTRY))}"
        )
    allowed = set(meta["parameters"])
    unexpected = sorted(set(arguments) - allowed)
    if unexpected:
        return _error(f"Invalid arguments for '{tool_name}': unexpected {unexpected}")
    merged = dict(arguments)
    for key, definition in meta["parameters"].items():
        if key not in merged and "default" in definition:
            merged[key] = definition["default"]
    missing = [
        key for key, definition in meta["parameters"].items() if definition.get("required") and key not in merged
    ]
    if missing:
        return _error(f"Invalid arguments for '{tool_name}': missing {missing}")
    try:
        return meta["function"](**merged)
    except HTTPException as exc:
        return _error(str(exc.detail))
    except (FileNotFoundError, ValueError) as exc:
        return _error(str(exc))
    except TypeError as exc:
        return _error(f"Invalid arguments for '{tool_name}': {exc}")
    except Exception as exc:  # pragma: no cover - defensive API boundary
        logger.exception("MCP tool %s failed", tool_name)
        return _error(f"Tool '{tool_name}' failed: {exc}")
