/** Phase 6 research XAI summaries.
 * Pure deterministic calculations from actual FastAPI responses only.
 * No simulated predictions, diagnostic probabilities, or hidden data stores.
 */
export const POSITIVE_STATUSES = new Set(['confirmed_present', 'suspected_present']);
export const MAX_COMPARE_METHODS = 4;

export function toApiObservations(observations) {
  return observations.map(({ hpo_id, status }) => ({ hpo_id, status }));
}

export function rankPayload(observations, options, method) {
  return {
    observations: toApiObservations(observations),
    method,
    quality: Boolean(options.quality),
    top_k: Math.max(1, Math.min(20, Number(options.top_k) || 5)),
    candidates: Math.max(1, Math.min(100, Number(options.candidates) || 40)),
  };
}

export function evidenceGroups(explanation, observations) {
  if (!explanation || !Array.isArray(explanation.evidence)) return null;
  const names = new Map(observations.map((row) => [row.hpo_id, row.name || row.hpo_id]));
  const items = explanation.evidence.map((entry) => {
    const value = typeof entry.contribution === 'number' ? entry.contribution : null;
    const absent = entry.status === 'confirmed_absent';
    let role = 'unmatched';
    if (entry.status === 'unknown') role = 'ignored';
    else if (absent && entry.match > 0) role = 'contradicting';
    else if (!absent && value != null && value > 0) role = 'supporting';
    else if (!absent && value === null && entry.match > 0) role = 'annotated';
    return { ...entry, label: names.get(entry.hpo_id) || entry.hpo_id, role };
  });
  const baseline = explanation.explanation_type === 'signed_ontology_contributions';
  const support = baseline ? items.reduce((x, e) => x + Math.max(0, e.contribution || 0), 0) : null;
  const opposition = baseline ? items.reduce((x, e) => x + Math.min(0, e.contribution || 0), 0) : null;
  const net = baseline ? Math.round((support + opposition) * 1e6) / 1e6 : null;
  const largest = Math.max(1e-9, ...items.map((e) => Math.abs(e.contribution || 0)));
  const validScore = baseline && Math.abs(net - explanation.reconstructed_baseline_score) <= 0.00001;
  return { items, baseline, support, opposition, net, largest, validScore };
}

export function compareMethods(reports) {
  if (!Array.isArray(reports) || reports.length === 0) return null;
  const firsts = reports.map((report) => ({
    method: report.method,
    first: report.results?.[0] || null,
    count: report.results?.length || 0,
    topFiveIds: (report.results || []).slice(0, 5).map((r) => r.disease_id),
    model_sha256: report.model_sha256 || null,
  }));
  const counts = new Map();
  for (const row of firsts) if (row.first) {
    counts.set(row.first.disease_id, (counts.get(row.first.disease_id) || 0) + 1);
  }
  const leaders = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const consensusId = leaders[0]?.[0] || null;
  const votes = leaders[0]?.[1] || 0;
  return {
    rows: firsts,
    consensusId,
    agreementCount: votes,
    allAgree: Boolean(consensusId && votes === firsts.length),
    methodsCount: firsts.length,
    // Agreement is an observation about algorithms, not correctness.
    agreementLabel: consensusId ? votes + ' of ' + firsts.length + ' methods share a leading candidate'
      : 'No leading candidates in the selected methods',
  };
}

export function ablationChoices(observations) {
  const positives = observations.filter((o) => POSITIVE_STATUSES.has(o.status));
  return observations.filter((o) => (
    o.status !== 'unknown' &&
    (o.status === 'confirmed_absent' || positives.length > 1)
  ));
}

export function dropObservation(observations, hpoId) {
  if (!ablationChoices(observations).some((row) => row.hpo_id === hpoId)) {
    throw new Error('Cannot remove the last present or suspected phenotype.');
  }
  return observations.filter((row) => row.hpo_id !== hpoId);
}

export function describeAblation(original, after, removedId) {
  if (!original || !after || original.method !== after.method) {
    throw new Error('Sensitivity reports must use the same ranking method.');
  }
  const initial = original.results?.[0] || null;
  const changed = after.results?.[0] || null;
  const oldPosition = initial ? (after.results || []).findIndex((x) => x.disease_id === initial.disease_id) : -1;
  const oldCandidate = oldPosition < 0 ? null : after.results[oldPosition];
  return {
    removedId,
    method: original.method,
    before: initial,
    after: changed,
    changedLeader: (initial?.disease_id || null) !== (changed?.disease_id || null),
    originalLeaderRankAfter: oldPosition < 0 ? null : oldPosition + 1,
    originalLeaderScoreAfter: oldCandidate?.score ?? null,
    // Only a same-method raw ranking-score difference. Not a risk difference
    // and not the isolated causal contribution of the omitted phenotype.
    rawScoreChange: initial && oldCandidate ? oldCandidate.score - initial.score : null,
  };
}
