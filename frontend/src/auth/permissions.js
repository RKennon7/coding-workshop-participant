/**
 * Role-based permissions. Mirrors UserRole in backend/v1/app/models/user.py.
 *
 * Components check permissions (what a user can do) instead of roles (who they are),
 * so changing what a role is allowed to do only means editing the map below.
 * The backend still has to enforce these, the frontend only hides what a user can't use.
 *
 * Components normally check these through hooks/usePermissions.js (which reads the role from the
 * logged in user's JWT); components/layout/navigation.js uses them to decide which tabs show.
 * Per-ticket rules (e.g. "only the assigned engineer") live in incidentRules.js instead.
 */

// values match the `role` claim in the JWT and the role field returned by /users
export const ROLES = {
    FACILITY_ADMIN: 'Facility Admin',
    ENGINEER: 'Engineer',
    EMPLOYEE: 'Employee',
};

// permission strings are "<resource>:<action>"
export const PERMISSIONS = {
    ANALYTICS_VIEW: 'analytics:view',

    INCIDENTS_VIEW: 'incidents:view',
    INCIDENTS_CREATE: 'incidents:create',
    INCIDENTS_UPDATE: 'incidents:update',               // edit every field
    INCIDENTS_UPDATE_STATUS: 'incidents:update_status', // status + blocked reason only
    INCIDENTS_ESCALATE: 'incidents:escalate',           // request escalation / priority
    INCIDENTS_DELETE: 'incidents:delete',
    INCIDENT_NOTES_CREATE: 'incident_notes:create',
    INCIDENT_NOTES_INTERNAL: 'incident_notes:internal', // see + write engineer/admin-only notes

    FACILITIES_VIEW: 'facilities:view',
    FACILITIES_MANAGE: 'facilities:manage',

    ENGINEERS_VIEW: 'engineers:view',
    ENGINEERS_MANAGE: 'engineers:manage',

    USERS_VIEW: 'users:view',
    USERS_MANAGE: 'users:manage',
};

const P = PERMISSIONS;

const ROLE_PERMISSIONS = {
    // full CRUD on everything
    [ROLES.FACILITY_ADMIN]: new Set(Object.values(PERMISSIONS)),

    // works assigned tickets: status updates + notes, read-only facilities for context,
    // sees the engineer roster and keeps their own availability up to date
    [ROLES.ENGINEER]: new Set([
        P.ANALYTICS_VIEW,
        P.INCIDENTS_VIEW,
        P.INCIDENTS_UPDATE_STATUS,
        P.INCIDENT_NOTES_CREATE,
        P.INCIDENT_NOTES_INTERNAL,
        P.FACILITIES_VIEW,
        P.ENGINEERS_VIEW,
    ]),

    // reports and tracks their own incidents
    [ROLES.EMPLOYEE]: new Set([
        P.ANALYTICS_VIEW,
        P.INCIDENTS_VIEW,
        P.INCIDENTS_CREATE,
        P.INCIDENTS_ESCALATE,
        P.INCIDENT_NOTES_CREATE,
    ]),
};

/**
 * Whether a role has a permission. Unknown or missing roles (e.g. logged out) have none.
 * @param {string | undefined} role one of ROLES
 * @param {string} permission one of PERMISSIONS
 * @returns {boolean}
 */
export function hasPermission(role, permission) {
    return ROLE_PERMISSIONS[role]?.has(permission) ?? false;
}
