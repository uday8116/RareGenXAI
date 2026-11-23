import test from 'node:test';
import assert from 'node:assert/strict';
import { api, ApiError } from '../src/api.js';
import { rankingCsv, rankingJson, downloadRanking } from '../src/report-export.js';
import { BENCHMARK, BENCHMARK_CASES, BENCHMARK_SOURCE } from '../src/research.js';

const example = {
  method: 'xgboost',
  model_sha256: 'a'.repeat(64),
  explanation_type: 'matched_terms_and_feature_values',
  results: [{
    disease_id: 'MIM:00001',
    disease_name: '=HYPERLINK("example","bad")',
    score: -0.125,
    matched_hpo: ['HP:0001250'],
    retrieval_similarity: 0.45,
  }],
};

test('CSV/JSON exports keep evidence, numeric scores, provenance and formula safety', () => {
  const csv = rankingCsv(example);
  assert.match(csv, /'=\s*HYPERLINK|'\=HYPERLINK/);
  assert.ok(csv.includes('"-0.125"'));
  assert.ok(csv.includes('HP:0001250'));
  assert.ok(!csv.includes('"=HYPERLINK'));
  const json = JSON.parse(rankingJson(example));
  assert.equal(json.model_sha256, 'a'.repeat(64));
  assert.equal(json.results[0].score, -0.125);
  assert.match(json.warning, /not calibrated/);
  assert.equal(rankingCsv({...example, results: []}).trim().split('\r\n').length, 1);
  assert.throws(() => downloadRanking(example, 'html'), /Invalid local research report/);
});

test('historical benchmark is clearly sourced and not a live count', () => {
  assert.equal(BENCHMARK_CASES, 178);
  assert.equal(BENCHMARK.length, 6);
  assert.ok(BENCHMARK_SOURCE.includes('/actions/runs/'));
  const overlap = BENCHMARK.find((m) => m.id === 'overlap');
  assert.equal(overlap.top1, 37.64);
  assert.equal(overlap.top5, 54.49);
});

test('API sends only structured HPO JSON to the same-origin local proxy', async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({url, options});
    return {ok:true, status:200, json:async()=>({method:'overlap',results:[]})};
  };
  try {
    const controller = new AbortController();
    await api.rank({
      method:'overlap', observations:[{hpo_id:'HP:0001250',status:'confirmed_present'}],
    }, controller.signal);
    await api.phenotypes('seizure & delay');
    assert.equal(calls[0].url, '/api/v1/rank');
    assert.equal(calls[0].options.method, 'POST');
    assert.equal(calls[0].options.credentials, 'omit');
    assert.equal(calls[0].options.cache, 'no-store');
    assert.ok(calls[0].options.signal);
    assert.equal(calls[0].options.signal.aborted, false);
    const posted = JSON.parse(calls[0].options.body);
    assert.deepEqual(posted.observations, [{hpo_id:'HP:0001250',status:'confirmed_present'}]);
    assert.ok(calls[1].url.includes('seizure%20%26%20delay'));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('API forwards caller cancellation to its internal fetch signal', async () => {
  const originalFetch = globalThis.fetch;
  let receivedSignal;
  globalThis.fetch = async (_url, options) => new Promise((_resolve, reject) => {
    receivedSignal = options.signal;
    options.signal.addEventListener('abort', () => {
      const error = new Error('Aborted');
      error.name = 'AbortError';
      reject(error);
    }, {once:true});
  });
  try {
    const controller = new AbortController();
    const promise = api.rank({
      method:'overlap', observations:[{hpo_id:'HP:0001250', status:'confirmed_present'}],
    }, controller.signal);
    controller.abort();
    await assert.rejects(promise, (e) => e instanceof ApiError
      && e.message.includes('Request cancelled or timed out'));
    assert.equal(receivedSignal.aborted, true);
  } finally { globalThis.fetch = originalFetch; }
});

test('API reports typed validation failure rather than inventing results', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok:false, status:422, json:async()=>({detail:[{msg:'Unsupported clinical HPO value'}]}),
  });
  try {
    await assert.rejects(api.rank({}), (e) => e instanceof ApiError
      && e.status === 422 && e.message.includes('Unsupported clinical HPO'));
  } finally { globalThis.fetch = originalFetch; }
});

test('API connection failure remains visible to users', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('ECONNREFUSED'); };
  try {
    await assert.rejects(api.ready(), (e) => e instanceof ApiError
      && e.message.includes('Cannot reach the local FastAPI backend'));
  } finally { globalThis.fetch = originalFetch; }
});
