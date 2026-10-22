/**
 * Root component. Wraps everything in AuthProvider and picks the top-level screen:
 * logged out -> LoginForm / RegisterForm, logged in -> MainLayout (header, tabs and pages).
 * There is no URL router: once logged in, MainLayout switches pages via NavigationContext.
 */
import { useState } from 'react';
import LoginForm from './components/auth/LoginForm';
import RegisterForm from './components/auth/RegisterForm';
import MainLayout from './components/layout/MainLayout';
import { AuthProvider, useAuth } from './context/AuthContext';

// split out from App because useAuth() only works inside AuthProvider
function AppContent() {
  const {isAuthenticated} = useAuth();
  // logged out users see the login screen, or first-time account setup
  const [showRegister, setShowRegister] = useState(false);

  if (isAuthenticated) {
    return <MainLayout />;
  }
  return showRegister
    ? <RegisterForm onShowLogin={() => setShowRegister(false)} />
    : <LoginForm onShowRegister={() => setShowRegister(true)} />;
}

/** App shell: provides auth state to the whole tree. Rendered by main.jsx. */
function App() {
  return (
    <AuthProvider>
      <AppContent/>
    </AuthProvider>
  )
}

export default App
