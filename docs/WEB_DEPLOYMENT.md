# Web app deployment guide

## Local run (recommended for a private research prototype)
```bash
git clone https://github.com/uday8116/RareGenXAI.git
cd RareGenXAI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.data
python -m src.train_ml --train-diseases 200 --test-diseases 60
python -m pytest -q
streamlit run app.py
```
The first Streamlit launch also attempts to prepare the official HPO dataset if it is missing. A working internet connection is required for that step. Trained Logistic Regression and Random Forest models require the separate training command above. TF-IDF and HPO-based models work without that step.

## Streamlit Community Cloud
Official instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

1. Open https://share.streamlit.io and connect your GitHub account.
2. Create an app using repository `uday8116/RareGenXAI`, branch `main`, and entrypoint `app.py`.
3. Select a supported Python version (prefer Python 3.11 where available).
4. Deploy, then watch the logs as the app downloads and processes official HPO files.

**Important:** This repository has been private. Streamlit requires you to explicitly grant access to private repositories. The platform's free resource limits may prevent large HPO ontology loading, and trained models stored only on your laptop are not available in a fresh cloud container. Until a persistent model artifact or a controlled training/startup step is provided, the hosted app will support the untrained TF-IDF and ontology methods but not Logistic Regression or Random Forest. Do not upload identifiable patient information to a public demo.

## Deployment verification
- Check the app loads and HPO search returns real terms.
- Add confirmed and suspected observations.
- Rank with exact overlap, HPO semantic, and TF-IDF.
- For trained rerankers, verify `models/raregen_ml.joblib` exists in the deployed environment.
- Confirm explanations are present and scores are not called probabilities.
- Verify resource usage and restart behavior.

## Status
Deployment instructions are prepared; a live public URL and its operational availability have **not** been verified. External deployment requires the repository owner's Streamlit authorization and configuration.
