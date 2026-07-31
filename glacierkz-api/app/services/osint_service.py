"""Evidence-bounded OSINT event radar for cryosphere screening.

The service deliberately separates a *reported signal* from a physical hazard
estimate.  It stores source metadata, applies deterministic spatial linking,
and proposes an observation action; it never converts media volume or an
earthquake report into a GLOF probability.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from defusedxml import ElementTree

from app.config import DATA_DIR
from app.services.glacier_registry_service import list_glaciers
from src.centralasia_benchmark.osint_evidence import build_osint_prediction_readiness

SCHEMA = "glaciernet-kz.osint-radar.v1"
DEFAULT_TTL_SECONDS = 15 * 60
CENTRAL_ASIA_BOUNDS = {
    "minlatitude": 40.0,
    "maxlatitude": 47.5,
    "minlongitude": 67.0,
    "maxlongitude": 88.0,
}
MAX_LINK_DISTANCE_KM = 350.0
USER_AGENT = "GlacierNET-KZ/0.5 (+https://github.com/nazkari86-lab/GlacierNET-KZ)"
CACHE_PATH = Path(os.getenv("OSINT_CACHE_PATH", str(DATA_DIR / "osint" / "event-radar.json")))

_lock = threading.Lock()
_memory_snapshot: dict[str, Any] | None = None
_memory_timestamp = 0.0

SOURCE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "usgs_earthquakes",
        "name": "USGS Earthquake Catalog",
        "tier": "authoritative_sensor_catalog",
        "mode": "live_api",
        "url": "https://earthquake.usgs.gov/fdsnws/event/1/",
        "license_note": "Public US government data; retain source attribution.",
        "role": "Regional seismic trigger context; not evidence of a glacier-lake failure.",
    },
    {
        "id": "gdacs",
        "name": "Global Disaster Alert and Coordination System",
        "tier": "official_multilateral",
        "mode": "live_api",
        "url": "https://www.gdacs.org/",
        "license_note": "Display metadata and link to the originating GDACS event.",
        "role": "Cross-border disaster-event corroboration and situational context.",
    },
    {
        "id": "kazhydromet",
        "name": "Kazhydromet",
        "tier": "official_national",
        "mode": "official_link",
        "url": "https://www.kazhydromet.kz/en/sedimentary-genesis/ezhednevnyy-byulleten-selevoy-opasnosti-dozhdevogo-genezisa",
        "license_note": "Link to the official bulletin; do not republish full bulletin text.",
        "role": "Authoritative mudflow and weather bulletin review.",
    },
    {
        "id": "kazakhstan_mcs",
        "name": "Ministry for Emergency Situations of Kazakhstan",
        "tier": "official_national",
        "mode": "official_link",
        "url": "https://www.gov.kz/memleket/entities/emer?lang=en",
        "license_note": "Link to the official notice; preserve publication context.",
        "role": "Official warnings, field operations, and high-mountain lake monitoring.",
    },
    {
        "id": "reliefweb",
        "name": "ReliefWeb / UN OCHA",
        "tier": "curated_humanitarian",
        "mode": "requires_appname",
        "url": "https://reliefweb.int/",
        "license_note": "Partner content may be copyrighted; store metadata and canonical links only.",
        "role": "Curated humanitarian reports after an approved appname is configured.",
    },
    {
        "id": "gdelt_cloud",
        "name": "GDELT Cloud",
        "tier": "open_news_intelligence",
        "mode": "requires_api_key",
        "url": "https://gdeltcloud.com/",
        "license_note": "Store derived metadata and canonical article links, not copied article bodies.",
        "role": "Optional multilingual story clustering; never treated as an official alert.",
    },
)

KEYWORDS: dict[str, tuple[str, ...]] = {
    "glacier_lake": (
        "glacial lake",
        "glacier lake",
        "ледниковое озеро",
        "моренное озеро",
        "мұздық көл",
    ),
    "mudflow": ("mudflow", "debris flow", "селевой", "сель", "сел қауп", "лай көшкін"),
    "flood": ("flood", "flash flood", "наводнен", "павод", "су тасқын"),
    "avalanche": ("avalanche", "лавин", "қар көшкін"),
    "heavy_precipitation": ("heavy rain", "extreme rainfall", "ливн", "сильный дожд", "нөсер"),
    "glacier_change": ("glacier", "ice melt", "ледник", "таяние льда", "мұздық"),
    "earthquake": ("earthquake", "seismic", "землетряс", "жер сілкін"),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        # USGS timestamps are milliseconds.
        seconds = float(value) / 1000 if float(value) > 10_000_000_000 else float(value)
        try:
            return datetime.fromtimestamp(seconds, timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None


def _haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius = 6371.0088
    phi_a, phi_b = math.radians(lat_a), math.radians(lat_b)
    d_phi = math.radians(lat_b - lat_a)
    d_lambda = math.radians(lon_b - lon_a)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi_a) * math.cos(phi_b) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _clean_text(value: Any, limit: int = 500) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def classify_event(text: str, fallback: str = "other") -> tuple[str, list[str]]:
    normalized = text.casefold()
    matches = [event_type for event_type, words in KEYWORDS.items() if any(word in normalized for word in words)]
    if fallback != "other" and fallback not in matches:
        matches.insert(0, fallback)
    return (matches[0] if matches else fallback), matches


def _stable_id(source_id: str, external_id: str, url: str, title: str) -> str:
    raw = "|".join((source_id, external_id, url, title.casefold()))
    return f"{source_id}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def parse_usgs(payload: dict[str, Any], fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Normalize an official USGS GeoJSON response without adding hazard claims."""
    fetched = fetched_at or _utc_now()
    events: list[dict[str, Any]] = []
    for feature in payload.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        properties = feature.get("properties") or {}
        if len(coordinates) < 2:
            continue
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        title = _clean_text(properties.get("title") or properties.get("place") or "USGS earthquake")
        published = _parse_datetime(properties.get("time")) or fetched
        magnitude = properties.get("mag")
        url = str(properties.get("url") or properties.get("detail") or "")
        external_id = str(feature.get("id") or url or title)
        events.append(
            {
                "id": _stable_id("usgs_earthquakes", external_id, url, title),
                "external_id": external_id,
                "source_id": "usgs_earthquakes",
                "source_name": "USGS Earthquake Catalog",
                "source_tier": "authoritative_sensor_catalog",
                "title": title,
                "summary": f"Catalogued magnitude {magnitude} earthquake."
                if magnitude is not None
                else "Catalogued earthquake.",
                "url": url,
                "published_at": _iso(published),
                "event_type": "earthquake",
                "matched_topics": ["earthquake"],
                "latitude": latitude,
                "longitude": longitude,
                "location_name": _clean_text(properties.get("place"), 180),
                "geolocation_method": "source_coordinates",
                "geolocation_uncertainty_km": None,
                "magnitude": float(magnitude) if magnitude is not None else None,
                "severity_label": None,
                "fetched_at": _iso(fetched),
            }
        )
    return events


def parse_gdacs(payload: dict[str, Any], fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Normalize GDACS GeoJSON defensively across documented response variants."""
    fetched = fetched_at or _utc_now()
    events: list[dict[str, Any]] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if geometry.get("type") != "Point" or len(coordinates) < 2:
            continue
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        event_code = str(
            properties.get("eventtype") or properties.get("eventType") or properties.get("event_type") or "other"
        ).upper()
        event_type = {
            "EQ": "earthquake",
            "FL": "flood",
            "TC": "storm",
            "DR": "drought",
            "VO": "volcano",
            "WF": "wildfire",
        }.get(event_code, "other")
        title = _clean_text(
            properties.get("name")
            or properties.get("eventname")
            or properties.get("title")
            or f"GDACS {event_code} event"
        )
        url = str(properties.get("url") or properties.get("link") or "")
        external_id = str(properties.get("eventid") or properties.get("eventId") or url or title)
        published = (
            _parse_datetime(properties.get("fromdate") or properties.get("fromDate") or properties.get("date"))
            or fetched
        )
        events.append(
            {
                "id": _stable_id("gdacs", external_id, url, title),
                "external_id": external_id,
                "source_id": "gdacs",
                "source_name": "GDACS",
                "source_tier": "official_multilateral",
                "title": title,
                "summary": "GDACS event metadata; open the source record for the authoritative description.",
                "url": url,
                "published_at": _iso(published),
                "event_type": event_type,
                "matched_topics": [event_type],
                "latitude": latitude,
                "longitude": longitude,
                "location_name": _clean_text(properties.get("country") or properties.get("location"), 180),
                "geolocation_method": "source_coordinates",
                "geolocation_uncertainty_km": None,
                "magnitude": None,
                "severity_label": _clean_text(properties.get("alertlevel") or properties.get("alertLevel"), 40) or None,
                "fetched_at": _iso(fetched),
            }
        )
    return events


def parse_feed(xml_text: str, source: dict[str, Any], fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Parse configured RSS/Atom metadata using the standard library.

    Full article bodies are intentionally discarded. Items without explicit
    coordinates remain visible in the source ledger but cannot become map
    markers unless a local gazetteer resolves their location.
    """
    fetched = fetched_at or _utc_now()
    root = ElementTree.fromstring(xml_text)
    entries = root.findall(".//item")
    if not entries:
        entries = root.findall(".//{*}entry")
    events: list[dict[str, Any]] = []
    for entry in entries:
        values = {child.tag.rsplit("}", 1)[-1]: _clean_text(child.text) for child in entry}
        title = values.get("title", "")
        summary = values.get("description") or values.get("summary") or ""
        combined = f"{title} {summary}"
        event_type, topics = classify_event(combined)
        if event_type == "other":
            continue
        link = values.get("link", "")
        if not link:
            link_node = entry.find("{*}link")
            link = str(link_node.attrib.get("href", "")) if link_node is not None else ""
        published = (
            _parse_datetime(values.get("pubDate") or values.get("published") or values.get("updated")) or fetched
        )
        lat = values.get("lat")
        lon = values.get("long") or values.get("lon")
        events.append(
            {
                "id": _stable_id(source["id"], values.get("guid", ""), link, title),
                "external_id": values.get("guid") or link or title,
                "source_id": source["id"],
                "source_name": source["name"],
                "source_tier": source["tier"],
                "title": title,
                "summary": summary[:240],
                "url": link,
                "published_at": _iso(published),
                "event_type": event_type,
                "matched_topics": topics,
                "latitude": float(lat) if lat else None,
                "longitude": float(lon) if lon else None,
                "location_name": "",
                "geolocation_method": "source_coordinates" if lat and lon else "unresolved",
                "geolocation_uncertainty_km": None,
                "magnitude": None,
                "severity_label": None,
                "fetched_at": _iso(fetched),
            }
        )
    return events


def parse_gdelt(payload: dict[str, Any], fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Normalize GDELT Cloud event cards, retaining only cryosphere keywords."""
    fetched = fetched_at or _utc_now()
    events: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        title = _clean_text(item.get("title") or "GDELT event")
        summary = _clean_text(item.get("summary"), 240)
        event_type, topics = classify_event(f"{title} {summary}")
        if event_type == "other":
            continue
        geo = item.get("geo") or {}
        latitude, longitude = geo.get("latitude"), geo.get("longitude")
        metrics = item.get("metrics") or {}
        url = str(item.get("primary_story_url") or item.get("url") or "")
        external_id = str(item.get("id") or item.get("event_code") or url or title)
        published = _parse_datetime(item.get("event_date")) or fetched
        events.append(
            {
                "id": _stable_id("gdelt_cloud", external_id, url, title),
                "external_id": external_id,
                "source_id": "gdelt_cloud",
                "source_name": "GDELT Cloud",
                "source_tier": "open_news_intelligence",
                "title": title,
                "summary": summary,
                "url": url,
                "published_at": _iso(published),
                "event_type": event_type,
                "matched_topics": topics,
                "latitude": float(latitude) if latitude is not None else None,
                "longitude": float(longitude) if longitude is not None else None,
                "location_name": _clean_text(geo.get("location") or geo.get("admin1") or geo.get("country"), 180),
                "geolocation_method": "provider_resolved_coordinates"
                if latitude is not None and longitude is not None
                else "unresolved",
                "geolocation_uncertainty_km": None,
                "magnitude": None,
                "severity_label": None,
                "provider_model_confidence": metrics.get("confidence"),
                "article_count": metrics.get("article_count"),
                "record_kind": "event_card",
                "fetched_at": _iso(fetched),
            }
        )
    return events


def parse_gdelt_stories(payload: dict[str, Any], fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Normalize GDELT Cloud story clusters without copying article bodies.

    GDELT event cards and story clusters are different products.  The latter is
    valuable for cryosphere monitoring because it clusters multilingual news
    even when there is no CAMEO-style event record.  It remains a reported
    signal, never a validated hazard or probability.
    """
    fetched = fetched_at or _utc_now()
    events: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        title = _clean_text(item.get("title") or item.get("headline") or "GDELT story cluster")
        summary = _clean_text(item.get("summary") or item.get("description"), 240)
        event_type, topics = classify_event(f"{title} {summary}")
        if event_type == "other":
            continue
        raw_geo = item.get("geo") or item.get("location") or {}
        geo = raw_geo if isinstance(raw_geo, dict) else {}
        latitude, longitude = geo.get("latitude"), geo.get("longitude")
        metrics = item.get("metrics") or {}
        top_articles = item.get("top_articles") or item.get("articles") or []
        first_article = top_articles[0] if isinstance(top_articles, list) and top_articles else {}
        url = str(
            item.get("url")
            or item.get("primary_story_url")
            or item.get("primary_article_url")
            or (first_article.get("url") if isinstance(first_article, dict) else "")
            or ""
        )
        external_id = str(item.get("id") or item.get("story_id") or url or title)
        published = _parse_datetime(item.get("story_date") or item.get("date") or item.get("published_at")) or fetched
        events.append(
            {
                "id": _stable_id("gdelt_cloud", f"story:{external_id}", url, title),
                "external_id": external_id,
                "source_id": "gdelt_cloud",
                "source_name": "GDELT Cloud",
                "source_tier": "open_news_intelligence",
                "title": title,
                "summary": summary,
                "url": url,
                "published_at": _iso(published),
                "event_type": event_type,
                "matched_topics": topics,
                "latitude": float(latitude) if latitude is not None else None,
                "longitude": float(longitude) if longitude is not None else None,
                "location_name": _clean_text(geo.get("location") or geo.get("admin1") or geo.get("country"), 180),
                "geolocation_method": "provider_resolved_coordinates"
                if latitude is not None and longitude is not None
                else "unresolved",
                "geolocation_uncertainty_km": None,
                "magnitude": None,
                "severity_label": None,
                "provider_model_confidence": metrics.get("confidence"),
                "article_count": metrics.get("article_count") or item.get("article_count"),
                "record_kind": "story_cluster",
                "fetched_at": _iso(fetched),
            }
        )
    return events


def parse_reliefweb(payload: dict[str, Any], fetched_at: datetime | None = None) -> list[dict[str, Any]]:
    """Normalize ReliefWeb report metadata without retaining report bodies."""
    fetched = fetched_at or _utc_now()
    events: list[dict[str, Any]] = []
    for row in payload.get("data", []):
        fields = row.get("fields") or {}
        title = _clean_text(fields.get("title") or "ReliefWeb report")
        event_type, topics = classify_event(title)
        if event_type == "other":
            continue
        url = str(fields.get("url") or fields.get("url_alias") or "")
        date_fields = fields.get("date") or {}
        published = _parse_datetime(date_fields.get("original") or date_fields.get("created")) or fetched
        countries = fields.get("country") or []
        location_name = ", ".join(
            _clean_text(country.get("name"), 80) for country in countries if isinstance(country, dict)
        )
        external_id = str(row.get("id") or url or title)
        events.append(
            {
                "id": _stable_id("reliefweb", external_id, url, title),
                "external_id": external_id,
                "source_id": "reliefweb",
                "source_name": "ReliefWeb / UN OCHA",
                "source_tier": "curated_humanitarian",
                "title": title,
                "summary": "Curated report metadata; open the source record for the report and originating organization.",
                "url": url,
                "published_at": _iso(published),
                "event_type": event_type,
                "matched_topics": topics,
                "latitude": None,
                "longitude": None,
                "location_name": location_name,
                "geolocation_method": "unresolved",
                "geolocation_uncertainty_km": None,
                "magnitude": None,
                "severity_label": None,
                "fetched_at": _iso(fetched),
            }
        )
    return events


def _nearest_glacier(
    event: dict[str, Any], glaciers: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, float | None]:
    if event.get("latitude") is None or event.get("longitude") is None:
        return None, None
    nearest: dict[str, Any] | None = None
    nearest_distance = math.inf
    for glacier in glaciers:
        centroid = glacier["centroid"]
        distance = _haversine_km(
            float(event["latitude"]),
            float(event["longitude"]),
            float(centroid["latitude"]),
            float(centroid["longitude"]),
        )
        if distance < nearest_distance:
            nearest, nearest_distance = glacier, distance
    return nearest, nearest_distance if nearest else None


def _recency_score(published_at: str, now: datetime) -> float:
    published = _parse_datetime(published_at)
    if not published:
        return 0.2
    age_hours = max(0.0, (now - published).total_seconds() / 3600)
    return max(0.0, min(1.0, math.exp(-age_hours / (24 * 14))))


def _source_reliability(tier: str) -> float:
    return {
        "official_national": 0.96,
        "authoritative_sensor_catalog": 0.94,
        "official_multilateral": 0.9,
        "curated_humanitarian": 0.82,
        "open_news_intelligence": 0.58,
    }.get(tier, 0.45)


def enrich_and_rank(
    events: list[dict[str, Any]], glaciers: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    current = now or _utc_now()
    enriched: list[dict[str, Any]] = []
    for event in events:
        nearest, distance = _nearest_glacier(event, glaciers)
        if distance is not None and distance > MAX_LINK_DISTANCE_KM:
            continue
        reliability = _source_reliability(str(event["source_tier"]))
        recency = _recency_score(str(event["published_at"]), current)
        spatial = 0.0 if distance is None else max(0.0, 1 - distance / MAX_LINK_DISTANCE_KM)
        completeness = (
            sum(event.get(key) not in (None, "") for key in ("title", "url", "published_at", "latitude", "longitude"))
            / 5
        )
        evidence_confidence = round(0.45 * reliability + 0.25 * completeness + 0.2 * spatial + 0.1 * recency, 3)
        trigger_weight = min(max(float(event.get("magnitude") or 0) / 7, 0.35), 1.0)
        observation_priority = round(100 * (0.35 * recency + 0.3 * spatial + 0.2 * reliability + 0.15 * trigger_weight))
        if distance is None:
            link_scope = "unresolved"
            rationale = "No source coordinates or auditable gazetteer match; not placed on the map."
        elif distance <= 25:
            link_scope = "near_glacier"
            rationale = (
                f"Source coordinate is {distance:.1f} km from the nearest RGI centroid; inspect local evidence now."
            )
        elif distance <= 120:
            link_scope = "regional_trigger_context"
            rationale = (
                f"Source coordinate is {distance:.1f} km from the nearest RGI centroid; regional trigger context only."
            )
        else:
            link_scope = "broad_context"
            rationale = f"Source coordinate is {distance:.1f} km from the nearest RGI centroid; too distant for a local hazard claim."
        action = {
            "earthquake": "Inspect the latest cloud-free optical/SAR scene and lake/dam evidence; do not infer damage from magnitude alone.",
            "mudflow": "Compare the reported corridor with HydroRIVERS and OSM assets, then request official field confirmation.",
            "flood": "Check downstream river/lake observations and the latest official hydrometeorological bulletin.",
            "glacier_lake": "Open the linked glacier/lake evidence case and verify boundary, freeboard, outlet and acquisition date.",
            "heavy_precipitation": "Review Kazhydromet precipitation/mudflow bulletins and prioritize a fresh SAR/optical acquisition.",
        }.get(str(event["event_type"]), "Review the primary source and acquire a directly relevant observation.")
        content_digest = hashlib.sha256(
            json.dumps(
                {key: event.get(key) for key in ("source_id", "external_id", "title", "url", "published_at")},
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        enriched.append(
            {
                **event,
                "content_sha256": content_digest,
                "linked_glacier": (
                    {
                        "rgi_id": nearest["rgi_id"],
                        "name": nearest["name"],
                        "name_ru": nearest["name_ru"],
                        "centroid": nearest["centroid"],
                    }
                    if nearest
                    else None
                ),
                "distance_to_glacier_km": round(distance, 2) if distance is not None else None,
                "link_scope": link_scope,
                "link_rationale": rationale,
                "source_reliability_0_1": reliability,
                "recency_score_0_1": round(recency, 3),
                "spatial_relevance_0_1": round(spatial, 3),
                "evidence_completeness_0_1": round(completeness, 3),
                "evidence_confidence_0_1": evidence_confidence,
                "observation_priority_0_100": observation_priority,
                "recommended_action": action,
                "hazard_probability": None,
                "claim_status": "reported_signal_not_validated_hazard",
            }
        )
    return _deduplicate(enriched)


def _deduplicate(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse exact source/url duplicates while preserving source provenance."""
    unique: dict[str, dict[str, Any]] = {}
    for event in events:
        url = str(event.get("url") or "")
        key = f"url:{urlparse(url).netloc}{urlparse(url).path}" if url else f"id:{event['id']}"
        current = unique.get(key)
        if current is None or event["observation_priority_0_100"] > current["observation_priority_0_100"]:
            unique[key] = event
    return sorted(
        unique.values(),
        key=lambda item: (item["observation_priority_0_100"], item["published_at"]),
        reverse=True,
    )


def _get_json(
    client: httpx.Client,
    url: str,
    params: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.get(url, params=params, headers=headers)
            if response.status_code == 204:
                return {"type": "FeatureCollection", "features": []}
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.15 * (2**attempt))
    if last_error:
        raise last_error
    return None


def _fetch_live(now: datetime) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    health: list[dict[str, Any]] = []
    # GDELT Cloud accepts an inclusive date window of at most 30 calendar
    # dates. `now - 30 days` plus today's date can be 31 dates, so make the
    # configured count inclusive and clamp it to the provider limit.
    lookback_days = min(max(int(os.getenv("OSINT_LOOKBACK_DAYS", "30")), 1), 30)
    start = now - timedelta(days=lookback_days - 1)
    with httpx.Client(timeout=httpx.Timeout(8.0, connect=4.0), headers={"User-Agent": USER_AGENT}) as client:
        try:
            payload = _get_json(
                client,
                "https://earthquake.usgs.gov/fdsnws/event/1/query",
                {
                    "format": "geojson",
                    "starttime": start.date().isoformat(),
                    **CENTRAL_ASIA_BOUNDS,
                    "minmagnitude": 2.5,
                    "orderby": "time",
                    "limit": 200,
                },
            )
            parsed = parse_usgs(payload or {}, now)
            events.extend(parsed)
            health.append({"source_id": "usgs_earthquakes", "status": "online", "items": len(parsed), "error": None})
        except (httpx.HTTPError, ValueError) as error:
            health.append(
                {"source_id": "usgs_earthquakes", "status": "unavailable", "items": 0, "error": type(error).__name__}
            )

        gdacs_url = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
        try:
            payload = _get_json(
                client,
                gdacs_url,
                {
                    "eventlist": "EQ;FL;TC;VO",
                    "fromdate": start.date().isoformat(),
                    "todate": now.date().isoformat(),
                },
            )
            parsed = parse_gdacs(payload or {}, now)
            events.extend(parsed)
            health.append({"source_id": "gdacs", "status": "online", "items": len(parsed), "error": None})
        except (httpx.HTTPError, ValueError) as error:
            health.append({"source_id": "gdacs", "status": "unavailable", "items": 0, "error": type(error).__name__})

        for variable, source_id in (
            ("KAZHYDROMET_OSINT_FEEDS", "kazhydromet"),
            ("GOV_KZ_OSINT_FEEDS", "kazakhstan_mcs"),
        ):
            urls = [item.strip() for item in os.getenv(variable, "").split(",") if item.strip()]
            source = next(item for item in SOURCE_CATALOG if item["id"] == source_id)
            count = 0
            errors = 0
            for url in urls:
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    parsed = parse_feed(response.text, source, now)
                    events.extend(parsed)
                    count += len(parsed)
                except (httpx.HTTPError, ElementTree.ParseError, ValueError):
                    errors += 1
            health.append(
                {
                    "source_id": source_id,
                    "status": "not_configured" if not urls else ("partial" if errors else "online"),
                    "items": count,
                    "error": f"{errors} feed(s) failed" if errors else None,
                }
            )

        reliefweb_appname = os.getenv("RELIEFWEB_APPNAME", "").strip()
        if reliefweb_appname:
            try:
                payload = _get_json(
                    client,
                    "https://api.reliefweb.int/v2/reports",
                    {
                        "appname": reliefweb_appname,
                        "limit": 100,
                        "sort[]": "date:desc",
                        "query[value]": "glacier glacial lake mudflow avalanche flood Kazakhstan Kyrgyzstan Tajikistan",
                        "fields[include][]": ["title", "url", "url_alias", "date", "country", "source"],
                    },
                )
                parsed = parse_reliefweb(payload or {}, now)
                events.extend(parsed)
                health.append({"source_id": "reliefweb", "status": "online", "items": len(parsed), "error": None})
            except (httpx.HTTPError, ValueError) as error:
                health.append(
                    {"source_id": "reliefweb", "status": "unavailable", "items": 0, "error": type(error).__name__}
                )
        else:
            health.append({"source_id": "reliefweb", "status": "ready_for_credentials", "items": 0, "error": None})

        gdelt_key = os.getenv("GDELT_CLOUD_API_KEY", os.getenv("GDELT_API_KEY", "")).strip()
        if gdelt_key:
            gdelt_params = {
                "date_start": start.date().isoformat(),
                "date_end": now.date().isoformat(),
                "region": "Central Asia",
                "bbox": "40,67,47.5,88",
                # Search in English, Russian, and Kazakh.  The normalizer below
                # still excludes material without a cryosphere-relevant topic.
                "search": "glacier glacial lake mudflow avalanche flood ледник ледниковое озеро сель наводнение мұздық сел тасқын",
                "languages": "ru,kk,en",
                "sort": "recent",
                "limit": 100,
                "include_images": "false",
            }
            parsed_gdelt: list[dict[str, Any]] = []
            gdelt_errors: list[str] = []
            for endpoint, parser in (
                ("events", parse_gdelt),
                ("stories", parse_gdelt_stories),
            ):
                try:
                    payload = _get_json(
                        client,
                        f"https://gdeltcloud.com/api/v2/{endpoint}",
                        gdelt_params,
                        headers={"Authorization": f"Bearer {gdelt_key}"},
                    )
                    parsed_gdelt.extend(parser(payload or {}, now))
                except (httpx.HTTPError, ValueError) as error:
                    # Keep the usable GDELT product live if its companion is
                    # temporarily unavailable or has a provider-side query limit.
                    gdelt_errors.append(f"{endpoint}:{type(error).__name__}")
            events.extend(parsed_gdelt)
            health.append(
                {
                    "source_id": "gdelt_cloud",
                    "status": "online" if not gdelt_errors else ("partial" if parsed_gdelt else "unavailable"),
                    "items": len(parsed_gdelt),
                    "error": ", ".join(gdelt_errors) or None,
                }
            )
        else:
            health.append({"source_id": "gdelt_cloud", "status": "ready_for_credentials", "items": 0, "error": None})
    return events, health


def _write_cache(snapshot: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CACHE_PATH)


def _read_cache() -> dict[str, Any] | None:
    try:
        payload = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return payload if payload.get("schema") == SCHEMA else None
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def build_event_radar(*, force_refresh: bool = False) -> dict[str, Any]:
    """Return a cached, provenance-rich live radar snapshot."""
    global _memory_snapshot, _memory_timestamp
    now_epoch = time.time()
    ttl = int(os.getenv("OSINT_CACHE_TTL_SECONDS", str(DEFAULT_TTL_SECONDS)))
    if not force_refresh and _memory_snapshot is not None and now_epoch - _memory_timestamp < ttl:
        return {**_memory_snapshot, "cache": {"status": "memory_hit", "ttl_seconds": ttl}}
    with _lock:
        if not force_refresh and _memory_snapshot is not None and now_epoch - _memory_timestamp < ttl:
            return {**_memory_snapshot, "cache": {"status": "memory_hit", "ttl_seconds": ttl}}
        disk = _read_cache()
        if not force_refresh and disk:
            generated = _parse_datetime(disk.get("generated_at"))
            if generated and (_utc_now() - generated).total_seconds() < ttl:
                _memory_snapshot, _memory_timestamp = disk, now_epoch
                return {**disk, "cache": {"status": "disk_hit", "ttl_seconds": ttl}}

        now = _utc_now()
        raw_events, source_health = _fetch_live(now)
        if not raw_events and disk:
            fallback = {
                **disk,
                "source_health": source_health,
                "cache": {"status": "stale_fallback", "ttl_seconds": ttl},
                "warnings": ["Live sources returned no usable items; showing the last cached snapshot."],
            }
            _memory_snapshot, _memory_timestamp = fallback, now_epoch
            return fallback
        glaciers = list_glaciers(limit=1000, include_geometry=False)["glaciers"]
        events = enrich_and_rank(raw_events, glaciers, now)
        snapshot = {
            "schema": SCHEMA,
            "generated_at": _iso(now),
            "region": {"name": "Central Asian glacier screening window", "bounds": CENTRAL_ASIA_BOUNDS},
            "events": events,
            "source_health": source_health,
            "summary": {
                "events_total": len(events),
                "near_glacier": sum(event["link_scope"] == "near_glacier" for event in events),
                "regional_trigger_context": sum(event["link_scope"] == "regional_trigger_context" for event in events),
                "official_or_authoritative": sum(
                    event["source_tier"]
                    in {"official_national", "official_multilateral", "authoritative_sensor_catalog"}
                    for event in events
                ),
                "unresolved": sum(event["link_scope"] == "unresolved" for event in events),
            },
            "method": {
                "spatial_link": "nearest RGI centroid, Haversine distance; maximum retained distance 350 km",
                "ranking": "deterministic observation priority from recency, distance, source tier, completeness and event metadata",
                "deduplication": "canonical URL/source identifier",
                "not_a_model": "No OSINT item is converted into a calibrated physical hazard probability.",
            },
            "claims_allowed": [
                "A named source reported or catalogued the displayed event.",
                "The source coordinate has the displayed distance to the nearest local RGI centroid.",
                "The event can prioritize acquisition and expert review.",
            ],
            "claims_not_allowed": [
                "The event caused glacier, lake, dam, or downstream damage.",
                "The linked glacier is hazardous because a report is nearby.",
                "The displayed priority is a probability of GLOF or harm.",
                "This screen is an official warning.",
            ],
            "warnings": [],
        }
        _write_cache(snapshot)
        _memory_snapshot, _memory_timestamp = snapshot, now_epoch
        return {**snapshot, "cache": {"status": "refreshed", "ttl_seconds": ttl}}


def source_catalog() -> dict[str, Any]:
    configured = {
        "kazhydromet": bool(os.getenv("KAZHYDROMET_OSINT_FEEDS")),
        "kazakhstan_mcs": bool(os.getenv("GOV_KZ_OSINT_FEEDS")),
        "reliefweb": bool(os.getenv("RELIEFWEB_APPNAME")),
        "gdelt_cloud": bool(os.getenv("GDELT_CLOUD_API_KEY") or os.getenv("GDELT_API_KEY")),
    }
    return {
        "schema": "glaciernet-kz.osint-source-catalog.v1",
        "sources": [
            {**source, "configured": configured.get(source["id"], source["mode"] == "live_api")}
            for source in SOURCE_CATALOG
        ],
        "content_policy": "Retain normalized metadata, source coordinates, short source descriptions, digests, and canonical links; do not mirror article bodies.",
    }


def osint_readiness() -> dict[str, Any]:
    project_root = Path(os.getenv("CORE_DIR", str(Path(__file__).resolve().parents[3])))
    benchmark = build_osint_prediction_readiness(project_root)
    return {
        "schema": "glaciernet-kz.osint-readiness.v1",
        "status": (
            "event_radar_and_retrospective_evaluation_ready"
            if benchmark["status"] == "evaluation_ready"
            else "event_radar_ready_hazard_calibration_blocked"
        ),
        "available": [
            "live USGS regional earthquake catalog",
            "live GDACS connector with empty-result handling",
            "optional official RSS/Atom connectors",
            "deterministic RGI spatial linking",
            "provenance digests, source health, cache and stale fallback",
            "observation-priority ranking and source-specific next action",
        ],
        "blocked": [
            "calibrated event-to-GLOF probability",
            "validated causal attribution",
            "automatic official warning dissemination",
            "news-based forecasting without a retrospective event/control cohort",
            *benchmark["blockers"],
        ],
        "unlock_requires": [
            "timestamped authoritative event and non-event control cohort",
            "source-by-source recall and false-alarm evaluation",
            "spatial/temporal leakage audit",
            "probability calibration and prospective shadow-mode validation",
        ],
        "benchmark": benchmark,
        "safety_statement": "OSINT is an acquisition-prioritization signal, not an official warning or a substitute for field evidence.",
    }
