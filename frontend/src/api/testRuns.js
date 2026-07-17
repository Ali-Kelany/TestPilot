/**
 * Test Run API — wraps every /api/test-runs endpoint.
 *
 * Endpoint reference:
 *   GET    /api/test-runs/:id                  → TestRunResponse
 *   DELETE /api/test-runs/:id                  → (204)
 *   GET    /api/test-runs/:id/screenshots      → { screenshots: ScreenshotMeta[] }
 *   GET    /api/test-runs/:id/screenshots/:n   → image bytes  (used as <img src>)
 *   GET    /api/test-runs/:id/logs             → { logs: string }
 */

import { get, del } from './client.js'

// ── Reads ─────────────────────────────────────────────────────────────────────

/**
 * Fetch full details for a single run, including step results.
 *
 * @param {string} id  Run UUID (same as the session_id from WebSocket events)
 * @returns {Promise<TestRunResponse>}
 */
export function getTestRun(id) {
  return get(`/test-runs/${id}`)
}

/**
 * Fetch metadata for all screenshots in a run (no image bytes).
 * Returns an array sorted by sequence order.
 *
 * Each item contains:
 *   { id, index, step_number, kind, sequence, mime_type, captured_at, url }
 *
 * @param {string} runId
 * @returns {Promise<{ screenshots: ScreenshotMeta[] }>}
 */
export function getScreenshots(runId) {
  return get(`/test-runs/${runId}/screenshots`)
}

/**
 * Build the URL for a screenshot image by its DB id.
 * Use directly as the `src` of an <img> tag — the browser fetches the bytes.
 *
 * @param {string} runId
 * @param {number} screenshotId  DB primary key of the screenshot
 * @returns {string}
 *
 * @example
 * <img src={screenshotUrl(run.id, 42)} alt="Step 2 observation" />
 */
export function screenshotUrl(runId, screenshotId) {
  return `/api/test-runs/${runId}/screenshots/${screenshotId}`
}

/**
 * Fetch the raw log text for a run.
 * Optionally limited to the last N lines.
 *
 * @param {string}         runId
 * @param {{ lines?: number }} [params]
 * @returns {Promise<{ logs: string }>}
 */
export function getLogs(runId, { lines } = {}) {
  const qs = lines ? `?lines=${lines}` : ''
  return get(`/test-runs/${runId}/logs${qs}`)
}

// ── Writes ────────────────────────────────────────────────────────────────────

/**
 * Delete a test run and all associated screenshots / logs.
 *
 * @param {string} id
 * @returns {Promise<null>}
 */
export function deleteTestRun(id) {
  return del(`/test-runs/${id}`)
}

// ── JSDoc type stubs ──────────────────────────────────────────────────────────

/**
 * @typedef {{
 *   id: string,
 *   test_case_id: string,
 *   test_case_name: string,
 *   status: 'running'|'passed'|'failed'|'error'|'aborted',
 *   provider: string|null,
 *   model: string|null,
 *   duration_seconds: number|null,
 *   steps_passed: number,
 *   steps_failed: number,
 *   total_tokens: number|null,
 *   started_at: string,
 *   completed_at: string|null,
 *   step_results: StepResultResponse[],
 * }} TestRunResponse
 *
 * @typedef {{
 *   id: number,
 *   step_number: number,
 *   status: 'passed'|'failed',
 *   retry_count: number,
 *   result_reason: string|null,
 *   screenshot_observation_id: number|null,
 *   screenshot_verification_id: number|null,
 *   executed_at: string,
 * }} StepResultResponse
 *
 * @typedef {{
 *   id: number,
 *   index: number,
 *   step_number: number,
 *   kind: 'observation'|'verification',
 *   sequence: number,
 *   mime_type: string,
 *   captured_at: string,
 *   url: string,
 * }} ScreenshotMeta
 */
