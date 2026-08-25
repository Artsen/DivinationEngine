import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Link, Navigate, RouterProvider } from 'react-router-dom'
import { App } from './App'
import { NewReadingPage } from './pages/NewReadingPage'
import { ReadingPage } from './pages/ReadingPage'
import { ReadingsPage } from './pages/ReadingsPage'
import { SpreadsPage } from './pages/SpreadsPage'
import './styles.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 10_000, retry: 1 } },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/readings" replace /> },
      { path: 'readings', element: <ReadingsPage /> },
      { path: 'readings/new', element: <NewReadingPage /> },
      { path: 'readings/:id', element: <ReadingPage /> },
      { path: 'spreads', element: <SpreadsPage /> },
      { path: '*', element: <main className="page"><h1>Page not found</h1><Link to="/readings">Return to readings</Link></main> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode><QueryClientProvider client={queryClient}><RouterProvider router={router} /></QueryClientProvider></StrictMode>,
)
