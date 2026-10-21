import InsightsIcon from '@mui/icons-material/Insights';
import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber';
import ApartmentIcon from '@mui/icons-material/Apartment';
import EngineeringIcon from '@mui/icons-material/Engineering';
import GroupIcon from '@mui/icons-material/Group';
import { PERMISSIONS } from '../../auth/permissions.js';
import AnalyticsPage from '../../pages/AnalyticsPage.jsx';
import IncidentsPage from '../../pages/IncidentsPage.jsx';
import FacilitiesPage from '../../pages/FacilitiesPage.jsx';
import EngineersPage from '../../pages/EngineersPage.jsx';
import UsersPage from '../../pages/UsersPage.jsx';

// main menu tabs, in display order. a tab only shows if the user has its permission
export const NAV_SECTIONS = [
    {id: 'analytics', label: 'Analytics', icon: InsightsIcon, permission: PERMISSIONS.ANALYTICS_VIEW, component: AnalyticsPage},
    {id: 'incidents', label: 'Incidents', icon: ConfirmationNumberIcon, permission: PERMISSIONS.INCIDENTS_VIEW, component: IncidentsPage},
    {id: 'facilities', label: 'Facilities', icon: ApartmentIcon, permission: PERMISSIONS.FACILITIES_VIEW, component: FacilitiesPage},
    {id: 'engineers', label: 'Engineers', icon: EngineeringIcon, permission: PERMISSIONS.ENGINEERS_VIEW, component: EngineersPage},
    {id: 'users', label: 'Users', icon: GroupIcon, permission: PERMISSIONS.USERS_VIEW, component: UsersPage},
];
