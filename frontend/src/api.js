/**
 * Phase 5 API client. Always uses same-origin /api/v1 through Vite's localhost
 * proxy. A missing backend is reported explicitly; no fabricated predictions.
 * The client never persists clinical observations in localStorage or cookies.
 */
const BASE = '/api/v1';
const DEFAULT_TIMEOUT_MS = 15000;

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function describeValidation(detail) {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((part) => part.msg || part.message || 'Invalid field').join('; ');
  }
  return 'The request could not be completed.';
}

async function call(path, { method = 'GET', body, signal, timeout = DEFAULT_TIMEOUT_MS } = {}) {
  const controller = new AbortController();
  const handle = setTimeout(() => controller.abort(), timeout);
  const externalAbort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', externalAbort, { once: true });
  try {
    const response = await fetch(BASE + path, {
      method,
      signal: controller.signal,
      credentials: 'omit',
      cache: 'no-store',
      headers: { Accept: 'application/json', ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    let data = null;
    try {
      data = await response.json();
    } catch {
      if (response.ok) throw new ApiError('The API returned an invalid JSON response.', response.status);
    }
    if (!response.ok) {
      throw new ApiError(describeValidation(data?.detail) || 'API request failed.', response.status);
    }
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error?.name === 'AbortError') {
      throw new ApiError('Request cancelled or timed out. Please retry.');
    }
    throw new ApiError('Cannot reach the local FastAPI backend. Start it on 127.0.0.1:8000.');
  } finally {
    clearTimeout(handle);
    signal?.removeEventListener('abort', externalAbort);
  }
}

export const api = {
  health: () => call('/health', { timeout: 4000 }),
  ready: () => call('/ready', { timeout: 10000 }),
  stats: () => call('/knowledge/stats'),
  models: () => call('/models'),
  phenotypes: (query, signal) => call('/phenotypes/search?q=' + encodeURIComponent(query) + '&limit=12', { signal }),
  phenotype: (id) => call('/phenotypes/' + encodeURIComponent(id)),
  diseases: (query, signal) => call('/diseases/search?q=' + encodeURIComponent(query) + '&limit=25', { signal }),
  disease: (id) => call('/diseases/' + encodeURIComponent(id)),
  rank: (payload, signal) => call('/rank', { method: 'POST', body: payload, signal, timeout: 60000 }),
  explain: (payload, signal) => call('/explain', { method: 'POST', body: payload, signal, timeout: 20000 }),
};
