import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App.jsx';

const rankFixture = {
  method: 'overlap',
  requested_count: 2,
  model_sha256: null,
  explanation_type: 'per_phenotype_score_contributions',
  results: [{
    disease_id: 'MIM:1234',
    disease_name: 'Synthetic example syndrome',
    score: 0.75,
    matched_hpo: ['HP:0001250'],
    evidence: [{
      hpo_id: 'HP:0001250',
      status: 'confirmed_present',
      match: 1,
      contribution: 0.75,
    }],
  }],
  disclaimer: 'Research candidate ranking; scores are not calibrated disease probabilities.',
};
const ready = {ready:true,knowledge_schema:'2',disease_count:12867,phenotype_count:19000,model_status:'available'};
const methods = {status:'available',methods:['overlap','semantic','tfidf','logistic','random_forest','xgboost','mlp'],
  model_sha256:'a'.repeat(64),profile_sha256:'b'.repeat(64),manifest_schema:2};
const stats = {schema_version:'2',counts:{diseases:12867,hpo_terms:19000,disease_phenotypes:205000},sources:[]};

function mockJson(data, ok = true, status = 200) {
  return {ok,status,json:async()=>data};
}
function apiMock() {
  return vi.fn(async (url, options = {}) => {
    if (url === '/api/v1/ready') return mockJson(ready);
    if (url === '/api/v1/models') return mockJson(methods);
    if (url === '/api/v1/knowledge/stats') return mockJson(stats);
    if (url.startsWith('/api/v1/phenotypes/search?')) {
      return mockJson([{hpo_id:'HP:0001250',name:'Seizure',is_obsolete:0}]);
    }
    if (url.startsWith('/api/v1/diseases/search?')) {
      return mockJson([{disease_id:'MIM:1234',name:'Synthetic example syndrome'}]);
    }
    if (url === '/api/v1/diseases/MIM%3A1234') return mockJson({
      disease_id:'MIM:1234',name:'Synthetic example syndrome',
      phenotypes:[{hpo_id:'HP:0001250',hpo_name:'Seizure',is_negated:0,reference_id:'PMID:123',aspect:'P'}],
    });
    if (url === '/api/v1/explain') {
      const requested = JSON.parse(options.body);
      return mockJson({
        method: requested.method, disease_id: requested.disease_id,
        disease_name:'Synthetic example syndrome',
        explanation_type: requested.method === 'overlap' || requested.method === 'semantic'
          ? 'signed_ontology_contributions' : 'ontology_context_not_ml_attribution',
        model_sha256: requested.method === 'overlap' || requested.method === 'semantic' ? null : 'a'.repeat(64),
        reconstructed_baseline_score: requested.method === 'overlap' || requested.method === 'semantic' ? 0.75 : null,
        evidence: [
          {hpo_id:'HP:0001250',status:'confirmed_present',relation:'exact',
           best_disease_hpo_id:'HP:0001250',shared_ancestor_hpo_id:null,
           match:1,evidence_weight:1,contribution: requested.method === 'overlap' || requested.method === 'semantic' ? 0.75 : null},
          {hpo_id:'HP:0001263',status:'suspected_present',relation:'none',
           best_disease_hpo_id:null,shared_ancestor_hpo_id:null,
           match:0,evidence_weight:0.4,contribution: requested.method === 'overlap' || requested.method === 'semantic' ? 0 : null},
        ],
        disclaimer:'Research-only; not a diagnosis, probability or SHAP attribution.',
      });
    }
    if (url === '/api/v1/rank') {
      const payload = JSON.parse(options.body);
      if (payload.observations.length === 1) {
        return mockJson({...rankFixture, method:payload.method, results:[{
          disease_id:'MIM:5678', disease_name:'Different hypothetical disorder', score:0.55,
          matched_hpo:['HP:0001263'],evidence:[],
        }]});
      }
      return mockJson({...rankFixture,method:payload.method});
    }
    throw new Error('Unexpected endpoint: ' + url + ' ' + String(options?.method));
  });
}
function mount(path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><App/></MemoryRouter>);
}

beforeEach(() => vi.stubGlobal('fetch', apiMock()));

describe('Phase 5 website', () => {
  it('shows real backend status, live database statistics and research warning', async () => {
    mount('/');
    expect(await screen.findByText('12,867')).toBeInTheDocument();
    expect(screen.getByText('Rare diseases.')).toBeInTheDocument();
    expect(screen.getAllByText(/research demonstration only/i).length).toBeGreaterThan(0);
    expect(screen.getByRole('link',{name:'Phenotype workbench'})).toBeInTheDocument();
  });

  it('clears previously live HPO counts after the local API disconnects', async () => {
    const user = userEvent.setup();
    const normal = apiMock();
    let readyCalls = 0;
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
      if (url === '/api/v1/ready' && ++readyCalls > 1) {
        throw new Error('Backend disconnected');
      }
      return normal(url, options);
    }));
    mount('/');
    expect(await screen.findByText('12,867')).toBeInTheDocument();
    await user.click(screen.getByRole('button',{name:'Refresh backend status'}));
    await screen.findByText(/local API unavailable/i);
    expect(screen.queryByText('12,867')).not.toBeInTheDocument();
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('does not invent patient ranking results when the backend is offline', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('Connection refused'); }));
    mount('/workbench');
    expect(await screen.findByText(/cannot reach the local FastAPI backend/i)).toBeInTheDocument();
    expect(screen.getByText(/your analysis starts here/i)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/run disease prioritization/i})).toBeDisabled();
    expect(screen.queryByText('Synthetic example syndrome')).not.toBeInTheDocument();
  });

  it('validates HPO input, calls the real rank API and renders evidence (not probabilities)', async () => {
    const user = userEvent.setup();
    const fetchMock = apiMock();
    vi.stubGlobal('fetch', fetchMock);
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    expect(screen.getByText('Seizure')).toBeInTheDocument();
    expect(screen.getByText('Global developmental delay')).toBeInTheDocument();
    await user.click(screen.getByRole('button',{name:/run disease prioritization/i}));
    expect(await screen.findByText('Synthetic example syndrome')).toBeInTheDocument();
    expect(screen.getAllByText('0.7500').length).toBeGreaterThan(0);
    expect(screen.getByText(/not a probability/i)).toBeInTheDocument();
    expect(screen.getByText('Per-phenotype score contributions')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Export ranking as CSV'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Export ranking as JSON'})).toBeInTheDocument();
    const rankCall = fetchMock.mock.calls.find(([url]) => url === '/api/v1/rank');
    expect(rankCall).toBeTruthy();
    expect(rankCall[1].method).toBe('POST');
    expect(rankCall[1].credentials).toBe('omit');
    expect(JSON.parse(rankCall[1].body)).toEqual({
      method:'overlap',top_k:5,candidates:40,quality:true,
      observations:[
        {hpo_id:'HP:0001250',status:'confirmed_present'},
        {hpo_id:'HP:0001263',status:'suspected_present'},
      ],
    });
  });

  it('renders Phase 6 ontology trace from the actual explain API response', async () => {
    const user = userEvent.setup();
    const fetchMock = apiMock();
    vi.stubGlobal('fetch', fetchMock);
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    await user.click(screen.getByRole('button',{name:/run disease prioritization/i}));
    expect(await screen.findByRole('heading',{name:'Explainability laboratory'})).toBeInTheDocument();
    expect(await screen.findByText('Signed baseline evidence')).toBeInTheDocument();
    expect(screen.getByText(/nearest disease annotation: HP:0001250/i)).toBeInTheDocument();
    expect(screen.getByText(/consistent with baseline score/i)).toBeInTheDocument();
    const explainCall = fetchMock.mock.calls.find(([url]) => url === '/api/v1/explain');
    expect(JSON.parse(explainCall[1].body).disease_id).toBe('MIM:1234');
    expect(explainCall[1].credentials).toBe('omit');
  });

  it('never displays evidence from a mismatched explanation candidate or method', async () => {
    const user = userEvent.setup();
    const normal = apiMock();
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
      if (url === '/api/v1/explain') return mockJson({
        method:'semantic', disease_id:'MIM:9999',
        explanation_type:'signed_ontology_contributions', model_sha256:null,
        reconstructed_baseline_score:0.75,
        evidence:[{hpo_id:'HP:0001250',status:'confirmed_present',match:1,contribution:0.75}],
      });
      return normal(url, options);
    }));
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    await user.click(screen.getByRole('button',{name:/run disease prioritization/i}));
    expect(await screen.findByText(/returned explanation does not match the selected candidate/i)).toBeInTheDocument();
    expect(screen.queryByText('Signed baseline evidence')).not.toBeInTheDocument();
  });

  it('hides evidence when source contributions do not reproduce the original score', async () => {
    const user = userEvent.setup();
    const normal = apiMock();
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
      if (url === '/api/v1/explain') return mockJson({
        method:'overlap', disease_id:'MIM:1234',
        explanation_type:'signed_ontology_contributions', model_sha256:null,
        reconstructed_baseline_score:0.25,
        evidence:[{hpo_id:'HP:0001250',status:'confirmed_present',match:1,contribution:0.25}],
      });
      return normal(url, options);
    }));
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    await user.click(screen.getByRole('button',{name:/run disease prioritization/i}));
    expect(await screen.findByText(/evidence contributions do not reproduce the ranked baseline score/i)).toBeInTheDocument();
    expect(screen.queryByText('Signed baseline evidence')).not.toBeInTheDocument();
  });

  it('compares two actual same-case method responses without reporting accuracy', async () => {
    const user = userEvent.setup();
    const fetchMock = apiMock();
    vi.stubGlobal('fetch', fetchMock);
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    await user.click(screen.getByRole('button',{name:/run disease prioritization/i}));
    await screen.findByRole('heading',{name:'Explainability laboratory'});
    await user.click(screen.getByRole('tab',{name:/same-case model comparison/i}));
    await user.click(screen.getByRole('button',{name:/compare methods on these HPO findings/i}));
    expect(await screen.findByText(/methods share a leading candidate/i)).toBeInTheDocument();
    expect(screen.getByText(/top-candidate agreement/i)).toBeInTheDocument();
    const runs = fetchMock.mock.calls.filter(([url])=>url === '/api/v1/rank')
      .map(([_url,opts])=>JSON.parse(opts.body));
    expect(runs.length).toBeGreaterThanOrEqual(3);
    const compared = runs.slice(1);
    expect(compared.map((r)=>r.method)).toEqual(['overlap','semantic']);
    expect(compared[0].observations).toEqual(compared[1].observations);
  });

  it('runs bounded sensitivity after omitting one HPO phenotype', async () => {
    const user = userEvent.setup();
    const fetchMock = apiMock();
    vi.stubGlobal('fetch', fetchMock);
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    await user.click(screen.getByRole('button',{name:/run disease prioritization/i}));
    await screen.findByRole('heading',{name:'Explainability laboratory'});
    await user.click(screen.getByRole('tab',{name:/what-if sensitivity/i}));
    await user.click(screen.getByRole('button',{name:/rerun without selected phenotype/i}));
    expect(await screen.findByText('Different hypothetical disorder')).toBeInTheDocument();
    expect(screen.getByText(/outside returned top 20/i)).toBeInTheDocument();
    const rerun = fetchMock.mock.calls.filter(([url])=>url === '/api/v1/rank').at(-1);
    const body = JSON.parse(rerun[1].body);
    expect(body.observations).toEqual([{hpo_id:'HP:0001263',status:'suspected_present'}]);
    expect(body.top_k).toBe(20);
  });

  it('requires at least one present or suspected phenotype before submission', async () => {
    const user = userEvent.setup();
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    await user.selectOptions(screen.getByRole('combobox',{name:/evidence status for seizure/i}), 'confirmed_absent');
    await user.selectOptions(screen.getByRole('combobox',{name:/evidence status for global developmental delay/i}), 'unknown');
    expect(screen.getByText(/at least one phenotype must be present or suspected present/i)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/run disease prioritization/i})).toBeDisabled();
  });

  it('supports live HPO autocomplete and avoids duplicate observation additions', async () => {
    const user = userEvent.setup();
    mount('/workbench');
    await screen.findByText('API connected');
    await user.type(screen.getByRole('combobox',{name:/add clinical phenotype/i}), 'Seizure');
    const option = await screen.findByRole('option',{name:/seizure/i}, {timeout:2500});
    await user.click(option);
    expect(screen.getByText('Seizure')).toBeInTheDocument();
    expect(screen.getByText('1 / 20')).toBeInTheDocument();
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    expect(screen.getByText('2 / 20')).toBeInTheDocument();
  });

  it('allows keyboard-only selection from an HPO search dropdown', async () => {
    const user = userEvent.setup();
    mount('/workbench');
    await screen.findByText('API connected');
    const picker = screen.getByRole('combobox',{name:/add clinical phenotype/i});
    await user.type(picker, 'seizure');
    await screen.findByRole('option',{name:/seizure/i}, {timeout:2500});
    await user.keyboard('{ArrowDown}{Enter}');
    expect(screen.getByText('Seizure')).toBeInTheDocument();
    expect(screen.getByText('1 / 20')).toBeInTheDocument();
  });

  it('ignores a delayed ranking response after observations or method change', async () => {
    const user = userEvent.setup();
    const normal = apiMock();
    let completeRanking;
    const waitingRanking = new Promise((resolve) => { completeRanking = resolve; });
    const pendingFetch = vi.fn(async (url, options) => {
      if (url === '/api/v1/rank') return waitingRanking;
      return normal(url, options);
    });
    vi.stubGlobal('fetch', pendingFetch);
    mount('/workbench');
    await screen.findByText('API connected');
    await user.click(screen.getByRole('button',{name:/load example HPO terms/i}));
    await user.click(screen.getByRole('button',{name:/run disease prioritization/i}));
    await waitFor(() => expect(pendingFetch.mock.calls.some(([url]) => url === '/api/v1/rank')).toBe(true));
    const rankCall = pendingFetch.mock.calls.find(([url]) => url === '/api/v1/rank');
    expect(rankCall[1].signal.aborted).toBe(false);
    await user.selectOptions(screen.getByRole('combobox',{name:'Ranking method'}), 'semantic');
    expect(rankCall[1].signal.aborted).toBe(true);
    await act(async () => { completeRanking(mockJson(rankFixture)); });
    expect(screen.queryByText('Synthetic example syndrome')).not.toBeInTheDocument();
    expect(screen.getByText(/your analysis starts here/i)).toBeInTheDocument();
  });

  it('loads disease annotations on demand rather than making up a disease profile', async () => {
    const user = userEvent.setup();
    mount('/explorer');
    await screen.findByText('API connected');
    await user.type(screen.getByRole('textbox',{name:/search disease knowledge/i}), 'Syndrome');
    const match = await screen.findByRole('button',{name:/synthetic example syndrome/i}, {timeout:2500});
    await user.click(match);
    const panel = await screen.findByText('Associated HPO annotations');
    expect(panel).toBeInTheDocument();
    expect(screen.getByText('PMID:123', {exact:false})).toBeInTheDocument();
  });

  it('shows research experiments with referenced evidence and unresolved work', async () => {
    mount('/experiments');
    expect(screen.getByText('Experiments & validation')).toBeInTheDocument();
    expect(screen.getByText('Eligible published cases')).toBeInTheDocument();
    expect(screen.getByText('Held-out synthetic diseases')).toBeInTheDocument();
    expect(screen.getByText('Identical-case DeepRare prediction comparison')).toBeInTheDocument();
    expect(screen.getByRole('link',{name:/view external evaluation/i})).toHaveAttribute('href',
      'https://github.com/uday8116/RareGenXAI/actions/runs/44484831306');
  });

  it('keeps the model dashboard explicitly historical and links its evidence', async () => {
    const user = userEvent.setup();
    mount('/models');
    await screen.findByText('Available');
    expect(screen.getByText(/published RareBench evaluation/i)).toBeInTheDocument();
    expect(screen.getByText(/not a live result/i)).toBeInTheDocument();
    expect(screen.getAllByText('37.64%').length).toBeGreaterThan(0);
    await user.click(screen.getByRole('button',{name:'Top-5'}));
    expect(screen.getByText('54.49%')).toBeInTheDocument();
    expect(screen.getByRole('link',{name:/view original measured run/i})).toHaveAttribute('href',
      'https://github.com/uday8116/RareGenXAI/actions/runs/44484831306');
  });
});
