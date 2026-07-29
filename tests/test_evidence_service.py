"""Evidence packages must remain source-bound and explicit about limits."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glacierkz-api"))


def test_local_trend_evidence_is_chart_ready_and_not_overclaimed():
    from app.services.evidence_service import get_trend_evidence

    evidence = get_trend_evidence()

    assert evidence["primary_table"] == "results/tables/decision_ready_area_timeseries.csv"
    assert evidence["status"] == "exploratory_not_adjudicated"
    assert len(evidence["points"]) >= 3
    assert evidence["exploratory_linear_trend"]["n_observations"] == len(evidence["exploratory_points"])
    assert any("not measured glacier volume" in note for note in evidence["limitations"])


def test_llm_contract_forbids_unsupported_climate_claims():
    from app.services.evidence_service import get_trend_evidence, trend_evidence_prompt

    prompt = trend_evidence_prompt(get_trend_evidence())

    assert "Do not invent climate observations" in prompt
    assert "decision_ready_area_timeseries.csv" in prompt
