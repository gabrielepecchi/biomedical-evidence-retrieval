"""
Parse downloaded ClinicalTrials.gov JSON pages and load them into SQLite.

Reads all files matching data/raw/page_*.json, extracts V1 trial fields,
and inserts them into the trials, conditions, and interventions tables.
Re-running this script is safe — duplicates are silently ignored.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from tqdm import tqdm

try:
    from app.db import create_schema, get_connection
except ImportError:
    from db import create_schema, get_connection  # type: ignore[no-redef]

RAW_DATA_DIR: Path = Path("data") / "raw"


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------


def list_raw_files() -> list[Path]:
    """Return all page_*.json files in data/raw/, sorted by filename."""
    return sorted(RAW_DATA_DIR.glob("page_*.json"))


def extract_studies(page_data: dict) -> list[dict]:
    """Return the list of study objects from one page response dict."""
    return page_data.get("studies", [])


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_study(study: dict) -> dict:
    """
    Extract V1 fields from one raw study object.

    Returns a dict with three keys:
      trial         — flat dict matching the trials table columns
      conditions    — list of condition name strings
      interventions — list of dicts with intervention_type and intervention_name

    Uses .get() at every nesting level so missing fields never raise KeyError.
    """
    protocol = study.get("protocolSection", {})

    id_module          = protocol.get("identificationModule", {})
    desc_module        = protocol.get("descriptionModule", {})
    status_module      = protocol.get("statusModule", {})
    design_module      = protocol.get("designModule", {})
    sponsor_module     = protocol.get("sponsorCollaboratorsModule", {})
    eligibility_module = protocol.get("eligibilityModule", {})
    conditions_module  = protocol.get("conditionsModule", {})
    arms_module        = protocol.get("armsInterventionsModule", {})

    nct_id         = id_module.get("nctId") or ""
    title          = id_module.get("briefTitle") or ""
    brief_summary  = desc_module.get("briefSummary")
    overall_status = status_module.get("overallStatus")
    study_type     = design_module.get("studyType")
    start_date     = status_module.get("startDateStruct", {}).get("date")

    phases_raw = design_module.get("phases", [])
    phase = ", ".join(phases_raw) if phases_raw else None

    sponsor_name = sponsor_module.get("leadSponsor", {}).get("name")

    eligibility_criteria = eligibility_module.get("eligibilityCriteria")
    minimum_age          = eligibility_module.get("minimumAge")
    maximum_age          = eligibility_module.get("maximumAge")
    sex                  = eligibility_module.get("sex")

    condition_list: list[str] = conditions_module.get("conditions", [])

    intervention_list: list[dict[str, str | None]] = []
    for item in arms_module.get("interventions", []):
        intervention_list.append(
            {
                "intervention_type": item.get("type"),
                "intervention_name": item.get("name"),
            }
        )

    intervention_names = [
        i["intervention_name"]
        for i in intervention_list
        if i["intervention_name"]
    ]
    search_parts = [
        title,
        brief_summary or "",
        " ".join(condition_list),
        " ".join(intervention_names),
    ]
    search_text = " ".join(part for part in search_parts if part).strip()

    url         = f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else ""
    ingested_at = datetime.now(timezone.utc).isoformat()

    trial = {
        "nct_id":               nct_id,
        "title":                title,
        "brief_summary":        brief_summary,
        "overall_status":       overall_status,
        "phase":                phase,
        "study_type":           study_type,
        "sponsor_name":         sponsor_name,
        "start_date":           start_date,
        "eligibility_criteria": eligibility_criteria,
        "minimum_age":          minimum_age,
        "maximum_age":          maximum_age,
        "sex":                  sex,
        "url":                  url,
        "search_text":          search_text,
        "ingested_at":          ingested_at,
    }

    return {
        "trial":         trial,
        "conditions":    condition_list,
        "interventions": intervention_list,
    }


# ---------------------------------------------------------------------------
# Insertion
# ---------------------------------------------------------------------------


def insert_study(conn, parsed: dict) -> None:
    """
    Insert one parsed study into trials, conditions, and interventions.

    INSERT OR IGNORE on trials prevents duplicates on re-run.
    A WHERE NOT EXISTS guard does the same for conditions and interventions,
    which use AUTOINCREMENT primary keys and cannot rely on INSERT OR IGNORE
    alone to detect duplicates on non-primary columns.
    """
    trial  = parsed["trial"]
    nct_id = trial["nct_id"]

    conn.execute(
        """
        INSERT OR IGNORE INTO trials (
            nct_id, title, brief_summary, overall_status, phase,
            study_type, sponsor_name, start_date, eligibility_criteria,
            minimum_age, maximum_age, sex, url, search_text, ingested_at
        ) VALUES (
            :nct_id, :title, :brief_summary, :overall_status, :phase,
            :study_type, :sponsor_name, :start_date, :eligibility_criteria,
            :minimum_age, :maximum_age, :sex, :url, :search_text, :ingested_at
        )
        """,
        trial,
    )

    for condition in parsed["conditions"]:
        conn.execute(
            """
            INSERT INTO conditions (nct_id, condition)
            SELECT :nct_id, :condition
            WHERE NOT EXISTS (
                SELECT 1 FROM conditions
                WHERE nct_id = :nct_id AND condition = :condition
            )
            """,
            {"nct_id": nct_id, "condition": condition},
        )

    for item in parsed["interventions"]:
        conn.execute(
            """
            INSERT INTO interventions (nct_id, intervention_type, intervention_name)
            SELECT :nct_id, :intervention_type, :intervention_name
            WHERE NOT EXISTS (
                SELECT 1 FROM interventions
                WHERE nct_id            = :nct_id
                  AND intervention_type = :intervention_type
                  AND intervention_name = :intervention_name
            )
            """,
            {
                "nct_id":            nct_id,
                "intervention_type": item["intervention_type"],
                "intervention_name": item["intervention_name"],
            },
        )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def ingest_all() -> None:
    """Read all raw JSON pages and load their records into the database."""
    raw_files = list_raw_files()

    if not raw_files:
        print(f"No files found in {RAW_DATA_DIR}. Run download.py first.")
        return

    print(f"Found {len(raw_files)} page file(s). Connecting to database ...")

    conn = get_connection()
    create_schema(conn)

    processed = 0

    for file_path in tqdm(raw_files, desc="Ingesting pages", unit="page"):
        page_data = json.loads(file_path.read_text(encoding="utf-8"))
        studies   = extract_studies(page_data)

        for study in studies:
            parsed = parse_study(study)
            if not parsed["trial"]["nct_id"]:
                continue
            insert_study(conn, parsed)
            processed += 1

    conn.commit()
    conn.close()

    print(f"\nIngestion complete. Processed {processed} study record(s).")

    verify_conn = get_connection()
    count = verify_conn.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
    verify_conn.close()
    print(f"Rows now in trials table: {count}")


def main() -> None:
    ingest_all()


if __name__ == "__main__":
    main()
