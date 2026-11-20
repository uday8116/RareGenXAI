import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MAX_COMPARE_METHODS, toApiObservations, rankPayload, evidenceGroups,
  compareMethods, ablationChoices, dropObservation, describeAblation,
} from '../src/xai.js';

const obs = [
  { hpo_id:'HP:0001250', name:'Seizure', status:'confirmed_present' },
  { hpo_id:'HP:0001263', name:'Developmental delay', status:'suspected_present' },
  { hpo_id:'HP:0001290', name:'Low tone', status:'confirmed_absent' },
  { hpo_id:'HP:0000118', name:'Unknown sign', status:'unknown' },
];
const settings = { quality:true, top_k:5, candidates:40 };

test('Phase 6 case inputs contain HPO IDs/status only, with bounded options', () => {
  assert.equal(MAX_COMPARE_METHODS, 4);
  assert.deepEqual(toApiObservations(obs)[0], {
    hpo_id:'HP:0001250', status:'confirmed_present',
  });
  assert.equal(toApiObservations(obs)[0].name, undefined);
  const request = rankPayload(obs, {...settings, top_k:1000, candidates:500}, 'semantic');
  assert.equal(request.top_k, 20);
  assert.equal(request.candidates, 100);
  assert.equal(request.method, 'semantic');
  assert.equal(request.observations.length, 4);
});

test('signed baseline evidence remains auditable and separates negative evidence', () => {
  const explained = {
    method:'overlap', explanation_type:'signed_ontology_contributions',
    reconstructed_baseline_score:0.25,
    evidence:[
      {hpo_id:'HP:0001250', status:'confirmed_present', match:1, contribution:0.5, relation:'exact'},
      {hpo_id:'HP:0001290', status:'confirmed_absent', match:1, contribution:-0.25, relation:'exact'},
    ],
  };
  const groups = evidenceGroups(explained, obs);
  assert.equal(groups.baseline, true);
  assert.equal(groups.net, 0.25);
  assert.equal(groups.validScore, true);
  assert.equal(groups.support, 0.5);
  assert.equal(groups.opposition, -0.25);
  assert.equal(groups.items[0].label, 'Seizure');
  assert.equal(groups.items[1].role, 'contradicting');
});

test('ML evidence is context only; no fake SHAP score decomposition', () => {
  const groups = evidenceGroups({
    explanation_type:'ontology_context_not_ml_attribution',
    evidence:[{hpo_id:'HP:0001250', status:'confirmed_present', relation:'exact', match:1, contribution:null}],
  }, obs);
  assert.equal(groups.baseline, false);
  assert.equal(groups.support, null);
  assert.equal(groups.net, null);
  assert.equal(groups.items[0].role, 'annotated');
  assert.equal(evidenceGroups(null, obs), null);
});

test('same-case model agreement counts leaders, not diagnostic accuracy', () => {
  const reports = [
    {method:'overlap',results:[{disease_id:'MIM:1',disease_name:'A',score:1}]},
    {method:'semantic',results:[{disease_id:'MIM:1',disease_name:'A',score:0.7}]},
    {method:'xgboost',results:[{disease_id:'MIM:2',disease_name:'B',score:0.8}],model_sha256:'abc'},
  ];
  const group = compareMethods(reports);
  assert.equal(group.agreementCount, 2);
  assert.equal(group.consensusId, 'MIM:1');
  assert.equal(group.allAgree, false);
  assert.equal(group.rows[2].model_sha256, 'abc');
  assert.equal(compareMethods([]), null);
});

test('a missing predicted result is never fabricated as a zero score', () => {
  const info = compareMethods([
    {method:'overlap',results:[]},
    {method:'semantic',results:[]},
  ]);
  assert.equal(info.consensusId, null);
  assert.equal(info.agreementCount, 0);
});

test('leave-one-out keeps at least one positive and allows removing absent evidence', () => {
  const choices = ablationChoices(obs).map((row) => row.hpo_id);
  assert.deepEqual(choices, ['HP:0001250', 'HP:0001263', 'HP:0001290']);
  assert.equal(dropObservation(obs, 'HP:0001250').length, 3);
  assert.equal(dropObservation([{hpo_id:'HP:0001250',status:'confirmed_present'},
    {hpo_id:'HP:0001290',status:'confirmed_absent'}], 'HP:0001290').length, 1);
  assert.throws(() => dropObservation([{hpo_id:'HP:0001250',status:'confirmed_present'}],
    'HP:0001250'), /last present or suspected/);
  assert.throws(() => dropObservation(obs, 'HP:0000118'), /last present or suspected/);
});

test('sensitivity correctly reports same-method rank shifts, not risk', () => {
  const original = {method:'overlap',results:[{disease_id:'MIM:1',disease_name:'A',score:0.8}]};
  const after = {method:'overlap',results:[
    {disease_id:'MIM:2',disease_name:'B',score:0.7},
    {disease_id:'MIM:1',disease_name:'A',score:0.2},
  ]};
  const info = describeAblation(original, after, 'HP:0001250');
  assert.equal(info.changedLeader, true);
  assert.equal(info.originalLeaderRankAfter, 2);
  assert.ok(Math.abs(info.rawScoreChange + 0.6) < 1e-9);
  assert.throws(() => describeAblation(original, {method:'xgboost',results:[]}, 'HP:0001250'), /same ranking method/);
});

test('missing original leader in truncated rerank stays unknown', () => {
  const original = {method:'semantic',results:[{disease_id:'MIM:1',score:0.5}]};
  const after = {method:'semantic',results:[{disease_id:'MIM:2',score:0.9}]};
  const info = describeAblation(original, after, 'HP:0001250');
  assert.equal(info.originalLeaderRankAfter, null);
  assert.equal(info.rawScoreChange, null);
});
