/** Historical, independently reported RareBench measurements (not live data).
 * All methods evaluated on 178 eligible published cases using the same cohort.
 * Values are percentages, not patient-specific predicted probabilities.
 */
export const BENCHMARK_SOURCE = 'https://github.com/uday8116/RareGenXAI/actions/runs/44484831306';
export const BENCHMARK_CASES = 178;
export const BENCHMARK = [
  { id: 'overlap', label: 'Exact HPO overlap', top1: 37.64, top5: 54.49, kind: 'Knowledge baseline' },
  { id: 'xgboost', label: 'XGBoost', top1: 37.64, top5: 48.88, kind: 'Supervised reranker' },
  { id: 'random_forest', label: 'Random Forest', top1: 34.27, top5: 41.57, kind: 'Supervised reranker' },
  { id: 'logistic', label: 'Logistic Regression', top1: 32.58, top5: 47.19, kind: 'Supervised reranker' },
  { id: 'tfidf', label: 'TF-IDF retrieval', top1: 29.78, top5: 43.26, kind: 'Retrieval baseline' },
  { id: 'mlp', label: 'Neural MLP', top1: 26.40, top5: 32.02, kind: 'Supervised reranker' },
];
export const METHOD_LABELS = {
  overlap: 'Exact HPO overlap',
  semantic: 'Ontology similarity',
  tfidf: 'TF-IDF retrieval',
  logistic: 'Logistic Regression',
  random_forest: 'Random Forest',
  xgboost: 'XGBoost',
  mlp: 'Neural MLP',
};
export const EVIDENCE_STATUS = [
  { value: 'confirmed_present', label: 'Confirmed present' },
  { value: 'suspected_present', label: 'Suspected present' },
  { value: 'confirmed_absent', label: 'Confirmed absent' },
  { value: 'unknown', label: 'Unknown' },
];
export const SAMPLE_PHENOTYPES = [
  { hpo_id: 'HP:0001250', name: 'Seizure', status: 'confirmed_present' },
  { hpo_id: 'HP:0001263', name: 'Global developmental delay', status: 'suspected_present' },
];
export const LIMITS = { maxObservations: 20, maxResults: 20, defaultCandidates: 40 };
