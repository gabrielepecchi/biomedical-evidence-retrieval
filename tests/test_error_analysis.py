"""Tests for eval/error_analysis.json structure and content."""

import json
from pathlib import Path

import pytest

PATH = Path("eval/error_analysis.json")

REQUIRED_FIELDS = {"query_id", "category", "failure_mode", "method", "description", "possible_fix"}

VALID_METHODS = {"bm25_only", "semantic_only"}

VALID_FAILURE_MODES = {
    "lexical_overmatch",
    "semantic_drift",
    "synonym_mismatch",
    "intervention_mismatch",
    "biomarker_vs_treatment_confusion",
    "nonmotor_symptom_ambiguity",
    "field_specificity_gap",
    "candidate_pool_bias",
}


@pytest.fixture(scope="module")
def entries():
    assert PATH.exists(), f"File not found: {PATH}"
    with PATH.open() as f:
        return json.load(f)


def test_is_non_empty_list(entries):
    assert isinstance(entries, list)
    assert len(entries) > 0


@pytest.mark.parametrize("field", sorted(REQUIRED_FIELDS))
def test_all_entries_have_field(entries, field):
    for i, entry in enumerate(entries):
        assert field in entry, f"Entry {i} missing field '{field}'"


def test_query_id_starts_with_q(entries):
    for i, entry in enumerate(entries):
        assert entry["query_id"].startswith("Q"), (
            f"Entry {i}: query_id '{entry['query_id']}' does not start with 'Q'"
        )


def test_method_is_valid(entries):
    for i, entry in enumerate(entries):
        assert entry["method"] in VALID_METHODS, (
            f"Entry {i}: invalid method '{entry['method']}'"
        )


def test_failure_mode_is_valid(entries):
    for i, entry in enumerate(entries):
        assert entry["failure_mode"] in VALID_FAILURE_MODES, (
            f"Entry {i}: invalid failure_mode '{entry['failure_mode']}'"
        )


def test_description_is_non_empty_string(entries):
    for i, entry in enumerate(entries):
        assert isinstance(entry["description"], str) and entry["description"].strip(), (
            f"Entry {i}: description is empty or not a string"
        )


def test_possible_fix_is_non_empty_string(entries):
    for i, entry in enumerate(entries):
        assert isinstance(entry["possible_fix"], str) and entry["possible_fix"].strip(), (
            f"Entry {i}: possible_fix is empty or not a string"
        )
