# RareGenXAI local development on Apple Silicon (M5, 16 GB)

This guide sets up the **existing** Streamlit research prototype. The proposed React / FastAPI application is for later phases. No cloud hosting or paid API is required.

## What you need

- Mac with Apple Silicon and preferably 25 GB or more free SSD space.
- macOS Terminal, Git, Python **3.11** (preferred) or **3.12**.
- Homebrew is convenient but optional: https://brew.sh
- Node.js and npm are optional for Phase 1, but are needed when the React frontend begins.
- VS Code or another editor, working internet for first HPO download, access to this private repository.
- **Do not input identifiable patient records.** This is a research-only ranking tool, not a diagnostic service.

## 1. Install tools

In Terminal, first inspect your processor and existing tools:

```bash
uname -m             # arm64 on native Apple Silicon
xcode-select -p      # If missing, install command-line tools
python3.11 --version
git --version
node --version       # Optional until frontend work
```

If command-line tools are missing, run `xcode-select --install`. If using Homebrew:

```bash
brew install python@3.11 git node
```

Check `python3.11 --version` after installation. The Python dependencies are installed inside the project virtual environment, not globally. Avoid `sudo pip install`.

## 2. Get project code

```bash
git clone https://github.com/uday8116/RareGenXAI.git
cd RareGenXAI
```

The repository is private: authenticate with GitHub via your existing Git credential method. Before the Phase 1 pull request is merged, check out its feature branch with `git switch phase-01/foundation-macos-m5`. After merging, use `main`.

## 3. Bootstrap and verify

```bash
bash scripts/bootstrap_macos.sh
bash scripts/verify_local.sh
.venv/bin/python scripts/doctor.py --json
```

Bootstrap chooses a native `python3.11` or `python3.12`, creates `.venv`, installs `requirements.txt`, and runs the doctor. Bootstrap does not train ML models or fetch medical data unless requested. The doctor examines version, packages, command-line tools, free storage, HPO files, and model-artifact presence. It **does not** validate the contents of a trained model or the clinical meaning of data.

The quick verification runs environment checks and selected deterministic project tests without downloading HPO.

## 4. Prepare official HPO files

```bash
bash scripts/bootstrap_macos.sh --data
bash scripts/verify_local.sh --full
```

Data preparation downloads `hp.obo` and `phenotype.hpoa`, writes a SHA-256 source manifest and creates `data/processed/profiles.json`. The data is stored locally and gitignored. The `--full` check requires the prepared files and runs the complete Python test suite. If the official file schema changes, data preparation may fail; capture the error instead of inventing replacement data.

## 5. Start the current local UI

```bash
.venv/bin/python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`. This is the current Streamlit prototype. The React website and FastAPI service will be developed in subsequent phases.

## 6. Training is Phase 3, not Phase 1

The source repository includes an ML training script, but local trained weights are not shipped with Git:

```bash
.venv/bin/python -m src.train_ml
.venv/bin/python scripts/doctor.py --require-data --require-model
```

Only run the training command **after** preparing HPO data and selecting the planned model configurations. It trains synthetic HPO-derived examples, not real clinical patients. Existing benchmark results are not new local measurements.

## Troubleshooting

- `python3.11: command not found`: ensure Python 3.11 is installed and your shell PATH is updated, then open a new Terminal window.
- Wrong Python in `.venv`: after backing up any important local changes, delete `.venv` and rerun the bootstrap. Do not delete `data/` or `models/` when resetting Python.
- `ModuleNotFoundError`: rerun bootstrap and use `.venv/bin/python`, rather than the system Python.
- XGBoost shared library / `libomp` error on Apple Silicon: if it occurs, try `brew install libomp` and reinstall affected Python dependencies. Do not install this unless the error happens.
- HPO download error: verify internet access and official source URLs in `src/data.py`. Never replace failed downloads with fabricated data.
- `--full` reports missing HPO: run `bash scripts/bootstrap_macos.sh --data` first.
- Low memory: stop other resource-heavy applications, use one training process at a time, and avoid a full GNN experiment during bootstrap.
- No local website from React yet: expected in Phase 1; use the existing Streamlit app.

## Verify successful Phase 1 setup

The quick verification should exit with code 0. The doctor should report supported Python and available core modules. Missing HPO or saved models can be warnings at this stage; those artifacts belong to later phases. Keep the terminal output for debugging.
