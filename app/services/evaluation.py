import re

from app.schemas.estimation import StructureCheck


def evaluate_estimation_structure(text: str, finish_reason: str) -> StructureCheck:
    issues: list[str] = []

    has_title = bool(re.search(r'^## .+', text, re.MULTILINE))
    if not has_title:
        issues.append("Missing H2 title (## ...)")

    has_breakdown_table = bool(re.search(r'Task\s*\|\s*Hours\s*\|\s*Cost', text, re.IGNORECASE))
    if not has_breakdown_table:
        issues.append("Missing breakdown table header (Task | Hours | Cost)")

    has_totals_section = (
        bool(re.search(r'total\s+hours?', text, re.IGNORECASE))
        and bool(re.search(r'total\s+cost', text, re.IGNORECASE))
    )
    if not has_totals_section:
        issues.append("Missing totals section (Total hours / Total cost)")

    has_team_section = bool(re.search(r'recommended\s+team', text, re.IGNORECASE))
    if not has_team_section:
        issues.append("Missing 'Recommended Team' section")

    has_duration_section = bool(
        re.search(r'\d+[\s–-]+\d*\s*weeks?|\d+\s*weeks?', text, re.IGNORECASE)
    )
    if not has_duration_section:
        issues.append("Missing duration section (e.g. '4–6 weeks')")

    hours_match = _check_hours(text)
    if not hours_match:
        issues.append("Task hours don't sum to declared Total hours (tolerance ±1h)")

    cost_match = _check_costs(text)
    if not cost_match:
        issues.append("Task costs don't sum to declared Total cost (tolerance ±2%)")

    finish_reason_ok = finish_reason in ("stop", "end_turn")
    if not finish_reason_ok:
        issues.append(f"Unexpected finish_reason: '{finish_reason}'")

    checks = [
        has_title, has_breakdown_table, has_totals_section, has_team_section,
        has_duration_section, hours_match, cost_match, finish_reason_ok,
    ]
    score = round(sum(checks) / len(checks), 4)

    return StructureCheck(
        score=score,
        issues=issues,
        has_title=has_title,
        has_breakdown_table=has_breakdown_table,
        has_totals_section=has_totals_section,
        has_team_section=has_team_section,
        has_duration_section=has_duration_section,
        hours_match=hours_match,
        cost_match=cost_match,
        finish_reason_ok=finish_reason_ok,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_rows(text: str) -> list[tuple[float, float]]:
    """Return (hours, cost) pairs from task table rows, skipping header/separator/total rows."""
    rows: list[tuple[float, float]] = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 3:
            continue
        name_raw, hours_cell, cost_cell = cells[0], cells[1], cells[2]
        name = re.sub(r"\*", "", name_raw).strip()
        if re.search(r"\b(Task|Hours|Cost|Total)\b", name, re.IGNORECASE):
            continue
        if re.match(r"^[-:\s]+$", name):
            continue
        h = re.search(r"(\d+(?:\.\d+)?)", re.sub(r"\*", "", hours_cell))
        if not h:
            continue
        cost = _parse_num(cost_cell)
        if cost > 0:
            rows.append((float(h.group(1)), cost))
    return rows


def _parse_num(s: str) -> float:
    """Parse a number string that may contain currency symbols, bold markers, or thousand separators."""
    s = re.sub(r"[^\d.,]", "", re.sub(r"\*", "", s).strip())
    if not s:
        return 0.0
    if "," in s and "." not in s:
        s = s.replace(",", "")          # US thousands: 1,250 → 1250
    elif "," in s and "." in s:
        if s.rindex(".") > s.rindex(","):
            s = s.replace(",", "")      # US: 1,250.00
        else:
            s = s.replace(".", "").replace(",", ".")  # EU: 1.250,00
    try:
        return float(s)
    except ValueError:
        return 0.0


def _find_declared_hours(text: str) -> float | None:
    m = re.search(r"[Tt]otal\s+hours?[^\d]*(\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else None


def _find_declared_cost(text: str) -> float | None:
    m = re.search(r"[Tt]otal\s+cost[^\d]*([\d,.]+)", text)
    return _parse_num(m.group(1)) if m else None


def _check_hours(text: str) -> bool:
    rows = _parse_rows(text)
    if not rows:
        return False
    declared = _find_declared_hours(text)
    if declared is None:
        return False
    return abs(sum(h for h, _ in rows) - declared) <= 1.0


def _check_costs(text: str) -> bool:
    rows = _parse_rows(text)
    if not rows:
        return False
    declared = _find_declared_cost(text)
    if not declared:
        return False
    return abs(sum(c for _, c in rows) - declared) / declared <= 0.02
