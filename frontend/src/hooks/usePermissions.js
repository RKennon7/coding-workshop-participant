// the hook components use for RBAC checks: combines the logged in user's role (from AuthContext)
// with the role -> permission map in auth/permissions.js. UI gating only, the backend enforces it
import { useCallback } from 'react';
import { useAuth } from '../context/AuthContext.jsx';
import { hasPermission } from '../auth/permissions.js';

/**
 * exposes permission checks for the logged in user
 *   can('incidents:delete')            -> true if the user has that permission
 *   canAny(['incidents:update', ...])  -> true if the user has at least one of them
 * pass PERMISSIONS.* constants rather than raw strings. role is the JWT's role claim (one of ROLES).
 * can/canAny keep the same identity until the role changes, so they're safe in effect/memo deps
 * @returns {{role: string | undefined, can: (permission: string) => boolean, canAny: (permissions: string[]) => boolean}}
 */
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
