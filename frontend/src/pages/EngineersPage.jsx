/**
 * The Engineers tab: engineer profiles (specialty, availability, max open tickets) used for
 * assignment and workload balancing. Admins manage profiles; engineers can view the roster and
 * update their own phone + availability (backend: ENGINEER_SELF_FIELDS in routers/engineers.py).
 */
import { useMemo } from 'react';
import ResourceView from '../components/common/ResourceView.jsx';
import { PERMISSIONS, ROLES } from '../auth/permissions.js';
import { useAuth } from '../context/AuthContext.jsx';
import { usePermissions } from '../hooks/usePermissions.js';
import { toLabelMap, useOptions } from '../hooks/useResource.js';
import { engineersService, facilitiesService, usersService } from '../services/index.js';
import { INCIDENT_CATEGORIES, toOptions } from '../constants/enums.js';

/** Engineers grid + form on top of ResourceView. Visible to roles with engineers:view. */
function EngineersPage() {
    const {user} = useAuth();
    const {can} = usePermissions();
    const canManage = can(PERMISSIONS.ENGINEERS_MANAGE);

    // a profile links to a user account with the Engineer role (the users list is admin only)
    const allUsers = useOptions(usersService, (u) => `${u.username} (${u.email})`, {enabled: can(PERMISSIONS.USERS_VIEW)});
    const engineerUsers = useMemo(() => allUsers.filter((o) => o.row.role === ROLES.ENGINEER), [allUsers]);
    const facilityOptions = useOptions(facilitiesService, (f) => f.name);

    const columns = useMemo(() => {
        const users = toLabelMap(allUsers);
        const facilities = toLabelMap(facilityOptions);
        return [
            {field: 'id', headerName: 'ID', width: 70},
            {field: 'display_name', headerName: 'Name', flex: 1, minWidth: 160},
            {field: 'user_id', headerName: 'User', flex: 1, minWidth: 200, valueGetter: (value) => users[value] ?? value},
            // from the linked user account: change it on the Users page
            {field: 'facility_id', headerName: 'Facility', flex: 1, minWidth: 150, valueGetter: (value) => facilities[value] ?? value},
            {field: 'specialty', headerName: 'Specialty', width: 160, type: 'singleSelect', valueOptions: INCIDENT_CATEGORIES},
            {field: 'phone', headerName: 'Phone', width: 140},
            {field: 'is_available', headerName: 'Available', width: 100, type: 'boolean'},
            {field: 'max_open_tickets', headerName: 'Max Open Tickets', width: 150, type: 'number'},
        ];
    }, [allUsers, facilityOptions]);

    // admins edit everything; engineers can only keep their own phone + availability current
    const fields = useMemo(() => {
        const adminOrSelf = (row) => canManage || row.user_id === user?.uid;
        return [
            // the linked account is chosen once at creation, it can't be moved to another user
            {name: 'user_id', label: 'User Account', type: 'select', options: engineerUsers, required: true,
                editableBy: [], helperText: 'Only users with the Engineer role are listed'},
            {name: 'display_name', label: 'Display Name', required: true},
            {name: 'phone', label: 'Phone', editableBy: adminOrSelf},
            {name: 'specialty', label: 'Specialty', type: 'select', options: toOptions(INCIDENT_CATEGORIES)},
            {name: 'max_open_tickets', label: 'Max Open Tickets', type: 'number', defaultValue: 10, required: true},
            {name: 'is_available', label: 'Available for assignments', type: 'checkbox', defaultValue: true, editableBy: adminOrSelf},
        ];
    }, [engineerUsers, canManage, user]);

    return (
        <ResourceView
            title="Engineers"
            singular="Engineer"
            service={engineersService}
            columns={columns}
            fields={fields}
            // engineers lack ENGINEERS_MANAGE, but the editableBy row rules above still let them edit their own row
            permissions={{
                create: PERMISSIONS.ENGINEERS_MANAGE,
                update: PERMISSIONS.ENGINEERS_MANAGE,
                delete: PERMISSIONS.ENGINEERS_MANAGE,
            }}
            getRowLabel={(row) => row.display_name}
        />
    );
}

export default EngineersPage;
