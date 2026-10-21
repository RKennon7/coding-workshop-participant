import { AppBar, Box, Button, Chip, Toolbar, Typography } from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import { useAuth } from '../../context/AuthContext.jsx';
import ColorModeToggle from './ColorModeToggle.jsx';

{/** top bar shown on every authenticated page: app title, current user + role, logout */}
function AppHeader(){
    const {user, logout} = useAuth();

    return (
        <AppBar position="static">
            <Toolbar>
                <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                    Acme.inc
                </Typography>
                {user && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 2 }}>
                        <Typography variant="body1">{user.sub}</Typography>
                        <Chip
                            label={user.role}
                            size="small"
                            variant="outlined"
                            sx={{ color: 'inherit', borderColor: 'currentColor' }}
                        />
                    </Box>
                )}
                <Button color="inherit" startIcon={<LogoutIcon />} onClick={logout}>
                    Log Out
                </Button>
                <ColorModeToggle />
            </Toolbar>
        </AppBar>
    );
}

export default AppHeader;
