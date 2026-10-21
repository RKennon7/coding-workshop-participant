/**
 * Per-ticket edit rules. Mirrors ALLOWED_TRANSITIONS / EDITABLE_FIELDS in backend/v1/app/routers/incidents.py.
 *
 * Unlike permissions.js (what a role can do anywhere), these depend on how the user relates to one
 * ticket: an engineer can only update status on tickets assigned to them, a reporter can only
 * close/reopen once it's resolved, etc. The backend enforces the same rules, this just keeps
 * the form from offering changes that would be rejected.
 */
import { ROLES } from './permissions.js';

// which statuses each status can move to
export const ALLOWED_TRANSITIONS = {
    'Open': ['In Progress', 'Blocked', 'Resolved', 'Closed'],
    'In Progress': ['Open', 'Blocked', 'Resolved'],
    'Blocked': ['In Progress', 'Resolved'],
    'Resolved': ['Open', 'In Progress', 'Closed'],
    'Closed': ['Open'],
};

export const ACTORS = {ADMIN: 'admin', ASSIGNEE: 'assignee', REPORTER: 'reporter'};

const REPORTER_FIELDS = new Set([
    'title', 'description', 'category', 'priority', 'is_escalated', 'escalation_reason',
    'status', 'building_id', 'floor_id', 'seat_id',
]);
const ASSIGNEE_FIELDS = new Set(['status', 'blocked_reason']);

// user is the decoded token from useAuth(): {uid, role, ...}. returns null if they can't edit the ticket
export function incidentActor(incident, user) {
    if (!incident || !user) return null;
    if (user.role === ROLES.FACILITY_ADMIN) return ACTORS.ADMIN;
    if (user.role === ROLES.ENGINEER && incident.assignee_id === user.uid) return ACTORS.ASSIGNEE;
    if (incident.reporter_id === user.uid) return ACTORS.REPORTER;
    return null;
}

export function canEditIncidentField(incident, user, fieldName) {
    const actor = incidentActor(incident, user);
    if (actor === ACTORS.ADMIN) return true;
    if (actor === ACTORS.REPORTER) {
        // reporters can't touch a closed ticket, an admin has to reopen it
        if (incident.status === 'Closed' || !REPORTER_FIELDS.has(fieldName)) return false;
        // their only status change is closing or reopening a resolved ticket
        return fieldName !== 'status' || incident.status === 'Resolved';
    }
    if (actor === ACTORS.ASSIGNEE) return ASSIGNEE_FIELDS.has(fieldName);
    return false;
}

// statuses offered in the form: the current one plus every move this user may make from it
export function statusChoices(incident, user) {
    const current = incident?.status;
    if (!current) return [];
    const actor = incidentActor(incident, user);
    let next = ALLOWED_TRANSITIONS[current] ?? [];
    if (actor === ACTORS.REPORTER) {
        next = current === 'Resolved' ? ['Open', 'Closed'] : [];
    } else if (actor === ACTORS.ASSIGNEE) {
        next = current === 'Closed' ? [] : next.filter((status) => status !== 'Closed');
    } else if (actor !== ACTORS.ADMIN) {
        next = [];
    }
    return [current, ...next];
}
