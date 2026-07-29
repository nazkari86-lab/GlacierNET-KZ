import json
import subprocess
from pathlib import Path


def test_fixture_pipeline_emits_three_twin_engineering_passport(
    tmp_path: Path,
):
    command = [
        "/Users/dulatnurlanuly/miniforge3/envs/glaciers/bin/python",
        "scripts/build_cryogenesis_cohort.py",
        "--feature-fixture",
        "tests/fixtures/cryogenesis/physical_feature_fixture.json",
        "--output-root",
        str(tmp_path),
        "--anchor-year",
        "2020",
        "--outcome-year",
        "2024",
        "--cohort-id",
        "fixture-v1",
    ]
    subprocess.run(command, check=True)
    passport = json.loads(
        (tmp_path / "passports" / "RGI-A.json").read_text()
    )
    assert passport["match"]["status"] == "matched"
    assert len(passport["match"]["twins"]) == 3
    assert passport["claim_tier"] == "cohort_built"
    assert passport["claims_not_allowed"]
