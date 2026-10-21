import { Typography } from '@mui/material';

import LoginForm from './components/auth/LoginForm';
import AppHeader from './components/layout/AppHeader';
import { AuthProvider, useAuth } from './context/AuthContext';

function Dashboard(){
  return (
    <>
      <Typography>hello</Typography>
    </>
  )

}

function AppContent() {
  const {isAuthenticated} = useAuth();
  if (!isAuthenticated) {
    return <LoginForm />;
  }
  return (
    <>
      <AppHeader />
      <Dashboard />
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent/>
    </AuthProvider>
  )
}

export default App
