# Phase 7 — Independently checked historical RareBench benchmark archive

**Evidence type:** Reanalysis of real saved patient-case *predictions*, not a new Phase 7 inference run and **not prospective clinical validation**.

- Original GitHub Actions workflow: https://github.com/uday8116/RareGenXAI/actions/runs/44467435510
- Original artifact: `external-patient-benchmark` from the above workflow
- Retrospective de-identified dataset: published RareBench, 178 eligible cases (LIRICAL 143, MME 11, HMS 24)
- Original case CSV is **not contained in the GitHub archive**. The archived manifest's claim of its hash and each case's phenotype observations **could not be independently rechecked**.
- The full `joblib` model artifact was **not in this archive**. The model hash and disease universe below were reported by the archived saved-model manifest and are not an independent reload test.
- New exploratory confidence intervals: 2,000 within-cohort case-level percentile-bootstrap replicates, fixed seed 42. These do not justify statistical-significance or clinical-performance claims.

**Reproduce using the archived artifact downloaded from the linked workflow:**

```bash
python -m src.phase7_historical_reaudit --archive path/to/external-patient-benchmark.zip \
  --out-dir results/phase7_historical --run-id 44467435510 \
  --replicates 2000 --seed 42 --ml-rank-cap 40
```

The script checks every archived case-method ranking row and cross-checks the archived cohort summary before computing and writing interval results. It intentionally cannot independently validate the original HPO observations or repeat the trained models' predictions.

## Source fingerprints from inspected archive

- `data/external/rarebench_manifest.json`: `efbeb46700370d7c9b107e30906ea9375416c6aeb8983f37a905fa48f34d3b62`
- `models/raregen_ml.manifest.json`: `b002272134b12920e73a780b58bea700b85cc45894b831968fd996e3814d2d55`
- `results/external_case_results.csv`: `f4cfba8df16ec6dd53d7f20180d1276efe7d3849cbc6a1debed03bb815cfb93b`
- `results/external_cohort_summary.csv`: `0f2f93079218790cbada172b035ac0be3eba60bce4b0f18a1662eb540fb7d797`
- Artifact ZIP SHA-256: `c4175a83ab2f2b6ef53f29f1cff063cd59f8c606842c8c90ae3fc1eb68f836e2`
- Source RareBench CSV SHA-256 **claimed by archived manifest, not recomputed**: `7976df1ec8159c24b5dae8db2bd3e598547ef81421acdc901f5b095938761ddd`

## Recomputed, archive-backed results

**NOT a new Phase 7 inference run. NOT clinical validation.** This recomputes metrics and
uncertainty from the actual archived 178-case results of GitHub Actions run 44467435510.

The original HPO observation CSV and full saved model are not in this archive.
Therefore original phenotype inputs, model predictions, and the dataset CSV SHA cannot be independently checked.

## Archived results and exploratory 95% bootstrap intervals

| Cohort | N | Method | Top-1 | Top-5 | MRR | Known-disease coverage | List recall |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| ALL | 178 | logistic | 34.27% [27.53%, 41.01%] | 48.88% [41.57%, 56.18%] | 0.410 [0.346, 0.475] | 99.44% [98.31%, 100.00%] | 63.48% [56.18%, 70.22%] |
| ALL | 178 | mlp | 30.90% [24.16%, 37.64%] | 41.57% [34.27%, 48.88%] | 0.363 [0.300, 0.428] | 99.44% [98.31%, 100.00%] | 63.48% [56.18%, 70.22%] |
| ALL | 178 | overlap | 37.64% [30.34%, 44.94%] | 54.49% [47.19%, 61.80%] | 0.453 [0.387, 0.522] | 99.44% [98.31%, 100.00%] | 99.44% [98.31%, 100.00%] |
| ALL | 178 | random_forest | 32.58% [25.84%, 39.33%] | 42.13% [35.39%, 49.44%] | 0.371 [0.304, 0.435] | 99.44% [98.31%, 100.00%] | 63.48% [56.74%, 70.79%] |
| ALL | 178 | tfidf | 29.78% [23.60%, 35.96%] | 43.26% [35.96%, 50.00%] | 0.361 [0.298, 0.425] | 99.44% [98.31%, 100.00%] | 63.48% [56.18%, 70.22%] |
| ALL | 178 | xgboost | 36.52% [29.78%, 43.82%] | 51.69% [44.38%, 59.55%] | 0.436 [0.373, 0.502] | 99.44% [98.31%, 100.00%] | 63.48% [56.74%, 70.79%] |
| HMS | 24 | logistic | 4.17% [0.00%, 12.50%] | 20.83% [4.17%, 37.50%] | 0.112 [0.032, 0.223] | 95.83% [87.50%, 100.00%] | 33.33% [16.67%, 54.17%] |
| HMS | 24 | mlp | 4.17% [0.00%, 12.50%] | 8.33% [0.00%, 20.83%] | 0.068 [0.011, 0.163] | 95.83% [87.50%, 100.00%] | 33.33% [16.67%, 50.00%] |
| HMS | 24 | overlap | 0.00% [0.00%, 0.00%] | 8.33% [0.00%, 20.83%] | 0.048 [0.014, 0.100] | 95.83% [87.50%, 100.00%] | 95.83% [87.50%, 100.00%] |
| HMS | 24 | random_forest | 0.00% [0.00%, 0.00%] | 0.00% [0.00%, 0.00%] | 0.012 [0.005, 0.021] | 95.83% [87.50%, 100.00%] | 33.33% [16.67%, 54.17%] |
| HMS | 24 | tfidf | 4.17% [0.00%, 12.50%] | 8.33% [0.00%, 20.83%] | 0.062 [0.008, 0.160] | 95.83% [87.50%, 100.00%] | 33.33% [16.67%, 50.00%] |
| HMS | 24 | xgboost | 0.00% [0.00%, 0.00%] | 20.83% [8.33%, 37.50%] | 0.095 [0.035, 0.167] | 95.83% [87.50%, 100.00%] | 33.33% [16.67%, 54.17%] |
| LIRICAL | 143 | logistic | 37.76% [30.07%, 45.45%] | 51.05% [42.66%, 59.44%] | 0.439 [0.362, 0.514] | 100.00% [100.00%, 100.00%] | 66.43% [58.04%, 74.13%] |
| LIRICAL | 143 | mlp | 32.87% [25.17%, 40.56%] | 44.06% [36.36%, 52.45%] | 0.384 [0.308, 0.457] | 100.00% [100.00%, 100.00%] | 66.43% [58.04%, 74.13%] |
| LIRICAL | 143 | overlap | 41.26% [33.57%, 50.35%] | 59.44% [51.05%, 67.13%] | 0.494 [0.422, 0.567] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] |
| LIRICAL | 143 | random_forest | 34.97% [27.27%, 43.36%] | 46.85% [38.46%, 55.94%] | 0.402 [0.327, 0.482] | 100.00% [100.00%, 100.00%] | 66.43% [58.04%, 74.13%] |
| LIRICAL | 143 | tfidf | 32.17% [24.48%, 39.86%] | 46.15% [38.46%, 54.55%] | 0.387 [0.313, 0.457] | 100.00% [100.00%, 100.00%] | 66.43% [58.04%, 74.83%] |
| LIRICAL | 143 | xgboost | 41.26% [33.57%, 48.95%] | 54.55% [46.15%, 62.24%] | 0.474 [0.397, 0.550] | 100.00% [100.00%, 100.00%] | 66.43% [58.74%, 74.13%] |
| MME | 11 | logistic | 54.55% [27.27%, 81.82%] | 81.82% [54.55%, 100.00%] | 0.688 [0.461, 0.909] | 100.00% [100.00%, 100.00%] | 90.91% [72.73%, 100.00%] |
| MME | 11 | mlp | 63.64% [36.36%, 90.91%] | 81.82% [54.55%, 100.00%] | 0.742 [0.500, 0.955] | 100.00% [100.00%, 100.00%] | 90.91% [72.73%, 100.00%] |
| MME | 11 | overlap | 72.73% [45.45%, 100.00%] | 90.91% [72.73%, 100.00%] | 0.803 [0.576, 1.000] | 100.00% [100.00%, 100.00%] | 100.00% [100.00%, 100.00%] |
| MME | 11 | random_forest | 72.73% [45.45%, 100.00%] | 72.73% [45.45%, 90.91%] | 0.741 [0.478, 1.000] | 100.00% [100.00%, 100.00%] | 90.91% [72.73%, 100.00%] |
| MME | 11 | tfidf | 54.55% [27.27%, 81.82%] | 81.82% [54.55%, 100.00%] | 0.671 [0.444, 0.894] | 100.00% [100.00%, 100.00%] | 90.91% [72.73%, 100.00%] |
| MME | 11 | xgboost | 54.55% [27.27%, 81.82%] | 81.82% [54.55%, 100.00%] | 0.685 [0.458, 0.867] | 100.00% [100.00%, 100.00%] | 90.91% [72.73%, 100.00%] |

## Paired differences from exact overlap on identical saved case IDs

| Cohort | Method | Metric | Difference [exploratory 95% CI] |
| --- | --- | --- | ---: |
| ALL | logistic | top1 | -0.0337 [-0.0899, +0.0169] |
| ALL | logistic | top5 | -0.0562 [-0.1124, +0.0000] |
| ALL | logistic | mrr | -0.0431 [-0.0865, -0.0005] |
| ALL | mlp | top1 | -0.0674 [-0.1292, -0.0112] |
| ALL | mlp | top5 | -0.1292 [-0.1966, -0.0618] |
| ALL | mlp | mrr | -0.0896 [-0.1399, -0.0407] |
| ALL | random_forest | top1 | -0.0506 [-0.1067, +0.0056] |
| ALL | random_forest | top5 | -0.1236 [-0.1798, -0.0618] |
| ALL | random_forest | mrr | -0.0823 [-0.1282, -0.0363] |
| ALL | tfidf | top1 | -0.0787 [-0.1404, -0.0225] |
| ALL | tfidf | top5 | -0.1124 [-0.1742, -0.0506] |
| ALL | tfidf | mrr | -0.0925 [-0.1379, -0.0489] |
| ALL | xgboost | top1 | -0.0112 [-0.0618, +0.0449] |
| ALL | xgboost | top5 | -0.0281 [-0.0787, +0.0225] |
| ALL | xgboost | mrr | -0.0169 [-0.0560, +0.0216] |
| HMS | logistic | top1 | +0.0417 [+0.0000, +0.1250] |
| HMS | logistic | top5 | +0.1250 [+0.0000, +0.2917] |
| HMS | logistic | mrr | +0.0636 [+0.0158, +0.1218] |
| HMS | mlp | top1 | +0.0417 [+0.0000, +0.1250] |
| HMS | mlp | top5 | +0.0000 [-0.1250, +0.1250] |
| HMS | mlp | mrr | +0.0205 [-0.0228, +0.0725] |
| HMS | random_forest | top1 | +0.0000 [+0.0000, +0.0000] |
| HMS | random_forest | top5 | -0.0833 [-0.2083, +0.0000] |
| HMS | random_forest | mrr | -0.0357 [-0.0824, -0.0038] |
| HMS | tfidf | top1 | +0.0417 [+0.0000, +0.1250] |
| HMS | tfidf | top5 | +0.0000 [-0.1667, +0.1667] |
| HMS | tfidf | mrr | +0.0137 [-0.0610, +0.1150] |
| HMS | xgboost | top1 | +0.0000 [+0.0000, +0.0000] |
| HMS | xgboost | top5 | +0.1250 [+0.0000, +0.2500] |
| HMS | xgboost | mrr | +0.0466 [+0.0071, +0.0939] |
| LIRICAL | logistic | top1 | -0.0350 [-0.0979, +0.0280] |
| LIRICAL | logistic | top5 | -0.0839 [-0.1469, -0.0210] |
| LIRICAL | logistic | mrr | -0.0555 [-0.1042, -0.0076] |
| LIRICAL | mlp | top1 | -0.0839 [-0.1608, -0.0070] |
| LIRICAL | mlp | top5 | -0.1538 [-0.2308, -0.0769] |
| LIRICAL | mlp | mrr | -0.1103 [-0.1752, -0.0524] |
| LIRICAL | random_forest | top1 | -0.0629 [-0.1329, +0.0070] |
| LIRICAL | random_forest | top5 | -0.1259 [-0.2028, -0.0559] |
| LIRICAL | random_forest | mrr | -0.0916 [-0.1471, -0.0342] |
| LIRICAL | tfidf | top1 | -0.0909 [-0.1538, -0.0210] |
| LIRICAL | tfidf | top5 | -0.1329 [-0.2028, -0.0699] |
| LIRICAL | tfidf | mrr | -0.1073 [-0.1599, -0.0575] |
| LIRICAL | xgboost | top1 | +0.0000 [-0.0629, +0.0559] |
| LIRICAL | xgboost | top5 | -0.0490 [-0.1049, +0.0070] |
| LIRICAL | xgboost | mrr | -0.0198 [-0.0663, +0.0257] |
| MME | logistic | top1 | -0.1818 [-0.4545, +0.0000] |
| MME | logistic | top5 | -0.0909 [-0.2727, +0.0000] |
| MME | logistic | mrr | -0.1149 [-0.2298, -0.0003] |
| MME | mlp | top1 | -0.0909 [-0.2727, +0.0000] |
| MME | mlp | top5 | -0.0909 [-0.2727, +0.0000] |
| MME | mlp | mrr | -0.0608 [-0.1518, +0.0000] |
| MME | random_forest | top1 | +0.0000 [+0.0000, +0.0000] |
| MME | random_forest | top5 | -0.1818 [-0.4545, +0.0000] |
| MME | random_forest | mrr | -0.0620 [-0.1644, +0.0000] |
| MME | tfidf | top1 | -0.1818 [-0.4545, +0.0000] |
| MME | tfidf | top5 | -0.0909 [-0.2727, +0.0000] |
| MME | tfidf | mrr | -0.1317 [-0.2528, -0.0305] |
| MME | xgboost | top1 | -0.1818 [-0.4545, +0.0000] |
| MME | xgboost | top5 | -0.0909 [-0.2727, +0.0000] |
| MME | xgboost | mrr | -0.1179 [-0.2541, -0.0005] |

## Scientific limits

- Same published RareBench cohort as earlier research; NOT independent prospective cases.
- Potential literature leakage between patient descriptions and HPO disease annotations.
- ML shortlisting (40) differs from full-disease-universe exact overlap.
- Bootstrap intervals assume exchangeable cases and are exploratory with small cohorts.
- No authentic DeepRare predictions on these identical cases; no matched comparison.
- Archived source/model SHA claims are recorded but original case CSV and model bytes are absent.

See historical_provenance.json and archived GitHub run for exact fingerprints.
