import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Data is considered fresh for 30 s — avoids redundant refetches when
      // the user opens the same project twice in quick succession.
      staleTime: 30_000,

      // Retry once before surfacing an error to the component.
      retry: 1,

      // Don't refetch just because the user switched browser tabs.
      // The run history refreshes via explicit cache invalidation after
      // a run completes, not via background polling.
      refetchOnWindowFocus: false,
    },
    mutations: {
      // Surface mutation errors via the error state; don't retry.
      retry: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)