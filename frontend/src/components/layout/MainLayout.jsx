import { useState } from 'react';
import { Box, Container, Tab, Tabs } from '@mui/material';
import AppHeader from './AppHeader.jsx';
import { NAV_SECTIONS } from './navigation.js';
import { usePermissions } from '../../hooks/usePermissions.js';

{/** header + tab menu + the active section's page, limited to sections the user can see */}
function MainLayout() {
    const {can} = usePermissions();
    const sections = NAV_SECTIONS.filter((section) => can(section.permission));

    const [activeId, setActiveId] = useState(sections[0]?.id);
    // fall back to the first tab if the active one isn't available to this user
    const active = sections.find((section) => section.id === activeId) ?? sections[0];
    const ActivePage = active?.component;

    return (
        <Box sx={{minHeight: '100vh', bgcolor: 'background.default'}}>
            <AppHeader />
            <Box sx={{borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper'}}>
                <Container maxWidth="xl">
                    <Tabs
                        value={active?.id ?? false}
                        onChange={(_, id) => setActiveId(id)}
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
                {ActivePage && <ActivePage />}
            </Container>
        </Box>
    );
}

export default MainLayout;
