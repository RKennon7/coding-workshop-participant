// the main tab menu's definition. MainLayout renders a tab per section the user's role allows
// and mounts the section's component as the active page. ids are what navigate() takes
// (see context/NavigationContext.jsx)
import DashboardIcon from '@mui/icons-material/SpaceDashboard';
import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber';
import ApartmentIcon from '@mui/icons-material/Apartment';
import EngineeringIcon from '@mui/icons-material/Engineering';
import GroupIcon from '@mui/icons-material/Group';
import { PERMISSIONS } from '../../auth/permissions.js';
import DashboardPage from '../../pages/DashboardPage.jsx';
import IncidentsPage from '../../pages/IncidentsPage.jsx';
import FacilitiesPage from '../../pages/FacilitiesPage.jsx';
import EngineersPage from '../../pages/EngineersPage.jsx';
import UsersPage from '../../pages/UsersPage.jsx';

// main menu tabs, in display order. a tab only shows if the user has its permission
// (see ROLE_PERMISSIONS in auth/permissions.js: e.g. Users is admin only). the first visible tab is
// where a user lands after login
export const NAV_SECTIONS = [
    {id: 'analytics', label: 'Dashboard', icon: DashboardIcon, permission: PERMISSIONS.ANALYTICS_VIEW, component: DashboardPage},
    {id: 'incidents', label: 'Incidents', icon: ConfirmationNumberIcon, permission: PERMISSIONS.INCIDENTS_VIEW, component: IncidentsPage},
    {id: 'facilities', label: 'Facilities', icon: ApartmentIcon, permission: PERMISSIONS.FACILITIES_VIEW, component: FacilitiesPage},
    {id: 'engineers', label: 'Engineers', icon: EngineeringIcon, permission: PERMISSIONS.ENGINEERS_VIEW, component: EngineersPage},
    {id: 'users', label: 'Users', icon: GroupIcon, permission: PERMISSIONS.USERS_VIEW, component: UsersPage},
];
