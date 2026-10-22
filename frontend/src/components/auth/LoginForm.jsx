// login screen, shown by App.jsx to anyone who isn't logged in (all roles use the same form).
// accepts a username or an email. on success AuthContext stores the JWT and App switches to MainLayout.
import { useState } from 'react';
import { Alert, Box, Button, Divider, Link, Paper, TextField, Typography} from '@mui/material';
import { useAuth } from '../../context/AuthContext.jsx';

{/**
 * Login form. Uses login() from the global AuthContext (POST /auth/token, OAuth2 password form).
 *  - onShowRegister: switches App to the RegisterForm (first-time account setup)
 * shows an info banner when the previous session expired (token exp reached or the API returned 401)
 */}
function LoginForm({onShowRegister}){
    const {login, sessionExpired} = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);


    {/** form submission handler function. on success there's nothing to do here: App re-renders into MainLayout */}
    const handleSubmit = async (event) => {
        event.preventDefault();
        setError(null);
        try{
            await login(username.trim(), password);
        } catch {
            // one generic message, like the backend's 401 (which doesn't say whether the user exists or
            // just hasn't registered yet). note this also covers network/server errors
            setError('Incorrect username or password');
        }
    };

    return (
        <Box sx={{display: 'flex', justifyContent: 'center', mt: 8, px: 2}}>
            <Paper component="form" onSubmit={handleSubmit} variant="outlined" sx={{ p: 4, width: '100%', maxWidth: 360}}>
                <Typography variant="h6" gutterBottom>
                    Acme Login
                </Typography>
                {/* the expiry notice gives way to the login error once the user has tried again */}
                {sessionExpired && !error && (
                    <Alert severity="info" sx={{mb: 2}}>Your session has expired. Please log in again.</Alert>
                )}
                {error && (
                    <Alert severity="error" sx={{mb: 2}}>
                        {error}. If you haven't set up your account yet, use the link below first.
                    </Alert>
                )}
                <TextField
                    label="Username or email"
                    fullWidth
                    margin="normal"
                    autoComplete="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    />
                <TextField
                    label="Password"
                    type="password"
                    fullWidth
                    margin="normal"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    />
                    <Button type="submit" variant="contained" fullWidth sx={{ mt: 2}}>
                        Log In
                    </Button>
                <Divider sx={{my: 3}} />
                <Typography variant="body2" color="text.secondary" align="center">
                    First day?{' '}
                    <Link component="button" type="button" variant="body2" onClick={onShowRegister}>
                        Set up your account
                    </Link>
                </Typography>
            </Paper>
        </Box>
    );
}

export default LoginForm;
