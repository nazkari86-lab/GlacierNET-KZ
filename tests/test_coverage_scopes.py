from scripts.report_coverage_scopes import calculate_scopes


def test_calculate_scopes_preserves_repository_and_research_visibility():
    coverage = {
        "files": {
            "src/core.py": {"summary": {"num_statements": 10, "covered_lines": 8}},
            "src/prototype.py": {"summary": {"num_statements": 10, "covered_lines": 2}},
        }
    }
    config = {"research_modules": ["src/prototype.py", "src/not_imported.py"]}

    result = calculate_scopes(coverage, config)

    assert result["repository"]["percent"] == 50
    assert result["production_scope"]["percent"] == 80
    assert result["research_scaffolds"]["percent"] == 20
    assert result["classification"]["research_files_declared_but_not_imported"] == ["src/not_imported.py"]


def test_empty_coverage_is_rejected():
    try:
        calculate_scopes({"files": {}}, {"research_modules": []})
    except ValueError as error:
        assert "no per-file data" in str(error)
    else:
        raise AssertionError("empty coverage must fail closed")
