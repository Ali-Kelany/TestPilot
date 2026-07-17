import { Routes, Route, Navigate } from 'react-router-dom'

// Pages are imported lazily so the initial bundle only includes the
// home page. Vite splits each lazy import into its own chunk automatically.
import { lazy, Suspense } from 'react'

const ProjectsPage  = lazy(() => import('./pages/ProjectsPage.jsx'))
const WorkspacePage = lazy(() => import('./pages/WorkspacePage.jsx'))
const RunDetailPage = lazy(() => import('./pages/RunDetailPage.jsx'))

// Simple full-page loading state shown during chunk fetch.
// Replaced by skeleton screens once each page is implemented.
function PageLoader() {
  return (
    <div className="flex h-screen items-center justify-center text-sm text-gray-400">
      Loading…
    </div>
  )
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Home — project list */}
        <Route path="/" element={<ProjectsPage />} />

        {/* Project workspace — sidebar + selected test case panel.
            The selected test case lives in a ?tc= query param so the
            URL is shareable and survives a browser refresh. */}
        <Route path="/projects/:projectId" element={<WorkspacePage />} />

        {/* Full-page run detail — for inspecting a completed run.
            Opened from the run history table; can be opened in a new tab. */}
        <Route path="/runs/:runId" element={<RunDetailPage />} />

        {/* Catch-all — redirect unknown paths back home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}