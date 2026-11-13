# Experimental HPO GNN: implementation status

The new `src/gnn.py` implements a two-layer GraphSAGE-style neural network using PyTorch. It aggregates HPO parent-child neighbors, pools disease annotations, encodes patient observations, and learns a candidate-ranking head from **synthetic HPO disease-profile queries**. This is an experimental research baseline, not a clinically validated model.

## Run
```bash
python -m pip install -r requirements.txt
python -m pip install torch
python -m src.data
python -m src.rarebench --limit-per-subset 100000
python -m pytest tests/test_gnn.py -q
python -m src.evaluate_gnn --train-diseases 40 --epochs 2
```

Results are written to `results/gnn_external_summary.json` and `results/gnn_external_cases.csv`. Training on the full HPO graph may be slow on CPU; start with the smaller configuration above.

## Important limitations
- PyTorch is optional and not installed in the standard CI environment; the GNN smoke test skips when torch is unavailable. A green standard CI run does **not** prove the neural network test executed.
- The GNN is trained on synthetic disease profiles, not patient data.
- The reference graph includes disease–phenotype annotations from the same knowledge base used for evaluation; literature overlap and information leakage are possible.
- Candidate retrieval is limited to TF-IDF top 40; a GNN cannot rescue diagnoses missing from that shortlist.
- No matched-case GNN metrics or statistical evidence of superiority exist until the experiment completes.
- A proper research evaluation should use disease-disjoint held-out synthetic queries, repeated random seeds, paired confidence intervals, cohort-specific error analysis and ablations before making claims.
