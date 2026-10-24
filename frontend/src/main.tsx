import '@fontsource-variable/inter'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import './index.css'
import { CasePage } from './pages/CasePage'
import { LandingPage } from './pages/LandingPage'
import { CaseProvider } from './state/caseState'

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/case', element: <CasePage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CaseProvider>
      <RouterProvider router={router} />
    </CaseProvider>
  </StrictMode>,
)
