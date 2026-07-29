from scripts.train_enhanced_spatial_holdout import validate_glacier_disjoint


def test_validate_glacier_disjoint_accepts_grouped_years():
    rows = {
        "train": [
            {"glacier_id": "G1", "year": "2022"},
            {"glacier_id": "G1", "year": "2023"},
        ],
        "val": [{"glacier_id": "G2", "year": "2022"}],
        "test": [{"glacier_id": "G3", "year": "2024"}],
    }
    assert validate_glacier_disjoint(rows) == {
        "train": ["G1"],
        "val": ["G2"],
        "test": ["G3"],
    }


def test_validate_glacier_disjoint_rejects_leakage():
    rows = {
        "train": [{"glacier_id": "G1"}],
        "val": [{"glacier_id": "G1"}],
        "test": [{"glacier_id": "G3"}],
    }
    try:
        validate_glacier_disjoint(rows)
    except ValueError as error:
        assert "glacier leakage" in str(error)
    else:
        raise AssertionError("expected split leakage to fail closed")
