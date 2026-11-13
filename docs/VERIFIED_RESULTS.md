# Verified preliminary experiment results

Source: https://github.com/uday8116/RareGenXAI/actions/runs/43474246347

## Data and execution
- Official HPO annotation rows processed: **286,649**.
- Positive disease profiles built: **12,879**.
- Automated unit tests: **7 passed**.
- Small synthetic benchmark: **3 queries at each of four missingness rates**, 12 query scenarios and 36 method evaluations.
- All three methods returned identical metrics in this small smoke benchmark.

| Missingness | Top-1 | Top-5 | MRR |
|---|---:|---:|---:|
| 0% | 1.000 | 1.000 | 1.000 |
| 20% | 0.667 | 1.000 | 0.833 |
| 40% | 0.667 | 0.667 | 0.671 |
| 60% | 0.000 | 0.333 | 0.197 |

These results are from the actual GitHub Actions log, not fabricated values.

## Critical limitations
- Only three synthetic queries per missingness rate; no statistical significance or generalization claim.
- No advantage of the proposed evidence-weighted method was demonstrated.
- The current synthetic generator samples positive phenotypes from the same disease annotations used to rank candidates, so this is not independent patient validation.
- The benchmark does not simulate confirmed-absent observations; the negative-evidence capability is implemented but not evaluated here.
- The scores are ranking scores, not calibrated disease probabilities.
- No clinical accuracy, diagnosis, safety, or novelty claim follows from these measurements.

## Expanded verification
The current workflow adds a Streamlit integration test after dataset preparation, a larger 12-query-per-missingness benchmark, and measured plots. See the latest Actions run in the repository. These are still preliminary experiments, not a completed clinical validation study.
