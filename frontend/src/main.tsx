import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import GitHubCallback from './pages/GitHubCallback.tsx'

const root = document.getElementById('root')!

// Check if this is the GitHub callback route
const isGithubCallback = window.location.pathname === '/github/callback'

createRoot(root).render(
  <StrictMode>
    {isGithubCallback ? <GitHubCallback /> : <App />}
  </StrictMode>,
)
