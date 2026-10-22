import { useMemo } from 'react';
import { Chip } from '@mui/material';
import ResourceView from '../components/common/ResourceView.jsx';
import { PERMISSIONS, ROLES } from '../auth/permissions.js';
import { toLabelMap, useOptions } from '../hooks/useResource.js';
import { facilitiesService, usersService } from '../services/index.js';
import { USER_ROLES, toOptions } from '../constants/enums.js';

function UsersPage() {
    const facilityOptions = useOptions(facilitiesService, (f) => f.name);

    const columns = useMemo(() => {
        const facilities = toLabelMap(facilityOptions);
        return [
            {field: 'id', headerName: 'ID', width: 70},
            {field: 'username', headerName: 'Username', flex: 1, minWidth: 150},
            {field: 'email', headerName: 'Email', flex: 1, minWidth: 220},
            {field: 'role', headerName: 'Role', width: 150, type: 'singleSelect', valueOptions: USER_ROLES},
            {
                field: 'facility_id', headerName: 'Facility', flex: 1, minWidth: 160,
                valueGetter: (value, row) => (value ? facilities[value] ?? `#${value}` : row.role === ROLES.FACILITY_ADMIN ? 'All facilities' : 'Needs facility'),
                // engineers/employees left without one (e.g. their facility was deleted) stand out until reassigned
                renderCell: ({value, row}) => (row.facility_id == null && row.role !== ROLES.FACILITY_ADMIN
                    ? <Chip size="small" color="warning" variant="outlined" label={value} />
                    : value),
            },
            {field: 'is_active', headerName: 'Active', width: 90, type: 'boolean'},
            {field: 'is_registered', headerName: 'Registered', width: 110, type: 'boolean'},
        ];
    }, [facilityOptions]);

    const fields = useMemo(() => [
        {name: 'username', label: 'Username', required: true},
        {name: 'email', label: 'Email', type: 'email', required: true, helperText: 'Must be an @acme.inc address'},
        {name: 'role', label: 'Role', type: 'select', options: toOptions(USER_ROLES), defaultValue: 'Employee', required: true},
        {
            // engineers/employees only see their own facility. for admins it's just where their filters start
            name: 'facility_id', label: 'Facility', type: 'select', options: facilityOptions,
            required: (values) => values.role !== ROLES.FACILITY_ADMIN,
            helperText: 'Engineers and employees only see this facility. Optional for admins: their dashboard starts on it',
        },
        {name: 'password', label: 'Password', type: 'password', createOnly: true,
            helperText: 'Optional. Leave blank to invite the user: they set their own password when they register'},
        {name: 'is_active', label: 'Active', type: 'checkbox', defaultValue: true, hideOnCreate: true},
    ], [facilityOptions]);

    return (
        <ResourceView
            title="Users"
            singular="User"
            service={usersService}
            columns={columns}
            fields={fields}
            permissions={{
                create: PERMISSIONS.USERS_MANAGE,
                update: PERMISSIONS.USERS_MANAGE,
                delete: PERMISSIONS.USERS_MANAGE,
            }}
            getRowLabel={(row) => row.username}
        />
    );
}

export default UsersPage;
