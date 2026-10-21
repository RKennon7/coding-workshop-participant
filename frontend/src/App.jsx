import { useState } from 'react';
import LoginForm from './components/auth/LoginForm';
import RegisterForm from './components/auth/RegisterForm';
import MainLayout from './components/layout/MainLayout';
import { AuthProvider, useAuth } from './context/AuthContext';

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

function App() {
  return (
    <AuthProvider>
      <AppContent/>
    </AuthProvider>
  )
}

export default App
