/**
 * Local-only export of already returned disease ranking results.
 * Files contain candidate diseases and HPO evidence, no patient names or notes.
 */
export const EXPORT_DISCLAIMER = 'Research-only candidate prioritization; scores are not calibrated disease probabilities or diagnoses.';

function safeCsvValue(value) {
  // Preserve genuine numeric ranking scores as numeric spreadsheet cells.
  if (typeof value === 'number' && Number.isFinite(value)) return '"' + value + '"';
  const raw = String(value ?? '');
  // Neutralize Excel/Calc formula injection in disease labels and identifiers.
  const safe = /^[\s]*[=+@\-\t\r]/u.test(raw) ? "'" + raw : raw;
  return '"' + safe.replaceAll('"', '""') + '"';
}

export function rankingCsv(report) {
  const columns = [
    'rank', 'disease_id', 'disease_name', 'ranking_score',
    'matched_hpo_ids', 'retrieval_similarity', 'method', 'research_warning',
  ];
  const rows = (report?.results || []).map((r, i) => [
    i + 1, r.disease_id, r.disease_name, r.score,
    (r.matched_hpo || []).join(';'), r.retrieval_similarity ?? '',
    report.method, EXPORT_DISCLAIMER,
  ]);
  return [columns.map(safeCsvValue).join(','), ...rows.map((row) => row.map(safeCsvValue).join(','))].join('\r\n') + '\r\n';
}

export function rankingJson(report) {
  return JSON.stringify({
    source: 'RareGenXAI local research dashboard',
    kind: 'ranked_disease_candidates_not_diagnosis',
    warning: EXPORT_DISCLAIMER,
    method: report.method,
    model_sha256: report.model_sha256 ?? null,
    explanation_type: report.explanation_type,
    results: report.results,
  }, null, 2) + '\n';
}

export function downloadRanking(report, format = 'csv') {
  if (!report || !Array.isArray(report.results) || !['csv', 'json'].includes(format)) {
    throw new Error('Invalid local research report export request');
  }
  const data = format === 'csv' ? rankingCsv(report) : rankingJson(report);
  const type = format === 'csv' ? 'text/csv;charset=utf-8' : 'application/json;charset=utf-8';
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'raregenxai-ranking-' + report.method + '.' + format;
  link.style.display = 'none';
  document.body.appendChild(link);
  try {
    link.click();
  } finally {
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
