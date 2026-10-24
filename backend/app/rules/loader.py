"""Load rules/masshealth.yaml into a validated model. Invalid files raise RulesError naming the rule id."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from app.rules.sources import SOURCES
from app.schemas.common import RuleStatus
from app.settings import get_settings


class RulesError(ValueError):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleEntry(_Strict):
    id: str
    description: str | None = None
    label: str | None = None
    value: bool | float | None = None
    options: list[str] | None = None
    default_for_display: str | None = None
    allowed_org_types: list[str] | None = None
    requires_non_partisan: bool | None = None
    source: str | None
    status: RuleStatus

    @model_validator(mode="after")
    def _check_source(self) -> "RuleEntry":
        if self.source is None and self.status != "unresolved":
            raise ValueError(
                f"rule '{self.id}': source may be null only when status is 'unresolved'"
            )
        if self.source is not None and self.source not in SOURCES:
            raise ValueError(f"rule '{self.id}': unknown source '{self.source}'")
        return self


class RulesMeta(_Strict):
    program: str
    effective_date: str
    last_reviewed: str
    disclaimer: str


class RulesFile(_Strict):
    meta: RulesMeta
    compliance_window: list[RuleEntry]
    paths: list[RuleEntry]
    documents: list[RuleEntry]
    exemptions: list[RuleEntry]

    def all_rules(self) -> list[RuleEntry]:
        return [*self.compliance_window, *self.paths, *self.documents, *self.exemptions]

    @model_validator(mode="after")
    def _check_unique_ids(self) -> "RulesFile":
        seen: set[str] = set()
        for rule in self.all_rules():
            if rule.id in seen:
                raise ValueError(f"rule '{rule.id}': duplicate id")
            seen.add(rule.id)
        return self


def _rule_id_at(data: object, loc: tuple) -> str | None:
    """Best-effort rule id for a validation error location like ('paths', 3, 'status')."""
    if len(loc) >= 2 and isinstance(data, dict) and isinstance(loc[1], int):
        section = data.get(loc[0])
        if isinstance(section, list) and loc[1] < len(section):
            entry = section[loc[1]]
            if isinstance(entry, dict) and entry.get("id"):
                return str(entry["id"])
    return None


def load_rules(path: Path) -> RulesFile:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise RulesError(f"cannot read rules file {path}: {exc}") from exc
    try:
        return RulesFile.model_validate(data)
    except ValidationError as exc:
        parts = []
        for err in exc.errors():
            rule_id = _rule_id_at(data, tuple(err["loc"]))
            prefix = f"rule '{rule_id}' " if rule_id and rule_id not in err["msg"] else ""
            loc = ".".join(str(p) for p in err["loc"])
            parts.append(f"{prefix}{loc}: {err['msg']}")
        raise RulesError(f"invalid rules file {path}: " + "; ".join(parts)) from exc


@lru_cache
def get_rules() -> RulesFile:
    return load_rules(get_settings().rules_path)
