
import { useCallback, useEffect, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  listProjects,
  createProject,
  updateProject,
  deleteProject,
} from '../api/projects.js'
import ProjectCard from '../components/ProjectCard.jsx'
import Modal       from '../components/ui/Modal.jsx'
import Button      from '../components/ui/Button.jsx'
import { Input, Textarea } from '../components/ui/Input.jsx'

// ── Card skeleton shown during initial load ───────────────────────────────────

function CardSkeleton() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4 animate-pulse">
      <div className="space-y-2">
        <div className="h-4 w-1/2 bg-gray-100 rounded" />
        <div className="h-3 w-3/4 bg-gray-100 rounded" />
      </div>
      <div className="space-y-2">
        <div className="h-2 w-full bg-gray-100 rounded-full" />
        <div className="flex gap-3">
          <div className="h-3 w-16 bg-gray-100 rounded" />
          <div className="h-3 w-16 bg-gray-100 rounded" />
        </div>
      </div>
      <div className="h-px bg-gray-100" />
      <div className="flex justify-between">
        <div className="h-5 w-20 bg-gray-100 rounded" />
        <div className="h-3 w-24 bg-gray-100 rounded" />
      </div>
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ onCreate }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gray-100">
        <svg className="w-7 h-7 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v8.25m19.5 0A2.25 2.25 0 0 1 19.5 16.5H4.5a2.25 2.25 0 0 1-2.25-2.25v-.75" />
        </svg>
      </div>
      <p className="text-sm font-semibold text-gray-900 mb-1">No projects yet</p>
      <p className="text-xs text-gray-400 mb-6 max-w-xs">
        Create your first project to start organising test cases and running the agent.
      </p>
      <Button variant="primary" onClick={onCreate}>
        Create project
      </Button>
    </div>
  )
}

// ── Project form (shared by create + edit modals) ─────────────────────────────

function ProjectForm({ initial = {}, onSubmit, loading, error, submitLabel = 'Save' }) {
  const [name, setName]        = useState(initial.name        ?? '')
  const [description, setDesc] = useState(initial.description ?? '')
  const [nameErr, setNameErr]  = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!name.trim()) { setNameErr('Name is required'); return }
    onSubmit({ name: name.trim(), description: description.trim() || null })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Name"
        placeholder="e.g. Checkout Flow"
        value={name}
        onChange={(e) => { setName(e.target.value); setNameErr('') }}
        error={nameErr}
        autoFocus
      />
      <Textarea
        label="Description (optional)"
        placeholder="What does this project test?"
        value={description}
        onChange={(e) => setDesc(e.target.value)}
      />
      {error && (
        <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-md px-3 py-2">
          {error}
        </p>
      )}
      <div className="flex justify-end gap-2 pt-1">
        <Button type="submit" variant="primary" loading={loading}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

// ── Delete confirmation modal ─────────────────────────────────────────────────

function DeleteModal({ project, onConfirm, onClose, loading, error }) {
  return (
    <Modal open={!!project} onClose={onClose} title="Delete project">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Are you sure you want to delete{' '}
          <span className="font-semibold text-gray-900">{project?.name}</span>?
          This will permanently remove all test cases and run history.
        </p>
        {error && (
          <p className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-md px-3 py-2">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button variant="danger" onClick={onConfirm} loading={loading}>
            Delete
          </Button>
        </div>
      </div>
    </Modal>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ProjectsPage() {
  // modal state to open modal to make crud in project
  const [showCreate,   setShowCreate]   = useState(false)
  const [editProject,  setEditProject]  = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  // data
  const [projects, setProjects] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isError, setIsError] = useState(false)
  const [reloadTick, setReloadTick] = useState(0)


  // depandancy to reload projects after create/edit/delete
  const reloadProjects = useCallback(() => {
    setReloadTick((tick) => tick + 1)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadProjects() {
      setIsLoading(true)
      setIsError(false)
      try {
        const response = await listProjects()
        if (!cancelled) {
          setProjects(response?.items ?? [])
        }
      } catch {
        if (!cancelled) {
          setIsError(true)
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    loadProjects()

    return () => {
      cancelled = true
    }
  }, [reloadTick])

  // mutations for create/edit/delete project
  const createMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      reloadProjects()
      setShowCreate(false)
    },
  })

  const editMutation = useMutation({
    mutationFn: ({ id, data }) => updateProject(id, data),
    onSuccess: () => {
      reloadProjects()
      setEditProject(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => deleteProject(id),
    onSuccess: () => {
      reloadProjects()
      setDeleteTarget(null)
    },
  })

  // reset mutation errors when modals re-open
  const openCreate = () => { createMutation.reset(); setShowCreate(true) }
  const openEdit   = (p) => { editMutation.reset();  setEditProject(p)   }
  const openDelete = (p) => { deleteMutation.reset(); setDeleteTarget(p) }

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Top bar */}
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto max-w-6xl px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="block w-2 h-2 rounded-full bg-accent" />
            <span className="text-sm font-semibold text-gray-900">Web Agent</span>
          </div>
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-medium text-gray-500">Projects</h1>
            <Button variant="primary" size="sm" onClick={openCreate}>
              + New project
            </Button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-6xl px-6 py-8">

        {/* Loading skeletons */}
        {isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        )}

        {/* Fetch error */}
        {isError && (
          <div className="flex items-center gap-3 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600">
            <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-8-5a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0v-4.5A.75.75 0 0 1 10 5Zm0 10a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" clipRule="evenodd"/>
            </svg>
            Could not load projects. Is the server running on port 8000?
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !isError && projects.length === 0 && (
          <EmptyState onCreate={openCreate} />
        )}

        {/* Grid */}
        {!isLoading && projects.length > 0 && (
          <>
            <p className="text-xs text-gray-400 mb-5">
              {projects.length} {projects.length === 1 ? 'project' : 'projects'}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {projects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onEdit={openEdit}
                  onDelete={openDelete}
                />
              ))}
            </div>
          </>
        )}
      </main>

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New project">
        <ProjectForm
          submitLabel="Create project"
          loading={createMutation.isPending}
          error={createMutation.error?.message}
          onSubmit={(data) => createMutation.mutate(data)}
        />
      </Modal>

      {/* Edit modal */}
      <Modal open={!!editProject} onClose={() => setEditProject(null)} title="Edit project">
        {editProject && (
          <ProjectForm
            key={editProject.id}
            initial={editProject}
            submitLabel="Save changes"
            loading={editMutation.isPending}
            error={editMutation.error?.message}
            onSubmit={(data) => editMutation.mutate({ id: editProject.id, data })}
          />
        )}
      </Modal>

      {/* Delete modal */}
      <DeleteModal
        project={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        loading={deleteMutation.isPending}
        error={deleteMutation.error?.message}
        onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
      />
    </div>
  )
}
