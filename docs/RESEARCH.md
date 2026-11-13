# Research protocol (preliminary)

## Research question
Does distinguishing confirmed-present, suspected-present, confirmed-absent and unknown findings improve phenotype-based rare-disease ranking under incomplete observations?

## Contribution under investigation
A transparent HPO semantic similarity ranking function with explicit observation reliability weights and per-observation score decomposition. This is a **hypothesis**, not a verified novel algorithm.

## Comparators
1. Exact HPO overlap (positive findings only).
2. Ontology-aware semantic matching (positive findings only).
3. Proposed semantic matching with evidence-quality weights.

## Experimental design
Sample disease-phenotype queries from HPO disease annotations for an initial controlled synthetic benchmark. Vary missingness 0%, 20%, 40%, 60%; use fixed random seeds. Report Top-1, Top-5, and MRR, along with number of queries and release checksums. Note that the same knowledge base is used to construct and evaluate these synthetic queries, creating an optimistic evaluation bias.

## Key threats to validity
- No independent patient cases yet.
- HPOA associations are disease knowledge, not real patient observations.
- Synthetic suspected-status labels do not represent clinical confidence.
- Negative phenotype weights are heuristics.
- Uncertainty is not calibrated.
- Disease annotations can be sparse or biased.
- LIRICAL and related methods already model negative evidence; novelty cannot be claimed from that alone.
- Scores are not probabilities; results must not be used for patient care.

## Publication requirements
Conduct a comprehensive current literature review, use independent real-case validation with permission, evaluate against fair published baselines, report statistical intervals and error analysis, and make code and data versions reproducible. Do not fabricate experiments or accuracy values.

## Proposed report outline
Introduction; HPO foundations; literature survey; dataset provenance; methods and mathematical definition; system architecture; experiments; results; limitations; conclusion; references.
