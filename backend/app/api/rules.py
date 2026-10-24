from fastapi import APIRouter

from app.rules import accessors
from app.rules.sources import SOURCES
from app.schemas.api import RulesResponse, Thresholds, UnresolvedRule

router = APIRouter(tags=["rules"])


@router.get("/rules", response_model=RulesResponse)
def get_rules() -> RulesResponse:
    return RulesResponse(
        rules_version=accessors.rules_version(),
        thresholds=Thresholds(
            hours=accessors.hours_threshold_hours(),
            income_cents=accessors.income_threshold_cents(),
            rfi_response_days=accessors.rfi_response_days(),
        ),
        rule_statuses=accessors.rule_statuses(),
        unresolved_rules=[
            UnresolvedRule(id=r.id, description=r.description or r.id) for r in accessors.unresolved_rules()
        ],
        exemption_questions=accessors.exemptions(),
        sources=dict(SOURCES),
    )
