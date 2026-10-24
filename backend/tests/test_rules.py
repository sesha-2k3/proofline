from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from app.rules import accessors
from app.rules.loader import RulesError, load_rules
from app.rules.sources import SOURCES
from app.settings import get_settings

RULES_PATH = get_settings().rules_path


def _raw() -> dict:
    return yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _find(data: dict, rule_id: str) -> dict:
    for section in ("compliance_window", "paths", "documents", "exemptions"):
        for entry in data[section]:
            if entry["id"] == rule_id:
                return entry
    raise KeyError(rule_id)


def test_valid_file_loads():
    rules = load_rules(RULES_PATH)
    assert rules.meta.effective_date == "2027-01-01"
    assert len(rules.exemptions) == 10


def test_missing_source_on_confirmed_rule_fails_with_id(tmp_path):
    data = _raw()
    _find(data, "hours_threshold")["source"] = None
    with pytest.raises(RulesError, match="hours_threshold"):
        load_rules(_write(tmp_path, data))


def test_invalid_status_fails_with_id(tmp_path):
    data = _raw()
    _find(data, "income_threshold_cents")["status"] = "maybe"
    with pytest.raises(RulesError, match="income_threshold_cents"):
        load_rules(_write(tmp_path, data))


def test_unknown_source_fails_with_id(tmp_path):
    data = _raw()
    _find(data, "paystub_recency_days")["source"] = "S9"
    with pytest.raises(RulesError, match="paystub_recency_days"):
        load_rules(_write(tmp_path, data))


def test_duplicate_id_fails(tmp_path):
    data = _raw()
    data["paths"].append(dict(_find(data, "hours_threshold")))
    with pytest.raises(RulesError, match="hours_threshold"):
        load_rules(_write(tmp_path, data))


def test_extra_key_forbidden(tmp_path):
    data = _raw()
    _find(data, "medicare")["surprise"] = 1
    with pytest.raises(RulesError, match="medicare"):
        load_rules(_write(tmp_path, data))


@settings(max_examples=200, deadline=None)
@given(
    section=st.sampled_from(["compliance_window", "paths", "documents", "exemptions"]),
    index=st.integers(min_value=0, max_value=50),
    status=st.sampled_from(["confirmed", "provisional"]),
)
def test_property_null_source_requires_unresolved(tmp_path_factory, section, index, status):
    """**Validates: Requirements 1** — any rule with null source and a non-unresolved status
    makes the file invalid, and the error names that rule id."""
    data = _raw()
    entry = data[section][index % len(data[section])]
    entry["source"] = None
    entry["status"] = status
    with pytest.raises(RulesError, match=entry["id"]):
        load_rules(_write(tmp_path_factory.mktemp("r"), data))


def test_accessors_return_yaml_values():
    data = _raw()
    assert accessors.hours_threshold() == round(_find(data, "hours_threshold")["value"] * 100)
    assert accessors.hours_threshold_hours() == _find(data, "hours_threshold")["value"]
    assert accessors.income_threshold_cents() == _find(data, "income_threshold_cents")["value"]
    assert accessors.rfi_response_days() == _find(data, "rfi_response_days")["value"]
    assert accessors.paystub_recency_days() == _find(data, "paystub_recency_days")["value"]
    assert accessors.allowed_volunteer_org_types() == _find(
        data, "volunteer_org_requirement"
    )["allowed_org_types"]
    assert accessors.rules_version() == data["meta"]["last_reviewed"]
    assert isinstance(accessors.hours_threshold(), int)


def test_statuses_and_unresolved():
    assert accessors.rule_status("rfi_response_days") == "provisional"
    assert accessors.is_unresolved("self_employment_income_basis")
    assert not accessors.is_unresolved("hours_threshold")
    ids = {r.id for r in accessors.unresolved_rules()}
    assert ids == {
        "job_training_approved",
        "self_employment_income_basis",
        "pay_period_split_method",
        "volunteer_proof",
        "school_proof",
    }


def test_exemptions_have_source_urls():
    items = accessors.exemptions()
    assert len(items) == 10
    for item in items:
        assert item.source_url == SOURCES[item.source]


def test_app_starts_with_valid_rules():
    from app.main import app

    with TestClient(app):
        pass
