import { describe, expect, it } from 'vitest';
import { rankingCsv, rankingJson, EXPORT_DISCLAIMER } from '../report-export.js';

const fixture = {
  method: 'xgboost',
  model_sha256: 'a'.repeat(64),
  explanation_type: 'matched_terms_and_feature_values',
  results: [{
    disease_id: 'MIM:1234',
    disease_name: '=HYPERLINK("http://unsafe.example","click")',
    score: 0.81,
    matched_hpo: ['HP:0001250', 'HP:0001263'],
    retrieval_similarity: 0.76,
    features: { tfidf_similarity: 0.76 },
  }],
};

describe('Research export safety and reproducibility', () => {
  it('exports existing returned model rankings without patient identifiers', () => {
    const csv = rankingCsv(fixture);
    expect(csv).toContain('"xgboost"');
    expect(csv).toContain('"MIM:1234"');
    expect(csv).toContain('"HP:0001250;HP:0001263"');
    expect(csv).toContain('not calibrated disease probabilities');
    expect(csv).not.toContain('patient_name');
    expect(csv).not.toContain('hospital_id');
  });

  it('neutralizes potentially dangerous spreadsheet formulas', () => {
    const csv = rankingCsv(fixture);
    expect(csv).toContain("'=HYPERLINK");
    expect(csv).toContain('""http://unsafe.example""');
    expect(csv).not.toContain('"=HYPERLINK');
  });

  it('preserves original model evidence and source fingerprint in JSON', () => {
    const exported = JSON.parse(rankingJson(fixture));
    expect(exported.kind).toBe('ranked_disease_candidates_not_diagnosis');
    expect(exported.warning).toBe(EXPORT_DISCLAIMER);
    expect(exported.model_sha256).toBe('a'.repeat(64));
    expect(exported.results[0].features.tfidf_similarity).toBe(0.76);
  });

  it('supports valid empty candidate lists without making up results', () => {
    const noMatch = { ...fixture, results: [] };
    expect(rankingCsv(noMatch).split('\r\n').filter(Boolean)).toHaveLength(1);
    expect(JSON.parse(rankingJson(noMatch)).results).toEqual([]);
  });
});
