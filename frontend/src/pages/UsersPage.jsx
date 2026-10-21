import { useMemo } from 'react';
import ResourceView from '../components/common/ResourceView.jsx';
import { PERMISSIONS } from '../auth/permissions.js';
import { usersService } from '../services/index.js';
import { USER_ROLES, toOptions } from '../constants/enums.js';

const columns = [
    {field: 'id', headerName: 'ID', width: 70},
    {field: 'username', headerName: 'Username', flex: 1, minWidth: 150},
    {field: 'email', headerName: 'Email', flex: 1, minWidth: 220},
    {field: 'role', headerName: 'Role', width: 150, type: 'singleSelect', valueOptions: USER_ROLES},
    {field: 'is_active', headerName: 'Active', width: 90, type: 'boolean'},
    {field: 'is_registered', headerName: 'Registered', width: 110, type: 'boolean'},
];

function UsersPage() {
    const fields = useMemo(() => [
        {name: 'username', label: 'Username', required: true},
        {name: 'email', label: 'Email', type: 'email', required: true, helperText: 'Must be an @acme.inc address'},
        {name: 'role', label: 'Role', type: 'select', options: toOptions(USER_ROLES), defaultValue: 'Employee', required: true},
        {name: 'password', label: 'Password', type: 'password', createOnly: true,
            helperText: 'Optional. Leave blank to invite the user: they set their own password when they register'},
        {name: 'is_active', label: 'Active', type: 'checkbox', defaultValue: true, hideOnCreate: true},
    ], []);

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
