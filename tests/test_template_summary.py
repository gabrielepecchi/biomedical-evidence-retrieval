"""Tests for template_summary.generate_summary."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

try:
    from app.models import TrialRecord
    from app.summary.template_summary import generate_summary
except ImportError:
    from models import TrialRecord  # type: ignore[no-redef]
    from template_summary import generate_summary  # type: ignore[no-redef]


def make_full_trial() -> TrialRecord:
    """Return a fully populated TrialRecord for testing."""
    return TrialRecord(
        nct_id="NCT00000001",
        title="A Study of Levodopa in Parkinson Disease",
        url="https://clinicaltrials.gov/study/NCT00000001",
        search_text="levodopa parkinson disease",
        brief_summary="This study evaluates the efficacy of levodopa. It is a randomised controlled trial.",
        overall_status="Recruiting",
        phase="Phase 3",
        study_type="Interventional",
        sponsor_name="National Institute of Neurology",
        start_date="2020-01-15",
        eligibility_criteria="Inclusion: adults aged 40–80 with confirmed Parkinson disease. Exclusion: prior deep brain stimulation.",
        minimum_age="40 Years",
        maximum_age="80 Years",
        sex="All",
        conditions=["Parkinson Disease"],
        interventions=[
            {"intervention_type": "Drug", "intervention_name": "Levodopa"},
        ],
    )


def test_full_trial_summary_contains_key_labels() -> None:
    """A fully populated TrialRecord should produce a summary with key field labels."""
    trial = make_full_trial()
    summary = generate_summary(trial)

    assert summary, "Summary should not be empty"
    assert "[Title]" in summary
    assert "[Brief Summary]" in summary
    assert "[Conditions]" in summary


def test_missing_fields_are_omitted() -> None:
    """Optional fields set to None or empty should not appear in the summary."""
    trial = TrialRecord(
        nct_id="NCT00000002",
        title="Minimal Trial",
        url="https://clinicaltrials.gov/study/NCT00000002",
        search_text="minimal trial",
        brief_summary=None,
        overall_status=None,
        phase=None,
        study_type=None,
        sponsor_name=None,
        start_date=None,
        eligibility_criteria=None,
        conditions=[],
        interventions=[],
    )
    summary = generate_summary(trial)

    assert "None" not in summary
    assert "[Brief Summary]" not in summary
    assert "[Phase]" not in summary
    assert "[Status]" not in summary
    assert "[Sponsor]" not in summary
    assert "[Eligibility Criteria]" not in summary


def test_eligibility_text_is_truncated() -> None:
    """A long eligibility_criteria value should be truncated in the summary."""
    long_eligibility = "Inclusion criteria: " + ("patients with confirmed diagnosis. " * 20)
    trial = TrialRecord(
        nct_id="NCT00000003",
        title="Truncation Test Trial",
        url="https://clinicaltrials.gov/study/NCT00000003",
        search_text="truncation test",
        eligibility_criteria=long_eligibility,
        conditions=[],
        interventions=[],
    )
    summary = generate_summary(trial)

    assert "[Eligibility Criteria]" in summary

    start = summary.find("Eligibility criteria include:")
    end = summary.find("[Eligibility Criteria]")
    excerpt = summary[start:end].strip()
    assert len(excerpt) < len(long_eligibility)
