"""Shared temporal-consistency policy for annual glacier estimates."""

from __future__ import annotations


def classify_annual_change(relative_change: float | None) -> tuple[str, str]:
    """Classify absolute change relative to the previous comparable year."""
    if relative_change is None:
        return "baseline", "no previous comparable year"
    percent = relative_change * 100
    if relative_change <= 0.05:
        return "normal", f"annual area change {percent:.1f}% is within 5%"
    if relative_change <= 0.15:
        return "review", f"annual area change {percent:.1f}% requires review"
    if relative_change <= 0.30:
        return "suspicious", f"annual area change {percent:.1f}% exceeds 15%"
    return "reject", f"annual area change {percent:.1f}% exceeds automatic 30% rejection threshold"
