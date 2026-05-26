"""Tests for eval/patient_cases.json and eval/patient_case_matches_alpha_0_5.json."""

import json
from pathlib import Path

import pytest

CASES_PATH = Path("eval/patient_cases.json")
MATCHES_PATH = Path("eval/patient_case_matches_alpha_0_5.json")

CASE_FIELDS = {
    "case_id", "age", "condition", "symptoms", "prior_treatments",
    "exclusions", "mobility", "cognitive_status", "matching_query",
    "target_category", "notes",
}

MATCH_CASE_FIELDS = {"case_id", "matching_query", "target_category", "matches"}

MATCH_FIELDS = {
    "rank", "nct_id", "title", "overall_status", "phase",
    "study_type", "hybrid_score", "compatibility_label", "compatibility_reason",
}

VALID_LABELS = {"likely_relevant", "possibly_relevant", "unclear"}
ELIGIBILITY_PHRASE = "does not indicate clinical eligibility"


@pytest.fixture(scope="module")
def cases():
    assert CASES_PATH.exists(), f"File not found: {CASES_PATH}"
    return json.loads(CASES_PATH.read_text())


@pytest.fixture(scope="module")
def matches():
    assert MATCHES_PATH.exists(), f"File not found: {MATCHES_PATH}"
    return json.loads(MATCHES_PATH.read_text())


# --- patient_cases.json ---

def test_cases_is_non_empty_list(cases):
    assert isinstance(cases, list)
    assert len(cases) > 0


@pytest.mark.parametrize("field", sorted(CASE_FIELDS))
def test_case_fields_present(cases, field):
    for i, case in enumerate(cases):
        assert field in case, f"Case {i} missing field '{field}'"


# --- patient_case_matches_alpha_0_5.json ---

def test_matches_is_non_empty_list(matches):
    assert isinstance(matches, list)
    assert len(matches) > 0


@pytest.mark.parametrize("field", sorted(MATCH_CASE_FIELDS))
def test_output_case_fields_present(matches, field):
    for i, case in enumerate(matches):
        assert field in case, f"Output case {i} missing field '{field}'"


def test_each_output_case_has_ten_matches(matches):
    for case in matches:
        assert len(case["matches"]) == 10, (
            f"{case['case_id']}: expected 10 matches, got {len(case['matches'])}"
        )


@pytest.mark.parametrize("field", sorted(MATCH_FIELDS))
def test_match_fields_present(matches, field):
    for case in matches:
        for i, match in enumerate(case["matches"]):
            assert field in match, (
                f"{case['case_id']} match {i} missing field '{field}'"
            )


def test_compatibility_label_is_valid(matches):
    for case in matches:
        for match in case["matches"]:
            assert match["compatibility_label"] in VALID_LABELS, (
                f"{case['case_id']} rank {match['rank']}: "
                f"invalid label '{match['compatibility_label']}'"
            )


def test_ranks_1_to_3_are_likely_relevant(matches):
    for case in matches:
        for match in case["matches"]:
            if match["rank"] <= 3:
                assert match["compatibility_label"] == "likely_relevant", (
                    f"{case['case_id']} rank {match['rank']}: "
                    f"expected 'likely_relevant', got '{match['compatibility_label']}'"
                )


def test_ranks_4_to_10_are_possibly_relevant(matches):
    for case in matches:
        for match in case["matches"]:
            if 4 <= match["rank"] <= 10:
                assert match["compatibility_label"] == "possibly_relevant", (
                    f"{case['case_id']} rank {match['rank']}: "
                    f"expected 'possibly_relevant', got '{match['compatibility_label']}'"
                )


def test_compatibility_reason_contains_eligibility_phrase(matches):
    for case in matches:
        for match in case["matches"]:
            assert ELIGIBILITY_PHRASE in match["compatibility_reason"], (
                f"{case['case_id']} rank {match['rank']}: "
                f"compatibility_reason missing phrase '{ELIGIBILITY_PHRASE}'"
            )
