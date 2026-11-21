"""Tests are deliberately tiny invented rows; never reported as patient accuracy."""
import csv
import json
from pathlib import Path
import pytest
from src.phase7_experiments import (
    freeze, sha256, load_csv, read_cases, read_model_manifest, read_dataset_manifest,
    audit_rows, summarize, verify_legacy_summary, run_audit,
    verify_plan_for_inference, verify_known_disease_membership, require_trained_models,
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
        'disease_universe':4,
        'source':{'kind':'hpo_sqlite_v2_aspect_P'},
        'training':{'train_disease_ids':['MIM:1'], 'heldout_disease_ids':['MIM:3']},
    }))
    plan=freeze(casefile,dataset,model,['overlap','xgboost'],model_path=model_file,seed=42)
    plan_file=tmp_path/'plan.json';plan_file.write_text(json.dumps(plan))
    results=[]
    placements={('SYN-A','overlap'):1,('SYN-A','xgboost'):2,
                ('SYN-B','overlap'):None,('SYN-B','xgboost'):None,
                ('SYN-C','overlap'):3,('SYN-C','xgboost'):None}
    for c in cases:
        for method in ('overlap','xgboost'):
            rank=placements[(c['case_id'],method)]
            results.append({'case_id':c['case_id'],'cohort':c['cohort'],
                            'method':method,'true_disease_id':c['disease_id'],
                            'known_disease':int(c['case_id']!='SYN-B'),
                            'rank':rank or '', 'top1':int(rank==1),
                            'top5':int(rank is not None and rank<=5),
                            'reciprocal_rank':1/rank if rank else 0,'retrieval_k':40})
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
    assert len(result['output_csv_sha256'])==5
    paired=list(csv.DictReader((a['out']/'phase7_paired_effects.csv').open()))
    p=next(r for r in paired if r['cohort']=='ALL' and r['method']=='xgboost' and r['metric']=='top1')
    assert p['n']=='3'
    assert abs(float(p['difference']) + 1/3) < 1e-12  # No fabricated hit for unknown disease
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


def test_changed_retrieval_limit_is_rejected(inputs):
    a=inputs;a['rows'][0]['retrieval_k']=25;csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='Retrieval candidate limit'):
        audit(a)


def test_candidate_universe_coverage_gets_cohort_uncertainty(inputs):
    a=inputs;audit(a)
    rows=list(csv.DictReader((a['out']/'phase7_cohort_metrics.csv').open()))
    coverage=[r for r in rows if r['cohort']=='ALL' and r['method']=='overlap' and r['metric']=='disease_coverage']
    assert len(coverage)==1
    assert abs(float(coverage[0]['estimate'])-2/3)<1e-9
    paired=list(csv.DictReader((a['out']/'phase7_paired_effects.csv').open()))
    assert all(row['metric']!='disease_coverage' for row in paired)


def test_preregister_requires_a_baseline(inputs):
    a=inputs
    with pytest.raises(ValueError,match='requires overlap'):
        freeze(a['cases'],a['dataset_manifest'],a['model_manifest'],['xgboost'])


def test_frozen_cohort_composition_must_match_case_file(inputs):
    a=inputs;plan=a['plan_data'];plan['cohorts']={'toyA':3}
    a['plan'].write_text(json.dumps(plan))
    with pytest.raises(ValueError,match='cohort composition'):
        audit(a)


def test_modified_plan_with_duplicated_methods_is_rejected(inputs):
    a=inputs;plan=a['plan_data'];plan['methods']=['overlap','overlap']
    a['plan'].write_text(json.dumps(plan))
    with pytest.raises(ValueError,match='duplicated'):
        audit(a)


def test_disease_overlap_with_synthetic_training_is_reported_not_confused_with_patient_leakage(inputs):
    a=inputs;audit(a)
    rows=list(csv.DictReader((a['out']/'phase7_synthetic_training_overlap.csv').open()))
    group={r['split_membership']:int(r['count']) for r in rows if r['cohort']=='ALL'}
    assert group=={'synthetic_training_disease':1,'synthetic_heldout_disease':1,
                   'outside_model_disease_universe':1}


def test_invalid_training_heldout_manifest_overlap_is_rejected(inputs):
    a=inputs
    model=json.loads(a['model_manifest'].read_text())
    model['training']['heldout_disease_ids']=['MIM:1']
    a['model_manifest'].write_text(json.dumps(model))
    with pytest.raises(ValueError,match='Frozen plan'):
        audit(a)


def test_unknown_disease_cannot_be_reported_as_ranked(inputs):
    a=inputs
    row=next(r for r in a['rows'] if r['case_id']=='SYN-B' and r['method']=='xgboost')
    row.update(rank=1, top1=1, top5=1, reciprocal_rank=1)
    csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='Ranked a disease marked outside'):
        audit(a)


def test_ml_rank_cannot_exceed_frozen_retrieval_limit(inputs):
    a=inputs
    row=next(r for r in a['rows'] if r['case_id']=='SYN-A' and r['method']=='xgboost')
    row.update(rank=41, top1=0, top5=0, reciprocal_rank=1/41)
    csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='exceeds frozen ML'):
        audit(a)


def test_baseline_rank_cannot_exceed_model_universe(inputs):
    a=inputs
    row=next(r for r in a['rows'] if r['case_id']=='SYN-C' and r['method']=='overlap')
    row.update(rank=5, top1=0, top5=1, reciprocal_rank=1/5)
    csv_file(a['results'],a['rows'])
    with pytest.raises(ValueError,match='exceeds the verified model disease universe'):
        audit(a)


def test_model_universe_size_cannot_change_after_freeze(inputs):
    a=inputs
    manifest=json.loads(a['model_manifest'].read_text())
    manifest['disease_universe']=400
    a['model_manifest'].write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='Frozen plan'):
        audit(a)


def test_frozen_plan_must_match_inputs_before_prediction(inputs):
    a=inputs
    result=verify_plan_for_inference(
        a['plan'], cases_path=a['cases'], model_path=a['model'],
        methods=['overlap','xgboost'], retrieval_k=40, max_cases=0,
    )
    assert result['case_count']==3
    assert result['methods']==['overlap','xgboost']


@pytest.mark.parametrize('overrides', [
    {'methods':['xgboost','overlap']},
    {'retrieval_k':25},
    {'max_cases':2},
    {'deeprare':'fake_output.csv'},
])
def test_frozen_plan_blocks_changed_inference_arguments(inputs, overrides):
    a=inputs
    args=dict(cases_path=a['cases'],model_path=a['model'],
              methods=['overlap','xgboost'],retrieval_k=40,max_cases=0)
    args.update(overrides)
    with pytest.raises(ValueError,match='frozen Phase 7|DeepRare'):
        verify_plan_for_inference(a['plan'],**args)


def test_frozen_plan_blocks_changed_model_even_before_inference(inputs):
    a=inputs;a['model'].write_bytes(b'tampered and invalid')
    with pytest.raises(ValueError,match='Model bytes'):
        verify_plan_for_inference(a['plan'],cases_path=a['cases'],
            model_path=a['model'],methods=['overlap','xgboost'],retrieval_k=40)


def test_frozen_plan_blocks_changed_case_file_even_before_inference(inputs):
    a=inputs
    a['cases'].write_text(a['cases'].read_text().replace('SYN-A','SYN-Z'))
    with pytest.raises(ValueError,match='Published case file'):
        verify_plan_for_inference(a['plan'],cases_path=a['cases'],
            model_path=a['model'],methods=['overlap','xgboost'],retrieval_k=40)


def test_model_profile_membership_verification_reads_real_candidate_identifiers(inputs):
    a=inputs
    bykey=audit_rows(load_csv(a['results'],set(a['rows'][0])),read_cases(a['cases']),a['plan_data'])
    size=verify_known_disease_membership(bykey,read_cases(a['cases']),a['plan_data'],
                                         {'MIM:1','MIM:3','MIM:4','MIM:5'})
    assert size==4


def test_false_case_coverage_is_rejected_against_verified_candidate_ids(inputs):
    a=inputs
    for row in a['rows']:
        if row['case_id']=='SYN-B':
            row['known_disease']=1
    csv_file(a['results'],a['rows'])
    bykey=audit_rows(load_csv(a['results'],set(a['rows'][0])),read_cases(a['cases']),a['plan_data'])
    with pytest.raises(ValueError,match='disagrees with verified model profiles'):
        verify_known_disease_membership(
            bykey,read_cases(a['cases']),a['plan_data'],
            {'MIM:1','MIM:3','MIM:4','MIM:5'},
        )


def test_verified_candidate_count_must_match_frozen_universe(inputs):
    a=inputs
    bykey=audit_rows(load_csv(a['results'],set(a['rows'][0])),read_cases(a['cases']),a['plan_data'])
    with pytest.raises(ValueError,match='disease-universe size'):
        verify_known_disease_membership(bykey,read_cases(a['cases']),a['plan_data'],{'MIM:1','MIM:3'})


def test_strict_membership_mode_refuses_missing_trusted_model_path(inputs):
    a=inputs
    with pytest.raises(ValueError,match='requires --model'):
        audit(a,verify_model_membership=True,model_path=None)


def test_generated_research_report_contains_only_audited_metrics_and_source_hashes(inputs):
    a=inputs
    result=audit(a)
    path=a['out']/'phase7_research_report.md'
    assert path.is_file()
    report=path.read_text(encoding='utf-8')
    assert "RareGenXAI" in report
    assert "Retrospective" in report
    assert "Top-1" in report and "Known disease coverage" in report
    assert "xgboost" in report and "toyA" in report
    assert "No genuine matched-case DeepRare" in report
    assert a['plan_data']['model_artifact_sha256'] in report
    assert result['research_report_sha256']==sha256(path)
    assert 'SYN-A' not in report  # Aggregated report excludes case-level records


def test_report_deterministic_across_identical_observations(inputs):
    a=inputs
    audit(a)
    report=(a['out']/'phase7_research_report.md').read_bytes()
    audit(a)
    assert report==(a['out']/'phase7_research_report.md').read_bytes()


def test_missing_preregistered_trained_model_fails_before_scoring():
    with pytest.raises(ValueError, match="xgboost"):
        require_trained_models(
            ["tfidf", "logistic", "xgboost", "mlp", "overlap"],
            {"logistic": object(), "mlp": object()},
        )


def test_all_available_preregistered_methods_pass_preflight():
    assert require_trained_models(
        ["tfidf", "logistic", "random_forest", "xgboost", "mlp", "overlap"],
        {"logistic": object(), "random_forest": object(),
         "xgboost": object(), "mlp": object()},
    ) is None
