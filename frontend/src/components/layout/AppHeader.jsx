import { AppBar, Box, Button, Chip, IconButton, Toolbar, Tooltip, Typography } from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import { useAuth } from '../../context/AuthContext.jsx';
import ColorModeToggle from './ColorModeToggle.jsx';

{/** top bar shown on every authenticated page: app title, current user + role, logout. compacts on phones */}
function AppHeader(){
    const {user, profile, logout} = useAuth();

    return (
        <AppBar position="static">
            <Toolbar sx={{gap: 1}}>
                <Typography variant="h6" component="div" noWrap sx={{flexGrow: 1}}>
                    Acme.inc
                </Typography>
                {user && (
                    <Box sx={{display: 'flex', alignItems: 'center', gap: 1, minWidth: 0}}>
                        <Typography variant="body1" noWrap sx={{display: {xs: 'none', sm: 'block'}}}>{user.sub}</Typography>
                        <Chip
                            label={user.role}
                            size="small"
                            variant="outlined"
                            sx={{color: 'inherit', borderColor: 'currentColor'}}
                        />
                        {profile?.facility_name && (
                            <Typography variant="body2" color="text.secondary" noWrap sx={{display: {xs: 'none', md: 'block'}}}>
                                {profile.facility_name}
                            </Typography>
                        )}
                    </Box>
                )}
                <Button color="inherit" startIcon={<LogoutIcon />} onClick={logout} sx={{display: {xs: 'none', sm: 'inline-flex'}}}>
                    Log Out
                </Button>
                <Tooltip title="Log out">
                    <IconButton color="inherit" onClick={logout} aria-label="Log out" sx={{display: {xs: 'inline-flex', sm: 'none'}}}>
                        <LogoutIcon />
                    </IconButton>
                </Tooltip>
                <ColorModeToggle />
            </Toolbar>
        </AppBar>
    );
}

export default AppHeader;
