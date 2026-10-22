/**
 * Vite entry point (loaded by index.html). Mounts <App /> into #root.
 *
 * ColorModeProvider sits outermost so the MUI theme (light/dark) and CssBaseline apply to
 * every screen, including the login/register forms shown before AuthProvider has a user.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ColorModeProvider } from './context/ColorModeContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ColorModeProvider>
      <App />
    </ColorModeProvider>
  </StrictMode>,
)
