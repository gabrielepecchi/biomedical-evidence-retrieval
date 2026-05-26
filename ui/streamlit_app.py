"""Streamlit front end for the Biomedical Evidence Retrieval and Trial Matching Platform."""

import requests
import streamlit as st

BASE_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def call_search(
    query: str,
    top_n: int,
    alpha: float,
    overall_status: str,
    phase: str,
    study_type: str,
) -> dict | None:
    """Call the /search endpoint and return the parsed JSON, or None on error."""
    params: dict = {"q": query, "top_n": top_n, "alpha": alpha}
    if overall_status:
        params["overall_status"] = overall_status
    if phase:
        params["phase"] = phase
    if study_type:
        params["study_type"] = study_type

    try:
        response = requests.get(f"{BASE_URL}/search", params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API. Make sure the FastAPI backend is running at http://localhost:8000.")
        return None
    except requests.exceptions.HTTPError as exc:
        st.error(f"API error: {exc.response.status_code} — {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None


def call_summary(nct_id: str) -> dict | None:
    """Call the /summary/{nct_id} endpoint and return the parsed JSON, or None on error."""
    try:
        response = requests.get(f"{BASE_URL}/summary/{nct_id}", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API.")
        return None
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 404:
            st.warning(f"No summary found for {nct_id}.")
        else:
            st.error(f"API error: {exc.response.status_code} — {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def render_intervention(item: dict) -> str:
    """Format a single intervention dict as a readable string."""
    itype = item.get("intervention_type") or ""
    iname = item.get("intervention_name") or ""
    if itype and iname:
        return f"{itype}: {iname}"
    return iname or itype or "—"


def render_result(result: dict) -> None:
    """Render a single search result inside a Streamlit expander."""
    rank = result.get("rank", "?")
    title = result.get("title") or "Untitled"
    nct_id = result.get("nct_id", "")
    label = f"#{rank} — {title}"

    with st.expander(label):
        st.markdown(f"**NCT ID:** {nct_id}")
        st.markdown(f"**Title:** {title}")
        st.markdown(f"**Overall Status:** {result.get('overall_status') or '—'}")
        st.markdown(f"**Phase:** {result.get('phase') or '—'}")
        st.markdown(f"**Study Type:** {result.get('study_type') or '—'}")

        conditions = result.get("conditions") or []
        st.markdown(f"**Conditions:** {', '.join(conditions) if conditions else '—'}")

        interventions = result.get("interventions") or []
        intervention_strs = [render_intervention(i) for i in interventions]
        st.markdown(f"**Interventions:** {', '.join(intervention_strs) if intervention_strs else '—'}")

        st.markdown(f"**Brief Summary:** {result.get('brief_summary') or '—'}")

        st.markdown(
            f"**Scores:** BM25 `{result.get('bm25_score', 0.0):.4f}` · "
            f"Semantic `{result.get('semantic_score', 0.0):.4f}` · "
            f"Hybrid `{result.get('hybrid_score', 0.0):.4f}`"
        )

        url = result.get("url") or ""
        if url:
            st.markdown(f"**URL:** [{url}]({url})")

        summary_key = f"summary_{nct_id}"

        if st.button("Get Grounded Summary", key=f"btn_{nct_id}"):
            data = call_summary(nct_id)
            if data:
                st.session_state[summary_key] = data

        if summary_key in st.session_state:
            summary_data = st.session_state[summary_key]
            st.markdown("---")
            st.markdown("**Grounded Summary:**")
            st.write(summary_data.get("summary", ""))
            fields_used = summary_data.get("fields_used") or []
            if fields_used:
                st.markdown(f"*Fields used: {', '.join(fields_used)}*")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


def main() -> None:
    """Render the single-page Streamlit UI."""
    st.set_page_config(
        page_title="Biomedical Trial Search",
        page_icon="🔬",
        layout="centered",
    )

    st.title("🔬 Biomedical Evidence Retrieval")
    st.caption("Search clinical trials using hybrid BM25 and semantic retrieval.")

    st.divider()

    query = st.text_input("Search query", placeholder="e.g. dopamine agonist Parkinson's disease")

    col1, col2 = st.columns(2)
    with col1:
        alpha = st.slider(
            "Alpha (BM25 weight)",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.05,
            help="1.0 = BM25 only · 0.0 = semantic only · 0.5 = balanced",
        )
    with col2:
        top_n = st.selectbox("Number of results", options=[5, 10, 20], index=1)

    with st.expander("Filters (optional)"):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        with filter_col1:
            overall_status = st.text_input(
                "Overall Status",
                placeholder="e.g. Recruiting",
                help="Case-insensitive exact match",
            )
        with filter_col2:
            phase = st.text_input(
                "Phase",
                placeholder="e.g. Phase 2",
                help="Case-insensitive exact match",
            )
        with filter_col3:
            study_type = st.text_input(
                "Study Type",
                placeholder="e.g. Interventional",
                help="Case-insensitive exact match",
            )

    if st.button("Search", type="primary"):
        if not query or not query.strip():
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Searching..."):
                data = call_search(
                    query,
                    top_n=top_n,
                    alpha=alpha,
                    overall_status=overall_status.strip(),
                    phase=phase.strip(),
                    study_type=study_type.strip(),
                )
            if data is not None:
                st.session_state["search_results"] = data.get("results") or []
                st.session_state["search_query"] = query

    if "search_results" in st.session_state:
        results = st.session_state["search_results"]
        if not results:
            st.info("No results found. Try a different query.")
        else:
            stored_query = st.session_state.get("search_query", "")
            st.success(f"{len(results)} result(s) for **{stored_query}**")
            for result in results:
                render_result(result)


if __name__ == "__main__":
    main()
