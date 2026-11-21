"""Tests are deliberately tiny invented rows; never reported as patient accuracy."""
import csv
import json
from pathlib import Path
import pytest
from src.phase7_experiments import (
    freeze, sha256, load_csv, read_cases, read_model_manifest, read_dataset_manifest,
    audit_rows, summarize, verify_legacy_summary, run_audit,
)


def csv_file(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


@pytest.fixture
def inputs(tmp_path):
    cases = [
        {'case_id':'SYN-A','disease_id':'MIM:1','hpo_ids':'HP:0001250;HP:0001263','cohort':'toyA'},
        {'case_id':'SYN-B','disease_id':'MIM:2','hpo_ids':'HP:0001250','cohort':'toyA'},
        {'case_id':'SYN-C','disease_id':'MIM:3','hpo_ids':'HP:0001263','cohort':'toyB'},
    ]
    casefile=tmp_path/'cases.csv';csv_file(casefile,cases)
    dataset=tmp_path/'rarebench_manifest.json';dataset.write_text(json.dumps({
        'dataset':'chenxz/RareBench','archive_sha256':'a'*64,
        'eligible_total':3,'sha256':sha256(casefile),
    }))
    model_file=tmp_path/'model.joblib';model_file.write_bytes(b'toy_model_byte_fixture_not_a_real_model')
    model=tmp_path/'model.manifest.json';model.write_text(json.dumps({
        'artifact_sha256':sha256(model_file),'profile_sha256':'b'*64,
        'source':{'kind':'hpo_sqlite_v2_aspect_P'},
    }))
    plan=freeze(casefile,dataset,model,['overlap','xgboost'],model_path=model_file,seed=42)
    plan_file=tmp_path/'plan.json';plan_file.write_text(json.dumps(plan))
    results=[]
    placements={('SYN-A','overlap'):1,('SYN-A','xgboost'):2,
                ('SYN-B','overlap'):None,('SYN-B','xgboost'):1,
                ('SYN-C','overlap'):3,('SYN-C','xgboost'):None}
    for c in cases:
        for method in ('overlap','xgboost'):
            rank=placements[(c['case_id'],method)]
            results.append({'case_id':c['case_id'],'cohort':c['cohort'],
                            'method':method,'true_disease_id':c['disease_id'],
                            'known_disease':int(c['case_id']!='SYN-B'),
                            'rank':rank or '', 'top1':int(rank==1),
                            'top5':int(rank is not None and rank<=5),
                            'reciprocal_rank':1/rank if rank else 0})
    raw=tmp_path/'results.csv';csv_file(raw,results)
    # Echo the legacy generated summary from the verified raw case rows.
    bykey=audit_rows(load_csv(raw,set(results[0])),read_cases(casefile),plan)
    old=[]
    for cohort in ('ALL','toyA','toyB'):
        for method in ('overlap','xgboost'):
            subset=[r for (cid,m),r in bykey.items() if m==method and (cohort=='ALL' or r['cohort']==cohort)]
            n=len(subset)
            old.append({'cohort':cohort,'method':method,'n':n,
                        'top1':sum(r['top1'] for r in subset)/n,
                        'top5':sum(r['top5'] for r in subset)/n,
                        'mrr':sum(r['mrr'] for r in subset)/n,
                        'disease_coverage':sum(r['known_disease'] for r in subset)/n,
                        'candidate_recall':sum(r['candidate_recall'] for r in subset)/n})
    summary=tmp_path/'legacy.csv';csv_file(summary,old)
    return {'cases':casefile,'dataset_manifest':dataset,'model_manifest':model,
            'model':model_file,'plan':plan_file,'results':raw,'summary':summary,
            'out':tmp_path/'audit','rows':results,'plan_data':plan}


def audit(a, **overrides):
    kw=dict(cases_path=a['cases'],results_path=a['results'],
            legacy_summary_path=a['summary'],plan_path=a['plan'],
            dataset_manifest_path=a['dataset_manifest'],model_manifest_path=a['model_manifest'],
            model_path=a['model'],out_dir=a['out'],replicates=120)
    kw.update(overrides)
    return run_audit(**kw)


def test_full_audit_real_metric_computation_only_from_given_fixture(inputs):
    a=inputs;result=audit(a)
    assert result['case_count']==3
    assert result['methods']==['overlap','xgboost']
    assert len(result['output_csv_sha256'])==4
    paired=list(csv.DictReader((a['out']/'phase7_paired_effects.csv').open()))
    p=next(r for r in paired if r['cohort']=='ALL' and r['method']=='xgboost' and r['metric']=='top1')
    assert p['n']=='3'
    assert float(p['difference']) == 0 # 1 success in each model; opposite cases
    errors=list(csv.DictReader((a['out']/'phase7_error_analysis.csv').open()))
    assert any(r['error_category']=='truth_not_in_returned_ranked_list' for r in errors)
    assert any(r['error_category']=='truth_outside_model_disease_universe' for r in errors)


def test_seeded_repetitions_identical_outputs(inputs):
    a=inputs;audit(a)
    first=(a['out']/'phase7_paired_effects.csv').read_bytes()
    audit(a)
    assert first==(a['out']/'phase7_paired_effects.csv').read_bytes()


def test_missing_case_method_is_rejected(inputs):
    a=inputs;csv_file(a['results'],a['rows'][:-1])
    with pytest.raises(ValueError,match='Incomplete paired'):
        audit(a)


def test_duplicate_case_method_is_rejected(inputs):
    a=inputs;csv_file(a['results'],a['rows']+[a['rows'][0]])
    with pytest.raises(ValueError,match='duplicate case/method'):
        audit(a)


def test_ground_truth_and_metric_fabrication_rejected(inputs):
    a=inputs;a['rows'][0]['top1']=0
    csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='Rank / metric mismatch'):
        audit(a)


def test_case_input_tampering_fails_frozen_plan(inputs):
    a=inputs;a['cases'].write_text(a['cases'].read_text().replace('MIM:1','MIM:0'))
    with pytest.raises(ValueError,match='CSV SHA-256'):
        audit(a)


def test_model_manifest_tampering_fails(inputs):
    a=inputs;a['model_manifest'].write_text(a['model_manifest'].read_text().replace('b'*64,'c'*64))
    with pytest.raises(ValueError,match='Frozen plan'):
        audit(a)


def test_comparison_summary_must_equal_raw_cases(inputs):
    a=inputs;legacy=list(csv.DictReader(a['summary'].open()))
    legacy[0]['top1']='0.99';csv_file(a['summary'],legacy)
    with pytest.raises(ValueError,match='Legacy summary top1'):
        audit(a)


def test_mixed_case_cohort_is_rejected(inputs):
    a=inputs;a['rows'][0]['cohort']='toyB';csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='Cohort or ground truth'):
        audit(a)


def test_empty_and_duplicate_source_cases_rejected(inputs):
    a=inputs;data=list(csv.DictReader(a['cases'].open()))
    data.append(data[0].copy());csv_file(a['cases'],data)
    with pytest.raises(ValueError,match='Duplicate case ID'):
        read_cases(a['cases'])


def test_invalid_true_rank_or_reciprocal_rejected(inputs):
    a=inputs;a['rows'][1]['rank']='-1';csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='Malformed rank'):
        audit(a)


def test_freeze_enforces_prior_source_hash_and_comparison_scope(inputs):
    a=inputs
    with pytest.raises(ValueError,match='DeepRare'):
        freeze(a['cases'],a['dataset_manifest'],a['model_manifest'],['overlap','DeepRare_external'])
    with pytest.raises(ValueError,match='duplicate'):
        freeze(a['cases'],a['dataset_manifest'],a['model_manifest'],['overlap','overlap'])


def test_bootstrap_constraints_are_enforced(inputs):
    a=inputs
    with pytest.raises(ValueError,match='100 to 100000'):
        audit(a,replicates=8)


def test_model_bytes_must_agree_with_manifest(inputs):
    a=inputs;a['model'].write_bytes(b'fake_tampered_model')
    with pytest.raises(ValueError,match='Model bytes'):
        audit(a)


def test_case_coverage_consistent_across_methods(inputs):
    a=inputs;a['rows'][0]['known_disease']=0;csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='Conflicting disease-coverage'):
        audit(a)
