"""Only invented SYN fixtures; no archived patient record is embedded in tests."""
import csv
import io
import json
import zipfile
import pytest
from src.phase7_historical_reaudit import reanalyse, sha, NEEDED


def csvbytes(rows):
    file=io.StringIO(newline='')
    writer=csv.DictWriter(file,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
    return file.getvalue().encode('utf-8')


@pytest.fixture
def archive(tmp_path):
    cases=(('SYN-A','SYN-D1','toyA',1),('SYN-B','SYN-D2','toyB',0))
    rows=[]
    for c,d,co,known in cases:
        for m in ('overlap','xgboost'):
            pos=1 if c=='SYN-A' and m=='overlap' else 2 if c=='SYN-A' else None
            rows.append(dict(case_id=c,cohort=co,method=m,true_disease_id=d,
                known_disease=known,rank=pos or '',top1=int(pos==1),
                top5=int(pos is not None and pos<=5),reciprocal_rank=1/pos if pos else 0))
    sums=[]
    for co in ('ALL','toyA','toyB'):
        for m in ('overlap','xgboost'):
            x=[r for r in rows if r['method']==m and (co=='ALL' or r['cohort']==co)]
            n=len(x)
            sums.append(dict(cohort=co,method=m,n=n,
                top1=sum(int(r['top1']) for r in x)/n,
                top5=sum(int(r['top5']) for r in x)/n,
                mrr=sum(float(r['reciprocal_rank']) for r in x)/n,
                disease_coverage=sum(int(r['known_disease']) for r in x)/n,
                candidate_recall=sum(bool(r['rank']) for r in x)/n))
    data={
        NEEDED[0]:json.dumps(dict(dataset='chenxz/RareBench',eligible_total=2,
                                   sha256='a'*64)).encode(),
        NEEDED[1]:json.dumps(dict(source={'kind':'hpo_sqlite_v2_aspect_P'},
                                   disease_universe=4,artifact_sha256='b'*64,
                                   training={'train_disease_ids':['SYN-D1'],'heldout_disease_ids':[]})).encode(),
        NEEDED[2]:csvbytes(rows),
        NEEDED[3]:csvbytes(sums),
    }
    def save(data):
        p=tmp_path/'historical.zip'
        with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,body in data.items():z.writestr(name,body)
        return p
    return data,save,tmp_path


def test_valid_historical_archive_recalculates_all_tables_and_report(archive):
    data,save,tmp=archive
    p=save(data)
    audited=reanalyse(p,tmp/'out',run_id=123,replicates=120)
    assert audited['case_count']==2
    assert audited['cohorts']=={'toyA':1,'toyB':1}
    assert audited['scope'].startswith('HISTORICAL ARCHIVED')
    assert len(audited['output_csv_sha256'])==4
    report=(tmp/'out'/'historical_report.md').read_text()
    assert 'NOT a new Phase 7 inference run' in report
    assert 'DeepRare' in report
    assert 'SYN-A' not in report
    assert audited['archived_files_sha256'][NEEDED[2]]==sha(data[NEEDED[2]])


def test_reanalysis_is_repeatable_for_identical_archive_and_seed(archive):
    data,save,tmp=archive
    p=save(data)
    reanalyse(p,tmp/'out',run_id=123,replicates=120,seed=42)
    original=(tmp/'out'/'historical_paired_effects.csv').read_bytes()
    reanalyse(p,tmp/'out',run_id=123,replicates=120,seed=42)
    assert original==(tmp/'out'/'historical_paired_effects.csv').read_bytes()


def test_fabricated_top1_flag_rejected(archive):
    data,save,tmp=archive
    r=list(csv.DictReader(io.StringIO(data[NEEDED[2]].decode())))
    r[0]['top1']='0' if r[0]['top1']=='1' else '1'
    data[NEEDED[2]]=csvbytes(r)
    with pytest.raises(ValueError,match='Fabricated'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=120)


def test_duplicate_case_method_rejected(archive):
    data,save,tmp=archive
    r=list(csv.DictReader(io.StringIO(data[NEEDED[2]].decode())))
    data[NEEDED[2]]=csvbytes(r+[r[0]])
    with pytest.raises(ValueError,match='Duplicate record'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=120)


def test_missing_case_method_rejected(archive):
    data,save,tmp=archive
    r=list(csv.DictReader(io.StringIO(data[NEEDED[2]].decode())))
    data[NEEDED[2]]=csvbytes(r[:-1])
    with pytest.raises(ValueError,match='Incomplete case-method'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=120)


def test_changed_published_summary_rejected(archive):
    data,save,tmp=archive
    s=list(csv.DictReader(io.StringIO(data[NEEDED[3]].decode())))
    s[0]['top1']='0.8'
    data[NEEDED[3]]=csvbytes(s)
    with pytest.raises(ValueError,match='does not match cases'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=120)


def test_ranked_disease_outside_knowledge_rejected(archive):
    data,save,tmp=archive
    r=list(csv.DictReader(io.StringIO(data[NEEDED[2]].decode())))
    r[-1].update(rank='1',top1='1',top5='1',reciprocal_rank='1')
    data[NEEDED[2]]=csvbytes(r)
    with pytest.raises(ValueError,match='Unknown disease assigned a rank'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=120)


def test_incorrect_model_provenance_rejected(archive):
    data,save,tmp=archive
    model=json.loads(data[NEEDED[1]])
    model['source']['kind']='legacy-all-aspects'
    data[NEEDED[1]]=json.dumps(model).encode()
    with pytest.raises(ValueError,match='phenotype-only'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=120)


def test_missing_artifact_entry_rejected(archive):
    data,save,tmp=archive
    del data[NEEDED[3]]
    with pytest.raises(ValueError,match='Missing original archived'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=120)


def test_invalid_bootstrap_replicates_rejected(archive):
    data,save,tmp=archive
    with pytest.raises(ValueError,match='Bootstrap replicate'):
        reanalyse(save(data),tmp/'out',run_id=123,replicates=4)
