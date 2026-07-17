/**
 * Project API — wraps every /api/projects endpoint.
 *
 * Each function returns the raw parsed JSON that the backend sends.
 * Frontend components call these directly from useEffect-driven fetches
 * or mutation handlers.
 *
 * Endpoint reference:
 *   GET    /api/projects                         → PaginatedResponse<ProjectResponse>
 *   POST   /api/projects                         → ProjectResponse  (201)
 *   GET    /api/projects/:id                     → ProjectResponse
 *   PUT    /api/projects/:id                     → ProjectResponse
 *   DELETE /api/projects/:id                     → (204)
 *   GET    /api/projects/:id/stats               → ProjectStats
 *   GET    /api/projects/:id/test-cases          → PaginatedResponse<TestCaseResponse>
 *   GET    /api/projects/:id/test-runs           → PaginatedResponse<TestRunListResponse>
 */

import { get, post, put, del } from './client.js'

// ── Reads ─────────────────────────────────────────────────────────────────────

/**
 * Fetch a paginated list of all projects.
 *
 * @param {{ page?: number, pageSize?: number }} [params]
 * @returns {Promise<{ items: ProjectResponse[], total: number, pages: number }>}
 */
export function listProjects({ page = 1, pageSize = 50 } = {}) {
  return get(`/projects?page=${page}&page_size=${pageSize}`)
}

// get project by id
export function getProject(id) {
  return get(`/projects/${id}`)
}

/**
 * Fetch aggregate stats for a project (pass rate, total runs, …).
 *
 * @param {string} id
 * @returns {Promise<ProjectStats>}
 */
export function getProjectStats(id) {
  return get(`/projects/${id}/stats`)
}

/**
 * Fetch the test cases that belong to a project.
 * Used to populate the workspace sidebar.
 *
 * @param {string} id
 * @param {{ page?: number, pageSize?: number }} [params]
 * @returns {Promise<{ items: TestCaseResponse[], total: number }>}
 */
export function listProjectTestCases(id, { page = 1, pageSize = 100 } = {}) {
  return get(`/projects/${id}/test-cases?page=${page}&page_size=${pageSize}`)
}

/**
 * Fetch all test runs across every test case in a project.
 * Used for the project-level history view.
 *
 * @param {string} id
 * @param {{ page?: number, pageSize?: number }} [params]
 * @returns {Promise<{ items: TestRunListResponse[], total: number }>}
 */
export function listProjectTestRuns(id, { page = 1, pageSize = 50 } = {}) {
  return get(`/projects/${id}/test-runs?page=${page}&page_size=${pageSize}`)
}

// ── Writes ────────────────────────────────────────────────────────────────────

/**
 * Create a new project.
 *
 * @param {{ name: string, description?: string }} data
 * @returns {Promise<ProjectResponse>}
 */
export function createProject(data) {
  return post('/projects', data)
}

/**
 * Update a project's name or description.
 *
 * @param {string}                                       id
 * @param {{ name?: string, description?: string | null }} data
 * @returns {Promise<ProjectResponse>}
 */
export function updateProject(id, data) {
  return put(`/projects/${id}`, data)
}

/**
 * Delete a project and all of its test cases.
 * Returns null (204 No Content).
 *
 * @param {string} id
 * @returns {Promise<null>}
 */
export function deleteProject(id) {
  return del(`/projects/${id}`)
}

// ── JSDoc type stubs (not enforced at runtime, just for IDE hints) ─────────────

/**
 * @typedef {{ id: string, name: string, description: string|null, created_at: string, test_cases_count: number }} ProjectResponse
 * @typedef {{ test_cases_count: number, total_runs: number, passed_runs: number, failed_runs: number, success_rate: number }} ProjectStats
 * @typedef {{ id: string, status: string, provider: string|null, duration_seconds: number|null, steps_passed: number, steps_failed: number, started_at: string, completed_at: string|null }} TestRunListResponse
 * @typedef {{ id: string, project_id: string, external_id: string|null, name: string, type: string, target_url: string, steps: {action:string,assertion:string}[], created_at: string, runs_count: number }} TestCaseResponse
 */
