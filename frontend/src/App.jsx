import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity, ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, BrainCircuit,
  Check, ChevronDown, ChevronRight, CircleAlert, ClipboardList, Compass, Download,
  Database, Dna, ExternalLink, FileText, FlaskConical, GitBranch, HeartPulse,
  Info, Layers, LoaderCircle, Menu, Microscope, Network, Plus, RefreshCw,
  Search, ShieldCheck, SlidersHorizontal, Sparkles, Stethoscope, Trash2, X,
} from 'lucide-react';
import { api } from './api.js';
import ExplanationLab from './components/ExplanationLab.jsx';
import { downloadRanking } from './report-export.js';
import {
  BENCHMARK, BENCHMARK_CASES, BENCHMARK_SOURCE, EVIDENCE_STATUS,
  LIMITS, METHOD_LABELS, SAMPLE_PHENOTYPES,
} from './research.js';

const NAV = [
  { path: '/', label: 'Overview', icon: Layers },
  { path: '/workbench', label: 'Phenotype workbench', icon: Dna },
  { path: '/explorer', label: 'Disease explorer', icon: Search },
  { path: '/models', label: 'Model laboratory', icon: BrainCircuit },
  { path: '/experiments', label: 'Experiments', icon: FlaskConical },
  { path: '/documentation', label: 'Documentation', icon: BookOpen },
];

function formatNumber(value) {
  return typeof value === 'number' ? value.toLocaleString('en-US') : '—';
}
function displayScore(score) {
  const n = Number(score);
  return Number.isFinite(n) ? n.toFixed(4) : '—';
}
function Badge({ children, tone = 'muted' }) {
  return <span className={'badge badge-' + tone}>{children}</span>;
}
function SectionIntro({ eyebrow, title, description, children }) {
  return <div className="section-heading"><div><div className="eyebrow">{eyebrow}</div>
    <h1>{title}</h1><p>{description}</p></div>{children}</div>;
}
function EmptyState({ icon: Icon = Search, title, description, children }) {
  return <div className="empty-state" role="status"><div className="empty-icon"><Icon size={25} /></div>
    <h3>{title}</h3><p>{description}</p>{children}</div>;
}
function Alert({ children, tone = 'warning' }) {
  return <div role="alert" className={'alert alert-' + tone}><CircleAlert size={18} aria-hidden="true" /><span>{children}</span></div>;
}
function Panel({ title, subtitle, action, children, className = '' }) {
  return <section className={'panel ' + className}>
    {(title || subtitle || action) && <header className="panel-header"><div>
      {title && <h2>{title}</h2>}{subtitle && <p>{subtitle}</p>}
    </div>{action}</header>}
    <div className="panel-content">{children}</div></section>;
}
function Spinner({ label = 'Loading' }) {
  return <span className="spinner-label"><LoaderCircle size={16} className="spin" aria-hidden="true" /> {label}</span>;
}
function ResearchWarning({ compact = false }) {
  return <div className={'research-warning' + (compact ? ' compact' : '')}>
    <ShieldCheck size={19} aria-hidden="true" />
    <span><strong>Research demonstration only.</strong> Candidate scores are ranking signals, not disease probabilities or clinical diagnoses. Do not enter personal patient information.</span>
  </div>;
}

function useBackend() {
  const [status, setStatus] = useState({ state: 'checking', ready: null, models: null, error: '' });
  const refresh = useCallback(async () => {
    setStatus((old) => ({ ...old, state: 'checking', error: '' }));
    try {
      const ready = await api.ready();
      const models = await api.models();
      setStatus({ state: 'online', ready, models, error: '' });
    } catch (err) {
      setStatus({ state: 'offline', ready: null, models: null, error: err.message });
    }
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  return { ...status, refresh };
}

function ConnectionStatus({ backend, compact = false }) {
  const online = backend.state === 'online';
  return <div className={'connection ' + (online ? 'connected' : backend.state === 'checking' ? 'connecting' : 'disconnected')} title={backend.error || 'Connection to locally running FastAPI backend'}>
    <span className="connection-dot" />
    {!compact && <span>{online ? 'API connected' : backend.state === 'checking' ? 'Checking API' : 'API offline'}</span>}
  </div>;
}

function Sidebar({ backend, close }) {
  return <aside className="sidebar">
    <div className="brand"><div className="brand-mark"><Dna size={26} /></div><div><strong>RareGen<span>XAI</span></strong><small>RESEARCH INTELLIGENCE</small></div></div>
    <div className="sidebar-label">WORKSPACE</div>
    <nav aria-label="Primary navigation" className="sidebar-nav">
      {NAV.map(({ path, label, icon: Icon }) => <NavLink onClick={close} key={path} end={path === '/'} to={path}
        className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}><Icon size={19} /><span>{label}</span><ChevronRight size={15} className="nav-caret" /></NavLink>)}
    </nav>
    <div className="sidebar-spacer" />
    <div className="sidebar-research">
      <span className="mini-orb"><FlaskConical size={18} /></span>
      <strong>Built for discovery</strong>
      <p>Exploring rare disorder candidates through clinical phenotype knowledge.</p>
      <Badge tone="teal">LOCAL · RESEARCH</Badge>
    </div>
    <div className="sidebar-bottom"><ConnectionStatus backend={backend} /><span>v0.5 · Academic prototype</span></div>
  </aside>;
}

function DashboardLayout({ backend, children }) {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);
  const current = NAV.find((x) => x.path === location.pathname) || NAV[0];
  return <div className="app-shell">
    {menuOpen && <button className="sidebar-overlay" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
    <div className={'sidebar-frame' + (menuOpen ? ' show' : '')}><Sidebar backend={backend} close={() => setMenuOpen(false)} /></div>
    <div className="app-content">
      <header className="topbar">
        <div className="topbar-left"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMenuOpen(true)}><Menu size={22} /></button>
          <span className="breadcrumb">Workspace</span><ChevronRight size={15} className="dim"/><strong>{current.label}</strong></div>
        <div className="topbar-actions"><ConnectionStatus backend={backend} compact /><span className="topbar-divider" />
          <button className="refresh-button" onClick={backend.refresh} aria-label="Refresh backend status" disabled={backend.state === 'checking'}>
            <RefreshCw size={17} className={backend.state === 'checking' ? 'spin' : ''} /> <span>Refresh status</span>
          </button></div>
      </header>
      <main className="main-content" id="main-content">{children}</main>
      <footer className="footer"><span>RareGenXAI · Explainable phenotype intelligence</span><span>Academic research prototype · Local only</span></footer>
    </div>
  </div>;
}

function Metric({ icon: Icon, label, value, detail, accent = '' }) {
  return <div className={'metric-card ' + accent}><div className="metric-heading"><div className="metric-icon"><Icon size={20}/></div><span className="metric-arrow"><ArrowUpRight size={18}/></span></div>
    <div className="metric-value">{value}</div><div className="metric-name">{label}</div><p>{detail}</p></div>;
}

function Overview({ backend }) {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState('');
  useEffect(() => {
    if (backend.state !== 'online') {
      setStats(null);
      setStatsError('');
      return;
    }
    let live = true;
    api.stats().then((data) => { if (live) { setStats(data); setStatsError(''); } })
      .catch((err) => { if (live) setStatsError(err.message); });
    return () => { live = false; };
  }, [backend.state, backend.ready]);
  const count = stats?.counts || {};
  const trained = backend.models?.status === 'available';
  return <>
    <div className="hero"><div className="hero-decoration hero-decoration-one"/><div className="hero-decoration hero-decoration-two"/>
      <div className="hero-text"><div className="hero-label"><Sparkles size={14}/> INTELLIGENT PHENOTYPE EXPLORATION</div>
        <h1>Rare diseases.<br/><em>Clearer evidence.</em></h1>
        <p>Explore Human Phenotype Ontology knowledge, prioritize candidate rare disorders, and understand the evidence behind each research ranking.</p>
        <div className="hero-actions"><button className="button primary" onClick={() => navigate('/workbench')}>Start phenotype analysis <ArrowRight size={18}/></button>
          <button className="button ghost-light" onClick={() => navigate('/explorer')}>Explore diseases <Compass size={18}/></button></div>
        <div className="hero-footnote"><span className="tiny-green-dot"/> Privacy-first · Local execution · Explainable results</div></div>
      <div className="hero-art" aria-hidden="true"><div className="art-ring ring-a"/><div className="art-ring ring-b"/><div className="art-ring ring-c"/>
        <div className="art-center"><Dna size={72} strokeWidth={1.15}/></div><div className="art-node node-a"/><div className="art-node node-b"/><div className="art-node node-c"/><div className="art-node node-d"/></div>
    </div>
    {backend.state === 'offline' && <Alert>Local API unavailable: {backend.error} The dashboard shows only explicitly labeled historical research figures until the backend starts.</Alert>}
    <div className="metrics-grid">
      <Metric icon={Database} label="Annotated diseases" value={formatNumber(count.diseases)} detail={stats ? 'Live from the local HPO database' : 'Available when the API is connected'} accent="accent-teal"/>
      <Metric icon={Network} label="HPO ontology terms" value={formatNumber(count.hpo_terms)} detail={stats ? 'Live ontology term count' : 'Read from Phase 2 knowledge source'}/>
      <Metric icon={BrainCircuit} label="ML model availability" value={trained ? 'Ready' : 'Unavailable'} detail={trained ? 'Verified trained model bundle loaded' : 'Baseline methods work without saved ML weights'}/>
      <Metric icon={ClipboardList} label="Published benchmark cases" value="178" detail="Historical RareBench evaluation, not live clinical data"/>
    </div>
    {statsError && <Alert>{statsError}</Alert>}
    <div className="overview-columns">
      <Panel title="Your research workflow" subtitle="From observed phenotypes to transparent candidate rankings" className="workflow-panel">
        <div className="workflow-list">
          {[{ no:'01', icon:Search, title:'Select clinical phenotypes', text:'Search official HPO terminology and mark observed evidence.' },
            { no:'02', icon:SlidersHorizontal, title:'Choose a ranking method', text:'Compare knowledge baselines with verified trained rerankers.' },
            { no:'03', icon:Activity, title:'Review the evidence', text:'Inspect matched terms, contributions, and model input features.' }].map(({no,icon:Icon,title,text}) =>
            <div className="workflow-step" key={no}><div className="workflow-number">{no}</div><div className="workflow-icon"><Icon size={19}/></div>
              <div><strong>{title}</strong><p>{text}</p></div></div>)}
        </div>
        <button className="link-button" onClick={() => navigate('/workbench')}>Open workbench <ArrowRight size={17}/></button>
      </Panel>
      <Panel title="Research snapshot" subtitle="Published benchmark · 178 eligible cases" className="snapshot-panel"
        action={<Badge tone="muted">HISTORICAL</Badge>}>
        <div className="snapshot-metric"><span>Best reported Top-1</span><strong>37.64%</strong></div>
        <div className="snapshot-bar"><div style={{ width:'37.64%' }}/></div>
        <div className="snapshot-metric"><span>Exact overlap · reported Top-5</span><strong>54.49%</strong></div>
        <div className="snapshot-bar alt"><div style={{ width:'54.49%' }}/></div>
        <p className="snapshot-note">Exact HPO overlap and XGBoost tied on reported Top-1; this does not establish diagnostic accuracy.</p>
        <a href={BENCHMARK_SOURCE} target="_blank" rel="noreferrer" className="source-link">View measured workflow <ExternalLink size={15}/></a>
        <button className="link-button" onClick={() => navigate('/models')}>Compare all models <ArrowRight size={17}/></button>
      </Panel>
    </div>
    <ResearchWarning />
  </>;
}

function PhenotypePicker({ observations, setObservations, disabled }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [state, setState] = useState('idle');
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const [validation, setValidation] = useState('');
  const [activeOption, setActiveOption] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (query.trim().length < 2 || disabled) { setResults([]); setState('idle'); return; }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setState('loading');
      api.phenotypes(query.trim(), controller.signal).then((rows) => {
        setResults(rows.filter((r) => !r.is_obsolete));
        setActiveOption(0);
        setState('done');
        setError('');
      }).catch((err) => {
        if (!controller.signal.aborted) { setState('error'); setError(err.message); }
      });
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, disabled]);

  function add(phenotype) {
    if (observations.some((o) => o.hpo_id === phenotype.hpo_id)) {
      setValidation('This phenotype is already in your observations.'); return;
    }
    if (observations.length >= LIMITS.maxObservations) {
      setValidation('The API accepts up to 20 observations per analysis.'); return;
    }
    setObservations((items) => [...items, { ...phenotype, status:'confirmed_present' }]);
    setQuery(''); setResults([]); setValidation(''); setOpen(false);
  }
  function sample() {
    setObservations((items) => {
      const ids = new Set(items.map((x) => x.hpo_id));
      return [...items, ...SAMPLE_PHENOTYPES.filter((x) => !ids.has(x.hpo_id))].slice(0, LIMITS.maxObservations);
    });
    setValidation('');
  }
  return <div>
    <label htmlFor="phenotype-search" className="form-label">Add clinical phenotype</label>
    <div className="search-field"><Search size={19} aria-hidden="true"/><input id="phenotype-search" ref={inputRef}
      autoComplete="off" value={query} disabled={disabled} placeholder="Search seizures, developmental delay, HP:0001250..."
      onChange={(e) => { setQuery(e.target.value); setOpen(true); setActiveOption(0); setValidation(''); }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') { setOpen(false); return; }
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault();
          setOpen(true);
          if (results.length > 0) {
            setActiveOption((i) => (i + (e.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length);
          }
          return;
        }
        if (e.key === 'Enter' && open && query.trim().length >= 2) {
          e.preventDefault();
          if (state === 'done' && results.length > 0) add(results[activeOption]);
        }
      }}
      onFocus={() => setOpen(true)} aria-expanded={open && query.length >= 2}
      aria-autocomplete="list"
      aria-activedescendant={open && state === 'done' && results[activeOption] ? 'hpo-option-' + results[activeOption].hpo_id : undefined}
      aria-controls="phenotype-options" role="combobox" />
      {query && <button type="button" aria-label="Clear phenotype search" onClick={() => { setQuery(''); setResults([]); inputRef.current?.focus(); }}><X size={16}/></button>}
    </div>
    {open && query.trim().length >= 2 && !disabled && <div className="search-popover" id="phenotype-options" role="listbox">
      {state === 'loading' && <div className="search-feedback"><Spinner label="Searching HPO terms"/></div>}
      {state === 'error' && <div className="search-feedback">{error}</div>}
      {state === 'done' && results.length === 0 && <div className="search-feedback">No matching active HPO terms found.</div>}
      {state === 'done' && results.map((term, i) => <button id={'hpo-option-' + term.hpo_id} className={'search-option' + (i === activeOption ? ' selected' : '')}
        role="option" aria-selected={i === activeOption} key={term.hpo_id} type="button" onMouseEnter={() => setActiveOption(i)} onClick={() => add(term)}>
        <span><strong>{term.name}</strong><small>{term.hpo_id}</small></span><Plus size={17}/></button>)}
    </div>}
    <div className="field-hint"><span>Use official Human Phenotype Ontology terminology.</span>
      <button type="button" className="subtle-button" onClick={sample}>Load example HPO terms <Plus size={13}/></button></div>
    {validation && <div className="field-error" role="alert">{validation}</div>}
    <div className="selected-heading"><span>Observations <b>{observations.length} / {LIMITS.maxObservations}</b></span>
      {observations.length > 0 && <button className="subtle-button danger-text" onClick={() => setObservations([])}><Trash2 size={14}/> Clear all</button>}</div>
    {observations.length === 0 ? <div className="observations-empty">No phenotypes added. Search above or load the educational example.</div> :
      <div className="observations" aria-label="Selected HPO observations">{observations.map((o) => <div key={o.hpo_id} className="observation-item">
        <div className="observation-token"><div className="phenotype-symbol"><Dna size={15}/></div><div><strong>{o.name}</strong><small>{o.hpo_id}</small></div></div>
        <div className="observation-controls"><select aria-label={'Evidence status for ' + o.name} value={o.status} onChange={(e) => setObservations((items) => items.map((x) => x.hpo_id === o.hpo_id ? { ...x,status:e.target.value } : x))}>
          {EVIDENCE_STATUS.map((x) => <option value={x.value} key={x.value}>{x.label}</option>)}
        </select><button type="button" aria-label={'Remove ' + o.name} onClick={() => setObservations((items) => items.filter((x) => x.hpo_id !== o.hpo_id))}><X size={18}/></button></div>
      </div>)}</div>}
  </div>;
}

function ResultCard({ disease, index, type, onExplore }) {
  const [open, setOpen] = useState(index === 0);
  const evidence = disease.evidence || [];
  return <article className="result-card">
    <div className="result-main"><div className="result-index">{String(index + 1).padStart(2,'0')}</div>
      <div className="result-description"><span className="result-identifier">{disease.disease_id}</span>
        <h3>{disease.disease_name}</h3><div className="result-badges"><Badge tone="teal">{(disease.matched_hpo || []).length} direct HPO matches</Badge>
          {typeof disease.retrieval_similarity === 'number' && <Badge>TF-IDF: {displayScore(disease.retrieval_similarity)}</Badge>}</div></div>
      <div className="result-score"><span>Ranking score</span><strong>{displayScore(disease.score)}</strong><small>Not a probability</small></div></div>
    <div className="result-actions"><button className="subtle-button" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? 'Hide' : 'View'} evidence <ChevronDown size={15} className={open ? 'rotate' : ''}/></button>
      <button className="subtle-button" onClick={() => onExplore(disease.disease_id)}>View disease details <ArrowRight size={15}/></button></div>
    {open && <div className="result-evidence"><div className="evidence-heading"><span>{type === 'per_phenotype_score_contributions' ? 'Per-phenotype score contributions' : 'Direct HPO evidence and reranker inputs'}</span><Badge tone="muted">EXPLAINABILITY</Badge></div>
      {evidence.length > 0 ? <div className="evidence-list">{evidence.map((e, i) => <div key={e.hpo_id + '-' + i} className="evidence-row">
        <span className="evidence-term">{e.hpo_id}<small>{e.status.replaceAll('_',' ')}</small></span>
        <div className="evidence-bar"><div style={{width:(Math.min(100,Math.max(0,(Number(e.match) || 0)*100)))+'%'}}/></div>
        <span className="evidence-value">{typeof e.contribution === 'number' ? displayScore(e.contribution) : typeof e.match === 'number' ? Math.round(e.match * 100)+'% match' : '—'}</span>
      </div>)}</div> : <p className="muted-text">This method returned no per-phenotype evidence records.</p>}
      {disease.features && <div className="features-grid">{Object.entries(disease.features).map(([key,value]) => <div className="feature" key={key}><small>{key.replaceAll('_',' ')}</small><strong>{displayScore(value)}</strong></div>)}</div>}
      {disease.features && <p className="fineprint">Feature values are inputs to the trained reranker, not SHAP values or causal explanations.</p>}
    </div>}
  </article>;
}

function Workbench({ backend }) {
  const navigate = useNavigate();
  const [observations, setObservations] = useState([]);
  const [method, setMethod] = useState('overlap');
  const [topK, setTopK] = useState(5);
  const [candidates, setCandidates] = useState(40);
  const [quality, setQuality] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [report, setReport] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const pendingRequest = useRef(null);
  useEffect(() => () => pendingRequest.current?.abort(), []);
  function invalidateAnalysis() {
    pendingRequest.current?.abort();
    pendingRequest.current = null;
    setLoading(false);
    setReport(null);
    setError('');
  }
  useEffect(() => {
    if (backend.state !== 'online') {
      pendingRequest.current?.abort();
      pendingRequest.current = null;
      setLoading(false);
      setReport(null);
    }
  }, [backend.state]);
  const available = backend.models?.methods || ['overlap','semantic'];
  const isOnline = backend.state === 'online';
  const valid = observations.length > 0 && observations.some((o) => o.status === 'confirmed_present' || o.status === 'suspected_present');
  const modelReady = ['overlap','semantic'].includes(method) || backend.models?.status === 'available';
  const canSubmit = isOnline && valid && modelReady && !loading;
  async function run(e) {
    e.preventDefault();
    if (!canSubmit) return;
    const controller = new AbortController();
    pendingRequest.current?.abort();
    pendingRequest.current = controller;
    setError(''); setReport(null); setLoading(true);
    try {
      const response = await api.rank({
        observations: observations.map(({hpo_id,status}) => ({hpo_id,status})),
        method, top_k:Number(topK), candidates:Number(candidates), quality,
      }, controller.signal);
      if (pendingRequest.current === controller) setReport(response);
    } catch (err) {
      if (pendingRequest.current === controller) setError(err.message);
    } finally {
      if (pendingRequest.current === controller) {
        pendingRequest.current = null;
        setLoading(false);
      }
    }
  }
  return <>
    <SectionIntro eyebrow="ANALYSIS / 01" title="Phenotype workbench" description="Build an observation set, select a ranking method, and explore evidence-backed rare disease candidates." />
    <div className="workbench-layout">
      <section className="panel workbench-controls"><div className="panel-header"><div><h2>Research input</h2><p>Enter HPO terms only; do not use patient identifiers.</p></div><Badge tone="teal">HPO</Badge></div>
        <form className="panel-content" onSubmit={run}>
          <PhenotypePicker observations={observations} setObservations={(fn) => {setObservations(fn);invalidateAnalysis();}} disabled={!isOnline}/>
          <div className="form-divider"/>
          <div className="form-row"><label htmlFor="rank-method" className="form-label">Ranking method</label>
            <select id="rank-method" value={method} onChange={(e) => { setMethod(e.target.value);invalidateAnalysis(); }}>
              {Object.entries(METHOD_LABELS).map(([id,label]) => <option key={id} value={id} disabled={!available.includes(id)}>{label}{!available.includes(id) ? ' · requires model' : ''}</option>)}
            </select></div>
          <div className="form-row"><label htmlFor="result-limit" className="form-label">Maximum results</label>
            <select id="result-limit" value={topK} onChange={(e) => { setTopK(Number(e.target.value)); invalidateAnalysis(); }}>{[3,5,10,20].map((n) => <option value={n} key={n}>Top {n}</option>)}</select></div>
          <button className="advanced-toggle" type="button" onClick={() => setShowAdvanced(!showAdvanced)} aria-expanded={showAdvanced}>
            <SlidersHorizontal size={16}/> Advanced options <ChevronDown size={15} className={showAdvanced ? 'rotate' : ''}/></button>
          {showAdvanced && <div className="advanced-fields"><label className="toggle-row"><span>Evidence weighting (baseline methods)</span><input type="checkbox" checked={quality} onChange={(e) => { setQuality(e.target.checked); invalidateAnalysis(); }}/></label>
            <label htmlFor="candidate-limit" className="form-label">TF-IDF candidate shortlist ({candidates})</label>
            <input id="candidate-limit" type="range" min="10" max="100" step="10" value={candidates} onChange={(e) => { setCandidates(Number(e.target.value)); invalidateAnalysis(); }}/></div>}
          {!valid && observations.length > 0 && <p className="field-error">At least one phenotype must be present or suspected present.</p>}
          {!isOnline && <Alert>{backend.state === 'checking'
            ? 'Checking the local FastAPI connection...'
            : (backend.error || 'Start FastAPI on 127.0.0.1:8000 to search HPO and run rankings.')}</Alert>}
          {!modelReady && <Alert>Selected ML method requires the verified Phase 3 model bundle.</Alert>}
          <button type="submit" className="button primary submit-button" disabled={!canSubmit}>{loading ? <Spinner label="Ranking candidates..."/> : <><Activity size={19}/> Run disease prioritization <ArrowRight size={18}/></>}</button>
          <p className="fineprint centered">Ranking only. No medical diagnosis, no patient history stored.</p>
        </form>
      </section>
      <section className="results-section" aria-live="polite"><div className="results-header"><div><div className="eyebrow">ANALYSIS OUTPUT</div><h2>Ranked candidates</h2><p>Results depend on the HPO snapshot and selected method.</p></div>
        {report && <Badge tone="teal">{report.results.length} results</Badge>}</div>
        {error && <Alert tone="error">{error}</Alert>}
        {loading && <div className="analysis-loader"><LoaderCircle className="spin" size={30}/><h3>Analyzing phenotype evidence</h3><p>Evaluating candidate disease profiles against the selected method.</p></div>}
        {!loading && report && report.results.length === 0 && <EmptyState icon={Info} title="No supported candidate match" description="The selected method found no candidate with positive supporting evidence. Try additional or more specific phenotypes." />}
        {!loading && report && report.results.length > 0 && <div className="results-list"><div className="results-meta"><Badge>{METHOD_LABELS[report.method] || report.method}</Badge>
          <span>{report.explanation_type === 'per_phenotype_score_contributions' ? 'Weighted HPO contributions' : 'Matched HPO terms & model feature values'}</span>
          <div className="export-actions">
            <button type="button" onClick={() => downloadRanking(report, 'csv')} aria-label="Export ranking as CSV"><Download size={15}/> CSV</button>
            <button type="button" onClick={() => downloadRanking(report, 'json')} aria-label="Export ranking as JSON"><Download size={15}/> JSON</button>
          </div></div>
          {report.results.map((d, i) => <ResultCard key={d.disease_id} disease={d} index={i} type={report.explanation_type}
            onExplore={(id) => navigate('/explorer?disease=' + encodeURIComponent(id))}/>)}
          <ExplanationLab report={report} observations={observations}
            options={{quality, top_k:topK, candidates}} availableMethods={available}/>
          <p className="fineprint">Exports are saved to your device only. Downloaded files include disease rankings and matched HPO IDs; treat research results as sensitive when sharing.</p>
          <ResearchWarning compact />
        </div>}
        {!loading && !report && <EmptyState icon={Microscope} title="Your analysis starts here" description="Add observed HPO phenotypes, select a method and run a local research analysis to view ranked disease candidates.">
          <div className="empty-tip"><Sparkles size={16}/> Tip: Try the built-in educational HPO example.</div>
        </EmptyState>}
      </section>
    </div>
  </>;
}

function Explorer({ backend }) {
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState([]);
  const [selected, setSelected] = useState(null);
  const [details, setDetails] = useState(null);
  const [searchError, setSearchError] = useState('');
  const [detailError, setDetailError] = useState('');
  const [searching, setSearching] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const isOnline = backend.state === 'online';
  const fromQuery = new URLSearchParams(location.search).get('disease');
  useEffect(() => { if (fromQuery) { setSelected(fromQuery); setQuery(fromQuery); } }, [fromQuery]);
  useEffect(() => {
    if (!isOnline || query.trim().length < 2) { setMatches([]); setSearching(false); return; }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setSearching(true);
      api.diseases(query.trim(), controller.signal).then((rows) => { setMatches(rows); setSearchError(''); })
        .catch((err) => { if (!controller.signal.aborted) setSearchError(err.message); })
        .finally(() => { if (!controller.signal.aborted) setSearching(false); });
    }, 320);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, isOnline]);
  useEffect(() => {
    if (!selected || !isOnline) { setDetails(null); return; }
    let active = true;
    setLoadingDetails(true); setDetailError(''); setDetails(null);
    api.disease(selected).then((data) => { if (active) setDetails(data); })
      .catch((err) => { if (active) { setDetails(null); setDetailError(err.message); } })
      .finally(() => { if (active) setLoadingDetails(false); });
    return () => { active = false; };
  }, [selected, isOnline]);
  return <>
    <SectionIntro eyebrow="KNOWLEDGE / 02" title="Disease explorer" description="Search the official local HPO disease-annotation knowledge base and inspect associated phenotype evidence."/>
    {!isOnline && <Alert>Connect your local API to explore disease annotations.</Alert>}
    <div className="explorer-layout">
      <Panel title="Find a rare disorder" subtitle="Search by disease name or known identifier.">
        <label htmlFor="disease-search" className="form-label">Search disease knowledge</label>
        <div className="search-field"><Search size={19}/><input id="disease-search" value={query} disabled={!isOnline} onChange={(e) => { setQuery(e.target.value); setMatches([]); setSearchError(''); }}
          placeholder="Search Marfan, ORPHA:..., MIM:..." autoComplete="off" /></div>
        {searching && <p className="small-status"><Spinner label="Searching diseases"/></p>}
        {searchError && <Alert tone="error">{searchError}</Alert>}
        <div className="disease-list">{matches.map((d) => <button key={d.disease_id} className={'disease-list-item' + (selected === d.disease_id ? ' selected' : '')} onClick={() => setSelected(d.disease_id)}>
          <span className="disease-list-icon"><Dna size={18}/></span><span><strong>{d.name}</strong><small>{d.disease_id}</small></span><ChevronRight size={16}/></button>)}
          {query.trim().length >= 2 && !searching && matches.length === 0 && !searchError && <p className="list-muted">No matching disorders found in this database snapshot.</p>}
          {query.trim().length < 2 && <div className="list-muted">Type at least two characters to search.</div>}</div>
      </Panel>
      <Panel title="Disease profile" subtitle={selected ? 'Evidence from the official HPO annotation source' : 'Select a disorder to inspect its annotations.'}>
        {loadingDetails && <div className="loading-details"><Spinner label="Loading disease profile"/></div>}
        {detailError && <Alert tone="error">{detailError}</Alert>}
        {!loadingDetails && !details && !detailError && <EmptyState icon={Database} title="Select a disease" description="The phenotype-annotation profile will appear here, including evidence, negation and reference fields."/>}
        {!loadingDetails && details && <div className="disease-detail">
          <div className="disease-detail-head"><Badge tone="teal">KNOWLEDGE PROFILE</Badge><h3>{details.name}</h3><p>{details.disease_id}</p></div>
          <div className="annotation-header"><h4>Associated HPO annotations</h4><span>{details.phenotypes.length} records</span></div>
          <div className="annotation-list">{details.phenotypes.slice(0,200).map((p, i) => <div key={p.hpo_id + '-' + i} className="annotation-row">
            <div><strong>{p.hpo_name}</strong><span>{p.hpo_id}{p.reference_id ? ' · ' + p.reference_id : ''}</span></div>
            <Badge tone={p.is_negated ? 'amber' : 'teal'}>{p.is_negated ? 'Negated' : 'Annotated'}</Badge></div>)}</div>
          {details.phenotypes.length > 200 && <p className="fineprint">Showing the first 200 annotations to keep this view responsive.</p>}
          <p className="fineprint">These are disease–phenotype knowledge annotations, not patient-specific findings.</p>
        </div>}
      </Panel>
    </div>
    <ResearchWarning compact/>
  </>;
}

function ModelLab({ backend }) {
  const [mode, setMode] = useState('top1');
  const model = backend.models;
  const ready = model?.status === 'available';
  return <>
    <SectionIntro eyebrow="RESEARCH / 03" title="Model laboratory" description="Inspect locally available ranking methods and compare results from one documented, historical research benchmark."/>
    <div className="lab-status-grid"><div className="lab-status-card"><div className="status-heading"><BrainCircuit size={20}/><span>Verified model bundle</span></div>
      <h2>{ready ? 'Available' : model?.status === 'incompatible' ? 'Incompatible' : 'Not loaded'}</h2>
      <p>{ready ? 'The local API has verified the Phase 3 saved model and its HPO snapshot.' : 'Connect and verify the saved model to enable supervised ranking methods.'}</p>
      {ready && <div className="fingerprint" title={model.model_sha256}><small>Model SHA-256</small><code>{model.model_sha256?.slice(0,20)}…</code></div>}</div>
      <div className="lab-status-card alt"><div className="status-heading"><Activity size={20}/><span>Active research methods</span></div>
        <h2>{model?.methods?.length || 0}<small> available</small></h2><p>{(model?.methods || ['overlap','semantic']).map((id) => METHOD_LABELS[id] || id).join(' · ')}</p></div></div>
    <Panel title="Historical model comparison" subtitle={'Published RareBench evaluation · '+BENCHMARK_CASES+' eligible cases · not a live result'}
      action={<div className="segmented-control" role="group" aria-label="Select ranking accuracy metric">
        <button className={mode === 'top1' ? 'selected' : ''} onClick={() => setMode('top1')} aria-pressed={mode === 'top1'}>Top-1</button>
        <button className={mode === 'top5' ? 'selected' : ''} onClick={() => setMode('top5')} aria-pressed={mode === 'top5'}>Top-5</button></div>}>
      <div className="benchmark-bars">{BENCHMARK.map((entry) => <div key={entry.id} className="benchmark-row">
        <div className="benchmark-title"><span>{entry.label}</span><small>{entry.kind}</small></div>
        <div className="benchmark-track"><div className={entry.id === 'overlap' ? 'benchmark-fill primary-fill' : 'benchmark-fill'} style={{width:entry[mode]+'%'}}/></div>
        <strong>{entry[mode].toFixed(2)}%</strong></div>)}</div>
      <div className="benchmark-footer"><div><Info size={17}/><span>These values come from a historical GitHub run, not the installed model or live patient performance. The exact-overlap baseline ranks a larger disease universe than the ML top-40 shortlist.</span></div>
        <a className="source-link" href={BENCHMARK_SOURCE} target="_blank" rel="noreferrer">View original measured run <ExternalLink size={15}/></a></div>
    </Panel>
    <div className="insight-grid">
      <Panel title="What the benchmark tells us" subtitle="Interpret results fairly"><p className="insight-copy">Exact HPO overlap achieved <strong>37.64% Top-1</strong> in this matched research cohort. XGBoost matched that Top-1 figure, but had lower Top-5 accuracy. More complex models did not consistently outperform the simple baseline.</p></Panel>
      <Panel title="What's not yet measured" subtitle="Scientific limitations"><p className="insight-copy">This dashboard is not a live evaluation server. It does not compute SHAP, calibrated probabilities, prospective patient accuracy or a genuine identical-case DeepRare benchmark. Those are separate research tasks.</p></Panel>
    </div>
    <ResearchWarning compact/>
  </>;
}

function Experiments() {
  const studies = [
    { number: '178', label: 'Eligible published cases', tag: 'External research cohort', desc: 'Matched-case published RareBench evaluation covering eligible LIRICAL, MME and HMS records.', href: BENCHMARK_SOURCE, link: 'View external evaluation' },
    { number: '120', label: 'Held-out synthetic diseases', tag: 'Training protocol', desc: 'Disease-disjoint synthetic HPO validation in the standard 600/120 Phase 3 training configuration. Not patient diagnostic accuracy.', href: 'https://github.com/uday8116/RareGenXAI/blob/main/docs/PHASE_03_REVIEW.md', link: 'Review training protocol' },
    { number: 'GNN', label: 'Experimental research extension', tag: 'Not in core model bundle', desc: 'An experimental ontology graph approach exists separately; do not compare its historical results as a newly reproduced matched model.', href: 'https://github.com/uday8116/RareGenXAI/blob/main/docs/GNN_FULL_BENCHMARK_RESULTS.md', link: 'View GNN experiment' },
  ];
  return <>
    <SectionIntro eyebrow="RESEARCH / 04" title="Experiments & validation" description="Trace what was actually evaluated, the evidence behind the figures, and the research work that remains." />
    <div className="experiments-grid">{studies.map((study) => <article className="experiment-card" key={study.label}>
      <Badge tone="teal">{study.tag}</Badge>
      <h2>{study.number}</h2><h3>{study.label}</h3><p>{study.desc}</p>
      <a className="source-link" href={study.href} target="_blank" rel="noreferrer">{study.link} <ExternalLink size={15}/></a>
    </article>)}</div>
    <div className="insight-grid">
      <Panel title="Research evaluation protocol" subtitle="Reproducible, non-clinical candidate prioritization">
        <div className="guardrails">
          {[
            ['Separate training and test context','Synthetic HPO-derived training data should not be described as real patient training data.'],
            ['Use one eligible external cohort','Top-k and Top-5 percentages need the exact 178-case evaluation reference, eligible-case criteria and source version.'],
            ['Disclose candidate retrieval','ML rerankers see a TF-IDF shortlist; the overlap baseline ranks the larger disease universe.'],
            ['Avoid overclaiming explainability','ML feature values are not SHAP explanations and rankings are not calibrated disease risks.'],
          ].map(([title,desc]) => <div className="guardrail" key={title}><Check size={17}/><div><strong>{title}</strong><p>{desc}</p></div></div>)}
        </div>
      </Panel>
      <Panel title="Open research questions" subtitle="Not complete in the current browser dashboard">
        <div className="research-gaps">
          <div><CircleAlert size={17}/><span>Independent prospective clinical validation</span><Badge>Not established</Badge></div>
          <div><CircleAlert size={17}/><span>Identical-case DeepRare prediction comparison</span><Badge>Not reproduced</Badge></div>
          <div><CircleAlert size={17}/><span>Calibrated disease probabilities</span><Badge>Not available</Badge></div>
          <div><CircleAlert size={17}/><span>Model-specific SHAP explanations</span><Badge>Future research</Badge></div>
        </div>
        <p className="fineprint">The website only displays documented study results. It does not perform new evaluations or compute significance tests automatically.</p>
      </Panel>
    </div>
    <ResearchWarning compact/>
  </>;
}

function Documentation() {
  const sections = [
    {no:'01', title:'Start the research backend', cmd:'bash scripts/start_api.sh', desc:'Phase 2 SQLite and Phase 3 models must be prepared and verified.'},
    {no:'02', title:'Start the research frontend', cmd:'cd frontend && npm install && npm run dev', desc:'The Vite server listens only on 127.0.0.1:5173 and proxies /api/v1 to local FastAPI.'},
    {no:'03', title:'Open the dashboard', cmd:'http://127.0.0.1:5173', desc:'Use the phenotype workbench, disease explorer and model laboratory.'},
  ];
  return <>
    <SectionIntro eyebrow="GUIDE / 04" title="Documentation" description="A practical guide to the local architecture, data handling, and API powering this research dashboard."/>
    <div className="docs-banner"><div className="docs-banner-icon"><Network size={34}/></div><div><h2>One system. Three connected layers.</h2>
      <p>React/Vite for the user experience, FastAPI for validated requests and model ranking, and read-only HPO SQLite with a verified local model bundle.</p></div></div>
    <Panel title="Run locally on your Mac" subtitle="No hosting subscription, Docker, cloud database or dedicated GPU required.">
      <div className="docs-steps">{sections.map((s) => <div className="docs-step" key={s.no}><div className="docs-number">{s.no}</div><div><h3>{s.title}</h3><p>{s.desc}</p><code>{s.cmd}</code></div></div>)}</div>
    </Panel>
    <div className="docs-columns"><Panel title="API reference" subtitle="Versioned /api/v1 HTTP endpoints">
      <div className="api-reference">{[['GET','/health'],['GET','/ready'],['GET','/knowledge/stats'],['GET','/phenotypes/search'],['GET','/diseases/search'],['GET','/diseases/{id}'],['GET','/models'],['POST','/rank']].map(([method,path]) =>
        <div className="api-reference-row" key={path}><Badge tone={method === 'POST' ? 'teal' : 'muted'}>{method}</Badge><code>/api/v1{path}</code></div>)}</div>
      <p className="fineprint">Full Swagger documentation is available from FastAPI at http://127.0.0.1:8000/docs after the backend starts.</p>
    </Panel><Panel title="Scientific guardrails" subtitle="Important usage boundaries">
      <div className="guardrails">{[
        ['Local-only execution','The included launcher and dev proxy use loopback; the service is not internet-hosted.'],
        ['No patient history','Observations remain in browser memory for the active session and are not persisted by the dashboard.'],
        ['Model scores ≠ probabilities','Scores are not calibrated and should never be interpreted as disease risk.'],
        ['Historical ≠ live metrics','The model dashboard links to its original published GitHub evaluation.']
      ].map(([title,desc]) => <div className="guardrail" key={title}><Check size={17}/><div><strong>{title}</strong><p>{desc}</p></div></div>)}</div>
    </Panel></div>
    <div className="docs-links"><a target="_blank" rel="noreferrer" href="https://github.com/uday8116/RareGenXAI/blob/main/docs/PHASE_04_BACKEND.md"><BookOpen size={17}/> Phase 4 API guide <ExternalLink size={14}/></a>
      <a target="_blank" rel="noreferrer" href="https://github.com/uday8116/RareGenXAI/blob/main/docs/PHASE_03_FINAL_AUDIT.md"><FileText size={17}/> Model research audit <ExternalLink size={14}/></a></div>
    <ResearchWarning compact/>
  </>;
}

export default function App() {
  const backend = useBackend();
  return <DashboardLayout backend={backend}><Routes>
    <Route path="/" element={<Overview backend={backend}/>}/>
    <Route path="/workbench" element={<Workbench backend={backend}/>}/>
    <Route path="/explorer" element={<Explorer backend={backend}/>}/>
    <Route path="/models" element={<ModelLab backend={backend}/>}/>
    <Route path="/experiments" element={<Experiments/>}/>
    <Route path="/documentation" element={<Documentation/>}/>
    <Route path="*" element={<div className="not-found"><EmptyState icon={Compass} title="Page not found" description="Choose a workspace page from the navigation."/><NavLink className="button primary" to="/">Back to overview <ArrowLeft size={16}/></NavLink></div>}/>
  </Routes></DashboardLayout>;
}
