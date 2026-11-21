"""Strict retrospective reanalysis of an existing RareGenXAI GitHub Actions artifact ZIP.

This validates SAVED predictions/metrics and computes fresh exploratory intervals.
It cannot verify the original patient's HPO input CSV or rerun the model.
Research-only; never clinical validation or a newly run Phase 7 experiment.
"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import io
import json
import math
import random
import zipfile
from pathlib import Path

NEEDED=("data/external/rarebench_manifest.json", "models/raregen_ml.manifest.json",
        "results/external_case_results.csv", "results/external_cohort_summary.csv")
FIELDS=("top1", "top5", "mrr", "candidate_recall", "disease_coverage")


def sha(data):return hashlib.sha256(data).hexdigest()


def rows_from(raw):
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):
        raise ValueError("Duplicate/missing header fields")
    rows=list(reader)
    if not rows or any(None in x or any(y is None for y in x.values()) for x in rows):
        raise ValueError("Empty, malformed or extra CSV records")
    return rows


def ci(values, seed, replicates):
    if replicates < 100 or replicates > 100000:raise ValueError("Bootstrap replicate count out of bounds")
    if not values:raise ValueError("No eligible cases")
    rng=random.Random(int(sha(json.dumps(seed,separators=(",", ":")).encode())[:16],16))
    n=len(values)
    draws=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(replicates))
    return draws[int(.025*(replicates-1))],draws[int(.975*(replicates-1))]


def write_csv(path, rows):
    if not rows:raise ValueError("Cannot emit an empty results table")
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return sha(path.read_bytes())


def reanalyse(archive_path, out_dir, *, run_id, replicates=2000, seed=42, ml_rank_cap=40):
    if not str(run_id).isdigit() or ml_rank_cap < 1:raise ValueError("Invalid run ID or ML cap")
    archive_path=Path(archive_path);out=Path(out_dir)
    with zipfile.ZipFile(archive_path) as z:
        invalid=z.testzip()
        if invalid:raise ValueError("Corrupted ZIP entry: "+invalid)
        if not set(NEEDED).issubset(z.namelist()):raise ValueError("Missing original archived benchmark/manifest files")
        data={path:z.read(path) for path in NEEDED}
    dataset=json.loads(data[NEEDED[0]])
    model=json.loads(data[NEEDED[1]])
    raw=rows_from(data[NEEDED[2]])
    original_summary=rows_from(data[NEEDED[3]])
    if dataset.get('dataset')!='chenxz/RareBench' or dataset.get('eligible_total') is None:
        raise ValueError("Unsupported dataset provenance")
    if model.get('source',{}).get('kind')!='hpo_sqlite_v2_aspect_P':
        raise ValueError("Model is not an official phenotype-only HPO snapshot")
    disease_universe=model.get('disease_universe')
    if not isinstance(disease_universe,int) or disease_universe<=0:raise ValueError("Missing model universe size")
    cases=collections.defaultdict(dict)
    methods=set()
    for r in raw:
        case=r.get('case_id','').strip();method=r.get('method','').strip()
        truth=r.get('true_disease_id','').strip();cohort=r.get('cohort','').strip()
        if not (case and method and truth and cohort):raise ValueError("Empty required field")
        if method in cases[case]:raise ValueError(f"Duplicate record {case}/{method}")
        methods.add(method)
        known=r.get('known_disease')
        if known not in ('0','1'):raise ValueError("Invalid disease universe flag")
        rank_raw=r.get('rank','').strip()
        rank=None if not rank_raw else int(rank_raw) if rank_raw.isdecimal() and int(rank_raw)>0 else None
        if rank_raw and rank is None:raise ValueError("Invalid rank")
        if rank is not None and known=='0':raise ValueError("Unknown disease assigned a rank")
        if rank is not None and (rank>disease_universe or (method!='overlap' and rank>ml_rank_cap)):
            raise ValueError("Rank beyond known candidate limit")
        top1=int(rank==1);top5=int(rank is not None and rank<=5);rr=1/rank if rank else 0
        if (r.get('top1')!=str(top1) or r.get('top5')!=str(top5) or
            not math.isclose(float(r.get('reciprocal_rank')),rr,rel_tol=0,abs_tol=1e-9)):
            raise ValueError("Fabricated rank flags or reciprocal-rank value")
        cases[case][method]={'case_id':case,'cohort':cohort,'method':method,'truth':truth,
           'known':int(known),'rank':rank,'top1':top1,'top5':top5,'mrr':rr,
           'candidate_recall':int(rank is not None),'disease_coverage':int(known)}
    methods=sorted(methods)
    if 'overlap' not in methods or len(methods)<2:raise ValueError("No paired baseline")
    if len(cases)!=dataset['eligible_total']:raise ValueError("Archived eligible case count disagrees with results")
    metadata={}
    for case,ms in cases.items():
        if set(ms)!=set(methods):raise ValueError("Incomplete case-method matrix: "+case)
        facts={(r['cohort'],r['truth'],r['known']) for r in ms.values()}
        if len(facts)!=1:raise ValueError("Cohort/diagnosis/disease coverage mismatch")
        metadata[case]=next(iter(facts))
    cohorts=collections.Counter(x[0] for x in metadata.values())
    if 'ALL' in cohorts:raise ValueError("Reserved cohort ALL")
    # Published aggregate is independently recomputed from individual case rankings.
    old={(r['cohort'],r['method']):r for r in original_summary}
    expected={(co,m) for co in ('ALL',*cohorts) for m in methods}
    if len(old)!=len(original_summary) or set(old)!=expected:raise ValueError("Published summary has missing/extra/duplicate groups")
    summary=[];paired=[];errors=[]
    for cohort in ('ALL',*sorted(cohorts)):
        ids=sorted(c for c in cases if cohort=='ALL' or metadata[c][0]==cohort)
        for method in methods:
            subset=[cases[c][method] for c in ids];n=len(ids)
            o=old[(cohort,method)]
            if o.get('n')!=str(n):raise ValueError("Incorrect archived cohort N")
            for field,archived in [('top1','top1'),('top5','top5'),('mrr','mrr'),
                                   ('disease_coverage','disease_coverage'),('candidate_recall','candidate_recall')]:
                measured=sum(r[field] for r in subset)/n
                if not math.isclose(float(o[archived]),measured,rel_tol=0,abs_tol=1e-9):
                    raise ValueError(f"Archived {cohort}/{method}/{field} does not match cases")
                lo,hi=ci([r[field] for r in subset],[seed,cohort,method,field],replicates)
                summary.append(dict(cohort=cohort,method=method,metric=field,n=n,
                                    estimate=measured,ci95_low=lo,ci95_high=hi))
                if method!='overlap' and field!='disease_coverage':
                    diffs=[cases[c][method][field]-cases[c]['overlap'][field] for c in ids]
                    dlo,dhi=ci(diffs,[seed,cohort,method,field,'paired'],replicates)
                    paired.append(dict(cohort=cohort,method=method,baseline='overlap',metric=field,
                                       n=n,difference=sum(diffs)/n,ci95_low=dlo,ci95_high=dhi))
            reasons=collections.Counter('top1_hit' if r['rank']==1 else 'rank_2_to_5' if r['rank'] and r['rank']<=5
                else 'rank_beyond_top5' if r['rank'] else 'truth_outside_model_disease_universe' if not r['known']
                else 'truth_not_in_returned_ranked_list' for r in subset)
            for name,count in sorted(reasons.items()):
                errors.append(dict(cohort=cohort,method=method,error_category=name,n=n,
                                   count=count,fraction=count/n))
    training=model.get('training',{})
    trained=set(training.get('train_disease_ids',[]));heldout=set(training.get('heldout_disease_ids',[]))
    if trained&heldout:raise ValueError('Overlap of synthetic training/heldout IDs')
    overlap=[]
    for cohort in ('ALL',*sorted(cohorts)):
        ids=[c for c in cases if cohort=='ALL' or metadata[c][0]==cohort]
        labels=collections.Counter('outside_model_disease_universe' if not metadata[c][2] else
            'synthetic_training_disease' if metadata[c][1] in trained else
            'synthetic_heldout_disease' if metadata[c][1] in heldout else
            'other_model_disease_or_unrecorded_split' for c in ids)
        for label,count in sorted(labels.items()):
            overlap.append(dict(cohort=cohort,split_membership=label,n=len(ids),count=count,fraction=count/len(ids)))
    out.mkdir(parents=True,exist_ok=True)
    hashes={}
    for name,table in [('historical_cohort_metrics.csv',summary),('historical_paired_effects.csv',paired),
                       ('historical_error_analysis.csv',errors),('historical_training_overlap.csv',overlap)]:
        hashes[name]=write_csv(out/name,table)
    provenance=dict(scope='HISTORICAL ARCHIVED PREDICTIONS ONLY — NOT A NEW PHASE 7 MODEL RUN',
        github_workflow_run_id=str(run_id),archive_sha256=sha(archive_path.read_bytes()),
        archived_files_sha256={key:sha(value) for key,value in data.items()},
        published_rarebench_csv_claimed_sha256_not_independently_verified=dataset.get('sha256'),
        model_artifact_sha256_claimed_by_archived_manifest=model.get('artifact_sha256'),
        disease_universe=disease_universe,cohorts=dict(sorted(cohorts.items())),
        case_count=len(cases),methods=methods,ml_rank_cap_inferred_from_workflow=ml_rank_cap,
        bootstrap_seed=seed,bootstrap_replicates=replicates,output_csv_sha256=hashes,
        limitation='Original phenotype input CSV and full model weights are NOT in this archive; cannot reproduce original predictions or confirm source-case CSV hash')
    (out/'historical_provenance.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n')
    def entry(c,m,field):return next(r for r in summary if (r['cohort'],r['method'],r['metric'])==(c,m,field))
    lines=["# Phase 7 independent historical-archive reanalysis", "",
       "**NOT a new Phase 7 inference run. NOT clinical validation.** This recomputes metrics and",
       "uncertainty from the actual archived 178-case results of GitHub Actions run "+str(run_id)+".","",
       "The original HPO observation CSV and full saved model are not in this archive.",
       "Therefore original phenotype inputs, model predictions, and the dataset CSV SHA cannot be independently checked.","",
       "## Archived results and exploratory 95% bootstrap intervals","",
       "| Cohort | N | Method | Top-1 | Top-5 | MRR | Known-disease coverage | List recall |",
       "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |"]
    def fmt(r,percent=False):
        vals=[r[k] for k in ('estimate','ci95_low','ci95_high')]
        return (f'{vals[0]*100:.2f}% [{vals[1]*100:.2f}%, {vals[2]*100:.2f}%]' if percent
                else f'{vals[0]:.3f} [{vals[1]:.3f}, {vals[2]:.3f}]')
    for co in ('ALL',*sorted(cohorts)):
        for m in methods:
            lines.append(f"| {co} | {len(cases) if co=='ALL' else cohorts[co]} | {m} | "+' | '.join(
              fmt(entry(co,m,k),k!='mrr') for k in ('top1','top5','mrr','disease_coverage','candidate_recall'))+' |')
    lines += ["", "## Paired differences from exact overlap on identical saved case IDs", "",
              "| Cohort | Method | Metric | Difference [exploratory 95% CI] |", "| --- | --- | --- | ---: |"]
    for row in paired:
        if row['metric'] in ('top1','top5','mrr'):
            lines.append(f"| {row['cohort']} | {row['method']} | {row['metric']} | "
                f"{row['difference']:+.4f} [{row['ci95_low']:+.4f}, {row['ci95_high']:+.4f}] |")
    lines += ["","## Scientific limits", "",
      "- Same published RareBench cohort as earlier research; NOT independent prospective cases.",
      "- Potential literature leakage between patient descriptions and HPO disease annotations.",
      "- ML shortlisting (40) differs from full-disease-universe exact overlap.",
      "- Bootstrap intervals assume exchangeable cases and are exploratory with small cohorts.",
      "- No authentic DeepRare predictions on these identical cases; no matched comparison.",
      "- Archived source/model SHA claims are recorded but original case CSV and model bytes are absent.","",
      "See historical_provenance.json and archived GitHub run for exact fingerprints.",""]
    (out/'historical_report.md').write_text('\n'.join(lines),encoding='utf-8')
    return provenance


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True)
    p.add_argument('--out-dir',default='results/phase7_historical')
    p.add_argument('--run-id',required=True)
    p.add_argument('--replicates',type=int,default=2000)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--ml-rank-cap',type=int,default=40)
    args=p.parse_args()
    summary=reanalyse(args.archive,args.out_dir,run_id=args.run_id,replicates=args.replicates,
                      seed=args.seed,ml_rank_cap=args.ml_rank_cap)
    print(json.dumps({'case_count':summary['case_count'],'cohorts':summary['cohorts'],
                      'output_dir':args.out_dir,'scope':summary['scope']},indent=2))

if __name__=='__main__':main()