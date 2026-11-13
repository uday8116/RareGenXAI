# Final submission and demonstration checklist

## Already completed and verified
- [x] HPO ontology and disease-profile preparation
- [x] Explainable phenotype-based disease ranking
- [x] TF-IDF, Logistic Regression and Random Forest baselines
- [x] Streamlit source application
- [x] Automated GitHub tests (previous successful runs)
- [x] External RareBench evaluation on all 178 eligible cases
- [x] Cohort-specific metrics and provenance
- [x] Final technical report: `docs/FINAL_PROJECT_REPORT.md`
- [x] Honest DeepRare comparison protocol and limitations

## Needs repository owner's or university's participation
- [ ] **Deploy live Streamlit demo:** log into https://share.streamlit.io, authorize access to this private GitHub repository, select branch `main`, file `app.py`, and follow `docs/WEB_DEPLOYMENT.md`. Record the real URL only after it works.
- [ ] **University dissertation formatting:** provide required template, student/supervisor details, certificates and declarations. Existing drafts should be updated to match `docs/FINAL_PROJECT_REPORT.md`.
- [ ] **Final presentation:** update existing slide draft with the full 178-case cohort results, a real app screenshot and the limitations.
- [ ] **Demonstration:** run app locally or deployed; show input HPO terms, ranked disorders, and explanations. Do not enter identifiable patient information.
- [ ] **Supervisor review:** approve research claims and required scope.

## Optional research extensions (not prerequisites unless supervisor requires them)
- [ ] Matched-case DeepRare run (requires genuine predictions on the same 178 cases).
- [ ] Statistical confidence intervals, cohort error analysis, and further validation.
- [ ] Prospective clinical validation under ethics approval.

## Final demonstration commands
```bash
python -m pip install -r requirements.txt
python -m src.data
python -m pytest -q
streamlit run app.py
```
To reproduce the external benchmark, see `docs/VERIFIED_EXTERNAL_RESULTS.md`.

## Final research statement
The 178-case retrospective RareBench evaluation succeeded. Exact overlap achieved 37.64% Top-1 and 54.49% Top-5. This research prototype is not a medical device and cannot be used as a clinical diagnosis service. Public deployment and university approval are not yet verified.
