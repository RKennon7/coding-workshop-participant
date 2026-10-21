import { usePermissions } from '../../hooks/usePermissions.js';

{/**
 * renders children only if the user has the permission (or any of a list of permissions)
 *   <Can permission={PERMISSIONS.USERS_MANAGE}><Button>Add user</Button></Can>
 *   <Can permission={[PERMISSIONS.INCIDENTS_UPDATE, PERMISSIONS.INCIDENTS_UPDATE_STATUS]} fallback={<ReadOnly />}>
 */}
function Can({permission, fallback = null, children}) {
    const {can, canAny} = usePermissions();
    const allowed = Array.isArray(permission) ? canAny(permission) : can(permission);
    return allowed ? children : fallback;
}

export default Can;
