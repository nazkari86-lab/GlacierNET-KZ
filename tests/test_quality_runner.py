from __future__ import annotations

from scripts.run_quality_gates import run


def test_quality_runner_can_execute_compile_gate():
    assert run("compile-test", ["python", "-m", "compileall", "-q", "src"])
