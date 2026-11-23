import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowLeftRight, CheckCircle2, GitBranch,
  Info, Layers, LoaderCircle, RefreshCw, ShieldCheck, Sparkles,
} from 'lucide-react';

import { api } from '../api.js';
import { METHOD_LABELS } from '../research.js';
import {
  MAX_COMPARE_METHODS, ablationChoices, compareMethods, describeAblation,
  dropObservation, evidenceGroups, rankPayload, matchesExplanation,
  assertConsistentModelVersions,
} from '../xai.js';

const METHODS = Object.keys(METHOD_LABELS);

function Notice({ children, danger = false }) {
  return <p className={'xai-notice' + (danger ? ' xai-error' : '')} role={danger ? 'alert' : undefined}>
    {danger ? <AlertTriangle size={16}/> : <Info size={16}/>}
    <span>{children}</span>
  </p>;
}

function Busy({ label }) {
  return <span className="xai-busy"><LoaderCircle className="spin" size={16} aria-hidden="true"/>{label}</span>;
}

function EvidenceTrace({ report, observations, options }) {
  const [selected, setSelected] = useState(report.results[0]?.disease_id || '');
  const [explanation, setExplanation] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const request = useMemo(() => rankPayload(observations, options, report.method),
    [observations, options.quality, options.top_k, options.candidates, report.method]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    setBusy(true);
    setError('');
    setExplanation(null);
    api.explain({ ...request, disease_id: selected }, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setExplanation(value);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [selected, request]);

  const groups = useMemo(() => evidenceGroups(explanation, observations), [explanation, observations]);
  const mismatchedExplanation = Boolean(explanation && !matchesExplanation(explanation, report, selected));
  const chosenRank = report.results.find((r) => r.disease_id === selected);
  const deviation = groups?.baseline && chosenRank
    ? Math.abs(groups.net - chosenRank.score) : 0;

  return <div className="xai-stack">
    <div className="xai-control-row">
      <div>
        <label className="form-label" htmlFor="xai-candidate">Disease candidate to explain</label>
        <select id="xai-candidate" className="xai-select" value={selected} onChange={(e) => setSelected(e.target.value)}>
          {report.results.map((row, idx) =>
            <option value={row.disease_id} key={row.disease_id}>#{idx + 1} {row.disease_name} ({row.disease_id})</option>)}
        </select>
      </div>
      <div className="xai-legend"><span className="xai-dot support"/> Supporting evidence
        <span className="xai-dot oppose"/> Contradicting evidence</div>
    </div>
    {busy && <Busy label="Tracing HPO ontology evidence..."/>}
    {error && <Notice danger>Ontology explanation unavailable: {error}. This panel never invents explanation records.</Notice>}
    {mismatchedExplanation && <Notice danger>The returned explanation does not match the selected candidate, method or verified model. Rerun ranking; no untrusted evidence will be displayed.</Notice>}
    {groups?.baseline && !mismatchedExplanation && (!groups.validScore || deviation > 0.00001)
      && <Notice danger>The evidence contributions do not reproduce the ranked baseline score. The trace is hidden until the source snapshot is checked.</Notice>}
    {groups && !mismatchedExplanation && (!groups.baseline || (groups.validScore && deviation <= 0.00001)) && <>
      <div className="xai-summary-grid">
        <div className="xai-mini-card"><small>Explanation kind</small><strong>{groups.baseline ? 'Signed baseline evidence' : 'Ontology context only'}</strong></div>
        <div className="xai-mini-card"><small>{groups.baseline ? 'Supporting score' : 'Ontology matches'}</small>
          <strong>{groups.baseline ? '+' + groups.support.toFixed(4) : groups.items.filter((e) => e.match > 0).length}</strong></div>
        <div className="xai-mini-card"><small>{groups.baseline ? 'Contradicting score' : 'ML attribution'}</small>
          <strong>{groups.baseline ? groups.opposition.toFixed(4) : 'Not computed'}</strong></div>
      </div>
       <div className="xai-trace">
        {groups.items.map((e) => {
          const pct = groups.baseline ? Math.min(100, 100 * Math.abs(e.contribution || 0) / groups.largest)
            : 100 * (e.match || 0);
          return <div className="xai-evidence-item" key={e.hpo_id}>
            <div className="xai-evidence-info">
              <strong>{e.label}</strong><small>{e.hpo_id} · {e.status.replaceAll('_', ' ')} · {e.relation.replaceAll('_', ' ')}</small>
              {e.best_disease_hpo_id && <small>Nearest disease annotation: {e.best_disease_hpo_id}
                {e.shared_ancestor_hpo_id ? ' · Shared ancestor: ' + e.shared_ancestor_hpo_id : ''}</small>}
            </div>
            <div className="xai-impact">
              <div className="xai-impact-track">
                <div className={'xai-impact-fill' + (e.role === 'contradicting' ? ' negative' : '')}
                  style={{width: pct + '%'}} aria-hidden="true"/>
              </div>
              <span>{groups.baseline
                ? (e.contribution >= 0 ? '+' : '') + e.contribution.toFixed(4)
                : e.match.toFixed(2) + ' ontology match'}</span>
            </div>
          </div>;
        })}
      </div>
      {groups.baseline ? <div className="xai-composition">
        <span>Signed component sum</span><strong>{groups.net.toFixed(4)}</strong>
        <span className="xai-check"><CheckCircle2 size={15}/> {groups.validScore && deviation <= 0.00001 ? 'Consistent with baseline score' : 'Check score consistency'}</span>
      </div> : <Notice>For trained models, these ontology links are descriptive context only. There are **no per-phenotype SHAP values**, causal importances, or calibrated probabilities.</Notice>}
      <p className="fineprint">Ontology relationships are based on the local HPO snapshot. A missing annotation does not prove that a phenotype cannot occur in a disease. These signs follow the research ranking weights, not medical certainty.</p>
    </>}
  </div>;
}

function CaseComparison({ report, observations, options, availableMethods }) {
  const available = METHODS.filter((m) => availableMethods.includes(m));
  const [selected, setSelected] = useState(() => {
    const pair = [...new Set(['overlap', report.method])].filter((m) => available.includes(m));
    if (pair.length < 2) {
      const next = available.find((m) => !pair.includes(m));
      if (next) pair.push(next);
    }
    return pair.slice(0, 2);
  });
  const [responses, setResponses] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const controllerRef = useRef(null);
  useEffect(() => () => controllerRef.current?.abort(), []);
  const output = useMemo(() => compareMethods(responses), [responses]);

  function toggle(method) {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setBusy(false); setResponses(null); setError('');
    setSelected((list) => list.includes(method) ? list.filter((x) => x !== method)
      : list.length >= MAX_COMPARE_METHODS ? list : [...list, method]);
  }

  async function run() {
    if (selected.length < 2 || busy) return;
    const controller = new AbortController();
    controllerRef.current?.abort();
    controllerRef.current = controller;
    setResponses(null); setError(''); setBusy(true);
    const results = [];
    try {
      for (const method of selected) {
        if (controller.signal.aborted) return;
        setProgress(METHOD_LABELS[method] || method);
        // Keep every method on the exact same output cutoff; candidate
        // universe may still differ by retrieval method.
        const payload = rankPayload(observations, options, method);
        const ranked = await api.rank(payload, controller.signal);
        if (ranked?.method !== method || !Array.isArray(ranked.results)) {
          throw new Error('Unexpected response while comparing model outputs.');
        }
        assertConsistentModelVersions([...results, ranked], report);
        results.push(ranked);
      }
      if (controllerRef.current === controller) setResponses(results);
    } catch (err) {
      if (controllerRef.current === controller) setError(err.message);
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setBusy(false); setProgress('');
      }
    }
  }

  return <div className="xai-stack">
    <Notice>All selected models receive the same HPO observations and ranking settings. Their score scales and candidate pools can differ. Agreement is not evidence of correctness or patient-level accuracy.</Notice>
    <fieldset className="xai-checkbox-fieldset" disabled={busy}>
      <legend className="form-label">Select 2–{MAX_COMPARE_METHODS} locally available methods</legend>
      <div className="xai-method-pills">{METHODS.map((m) => {
        const enabled = available.includes(m);
        return <label key={m} className={'xai-method-pill' + (selected.includes(m) ? ' checked' : '') + (!enabled ? ' disabled' : '')}>
          <input type="checkbox" checked={selected.includes(m)} disabled={!enabled || (selected.length >= MAX_COMPARE_METHODS && !selected.includes(m))}
            onChange={() => toggle(m)}/>
          {METHOD_LABELS[m]}
        </label>;
      })}</div>
    </fieldset>
    <button type="button" className="button primary" disabled={busy || selected.length < 2}
      onClick={run}><GitBranch size={17}/>{busy ? 'Comparing ' + progress + '...' : 'Compare methods on these HPO findings'}</button>
    {busy && <Busy label="Running real local model inference. No results are simulated."/>}
    {error && <Notice danger>{error}</Notice>}
    {output && <div className="xai-stack" aria-live="polite">
      <div className="xai-summary-grid">
        <div className="xai-mini-card"><small>Methods compared</small><strong>{output.methodsCount}</strong></div>
        <div className="xai-mini-card"><small>Top-candidate agreement</small><strong>{output.agreementCount}/{output.methodsCount}</strong></div>
        <div className="xai-mini-card"><small>Interpretation</small><strong>{output.allAgree ? 'Same leading candidate' : 'Methods differ'}</strong></div>
      </div>
      <div className="xai-table-wrap"><table className="xai-table">
        <thead><tr><th scope="col">Method</th><th scope="col">Top-ranked candidate</th>
          <th scope="col">Raw rank score</th><th scope="col">Results returned</th></tr></thead>
        <tbody>{output.rows.map((row) => <tr key={row.method}>
          <th scope="row">{METHOD_LABELS[row.method] || row.method}</th>
          <td>{row.first ? <><strong>{row.first.disease_name}</strong><small>{row.first.disease_id}</small></> : 'No matching candidate'}</td>
          <td>{typeof row.first?.score === 'number' ? row.first.score.toFixed(4) : '—'}</td>
          <td>{row.count}</td>
        </tr>)}</tbody>
      </table></div>
      <Notice>{output.agreementLabel}. These rankings have no known ground truth for this input, so Top-1 accuracy cannot be calculated here.</Notice>
    </div>}
  </div>;
}

function SensitivityLab({ report, observations, options }) {
  const choices = useMemo(() => ablationChoices(observations), [observations]);
  const [omit, setOmit] = useState(choices[0]?.hpo_id || '');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const controllerRef = useRef(null);
  useEffect(() => () => controllerRef.current?.abort(), []);
  const result = useMemo(() => response ? describeAblation(report, response, omit) : null, [report, response, omit]);

  async function run() {
    if (!omit || busy) return;
    const controller = new AbortController();
    controllerRef.current?.abort();
    controllerRef.current = controller;
    setError(''); setResponse(null); setBusy(true);
    try {
      const perturbed = dropObservation(observations, omit);
      const payload = rankPayload(perturbed, options, report.method);
      payload.top_k = 20;
      const ranked = await api.rank(payload, controller.signal);
      if (ranked?.method !== report.method || !Array.isArray(ranked.results)) {
        throw new Error('The sensitivity rerun did not return a valid ranking.');
      }
      assertConsistentModelVersions([ranked], report);
      if (controllerRef.current === controller) setResponse(ranked);
    } catch (err) {
      if (controllerRef.current === controller) setError(err.message);
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setBusy(false);
      }
    }
  }

  return <div className="xai-stack">
    <Notice>This is a leave-one-phenotype-out sensitivity test: rerun the same method without one chosen observation. It may change the normalization, retrieval shortlist, and model features. It is not a causal explanation or a calibrated disease-risk change.</Notice>
    {choices.length === 0
      ? <Notice danger>At least two present/suspected findings, or one removable confirmed-absent finding, are needed for a valid test. The last positive finding cannot be removed.</Notice>
      : <>
        <div className="xai-control-row">
          <div><label className="form-label" htmlFor="xai-omit">Observation to omit in the what-if rerun</label>
            <select id="xai-omit" className="xai-select" value={omit} onChange={(e) => {
              controllerRef.current?.abort(); controllerRef.current = null;
              setBusy(false); setResponse(null); setError(''); setOmit(e.target.value);
            }}>
              {choices.map((row) => <option key={row.hpo_id} value={row.hpo_id}>{row.name || row.hpo_id} ({row.hpo_id})</option>)}
            </select></div>
        </div>
        <button type="button" className="button primary" onClick={run} disabled={busy}>
          <RefreshCw size={17}/>{busy ? 'Running sensitivity check...' : 'Rerun without selected phenotype'}</button>
      </>}
    {busy && <Busy label="Re-ranking the modified observation set..."/>}
    {error && <Notice danger>{error}</Notice>}
    {result && <div className="xai-stack" aria-live="polite">
      <div className="xai-side-by-side">
        <div className="xai-side"><small>Original leading candidate</small><strong>{result.before?.disease_name || 'No candidates'}</strong><span>{result.before?.disease_id || '—'}</span></div>
        <ArrowLeftRight size={19} className="xai-between" aria-hidden="true"/>
        <div className="xai-side"><small>After removing {result.removedId}</small><strong>{result.after?.disease_name || 'No candidates'}</strong><span>{result.after?.disease_id || '—'}</span></div>
      </div>
      <div className="xai-summary-grid">
        <div className="xai-mini-card"><small>Leading candidate changed</small><strong>{result.changedLeader ? 'Yes' : 'No'}</strong></div>
        <div className="xai-mini-card"><small>Original leader after rerank</small><strong>{result.originalLeaderRankAfter ? '#' + result.originalLeaderRankAfter : 'Outside returned top 20'}</strong></div>
        <div className="xai-mini-card"><small>Same-method score difference</small><strong>{typeof result.rawScoreChange === 'number' ? result.rawScoreChange.toFixed(4) : 'Not available'}</strong></div>
      </div>
      <p className="fineprint">An unlisted candidate may be absent from the retrieval shortlist or outside the returned top 20. A rank change does not prove the omitted phenotype caused or ruled out a disease.</p>
    </div>}
  </div>;
}

const LAB_TABS = [
  { id: 'evidence', label: 'HPO evidence trace', icon: Layers },
  { id: 'comparison', label: 'Same-case model comparison', icon: GitBranch },
  { id: 'sensitivity', label: 'What-if sensitivity', icon: Activity },
];

export default function ExplanationLab({ report, observations, options, availableMethods }) {
  const [tab, setTab] = useState('evidence');
  if (!report || !report.results?.length) return null;
  return <section className="xai-lab" aria-label="Phase 6 explainability laboratory">
    <div className="xai-lab-header">
      <div><span className="eyebrow"><Sparkles size={13}/> PHASE 06 · AUDITABLE AI</span>
        <h2>Explainability laboratory</h2>
        <p>Explore real ontology evidence, compare local methods on the same input, and study ranking sensitivity.</p></div>
      <span className="xai-research-tag"><ShieldCheck size={14}/> RESEARCH ONLY</span>
    </div>
    <div className="xai-tab-list" role="tablist" aria-label="Explainability analysis tools">
      {LAB_TABS.map(({ id, label, icon: Icon }) =>
        <button type="button" key={id} role="tab" id={'xai-tab-' + id}
          aria-controls={'xai-panel-' + id} aria-selected={tab === id}
          className={'xai-tab' + (tab === id ? ' active' : '')}
          onClick={() => setTab(id)}><Icon size={17}/>{label}</button>)}
    </div>
    <div className="xai-tab-panel" role="tabpanel" id={'xai-panel-' + tab} aria-labelledby={'xai-tab-' + tab}>
      {tab === 'evidence' && <EvidenceTrace report={report} observations={observations} options={options}/>}
      {tab === 'comparison' && <CaseComparison report={report} observations={observations} options={options} availableMethods={availableMethods}/>}
      {tab === 'sensitivity' && <SensitivityLab report={report} observations={observations} options={options}/>}
    </div>
  </section>;
}
