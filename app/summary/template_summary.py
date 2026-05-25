"""Generates a plain-text summary of a clinical trial from a TrialRecord using templates only."""

try:
    from app.models import TrialRecord
except ImportError:
    from models import TrialRecord  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _join_conditions(trial: TrialRecord) -> str:
    """Return a comma-joined string of conditions, or an empty string if none."""
    items = [c for c in trial.conditions if c and c.strip()]
    return ", ".join(items)


def _join_interventions(trial: TrialRecord) -> str:
    """Return a comma-joined string of intervention names, or an empty string if none."""
    names = [
        i["intervention_name"]
        for i in trial.interventions
        if i.get("intervention_name") and str(i["intervention_name"]).strip()
    ]
    return ", ".join(names)


def _first_sentence(text: str) -> str:
    """Return the first sentence of text, or the full text if no period is found."""
    text = text.strip()
    end = text.find(".")
    if end == -1:
        return text
    return text[: end + 1].strip()


def _truncate_eligibility(text: str, max_chars: int = 200) -> str:
    """Return up to max_chars characters of text, appending '...' if truncated."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


def generate_summary(trial: TrialRecord) -> str:
    """
    Build a plain-text summary of a clinical trial using only template strings.

    No model, API, or external service is called. Fields that are missing,
    empty, or null are silently omitted. The string 'None' never appears
    in the output.

    Args:
        trial: A TrialRecord instance populated from the database.

    Returns:
        A multi-sentence summary string.
    """
    sentences: list[str] = []

    # Title
    if trial.title and trial.title.strip():
        sentences.append(f"{trial.title.strip()} [Title]")

    # Study type and conditions
    conditions = _join_conditions(trial)
    if trial.study_type and trial.study_type.strip() and conditions:
        sentences.append(
            f"This is a {trial.study_type.strip()} study investigating "
            f"{conditions} [Conditions]."
        )
    elif trial.study_type and trial.study_type.strip():
        sentences.append(f"This is a {trial.study_type.strip()} study.")
    elif conditions:
        sentences.append(f"This study investigates {conditions} [Conditions].")

    # Interventions
    interventions = _join_interventions(trial)
    if interventions:
        sentences.append(f"Interventions include: {interventions} [Interventions].")

    # Status and phase
    if trial.overall_status and trial.overall_status.strip() and trial.phase and trial.phase.strip():
        sentences.append(
            f"The trial status is {trial.overall_status.strip()} [Status] "
            f"and the phase is {trial.phase.strip()} [Phase]."
        )
    elif trial.overall_status and trial.overall_status.strip():
        sentences.append(f"The trial status is {trial.overall_status.strip()} [Status].")
    elif trial.phase and trial.phase.strip():
        sentences.append(f"The trial phase is {trial.phase.strip()} [Phase].")

    # Brief summary (first sentence only)
    if trial.brief_summary and trial.brief_summary.strip():
        first = _first_sentence(trial.brief_summary)
        if first:
            sentences.append(f"{first} [Brief Summary]")

    # Eligibility criteria (truncated)
    if trial.eligibility_criteria and trial.eligibility_criteria.strip():
        excerpt = _truncate_eligibility(trial.eligibility_criteria)
        if excerpt:
            sentences.append(f"Eligibility criteria include: {excerpt} [Eligibility Criteria]")

    # Sponsor and start date
    if trial.sponsor_name and trial.sponsor_name.strip() and trial.start_date and trial.start_date.strip():
        sentences.append(
            f"The trial is sponsored by {trial.sponsor_name.strip()} [Sponsor] "
            f"and started on {trial.start_date.strip()} [Start Date]."
        )
    elif trial.sponsor_name and trial.sponsor_name.strip():
        sentences.append(f"The trial is sponsored by {trial.sponsor_name.strip()} [Sponsor].")
    elif trial.start_date and trial.start_date.strip():
        sentences.append(f"The trial started on {trial.start_date.strip()} [Start Date].")

    return " ".join(sentences)
