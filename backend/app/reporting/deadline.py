"""RFI response deadline: rfi_received_date + rfi_response_days, labeled with the rule's status (R2.3)."""

from datetime import date, timedelta

from app.rules import accessors
from app.schemas.common import CaseInfo
from app.schemas.ledger import Deadline

RULE_ID = "rfi_response_days"


def response_deadline(case_info: CaseInfo) -> Deadline | None:
    if case_info.rfi_received_date is None:
        return None
    received = date.fromisoformat(case_info.rfi_received_date)
    due = received + timedelta(days=accessors.rfi_response_days())
    return Deadline(date=due.isoformat(), rule_id=RULE_ID, rule_status=accessors.rule_status(RULE_ID))
