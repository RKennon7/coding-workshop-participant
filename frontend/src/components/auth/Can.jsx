// declarative permission gate for JSX, e.g. the "add note" box in IncidentNotes.
// works for every role: it checks the logged-in user's role against the map in auth/permissions.js.
// hiding UI is only for UX, the backend enforces the same rules on every request.
import { usePermissions } from '../../hooks/usePermissions.js';

{/**
 * Renders children only if the user has the permission (or any of a list of permissions).
 *  - permission: one permission string, or an array (passes if the user has at least one)
 *  - fallback: rendered instead when the check fails (default: nothing)
 *   <Can permission={PERMISSIONS.USERS_MANAGE}><Button>Add user</Button></Can>
 *   <Can permission={[PERMISSIONS.INCIDENTS_UPDATE, PERMISSIONS.INCIDENTS_UPDATE_STATUS]} fallback={<ReadOnly />}>
 */}
function Can({permission, fallback = null, children}) {
    const {can, canAny} = usePermissions();
    const allowed = Array.isArray(permission) ? canAny(permission) : can(permission);
    return allowed ? children : fallback;
}

export default Can;
