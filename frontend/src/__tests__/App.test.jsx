import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
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
    if (url === '/api/v1/rank') return mockJson(rankFixture);
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
    expect(screen.getByText('0.7500')).toBeInTheDocument();
    expect(screen.getByText(/not a probability/i)).toBeInTheDocument();
    expect(screen.getByText('Per-phenotype score contributions')).toBeInTheDocument();
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
