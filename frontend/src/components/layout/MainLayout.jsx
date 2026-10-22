import { useCallback, useMemo, useState } from 'react';
import { Alert, Box, Container, Tab, Tabs } from '@mui/material';
import AppHeader from './AppHeader.jsx';
import { NAV_SECTIONS } from './navigation.js';
import { NavigationContext } from '../../context/NavigationContext.jsx';
import { usePermissions } from '../../hooks/usePermissions.js';
import { useAuth } from '../../context/AuthContext.jsx';
import { ROLES } from '../../auth/permissions.js';

{/** header + tab menu + the active section's page, limited to sections the user can see */}
function MainLayout() {
    const {can, role} = usePermissions();
    const {profile} = useAuth();
    // e.g. their facility was deleted: they see no locations until an admin reassigns them
    const needsFacility = role !== ROLES.FACILITY_ADMIN && profile && profile.facility_id == null;
    const sections = NAV_SECTIONS.filter((section) => can(section.permission));

    // params are handed to the page (e.g. filters from a dashboard click). visit counts every navigation,
    // so the page remounts and picks up new params even when it's already the active tab
    const [nav, setNav] = useState({id: sections[0]?.id, params: null, visit: 0});
    const navigate = useCallback((id, params = null) => {
        setNav((prev) => ({id, params, visit: prev.visit + 1}));
        window.scrollTo({top: 0});
    }, []);
    const navigation = useMemo(() => ({navigate}), [navigate]);

    // fall back to the first tab if the active one isn't available to this user
    const active = sections.find((section) => section.id === nav.id) ?? sections[0];
    const ActivePage = active?.component;

    return (
        <NavigationContext.Provider value={navigation}>
            <Box sx={{minHeight: '100vh', bgcolor: 'background.default'}}>
                <AppHeader />
                <Box sx={{borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper'}}>
                    <Container maxWidth="xl">
                        <Tabs
                            value={active?.id ?? false}
                            onChange={(_, id) => navigate(id)}
                            variant="scrollable"
                            scrollButtons="auto"
                            allowScrollButtonsMobile
                            aria-label="Main sections"
                        >
                            {sections.map(({id, label, icon: Icon}) => (
                                <Tab key={id} value={id} label={label} icon={<Icon fontSize="small" />} iconPosition="start" sx={{minHeight: 56}} />
                            ))}
                        </Tabs>
                    </Container>
                </Box>
                <Container maxWidth="xl" component="main" sx={{py: 3}}>
                    {needsFacility && (
                        <Alert severity="warning" sx={{mb: 2}}>
                            Your account isn't assigned to a facility yet, so there are no locations to report issues at.
                            Please contact a Facility Admin to be assigned to one.
                        </Alert>
                    )}
                    {ActivePage && <ActivePage key={nav.visit} params={active.id === nav.id ? nav.params : null} />}
                </Container>
            </Box>
        </NavigationContext.Provider>
    );
}

export default MainLayout;
