"""The only way the rest of the app reads thresholds and rule statuses."""

from app.rules.loader import RuleEntry, RulesError, get_rules
from app.rules.sources import SOURCES
from app.schemas.common import RuleStatus
from app.schemas.ledger import PossibleExemption


def rule(rule_id: str) -> RuleEntry:
    for entry in get_rules().all_rules():
        if entry.id == rule_id:
            return entry
    raise RulesError(f"rule '{rule_id}' not found")


def _number(rule_id: str) -> float:
    value = rule(rule_id).value
    if isinstance(value, bool) or value is None:
        raise RulesError(f"rule '{rule_id}' has no numeric value")
    return float(value)


def rules_version() -> str:
    return get_rules().meta.last_reviewed


def hours_threshold() -> int:
    """Monthly hours threshold in integer hundredths of an hour."""
    return round(_number("hours_threshold") * 100)


def hours_threshold_hours() -> float:
    return hours_threshold() / 100


def income_threshold_cents() -> int:
    return round(_number("income_threshold_cents"))


def rfi_response_days() -> int:
    return round(_number("rfi_response_days"))


def paystub_recency_days() -> int:
    return round(_number("paystub_recency_days"))


def allowed_volunteer_org_types() -> list[str]:
    return list(rule("volunteer_org_requirement").allowed_org_types or [])


def rule_status(rule_id: str) -> RuleStatus:
    return rule(rule_id).status


def is_unresolved(rule_id: str) -> bool:
    return rule_status(rule_id) == "unresolved"


def rule_statuses() -> dict[str, RuleStatus]:
    return {entry.id: entry.status for entry in get_rules().all_rules()}


def unresolved_rules() -> list[RuleEntry]:
    return [entry for entry in get_rules().all_rules() if entry.status == "unresolved"]


def exemptions() -> list[PossibleExemption]:
    return [
        PossibleExemption(
            id=entry.id,
            label=entry.label or entry.description or entry.id,
            source=entry.source or "",
            source_url=SOURCES.get(entry.source or "", ""),
        )
        for entry in get_rules().exemptions
    ]
