"""Exemption questionnaire from the rules file (R8).

Proofline never says someone is exempt. A "yes" answer only produces a possible exemption
that the navigator must confirm, with its source.
"""

from app.rules import accessors
from app.schemas.api import ExemptionAnswer
from app.schemas.ledger import PossibleExemption

POSSIBLE_EXEMPTION_LABEL = {
    "en": "Possible exemption — navigator to confirm",
    "es": "Posible exención — el navegador debe confirmar",
}


def questions() -> list[PossibleExemption]:
    return accessors.exemptions()


def possible_exemptions(answers: list[ExemptionAnswer]) -> list[PossibleExemption]:
    """Exemptions answered "yes", in rules-file order. Unknown ids are ignored."""
    yes = {a.id for a in answers if a.answer}
    return [e for e in questions() if e.id in yes]
