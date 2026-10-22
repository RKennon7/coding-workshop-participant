// "first day" account setup screen, reached from the link on LoginForm (logged-out users of any role).
// registration is invite-only: a Facility Admin creates the user (email, role, campus) first, and here
// the new user just claims that account by choosing a password.
import { useState } from 'react';
import { Alert, Box, Button, Divider, Link, Paper, TextField, Typography } from '@mui/material';
import { useAuth } from '../../context/AuthContext.jsx';
import { getErrorMessage } from '../../hooks/useResource.js';

// mirrors NewPassword (min_length=8) in backend/v1/app/schemas/common.py. the backend also caps passwords
// at 72 bytes (bcrypt's limit), that one is only checked server side
const MIN_PASSWORD_LENGTH = 8;

{/**
 * First-time setup for an account a Facility Admin already created (POST /auth/register).
 * the user proves nothing beyond knowing the invited email, then picks their own password.
 * on success the backend returns a token, so they land straight in the app.
 *  - onShowLogin: switches App back to the LoginForm
 * the backend rejects emails outside @acme.inc, emails with no invited account, and accounts that
 * are already registered; those messages are shown as-is in the error banner.
 */}
function RegisterForm({onShowLogin}) {
    const {register} = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);

    // only flag these once the user has typed something, so an empty form doesn't start out red
    const passwordTooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH;
    const mismatch = confirm.length > 0 && confirm !== password;

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (password.length < MIN_PASSWORD_LENGTH || password !== confirm) {
            return;
        }
        setSaving(true);
        setError(null);
        try {
            // the email is lowercased and domain-checked by the backend (AcmeEmail in schemas/common.py).
            // success logs the user in and App unmounts this form, so saving is only reset on failure
            await register(email.trim(), password);
        } catch (err) {
            setError(getErrorMessage(err));
            setSaving(false);
        }
    };

    return (
        <Box sx={{display: 'flex', justifyContent: 'center', mt: 8, px: 2}}>
            <Paper component="form" onSubmit={handleSubmit} variant="outlined" sx={{p: 4, width: '100%', maxWidth: 420}}>
                <Typography variant="h6" gutterBottom>
                    Set up your account
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{mb: 1}}>
                    Your Facility Admin creates your account and gives you the <strong>@acme.inc email
                    address</strong> it was set up with (and your username).
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{mb: 2}}>
                    Enter that email below and choose a password. You only do this once: after that,
                    log in with your username or email and the password you chose here.
                </Typography>

                {error && <Alert severity="error" sx={{mb: 2}}>{error}</Alert>}

                <TextField
                    label="Work email"
                    type="email"
                    placeholder="first.last@acme.inc"
                    required
                    fullWidth
                    margin="normal"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    disabled={saving}
                />
                <TextField
                    label="New password"
                    type="password"
                    required
                    fullWidth
                    margin="normal"
                    autoComplete="new-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    error={passwordTooShort}
                    helperText={`At least ${MIN_PASSWORD_LENGTH} characters`}
                    disabled={saving}
                />
                <TextField
                    label="Confirm password"
                    type="password"
                    required
                    fullWidth
                    margin="normal"
                    autoComplete="new-password"
                    value={confirm}
                    onChange={(event) => setConfirm(event.target.value)}
                    error={mismatch}
                    helperText={mismatch ? "Passwords don't match" : ' '}
                    disabled={saving}
                />
                <Button
                    type="submit"
                    variant="contained"
                    fullWidth
                    sx={{mt: 1}}
                    disabled={saving || password.length < MIN_PASSWORD_LENGTH || password !== confirm}
                >
                    Create Password &amp; Log In
                </Button>

                <Divider sx={{my: 3}} />
                <Typography variant="body2" color="text.secondary" align="center">
                    Already set up?{' '}
                    <Link component="button" type="button" variant="body2" onClick={onShowLogin}>
                        Back to login
                    </Link>
                </Typography>
                <Typography variant="caption" color="text.secondary" component="p" align="center" sx={{mt: 1}}>
                    Don't have an account email yet? Contact your Facility Admin.
                </Typography>
            </Paper>
        </Box>
    );
}

export default RegisterForm;
