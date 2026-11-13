"""Streamlit prototype for phenotype-based rare disease prioritization."""
import json
from pathlib import Path
import streamlit as st
from src.data import load_ontology
from src.ranking import ontology_parents, information_content, rank

st.set_page_config(page_title="RareGen XAI", page_icon="🧬", layout="wide")
st.title("🧬 RareGen XAI")
st.caption("Research demonstration only. Not a diagnostic device; scores are NOT disease probabilities.")
path = Path("data/processed/profiles.json")
if not path.exists():
    st.error("Dataset not prepared. Run: python -m src.data")
    st.stop()

@st.cache_resource
def resources():
    data = json.loads(path.read_text())
    ontology = load_ontology()
    parents = ontology_parents(ontology)
    profiles = {k: set(v) for k, v in data["profiles"].items()}
    ic = information_content(profiles, parents)
    term_names = {t.id: t.name or t.id for t in ontology.terms()}
    return data, parents, profiles, ic, term_names

data, parents, profiles, ic, names = resources()
st.subheader("Patient observations")
st.write("Select a phenotype, then record whether it is present, suspected, absent, or unknown.")
if "observations" not in st.session_state:
    st.session_state.observations = []
search = st.text_input("Search HPO phenotype (name or HP ID)", "seizure")
matches = [(k, v) for k, v in names.items() if search.lower() in v.lower() or search.lower() in k.lower()][:60] if len(search) >= 2 else []
if matches:
    selected = st.selectbox("Phenotype", [x[0] for x in matches], format_func=lambda k: f"{names[k]} ({k})")
    status = st.selectbox("Observation", ["confirmed_present", "suspected_present", "confirmed_absent", "unknown"],
                          format_func=lambda x: x.replace("_", " ").title())
    if st.button("Add observation"):
        st.session_state.observations = [x for x in st.session_state.observations if x[0] != selected] + [(selected, status)]
else:
    st.info("Type at least two characters to search for an HPO term.")
for i, (hp, status) in enumerate(st.session_state.observations):
    col1, col2 = st.columns([5, 1])
    col1.write(f"{names.get(hp, hp)} ({hp}) — {status.replace('_', ' ')}")
    if col2.button("Remove", key=f"remove_{hp}"):
        st.session_state.observations.pop(i)
        st.rerun()
method = st.radio("Ranking method", ["semantic", "overlap"], horizontal=True)
quality = st.checkbox("Use proposed evidence-quality weights", value=True)
if st.button("Rank candidate disorders", type="primary"):
    observations = st.session_state.observations
    if not any(s in ("confirmed_present", "suspected_present") for _, s in observations):
        st.warning("Add at least one present or suspected finding. Negative-only rankings are not supported in this prototype.")
    else:
        results = rank(observations, profiles, parents, ic, data["labels"], method, quality, top_k=5)
        st.subheader("Top 5 candidates")
        for i, result in enumerate(results, 1):
            with st.expander(f"{i}. {result['disease_name']} ({result['disease_id']}) — score {result['score']:.3f}", expanded=i==1):
                st.write("Score contributions (positive supports; negative contradicts):")
                st.dataframe([{**e, "phenotype": names.get(e["hpo_id"], e["hpo_id"])} for e in result["evidence"]],
                             hide_index=True, use_container_width=True)
        st.warning("Do not use these results to diagnose, exclude, or treat a patient.")
