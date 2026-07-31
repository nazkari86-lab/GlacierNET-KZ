"""Deterministic tests for the evidence-bounded OSINT Event Radar."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.routers import osint as osint_router
from app.services.osint_service import (
    enrich_and_rank,
    parse_feed,
    parse_gdacs,
    parse_gdelt,
    parse_reliefweb,
    parse_usgs,
)

client = TestClient(app)
NOW = datetime(2026, 7, 31, 8, 0, tzinfo=timezone.utc)


def _glacier(rgi_id: str = "RGI-test", lat: float = 43.05, lon: float = 77.05):
    return {
        "rgi_id": rgi_id,
        "name": "Test Glacier",
        "name_ru": "Тестовый ледник",
        "centroid": {"latitude": lat, "longitude": lon},
    }


def test_usgs_parser_preserves_source_coordinates_and_never_adds_probability():
    events = parse_usgs(
        {
            "features": [
                {
                    "id": "us-test",
                    "geometry": {"type": "Point", "coordinates": [77.1, 43.1, 10]},
                    "properties": {
                        "title": "M 4.2 - test event",
                        "place": "Test Range",
                        "mag": 4.2,
                        "time": 1785481200000,
                        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us-test",
                    },
                }
            ]
        },
        NOW,
    )
    assert len(events) == 1
    assert events[0]["latitude"] == 43.1
    assert events[0]["longitude"] == 77.1
    assert events[0]["source_tier"] == "authoritative_sensor_catalog"
    ranked = enrich_and_rank(events, [_glacier()], NOW)
    assert ranked[0]["link_scope"] == "near_glacier"
    assert ranked[0]["hazard_probability"] is None
    assert ranked[0]["claim_status"] == "reported_signal_not_validated_hazard"
    assert ranked[0]["recommended_action"].startswith("Inspect")


def test_event_ranking_is_nearest_glacier_specific_and_deterministic():
    events = parse_usgs(
        {
            "features": [
                {
                    "id": "near-second",
                    "geometry": {"type": "Point", "coordinates": [79.02, 45.01, 8]},
                    "properties": {
                        "title": "M 3.8 - regional event",
                        "place": "Second Range",
                        "mag": 3.8,
                        "time": 1785481200000,
                        "url": "https://example.test/near-second",
                    },
                }
            ]
        },
        NOW,
    )
    ranked = enrich_and_rank(events, [_glacier(), _glacier("RGI-second", 45.0, 79.0)], NOW)
    assert ranked[0]["linked_glacier"]["rgi_id"] == "RGI-second"
    assert ranked[0]["distance_to_glacier_km"] < 3
    assert 0 <= ranked[0]["observation_priority_0_100"] <= 100
    assert len(ranked[0]["content_sha256"]) == 64


def test_events_beyond_the_explicit_spatial_scope_are_removed():
    events = parse_usgs(
        {
            "features": [
                {
                    "id": "far",
                    "geometry": {"type": "Point", "coordinates": [10, 10]},
                    "properties": {"title": "M 5 - far", "mag": 5, "time": 1785481200000},
                }
            ]
        },
        NOW,
    )
    assert enrich_and_rank(events, [_glacier()], NOW) == []


def test_gdacs_parser_handles_documented_geojson_shape():
    events = parse_gdacs(
        {
            "features": [
                {
                    "geometry": {"type": "Point", "coordinates": [76.9, 43.2]},
                    "properties": {
                        "eventid": "123",
                        "eventtype": "FL",
                        "name": "Flood event",
                        "fromdate": "2026-07-30T00:00:00Z",
                        "alertlevel": "Orange",
                        "url": "https://www.gdacs.org/report.aspx?eventid=123",
                    },
                }
            ]
        },
        NOW,
    )
    assert events[0]["event_type"] == "flood"
    assert events[0]["severity_label"] == "Orange"


def test_feed_parser_discards_article_body_and_keeps_relevant_metadata():
    source = {"id": "official", "name": "Official Feed", "tier": "official_national"}
    events = parse_feed(
        """<rss><channel><item>
        <title>Mudflow warning near Almaty</title>
        <description>Short bulletin summary.</description>
        <link>https://example.test/bulletin/1</link>
        <pubDate>Thu, 30 Jul 2026 10:00:00 GMT</pubDate>
        </item></channel></rss>""",
        source,
        NOW,
    )
    assert len(events) == 1
    assert events[0]["event_type"] == "mudflow"
    assert events[0]["geolocation_method"] == "unresolved"
    assert len(events[0]["summary"]) <= 240


def test_gdelt_parser_keeps_only_relevant_geolocated_event_cards():
    events = parse_gdelt(
        {
            "data": [
                {
                    "id": "event-1",
                    "title": "Glacial lake flood review",
                    "summary": "A regional glacial lake report.",
                    "event_date": "2026-07-30",
                    "primary_story_url": "https://example.test/story",
                    "geo": {"latitude": 43.1, "longitude": 77.1, "location": "Almaty"},
                    "metrics": {"confidence": 0.75, "article_count": 3},
                },
                {"id": "event-2", "title": "Unrelated political meeting", "geo": {}},
            ]
        },
        NOW,
    )
    assert len(events) == 1
    assert events[0]["event_type"] == "glacier_lake"
    assert events[0]["provider_model_confidence"] == 0.75
    assert events[0]["source_tier"] == "open_news_intelligence"


def test_reliefweb_parser_retains_metadata_only_and_stays_unresolved():
    events = parse_reliefweb(
        {
            "data": [
                {
                    "id": 10,
                    "fields": {
                        "title": "Kazakhstan: mudflow situation report",
                        "url": "https://reliefweb.int/report/10",
                        "date": {"original": "2026-07-30T00:00:00Z"},
                        "country": [{"name": "Kazakhstan"}],
                    },
                }
            ]
        },
        NOW,
    )
    assert events[0]["event_type"] == "mudflow"
    assert events[0]["latitude"] is None
    assert events[0]["geolocation_method"] == "unresolved"
    assert "report metadata" in events[0]["summary"]


def test_osint_api_filters_a_cached_snapshot(monkeypatch):
    snapshot = {
        "schema": "glaciernet-kz.osint-radar.v1",
        "generated_at": "2026-07-31T08:00:00Z",
        "events": [
            {
                "id": "one",
                "event_type": "earthquake",
                "source_tier": "authoritative_sensor_catalog",
                "link_scope": "near_glacier",
                "linked_glacier": {"rgi_id": "RGI-one"},
            },
            {
                "id": "two",
                "event_type": "flood",
                "source_tier": "official_multilateral",
                "link_scope": "broad_context",
                "linked_glacier": {"rgi_id": "RGI-two"},
            },
        ],
        "source_health": [],
        "summary": {},
        "method": {},
        "claims_allowed": [],
        "claims_not_allowed": [],
        "warnings": [],
        "cache": {"status": "memory_hit", "ttl_seconds": 900},
    }
    monkeypatch.setattr(osint_router, "build_event_radar", lambda force_refresh=False: snapshot)
    monkeypatch.setattr(osint_router, "get_glacier", lambda rgi_id, include_geometry=False: _glacier(rgi_id))
    monkeypatch.setattr(
        osint_router,
        "enrich_and_rank",
        lambda events, glaciers: [{**events[0], "linked_glacier": {"rgi_id": glaciers[0]["rgi_id"]}}],
    )
    response = client.get("/api/osint/events?rgi_id=RGI-one&scope=near_glacier")
    assert response.status_code == 200
    body = response.json()
    assert body["returned"] == 1
    assert body["events"][0]["id"] == "one"


def test_osint_readiness_blocks_news_based_hazard_prediction():
    response = client.get("/api/osint/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "event_radar_ready_hazard_calibration_blocked"
    assert "calibrated event-to-GLOF probability" in body["blocked"]
    assert "not an official warning" in body["safety_statement"]


def test_source_catalog_exposes_credential_boundaries():
    response = client.get("/api/osint/sources")
    assert response.status_code == 200
    modes = {source["id"]: source["mode"] for source in response.json()["sources"]}
    assert modes["usgs_earthquakes"] == "live_api"
    assert modes["reliefweb"] == "requires_appname"
    assert modes["gdelt_cloud"] == "requires_api_key"
