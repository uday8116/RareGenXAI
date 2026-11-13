# GNN research architecture proposal (not yet implemented)

## Goal
Explore whether HPO graph structure can improve disease ranking beyond exact phenotype overlap and the new XGBoost/MLP rerankers. This is a research proposal, **not an implemented or validated GNN**.

## Graph representation
- HPO nodes: phenotype terms from official hp.obo.
- Disease nodes: IDs from phenotype.hpoa.
- Typed edges: phenotype parent/child relations and disease–phenotype annotation edges.
- Patient input: a set of observed phenotype nodes and evidence-status attributes.

## Candidate architecture
1. Construct a heterogeneous graph and freeze a versioned HPO snapshot.
2. Encode phenotype and disease nodes using trainable embeddings and/or ontology information content.
3. Apply a 2-layer relation-aware graph encoder (e.g. R-GCN) with separate relation types.
4. Aggregate patient HPO embeddings with confidence-weighted attention.
5. Score disease nodes using patient–disease embedding similarity or a small MLP head.
6. Expose feature-attribution and ranking-stability analysis, and verify explanations against controlled perturbations.

## Experimental safeguards
- Split training/validation/test by case and disease where appropriate; never use test diagnoses to construct training targets.
- Disease–phenotype edges from the reference ontology may contain information linked to published patient cases; document annotation leakage risk.
- Compare against exact overlap, semantic similarity, TF-IDF, Logistic Regression, Random Forest, XGBoost and MLP under identical evaluation conditions.
- Report candidate coverage, Top-1, Top-5, MRR, per-cohort performance and confidence intervals.
- Conduct ablations: no HPO edges, no disease–phenotype edges, no attention, no uncertainty weighting.
- Do not call graph attention coefficients clinical explanations without validating explanation faithfulness.
- Check memory and runtime constraints; graph methods may need PyTorch Geometric and dedicated compute.

## Milestones
1. Graph data export and tests.
2. Minimal graph encoder with train/validation separation.
3. Controlled training and ablations.
4. Patient-case external evaluation and failure analysis.
5. Optional integration in Streamlit after validation.

## Current status
XGBoost and MLP source code added; GNN design documented only. Do not claim that GNN has been trained or evaluated.
