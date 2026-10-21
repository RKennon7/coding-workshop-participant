import { useCallback } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { hasPermission } from '../auth/permissions.js';

// exposes permission checks for the logged in user
//   can('incidents:delete')            -> true if the user has that permission
//   canAny(['incidents:update', ...])  -> true if the user has at least one of them
export function usePermissions() {
    const {user} = useAuth();
    const role = user?.role;

    const can = useCallback((permission) => hasPermission(role, permission), [role]);
    const canAny = useCallback(
        (permissions) => permissions.some((permission) => hasPermission(role, permission)),
        [role]
    );

    return {role, can, canAny};
}
