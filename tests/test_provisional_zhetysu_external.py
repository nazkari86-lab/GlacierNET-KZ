from __future__ import annotations

import pandas as pd

from scripts.evaluate_provisional_zhetysu_external import ZHETYSU_CANDIDATE_BBOX, _is_candidate


def test_candidate_filter_is_explicit_and_reproducible() -> None:
    frame = pd.DataFrame({"cenlon": [78.9, 80.0, 84.2], "cenlat": [44.0, 44.0, 44.0]})
    assert len(_is_candidate(frame)) == 1
    assert ZHETYSU_CANDIDATE_BBOX == (79.0, 43.0, 84.1, 45.37)
